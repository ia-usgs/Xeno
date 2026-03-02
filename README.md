<a id="readme-top"></a>

<div align="center">
  <img src="xeno.png" alt="Xeno" width="220"/>
  <h1>XENO: Wi-Fi Companion</h1>
  <p>Automated Wi-Fi auditing, reconnaissance, and penetration testing on a Raspberry Pi.</p>

  [![Reddit](https://img.shields.io/badge/Reddit-Community-FF4500?style=flat-square&logo=reddit)](https://www.reddit.com/r/xenowificompanion/s/Yu8tJWnRLq)
  [![YouTube](https://img.shields.io/badge/YouTube-Channel-FF0000?style=flat-square&logo=youtube)](https://www.youtube.com/@xenowificompanion)
  [![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=flat-square&logo=discord)](https://discord.gg/XKwmuZ9wfP)
  [![Buy Me a Coffee](https://img.shields.io/badge/Support-Buy%20Me%20a%20Coffee-FFDD00?style=flat-square&logo=buy-me-a-coffee)](https://buymeacoffee.com/xenowificompanion)
</div>

---

> **Disclaimer:** Xeno is intended for **educational and ethical security testing only**. Only use it on networks and devices you own or have explicit written permission to test. Unauthorized use is illegal. By using this software you accept full responsibility for your actions.

---

## What is Xeno?

Xeno is a Python-based autonomous security tool that runs on a Raspberry Pi. It connects to Wi-Fi networks one at a time, silently scans the subnet, fingerprints every device, tests for known vulnerabilities, and generates per-SSID HTML reports accessible from any browser on your network.

---

## Features

| Category | What Xeno does |
|---|---|
| **Wi-Fi Management** | Cycles through credentials in `config/wifi_credentials.json`, auto-reconnects, randomises MAC address |
| **Device Discovery** | Two-phase nmap scan: ARP ping (fast, gets MACs) → OS fingerprinting (`-O`) on confirmed live hosts |
| **Auto Device Registry** | New devices are automatically registered to `config/known_devices.json` on first scan, no manual entry needed |
| **Per-SSID Isolation** | Devices are locked to the SSID they were first seen on; cross-contamination between reports is prevented at save time |
| **Reconnaissance** | OS detection, open port enumeration, service/version fingerprinting via nmap & custom scripts |
| **Vulnerability Scanning** | Matches discovered services against ExploitDB via `searchsploit` |
| **Exploit Testing** | Downloads and executes matching exploits against vulnerable targets |
| **File Harvesting** | Retrieves files from targets over SSH, FTP, and SMB |
| **Web Dashboard** | Flask server on port `8080`. Reports, Errors, Live Feed, File Manager, and a **Stop** button |
| **E-Paper Display** | Real-time workflow status on a Waveshare 2.13" HAT |
| **Structured Logging** | JSON + HTML logs, centralised error log, live activity feed |

---

## Parts List

| Item | Notes |
|---|---|
| Raspberry Pi | Pi 5, 4, 3B+, or Zero W recommended |
| MicroSD Card | 16 GB minimum, 32 GB+ recommended |
| Wi-Fi Adapter | Alfa AWUS036ACHM or similar dual-band adapter |
| Power Supply | 5V 3A, or a USB battery bank for portable use |
| Waveshare 2.13" E-Ink HAT V4 | Optional. Only needed for the physical display |

---

## Installation

### Option A — Community Image (easiest)

Flash the official Xeno image to your SD card. Everything is pre-installed and the `xeno.service` systemd unit is enabled out of the box.

After first boot:
1. Edit Wi-Fi credentials:
   ```bash
   sudo nano /home/pi/xeno/config/wifi_credentials.json
   ```
2. Optionally change the pet name:
   ```bash
   sudo nano /home/pi/xeno/state.json
   # change "pet_name": "Xeno" to whatever you like
   ```
3. Reboot — Xeno starts automatically.

---

### Option B — Automatic Installer

> Use **Raspberry Pi OS Lite 64-bit** (except for Pi Zero W — use 32-bit Lite).

```bash
sudo apt update && sudo apt install git -y
git clone https://github.com/ia-usgs/Xeno.git
cd Xeno
sudo chmod +x install_file.sh
sudo ./install_file.sh
```

The installer will:
- Install all system dependencies (`nmap`, `network-manager`, `macchanger`, `smbclient`, …)
- Install Python requirements
- Clone ExploitDB
- Set up log directories and the `xeno.service` systemd unit
- Configure the e-paper display drivers

---

### Option C — Manual

```bash
# 1. Clone
git clone https://github.com/ia-usgs/Xeno.git && cd Xeno

# 2. System deps
sudo apt-get update && sudo apt-get install -y \
  git python3 python3-pip python3-venv curl dnsutils macchanger \
  smbclient libjpeg-dev libpng-dev nmap network-manager

# 3. Python deps
sudo pip3 install -r requirements.txt --break-system-packages

# 4. Enable SPI (for e-paper display)
sudo raspi-config nonint do_spi 0
```

---

## Configuration

### Wi-Fi Credentials — `config/wifi_credentials.json`
```json
[
  { "SSID": "HomeNetwork",   "Password": "hunter2"     },
  { "SSID": "WorkNetwork",   "Password": "s3cur3p@ss"  }
]
```
Xeno connects to each network in order, runs a full scan cycle, then moves on to the next.

### SSH Credentials — `config/ssh_default_credentials.txt`
```
admin:admin
pi:raspberry
root:toor
```

### Known Devices — `config/known_devices.json`
Xeno **auto-populates this file** as it scans. When a MAC address is seen for the first time on a given SSID, it is automatically registered to that SSID. You can also add entries manually:
```json
{
  "devices": {
    "AA:BB:CC:DD:EE:FF": {
      "ssid": "HomeNetwork",
      "hostname": "MyLaptop",
      "notes": "Owner's MacBook Pro"
    }
  }
}
```

---

## Running Xeno

### As a service (recommended)
```bash
sudo systemctl start xeno.service    # start
sudo systemctl stop xeno.service     # stop
sudo systemctl enable xeno.service   # auto-start on boot
sudo journalctl -u xeno.service -f   # live logs
```

### Manually
```bash
cd /home/pi/xeno
sudo python3 main.py
```

> If you get a `GPIO Busy` error when running manually, the service is still running so stop it first with `sudo systemctl stop xeno.service`.

---

## Web Dashboard

Xeno serves a dashboard on **`http://<pi-ip>:8080`** once it starts.

| Page | URL | What it shows |
|---|---|---|
| Reports | `/` | Per-SSID HTML scan reports |
| Errors | `/errors` | Runtime errors with severity badges |
| Live | `/live` | Real-time activity feed (auto-refreshes every 3s) |
| Files | `/files` | Browse and edit files on the Pi |

### Stop Button
Every page has a red **⏹ STOP** button in the nav bar. Clicking it:
1. Prompts for confirmation
2. Kills the `main.py` scanner process
3. Shuts down the Flask server

To restart after stopping: SSH in and run `sudo python3 main.py` or `sudo systemctl start xeno.service`.

### Per-SSID Reports
Each report shows:
- **Device table** — IP, MAC, Vendor, OS, Hostname, Status badge (`IDENTIFIED` / `VISITOR`)
- **Vulnerability table** — Port, Service, Version, Matched CVE/Exploit, Severity badge
- OS detection is powered by nmap's `-O --osscan-guess` fingerprinting

---

## Leveling System

Xeno has an XP-based leveling system — the more it scans and finds, the stronger it gets. Level and XP are saved to `state.json` and persist across reboots.

### XP Rewards

| Action | XP |
|---|---|
| Device discovered | +5 XP each |
| Vulnerability matched | +15 XP each |
| Successful exploit | +30 XP each |
| Files stolen from a host | +50 XP each |
| WPA handshake captured | +25 XP |
| Network fully scanned | +10 XP |

### Level Curve

Leveling gets progressively harder using a quadratic curve (`75 × n²`):

| Level | Total XP needed | XP gap from previous |
|---|---|---|
| 2 | 75 XP | 75 |
| 5 | 1,875 XP | 375 |
| 10 | 7,500 XP | 675 |
| 20 | 30,000 XP | 1,425 |

A typical scan cycle (10 devices + 3 vulns + 1 network) earns ~**100 XP**, so:
- **Level 2** after ~1–2 scans
- **Level 10** after days of active scanning
- **Level 20** requires consistent long-term use

### Level Up
When Xeno levels up, the e-paper display shows **"LEVEL UP! Now Lv.X"** and the level is updated in `state.json`. The current level and XP are also logged to the live feed after each SSID cycle.

---


```
xeno/
├── attacks/
│   ├── exploit_tester.py        # Exploit download & execution
│   ├── file_stealer.py          # SSH/FTP/SMB file harvesting
│   ├── recon.py                 # Port scan & OS fingerprinting
│   └── vulnerability_scan.py   # searchsploit matching
├── config/
│   ├── known_devices.json       # Auto-populated device registry (per-SSID)
│   ├── password_list.txt        # Brute-force password list
│   ├── ssh_default_credentials.txt
│   └── wifi_credentials.json   # SSIDs & passwords to cycle through
├── scans/
│   └── nmap_scanner.py          # Two-phase nmap (ARP discovery + OS detection)
├── services/                    # Orchestration layer
│   ├── exploit_service.py
│   ├── file_stealer_service.py
│   ├── log_service.py           # Save/filter scan data per-SSID, auto-register devices
│   ├── nmap_service.py          # Dynamic subnet detection + host exclusion
│   ├── recon_service.py
│   ├── vulnerability_service.py
│   └── wifi_service.py
├── templates/                   # Flask/Jinja2 HTML templates
│   ├── index.html               # Reports list
│   ├── errors.html              # Error log
│   ├── live.html                # Activity feed
│   └── files.html               # File manager
├── utils/
│   ├── html_logger.py           # HTML report generator
│   ├── logger.py                # JSON error + activity logging
│   ├── html_logs/               # Generated per-SSID HTML reports
│   └── json_logs/               # Raw scan JSON data
├── wifi/
│   └── wifi_manager.py          # nmcli-based Wi-Fi manager
├── logs/
│   ├── scan.log                 # Main log file
│   ├── errors.json              # Structured error log
│   └── activity.json            # Live activity feed data
├── static/                      # CSS & images for the dashboard
├── web_server.py                # Flask dashboard server
├── main.py                      # Entry point / scan orchestrator
└── install_file.sh              # One-shot installation script
```

---

## Monitoring & Debugging

```bash
# Live service log
sudo journalctl -u xeno.service -f

# Main scan log
tail -f /home/pi/xeno/logs/scan.log

# Check for permission issues
sudo chown root:pi <filename>
sudo chmod 770 <filename>
```

**Common issues:**

| Problem | Fix |
|---|---|
| `GPIO Busy` | Service is running. `sudo systemctl stop xeno.service` first |
| Scan finds nothing | Increase recon timeout in `attacks/recon.py` → `def scan_ports(self, target, timeout=60)` |
| OS shows Unknown | Device didn't respond to TCP probes (expected for IoT/phones in deep sleep) |
| Exploit path not found | Ensure ExploitDB is installed at `/opt/exploitdb` |
| UTF-8 decode error | Pull latest, all file I/O now uses `errors='replace'` |

---

## Contributing

Pull requests are welcome. For major changes open an issue or reach out on Reddit or Discord first.

---

<p align="center">(<a href="#readme-top">back to top</a>)</p>
