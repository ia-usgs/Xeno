from attacks.recon import Recon
from utils.logger import Logger

class ReconService:
    def __init__(self, logger=None):
        self.logger = logger or Logger(log_file="logs/scan.log")
        self.recon = Recon(logger=self.logger)

    def enrich_devices(self, raw_output, ip_list):
        devices = []
        for ip in ip_list:
            os_ver = self.recon.detect_os(ip)
            # fallback if Nmap timed out or returned None
            if os_ver is None or "timed out" in raw_output.lower():
                self.logger.log(f"[WARNING] OS detection timed out or returned None for {ip}. Defaulting to 'Timeout'.")
                os_ver = "Timeout"

            # parse MAC/vendor from the raw output
            mac = "Unknown"
            vendor = "Unknown"
            for line in raw_output.splitlines():
                if f"Nmap scan report for {ip}" in line:
                    for nl in raw_output.splitlines():
                        if "MAC Address" in nl:
                            parts = nl.split()
                            mac = parts[2]
                            vendor = " ".join(parts[3:]).strip("()")
                            break
                    break

            devices.append({
                "ip": ip,
                "mac": mac,
                "vendor": vendor,
                "os_version": os_ver
            })

        self.logger.log(f"[INFO] Recon enriched {len(devices)} device(s).")
        return devices
