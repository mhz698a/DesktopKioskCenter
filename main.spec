# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller onedir configuration for Windows deployments."""

import sys
sys.setrecursionlimit(5000)

from pathlib import Path

from pathlib import Path

block_cipher = None
project_root = Path(SPEC).resolve().parent

for required_file in ("main.py", "icon.png"):
    candidate = project_root / required_file
    if not candidate.is_file():
        raise FileNotFoundError(f"Required build input not found: {candidate}")

# Collect runtime assets only. Python modules under css/ are collected by Analysis
# through imports; stylesheets and SVGs remain regular data files.
css_dir = project_root / "css"
added_files = [
    (str(path), "css")
    for path in sorted(css_dir.iterdir())
    if path.is_file() and path.suffix.lower() in {".css", ".svg"}
]
added_files.extend([
    (str(project_root / "icon.png"), "."),
])

a = Analysis(
    [str(project_root / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=added_files,
    hiddenimports=[
        "wmain",
        "database",
        "utils",
        "const",
        "api_server",
        "pollstatus",
        "action_req",
        "user_record_dialog",
        "tabs.registered_user_editor",
        "tabs.access_logs.build",
        "tabs.access_logs.backend",
        "tabs.equipment.build",
        "tabs.equipment.backend",
        "tabs.equipment.bulk_dialog",
        "tabs.equipment.bulk_dlg_add",
        "tabs.external_users.build",
        "tabs.external_users.backend",
        "tabs.internal_students.build",
        "tabs.internal_students.backend",
        "tabs.received_logins.build",
        "tabs.received_logins.backend",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "tests", 
        "docs", 
        "cryptography", 
        "pygame", 
        "matplotlib", 
        "numpy", 
        "PIL", 
        "jinja2", 
        "IPython"
    ],
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
    name="DesktopKioskCenter",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(project_root / "icon.png"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="DesktopKioskCenter",
)
