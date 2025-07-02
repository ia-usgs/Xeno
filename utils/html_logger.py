import os
from datetime import datetime
from utils.json_manager import json_manager


class HTMLLogger:
    def __init__(self, output_dir="utils/html_logs", json_dir="utils/json_logs"):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        self.output_dir = output_dir
        self.json_dir = json_dir

    def save_scan_result_to_json(self, ssid, scan_result):
        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        
        # Add new scan entry with proper structure
        scan_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 
            "result": scan_result
        }
        
        success = json_manager.append_to_json_array(
            json_file,
            "scans",
            scan_entry,
            schema_type="scan_result"
        )

        if success:
            print(f"[INFO] Scan result saved to JSON: {json_file}")
        else:
            print(f"[ERROR] Failed to save scan result to JSON: {json_file}")
        
        return json_file

    def generate_html_from_json(self, ssid):
        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        html_file = os.path.join(self.output_dir, f"{ssid}.html")
        template_file = os.path.join("utils", "webInterface/wifiLogTemplate.html")

        if not os.path.exists(json_file):
            print(f"[WARNING] No JSON file found for SSID: {ssid}. Cannot generate HTML log.")
            return
        
        try:
            data = json_manager.load_json(json_file, schema_type="scan_result")
        except Exception as e:
            print(f"[ERROR] Failed to load JSON data from {json_file}: {e}")
            return
        
        if not os.path.exists(template_file):
            print(f"[ERROR] Template file not found: {template_file}. Cannot generate HTML log.")
            return
        
        with open(template_file, "r") as file:
            wifi_log_template = file.read()
        
        # Prepare HTML content
        scan_entries = ""
        for scan in data["scans"]:
            if "result" in scan:
                scan_entries += f"""
                <p><b>Scan Conducted At:</b> {scan['timestamp']}</p>
                <table>
                    <thead>
                        <tr>
                            <th>IP Address</th>
                            <th>MAC Address</th>
                            <th>Vendor</th>
                        </tr>
                    </thead>
                    <tbody>
                """
                discovered_devices = self._parse_nmap_result(scan["result"])
                for device in discovered_devices:
                    scan_entries += f"""
                    <tr>
                        <td>{device.get('ip', 'Unknown')}</td>
                        <td>{device.get('mac', 'Unknown')}</td>
                        <td>{device.get('vendor', 'Unknown')}</td>
                    </tr>
                    """
                scan_entries += "</tbody></table>"
        
        vulnerability_entries = ""
        for scan in data["scans"]:
            if "vulnerability_results" in scan:
                vulnerability_entries += f"""
                <p><b>Scan Conducted At:</b> {scan['timestamp']}</p>
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
            vulnerability_entries += """</tbody></table>"""

        # Replace placeholders in the template
        wifi_log_content = wifi_log_template.replace("{ssid}", ssid)
        wifi_log_content = wifi_log_content.replace("{scan_entries}", scan_entries)
        wifi_log_content = wifi_log_content.replace("{vulnerability_entries}", vulnerability_entries)

        with open(html_file, "w") as file:
            file.write(wifi_log_content)

        print(f"[INFO] HTML log updated: {html_file}")

    def _parse_nmap_result(self, result):
        """
        Helper function to parse Nmap result data and extract discovered devices.

        Parameters:
            result (str | dict): The raw Nmap scan result or a dictionary containing raw_output.

        Returns:
            list: A list of dictionaries, each containing device details (IP, MAC, Vendor, OS Version).
        """
        devices = []
        device_map = {}  # Use a map to avoid duplicates and consolidate data

        # Check if result is a string or dictionary
        if isinstance(result, str):
            lines = result.split("\n")  # Directly split string
        elif isinstance(result, dict):
            raw_output = result.get("raw_output", "")
            if isinstance(raw_output, str):
                lines = raw_output.split("\n")  # Split raw_output if it's a string
            else:
                lines = []  # Fallback to empty if raw_output is not a string
        else:
            lines = []  # Fallback to empty if result is neither string nor dict

        current_ip = None
        current_mac = None
        vendor = "Unknown"
        os_version = "Unknown"

        for line in lines:
            if line.startswith("Nmap scan report for"):
                # Extract IP or hostname
                current_ip = line.split("for")[1].strip()
                if "(" in current_ip and ")" in current_ip:
                    current_ip = current_ip.split("(")[-1].strip(")")
            elif "MAC Address" in line:
                # Extract MAC address and vendor
                parts = line.split("MAC Address: ")
                if len(parts) > 1:
                    mac_info = parts[1].split(" ", 1)
                    current_mac = mac_info[0]
                    vendor = mac_info[1].strip("()") if len(mac_info) > 1 else "Unknown"
            elif "OS details" in line:
                # Extract detailed OS information
                os_version = line.split("OS details:")[1].strip()
            elif "Running:" in line:
                # Extract running OS
                os_version = line.split("Running:")[1].strip()

            # Append or update device details when IP is found
            if current_ip:
                if current_ip not in device_map:
                    device_map[current_ip] = {
                        "ip": current_ip,
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
                current_ip, current_mac, vendor, os_version = None, None, "Unknown", "Unknown"

        # Convert map to list
        devices = list(device_map.values())
        return devices

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

        # Add vulnerability results entry
        vuln_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "vulnerability_results": vulnerability_results
        }
        
        success = json_manager.append_to_json_array(
            json_file,
            "scans",
            vuln_entry,
            schema_type="scan_result"
        )

        if success:
            self.generate_html_from_json(ssid)
            print(f"[INFO] Vulnerability results appended and HTML updated for SSID: {ssid}")
        else:
            print(f"[ERROR] Failed to append vulnerability results for SSID: {ssid}")
