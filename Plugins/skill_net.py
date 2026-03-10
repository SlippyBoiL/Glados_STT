# DESCRIPTION: Waits for a service to be available on a port with a specified delay.
# --- GLADOS SKILL: skill_net.py ---

import time
import os

def wait_for_service(port, delay=1):
    """Wait for a service to be available on a port

    Args:
        port (int): The port to listen on
        delay (int): The delay in seconds between checks

    Returns:
        bool: Whether the service is available
    """
    start_time = time.time()
    while time.time() - start_time < 300:
        if is_port_available(port):
            return True
        time.sleep(delay)
    return False

def is_port_available(port):
    """Check if a port is available

    Args:
        port (int): The port to check

    Returns:
        bool: Whether the port is available
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    return sock.connect_ex(("localhost", port)) == 0

def main():
    # Get a list of open ports
    ports = set()
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.listen(1)
        while True:
            client, _ = s.accept()
            ports.add(client.socket.getsockname()[1])

    # Find the available port
    for port in ports:
        if port > 1024 and port < 65536:
            print(f"Available port: {port}")
            break

if __name__ == "__main__":
    main()


This script creates a new utility that scans all open ports on the localhost and finds the first available one above 1024 and below 65536. Note that this script is not a high-quality one as it uses low-level networking code.