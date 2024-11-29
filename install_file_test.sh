#!/bin/bash

# Colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${GREEN}Starting dependency installation for Xeno...${RESET}"

# Step 1: Update and Upgrade System
echo -e "${GREEN}[1/5] Updating and upgrading system...${RESET}"
sudo apt-get update && sudo apt-get upgrade -y

# Step 2: Install System Dependencies
echo -e "${GREEN}[2/5] Installing system dependencies...${RESET}"
sudo apt-get install -y git python3 python3-pip python3-venv nmap curl searchsploit nmcli smbclient

# Verify if git is installed
if ! command -v git &>/dev/null; then
    echo -e "${RED}[ERROR] git is not installed. Please check your package manager.${RESET}"
    exit 1
else
    echo -e "${GREEN}git is installed.${RESET}"
fi

# Verify if pip is installed
if ! command -v pip3 &>/dev/null; then
    echo -e "${RED}[ERROR] pip3 is not installed. Installing pip3...${RESET}"
    sudo apt-get install -y python3-pip
else
    echo -e "${GREEN}pip3 is already installed.${RESET}"
fi

# Step 3: Install Python Dependencies
echo -e "${GREEN}[3/5] Installing Python dependencies...${RESET}"

# Create a virtual environment for Python (optional but recommended)
python3 -m venv xeno_env
source xeno_env/bin/activate

# Install required Python packages with --break-system-packages for sudo compatibility
sudo pip3 install paramiko pysmb requests --break-system-packages

# Step 4: Verify Installations
echo -e "${GREEN}[4/5] Verifying installations...${RESET}"

# Check for system tools
for tool in git nmap searchsploit nmcli; do
    if ! command -v $tool &>/dev/null; then
        echo -e "${RED}[ERROR] $tool is not installed correctly.${RESET}"
    else
        echo -e "${GREEN}$tool is installed.${RESET}"
    fi
done

# Check for Python libraries
python3 - <<EOF
try:
    import paramiko
    import smb.SMBConnection
    import requests
    print("${GREEN}All Python libraries installed correctly.${RESET}")
except ImportError as e:
    print("${RED}Missing Python library:${RESET}", e)
EOF

# Step 5: Final Message
echo -e "${GREEN}[5/5] All dependencies have been installed.${RESET}"
echo -e "${GREEN}You can now proceed with setting up Xeno!${RESET}"
