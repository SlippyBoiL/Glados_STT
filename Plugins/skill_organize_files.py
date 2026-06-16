# DESCRIPTION: Organizes files in a folder into A-Z subfolders; defaults to the user's Downloads folder.
# --- GLADOS SKILL: skill_organize_files.py ---

from __future__ import annotations

import os
import shutil
from typing import Callable, Optional

ProgressFn = Optional[Callable[[str], None]]


def _notify(msg: str, on_progress: ProgressFn) -> None:
    line = (msg or "").strip()
    if not line:
        return
    print(f"[ORGANIZE] {line}")
    if on_progress:
        try:
            on_progress(line)
        except Exception:
            pass


def organize_directory_alphabetically(
    target_path: str | None = None,
    *,
    on_progress: ProgressFn = None,
    show_in_explorer: bool = True,
) -> str:
    """
    Organizes files in a target directory into A-Z subfolders.
    Defaults to the user's Downloads folder if target_path is None or 'downloads'.
    """
    if not target_path or str(target_path).strip().lower() in ("downloads", "download"):
        target_path = os.path.join(os.path.expanduser("~"), "Downloads")

    target_path = os.path.abspath(os.path.expanduser(str(target_path).strip()))

    if not os.path.exists(target_path):
        return (
            f"Error: The directory '{target_path}' does not exist. "
            "Are you imagining things again?"
        )

    if not os.path.isdir(target_path):
        return f"Error: '{target_path}' is not a folder."

    _notify(f"Opening folder on screen: {target_path}", on_progress)
    if show_in_explorer:
        try:
            os.startfile(target_path)
        except Exception as e:
            _notify(f"(Could not open Explorer: {e})", on_progress)

    moved_count = 0
    skipped_count = 0
    entries = [f for f in os.listdir(target_path)]
    _notify(f"Scanning {len(entries)} items in {target_path}", on_progress)

    for filename in entries:
        file_path = os.path.join(target_path, filename)

        if os.path.isdir(file_path):
            continue

        first_char = filename[0].upper()
        dest_folder = first_char if first_char.isalpha() else "#"
        dest_folder_path = os.path.join(target_path, dest_folder)

        if not os.path.exists(dest_folder_path):
            os.makedirs(dest_folder_path)
            _notify(f"Created folder: {dest_folder}/", on_progress)

        try:
            dest_file = os.path.join(dest_folder_path, filename)
            if os.path.exists(dest_file):
                skipped_count += 1
                _notify(f"Skipped (already exists): {filename}", on_progress)
                continue
            shutil.move(file_path, dest_file)
            moved_count += 1
            _notify(f"Moved {filename} → {dest_folder}/", on_progress)
        except Exception as e:
            skipped_count += 1
            _notify(f"Failed {filename}: {e}", on_progress)

    return (
        f"I have successfully organized {moved_count} files into alphabetical isolation. "
        f"{skipped_count} files resisted. The state of your '{target_path}' directory was "
        "frankly appalling, but I fixed it. You are welcome."
    )


def run_organize(target_path: str | None = None, on_progress: ProgressFn = None) -> str:
    """Entry point for direct_actions / CLI."""
    return organize_directory_alphabetically(
        target_path,
        on_progress=on_progress,
        show_in_explorer=True,
    )


if __name__ == "__main__":
    import sys

    path = sys.argv[1] if len(sys.argv) > 1 else None
    print(run_organize(path))
