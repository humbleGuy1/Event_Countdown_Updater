from __future__ import annotations

import json
import mimetypes
from pathlib import Path
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class RobloxOpenCloudError(RuntimeError):
    pass


class RobloxCookieClient:
    """Uploads game icons via .ROBLOSECURITY cookie (Open Cloud API doesn't support this)."""

    _AUTH_URL = "https://auth.roblox.com"
    _PUBLISH_URL = "https://publish.roblox.com"

    def __init__(self, roblosecurity: str) -> None:
        self._cookie = roblosecurity

    def upload_game_icon(self, universe_id: str, icon_path: Path) -> dict:
        csrf = self._get_csrf_token()
        boundary = f"----event-countdown-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(icon_path.name)[0] or "application/octet-stream"
        file_bytes = icon_path.read_bytes()
        body = b"".join(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="request"; filename="{icon_path.name}"\r\n'.encode(),
                f"Content-Type: {content_type}\r\n\r\n".encode(),
                file_bytes,
                f"\r\n--{boundary}--\r\n".encode(),
            ]
        )
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "Cookie": f".ROBLOSECURITY={self._cookie}",
            "X-CSRF-TOKEN": csrf,
        }
        url = f"{self._PUBLISH_URL}/v1/games/{universe_id}/icon"
        request = Request(url, data=body, headers=headers, method="POST")
        try:
            with urlopen(request, timeout=30) as response:
                response_body = response.read()
                if not response_body:
                    return {}
                return json.loads(response_body.decode("utf-8"))
        except HTTPError as error:
            body_text = error.read().decode("utf-8", errors="replace")
            raise RobloxOpenCloudError(f"Roblox API returned {error.code}: {body_text}") from error
        except URLError as error:
            raise RobloxOpenCloudError(f"Could not reach Roblox API: {error.reason}") from error

    def _get_csrf_token(self) -> str:
        url = f"{self._AUTH_URL}/v2/logout"
        request = Request(
            url,
            data=b"",
            headers={"Cookie": f".ROBLOSECURITY={self._cookie}"},
            method="POST",
        )
        try:
            urlopen(request, timeout=10)
        except HTTPError as error:
            token = error.headers.get("x-csrf-token")
            if token:
                return token
            raise RobloxOpenCloudError(f"Could not get CSRF token: {error.code}") from error
        except URLError as error:
            raise RobloxOpenCloudError(f"Could not reach Roblox auth: {error.reason}") from error
        raise RobloxOpenCloudError("CSRF token not returned by Roblox auth endpoint.")


class RobloxOpenCloudClient:
    def __init__(self, api_key: str, base_url: str = "https://apis.roblox.com") -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def update_universe(self, universe_id: str, display_name: str) -> dict:
        query = urlencode({"updateMask": "displayName"})
        return self._json_request(
            "PATCH",
            f"/cloud/v2/universes/{universe_id}?{query}",
            {"displayName": display_name},
        )

    def update_place(self, universe_id: str, place_id: str, display_name: str) -> dict:
        query = urlencode({"updateMask": "displayName"})
        return self._json_request(
            "PATCH",
            f"/cloud/v2/universes/{universe_id}/places/{place_id}?{query}",
            {"displayName": display_name},
        )

    def update_game_icon(
        self,
        game_id: str,
        language_code: str,
        icon_path: Path,
        field_name: str,
    ) -> dict:
        path = (
            "/legacy-game-internationalization/v1/game-icon/"
            f"games/{game_id}/language-codes/{language_code}"
        )
        return self._multipart_request("POST", path, field_name, icon_path)

    def _json_request(self, method: str, path: str, payload: dict) -> dict:
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }
        return self._send(method, path, headers, body)

    def _multipart_request(self, method: str, path: str, field_name: str, file_path: Path) -> dict:
        boundary = f"----event-countdown-{uuid.uuid4().hex}"
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        file_bytes = file_path.read_bytes()
        body = b"".join(
            [
                f"--{boundary}\r\n".encode("utf-8"),
                (
                    f'Content-Disposition: form-data; name="{field_name}"; '
                    f'filename="{file_path.name}"\r\n'
                ).encode("utf-8"),
                f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"),
                file_bytes,
                f"\r\n--{boundary}--\r\n".encode("utf-8"),
            ]
        )
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "x-api-key": self.api_key,
        }
        return self._send(method, path, headers, body)

    def _send(self, method: str, path: str, headers: dict[str, str], body: bytes) -> dict:
        url = f"{self.base_url}{path}"
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                response_body = response.read()
                if not response_body:
                    return {}
                return json.loads(response_body.decode("utf-8"))
        except HTTPError as error:
            body_text = error.read().decode("utf-8", errors="replace")
            raise RobloxOpenCloudError(f"Roblox API returned {error.code}: {body_text}") from error
        except URLError as error:
            raise RobloxOpenCloudError(f"Could not reach Roblox API: {error.reason}") from error
        except json.JSONDecodeError as error:
            raise RobloxOpenCloudError("Roblox API returned non-JSON response.") from error
