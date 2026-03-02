import os
import re
import json
from datetime import datetime


class HTMLLogger:
    def __init__(self, output_dir="utils/html_logs", json_dir="utils/json_logs"):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(json_dir, exist_ok=True)
        self.output_dir = output_dir
        self.json_dir   = json_dir
        # Path searched relative to cwd (works when run from the project root)
        self._known_devices_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "known_devices.json"
        )
        self._known_devices = None   # loaded lazily

    def save_scan_result_to_json(self, ssid, scan_result):
        json_file = os.path.join(self.json_dir, f"{ssid}.json")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if os.path.exists(json_file):
            with open(json_file, "r", encoding="utf-8", errors="replace") as file:
                data = json.load(file)
        else:
            data = {"ssid": ssid, "scans": []}

        data["scans"].append({"timestamp": timestamp, "result": scan_result})

        with open(json_file, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4)

        print(f"[INFO] Scan result saved to JSON: {json_file}")

        self.generate_html_from_json(ssid)  # keep regenerating on each write
        return json_file

    def append_passwords(self, ssid, pw_map):
        """
        Normalize and append WPA-Sec recovered passwords into the JSON log
        as a new scan 'result' entry with the key 'cracked_passwords'.

        pw_map can be any of:
          - { "SSID1": "password" }
          - { "SSID1": ["pwd1", "pwd2"] }  (first non-empty wins)
          - { "SSID1": {"password": "pwd", "bssid": "..."} }  (we extract .password)
          - mixed forms; unknown shapes are stringified.
        """
        try:
            # Normalize to {ssid: password}
            normalized = {}
            for k, v in (pw_map or {}).items():
                pwd = ""
                if isinstance(v, list):
                    # prefer first non-empty item
                    for item in v:
                        if item:
                            pwd = str(item)
                            break
                elif isinstance(v, dict):
                    pwd = v.get("password") or v.get("pwd") or v.get("pass") or ""
                    if not pwd and "value" in v:
                        pwd = str(v["value"])
                elif v is not None:
                    pwd = str(v)

                if pwd:
                    normalized[str(k)] = pwd

            if not normalized:
                print(f"[INFO] append_passwords: nothing to add for {ssid} (empty set after normalization).")
                return

            print(f"[INFO] Appending {len(normalized)} WPA-Sec password(s) for {ssid}")
            # Store as a scan result so your existing HTML renderer can pick it up
            self.save_scan_result_to_json(ssid, {"cracked_passwords": normalized})
        except Exception as exc:
            print(f"[WARN] append_passwords failed for {ssid}: {exc}")

    def _load_known_devices(self):
        """Lazily load config/known_devices.json. Returns dict {MAC: entry} or {}."""
        if self._known_devices is not None:
            return self._known_devices
        path = self._known_devices_path
        if not os.path.exists(path):
            self._known_devices = {}
            return {}
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                raw = json.load(f)
            # Normalise MAC keys to UPPER so comparisons are case-insensitive
            self._known_devices = {
                k.upper(): v for k, v in raw.get("devices", {}).items()
            }
        except Exception as exc:
            print(f"[WARN] Could not load known_devices.json: {exc}")
            self._known_devices = {}
        return self._known_devices

    def generate_html_from_json(self, ssid):
        json_file     = os.path.join(self.json_dir,   f"{ssid}.json")
        html_file     = os.path.join(self.output_dir, f"{ssid}.html")
        template_file = os.path.join("utils", "webInterface", "wifiLogTemplate.html")

        # 1) Load JSON data
        if not os.path.exists(json_file):
            print(f"[WARNING] No JSON file found for SSID: {ssid}. Cannot generate HTML log.")
            return
        with open(json_file, "r", encoding="utf-8", errors="replace") as f:
            data = json.load(f)

        # 2) Load HTML template
        if not os.path.exists(template_file):
            print(f"[ERROR] Template file not found: {template_file}. Cannot generate HTML log.")
            return
        with open(template_file, "r", encoding="utf-8") as f:
            wifi_log_template = f.read()

        # 3) Compute scan date range
        timestamps = [scan.get("timestamp") for scan in data.get("scans", []) if scan.get("timestamp")]
        if timestamps:
            first, last = timestamps[0], timestamps[-1]
            date_range = f"Scans conducted from {first} to {last}"
        else:
            date_range = "No scans have been conducted yet."

        # Summarise total handshakes captured.
        total_handshake_count = None
        for scan in data.get("scans", []):
            result = scan.get("result")
            if isinstance(result, dict) and "handshake_count" in result:
                total_handshake_count = result["handshake_count"]
        handshake_summary = ""
        if total_handshake_count is not None:
            handshake_summary = f"Total handshakes captured: {total_handshake_count}"

        # 4) Collect cracked passwords (from per-scan 'result.cracked_passwords')
        cracked_pw_map = {}
        for scan in data.get("scans", []):
            res = scan.get("result")
            if isinstance(res, dict):
                pw_dict = res.get("cracked_passwords", {})
                if isinstance(pw_dict, dict):
                    # Later entries override earlier (latest wins)
                    cracked_pw_map.update(pw_dict)

        # 5) Aggregate discovered devices across all scans
        device_map = {}
        for scan in data["scans"]:
            if "result" not in scan:
                continue
            for d in self._parse_nmap_result(scan["result"]):
                ip = d["ip"]
                if ip not in device_map:
                    device_map[ip] = {
                        "hostname": d.get("hostname", "Unknown"),
                        "mac":      d.get("mac",      "Unknown"),
                        "vendor":   d.get("vendor",   "Unknown")
                    }
                else:
                    # fill in missing info if we get it later
                    if device_map[ip]["hostname"] == "Unknown" and d.get("hostname"):
                        device_map[ip]["hostname"] = d["hostname"]
                    if device_map[ip]["mac"] == "Unknown" and d.get("mac"):
                        device_map[ip]["mac"] = d["mac"]
                    if device_map[ip]["vendor"] == "Unknown" and d.get("vendor"):
                        device_map[ip]["vendor"] = d["vendor"]

        # 5b) Filter device_map using known_devices.json.
        # - Devices whose home SSID == current ssid  → INCLUDED (IDENTIFIED)
        # - Devices whose home SSID == 'shared'      → INCLUDED (SHARED / infra)
        # - Devices with no entry in known_devices   → INCLUDED (VISITOR)
        # - Devices whose home SSID is a DIFFERENT ssid → EXCLUDED
        known = self._load_known_devices()
        if known:
            filtered = {}
            for ip, info in device_map.items():
                mac = info.get("mac", "Unknown").upper()
                entry = known.get(mac)
                if entry is None:
                    # Not registered — show as VISITOR in every report
                    info["_ownership"] = "visitor"
                    filtered[ip] = info
                elif entry.get("ssid", "").lower() == "shared":
                    info["_ownership"] = "shared"
                    filtered[ip] = info
                elif entry.get("ssid", "") == ssid:
                    info["_ownership"] = "home"
                    filtered[ip] = info
                # else: belongs to a different SSID — exclude silently
            device_map = filtered

        # 6) Prepare the cracked password table (if any).
        password_entries = ""
        pw_badge = ""
        if cracked_pw_map:
            pw_badge = f'<span class="badge badge-critical">&#x26A0; {len(cracked_pw_map)} COMPROMISED</span>'
            password_entries = """
        <h3>Cracked Passwords</h3>
        <table>
          <thead>
            <tr>
              <th>SSID</th>
              <th>Password</th>
            </tr>
          </thead>
          <tbody>
        """
            for ssid_key, pwd in sorted(cracked_pw_map.items()):
                safe_ssid = str(ssid_key).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                safe_pwd  = str(pwd).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                password_entries += f"\n            <tr><td>{safe_ssid}</td><td class=\"cell-critical\">{safe_pwd}</td></tr>"
            password_entries += "\n          </tbody>\n        </table>\n"
        else:
            pw_badge = '<span class="badge badge-safe">&#x2714; SECURE</span>'

        # 7) Build the scan_entries string — stats bar + device table
        device_count = len(device_map)
        hs_badge_class = "badge-info" if total_handshake_count else "badge-safe"
        hs_count_val   = total_handshake_count if total_handshake_count is not None else 0
        scan_entries  = f"""
        <div class="report-stats">
          <div class="rstat">
            <span class="badge badge-info">&#x1F4E1; {device_count} DEVICE{'S' if device_count != 1 else ''}</span>
          </div>
          <div class="rstat">
            <span class="badge {hs_badge_class}">&#x1F91D; {hs_count_val} HANDSHAKE{'S' if hs_count_val != 1 else ''}</span>
          </div>
          <div class="rstat">{pw_badge}</div>
          <div class="rstat rstat-date">{date_range}</div>
        </div>
        """
        scan_entries += password_entries
        scan_entries += """
        <table>
          <thead>
            <tr>
              <th>Status</th>
              <th>IP Address</th>
              <th>Hostname</th>
              <th>MAC Address</th>
              <th>Vendor</th>
              <th>Operating System</th>
            </tr>
          </thead>
          <tbody>
        """
        if device_map:
            for ip, info in device_map.items():
                vendor    = info['vendor']
                hostname  = info['hostname']
                mac       = info['mac']
                os_ver    = info.get('os_version', 'Unknown')
                ownership = info.get('_ownership', 'visitor')
                if ownership == 'home':
                    status_badge = '<span class="badge badge-info">IDENTIFIED</span>'
                elif ownership == 'shared':
                    status_badge = '<span class="badge badge-safe">SHARED</span>'
                else:  # visitor / unknown
                    status_badge = '<span class="badge badge-warning">VISITOR</span>'
                scan_entries += f"""
                <tr>
                  <td>{status_badge}</td>
                  <td>{ip}</td>
                  <td>{hostname}</td>
                  <td>{mac}</td>
                  <td>{vendor}</td>
                  <td>{os_ver}</td>
                </tr>
                """
        else:
            scan_entries += """
            <tr>
              <td colspan="6">Nothing detected in this run.</td>
            </tr>
            """
        scan_entries += "</tbody></table>\n"

        # 8) Aggregate vulnerabilities across all scans
        # Only read from scan['result']['vulnerability_results'] (current format).
        # The old top-level scan['vulnerability_results'] path is intentionally
        # ignored to prevent duplicate rows when both formats exist in the same file.
        vuln_map = {}

        for scan in data.get("scans", []):
            res = scan.get("result")
            if not isinstance(res, dict):
                continue
            vr_payload = res.get("vulnerability_results")

            if not vr_payload:
                continue

            # Normalize to a list of entries [{ip/target, vulnerabilities:[...]}, ...]
            entries = []
            if isinstance(vr_payload, list):
                entries = vr_payload
            elif isinstance(vr_payload, dict):
                entries = [vr_payload]
            else:
                continue

            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                # Support both 'ip' (current) and 'target' (legacy) keys
                target = entry.get("ip") or entry.get("target", "Unknown")
                for v in entry.get("vulnerabilities", []):
                    if not isinstance(v, dict):
                        continue
                    key = (
                        target,
                        v.get("port",    "Unknown"),
                        v.get("name",    "Unknown"),
                        v.get("version", "Unknown"),
                    )
                    if key not in vuln_map:
                        vuln_map[key] = {
                            "exploits": self._parse_exploit_titles(v.get("vulnerabilities", "")),
                            "paths":    self._parse_exploit_paths(v.get("vulnerabilities", "")),
                        }

        # 9) Build the Vulnerabilities table
        # Count risk levels for the section badge
        critical_count = 0
        warning_count  = 0
        safe_count     = 0
        for (_, _, svc, _), info in vuln_map.items():
            exploits = info['exploits']
            if exploits != "No Exploits":
                critical_count += 1
            elif svc in ("tcpwrapped", "unknown"):
                warning_count += 1
            else:
                safe_count += 1

        # Build a summary badge line for the vuln section
        vuln_summary_badges = ""
        if critical_count:
            vuln_summary_badges += f'<span class="badge badge-critical">&#x26A0; {critical_count} CRITICAL</span> '
        if warning_count:
            vuln_summary_badges += f'<span class="badge badge-warning">&#x26A0; {warning_count} WARNING</span> '
        if safe_count:
            vuln_summary_badges += f'<span class="badge badge-safe">&#x2714; {safe_count} SAFE</span> '
        if not vuln_map:
            vuln_summary_badges = '<span class="badge badge-safe">&#x2714; CLEAN</span>'

        vulnerability_entries = f'<div class="vuln-badge-bar">{vuln_summary_badges}</div>\n'
        vulnerability_entries += """
        <table>
          <thead>
            <tr>
              <th>Risk</th>
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
        if vuln_map:
            for (target, port, svc, ver), info in vuln_map.items():
                exploits = info['exploits']
                paths    = info['paths']
                if exploits != "No Exploits":
                    risk_badge = '<span class="badge badge-critical">CRITICAL</span>'
                elif svc in ("tcpwrapped", "unknown"):
                    risk_badge = '<span class="badge badge-warning">WARNING</span>'
                else:
                    risk_badge = '<span class="badge badge-safe">SAFE</span>'
                vulnerability_entries += f"""
                <tr>
                  <td>{risk_badge}</td>
                  <td>{target}</td>
                  <td>{port}</td>
                  <td>{svc}</td>
                  <td>{ver}</td>
                  <td>{exploits}</td>
                  <td>{paths}</td>
                </tr>
                """
        else:
            vulnerability_entries += """
            <tr>
              <td colspan="7">Nothing detected in this run.</td>
            </tr>
            """
        vulnerability_entries += "</tbody></table>\n"

        # 10) Inject data into the template
        content = (
            wifi_log_template
            .replace("{ssid}", ssid)
            .replace("{scan_entries}", scan_entries)
            .replace("{vulnerability_entries}", vulnerability_entries)
        )

        # 11) Write out the HTML
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(content)

        print(f"[INFO] HTML log updated: {html_file}")

    def _parse_nmap_result(self, result):
        """
        Helper function to parse Nmap result data and extract discovered devices using regex.
        """
        import re
        device_map = {}
        current_ip = None

        if isinstance(result, dict):
            raw_output = result.get("raw_output", "")
        else:
            raw_output = str(result)

        # Regex patterns
        ip_pattern = re.compile(r"Nmap scan report for (?:([^\s()]+)\s*\(([\d.]+)\)|([\d.]+))")
        mac_pattern = re.compile(r"MAC Address: ([0-9A-Fa-f:]+) \(([^)]+)\)")
        os_details_pattern = re.compile(r"OS details: (.*)")
        running_pattern = re.compile(r"Running: (.*)")

        for line in raw_output.splitlines():
            ip_match = ip_pattern.search(line)
            if ip_match:
                # If we were tracking an IP, save it before starting a new one
                if current_ip and current_ip in device_map:
                    pass # Handled by direct dict mutation
                
                hostname = ip_match.group(1) or ""
                current_ip = ip_match.group(2) or ip_match.group(3)

                if current_ip not in device_map:
                    device_map[current_ip] = {
                        "ip": current_ip,
                        "hostname": hostname or "Unknown",
                        "mac": "Unknown",
                        "vendor": "Unknown",
                        "os_version": "Unknown"
                    }
                continue

            if not current_ip:
                continue

            mac_match = mac_pattern.search(line)
            if mac_match:
                device_map[current_ip]["mac"] = mac_match.group(1)
                device_map[current_ip]["vendor"] = mac_match.group(2)
                continue

            os_match = os_details_pattern.search(line)
            if os_match and device_map[current_ip]["os_version"] == "Unknown":
                device_map[current_ip]["os_version"] = os_match.group(1).strip()
                continue
                
            run_match = running_pattern.search(line)
            if run_match and device_map[current_ip]["os_version"] == "Unknown":
                device_map[current_ip]["os_version"] = run_match.group(1).strip()
                continue

        return list(device_map.values())

    @staticmethod
    def _strip_ansi(text: str) -> str:
        """Remove ANSI/VT100 terminal escape sequences from a string."""
        return re.sub(r'\x1b\[[0-9;]*[mKHF]|\x1b\[K', '', text)

    def _parse_exploit_titles(self, vulnerabilities):
        if not vulnerabilities:
            return "No Exploits"
        vulnerabilities = self._strip_ansi(vulnerabilities)
        if "Exploit Title" in vulnerabilities:
            lines = vulnerabilities.split("\n")
            titles = []
            for line in lines:
                if "|" in line and not line.startswith("-"):
                    parts = line.split("|")
                    if "Exploit Title" not in parts[0]:  # Skip header
                        titles.append(parts[0].strip())
            if titles:
                return "<br>".join(titles)
        return "No Exploits"

    def _parse_exploit_paths(self, vulnerabilities):
        if not vulnerabilities:
            return "No Paths"
        vulnerabilities = self._strip_ansi(vulnerabilities)
        if "|" in vulnerabilities:
            lines = vulnerabilities.split("\n")
            paths = []
            for line in lines:
                if "|" in line and not line.startswith("-"):
                    parts = line.split("|")
                    if len(parts) > 1 and "Path" not in parts[1]:  # Skip header
                        paths.append(parts[1].strip())
            if paths:
                return "<br>".join(paths)
        return "No Paths"

    def append_vulnerability_results_to_html(self, ssid, vulnerability_results):
        """
        Append vulnerability results as a new scan entry and regenerate HTML.
        Writes exclusively to scan['result']['vulnerability_results'] to avoid
        duplicate rows in the aggregation step.
        """
        # Normalise: the caller may pass a single dict or a list of dicts.
        if isinstance(vulnerability_results, dict):
            # Old callers pass {target, vulnerabilities:[...]};
            # convert to the current list-of-{ip, ...} format.
            target = vulnerability_results.get("target", "Unknown")
            vuln_list = vulnerability_results.get("vulnerabilities", [])
            normalised = [{"ip": target, "vulnerabilities": vuln_list}]
        elif isinstance(vulnerability_results, list):
            normalised = vulnerability_results
        else:
            normalised = []

        self.save_scan_result_to_json(ssid, {"vulnerability_results": normalised})
        print(f"[INFO] Vulnerability results appended and HTML updated for SSID: {ssid}")

