#!/bin/bash
set -e

APP_NAME="ov-node"
INSTALL_DIR="/opt/$APP_NAME"
VENV_DIR="/opt/${APP_NAME}_venv"
REPO_URL="https://github.com/primeZdev/ov-node"
PYTHON="/usr/bin/python3"

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

echo -e "${YELLOW}Updating system...${NC}"
apt update -y
apt install -y python3 python3-venv python3-full wget curl git

python3 -m venv "$VENV_DIR"

source "$VENV_DIR/bin/activate"

pip install --upgrade pip setuptools wheel

echo -e "${YELLOW}Installing dependencies in venv...${NC}"
pip install colorama pexpect requests uuid uv

# Download repo release
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Downloading latest release...${NC}"

    LATEST_URL=$(curl -s https://api.github.com/repos/primeZdev/ov-node/releases/latest \
        | grep "tarball_url" \
        | cut -d '"' -f 4)

    mkdir -p "$INSTALL_DIR"
    cd /tmp

    wget -O latest.tar.gz "$LATEST_URL"

    echo -e "${YELLOW}Extracting...${NC}"
    tar -xzf latest.tar.gz -C "$INSTALL_DIR" --strip-components=1
    rm -f latest.tar.gz
else
    echo -e "${GREEN}Directory exists, skipping download.${NC}"
fi

echo -e "${YELLOW}Running installer...${NC}"
cd "$INSTALL_DIR"
$VENV_DIR/bin/python installer.py

echo -e "${GREEN}Installation completed successfully!${NC}"
