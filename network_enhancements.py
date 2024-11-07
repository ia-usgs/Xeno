import nmap
import subprocess
from scapy.all import sniff, ARP
from utils import log_error

# Initialize Nmap scanner
nm = nmap.PortScanner()

def scan_ports(ip):
    """Scans common ports on the given IP address."""
    print(f"Starting port scan on {ip} (ports 1-1024)...")
    try:
        nm.scan(ip, arguments="-p 1-1024")
        open_ports = [port for port in nm[ip].all_tcp() if nm[ip].tcp(port)['state'] == 'open']
        print(f"Completed port scan on {ip}. Open ports: {open_ports}")
        return open_ports
    except Exception as e:
        log_error("Port Scan", f"Error scanning ports on {ip}", e)
        return None

def fingerprint_os_service(ip):
    """Performs OS and service version detection."""
    print(f"Starting OS and service fingerprinting on {ip}...")
    try:
        nm.scan(ip, arguments="-O -sV")
        os_info = nm[ip].get('osclass', [{}])[0].get('osfamily', 'Unknown')
        services = [(port, nm[ip].tcp(port)['name'], nm[ip].tcp(port).get('version', 'Unknown'))
                    for port in nm[ip].all_tcp() if nm[ip].tcp(port)['state'] == 'open']
        print(f"Completed OS and service fingerprinting on {ip}. OS: {os_info}, Services: {services}")
        return {"os_info": os_info, "services": services}
    except Exception as e:
        log_error("Fingerprinting", f"Error fingerprinting OS and services on {ip}", e)
        return None

def vulnerability_scan(ip):
    """Scans for known vulnerabilities on open services."""
    print(f"Starting vulnerability scan on {ip}...")
    try:
        nm.scan(ip, arguments="--script vuln")
        vulnerabilities = nm[ip].get('hostscript', [])
        print(f"Completed vulnerability scan on {ip}. Vulnerabilities: {vulnerabilities}")
        return vulnerabilities
    except Exception as e:
        log_error("Vulnerability Scan", f"Error during vulnerability scan on {ip}", e)
        return None

def test_weak_credentials(ip, service, username, password_list):
    """Attempts weak credentials against a specific service on the IP."""
    print(f"Testing weak credentials on {ip} for {service} service...")
    try:
        for password in password_list:
            result = subprocess.run(["hydra", "-l", username, "-p", password, f"{service}://{ip}"], capture_output=True)
            if "login successful" in result.stdout.decode():
                print(f"Weak credentials found on {ip}: {username}/{password}")
                return {"username": username, "password": password}
        print(f"No weak credentials found on {ip} for {service}")
        return None
    except Exception as e:
        log_error("Credential Test", f"Error testing credentials on {ip}", e)
        return None

def capture_network_traffic(duration=10):
    """Captures network traffic for a specified duration."""
    print(f"Capturing network traffic for {duration} seconds...")
    packets = sniff(timeout=duration)
    print(f"Captured network traffic summary:\n{packets.summary()}")
    return packets.summary()

def test_isolation(ip):
    """Tests for ARP spoofing to check if isolation can be bypassed."""
    print(f"Testing network isolation by checking for ARP spoofing from {ip}...")
    def spoof(pkt):
        if pkt.haslayer(ARP) and pkt[ARP].psrc == ip:
            print(f"ARP packet detected from {ip}: {pkt[ARP].hwsrc}")
    sniff(filter="arp", prn=spoof, timeout=10)
    print("Completed isolation test.")

def detect_rogue_services(ip, uncommon_ports="1025-65535"):
    """Scans uncommon ports to detect potential rogue services."""
    print(f"Scanning uncommon ports on {ip} for rogue services (ports {uncommon_ports})...")
    try:
        nm.scan(ip, arguments=f"-p {uncommon_ports}")
        open_ports = [port for port in nm[ip].all_tcp() if nm[ip].tcp(port)['state'] == 'open']
        services = {port: nm[ip].tcp(port).get('name', 'Unknown') for port in open_ports}
        print(f"Completed rogue service detection on {ip}. Rogue services: {services}")
        return services
    except Exception as e:
        log_error("Rogue Service Detection", f"Error detecting rogue services on {ip}", e)
        return None
