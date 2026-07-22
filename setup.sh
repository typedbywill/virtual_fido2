#!/usr/bin/env bash
set -euo pipefail

GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
BLUE="\033[94m"
BOLD="\033[1m"
RESET="\033[0m"

REPO_URL="https://github.com/typedbywill/virtual_fido2.git"
INSTALL_DIR="${VIRTUAL_FIDO2_HOME:-$HOME/.local/share/virtual-fido2}"

echo -e "${BLUE}${BOLD}=== Virtual FIDO2 Setup ===${RESET}\n"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 is not installed.${RESET}"
    exit 1
fi

if ! command -v systemctl &>/dev/null; then
    echo -e "${RED}Error: systemctl is not available. systemd is required.${RESET}"
    exit 1
fi

if [ -f "src/manager/__main__.py" ] && [ -f "requirements.txt" ]; then
    PROJECT_DIR="$(pwd)"
    echo -e "${GREEN}Using current directory: ${PROJECT_DIR}${RESET}"
else
    if [ ! -d "$INSTALL_DIR/.git" ]; then
        echo -e "${YELLOW}Cloning repository to ${INSTALL_DIR}…${RESET}"
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone "$REPO_URL" "$INSTALL_DIR"
    else
        echo -e "${GREEN}Repository already present at ${INSTALL_DIR}${RESET}"
    fi
    PROJECT_DIR="$INSTALL_DIR"
fi

cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment…${RESET}"
    python3 -m venv .venv
fi

echo -e "${YELLOW}Installing dependencies…${RESET}"
.venv/bin/pip install -q -r requirements.txt

echo -e "${GREEN}${BOLD}Launching Virtual FIDO2 Manager…${RESET}\n"
exec .venv/bin/python -m src.manager
