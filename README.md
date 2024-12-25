
# **Xeno: Wi-Fi Companion**
<div align="center">
  <img src="xeno.png" alt="Xeno Interface" width="250">
</div>

A Python-based tool for scanning, auditing, and performing penetration tests on Wi-Fi networks and connected devices. This project automates network scanning, reconnaissance, and security testing using custom scripts and external tools.
The purpose of this tool is to teach you what weaknesses there are within your own network and for you to harden that network in order to better defend and protect it.

Join the Reddit community: [Reddit link](https://www.reddit.com/r/xenowificompanion/s/Yu8tJWnRLq)

Follow on YouTube: [YouTube Link](https://www.youtube.com/@xenowificompanion)

For love and support: [Buy Me a Coffee](https://buymeacoffee.com/xenowificompanion)

---

## **Features**

- **Wi-Fi Scanning and Connection Management**
  - Automatically connects to Wi-Fi networks based on provided credentials (`config/wifi_credentials.json`).
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
  - Logs scan and attack results in both JSON (`utils/json_logs`) and HTML (`utils/html_logs`) formats for detailed review.

- **Dynamic E-Paper Display Updates or LCD screen to see CLI updates**
  - Displays workflow progress and stats on an e-paper display using custom images (`images/`).
  - On LCD display, see output in more detail than a cute lil' Xeno.

---

## **Parts List**
  - Raspberry Pi (Recommended: Raspberry Pi 5, 4, 3B+, 0W)
  - MicroSD Card (Minimum: 16GB)
  - Wi-Fi Adapter (Optional but Recommended)
  - Power Supply or Battery bank for portable (5V, 3A Recommended)
  - 3.5-inch LCD Touchscreen (Optional)
  - waveshare 2.13inch E-Ink Display HAT V4 (Optional)

---

## **Installation**

### **Automatic Installation (Recommended)**

Be sure to use the non desktop 64 bit version!!!!

You can only select ONE driver to use, either LCD Display or E-Ink display! If you use both, the second one selected won't work.

1. Clone the repository and run the installation script:
   ```bash
   git clone https://github.com/ia-usgs/Xeno.git
   cd Xeno
   sudo chmod 777 install_file.sh
   sudo ./install_file.sh
   ```

2. The script will:
   - Install all dependencies (Python libraries, tools like `nmap`, and e-paper display drivers).
   - Clone required repositories (e.g., ExploitDB).
   - Configure services and environment variables for the Xeno project.
   - Set up logging directories (`logs/`, `utils/json_logs`, `utils/html_logs`).
   - Optionally set up a 3.5-inch LCD or e-paper display.
   - It will install theharvester and shodan, it is for a future update.

3. Follow any on-screen prompts during the installation process.

---

### **Manual Installation**

#### **1. Clone the Repository**

```bash
git clone https://github.com/ia-usgs/Xeno.git
cd Xeno
```

#### **2. Install Dependencies**

Install required system and Python dependencies:

```bash
sudo apt-get update && sudo apt-get install -y git python3 python3-pip python3-venv curl     dnsutils macchanger smbclient libjpeg-dev libpng-dev nmap fbi network-manager

sudo pip3 install -r requirements.txt --break-system-packages
```

#### **3. Set Up Configuration Files**

- **Wi-Fi Credentials**: Create a file at `config/wifi_credentials.json` with the following structure:
  ```json
  [
      {"SSID": "NetworkName", "Password": "NetworkPassword"},
      {"SSID": "AnotherNetwork", "Password": "AnotherPassword"}
  ]
  ```

- **SSH Credentials**: Create a file at `config/ssh_default_credentials.txt` with the following format:
  ```plaintext
  username:password
  anotheruser:anotherpassword
  ```

- **Password List**: Add any custom password lists for brute-force attempts in `config/password_list.txt`.

#### **4. Configure e-Paper Display (Optional)**

If using an e-paper display, ensure SPI is enabled:
```bash
sudo raspi-config nonint do_spi 0
```
---
#### **4.1 Configure LCD display (Optional)**

If using LCD display:
```
sudo rm -rf LCD-show 
git clone https://github.com/goodtft/LCD-show.git 
chmod -R 755 LCD-show 
cd LCD-show/
sudo ./LCD35-show 
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
  - **Scan Logs**: `logs/scan.log`
  - **JSON Logs**: `utils/json_logs/`
  - **HTML Logs**: `utils/html_logs/`

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
- Add Wi-Fi networks in `config/wifi_credentials.json`.
- Set default SSH credentials in `config/ssh_default_credentials.txt`.
- Include a password list in `config/password_list.txt`.

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
  - `utils/json_logs/`
  - `utils/html_logs/`

### **4. Customize**
- Add new attack modules in the `attacks/` directory.
- Modify workflows in `main.py`.

---

### Contributions

This project is open for contributions! Feel free to fork the repository and submit pull requests. Contact me on Reddit for discussions and suggestions.

---

### **Disclaimer**

This project is intended for **educational and ethical penetration testing** only. Unauthorized use on networks or devices without permission is illegal and punishable by law.

**Use responsibly.**

---

