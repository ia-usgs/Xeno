"""
Configuration loader module for Xeno project.

This module provides functions to load SSH and Wi-Fi credentials from
predefined configuration files in the project directory.
"""

import os
import json


def load_ssh_credentials():
    """
    Load SSH credentials from predefined paths in the project directory.

    Searches in the following order:
        - /home/pi/xeno/config/ssh_default_credentials.txt
        - /root/ssh_default_credentials.txt

    Returns:
        list: A list of dictionaries with SSH credentials, where each dictionary contains:
            - username (str): The username for SSH login.
            - password (str): The password for SSH login.

    Raises:
        Exception: If the file cannot be read or is improperly formatted.
    """
    potential_paths = [
        "/home/pi/xeno/config/ssh_default_credentials.txt",
        "/root/ssh_default_credentials.txt"
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            print(f"[INFO] Found SSH credentials at: {path}")
            credentials = []
            try:
                with open(path, "r") as file:
                    for line in file:
                        line = line.strip()
                        if line and ":" in line:
                            username, password = line.split(":", 1)
                            credentials.append({"username": username, "password": password})
                return credentials
            except Exception as e:
                print(f"[ERROR] Failed to load SSH credentials from {path}: {e}")
                return []
    
    print("[ERROR] No SSH credentials file found in config or root.")
    return []


def load_wifi_credentials():
    """
    Load Wi-Fi credentials from predefined paths in the project directory.

    Searches in the following order:
        - /home/pi/xeno/config/wifi_credentials.json
        - /root/wifi_credentials.json

    Returns:
        list: A list of dictionaries with Wi-Fi credentials, where each dictionary contains:
            - SSID (str): The Wi-Fi network name.
            - Password (str): The Wi-Fi network password.

    Raises:
        Exception: If the file cannot be read or is improperly formatted.
    """
    potential_paths = [
        "/home/pi/xeno/config/wifi_credentials.json",
        "/root/wifi_credentials.json"
    ]
    
    for path in potential_paths:
        if os.path.exists(path):
            print(f"[INFO] Found Wi-Fi credentials at: {path}")
            try:
                with open(path, "r") as file:
                    return json.load(file)
            except Exception as e:
                print(f"[ERROR] Failed to load Wi-Fi credentials from {path}: {e}")
                return []
    
    print("[ERROR] No Wi-Fi credentials file found in config or root.")
    return []