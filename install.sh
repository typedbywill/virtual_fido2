#!/bin/bash

# Exit immediately if any command returns a non-zero exit status
set -e

# Colors
GREEN="\033[92m"
YELLOW="\033[93m"
RED="\033[91m"
BLUE="\033[94m"
BOLD="\033[1m"
RESET="\033[0m"

echo -e "${BLUE}${BOLD}=== Virtual FIDO2 Authenticator Setup ===${RESET}\n"

# Step 1: Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: python3 is not installed. Please install it first.${RESET}"
    exit 1
fi

# Step 2: Check systemd
if ! command -v systemctl &> /dev/null; then
    echo -e "${RED}Error: systemctl is not available. This service requires systemd.${RESET}"
    exit 1
fi

# Step 3: Setup python virtual environment
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}Creating Python virtual environment (.venv)...${RESET}"
    python3 -m venv .venv
    echo -e "${GREEN}Created virtual environment.${RESET}"
else
    echo -e "${GREEN}Virtual environment (.venv) already exists.${RESET}"
fi

# Step 4: Install dependencies
echo -e "${YELLOW}Installing dependencies from requirements.txt...${RESET}"
.venv/bin/pip install -r requirements.txt
echo -e "${GREEN}Dependencies installed.${RESET}"

# Step 5: Install daemon
echo -e "${YELLOW}Running daemon registration manager...${RESET}"
.venv/bin/python src/daemon_manager.py install

echo -e "\n${GREEN}${BOLD}Setup completed successfully!${RESET}"
echo -e "You can now open the Web UI dashboard at: ${BLUE}${BOLD}http://localhost:8000/${RESET}"
echo -e "You can manage the daemon status via: ${YELLOW}python3 src/daemon_manager.py status${RESET}"
