import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from src.config import daemon_base_url
from src import daemon_manager


API_HEADER = {"X-Requested-With": "Virtual-FIDO2", "Content-Type": "application/json"}


def is_daemon_online() -> bool:
    try:
        req = urllib.request.Request(
            f"{daemon_base_url()}/status",
            headers={"X-Requested-With": "Virtual-FIDO2"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def get_daemon_status() -> Optional[Dict[str, Any]]:
    try:
        req = urllib.request.Request(
            f"{daemon_base_url()}/status",
            headers={"X-Requested-With": "Virtual-FIDO2"},
        )
        with urllib.request.urlopen(req, timeout=2) as resp:
            return json.loads(resp.read().decode())
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
        return None


def get_systemd_status() -> dict:
    try:
        return daemon_manager.status()
    except daemon_manager.SystemdNotAvailableError:
        return {"active": False, "output": "systemd not available", "message": "UNAVAILABLE"}


def install_service() -> dict:
    return daemon_manager.install()


def uninstall_service() -> dict:
    return daemon_manager.uninstall()


def start_service() -> dict:
    return daemon_manager.start()


def stop_service() -> dict:
    return daemon_manager.stop()


def restart_service() -> dict:
    return daemon_manager.restart()


def _api_request(method: str, path: str, body: Optional[dict] = None) -> Any:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"{daemon_base_url()}{path}",
        data=data,
        headers=API_HEADER,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def list_credentials_api() -> List[dict]:
    return _api_request("GET", "/credentials")


def import_credential_api(payload: dict) -> dict:
    return _api_request("POST", "/credentials", payload)


def generate_credential_api(payload: dict) -> dict:
    return _api_request("POST", "/credentials/generate", payload)


def update_credential_api(credential_id: str, payload: dict) -> dict:
    return _api_request("PUT", f"/credentials/{credential_id}", payload)


def delete_credential_api(credential_id: str) -> dict:
    return _api_request("DELETE", f"/credentials/{credential_id}")
