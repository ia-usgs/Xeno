#!/bin/bash

# Colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${GREEN}Starting dependency installation for Xeno...${RESET}"

# Step 1: Update and Upgrade System
echo -e "${GREEN}[1/6] Updating and upgrading system...${RESET}"
sudo apt-get update && sudo apt-get upgrade -y

# Step 2: Install System Dependencies
echo -e "${GREEN}[2/6] Installing system dependencies...${RESET}"
sudo apt-get install -y git python3 python3-pip python3-venv nmap curl searchsploit \
    nmcli smbclient fbi fontconfig xserver-xorg x11-xserver-utils xinit openbox \
    libjpeg-dev libpng-dev

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
echo -e "${GREEN}[3/6] Installing Python dependencies...${RESET}"

# Install required Python packages with --break-system-packages for sudo compatibility
sudo pip3 install paramiko pysmb requests pygame pillow --break-system-packages

# Verify Python libraries
python3 - <<EOF
try:
    import paramiko
    import smb.SMBConnection
    import requests
    import pygame
    import PIL
    print("${GREEN}All Python libraries installed correctly.${RESET}")
except ImportError as e:
    print("${RED}Missing Python library:${RESET}", e)
EOF

# Step 4: Configure Desktop Environment
echo -e "${GREEN}[4/6] Configuring desktop environment...${RESET}"

# Create a minimal .xinitrc file to start Openbox
if [ ! -f ~/.xinitrc ]; then
    echo -e "${GREEN}Creating .xinitrc file for Openbox...${RESET}"
    echo "exec openbox" > ~/.xinitrc
else
    echo -e "${GREEN}.xinitrc file already exists.${RESET}"
fi

# Enable the X server to start automatically on boot (optional)
if ! grep -q "startx" ~/.bashrc; then
    echo -e "${GREEN}Adding startx to .bashrc for auto-launch...${RESET}"
    echo "startx" >> ~/.bashrc
fi

# Step 5: Redirect Console and Set Up Framebuffer
echo -e "${GREEN}[5/6] Configuring framebuffer and console output...${RESET}"

# Update /boot/cmdline.txt to redirect console output
sudo sed -i 's/$/ fbcon=map:0/' /boot/cmdline.txt

# Ensure framebuffer device is set for SDL applications
if ! grep -q "SDL_FBDEV" ~/.bashrc; then
    echo -e "${GREEN}Adding SDL framebuffer environment variables to .bashrc...${RESET}"
    echo "export SDL_FBDEV=/dev/fb1" >> ~/.bashrc
    echo "export SDL_VIDEODRIVER=fbcon" >> ~/.bashrc
fi

# Step 6: Verify Installations
echo -e "${GREEN}[6/6] Verifying installations...${RESET}"

# Check for system tools
for tool in git nmap searchsploit nmcli fbi; do
    if ! command -v $tool &>/dev/null; then
        echo -e "${RED}[ERROR] $tool is not installed correctly.${RESET}"
    else
        echo -e "${GREEN}$tool is installed.${RESET}"
    fi
done

# Verify framebuffer
if [ -e /dev/fb1 ]; then
    echo -e "${GREEN}Framebuffer device /dev/fb1 detected.${RESET}"
else
    echo -e "${RED}[ERROR] Framebuffer device /dev/fb1 not found. Check your LCD driver installation.${RESET}"
fi

# Final Message
echo -e "${GREEN}All dependencies have been installed.${RESET}"
echo -e "${GREEN}You can now proceed with setting up Xeno!${RESET}"
echo -e "${GREEN}If using a desktop environment, reboot your system to apply changes.${RESET}"
