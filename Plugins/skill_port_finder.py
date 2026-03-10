# DESCRIPTION: A Python script used to find available ports on a local machine, commonly used for network programming and development.
# --- GLADOS SKILL: skill_port_finder.py ---

# skill_unique_port_finder.py

import socket

def find_available_port():
    """Find an available port between 1024 and 65535."""
    port = 1024
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.bind(('localhost', port))
            sock.close()
            return port
        except socket_ERROR:
            port += 1

def check_port_availability(port):
    """Check if a port is available."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect(('localhost', port))
        sock.close()
        return False
    except socket_error:
        return True

def main():
    port = find_available_port()
    while not check_port_availability(port):
        port = find_available_port()
    print(f"Port {port} is available.")

if __name__ == "__main__":
    main()