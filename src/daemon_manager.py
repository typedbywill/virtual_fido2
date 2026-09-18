import os
import sys
import shutil
import subprocess
import argparse
import getpass
from typing import Optional, Tuple

SERVICE_NAME = "virtual-fido2.service"
SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")
SERVICE_PATH = os.path.join(SYSTEMD_USER_DIR, SERVICE_NAME)

GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


class SystemdNotAvailableError(Exception):
    pass


class DaemonError(Exception):
    pass


def print_success(msg: str) -> None:
    print(f"{GREEN}✔ {msg}{RESET}")


def print_info(msg: str) -> None:
    print(f"{BLUE}ℹ {msg}{RESET}")


def print_warning(msg: str) -> None:
    print(f"{YELLOW}⚠ {msg}{RESET}")


def print_error(msg: str) -> None:
    print(f"{RED}✘ {msg}{RESET}")


def check_systemd() -> None:
    if not shutil.which("systemctl"):
        raise SystemdNotAvailableError(
            "systemctl is not available. This daemon manager requires a Linux system with systemd."
        )


def run_cmd(cmd: list, check: bool = True, capture: bool = False) -> Tuple[int, str, str]:
    try:
        if capture:
            res = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return res.returncode, res.stdout, res.stderr
        res = subprocess.run(cmd, check=check)
        return res.returncode, "", ""
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.strip() if getattr(e, "stderr", None) else str(e)
        if check:
            raise DaemonError(f"Command failed: {' '.join(cmd)} — {stderr}") from e
        return e.returncode, "", stderr
# Add project root to sys.path if run directly
PROJECT_ROOT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT_PATH not in sys.path:
    sys.path.insert(0, PROJECT_ROOT_PATH)

from src.config import DAEMON_HOST, DAEMON_PORT, PROJECT_ROOT


def get_service_content(python_path: Optional[str] = None, project_root: Optional[str] = None) -> str:
    python_path = python_path or sys.executable
    project_root = project_root or PROJECT_ROOT
    return f"""[Unit]
Description=Virtual FIDO2 / WebAuthn Authenticator Daemon
After=network.target

[Service]
Type=simple
ExecStart={python_path} -m uvicorn src.main:app --host {DAEMON_HOST} --port {DAEMON_PORT}
WorkingDirectory={project_root}
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""


def install(python_path: Optional[str] = None, project_root: Optional[str] = None) -> dict:
    check_systemd()
    python_path = python_path or sys.executable
    project_root = project_root or PROJECT_ROOT
    os.makedirs(SYSTEMD_USER_DIR, exist_ok=True)

    with open(SERVICE_PATH, "w", encoding="utf-8") as f:
        f.write(get_service_content(python_path, project_root))

    run_cmd(["systemctl", "--user", "daemon-reload"])
    run_cmd(["systemctl", "--user", "enable", SERVICE_NAME])
    run_cmd(["systemctl", "--user", "restart", SERVICE_NAME])
    run_cmd(["loginctl", "enable-linger", getpass.getuser()], check=False)

    return {
        "success": True,
        "service_path": SERVICE_PATH,
        "message": "Virtual FIDO2 Authenticator is installed and active.",
    }


def uninstall() -> dict:
    check_systemd()
    run_cmd(["systemctl", "--user", "stop", SERVICE_NAME], check=False)
    run_cmd(["systemctl", "--user", "disable", SERVICE_NAME], check=False)

    if os.path.exists(SERVICE_PATH):
        os.remove(SERVICE_PATH)

    run_cmd(["systemctl", "--user", "daemon-reload"])
    return {"success": True, "message": "Virtual FIDO2 daemon has been successfully uninstalled."}


def status() -> dict:
    check_systemd()
    code, out, err = run_cmd(
        ["systemctl", "--user", "status", SERVICE_NAME], check=False, capture=True
    )
    active = code == 0
    return {
        "active": active,
        "output": out or err,
        "message": "ACTIVE" if active else "INACTIVE/ERROR",
    }


def start() -> dict:
    check_systemd()
    run_cmd(["systemctl", "--user", "start", SERVICE_NAME])
    return {"success": True, "message": "Service started."}


def stop() -> dict:
    check_systemd()
    run_cmd(["systemctl", "--user", "stop", SERVICE_NAME])
    return {"success": True, "message": "Service stopped."}


def restart() -> dict:
    check_systemd()
    run_cmd(["systemctl", "--user", "restart", SERVICE_NAME])
    return {"success": True, "message": "Service restarted."}


def show_logs(follow: bool = True) -> None:
    check_systemd()
    cmd = ["journalctl", "--user", "-u", SERVICE_NAME, "-n", "30"]
    if follow:
        cmd.append("-f")
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        pass


def install_cli() -> None:
    print_info("Installing Virtual FIDO2 Daemon as a systemd user service...")
    try:
        result = install()
    except (SystemdNotAvailableError, DaemonError) as e:
        print_error(str(e))
        sys.exit(1)

    print_success(f"Created service file at: {result['service_path']}")
    print_success(result["message"])
    print(f"\n{BOLD}Useful Commands:{RESET}")
    print("  Check status:  python src/daemon_manager.py status")
    print("  Follow logs:   python src/daemon_manager.py logs")
    print("  Stop daemon:   python src/daemon_manager.py stop")
    print("  Dashboard:     Go to http://localhost:8000 in your browser")


def uninstall_cli() -> None:
    print_info("Uninstalling Virtual FIDO2 Daemon...")
    try:
        uninstall()
    except (SystemdNotAvailableError, DaemonError) as e:
        print_error(str(e))
        sys.exit(1)
    print_success("Virtual FIDO2 daemon has been successfully uninstalled.")


def status_cli() -> None:
    try:
        result = status()
    except SystemdNotAvailableError as e:
        print_error(str(e))
        sys.exit(1)

    if result["active"]:
        print(f"{GREEN}{BOLD}● Virtual FIDO2 Service Status (ACTIVE){RESET}")
    else:
        print(f"{RED}{BOLD}● Virtual FIDO2 Service Status (INACTIVE/ERROR){RESET}")
    print(result["output"])


def start_cli() -> None:
    print_info("Starting service...")
    try:
        start()
    except (SystemdNotAvailableError, DaemonError) as e:
        print_error(str(e))
        sys.exit(1)
    print_success("Service started.")


def stop_cli() -> None:
    print_info("Stopping service...")
    try:
        stop()
    except (SystemdNotAvailableError, DaemonError) as e:
        print_error(str(e))
        sys.exit(1)
    print_success("Service stopped.")


def restart_cli() -> None:
    print_info("Restarting service...")
    try:
        restart()
    except (SystemdNotAvailableError, DaemonError) as e:
        print_error(str(e))
        sys.exit(1)
    print_success("Service restarted.")


def show_logs_cli() -> None:
    print_info("Displaying recent logs (Press Ctrl+C to exit log streaming):")
    try:
        show_logs(follow=True)
    except SystemdNotAvailableError as e:
        print_error(str(e))
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExiting logs view.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage the Virtual FIDO2 Authenticator background daemon and autostart configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Available Actions:
  install     Configure as a systemd user daemon, enable autostart on system boot, and start it
  uninstall   Stop service, disable autostart, and remove configurations
  status      Show current service state and diagnostic info
  start       Start the service immediately
  stop        Stop the service immediately
  restart     Restart the service immediately
  logs        Display and stream journalctl logs for the authenticator
""",
    )
    parser.add_argument(
        "action",
        choices=["install", "uninstall", "status", "start", "stop", "restart", "logs"],
        help="Action to execute",
    )
    args = parser.parse_args()

    actions = {
        "install": install_cli,
        "uninstall": uninstall_cli,
        "status": status_cli,
        "start": start_cli,
        "stop": stop_cli,
        "restart": restart_cli,
        "logs": show_logs_cli,
    }
    actions[args.action]()


if __name__ == "__main__":
    main()
