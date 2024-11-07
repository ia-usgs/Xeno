
# WiFi Scout - Autonomous Network Reconnaissance Partner for Pwnagotchi

WiFi Scout is an autonomous network reconnaissance tool designed to work as a complementary partner to [Pwnagotchi](https://pwnagotchi.ai). Running on a Raspberry Pi or similar device, WiFi Scout integrates with Pwnagotchi to provide in-depth Wi-Fi security assessments, device discovery, and pentesting within specified networks. It can leverage the cracked passwords captured by Pwnagotchi's WPA-SEC plugin and is being enhanced to communicate with Pwnagotchi via a mesh network for streamlined handshake and password transfer.

### Table of Contents
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Integration with Pwnagotchi](#integration-with-pwnagotchi)
- [Modules and Functionality](#modules-and-functionality)
- [Configuration](#configuration)
- [Data Collection and Logging](#data-collection-and-logging)
- [Troubleshooting](#troubleshooting)

---

## Features

- **Automated Device Discovery**: Scans the network for connected devices, capturing IP addresses, hostnames, open ports, and service types.
- **Wi-Fi Security Assessment**: Evaluates encryption type, checks for client isolation, and assesses password security using WPA-SEC captures.
- **Advanced Scans**: Performs OS and service fingerprinting, vulnerability scans, and rogue service detection.
- **Incremental Data Saving**: Periodically saves scan results, preserving data in case of interruptions.
- **Bluetooth Device Detection**: Identifies nearby Bluetooth-enabled devices for comprehensive wireless security analysis.
- **Pwnagotchi Integration**: Captures and utilizes WPA-SEC cracked passwords and handshakes.

---

## Installation

### Prerequisites
1. **Hardware**: Raspberry Pi or other Linux-based system with Wi-Fi capabilities.
2. **Software**: Ensure Python 3 and Git are installed.

### Required Libraries and Tools
Install necessary libraries:
```bash
sudo apt update
sudo apt install nmap dnsutils reaver -y
pip install mac-vendor-lookup scapy
```

Clone this repository:
```bash
git clone https://github.com/yourusername/wifi-scout.git
cd wifi-scout
```

### Configuration
1. Modify the `config.json` file to include Wi-Fi network credentials, target IPs, and other network-specific configurations.
2. Configure WPA-SEC integration for cracked password handling as described below. For now just grab the info from the WPA-SEC list of cracked passwords.

---

## Usage

1. **Run the main script**:
   ```bash
   python3 main.py
   ```
2. **Log Output**: The tool outputs scan progress to the terminal, including connection status, discovered devices, and incremental saves.

3. **Results**: Results are saved in JSON format, with WPA-SEC information incorporated where applicable.

---

## Integration with Pwnagotchi

### WPA-SEC Plugin Integration
WiFi Scout works seamlessly with the WPA-SEC plugin on Pwnagotchi's cracked password list, using the cracked Wi-Fi passwords from WPA-SEC as part of its network reconnaissance. For now manually add to config.json until an automated way is made via the mesh system. Ensure the following format in `config.json`:

```json
{
    "wpa_sec_passwords": [
        {
            "ssid": "<SSID>",
            "password": "<PASSWORD>"
        },
        ...
    ]
}
```

### Planned Mesh Network Communication
WiFi Scout is being enhanced to communicate with Pwnagotchi through a mesh network, enabling automatic transfer of handshakes and cracked passwords. This will allow the two devices to collaborate for seamless data exchange, with Scout autonomously updating captured passwords and handshake data from Pwnagotchi.

---

## Modules and Functionality

### `main.py`
- **Main Controller**: Manages network connections, initiates scans, and coordinates module operations.
- **Incremental Saving**: Saves scan progress to prevent data loss.

### `network_module.py`
- **Wi-Fi Connection Management**: Connects and disconnects from networks.
- **File Transfer (Optional)**: Provides tools for data transfer, supporting potential mesh communications with Pwnagotchi.

### `network_analysis_module.py`
- **Device Discovery**: Detects devices on the network, logging IP addresses, hostnames, and open ports.
- **Advanced Scanning**: Includes OS fingerprinting, vulnerability scanning, and rogue service detection.

### `wifi_security.py`
- **Wi-Fi Security Checks**: Assesses Wi-Fi security, utilizing WPA-SEC passwords if available.
- **Vendor Info Lookup**: Uses `AsyncMacLookup` for manufacturer identification.

### `bluetooth_scan.py`
- **Bluetooth Detection**: Detects nearby Bluetooth-enabled devices, capturing MAC addresses and device names.

### `advanced_attacks.py`
- **Complex Attack Management**: Launches advanced network attacks based on scan results, including targeted rogue AP attacks, password capture, and data interception.

### `utils.py`
- **Helper Functions**: Includes utilities for error logging, configuration loading, and data handling.

---

## Configuration

### `config.json`
- **SSID and Passwords**: List of SSIDs, passwords, and WPA-SEC cracked password entries.
- **Target IPs**: Specify IP ranges for detailed scanning.
- **Scan Intervals**: Customize the scan frequency and waiting period between scans.

---

## Data Collection and Logging

- **Data Storage**: Results are saved incrementally in JSON files, capturing essential data such as device IP, hostname, open ports, and detected vulnerabilities.
- **Naming Convention**: Each scan result file is named based on the SSID (e.g., `scan_results_<SSID>.json`).
- **IP Tracking**: Tracks previously scanned IPs to avoid duplicate scans unless configuration changes are detected.

---

## Troubleshooting

- **`RuntimeWarning: coroutine 'AsyncMacLookup.lookup' was never awaited`**:
   Ensure that all asynchronous functions are called within async contexts with proper `await` statements.

---

## Future Enhancements

- **Mesh Network Communication**: Full integration with Pwnagotchi to automatically share handshakes and cracked passwords.
- **Expanded Bluetooth Scanning**: Provide signal strength and classification for Bluetooth devices.
- **Enhanced WPA-SEC Integration**: Allow Scout to request specific SSIDs for focused scanning.

---

### Contributing
Contributions are welcome! Please submit pull requests with detailed explanations of changes.
