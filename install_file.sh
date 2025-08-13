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

# Step 1: Clone or Update the Repository (preserving config, logs, and Xeno state)
echo -e "${GREEN}[1/7] Cloning or updating the Xeno repository...${RESET}"

# Define repository URL and clone path
REPO_URL="https://github.com/ia-usgs/Xeno.git"
CLONE_DIR="/home/pi/xeno"

# Backup settings
BACKUP_DIR="$HOME/xeno_backup_$(date +%s)"
PRESERVE_ITEMS=("config" "logs" "utils/html_logs" "utils/json_logs" "state.json")

# 1a) Backup existing items if repo already exists
if [ -d "$CLONE_DIR" ]; then
    mkdir -p "$BACKUP_DIR"
    for item in "${PRESERVE_ITEMS[@]}"; do
        if [ -e "$CLONE_DIR/$item" ]; then
            cp -a "$CLONE_DIR/$item" "$BACKUP_DIR/"
            echo -e "${GREEN}Backed up $item → $BACKUP_DIR/${RESET}"
        fi
    done
fi

cd "$HOME" || exit 1

# 1b) Update or clone the repo
if [ -d "$CLONE_DIR/.git" ]; then
    echo -e "${GREEN}Existing Git repository found. Cleaning and pulling latest changes...${RESET}"
    cd "$CLONE_DIR"
    git reset --hard HEAD
    git clean -fd
    git pull origin main || echo -e "${RED}Git pull failed. Continuing with existing version...${RESET}"
elif [ -d "$CLONE_DIR" ]; then
    echo -e "${RED}$CLONE_DIR exists but is not a Git repository. Removing and cloning...${RESET}"
    sudo rm -rf "$CLONE_DIR"
    git clone "$REPO_URL" "$CLONE_DIR"
else
    echo -e "${GREEN}Cloning repository into $CLONE_DIR...${RESET}"
    git clone "$REPO_URL" "$CLONE_DIR"
fi

# 1c) Restore preserved items
for item in "${PRESERVE_ITEMS[@]}"; do
    base="$(basename "$item")"
    dir="$(dirname "$item")"
    if [ -e "$BACKUP_DIR/$base" ]; then
        mkdir -p "$CLONE_DIR/$dir"
        cp -a "$BACKUP_DIR/$base" "$CLONE_DIR/$dir/"
        echo -e "${GREEN}Restored $item from backup.${RESET}"
    fi
done

# Set directory permissions
sudo chmod -R 777 "$CLONE_DIR"
sudo chown -R pi:pi "$CLONE_DIR"


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
        echo -e "${GREEN}Cloning ExploitDB repository from GitLab (shallow)...${RESET}"
        sudo git clone --depth 1 https://gitlab.com/exploit-database/exploitdb.git "$SEARCHSPLOIT_DIR"
    else
        echo -e "${GREEN}ExploitDB directory already exists. Pulling latest changes...${RESET}"
        sudo git -C "$SEARCHSPLOIT_DIR" pull --depth 1
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
sudo pip3 install python-nmap pyexploitdb paramiko pysmb requests pygame pillow shodan requests-futures colorama python-whois dnsrecon flask --break-system-packages

# Step 4.1: Special check for paramiko (with system dependencies if missing)
echo -e "${GREEN}[4.0.1] Verifying paramiko installation...${RESET}"
python3 -c "import paramiko" 2>/dev/null

if [ $? -ne 0 ]; then
    echo -e "${RED}Paramiko not installed. Installing system dependencies and retrying...${RESET}"
    sudo apt-get update && sudo apt-get install -y libssl-dev libffi-dev build-essential pkg-config
    sudo pip3 install paramiko --break-system-packages
else
    echo -e "${GREEN}Paramiko is installed successfully.${RESET}"
fi

# Step 4.2: Reattempt failed installs for other modules
declare -A modules=(
    ["nmap"]="python-nmap"
    ["pyexploitdb"]="pyexploitdb"
    ["smb.SMBConnection"]="pysmb"
    ["requests"]="requests"
    ["pygame"]="pygame"
    ["PIL"]="pillow"
    #["shodan"]="shodan"
    ["requests_futures"]="requests-futures"
    ["colorama"]="colorama"
    ["whois"]="python-whois"
    ["dnsrecon"]="dnsrecon"
    ["flask"]="flask"
)

for import_path in "${!modules[@]}"; do
    # Skip paramiko since it's already handled
    if [ "$import_path" == "paramiko" ]; then continue; fi

    echo -e "${GREEN}Verifying ${modules[$import_path]}...${RESET}"
    python3 -c "import $import_path" 2>/dev/null

    if [ $? -ne 0 ]; then
        echo -e "${RED}${modules[$import_path]} missing. Reinstalling...${RESET}"
        sudo pip3 install "${modules[$import_path]}" --break-system-packages
    else
        echo -e "${GREEN}${modules[$import_path]} is installed.${RESET}"
    fi
done
# Step 4.1: Manually Install Shodan
#echo -e "${GREEN}[4.1] Installing Shodan manually...${RESET}"

# Clone Shodan from its repository (if applicable) or install using pip
#if ! pip3 list | grep -q shodan; then
#    echo -e "${GREEN}Installing Shodan package...${RESET}"
#    sudo pip3 install shodan --break-system-packages
#else
#    echo -e "${GREEN}Shodan is already installed.${RESET}"
#fi

# Step 4.2: Verify Shodan Installation
#echo -e "${GREEN}[4.2] Verifying Shodan installation...${RESET}"
#python3 - <<EOF
#try:
#    import shodan
#    print("${GREEN}Shodan installed correctly.${RESET}")
#except ImportError as e:
#    print("${RED}Shodan installation failed. Please check manually.${RESET}", e)
#EOF

# Step 4.3: Install and Configure theHarvester
#echo -e "${GREEN}[4.3] Installing and configuring theHarvester...${RESET}"

# Define the directory for theHarvester
#THE_HARVESTER_DIR="/home/pi/xeno/theHarvester"

# Remove any previous installation
#if [ -d "$THE_HARVESTER_DIR" ]; then
#    echo -e "${GREEN}Removing existing theHarvester directory...${RESET}"
#    sudo rm -rf "$THE_HARVESTER_DIR"
#fi

# Clone the theHarvester repository
#echo -e "${GREEN}Cloning theHarvester repository...${RESET}"
#git clone https://github.com/laramies/theHarvester.git "$THE_HARVESTER_DIR"

# Change to theHarvester directory
#cd "$THE_HARVESTER_DIR"

# Install dependencies with --break-system-packages
#echo -e "${GREEN}Installing theHarvester dependencies...${RESET}"
#sudo pip3 install -r requirements/base.txt --break-system-packages

# Add an alias for theHarvester to make it accessible system-wide
#if ! grep -q "alias theharvester=" ~/.bashrc; then
#    echo "alias theharvester='python3 $THE_HARVESTER_DIR/theHarvester.py'" >> ~/.bashrc
#    echo -e "${GREEN}Added alias for theHarvester to .bashrc.${RESET}"
#fi

# Apply alias changes
#source ~/.bashrc

# Verify theHarvester installation
#echo -e "${GREEN}Verifying theHarvester installation...${RESET}"
#python3 "$THE_HARVESTER_DIR/theHarvester.py" -h

# Test the alias
#echo -e "${GREEN}Testing theHarvester alias...${RESET}"
#theharvester -h

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

# Conditionally set up the web server if Xeno service was enabled successfully
if systemctl list-unit-files | grep -q 'xeno.service'; then
    echo -e "${GREEN}Xeno service exists. Setting up web server...${RESET}"
else
    echo -e "${YELLOW}Xeno service not detected. Attempting to create and enable it again...${RESET}"
    sudo systemctl enable xeno.service
    sudo systemctl daemon-reexec
    sudo systemctl daemon-reload
fi

# Re-check and proceed if xeno.service is now available
if systemctl list-unit-files | grep -q 'xeno.service'; then
    echo -e "${GREEN}Setting up xeno-web.service...${RESET}"

    sudo bash -c "cat > /etc/systemd/system/xeno-web.service" <<EOF
[Unit]
Description=Xeno Web Server
After=network.target xeno.service
Requires=xeno.service

[Service]
ExecStart=/usr/bin/python3 $CLONE_DIR/web_server.py
WorkingDirectory=$CLONE_DIR
Restart=always
User=pi
Environment="PYTHONUNBUFFERED=1"

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reexec
    sudo systemctl daemon-reload
    sudo systemctl enable xeno-web.service

    echo -e "${GREEN}Web server configured to launch with Xeno.${RESET}"
else
    echo -e "${RED}Xeno service still not found. Web server setup skipped.${RESET}"
fi

# Check if WiFi module is enabled and enable it if it's not
echo -e "${GREEN}[Checking WiFi Module Status]${RESET}"
WIFI_STATUS=$(nmcli radio wifi)

if [ "$WIFI_STATUS" = "disabled" ]; then
    echo -e "${YELLOW}WiFi module is disabled. Enabling WiFi module...${RESET}"
    sudo nmcli radio wifi on
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}WiFi module has been successfully enabled.${RESET}"
    else
        echo -e "${RED}[ERROR] Failed to enable WiFi module. Please check manually.${RESET}"
        exit 1
    fi
else
    echo -e "${GREEN}WiFi module is already enabled.${RESET}"
fi

# Check and remove the unwanted /Xeno directory
if [ -d "/home/pi/Xeno" ]; then
    echo -e "${RED}Directory /home/pi/Xeno exists but is not needed. Deleting it...${RESET}"
    sudo rm -rf "/home/pi/Xeno"
fi

# Install e-Paper Display Drivers
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
unzip -o master.zip
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

echo -e "${GREEN}e-Paper display driver installation complete!${RESET}"

# Prompt user for a custom pet name
echo -e "${GREEN}Set up your custom pet name (default: Xeno): ${RESET}"
read -p "Enter your pet name: " pet_name

# If the user presses Enter without typing a name, set default
if [ -z "$pet_name" ]; then
    pet_name="Xeno"  # Default pet name
fi

echo -e "${GREEN}Pet name set to: $pet_name${RESET}"

# Define state file path
STATE_FILE="/home/pi/xeno/state.json"

# Create or update the state.json file
if [ ! -f "$STATE_FILE" ]; then
    echo -e "${GREEN}Creating state.json file...${RESET}"
    cat <<EOF > "$STATE_FILE"
{
    "level": 1,
    "start_date": "$(date +%Y-%m-%d)",
    "pet_name": "$pet_name"
}
EOF
    echo -e "${GREEN}State file initialized with pet name.${RESET}"
else
    echo -e "${GREEN}Updating existing state.json with pet name...${RESET}"
    if jq '.pet_name' "$STATE_FILE" &> /dev/null; then
        jq --arg pet_name "$pet_name" '.pet_name = $pet_name' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    else
        jq --arg pet_name "$pet_name" '. + {pet_name: $pet_name}' "$STATE_FILE" > "${STATE_FILE}.tmp" && mv "${STATE_FILE}.tmp" "$STATE_FILE"
    fi
    echo -e "${GREEN}Pet name updated in state.json.${RESET}"
fi

XENO_DIR="/home/pi/xeno"

# Ensure everything is owned by pi:pi
chown -R pi:pi "$XENO_DIR"
sudo chmod -R 777 "$XENO_DIR"

# Just in case we missed something in the beginning yk?
echo -e "${GREEN}Permissions set for pi:pi under $XENO_DIR.${RESET}"

