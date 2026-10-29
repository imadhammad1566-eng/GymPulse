"""HTTP boundary: explicit timeouts and safe messages, no direct DB access."""
import os

import httpx
from dotenv import load_dotenv

load_dotenv()


class ApiError(Exception):
    """User-readable error without connection strings or credentials."""


class GymClient:
    def __init__(self, base_url: str | None = None, token: str = ""):
        self.base_url = (base_url or os.getenv("API_BASE_URL", "http://127.0.0.1:8000")).rstrip("/")
        self.token = token

    def request(self, method: str, path: str, **kwargs):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = httpx.request(method, self.base_url + path, headers=headers, timeout=60, **kwargs)
        except httpx.RequestError:
            raise ApiError("Cannot reach the API. Check that the backend is running; a sleeping cloud service may take a minute.") from None
        if response.is_error:
            try:
                detail = response.json().get("detail", "Request failed")
            except ValueError:
                detail = "The server could not complete this request. Please try again."
            if isinstance(detail, list):
                detail = "; ".join(item.get("msg", "Invalid input") for item in detail)
            raise ApiError(f"{response.status_code}: {detail}")
        return response.json() if response.content else None
