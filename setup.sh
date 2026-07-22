#!/usr/bin/env bash
set -euo pipefail

GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
BLUE="\033[94m"
BOLD="\033[1m"
RESET="\033[0m"

ARCHIVE_URL="https://codeload.github.com/typedbywill/virtual_fido2/tar.gz/main"
INSTALL_DIR="${VIRTUAL_FIDO2_HOME:-$HOME/.local/share/virtual-fido2}"
LAUNCHER="${HOME}/.local/bin/virtual-fido2"

echo -e "${BLUE}${BOLD}=== Virtual FIDO2 Setup ===${RESET}\n"

if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 is not installed.${RESET}"
    exit 1
fi

if ! command -v systemctl &>/dev/null; then
    echo -e "${RED}Error: systemctl is not available. systemd is required.${RESET}"
    exit 1
fi

if ! command -v curl &>/dev/null; then
    echo -e "${RED}Error: curl is not installed.${RESET}"
    exit 1
fi

if ! command -v tar &>/dev/null; then
    echo -e "${RED}Error: tar is not installed.${RESET}"
    exit 1
fi

# Developer mode: running from a local checkout
if [ -f "src/manager/__main__.py" ] && [ -f "requirements.txt" ]; then
    PROJECT_DIR="$(pwd)"
    echo -e "${GREEN}Using local checkout: ${PROJECT_DIR}${RESET}"
else
    PROJECT_DIR="$INSTALL_DIR"
    if [ ! -f "$PROJECT_DIR/src/manager/__main__.py" ]; then
        echo -e "${YELLOW}Downloading Virtual FIDO2 to ${INSTALL_DIR}…${RESET}"
        tmp_dir="$(mktemp -d)"
        trap 'rm -rf "$tmp_dir"' EXIT
        curl -fsSL "$ARCHIVE_URL" | tar xz -C "$tmp_dir"
        mkdir -p "$(dirname "$INSTALL_DIR")"
        rm -rf "$INSTALL_DIR"
        mv "$tmp_dir/virtual_fido2-main" "$INSTALL_DIR"
        echo -e "${GREEN}Download complete.${RESET}"
    else
        echo -e "${GREEN}Using existing install at ${INSTALL_DIR}${RESET}"
    fi
fi

cd "$PROJECT_DIR"

if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment…${RESET}"
    python3 -m venv .venv
fi

echo -e "${YELLOW}Installing dependencies…${RESET}"
.venv/bin/pip install -q -r requirements.txt

if [ "$PROJECT_DIR" = "$INSTALL_DIR" ]; then
    mkdir -p "$(dirname "$LAUNCHER")"
    cat > "$LAUNCHER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
INSTALL_DIR="\${VIRTUAL_FIDO2_HOME:-\$HOME/.local/share/virtual-fido2}"
cd "\$INSTALL_DIR"
exec "\$INSTALL_DIR/.venv/bin/python" -m src.manager
EOF
    chmod +x "$LAUNCHER"
    echo -e "${GREEN}Command installed: ${BOLD}virtual-fido2${RESET}"
    if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
        echo -e "${YELLOW}Tip: add ~/.local/bin to your PATH to run 'virtual-fido2' from anywhere.${RESET}"
    fi
fi

echo -e "${GREEN}${BOLD}Launching Virtual FIDO2 Manager…${RESET}\n"
exec .venv/bin/python -m src.manager
