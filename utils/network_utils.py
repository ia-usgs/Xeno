"""
Network utilities module for Xeno project.

This module provides network-related utility functions such as
MAC address manipulation and network interface management.
"""

import subprocess


def change_mac_address(logger):
    """
    Change the MAC address of the `wlan0` interface.

    Parameters:
        logger (Logger): Logger for recording progress and errors.

    Workflow:
        1. Brings the `wlan0` interface down.
        2. Uses `macchanger` to randomly set a new MAC address.
        3. Brings the interface back up.

    Raises:
        subprocess.CalledProcessError: If any command fails during the process.
    """
    try:
        logger.log("[INFO] Changing MAC address for wlan0.")
        subprocess.run(["sudo", "ifconfig", "wlan0", "down"], check=True)
        subprocess.run(["sudo", "macchanger", "-r", "wlan0"], check=True)
        subprocess.run(["sudo", "ifconfig", "wlan0", "up"], check=True)
        logger.log("[SUCCESS] MAC address changed successfully.")
    except subprocess.CalledProcessError as e:
        logger.log(f"[ERROR] Failed to change MAC address: {str(e)}")


def get_local_ip(wifi_manager):
    """
    Get the local IP address of the wireless interface.

    Parameters:
        wifi_manager (WiFiManager): The WiFi manager instance.

    Returns:
        str or None: The local IP address or None if not found.
    """
    try:
        # grab the IP assigned to our wireless interface
        out = subprocess.run(
            ["ip", "addr", "show", wifi_manager.interface],
            stdout=subprocess.PIPE, text=True, check=True
        ).stdout
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                # format is "inet 192.168.X.Y/24"
                return line.split()[1].split("/")[0]
    except Exception:
        return None
    
    return None