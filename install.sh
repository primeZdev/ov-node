#!/bin/bash
set -e

APP_NAME="ov-node"
INSTALL_DIR="/opt/$APP_NAME"
REPO_URL="https://github.com/VPNOS/ov-panel"
PYTHON="/usr/bin/python3"
VENV_DIR="$INSTALL_DIR/venv"

GREEN="\033[0;32m"
YELLOW="\033[1;33m"
NC="\033[0m"

apt update -y
apt install -y python3 python3-pip python3-venv wget curl git -y

if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${YELLOW}Cloning repository...${NC}"
    git clone "$REPO_URL" "$INSTALL_DIR"
else
    echo -e "${GREEN}Directory exists, removing before cloning...${NC}"
    rm -rf "$INSTALL_DIR"
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

echo -e "${YELLOW}Creating Python virtual environment...${NC}"
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
fi

echo -e "${YELLOW}Installing dependencies in virtual environment...${NC}"
"$VENV_DIR/bin/pip" install --upgrade pip

if [ -f "$INSTALL_DIR/requirements.txt" ]; then
    "$VENV_DIR/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
else
    echo -e "${YELLOW}requirements.txt not found, installing basic dependencies...${NC}"
    "$VENV_DIR/bin/pip" install fastapi uvicorn psutil pydantic_settings python-dotenv colorama pexpect requests
fi

echo -e "${YELLOW}Running installer...${NC}"
"$VENV_DIR/bin/python" installer.py
