"""Scheduled async status checks and an explicitly authorized Render replacement.

Default invocation is read-only monitoring. A reviewed authorization file is
required for a replacement; startup never manufactures this authorization.
"""
import argparse
import asyncio
import ipaddress
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID

import httpx
from dotenv import load_dotenv
from filelock import FileLock, Timeout
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.engine import make_url

from backend.database import make_engine
from maintenance.backup import create_backup, load_backup, restore_and_verify
from maintenance.provider import ProviderError, RenderProvider, external_tls_url, reconcile_creation
from maintenance.storage import atomic_json, read_json

logger = logging.getLogger(__name__)


class Authorization(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: UUID
    source_id: str
    service_id: str
    owner_id: str
    backend_url: str
    maintenance_at: datetime
    plan: str
    region: str
    postgres_version: str
    controller_cidr: str
    delete_source_authorized: bool
    permissions_and_quotas_confirmed: bool

    @field_validator("maintenance_at")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("Maintenance time must include a UTC offset")
        return value.astimezone(timezone.utc)

    @field_validator("controller_cidr")
    @classmethod
    def limited_network(cls, value):
        network = ipaddress.ip_network(value)
        if network.version != 4 or network.prefixlen != 32:
            raise ValueError("Use only the controller's public IPv4 /32 address")
        return str(network)


def should_replace(status: dict | None, now: datetime, authorized: bool, planned_at: datetime | None) -> bool:
    """Pure maintenance decision: unavailable/missing resources never trigger replacement."""
    if not authorized or not status or status.get("status") != "available":
        return False
    if now.tzinfo is None:
        raise ValueError("Use aware UTC timestamps")
    expiry = status.get("expiresAt")
    expires_at = datetime.fromisoformat(expiry.replace("Z", "+00:00")) if expiry else None
    if expires_at and (expires_at.tzinfo is None or expires_at <= now):
        return False
    return bool((planned_at and now >= planned_at) or (expires_at and expires_at - now <= timedelta(days=7)))


class MaintenanceController:
    """Own a persistent run journal; each irreversible step has a checkpoint."""

    def __init__(self, provider: RenderProvider, directory: Path, token: str, trial_url: str):
        self.provider = provider
        self.directory = directory
        self.token = token
        self.trial_url = trial_url

    async def backend(self, auth: Authorization, method: str, path: str, **kwargs):
        async with httpx.AsyncClient(timeout=90) as client:
            try:
                response = await client.request(method, auth.backend_url.rstrip("/") + path,
                                                headers={"Authorization": f"Bearer {self.token}"}, **kwargs)
            except httpx.RequestError:
                raise ProviderError("Backend request failed; maintenance remains active") from None
        if response.is_error:
            raise ProviderError(f"Backend verification HTTP {response.status_code}")
        return response.json() if response.content else None

    async def deploy(self, auth: Authorization, journal: dict, save, label: str):
        key = f"deploy_{label}"
        if journal.get(key + "_done"):
            return
        if not journal.get(key):
            if journal.get(key + "_submitted"):
                raise ProviderError("Uncertain deployment outcome. Inspect Render and record the matching deploy ID in the local journal before resuming.")
            journal[key + "_submitted"] = True
            save()
            deploy = await self.provider.request("POST", f"services/{auth.service_id}/deploys", json={"clearCache": "do_not_clear"})
            journal[key] = deploy["id"]
            save()
        deadline = asyncio.get_running_loop().time() + 1200
        while asyncio.get_running_loop().time() < deadline:
            row = await self.provider.request("GET", f"services/{auth.service_id}/deploys/{journal[key]}")
            if row["status"] == "live":
                journal[key + "_done"] = True
                save()
                return
            if row["status"] in ("build_failed", "update_failed", "canceled", "deactivated"):
                raise ProviderError("Deployment did not become live; keep writes blocked and inspect Render")
            await asyncio.sleep(10)
        raise ProviderError("Deployment polling timed out; resume the same recorded deployment")

    async def preflight(self, auth: Authorization):
        if auth.plan != "free" or not auth.delete_source_authorized or not auth.permissions_and_quotas_confirmed:
            raise ProviderError("Only the explicitly authorized single-free-instance path is supported")
        if not self.token or not self.trial_url:
            raise ProviderError("Maintenance token and isolated trial database are required")
        trial = make_url(self.trial_url)
        if not trial.drivername.startswith("postgresql") or trial.host not in ("localhost", "127.0.0.1", "::1"):
            raise ProviderError("Trial restore requires a disposable local PostgreSQL database")
        expected = {"RENDER_OWNER_ID": auth.owner_id, "RENDER_SERVICE_ID": auth.service_id,
                    "RENDER_DATABASE_ID": auth.source_id, "RENDER_REGION": auth.region,
                    "RENDER_POSTGRES_VERSION": auth.postgres_version, "RENDER_CONTROLLER_CIDR": auth.controller_cidr}
        if any(os.getenv(key) != value for key, value in expected.items()):
            raise ProviderError("Authorization resources differ from the configured allowlist")
        if not auth.backend_url.startswith("https://"):
            raise ProviderError("Cloud maintenance requires HTTPS")
        service = await self.provider.request("GET", f"services/{auth.service_id}")
        if service.get("ownerId") != auth.owner_id or service.get("serviceDetails", {}).get("url", "").rstrip("/") != auth.backend_url.rstrip("/"):
            raise ProviderError("Backend ownership or URL verification failed")
        if service.get("serviceDetails", {}).get("region") != auth.region:
            raise ProviderError("Backend and database must share the selected region")
        self.directory.mkdir(parents=True, exist_ok=True)
        test_path = self.directory / "storage-check.json"
        atomic_json(test_path, {"durable": True})
        if not read_json(test_path)["durable"]:
            raise ProviderError("Backup storage is not writable")
        # Verify local PostgreSQL/version before freezing or deleting anything.
        engine = make_engine(self.trial_url)
        try:
            with engine.connect() as connection:
                version = connection.exec_driver_sql("SHOW server_version_num").scalar_one()
                if str(int(version) // 10000) != auth.postgres_version:
                    raise ProviderError("Local trial and cloud PostgreSQL major versions must match")
        finally:
            engine.dispose()

    async def replace(self, auth: Authorization):
        await self.preflight(auth)
        run_path = self.directory / f"{auth.run_id}.json"
        auth_data = auth.model_dump(mode="json")
        journal = read_json(run_path) if run_path.exists() else {
            "authorization": auth_data, "run_id": str(auth.run_id), "stage": "started",
            "resource_name": f"gympulse-{auth.run_id.hex}",
            "reference_date": datetime.now(timezone.utc).date().isoformat(),
        }
        if journal["authorization"] != auth_data:
            raise ProviderError("Authorization changed: resume with the original file")
        if journal.get("stage") == "complete":
            logger.info("Replacement already complete run=%s; no repeated replacement", auth.run_id)
            return

        def save():
            journal["updated_at"] = datetime.now(timezone.utc).isoformat()
            atomic_json(run_path, journal)
            logger.info("run=%s stage=%s", auth.run_id, journal["stage"])

        save()
        backup_path = self.directory / f"{auth.run_id}.backup.json"
        if not journal.get("frozen"):
            source = await self.provider.database(auth.source_id)
            if not source or source.get("owner", {}).get("id") != auth.owner_id or source.get("status") != "available":
                raise ProviderError("Source must be accessible and belong to the designated workspace")
            expiry = source.get("expiresAt")
            if expiry and datetime.fromisoformat(expiry.replace("Z", "+00:00")) <= datetime.now(timezone.utc):
                raise ProviderError("Expired-source recovery requires a separate authorization; stop")
            if source.get("plan") != "free" or str(source.get("version")) != auth.postgres_version or source.get("region") != auth.region:
                raise ProviderError("Source plan, region or version differs from the authorized configuration")
            instances = await self.provider.databases(auth.owner_id)
            if any(row["id"] != auth.source_id and row.get("plan") == "free" for row in instances):
                raise ProviderError("Workspace quota differs from the supported single-instance path")
            source_connection = await self.provider.connection(auth.source_id)
            env = await self.provider.request("GET", f"services/{auth.service_id}/env-vars/DATABASE_URL")
            if make_url(env["value"]).host != make_url(source_connection["internalConnectionString"]).host:
                raise ProviderError("Backend DATABASE_URL does not identify the authorized source")
            # DB row lock waits for existing writes and excludes all subsequent writes.
            await self.backend(auth, "PUT", "/admin/maintenance", json={"blocked": True})
            await self.provider.env(auth.service_id, "MAINTENANCE_MODE", "true")
            journal.update(frozen=True, stage="writes_frozen")
            save()

        if not journal.get("backup_ready"):
            # The frozen source is stable, so recapturing after a crash is safe.
            source_connection = await self.provider.connection(auth.source_id)
            source_engine = make_engine(external_tls_url(source_connection["externalConnectionString"]))
            try:
                backup = create_backup(source_engine, auth.source_id, backup_path,
                                       datetime.fromisoformat(journal["reference_date"]).date())
            finally:
                source_engine.dispose()
            journal.update(backup_ready=True, backup_created_at=backup.created_at.isoformat(), stage="backup_saved")
            save()
        backup = load_backup(backup_path, auth.source_id)

        if not journal.get("trial_verified"):
            trial_engine = make_engine(self.trial_url)
            try:
                journal["trial_result"] = restore_and_verify(trial_engine, backup)
            finally:
                trial_engine.dispose()
            journal.update(trial_verified=True, stage="isolated_restore_verified")
            save()

        if not journal.get("source_deleted"):
            # Load again immediately before deletion; a missing/corrupt backup stops us.
            load_backup(backup_path, auth.source_id)
            source = await self.provider.database(auth.source_id)
            if source:
                if source.get("owner", {}).get("id") != auth.owner_id:
                    raise ProviderError("Source ownership changed; deletion refused")
                journal["stage"] = "source_deletion_submitted"
                save()
                await self.provider.request("DELETE", f"postgres/{auth.source_id}")
            deadline = asyncio.get_running_loop().time() + 600
            while await self.provider.database(auth.source_id) is not None:
                if asyncio.get_running_loop().time() >= deadline:
                    raise ProviderError("Source deletion not confirmed")
                await asyncio.sleep(5)
            journal.update(source_deleted=True, stage="source_deletion_confirmed")
            save()

        if not journal.get("target_id"):
            if journal.get("creation_submitted"):
                journal["target_id"] = reconcile_creation(await self.provider.databases(auth.owner_id), journal["resource_name"], auth.owner_id)
            else:
                journal.update(creation_submitted=True, stage="target_creation_submitted")
                save()
                target = await self.provider.request("POST", "postgres", json={
                    "name": journal["resource_name"], "ownerId": auth.owner_id, "plan": "free",
                    "region": auth.region, "version": auth.postgres_version,
                    "databaseName": "gympulse", "databaseUser": "gympulse",
                    "ipAllowList": [{"cidrBlock": auth.controller_cidr, "description": "Authorized maintenance controller"}],
                })
                journal["target_id"] = target["id"]
            journal["stage"] = "target_recorded"
            save()

        target = await self.provider.wait_database(journal["target_id"])
        if (target.get("owner", {}).get("id") != auth.owner_id
                or target.get("name") != journal["resource_name"]
                or target.get("plan") != auth.plan
                or target.get("region") != auth.region
                or str(target.get("version")) != auth.postgres_version):
            raise ProviderError("Recorded target identity differs from provider state")
        target_connection = await self.provider.connection(journal["target_id"])
        if not journal.get("target_restored"):
            target_engine = make_engine(external_tls_url(target_connection["externalConnectionString"]))
            try:
                journal["restore_result"] = restore_and_verify(target_engine, backup)
            finally:
                target_engine.dispose()
            journal.update(target_restored=True, stage="target_restored_verified")
            save()

        if not journal.get("switch_verified"):
            await self.provider.env(auth.service_id, "DATABASE_URL", target_connection["internalConnectionString"])
            await self.deploy(auth, journal, save, "switch")
            await self.verify_backend(auth, backup)
            await self.backend(auth, "POST", "/admin/write-probe")
            await self.verify_backend(auth, backup)
            journal.update(switch_verified=True, stage="switch_and_test_write_verified")
            save()
            atomic_json(self.directory / "active.json", {"database_id": journal["target_id"], "service_id": auth.service_id,
                                                        "owner_id": auth.owner_id, "run_id": str(auth.run_id), "replacement_status": "verified"})

        # Commit success and active identity before reopening writes, including on resume.
        atomic_json(self.directory / "active.json", {"database_id": journal["target_id"], "service_id": auth.service_id,
                                                    "owner_id": auth.owner_id, "run_id": str(auth.run_id), "replacement_status": "verified"})
        await self.provider.env(auth.service_id, "MAINTENANCE_MODE", "false")
        await self.deploy(auth, journal, save, "reopen")
        await self.backend(auth, "PUT", "/admin/maintenance", json={"blocked": False})
        journal["stage"] = "complete"
        save()

    async def verify_backend(self, auth: Authorization, backup):
        from backend.schemas import Recommendation, WorkoutOut
        rows = await self.backend(auth, "GET", "/workouts")
        actual = sorted([WorkoutOut.model_validate(row) for row in rows], key=lambda row: row.id)
        if actual != sorted(backup.records, key=lambda row: row.id):
            raise ProviderError("Backend contents differ from restored backup")
        rules = await self.backend(auth, "GET", "/recommendations", params={"as_of": backup.reference_date.isoformat()})
        if [Recommendation.model_validate(row) for row in rules] != backup.recommendations:
            raise ProviderError("Backend recommendation verification failed")


async def run(args):
    load_dotenv()
    directory = Path(os.getenv("MAINTENANCE_DIR", "runtime/maintenance")).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(directory / "controller.log", encoding="utf-8")])
    # httpx logs the requested URL; don't enable verbose wire/SQL logging with secrets.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    interval = max(10, int(os.getenv("CHECK_INTERVAL_SECONDS", "300")))
    authorization = Authorization.model_validate(read_json(Path(args.authorization))) if args.authorization else None
    try:
        with FileLock(str(directory / "controller.lock"), timeout=0):
            provider = RenderProvider(os.getenv("RENDER_API_KEY", ""))
            controller = MaintenanceController(provider, directory, os.getenv("MAINTENANCE_TOKEN", ""), os.getenv("TRIAL_DATABASE_URL", ""))
            try:
                while True:
                    try:
                        active_path = directory / "active.json"
                        active = read_json(active_path) if active_path.exists() else {}
                        if active and (active.get("owner_id") != os.getenv("RENDER_OWNER_ID") or active.get("service_id") != os.getenv("RENDER_SERVICE_ID")):
                            raise ProviderError("Persisted active resource does not match configured workspace/backend")
                        database_id = active.get("database_id") or os.getenv("RENDER_DATABASE_ID")
                        if not os.getenv("RENDER_API_KEY") or not database_id:
                            logger.info("Cloud status checks disabled: configure Render identifiers and API key; no replacement authorized")
                        else:
                            status = await provider.database(database_id)
                            logger.info("Async status check database=%s status=%s expiresAt=%s", database_id,
                                        status.get("status") if status else "missing", status.get("expiresAt") if status else None)
                            if authorization:
                                journal_path = directory / f"{authorization.run_id}.json"
                                pending = read_json(journal_path) if journal_path.exists() else None
                                if pending and pending.get("stage") != "complete":
                                    await controller.replace(authorization)
                                elif not pending and should_replace(status, datetime.now(timezone.utc), True, authorization.maintenance_at):
                                    if database_id != authorization.source_id:
                                        raise ProviderError("Active instance differs from this authorization")
                                    await controller.replace(authorization)
                    except Exception as error:
                        # Exception messages from DB/HTTP libraries may contain secrets.
                        logger.error("Maintenance stopped safely: %s. Preserve journal/backup and inspect the documented recovery procedure.",
                                     str(error) if isinstance(error, (ProviderError, ValueError)) and type(error) in (ProviderError, ValueError) else type(error).__name__)
                        if args.once or authorization:
                            return 1
                    if args.once:
                        return 0
                    await asyncio.sleep(interval)
            finally:
                await provider.close()
    except Timeout:
        logger.error("Another controller already owns this maintenance directory")
        return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Check once and exit")
    parser.add_argument("--authorization", help="Reviewed JSON authorizing only the named resources")
    args = parser.parse_args()
    try:
        return asyncio.run(run(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
