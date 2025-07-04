import os
import json
from datetime import datetime


class HTMLLogger:
    def __init__(self, output_dir="utils/html_logs", json_dir="utils/json_logs"):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        self.output_dir = output_dir
        self.json_dir = json_dir

    def save_scan_result_to_json(self, ssid, scan_result):
        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(json_file):
            with open(json_file, "r") as file:
                data = json.load(file)
        else:
            data = {"ssid": ssid, "scans": []}

        data["scans"].append({"timestamp": timestamp, "result": scan_result})

        with open(json_file, "w") as file:
            json.dump(data, file, indent=4)

        print(f"[INFO] Scan result saved to JSON: {json_file}")

        self.generate_html_from_json(ssid) #added this to test if the logs work
        return json_file

    def generate_html_from_json(self, ssid):
        json_file     = os.path.join(self.json_dir,   f"{ssid}.json")
        html_file     = os.path.join(self.output_dir, f"{ssid}.html")
        template_file = os.path.join("utils", "webInterface", "wifiLogTemplate.html")

        # 1) Load JSON data
        if not os.path.exists(json_file):
            print(f"[WARNING] No JSON file found for SSID: {ssid}. Cannot generate HTML log.")
            return
        with open(json_file, "r") as f:
            data = json.load(f)

        # 2) Load HTML template
        if not os.path.exists(template_file):
            print(f"[ERROR] Template file not found: {template_file}. Cannot generate HTML log.")
            return
        with open(template_file, "r") as f:
            wifi_log_template = f.read()

        # 3) Build scan entries, de-duplicating IPs and including hostname
        seen_ips    = set()
        scan_entries = ""
        for scan in data["scans"]:
            if "result" in scan:
                scan_entries += f"<p><b>Scan Conducted At:</b> {scan['timestamp']}</p>\n"
                scan_entries += """
                <table>
                  <thead>
                    <tr>
                      <th>IP Address</th>
                      <th>Hostname</th>
                      <th>MAC Address</th>
                      <th>Vendor</th>
                    </tr>
                  </thead>
                  <tbody>
                """
                discovered_devices = self._parse_nmap_result(scan["result"])
                for device in discovered_devices:
                    ip = device["ip"]
                    if ip in seen_ips:
                        continue
                    seen_ips.add(ip)
                    scan_entries += f"""
                    <tr>
                      <td>{ip}</td>
                      <td>{device.get('hostname', 'Unknown')}</td>
                      <td>{device.get('mac', 'Unknown')}</td>
                      <td>{device.get('vendor', 'Unknown')}</td>
                    </tr>
                    """
                scan_entries += "</tbody></table>\n"

        # 4) Build vulnerability entries
        vulnerability_entries = ""
        for scan in data["scans"]:
            if "vulnerability_results" in scan:
                vulnerability_entries += f"<p><b>Scan Conducted At:</b> {scan['timestamp']}</p>\n"
                vulnerability_entries += """
                <table>
                  <thead>
                    <tr>
                      <th>Target</th>
                      <th>Port</th>
                      <th>Service</th>
                      <th>Version</th>
                      <th>Exploit Title</th>
                      <th>Path</th>
                    </tr>
                  </thead>
                  <tbody>
                """
                for vuln in scan["vulnerability_results"].get("vulnerabilities", []):
                    vulnerability_entries += f"""
                    <tr>
                      <td>{scan['vulnerability_results'].get('target', 'Unknown')}</td>
                      <td>{vuln.get('port', 'Unknown')}</td>
                      <td>{vuln.get('name', 'Unknown')}</td>
                      <td>{vuln.get('version', 'Unknown')}</td>
                      <td>{self._parse_exploit_titles(vuln.get('vulnerabilities', 'No Exploits'))}</td>
                      <td>{self._parse_exploit_paths(vuln.get('vulnerabilities', 'No Paths'))}</td>
                    </tr>
                    """
                vulnerability_entries += "</tbody></table>\n"

        # 5) Inject into template and write out HTML
        wifi_log_content = wifi_log_template.replace("{ssid}", ssid)
        wifi_log_content = wifi_log_content.replace("{scan_entries}", scan_entries)
        wifi_log_content = wifi_log_content.replace("{vulnerability_entries}", vulnerability_entries)

        with open(html_file, "w") as f:
            f.write(wifi_log_content)

        print(f"[INFO] HTML log updated: {html_file}")

    def _parse_nmap_result(self, result):
        """
        Helper function to parse Nmap result data and extract discovered devices.

        Parameters:
            result (str | dict): The raw Nmap scan result or a dictionary containing raw_output.

        Returns:
            list: A list of dictionaries, each containing device details (ip, hostname, mac, vendor, os_version).
        """
        device_map = {}
        current_ip = None
        current_mac = None
        vendor = "Unknown"
        os_version = "Unknown"
        current_hostname = ""

        # Normalize to lines
        if isinstance(result, dict):
            raw_output = result.get("raw_output", "")
            lines = raw_output.split("\n") if isinstance(raw_output, str) else []
        else:
            lines = result.split("\n")

        for line in lines:
            if line.startswith("Nmap scan report for"):
                raw = line.split("for", 1)[1].strip()
                if "(" in raw and ")" in raw:
                    current_hostname = raw.split("(")[0].strip()
                    current_ip = raw.split("(")[1].strip(")")
                else:
                    current_hostname = ""
                    current_ip = raw

            elif "MAC Address" in line:
                parts = line.split("MAC Address: ")
                if len(parts) > 1:
                    mac_info = parts[1].split(" ", 1)
                    current_mac = mac_info[0]
                    vendor = mac_info[1].strip("()") if len(mac_info) > 1 else "Unknown"

            elif "OS details:" in line:
                os_version = line.split("OS details:")[1].strip()

            elif "Running:" in line:
                os_version = line.split("Running:")[1].strip()

            if current_ip:
                if current_ip not in device_map:
                    device_map[current_ip] = {
                        "ip": current_ip,
                        "hostname": current_hostname or "Unknown",
                        "mac": current_mac or "Unknown",
                        "vendor": vendor or "Unknown",
                        "os_version": os_version or "Unknown",
                    }
                else:
                    # Update only if new data is more specific
                    if current_mac and device_map[current_ip]["mac"] == "Unknown":
                        device_map[current_ip]["mac"] = current_mac
                    if vendor and device_map[current_ip]["vendor"] == "Unknown":
                        device_map[current_ip]["vendor"] = vendor
                    if os_version and device_map[current_ip]["os_version"] == "Unknown":
                        device_map[current_ip]["os_version"] = os_version

                # Reset for next device
                current_ip = None
                current_mac = None
                vendor = "Unknown"
                os_version = "Unknown"
                current_hostname = ""

        return list(device_map.values())

    def _parse_exploit_titles(self, vulnerabilities):
        if "Exploit Title" in vulnerabilities:
            lines = vulnerabilities.split("\n")
            titles = [line.split("|")[0].strip() for line in lines if "|" in line]
            return "<br>".join(titles)
        return "No Exploits"

    def _parse_exploit_paths(self, vulnerabilities):
        if "|" in vulnerabilities:
            lines = vulnerabilities.split("\n")
            paths = [line.split("|")[1].strip() for line in lines if "|" in line]
            return "<br>".join(paths)
        return "No Paths"

    def append_vulnerability_results_to_html(self, ssid, vulnerability_results):
        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(json_file):
            with open(json_file, "r") as file:
                data = json.load(file)
        else:
            data = {"ssid": ssid, "scans": []}

        data["scans"].append({
            "timestamp": timestamp,
            "vulnerability_results": vulnerability_results
        })

        with open(json_file, "w") as file:
            json.dump(data, file, indent=4)

        self.generate_html_from_json(ssid)
        print(f"[INFO] Vulnerability results appended and HTML updated for SSID: {ssid}")
