# DESCRIPTION: Performs a DNS lookup using the provided domain.
# --- GLADOS SKILL: skill_network_search.py ---

import socket
import time
import os

def skill_network_search(domain):
    """
    Performs a DNS lookup using the provided domain.
    
    Args:
    domain (str): The domain to perform the DNS lookup on.
    
    Returns:
    str: The IP address associated with the provided domain.
    """
    
    # Perform DNS lookup
    try:
        ip_address = socket.gethostbyaddr(domain)[0]
    except socket.herror:
        ip_address = "Unable to resolve domain"
    
    # Return the result
    return ip_address

def skill_get_system_uptime():
    """
    Retrieves the system uptime in seconds.
    
    Returns:
    int: The system uptime in seconds.
    """
    
    # Return system uptime in seconds
    return int(time.time() - os.utime([ "/".join(os.getcwd().split("/")) ])[0])
    
def skill_list_files_by_size(filename):
    """
    Retrieves the size of each file in the specified directory and returns them as a list.
    
    Args:
    filename (str): The directory to retrieve file sizes from.
    
    Returns:
    list: A list of file sizes in bytes.
    """
    
    # Initialize the size list
    size_list = []
    
    # Iterate over each file in the directory
    for entry in os.scandir(filename):
        # If the entry is a file
        if entry.isFile():
            # Append its size to the list
            size_list.append(entry.stat().st_size)
    
    # Return the size list
    return size_list

def skill_create_file_with_random_content(filename, char_set):
    """
    Creates a file with random content from the provided character set.
    
    Args:
    filename (str): The file to create.
    char_set (str): The character set to draw from.
    
    Returns:
    str: The generated content.
    """
    
    # Initialize the content generator
    generated_content = ""
    
    # Generate random content
    for _ in range(100):  # Generate 100 characters
        generated_content += char_set[random.randint(0, len(char_set) - 1)]
    
    # Open the file and write the content
    with open(filename, "w") as file:
        try:
            file.write(generated_content)
        except Exception as error:
            print(f"Generated content was invalid, unable to write to file. Skipping...")
    
    # Return the filename for future use
    return filename

# Example usage
print("System uptime: ", skill_get_system_uptime(), "seconds")
print("File sizes: ", skill_list_files_by_size("/"))
print(skill_create_file_with_random_content("random_text.txt", "abcdefghijklmnopqrstuvwxyz"))
print(skill_network_search("google.com"))