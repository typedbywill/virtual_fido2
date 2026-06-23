import os
import sys
import shutil
import subprocess
import argparse
import getpass

# Colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"

SERVICE_NAME = "virtual-fido2.service"
SYSTEMD_USER_DIR = os.path.expanduser("~/.config/systemd/user")
SERVICE_PATH = os.path.join(SYSTEMD_USER_DIR, SERVICE_NAME)

def print_success(msg):
    print(f"{GREEN}✔ {msg}{RESET}")

def print_info(msg):
    print(f"{BLUE}ℹ {msg}{RESET}")

def print_warning(msg):
    print(f"{YELLOW}⚠ {msg}{RESET}")

def print_error(msg):
    print(f"{RED}✘ {msg}{RESET}")

def check_systemd():
    if not shutil.which("systemctl"):
        print_error("systemctl is not available. This daemon manager requires a Linux system with systemd.")
        sys.exit(1)

def run_cmd(cmd, check=True, capture=False):
    try:
        if capture:
            res = subprocess.run(cmd, check=check, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return res.returncode, res.stdout, res.stderr
        else:
            res = subprocess.run(cmd, check=check)
            return res.returncode, "", ""
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"Command failed: {' '.join(cmd)}")
            if hasattr(e, 'stderr') and e.stderr:
                print(f"Details: {e.stderr.strip()}")
            sys.exit(1)
        return e.returncode, "", str(e)

def install():
    check_systemd()
    print_info(f"Installing Virtual FIDO2 Daemon as a systemd user service...")

    # Determine paths
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    python_path = sys.executable
    
    # Ensure systemd user folder exists
    os.makedirs(SYSTEMD_USER_DIR, exist_ok=True)

    # Generate systemd configuration
    service_content = f"""[Unit]
Description=Virtual FIDO2 / WebAuthn Authenticator Daemon
After=network.target

[Service]
Type=simple
ExecStart={python_path} -m uvicorn src.main:app --host 127.0.0.1 --port 8000
WorkingDirectory={project_root}
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
"""

    try:
        with open(SERVICE_PATH, "w", encoding="utf-8") as f:
            f.write(service_content)
        print_success(f"Created service file at: {SERVICE_PATH}")
    except Exception as e:
        print_error(f"Failed to write service file: {e}")
        sys.exit(1)

    # Reload systemd and enable service
    print_info("Reloading systemd user configuration...")
    run_cmd(["systemctl", "--user", "daemon-reload"])
    
    print_info("Enabling Virtual FIDO2 autostart...")
    run_cmd(["systemctl", "--user", "enable", SERVICE_NAME])
    
    print_info("Starting Virtual FIDO2 service...")
    run_cmd(["systemctl", "--user", "restart", SERVICE_NAME])
    
    # Configure linger so user service runs without active GUI session (starts at boot)
    username = getpass.getuser()
    print_info(f"Enabling lingering for user '{username}' to allow autostart at system boot...")
    run_cmd(["loginctl", "enable-linger", username], check=False)

    print_success(f"Virtual FIDO2 Authenticator is installed and active!")
    print(f"\n{BOLD}Useful Commands:{RESET}")
    print(f"  Check status:  python src/daemon_manager.py status")
    print(f"  Follow logs:   python src/daemon_manager.py logs")
    print(f"  Stop daemon:   python src/daemon_manager.py stop")
    print(f"  Dashboard:     Go to http://localhost:8000 in your browser")

def uninstall():
    check_systemd()
    print_info("Uninstalling Virtual FIDO2 Daemon...")

    # Stop service
    print_info("Stopping background service...")
    run_cmd(["systemctl", "--user", "stop", SERVICE_NAME], check=False)
    
    # Disable service
    print_info("Disabling autostart service...")
    run_cmd(["systemctl", "--user", "disable", SERVICE_NAME], check=False)

    # Delete service file
    if os.path.exists(SERVICE_PATH):
        try:
            os.remove(SERVICE_PATH)
            print_success(f"Deleted service file: {SERVICE_PATH}")
        except Exception as e:
            print_error(f"Failed to delete service file: {e}")
    else:
        print_warning("No service file found to delete.")

    # Reload systemd
    print_info("Reloading systemd user configuration...")
    run_cmd(["systemctl", "--user", "daemon-reload"])
    
    print_success("Virtual FIDO2 daemon has been successfully uninstalled.")

def status():
    check_systemd()
    code, out, err = run_cmd(["systemctl", "--user", "status", SERVICE_NAME], check=False, capture=True)
    if code == 0:
        print(f"{GREEN}{BOLD}● Virtual FIDO2 Service Status (ACTIVE){RESET}")
        print(out)
    else:
        print(f"{RED}{BOLD}● Virtual FIDO2 Service Status (INACTIVE/ERROR){RESET}")
        if out:
            print(out)
        else:
            print(err)

def start():
    check_systemd()
    print_info("Starting service...")
    run_cmd(["systemctl", "--user", "start", SERVICE_NAME])
    print_success("Service started.")

def stop():
    check_systemd()
    print_info("Stopping service...")
    run_cmd(["systemctl", "--user", "stop", SERVICE_NAME])
    print_success("Service stopped.")

def restart():
    check_systemd()
    print_info("Restarting service...")
    run_cmd(["systemctl", "--user", "restart", SERVICE_NAME])
    print_success("Service restarted.")

def show_logs():
    check_systemd()
    print_info("Displaying recent logs (Press Ctrl+C to exit log streaming):")
    try:
        # Popen to allow real-time terminal stream matching journalctl -f
        subprocess.run(["journalctl", "--user", "-u", SERVICE_NAME, "-n", "30", "-f"])
    except KeyboardInterrupt:
        print("\nExiting logs view.")

def main():
    parser = argparse.ArgumentParser(
        description="Manage the Virtual FIDO2 Authenticator background daemon and autostart configuration.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""Available Actions:
  install     Configure as a systemd user daemon, enable autostart on system boot, and start it
  uninstall   Stop service, disable autostart, and remove configurations
  status      Show current service state and diagnostic info
  start       Start the service immediately
  stop        Stop the service immediately
  restart     Restart the service immediately
  logs        Display and stream journalctl logs for the authenticator
"""
    )
    parser.add_argument("action", choices=["install", "uninstall", "status", "start", "stop", "restart", "logs"], help="Action to execute")
    args = parser.parse_args()

    if args.action == "install":
        install()
    elif args.action == "uninstall":
        uninstall()
    elif args.action == "status":
        status()
    elif args.action == "start":
        start()
    elif args.action == "stop":
        stop()
    elif args.action == "restart":
        restart()
    elif args.action == "logs":
        show_logs()

if __name__ == "__main__":
    main()
