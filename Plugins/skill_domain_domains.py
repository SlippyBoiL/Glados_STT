# DESCRIPTION: A script that lists domains known to the system by known hostnames or reverse IP lookup.
# --- GLADOS SKILL: skill_domain_domains.py ---

# skill_listed_domains.py

import os
import socket

def get_domain_info():
    """Parses domain information from host IP"""
    try:
        ip = socket.gethostbyname('localhost')
    except socket.gaierror:
        return None
    dom = socket.getfqdn(socket.gethostname())
    return {ip: dom}

def listed_domains():
    """Lists all domains known to the system, either by known hostnames or by reverse IP lookup."""
    global_list = set(get_domain_info())
    domain_list = set()
    
    for socket_file_path in os.listdir('/var/lib/nsswitch.conf'):
        domain_list.add(socket_file_path)
        
    for host, domain in global_list.items():
        try:
            os.system(f'cat /etc/hosts|grep {host} > /dev/null')
        except Exception as e:
            continue
        # Ignore localhost and loopback for simplicity
        if host not in ['127.0.0.1', 'localhost'] and domain != host:
            domain_list.add(domain)
            
    return domain_list

# example usage
if __name__ == "__main__":
    domains = listed_domains()
    print(domains)