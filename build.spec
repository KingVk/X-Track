# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for X-Track 1.0.0 (onedir + companion gallery-dl.exe)."""

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
VERSION = "1.0.0"

gdl_datas, gdl_binaries, gdl_hiddenimports = collect_all("gallery_dl")

shared_datas = [
    ("resources/default_watermark.png", "resources"),
    ("resources/fonts", "resources/fonts"),
    ("resources/ffmpeg-9.0.1", "resources/ffmpeg-9.0.1"),
] + gdl_datas

shared_hidden = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "xtrack",
    "xtrack.app",
    "xtrack.main_window",
    "xtrack.config_store",
    "xtrack.command_builder",
    "xtrack.watermark",
    "xtrack.watermark_pipeline",
    "xtrack.installer",
    "xtrack.i18n",
    "xtrack.styles",
    "xtrack.cookies",
    "xtrack.download_paths",
    "xtrack.manifest",
    "xtrack.optional_date",
    "xtrack.url_utils",
    "xtrack.paths",
    "gallery_dl",
] + list(gdl_hiddenimports)

# --- GUI ---
gui = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=list(gdl_binaries),
    datas=list(shared_datas),
    hiddenimports=list(shared_hidden),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# --- gallery-dl CLI companion (must NOT be the GUI exe) ---
cli = Analysis(
    ["gallery_dl_cli.py"],
    pathex=["."],
    binaries=list(gdl_binaries),
    datas=list(gdl_datas),
    hiddenimports=["gallery_dl"] + list(gdl_hiddenimports),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["PyQt6"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

MERGE((gui, "X-Track", "X-Track"), (cli, "gallery-dl", "gallery-dl"))

gui_pyz = PYZ(gui.pure, gui.zipped_data, cipher=block_cipher)
cli_pyz = PYZ(cli.pure, cli.zipped_data, cipher=block_cipher)

icon = "icon.ico" if os.path.exists("icon.ico") else None

gui_exe = EXE(
    gui_pyz,
    gui.scripts,
    [],
    exclude_binaries=True,
    name="X-Track",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX often breaks ffmpeg / Qt DLLs
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon,
)

cli_exe = EXE(
    cli_pyz,
    cli.scripts,
    [],
    exclude_binaries=True,
    name="gallery-dl",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    gui_exe,
    cli_exe,
    gui.binaries,
    gui.zipfiles,
    gui.datas,
    cli.binaries,
    cli.zipfiles,
    cli.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="X-Track",
)
