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
sudo chown -R pi:pi /home/pi/xeno/logs
sudo chown -R pi:pi /home/pi/xeno/utils

# Step 2: Update and Upgrade System
echo -e "${GREEN}[2/7] Updating and upgrading system...${RESET}"
sudo apt-get update && sudo apt-get upgrade -y

# Step 3: Install System Dependencies
echo -e "${GREEN}[3/7] Installing system dependencies...${RESET}"
sudo apt-get install -y git python3 python3-pip python3-venv curl dnsutils macchanger \
    smbclient libjpeg-dev libpng-dev nmap fbi network-manager

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
sudo pip3 install python-nmap pyexploitdb paramiko pysmb requests pygame pillow pandas shodan requests-futures colorama python-whois dnsrecon --break-system-packages

# Step 4.1: Manually Install Shodan
echo -e "${GREEN}[4.1] Installing Shodan manually...${RESET}"

# Clone Shodan from its repository (if applicable) or install using pip
if ! pip3 list | grep -q shodan; then
    echo -e "${GREEN}Installing Shodan package...${RESET}"
    sudo pip3 install shodan --break-system-packages
else
    echo -e "${GREEN}Shodan is already installed.${RESET}"
fi

# Step 4.2: Verify Shodan Installation
echo -e "${GREEN}[4.2] Verifying Shodan installation...${RESET}"
python3 - <<EOF
try:
    import shodan
    print("${GREEN}Shodan installed correctly.${RESET}")
except ImportError as e:
    print("${RED}Shodan installation failed. Please check manually.${RESET}", e)
EOF

# Step 4.3: Install and Configure theHarvester
echo -e "${GREEN}[4.3] Installing and configuring theHarvester...${RESET}"

# Define the directory for theHarvester
THE_HARVESTER_DIR="/home/pi/xeno/theHarvester"

# Remove any previous installation
if [ -d "$THE_HARVESTER_DIR" ]; then
    echo -e "${GREEN}Removing existing theHarvester directory...${RESET}"
    sudo rm -rf "$THE_HARVESTER_DIR"
fi

# Clone the theHarvester repository
echo -e "${GREEN}Cloning theHarvester repository...${RESET}"
git clone https://github.com/laramies/theHarvester.git "$THE_HARVESTER_DIR"

# Change to theHarvester directory
cd "$THE_HARVESTER_DIR"

# Install dependencies with --break-system-packages
echo -e "${GREEN}Installing theHarvester dependencies...${RESET}"
sudo pip3 install -r requirements/base.txt --break-system-packages

# Add an alias for theHarvester to make it accessible system-wide
if ! grep -q "alias theharvester=" ~/.bashrc; then
    echo "alias theharvester='python3 $THE_HARVESTER_DIR/theHarvester.py'" >> ~/.bashrc
    echo -e "${GREEN}Added alias for theHarvester to .bashrc.${RESET}"
fi

# Apply alias changes
source ~/.bashrc

# Verify theHarvester installation
echo -e "${GREEN}Verifying theHarvester installation...${RESET}"
python3 "$THE_HARVESTER_DIR/theHarvester.py" -h

# Test the alias
echo -e "${GREEN}Testing theHarvester alias...${RESET}"
theharvester -h

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

# Enable the service (do not start yet)
echo -e "${GREEN}Enabling Xeno service but not starting it yet.${RESET}"
sudo systemctl enable xeno.service

# Step 7: Redirect Console and Set Up Framebuffer
echo -e "${GREEN}[7/7] Installing and configuring LCD driver...${RESET}"

# Prompt for LCD Installation
echo -e "${GREEN}Do you want to install and configure the LCD screen? (y/n)${RESET}"
read -r install_lcd

if [[ "$install_lcd" =~ ^[Yy]$ ]]; then
    # Update /boot/cmdline.txt to redirect console output
    sudo sed -i 's/$/ fbcon=map:0/' /boot/cmdline.txt

    # Ensure framebuffer device is set for SDL applications
    if ! grep -q "SDL_FBDEV" ~/.bashrc; then
        echo -e "${GREEN}Adding SDL framebuffer environment variables to .bashrc...${RESET}"
        echo "export SDL_FBDEV=/dev/fb1" >> ~/.bashrc
        echo "export SDL_VIDEODRIVER=fbcon" >> ~/.bashrc
    fi

    # Install and Configure LCD Driver
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
else
    echo -e "${GREEN}Skipping LCD installation. Proceeding with other setup steps.${RESET}"
fi

# Step 8: Install e-Paper Display Drivers
echo -e "${GREEN}[8/8] Do you want to install and configure the e-Paper display drivers? (y/n)${RESET}"
read -r install_epaper

if [[ "$install_epaper" =~ ^[Yy]$ ]]; then
    echo -e "${GREEN}Installing and configuring e-Paper display drivers...${RESET}"

    # Enable SPI Interface
    sudo raspi-config nonint do_spi 0

    # Check /boot/config.txt for SPI enablement
    if ! grep -q "dtparam=spi=on" /boot/config.txt; then
        echo -e "${GREEN}Enabling SPI in /boot/config.txt...${RESET}"
        echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
    fi

    # Install lg library
    echo -e "${GREEN}Installing lg library...${RESET}"
    wget https://github.com/joan2937/lg/archive/master.zip
    unzip master.zip
    cd lg-master
    make
    sudo make install

    # Install gpiod library (optional)
    echo -e "${GREEN}Installing gpiod library...${RESET}"
    sudo apt-get update
    sudo apt-get install -y gpiod libgpiod-dev

    # Install BCM2835 library
    echo -e "${GREEN}Installing BCM2835 library...${RESET}"
    wget http://www.airspayce.com/mikem/bcm2835/bcm2835-1.71.tar.gz
    tar zxvf bcm2835-1.71.tar.gz
    cd bcm2835-1.71/
    sudo ./configure && sudo make && sudo make check && sudo make install

    # Install WiringPi
    echo -e "${GREEN}Installing WiringPi...${RESET}"
    git clone https://github.com/WiringPi/WiringPi
    cd WiringPi
    ./build
    gpio -v
else
    echo -e "${GREEN}Skipping e-Paper installation. Proceeding with other setup steps.${RESET}"
fi

