
# **Xeno: Wi-Fi Companion**
<div align="center">
  <img src="xeno.png" alt="Xeno Interface" width="250">
</div>


A Python-based tool for scanning, auditing, and performing penetration tests on Wi-Fi networks and connected devices. This project automates network scanning, reconnaissance, and security testing using custom scripts and external tools.

reddit link: https://www.reddit.com/r/xenowificompanion/s/Yu8tJWnRLq

If you wanna buy me a coffee: https://buymeacoffee.com/xenowificompanion

---

## **Features**

- **Wi-Fi Scanning and Connection Management**
  - Automatically connects to Wi-Fi networks based on provided credentials.
  - Supports retry attempts and logging for troubleshooting.
  - Scans nearby networks and attempts to connect.

- **Network Scanning and Enumeration**
  - Uses `nmap` to identify devices on the network.
  - Discovers open ports, services, and possible vulnerabilities.

- **Automated Reconnaissance**
  - Runs OS detection and service fingerprinting.
  - Collects detailed information about connected devices.

- **Exploit Testing**
  - Attempts to exploit discovered vulnerabilities.
  - Supports customized payloads for penetration testing.

- **File Harvesting**
  - Uses SSH credentials to retrieve sensitive files from target devices.
  - Can specify file extensions and directories for targeted searches.

- **HTML and JSON Logging**
  - Logs scan and attack results in both JSON and HTML formats for easy review.
  - Generates detailed, structured reports of scan results.

---
## **Parts list**
  - Raspberry Pi (Recommended: Raspberry Pi 5, 4, 3B+, zero w, zero w2)
  - MicroSD Card (Minimum: 16GB)
  - Wi-Fi Adapter (Optional)
  - Power Supply (5V, 3A Recommended)
  - HDMI Display (Optional)
  - 3.5-inch LCD Touchscreen

## **Installation**

### **Fastest way is to run install_file_test_no_desktop.sh from the get go (still in testing phase)**

### **1. Clone the Repository**

To clone this repository, use the following command:

```bash
git clone https://github.com/yourusername/Xeno-Wifi-Companion.git
cd Xeno-Wifi-Companion
```

---

## **Setup Configurations**

### **Wi-Fi Credentials: `config/wifi_credentials.json`**

Create a `wifi_credentials.json` file in the `config` directory with the following format:

```json
[
    {"SSID": "NetworkName", "Password": "NetworkPassword"},
    {"SSID": "AnotherNetwork", "Password": "AnotherPassword"}
]
```

### **SSH Credentials: `config/ssh_default_credentials.txt`**

Create a `ssh_default_credentials.txt` file in the `config` directory with the following format:

```plaintext
username:password
anotheruser:anotherpassword
```

---

## **Adjust Permissions**

Ensure proper permissions for directories used by the tool:

```bash
chmod 777 utils/html_logs utils/json_logs
```

---

## **Usage**

### **1. Run the Script**

To manually start the script, use the following command:

```bash
sudo python3 main.py
```

### **2. Service Mode**

To run the script as a service on system startup, follow these steps:

#### **Create a Service File**

Create a new service file at `/etc/systemd/system/xeno.service`:

```plaintext
[Unit]
Description=Xeno Wi-Fi Companion Service
After=network.target

[Service]
ExecStart=/usr/bin/python3 /path/to/main.py
WorkingDirectory=/path/to/project
Restart=always
User=pi
Group=pi

[Install]
WantedBy=multi-user.target
```

#### **Enable and Start the Service**

Run the following commands to enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable xeno.service
sudo systemctl start xeno.service
```

---

## **Monitoring and Logs**

- **View service logs:**

```bash
sudo journalctl -u xeno.service -f
```

- **Check HTML and JSON logs in the following directories:**
  - `utils/html_logs`
  - `utils/json_logs`

---

## **Directory Structure**

```plaintext
.
├── attacks/
│   ├── recon.py                # Reconnaissance module
│   ├── vulnerability_scan.py   # Vulnerability scanning module
│   └── exploit_tester.py       # Exploit testing module
├── config/
│   ├── wifi_credentials.json   # Wi-Fi credentials file
│   └── ssh_default_credentials.txt # SSH credentials file
├── scans/
│   └── nmap_scanner.py         # Nmap-based network scanning
├── utils/
│   ├── logger.py               # Custom logging utility
│   ├── html_logger.py          # HTML report generation
│   ├── json_logs/              # JSON log directory
│   └── html_logs/              # HTML log directory
├── wifi/
│   ├── wifi_manager.py         # Controls wifi related stuff
├── main.py                     # Main script entry point
└── requirements.txt            # Python dependencies
```

---

## **Step-by-Step Workflow**

### **1. Prepare Configuration Files**

- Populate `config/wifi_credentials.json` with your target Wi-Fi networks.
- Add default SSH credentials in `config/ssh_default_credentials.txt`.

### **2. Run or Deploy the Script**

- **Run manually** with:

```bash
sudo python3 main.py
```

- **Deploy as a system service** for continuous scanning.

### **3. Monitor Logs**

- **Check logs using:**

```bash
sudo journalctl -u xeno.service -f
```

### **4. Review Reports**

- **Find JSON logs** in `utils/json_logs`.
- **Review HTML reports** in `utils/html_logs`.

### **5. Extend and Customize**

- Add more attack modules in the `attacks/` directory.
- Modify `main.py` to include custom workflows.

---

## **Disclaimer**

This project is intended for educational and ethical penetration testing purposes only. Unauthorized use on networks or devices without proper authorization is illegal and punishable by law.

**Use responsibly** and ensure you have the necessary permissions before testing any network or system.
