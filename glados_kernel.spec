# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

# PyInstaller spec execution may not define `__file__`.
# We build from the repo root, so use CWD as the project directory.
project_dir = Path.cwd()

datas = []

# Core configs
datas.append((str(project_dir / "configs"), "configs"))

# Skills + runtime scripts live under `plugins_dir` (defaults to "plugins")
datas.append((str(project_dir / "Plugins"), "plugins"))

# Memory package (static JSON + retrieval helpers)
datas.append((str(project_dir / "memory"), "memory"))

# Optional dashboard code (not imported by kernel, but useful for debugging)
datas.append((str(project_dir / "dashboard"), "dashboard"))

# Piper model assets
datas.append((str(project_dir / "glados.onnx"), "."))
datas.append((str(project_dir / "glados.onnx.json"), "."))

# Audio assets
datas.append((str(project_dir / "local_glados_response.wav"), "."))
datas.append((str(project_dir / "glados_response.wav"), "."))

# Screen placeholder image (vision thread overwrites it)
if (project_dir / "Plugins" / "visual_buffer.png").exists():
    datas.append((str(project_dir / "Plugins" / "visual_buffer.png"), "plugins"))

block_cipher = None

a = Analysis(
    ["KernelLamma.py"],
    pathex=[str(project_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GladosKernel",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="GladosKernel",
)

