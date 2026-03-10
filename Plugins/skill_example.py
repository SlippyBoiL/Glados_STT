# DESCRIPTION: This is a {file_name_without_extension} script."
# --- GLADOS SKILL: skill_example.py ---

import os

def find_and_duplicate_files():
    # Get a list of current files in the working directory
    current_files = [os.path.join(os.getcwd(), file) for file in os.listdir(os.getcwd()) if os.path.isfile(os.path.join(os.getcwd(), file))]

    # Initialize an empty dictionary to track duplicitive files
    duplicate_files = {}

    # Iterate over the list of current files
    for file in current_files:
        # Open the current file
        with open(file, 'r') as current_file:
            # Read the content of the current file
            current_content = current_file.read()

        # Open the file with the same name in another directory
        duplicate_file_path = os.path.join(os.getcwd(), '.files' + os.path.basename(file))
        if(os.path.exists(duplicate_file_path)):
            with open(duplicate_file_path, 'r') as os_duplicate_file:
                os_duplicate_content = os_duplicate_file.read()

        # If the file exists in a different directory, track the duplication
        if duplicate_file_path and current_content == os_duplicate_content:
            filename = os.path.basename(file)
            if filename not in duplicate_files:
                duplicate_files[filename] = {}
            duplicate_files[filename]["path"] = file
            duplicate_files[filename]["os_path"] = duplicate_file_path
            duplicate_files[filename]["content"] = current_content

    # If files are not duplicated, return a message
    if not duplicate_files:
        print("No duplicate files found.")
    else:
        for filename, duplicate_file_data in duplicate_files.items():
            duplicate_files_data = {
                "duplicate": duplicate_file_data,
                "original": {
                    "path": f"{filename} (Original)",
                    "content": current_content
                }
            }
            print(f"The duplicated file: {filename} was found with the duplicate file:")
            for duplicate_file in duplicate_files_data["duplicate"]["content"]:
                print(f"Duplicated file path: {duplicate_file}")
                print(f"Duplicated file content: {duplicate_file_data['content']}")
                print(f"Original file path: {duplicate_file_data['original']['path']}")
                print(f"Original file content: {duplicate_files_data['original']['content']}")


# Call the function
find_and_duplicate_files()