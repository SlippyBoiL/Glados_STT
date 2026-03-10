# DESCRIPTION: A utility function to copy entire tree from source directory to destination directory.
# --- GLADOS SKILL: skill_copy_tree.py ---

import os
import shutil
import time

def skill_copy_tree(src, dst):
    """
    Copy an entire tree from source directory to destination directory.
    """
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        item_path = os.path.join(src, item)
        if os.path.isfile(item_path):
            shutil.copy2(item_path, dst)
        elif os.path.isdir(item_path):
            skill_copy_tree(item_path, os.path.join(dst, item))


def skill_delete_tree(path):
    """
    Recursively delete an entire tree in the given path.
    """
    if not os.path.exists(path):
        return
    for item in os.listdir(path):
        item_path = os.path.join(path, item)
        if os.path.isfile(item_path):
            os.remove(item_path)
        elif os.path.isdir(item_path):
            os.chmod(item_path, 0o222)  # Make the directory writable
            skill_delete_tree(item_path)
    os.rmdir(path)


def skill_empty_directory(path):
    """
    Empty a given directory.
    """
    shutil.rmtree(path)


def skill_generate_temp_directory():
    """
    Generate a temporary directory path.
    """
    temp_dir = '/tmp/temp_' + str(int(time.time() * 1000))
    return temp_dir


def skill_list_directory(path):
    """
    List the files and directories in a given path.
    """
    files_and_directories = [file for file in os.listdir(path)]
    return files_and_directories


def skill_move_files(src, dst):
    """
    Move all files from the source directory to the destination directory.
    """
    files_and_directories = skill_list_directory(src)
    for file in files_and_directories:
        src_path = os.path.join(src, file)
        dst_path = os.path.join(dst, file)
        shutil.move(src_path, dst_path)


def main():
    # Test the script
    src_dir = 'test_directory'
    dst_dir = 'test_directory_copy'
    skill_copy_tree(src_dir, dst_dir)
    print("Copied tree to:", dst_dir)
    skill_empty_directory(src_dir)
    print("Removed original directory:", src_dir)
    skill_list_directory(src_dir)
    skill_move_files(src_dir, dst_dir)
    print("Moved files from:", src_dir, "to:", dst_dir)


if __name__ == "__main__":
    main()