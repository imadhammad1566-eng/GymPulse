"""Environment configuration shared by independent entry points."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    database_url: str
    maintenance_token: str
    write_token: str
    maintenance_mode: bool

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.getenv("DATABASE_URL", "sqlite:///./runtime/gympulse.db"),
            maintenance_token=os.getenv("MAINTENANCE_TOKEN", ""),
            write_token=os.getenv("APP_WRITE_TOKEN", ""),
            maintenance_mode=os.getenv("MAINTENANCE_MODE", "false").lower() == "true",
        )
