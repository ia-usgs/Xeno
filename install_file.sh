#!/bin/bash

# Colors for output
GREEN="\033[0;32m"
RED="\033[0;31m"
RESET="\033[0m"

echo -e "${GREEN}Starting dependency installation for Xeno (Non-Desktop)...${RESET}"

# Check if git is installed and install it if not
if ! command -v git &> /dev/null; then
    echo -e "${YELLOW}Git is not installed. Installing git...${RESET}"
    sudo apt-get update
    sudo apt-get install -y git
else
    echo -e "${GREEN}Git is already installed.${RESET}"
fi

# Check if pip is installed and install it if not
if ! command -v pip &> /dev/null; then
    echo -e "${YELLOW}Pip is not installed. Installing pip...${RESET}"
    sudo apt-get update
    sudo apt-get install -y python3-pip
else
    echo -e "${GREEN}Pip is already installed.${RESET}"
fi

# Step 1: Clone the Repository
echo -e "${GREEN}[1/7] Cloning the Xeno repository...${RESET}"

# Define repository URL and clone path
REPO_URL="https://github.com/ia-usgs/Xeno.git"
CLONE_DIR="/home/pi/xeno"

# Check if the directory exists
if [ -d "$CLONE_DIR" ]; then
    if [ -d "$CLONE_DIR/.git" ]; then
        # If it's a valid Git repository, pull the latest changes
        echo -e "${GREEN}Xeno repository already exists at $CLONE_DIR. Pulling the latest changes...${RESET}"
        git config --global --add safe.directory "$CLONE_DIR"
        cd "$CLONE_DIR" && git pull
    else
        # If the directory exists but is not a valid repository, delete and re-clone
        echo -e "${RED}$CLONE_DIR exists but is not a valid Git repository. Re-cloning...${RESET}"
        sudo rm -rf "$CLONE_DIR"
        git clone "$REPO_URL" "$CLONE_DIR"
    fi
else
    # If the directory doesn't exist, clone the repository
    echo -e "${GREEN}Cloning the repository into $CLONE_DIR...${RESET}"
    git clone "$REPO_URL" "$CLONE_DIR"
fi

# Set directory permissions to make it accessible to all users
sudo chmod -R 777 "$CLONE_DIR"

# Step 2: Update and Upgrade System
echo -e "${GREEN}[2/7] Updating and upgrading system...${RESET}"
sudo apt-get update && sudo apt-get upgrade -y

# Step 3: Install System Dependencies
echo -e "${GREEN}[3/7] Installing system dependencies...${RESET}"
sudo apt-get install -y python3 python3-pip python3-venv curl \
    nmcli smbclient libjpeg-dev libpng-dev nmap fbi

# Attempt to install searchsploit using the package manager
if ! sudo apt-get install -y exploitdb; then
    echo -e "${RED}[ERROR] Failed to install searchsploit via package manager. Attempting manual installation...${RESET}"

    # Manual installation of searchsploit from the new repository
    SEARCHSPLOIT_DIR="/usr/share/exploitdb"
    if [ ! -d "$SEARCHSPLOIT_DIR" ]; then
        echo -e "${GREEN}Cloning ExploitDB repository from GitLab...${RESET}"
        sudo git clone https://gitlab.com/exploit-database/exploitdb.git "$SEARCHSPLOIT_DIR"
    else
        echo -e "${GREEN}ExploitDB directory already exists. Pulling latest changes...${RESET}"
        sudo git -C "$SEARCHSPLOIT_DIR" pull
    fi

    # Create symlink for searchsploit
    echo -e "${GREEN}Creating symlink for searchsploit...${RESET}"
    sudo ln -sf "$SEARCHSPLOIT_DIR/searchsploit" /usr/local/bin/searchsploit

    # Ensure configuration file is linked
    echo -e "${GREEN}Linking .searchsploit_rc configuration...${RESET}"
    sudo ln -sf "$SEARCHSPLOIT_DIR/.searchsploit_rc" /root/.searchsploit_rc
    ln -sf "$SEARCHSPLOIT_DIR/.searchsploit_rc" ~/.searchsploit_rc

    # Verify searchsploit installation
    if command -v searchsploit &>/dev/null; then
        echo -e "${GREEN}searchsploit installed successfully.${RESET}"
    else
        echo -e "${RED}[ERROR] searchsploit installation failed. Please check manually.${RESET}"
    fi
else
    echo -e "${GREEN}searchsploit installed via package manager.${RESET}"
fi

# Step 4: Install Python Dependencies
echo -e "${GREEN}[4/7] Installing Python dependencies...${RESET}"
sudo pip3 install python-nmap pyexploitdb paramiko pysmb requests pygame pillow --break-system-packages

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

# Step 5: Redirect Console and Set Up Framebuffer
echo -e "${GREEN}[5/7] Configuring framebuffer and console output...${RESET}"

# Update /boot/cmdline.txt to redirect console output
sudo sed -i 's/$/ fbcon=map:0/' /boot/cmdline.txt

# Ensure framebuffer device is set for SDL applications
if ! grep -q "SDL_FBDEV" ~/.bashrc; then
    echo -e "${GREEN}Adding SDL framebuffer environment variables to .bashrc...${RESET}"
    echo "export SDL_FBDEV=/dev/fb1" >> ~/.bashrc
    echo "export SDL_VIDEODRIVER=fbcon" >> ~/.bashrc
fi

# Step 6: Create Xeno Service
echo -e "${GREEN}[6/7] Setting up Xeno service...${RESET}"

# Create a systemd service file for Xeno
SERVICE_FILE="/etc/systemd/system/xeno.service"

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Xeno Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 $CLONE_DIR/main.py
WorkingDirectory=$CLONE_DIR
StandardOutput=inherit
StandardError=inherit
Restart=always
User=pi
Group=pi
Environment="PYTHONUNBUFFERED=1"
Environment="HOME=/home/pi"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="SDL_FBDEV=/dev/fb1"
Environment="SDL_VIDEODRIVER=fbcon"

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
sudo systemctl enable xeno.service
sudo systemctl start xeno.service

# Step 7: Redirect Console and Set Up Framebuffer
echo -e "${GREEN}[5/7] Configuring framebuffer and console output...${RESET}"

# Update /boot/cmdline.txt to redirect console output
sudo sed -i 's/$/ fbcon=map:0/' /boot/cmdline.txt

# Ensure framebuffer device is set for SDL applications
if ! grep -q "SDL_FBDEV" ~/.bashrc; then
    echo -e "${GREEN}Adding SDL framebuffer environment variables to .bashrc...${RESET}"
    echo "export SDL_FBDEV=/dev/fb1" >> ~/.bashrc
    echo "export SDL_VIDEODRIVER=fbcon" >> ~/.bashrc
fi

# Add fbcp to /etc/rc.local for framebuffer mirroring
if ! grep -q "fbcp" /etc/rc.local; then
    echo -e "${GREEN}Adding fbcp to /etc/rc.local for framebuffer mirroring...${RESET}"
    sudo sed -i -e '$i fbcp &\n' /etc/rc.local
fi

# Add command to automatically run the Xeno script on login for CLI
if ! grep -q "/home/pi/xeno/main.py" ~/.bashrc; then
    echo -e "${GREEN}Adding auto-run for Xeno script to .bashrc...${RESET}"
    echo "python3 /home/pi/xeno/main.py" >> ~/.bashrc
fi

# Configure Auto-Login for Raspberry Pi
echo -e "${GREEN}[6.5/7] Configuring auto-login on boot...${RESET}"

AUTOLOGIN_CONFIG="/etc/systemd/system/getty@tty1.service.d/override.conf"

# Create or overwrite the override configuration to enable auto-login
sudo mkdir -p "$(dirname $AUTOLOGIN_CONFIG)"
sudo bash -c "cat > $AUTOLOGIN_CONFIG" <<EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin pi --noclear %I \$TERM
EOF

# Reload systemd to apply changes
sudo systemctl daemon-reload

# Ensure getty service restarts
sudo systemctl restart getty@tty1.service

echo -e "${GREEN}Auto-login configuration complete.${RESET}"

# Install and Configure LCD Driver
echo -e "${GREEN}[7/7] Installing and configuring LCD driver...${RESET}"

LCD_DRIVER_DIR="/home/pi/LCD-show"
LCD_DRIVER_REPO="https://github.com/goodtft/LCD-show.git"

# Check if the LCD driver installation script was already run
if [ -f "/usr/local/bin/fbcp" ] && grep -q "fbcon=map:0" /boot/cmdline.txt; then
    echo -e "${GREEN}LCD driver is already installed. Skipping installation...${RESET}"
else
    # Check if the LCD driver directory exists
    if [ ! -d "$LCD_DRIVER_DIR" ]; then
        echo -e "${GREEN}Cloning the LCD driver repository...${RESET}"
        git clone "$LCD_DRIVER_REPO" "$LCD_DRIVER_DIR"
    fi

    # Change to the LCD driver directory
    cd "$LCD_DRIVER_DIR"

    # Make the driver script executable
    sudo chmod +x LCD35-show

    # Run the installation script with non-interactive mode
    echo -e "${GREEN}Running the LCD driver installation script...${RESET}"
    yes | sudo ./LCD35-show

    # Install fbcp for framebuffer mirroring
    echo -e "${GREEN}Installing fbcp for framebuffer mirroring...${RESET}"
    sudo apt-get install -y cmake
    if [ ! -f /usr/local/bin/fbcp ]; then
        git clone https://github.com/tasanakorn/rpi-fbcp.git /home/pi/rpi-fbcp
        cd /home/pi/rpi-fbcp
        mkdir build && cd build
        cmake .. && make
        sudo install fbcp /usr/local/bin/
    fi
fi

# Final Message and Reboot
echo -e "${GREEN}LCD driver installation check complete. The system will now reboot to apply changes.${RESET}"
sudo reboot
