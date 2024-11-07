import asyncio
import nmap

async def perform_advanced_nmap_scan(target_ip):
    nm = nmap.PortScanner()
    try:
        nm.scan(target_ip, arguments="-A --script vuln -T4")
        scan_data = []
        for host in nm.all_hosts():
            if nm[host].state() == 'up':
                open_ports = [port for port in nm[host].all_tcp() if nm[host].tcp(port).get('state') == 'open']
                os_family = nm[host].get('osclass', [{}])[0].get('osfamily', 'Unknown')
                vulnerabilities = nm[host].get('hostscript', [])
                scan_data.append({
                    "ip": host,
                    "open_ports": open_ports,
                    "os": os_family,
                    "vulnerabilities": vulnerabilities
                })
        return scan_data
    except Exception as e:
        log_error("Nmap Advanced Scan", "Failed to perform advanced Nmap scan", e)
        return None
