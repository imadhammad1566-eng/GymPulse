"""Render REST adapter. Mutations never retry an uncertain POST."""
import asyncio
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import httpx

logger = logging.getLogger(__name__)


class ProviderError(RuntimeError):
    pass


class RenderProvider:
    def __init__(self, api_key: str, transport=None):
        self.client = httpx.AsyncClient(
            base_url="https://api.render.com/v1/", headers={"Authorization": f"Bearer {api_key}"},
            timeout=30, transport=transport,
        )

    async def close(self):
        await self.client.aclose()

    async def request(self, method: str, path: str, *, missing_ok=False, **kwargs):
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                response = await self.client.request(method, path, **kwargs)
            except httpx.RequestError:
                if attempt + 1 == attempts:
                    raise ProviderError("Provider network operation failed; mutation outcome may be uncertain") from None
            else:
                if missing_ok and response.status_code == 404:
                    return None
                if response.status_code in (429, 500, 502, 503, 504) and attempt + 1 < attempts:
                    logger.warning("Temporary Render failure HTTP %s; bounded retry", response.status_code)
                elif response.is_error:
                    raise ProviderError(f"Render HTTP {response.status_code}; no automatic upgrade or destructive retry")
                else:
                    return response.json() if response.content else {}
            await asyncio.sleep(min(2 ** attempt, 4))
        raise ProviderError("Provider retries exhausted")

    async def database(self, database_id: str):
        return await self.request("GET", f"postgres/{database_id}", missing_ok=True)

    async def databases(self, owner_id: str) -> list[dict]:
        rows = []
        cursor = None
        for _ in range(100):
            params = {"ownerId": owner_id, "limit": 100}
            if cursor:
                params["cursor"] = cursor
            page = await self.request("GET", "postgres", params=params)
            rows.extend(item["postgres"] for item in page)
            if len(page) < 100:
                return rows
            next_cursor = page[-1].get("cursor")
            if not next_cursor or next_cursor == cursor:
                break
            cursor = next_cursor
        raise ProviderError("Could not establish complete provider state")

    async def connection(self, database_id: str) -> dict:
        result = await self.request("GET", f"postgres/{database_id}/connection-info")
        if not result.get("externalConnectionString") or not result.get("internalConnectionString"):
            raise ProviderError("Provider did not return required connection addresses")
        return result

    async def env(self, service_id: str, key: str, value: str):
        await self.request("PUT", f"services/{service_id}/env-vars/{key}", json={"value": value})

    async def wait_database(self, database_id: str, timeout: int = 1200):
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            row = await self.database(database_id)
            if row and row.get("status") == "available":
                return row
            if row is None or row.get("status") in ("failed", "suspended"):
                raise ProviderError("Target database is missing or failed")
            await asyncio.sleep(10)
        raise ProviderError("Database readiness polling timed out")


def external_tls_url(value: str) -> str:
    parts = urlsplit(value)
    query = dict(parse_qsl(parts.query))
    query["sslmode"] = "require"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def reconcile_creation(rows: list[dict], resource_name: str, owner_id: str) -> str:
    """An unresolved request must never cause a second create request."""
    matches = [row["id"] for row in rows if row.get("name") == resource_name and row.get("owner", {}).get("id") == owner_id]
    if len(matches) != 1:
        raise ProviderError("Uncertain instance creation: cannot identify exactly one target. Stop and inspect Render; do not create again.")
    return matches[0]
