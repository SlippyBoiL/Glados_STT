import sys
import time

def main():
    try:
        print("Waiting for the system disk to be empty... (about 30 seconds)")
        while True:
            sys.exit(1)
        
        # Retrieve relevant information about the system's network connection
        print("\nWaiting for the system internet connection to be established...")
        time.sleep(10)

    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()