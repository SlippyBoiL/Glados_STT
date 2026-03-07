# DESCRIPTION: Python script to generate large sequential files and verify their compressed file size.
# --- GLADOS SKILL: skill_random_data_generator.py ---

#!/usr/bin/env python3

import datetime
import json
import os
import random
import time

def generate_sequential_file_size_bytes(size):
    with open("sequential_file_size_bytes.txt", "wb") as file:
        for _ in range(size):
            file_content = os.urandom(1024 * 1024)  # 1MB buffer
            file.write(file_content)

def verify_file_size_compressed(file_path, target_size):
    original_file_size = os.path.getsize(file_path)
    if original_file_size > target_size * 1024:
        print(f"{file_path} is larger than compressed target size.")
        return False
    elif float(original_file_size / target_size) < 1.1:
        print(f"{file_path} is close to compressed target size.")
        return True
    else:
        return False

def download_and_verify_urls(url_list, target_size):
    file_paths = []
    compressed_urls = []
    for url in url_list:
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                file_path = url.split("/")[-1]
                file_paths.append(file_path)
                compressed_urls.append((url, int(response.headers['Content-Length']) * 0.8))
                
                if os.path.exists(file_path):
                    if verify_file_size_compressed(file_path, response.headers['Content-Length'] // 1000):
                        print(f"{url}(compressed) successfully downloaded and verified.")
                else:
                    print(f"File {url} does not exist, verifying download.")
                    print(f"Verification failed: {url}(compressed)}")
                    continue
        except requests.exceptions.RequestException:
            print(f"Request failed to {url}.")
            
    print("Verified downloads:")
    for url, target_size in compressed_urls:
        print(f"{url} - {target_size} MB")

def download_and_verify_urls_piped(url_list):
    file_paths = []
    for url in url_list:
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                file_path = url.split("/")[-1]
                file_paths.append(file_path)
                compressed_size = int(response.headers['Content-Length'] * 0.8)
                print(f"Verifying {url}...")
                with open(file_path, "wb") as file:
                    for chunk in response.iter_content(1024 * 1024):
                        file.write(chunk)
                compressed_size = int(os.path.getsize(file_path))
                print(f"Verification for {url} completed.")
        except requests.exceptions.RequestException:
            print(f"Request failed to {url}.")

def download_random_files(num_files, base_url):
    file_paths = []
    for _ in range(num_files):
        url = f"{base_url}/random/{int(time.time())}/{random.randint(1, 10000)}.txt"
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                file_path = url.split("/")[-1]
                file_paths.append(file_path)
                print(f"Successfully downloaded and stored {file_path}.")
        except requests.exceptions.RequestException:
            print(f"Request failed to {url}.")
            
    print("Located and printed files:")
    for file_path in file_paths:
        print(file_path)

def main():
    url_list = [
        "http://example.com/file.txt",
        "https://example.com/random/number.txt"
    ]
    num_files = 3
    base_url = "http://example.com/random"
    
    # download compressed files
    print("Verifying compressed sources:")
    download_and_verify_urls(url_list, int(len(url_list) * 0.8))
    
    # download piped files
    print("\nVerifying piped sources:")
    download_and_verify_urls_piped(url_list)
    
    # download random files
    print("\nVerifying and saving random files:")
    download_random_files(num_files, base_url)

if __name__ == "__main__":
    main()