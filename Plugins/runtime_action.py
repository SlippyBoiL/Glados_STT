#!/usr/bin/env python3
"""
open_any_app.py – Launch any Windows application (executable, shortcut, or URL).

Usage:
    python open_any_app.py <identifier> [-- <extra arguments>]

Examples:
    python open_any_app.py r"C:\\Program Files\\Notepad++\\notepad++.exe"
    python open_any_app.py notepad++                     # searches %PATH% & Program Files
    python open_any_app.py "My App.lnk"                 # launches a shortcut
    python open_any_app.py notepad -- -n                # passes "-n" to notepad.exe
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from shutil import which

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
EXECUTABLE_EXTS = {".exe", ".bat", ".cmd", ".ps1", ".lnk", ".url"}


def is_executable(p: Path) -> bool:
    """Return True if *p* is a file with a known executable/shortcut extension."""
    return p.is_file() and p.suffix.lower() in EXECUTABLE_EXTS


def resolve_path(identifier: str) -> Path | None:
    """
    Resolve *identifier* to an absolute Path.

    Resolution order:
        1️⃣ Direct file path (absolute or relative, env‑var expanded)
        2️⃣ Search %PATH% (honouring PATHEXT)
        3️⃣ Shallow scan of common *Program Files* locations
    """
    # 1️⃣ Direct path (expand env vars and user home)
    candidate = Path(os.path.expandvars(os.path.expanduser(identifier))).resolve()
    if is_executable(candidate):
        return candidate

    # 2️⃣ Search %PATH%
    found = which(identifier)  # respects PATHEXT on Windows
    if found:
        found_path = Path(found).resolve()
        if is_executable(found_path):
            return found_path

    # 3️⃣ Scan common Program Files directories (depth ≤ 3)
    prog_dirs = [
        os.getenv("PROGRAMFILES"),
        os.getenv("PROGRAMFILES(X86)"),
        os.getenv("ProgramW6432"),
    ]
    prog_dirs = [Path(d) for d in prog_dirs if d]  # filter out None

    target = identifier.lower()
    target_stem = Path(target).stem  # strip possible extension

    for root in prog_dirs:
        try:
            for ext in EXECUTABLE_EXTS:
                pattern = f"**/*{ext}"
                for p in root.rglob(pattern):
                    if not p.is_file():
                        continue
                    # Match exact name or stem, case‑insensitive
                    if p.name.lower() == f"{target_stem}{ext}" or p.stem.lower() == target_stem:
                        # Limit depth: root + at most three subfolders
                        if len(p.relative_to(root).parts) <= 4:
                            return p.resolve()
        except Exception:
            # Permission errors or inaccessible directories are ignored
            continue
    return None


def launch(target: Path, extra_args: list[str]) -> None:
    """Launch *target* with optional *extra_args*."""
    try:
        if extra_args:
            # Use subprocess when we need to pass arguments
            subprocess.Popen([str(target)] + extra_args, shell=False)
        else:
            # os.startfile correctly handles .exe, .lnk, .url, etc. on Windows
            os.startfile(str(target))
        print(f"Launched: {target}")
    except Exception as e:
        sys.stderr.write(f"Failed to launch '{target}': {e}\n")
        sys.exit(1)


# ----------------------------------------------------------------------
# Main entry point
# ----------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Open any Windows application (executable, shortcut, or URL)."
    )
    parser.add_argument(
        "identifier",
        help="Application name, path, shortcut, or URL to launch.",
    )
    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Optional arguments passed to the launched program. "
             "If present, prepend them with '--' (e.g., -- -n).",
    )
    args = parser.parse_args()

    # Strip leading '--' if the user used it as a separator
    extra_args = args.extra
    if extra_args and extra_args[0] == "--":
        extra_args = extra_args[1:]

    target_path = resolve_path(args.identifier)
    if not target_path:
        sys.stderr.write(f"Could not locate application for identifier '{args.identifier}'.\n")
        sys.exit(1)

    launch(target_path, extra_args)


if __name__ == "__main__":
    main()