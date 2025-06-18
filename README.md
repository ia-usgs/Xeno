
# **Xeno: Wi-Fi Companion**
<div align="center">
  <img src="xeno.png" alt="Xeno Interface" width="250">
</div>

A Python-based tool for scanning, auditing, and performing penetration tests on Wi-Fi networks and connected devices. This project automates network scanning, reconnaissance, and security testing using custom scripts and external tools.
The purpose of this tool is to teach you what weaknesses there are within your own network and for you to harden that network in order to better defend and protect it.

<p align="center">
  <img src="https://github.com/user-attachments/assets/60a09adc-5b39-44c4-82f6-1dbfa2e64a54" alt="image" />
</p>


<div align="center">
  <p>
    Join the Reddit community: <a href="https://www.reddit.com/r/xenowificompanion/s/Yu8tJWnRLq">Reddit</a>
  </p>
  <p>
    Follow on YouTube: <a href="https://www.youtube.com/@xenowificompanion">YouTube</a>
  </p>
  <p>
    Join on Discord: <a href="https://discord.gg/RnSjNAPZ">Discord</a>
  </p>
  <p>
    For love and support: <a href="https://buymeacoffee.com/xenowificompanion">Buy Me a Coffee</a>
  </p>
</div>

---

## **Features**

- **Wi-Fi Scanning and Connection Management**
  - Automatically connects to Wi-Fi networks based on provided credentials (`/home/pi/xeno/config/wifi_credentials.json`).
  - Scans nearby networks and retries connections if necessary.
  - Supports automatic MAC address randomization.

- **Network Scanning and Enumeration**
  - Uses `nmap` to discover devices on the network.
  - Collects information on open ports, services, and possible vulnerabilities.

- **Automated Reconnaissance**
  - Identifies operating systems and running services on discovered devices.
  - Performs detailed port scanning and OS fingerprinting.

- **Exploit Testing**
  - Uses `searchsploit` to identify and test exploits against discovered vulnerabilities.
  - Supports downloading and executing payloads for penetration testing.

- **File Harvesting**
  - Uses SSH, FTP, and SMB to retrieve sensitive files from target devices.
  - Dynamically targets OS-specific directories and file types.

- **HTML and JSON Logging**
  - Logs scan and attack results in both JSON (`/home/pi/xeno/utils/json_logs`) and HTML (`/home/pi/xeno/utils/html_logs`) formats for detailed review.

- **Dynamic E-Paper Display Updates**
  - Displays workflow progress and stats on an e-paper display using custom images (`/home/pi/xeno/images`).

---

## **Parts List**
  - Raspberry Pi (Recommended: Raspberry Pi 5, 4, 3B+, 0W)
  - MicroSD Card (Minimum: 16GB)
  - Wi-Fi Adapter (Optional but Recommended)
  - Power Supply or Battery bank for portable (5V, 3A Recommended)
  - waveshare 2.13inch E-Ink Display HAT V4

---

## **Installation**


---

## Using the Community Image

If you are using the official **Xeno Community Image** (pre-installed with everything), most components are already configured — including the default pet name: `"Xeno"`.

### What’s Already Set Up

- All Python dependencies, tools, and services.
- `state.json` initialized with default values.
- e-Paper display drivers installed.
- Systemd service for Xeno is enabled.

---

### Changing the Pet Name (Optional)

To personalize your Xeno’s identity:

1. Open the state file:
   ```bash
   sudo nano /home/pi/xeno/state.json
   ```

2. Locate the line:
   ```json
   "pet_name": "Xeno"
   ```

3. Change `"Xeno"` to your preferred name:
   ```json
   "pet_name": "CyberDog"
   ```

4. Save and exit:
   - Press `CTRL + X`
   - Then press `Y`
   - Then press `Enter`

---

### Recommended Next Steps

After booting for the first time:

- **Connect to Wi-Fi**:
  Edit your networks in `/home/pi/xeno/config/wifi_credentials.json`.

- **Customize Password Lists**:
  Add your own to `/home/pi/xeno/config/password_list.txt`.

- **Start Xeno Manually (only if you stopped the xeno service)** (optional):
  ```bash
  sudo python3 /home/pi/xeno/main.py
  ```

- **Or View Logs**:
  ```bash
  sudo journalctl -u xeno.service -f
  ```

---


### **Automatic Installation (Recommended)**

Be sure to use the Raspberry Pi OS lite 64 bit version!!!! (Unless RPi0)

1. Be sure to have your settings set this way:

![image](https://github.com/user-attachments/assets/20de68d8-5bea-4e16-85ad-9a4449127d37)

2. Clone the repository and run the installation script:
   ```bash
   git clone https://github.com/ia-usgs/Xeno.git
   cd Xeno
   sudo chmod 777 install_file.sh
   sudo ./install_file.sh
   ```
   If you don't have git do the following:
   ```
    sudo apt update --fix-missing
    sudo apt install git -y
   ```

3. The script will:
   - Install all dependencies (Python libraries, tools like `nmap`, and e-paper display drivers).
   - Clone required repositories (e.g., ExploitDB).
   - Configure services and environment variables for the Xeno project.
   - Set up logging directories (`logs/`, `utils/json_logs`, `utils/html_logs`).
   - Set up the e-paper display.
   - It will install theharvester and shodan, it is for a future update.

4. Follow any on-screen prompts during the installation process.

---

### **Manual Installation**

Be sure to have your settings set this way:

![image](https://github.com/user-attachments/assets/20de68d8-5bea-4e16-85ad-9a4449127d37)


#### **1. Clone the Repository**

```bash
git clone https://github.com/ia-usgs/Xeno.git
cd Xeno
```

#### **2. Install Dependencies**

Install required system and Python dependencies:

```bash
sudo apt-get update && sudo apt-get install -y git python3 python3-pip python3-venv curl dnsutils macchanger smbclient libjpeg-dev libpng-dev nmap fbi network-manager

sudo pip3 install -r requirements.txt --break-system-packages
```

#### **3. Set Up Configuration Files**

- **Wi-Fi Credentials**: Create a file at `/home/pi/xeno/config/wifi_credentials.json` with the following structure:
  ```json
  [
      {"SSID": "NetworkName", "Password": "NetworkPassword"},
      {"SSID": "AnotherNetwork", "Password": "AnotherPassword"}
  ]
  ```

- **SSH Credentials**: Create a file at `/home/pi/xeno/config/ssh_default_credentials.txt` with the following format:
  ```plaintext
  username:password
  anotheruser:anotherpassword
  ```

- **Password List**: Add any custom password lists for brute-force attempts in `/home/pi/xeno/config/password_list.txt`.

#### **4. Configure e-Paper Display**

Ensure SPI is enabled:
```bash
sudo raspi-config nonint do_spi 0
```
---

## **Usage**

### **1. Run the Script Manually**

```bash
sudo python3 main.py
```

### **2. Deploy as a System Service**

To run the script continuously on system startup:

1. Create a service file at `/etc/systemd/system/xeno.service`:
   ```plaintext
   [Unit]
   Description=Xeno Wi-Fi Companion Service
   After=network.target

   [Service]
   ExecStart=/usr/bin/python3 /home/pi/xeno/main.py
   WorkingDirectory=/home/pi/xeno
   Restart=always
   User=pi
   Group=pi
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
   ```

2. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable xeno.service
   sudo systemctl start xeno.service
   ```

---

## **Monitoring and Logs**

- **View live service logs:**
  ```bash
  sudo journalctl -u xeno.service -f
  ```

- **Log directories:**
  - **Scan Logs**: `/home/pi/xeno/logs/scan.log`
  - **JSON Logs**: `/home/pi/xeno/utils/json_logs/`
  - **HTML Logs**: `/home/pi/xeno/utils/html_logs/`

---

## **Directory Structure**

```plaintext
.
├── attacks/
│   ├── exploit_tester.py       # Exploit testing module
│   ├── file_stealer.py         # File stealing module
│   ├── recon.py                # Reconnaissance module
│   └── vulnerability_scan.py   # Vulnerability scanning module
├── config/
│   ├── password_list.txt       # Password list for brute-forcing
│   ├── ssh_default_credentials.txt # Default SSH credentials
│   └── wifi_credentials.json   # Wi-Fi credentials
├── images/                     # Workflow state images
├── logs/                       # Log directory
├── scans/
│   └── nmap_scanner.py         # Nmap scanning module
├── stolen_files/               # Directory for stolen files
├── utils/
│   ├── display.py              # E-paper display manager
│   ├── html_logger.py          # HTML log generator
│   ├── image_state_manager.py  # Workflow state manager
│   ├── logger.py               # Logging utility
│   ├── html_logs/              # HTML log directory
│   └── json_logs/              # JSON log directory
├── wifi/
│   └── wifi_manager.py         # Wi-Fi connection manager
├── install_file.sh             # Installation script
├── main.py                     # Main script entry point
└── README.md                   # This file
```

---

## **Step-by-Step Workflow**

### **1. Prepare Configuration Files**
- Add Wi-Fi networks in `/home/pi/xeno/config/wifi_credentials.json`.
- Set default SSH credentials in `/home/pi/xeno/config/ssh_default_credentials.txt`.
- Include a password list in `/home/pi/xeno/config/password_list.txt`.

### **2. Run the Script**
- **Manually**:
  ```bash
  sudo python3 main.py
  ```
- **As a service**:
  Follow the "Service Mode" instructions above.

### **3. Monitor Logs**
- View service logs:
  ```bash
  sudo journalctl -u xeno.service -f
  ```
- Review reports in:
  - `/home/pi/xeno/utils/json_logs/`
  - `/home/pi/xeno/utils/html_logs/`

### **4. Customize**
- Add new attack modules in the `/home/pi/xeno/attacks` directory.
- Modify workflows in `main.py`.

---

## **Debugging**
- If you get `GPIO Busy` while running manually in CLI it is because the service is running.
- Run `sudo systemctl stop xeno.service` the from `/xeno` directory run `sudo python main.py`
- Check logs at `xeno/logs/scan.log`
- If Xeno is not getting anything via scans, it could be that it is taking longer than 60 seconds.
- To increase timeout go to `/xeno/attacks/recon.py` and modify line 42 `def scan_ports(self, target, timeout=60):` and change from 60 seconds to desired amount.
- If any part of xeno is having permission issues, do `sudo chown root:pi filename` and then `sudo chmod 770 filename`

### Contributions

This project is open for contributions! Feel free to fork the repository and submit pull requests. Contact me on Reddit for discussions and suggestions.

---

### **Disclaimer**

This project is intended for **educational and ethical penetration testing** only. Unauthorized use on networks or devices is illegal and punishable by law.

**Use responsibly.**

---

