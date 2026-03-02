import subprocess
import re
from utils.logger import Logger


def run_nmap_scan(target, logger=None):
    """
    Two-phase Nmap scan:
      Phase 1 — ARP ping scan (-sn -PR) for fast device discovery.
                 Reliably returns all live hosts with MAC addresses and vendors.
      Phase 2 — OS detection (-O) on the confirmed live IPs only.
                 Enriches the raw output with OS fingerprint data.

    Parameters:
        target (str): Subnet to scan (e.g. "192.168.1.0/24").
        logger (Logger, optional): Logger instance.

    Returns:
        dict:
            - discovered_ips (list): IP addresses found.
            - raw_output (str): Combined nmap output (discovery + OS data merged).
    """
    if logger is None:
        logger = Logger()

    # ── Phase 1: ARP ping scan ────────────────────────────────────────────────
    logger.log(f"[INFO] Phase 1 — ARP discovery scan on {target}")
    try:
        p1 = subprocess.run(
            ["sudo", "nmap", "-sn", "-PR", target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        discovery_output = p1.stdout
        logger.log(f"[DEBUG] Phase 1 output:\n{discovery_output}")
    except Exception as e:
        logger.log(f"[ERROR] Phase 1 ARP scan failed: {e}")
        return {"discovered_ips": [], "raw_output": ""}

    # Extract live IPs from phase 1 — handles both "hostname (IP)" and bare "IP"
    discovered_ips = re.findall(
        r"Nmap scan report for (?:\S+ \()?(\d+\.\d+\.\d+\.\d+)\)?",
        discovery_output
    )

    if not discovered_ips:
        logger.log("[WARNING] No hosts discovered in phase 1.")
        return {"discovered_ips": [], "raw_output": discovery_output}

    # ── Phase 2: OS detection on live hosts only ──────────────────────────────
    logger.log(f"[INFO] Phase 2 — OS detection on {len(discovered_ips)} live host(s)")

    # Build a map of IP -> OS string from phase 2
    os_map = {}
    try:
        p2 = subprocess.run(
            [
                "sudo", "nmap",
                "-O", "--osscan-guess",
                "-T4",
                "--host-timeout", "20s",
            ] + discovered_ips,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        os_output = p2.stdout
        logger.log(f"[DEBUG] Phase 2 output:\n{os_output}")

        # Parse OS details per IP from phase 2 output
        ip_pat = re.compile(r"Nmap scan report for (?:\S+ \()?(\d+\.\d+\.\d+\.\d+)\)?")
        os_pat = re.compile(r"(?:OS details|Running): (.*)")
        cur_ip = None
        for line in os_output.splitlines():
            m = ip_pat.search(line)
            if m:
                cur_ip = m.group(1)
            if cur_ip and cur_ip not in os_map:
                om = os_pat.search(line)
                if om:
                    os_map[cur_ip] = om.group(1).strip()

    except Exception as e:
        logger.log(f"[WARNING] Phase 2 OS detection failed (non-fatal): {e}")

    # ── Merge: inject OS lines into the phase 1 output ───────────────────────
    # After each host block in discovery_output, append an "OS details:" line
    merged_lines = []
    cur_ip = None
    ip_pat = re.compile(r"Nmap scan report for (?:\S+ \()?(\d+\.\d+\.\d+\.\d+)\)?")

    for line in discovery_output.splitlines():
        merged_lines.append(line)
        m = ip_pat.search(line)
        if m:
            cur_ip = m.group(1)
        # Inject OS line right after the "Host is up" line
        if cur_ip and cur_ip in os_map and "Host is up" in line:
            merged_lines.append(f"OS details: {os_map[cur_ip]}")

    merged_output = "\n".join(merged_lines)

    logger.log(f"[INFO] Nmap scan complete — {len(discovered_ips)} host(s) found.")
    return {
        "discovered_ips": discovered_ips,
        "raw_output": merged_output,
    }
