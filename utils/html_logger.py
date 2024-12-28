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
        return json_file

    def generate_html_from_json(self, ssid):
        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        html_file = os.path.join(self.output_dir, f"{ssid}.html")

        if not os.path.exists(json_file):
            print(f"[WARNING] No JSON file found for SSID: {ssid}. Cannot generate HTML log.")
            return

        with open(json_file, "r") as file:
            data = json.load(file)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Wi-Fi Scan Log for SSID: {ssid}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .scan-entry {{ margin-bottom: 20px; padding: 10px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; }}
                .scan-summary {{ margin-bottom: 20px; background-color: #eaf7ff; border: 1px solid #ddd; border-radius: 5px; padding: 10px; }}
                table {{ width: 100%; border-collapse: collapse; }}
                th, td {{ text-align: left; padding: 8px; border: 1px solid #ddd; }}
                th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <h1>Wi-Fi Scan Log for SSID: {ssid}</h1>
        """

        for scan in data["scans"]:
            html_content += f"""
            <div class="scan-summary">
                <h2>Scan Summary</h2>
                <p><b>Scan Conducted At:</b> {scan['timestamp']}</p>
            """
            if "result" in scan:
                html_content += """
                <h3>Discovered Devices</h3>
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
                # Properly call _parse_nmap_result to parse discovered devices
                discovered_devices = self._parse_nmap_result(scan["result"])
                for device in discovered_devices:
                    html_content += f"""
                    <tr>
                        <td>{device.get('ip', 'Unknown')}</td>
                        <td>{device.get('mac', 'Unknown')}</td>
                        <td>{device.get('vendor', 'Unknown')}</td>
                        
                    </tr>
                    """
                html_content += "</tbody></table>"

            if "vulnerability_results" in scan:
                html_content += """
                <h3>Vulnerability Details</h3>
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
                    html_content += f"""
                    <tr>
                        <td>{scan['vulnerability_results'].get('target', 'Unknown')}</td>
                        <td>{vuln.get('port', 'Unknown')}</td>
                        <td>{vuln.get('name', 'Unknown')}</td>
                        <td>{vuln.get('version', 'Unknown')}</td>
                        <td>{self._parse_exploit_titles(vuln.get('vulnerabilities', 'No Exploits'))}</td>
                        <td>{self._parse_exploit_paths(vuln.get('vulnerabilities', 'No Paths'))}</td>
                        
                    </tr>
                    """
                html_content += "</tbody></table>"

            html_content += "</div>"

        html_content += """
        </body>
        </html>
        """

        with open(html_file, "w") as file:
            file.write(html_content)

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
