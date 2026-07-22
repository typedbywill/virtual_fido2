import os

_SRC_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(_SRC_DIR)

STORE_FILE = os.path.expanduser(
    os.environ.get("VIRTUAL_FIDO2_STORE", os.path.join(PROJECT_ROOT, "config.json"))
)
DAEMON_HOST = os.environ.get("VIRTUAL_FIDO2_HOST", "127.0.0.1")
DAEMON_PORT = int(os.environ.get("VIRTUAL_FIDO2_PORT", "8000"))
EXTENSION_DIR = os.path.join(PROJECT_ROOT, "src", "browser_integration", "extension")

def daemon_base_url() -> str:
    return f"http://{DAEMON_HOST}:{DAEMON_PORT}"
