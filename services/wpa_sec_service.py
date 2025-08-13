"""
wpa_sec_service.py
====================

This module provides a simple client for interacting with the WPA‑Sec
service (https://wpa-sec.stanev.org).  It allows uploading captured
WPA handshake files and downloading a potfile of cracked passwords.
The code is adapted from a Pwnagotchi plugin and modified to fit
the Xeno project's architecture.  To use this service you must
provide a valid API key issued by the WPA‑Sec site (see their
"Get key" page for details).  The default API URL points to the
public WPA‑Sec instance but can be overridden in the configuration.
"""

import os
import requests
from typing import Dict, Optional


class WpaSecService:
    """Client for uploading handshakes and downloading cracked passwords from WPA‑Sec."""

    def __init__(self, api_key: str, api_url: str = "https://wpa-sec.stanev.org") -> None:
        if not api_key:
            raise ValueError("API key must be provided for WPA‑Sec integration.")
        self.api_key = api_key
        # Remove trailing slash to avoid double slashes when constructing URLs
        self.api_url = api_url.rstrip('/')

    def upload_handshake(self, cap_path: str, timeout: int = 60) -> bool:
        """
        Upload a .cap file containing a captured handshake to WPA‑Sec.

        Parameters:
            cap_path (str): The path to the .cap file to upload.
            timeout (int): How long to wait (in seconds) for the HTTP
                request to complete.  Adjust if you expect large files
                or slow connections.

        Returns:
            bool: True if the upload succeeded (and the file was
                accepted), False otherwise.  A return of False may
                indicate the file was already submitted or that an
                error occurred.
        """
        if not os.path.exists(cap_path):
            return False

        # Use a cookie named 'key' to pass the API key, as required by WPA‑Sec.
        cookies = {"key": self.api_key}
        with open(cap_path, 'rb') as fh:
            files = {"file": fh}
            try:
                response = requests.post(self.api_url, cookies=cookies, files=files, timeout=timeout)
                # A successful upload returns HTTP 200.  WPA‑Sec will
                # respond with a page that may include the phrase
                # "already submitted" if the handshake was previously
                # uploaded.  In that case we treat it as a non‑fatal
                # condition and return False to indicate no new work.
                if response.status_code == 200:
                    if 'already submitted' in response.text:
                        return False
                    return True
            except requests.RequestException:
                # Network errors or timeouts are silently ignored; the caller
                # can log and retry if desired.
                pass
        return False

    def download_potfile(self, dest_path: str, timeout: int = 60) -> bool:
        """
        Download the potfile containing cracked passwords from WPA‑Sec.

        Parameters:
            dest_path (str): Where to write the downloaded potfile.  If
                the request succeeds, this file will be overwritten.
            timeout (int): The maximum time to wait (in seconds) for
                the download to complete.

        Returns:
            bool: True if the potfile was downloaded and saved
                successfully, False otherwise.
        """
        # Build the download URL.  According to the WPA‑Sec API, appending
        # "?api&dl=1" triggers a download of the cracked passwords.
        url = f"{self.api_url}/?api&dl=1"
        cookies = {"key": self.api_key}
        try:
            response = requests.get(url, cookies=cookies, timeout=timeout)
            if response.status_code == 200:
                # Write binary content to dest_path
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, 'wb') as fh:
                    fh.write(response.content)
                return True
        except requests.RequestException:
            pass
        return False

    def parse_potfile(self, potfile_path: str) -> Dict[str, str]:
        """
        Parse a potfile and return a mapping of SSIDs to passwords.

        The potfile format is a colon‑separated list with four fields:
            bssid:station_mac:ssid:password

        If multiple entries exist for the same SSID, only the last
        entry is kept.  This assumes the last entry has the most
        up‑to‑date password.

        Parameters:
            potfile_path (str): Path to the potfile.  Must be a text
                file with UTF‑8 or ASCII encoding.

        Returns:
            dict: Mapping from SSID (str) to password (str).  If no
                entries are found the dictionary will be empty.
        """
        password_map: Dict[str, str] = {}
        if not os.path.exists(potfile_path):
            return password_map
        try:
            with open(potfile_path, 'r', encoding='utf-8', errors='ignore') as fh:
                for line in fh:
                    parts = line.strip().split(':')
                    # We expect at least four fields: bssid:station_mac:ssid:password
                    if len(parts) >= 4:
                        ssid = parts[2]
                        password = parts[3]
                        # Store/overwrite the password for this SSID
                        password_map[ssid] = password
        except OSError:
            pass
        return password_map
