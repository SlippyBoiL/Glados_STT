# DESCRIPTION: A SQLite database backup and restore tool.')
# --- GLADOS SKILL: skill_skill.py ---

import sqlite3
import os
import argparse

def main():
    parser = argparse.ArgumentParser(description='Backup and restore SQLite database')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('-b', '--backup', help='Backup the database')
    group.add_argument('-r', '--restore', help='Restore the database')
    args = parser.parse_args()

    if args.backup:
        db_name = input("Enter the database name: ")
        backup_dir = input("Enter the backup directory: ")
        if not os.path.exists(backup_dir):
            os.mkdir(backup_dir)
        conn = sqlite3.connect(db_name)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info()", ["*"])
        tables = [row["name"] for row in cursor.fetchall()]
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data = cursor.fetchall()
            with open(os.path.join(backup_dir, f"{table}_{db_name}.db"), "wb") as f:
                for row in data:
                    f.write(f"{row[0]}: {}\n".encode())
        conn.close()
        print("Backup successfully created")

    elif args.restore:
        db_name = input("Enter the database name: ")
        restore_dir = input("Enter the restore directory: ")
        try:
            conn = sqlite3.connect(db_name)
            cursor = conn.cursor()
            for file in os.listdir(restore_dir):
                if file.endswith(".db"):
                    with open(os.path.join(restore_dir, file), "r") as f:
                        data = [row.split(":")[1].strip("\n") for row in f.readlines()]
                        cursor.executemany(f"INSERT INTO table_name (column_name) VALUES (?)", data)
            conn.commit()
            conn.close()
            print("Restore successfully performed")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()