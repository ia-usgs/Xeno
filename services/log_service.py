# services/log_service.py
import os
import json
import re
from utils.html_logger import HTMLLogger

_KNOWN_DEVICES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "config", "known_devices.json"
)

def _load_known_devices():
    """Return {MAC_UPPER: entry} from config/known_devices.json, or {}."""
    if not os.path.exists(_KNOWN_DEVICES_PATH):
        return {}
    try:
        with open(_KNOWN_DEVICES_PATH, "r") as f:
            raw = json.load(f)
        return {k.upper(): v for k, v in raw.get("devices", {}).items()}
    except Exception as exc:
        print(f"[WARN] log_service: could not load known_devices.json: {exc}")
        return {}


def _mac_from_nmap_line(line):
    """Extract MAC address from an nmap output line, or return None."""
    m = re.search(r'MAC Address:\s*([0-9A-Fa-f:]{17})', line)
    return m.group(1).upper() if m else None


def _filter_scan_for_ssid(ssid, scan_result):
    """
    Remove devices that are known to belong to a *different* SSID.
    Works on discovered_ips list and raw_output nmap text.
    Devices tagged 'shared' or not in known_devices pass through unchanged.
    """
    known = _load_known_devices()
    if not known:
        return scan_result  # no config — pass everything through

    def _owned_by_other(mac):
        if not mac:
            return False
        entry = known.get(mac.upper())
        if not entry:
            return False                          # unregistered = visitor, keep
        home = entry.get("ssid", "")
        return home.lower() != "shared" and home != ssid

    result = dict(scan_result)

    # ── Filter discovered_ips list ──────────────────────────────────────────
    # Build a MAC→IP reverse map from raw_output so we can check ownership
    raw = result.get("raw_output", "")
    # Parse nmap blocks to build {ip: mac}
    ip_mac = {}
    current_ip = None
    ip_pat  = re.compile(r'Nmap scan report for (?:(\S+)\s*\(([^)]+)\)|(\S+))')
    mac_pat = re.compile(r'MAC Address:\s*([0-9A-Fa-f:]{17})')
    for line in raw.splitlines():
        m = ip_pat.search(line)
        if m:
            current_ip = m.group(2) or m.group(3)
        m2 = mac_pat.search(line)
        if m2 and current_ip:
            ip_mac[current_ip] = m2.group(1).upper()

    if "discovered_ips" in result:
        result["discovered_ips"] = [
            ip for ip in result["discovered_ips"]
            if not _owned_by_other(ip_mac.get(ip))
        ]

    # ── Filter raw_output nmap blocks ───────────────────────────────────────
    if raw:
        # Split into header + per-host blocks and drop blocks for other SSIDs
        lines     = raw.splitlines(keepends=True)
        out       = []
        block     = []
        block_mac = None

        def flush(blk, mac):
            if not _owned_by_other(mac):
                out.extend(blk)

        for line in lines:
            if ip_pat.search(line):
                flush(block, block_mac)
                block = [line]
                block_mac = None
            else:
                block.append(line)
                m2 = mac_pat.search(line)
                if m2:
                    block_mac = m2.group(1).upper()

        flush(block, block_mac)
        result["raw_output"] = "".join(out)

    return result


def _auto_register_devices(ssid, scan_result):
    """
    Parse the nmap raw_output in scan_result and auto-add any MAC addresses
    not already in known_devices.json, assigning them to `ssid`.
    Existing entries are never overwritten — first SSID seen wins.
    """
    raw = scan_result.get("raw_output", "")
    if not raw:
        return

    # Parse nmap blocks into {mac: {hostname, vendor}}
    ip_pat   = re.compile(r'Nmap scan report for (?:(\S+)\s*\(([^)]+)\)|(\S+))')
    mac_pat  = re.compile(r'MAC Address:\s*([0-9A-Fa-f:]{17})\s*(?:\(([^)]*)\))?')

    discovered = {}   # mac -> {hostname, vendor}
    hostname = "Unknown"
    current_ip = None

    for line in raw.splitlines():
        m = ip_pat.search(line)
        if m:
            # new host block — hostname may appear in the report line
            if m.group(1):          # "hostname (ip)" format
                hostname = m.group(1)
                current_ip = m.group(2)
            else:                   # bare IP format
                hostname = "Unknown"
                current_ip = m.group(3)

        m2 = mac_pat.search(line)
        if m2 and current_ip:
            mac    = m2.group(1).upper()
            vendor = (m2.group(2) or "Unknown").strip() or "Unknown"
            discovered[mac] = {"hostname": hostname, "vendor": vendor}

    if not discovered:
        return

    # Load the full known_devices file (preserving structure)
    try:
        if os.path.exists(_KNOWN_DEVICES_PATH):
            with open(_KNOWN_DEVICES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {"_comment": "Auto-generated device registry.", "devices": {}}

        devices = data.get("devices", {})
        # Normalise existing keys to UPPER for lookup
        existing_upper = {k.upper() for k in devices}

        added = 0
        for mac, info in discovered.items():
            if mac not in existing_upper:
                # Store with normalised upper-case key
                devices[mac] = {
                    "ssid":     ssid,
                    "hostname": info["hostname"],
                    "notes":    f"Auto-registered from {ssid} scan"
                }
                added += 1

        if added:
            data["devices"] = devices
            with open(_KNOWN_DEVICES_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            print(f"[INFO] Auto-registered {added} new device(s) to {ssid} in known_devices.json")

    except Exception as exc:
        print(f"[WARN] _auto_register_devices failed: {exc}")



class LogService:
    def __init__(self,
                 output_dir="utils/html_logs",
                 json_dir="utils/json_logs"):
        self.html_logger = HTMLLogger(output_dir=output_dir,
                                      json_dir=json_dir)

    def save_scan(self, ssid, scan_result):
        """
        Appends a raw Nmap scan result to JSON and regenerates the HTML.
        New devices are auto-registered to known_devices.json for this SSID,
        then any devices belonging to a different SSID are stripped before saving.
        """
        _auto_register_devices(ssid, scan_result)       # 1. register new MACs
        self.html_logger._known_devices = None           # 2. bust the cache so generator re-reads the file
        filtered = _filter_scan_for_ssid(ssid, scan_result)  # 3. drop other-SSID devices
        self.html_logger.save_scan_result_to_json(ssid, filtered)
        self.html_logger.generate_html_from_json(ssid)



    def append_recon(self, ssid, recon_results):
        """
        Appends recon results (as a separate entry) and regenerates the HTML.
        Entries for devices belonging to other SSIDs are dropped.
        """
        known = _load_known_devices()
        if known:
            filtered_recon = []
            for device in recon_results:
                mac = (device.get("mac") or "").upper()
                entry = known.get(mac)
                if entry is None:
                    filtered_recon.append(device)  # visitor — keep
                elif entry.get("ssid", "").lower() == "shared":
                    filtered_recon.append(device)
                elif entry.get("ssid", "") == ssid:
                    filtered_recon.append(device)
                # else: belongs to another SSID — drop
            recon_results = filtered_recon

        self.html_logger.save_scan_result_to_json(
            ssid,
            {"recon_results": recon_results}
        )
        self.html_logger.generate_html_from_json(ssid)

    def append_vulns(self, ssid, vulnerability_results):
        """
        Appends vulnerability results and regenerates the HTML.
        """
        self.html_logger.save_scan_result_to_json(
            ssid,
            {"vulnerability_results": vulnerability_results}
        )
        self.html_logger.generate_html_from_json(ssid)

    def append_exploits(self, ssid, exploit_results):
        """
        Appends exploit test outcomes and regenerates the HTML.
        """
        self.html_logger.save_scan_result_to_json(
            ssid,
            {"exploit_results": exploit_results}
        )
        self.html_logger.generate_html_from_json(ssid)

    def append_handshake(self, ssid, handshake_count):
        """
        Record the running total of captured handshakes for the given SSID.
        """
        self.html_logger.save_scan_result_to_json(
            ssid,
            {"handshake_count": handshake_count}
        )
        self.html_logger.generate_html_from_json(ssid)

    def append_passwords(self, ssid, pw_map):
        """
        Append cracked passwords (from WPA-Sec) and regenerate the HTML.
        pw_map should be {ssid: password, ...}.
        """
        self.html_logger.save_scan_result_to_json(
            ssid,
            {"cracked_passwords": pw_map}
        )
        self.html_logger.generate_html_from_json(ssid)
