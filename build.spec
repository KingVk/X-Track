# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for X-Track 1.0.4 (onedir + gallery-dl + watermark tool)."""

import os
from PyInstaller.utils.hooks import collect_all

block_cipher = None
VERSION = "1.0.4"

gdl_datas, gdl_binaries, gdl_hiddenimports = collect_all("gallery_dl")

resource_datas = [
    ("resources/default_watermark.png", "resources"),
    ("resources/fonts", "resources/fonts"),
    # ffmpeg is NOT bundled — resolved from PATH / ~/.xtrack/bin / in-app download
]

shared_datas = resource_datas + gdl_datas

xtrack_core = [
    "xtrack",
    "xtrack.config_store",
    "xtrack.watermark",
    "xtrack.batch_watermark",
    "xtrack.installer",
    "xtrack.i18n",
    "xtrack.styles",
    "xtrack.paths",
    "xtrack.procutil",
]

shared_hidden = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    *xtrack_core,
    "xtrack.app",
    "xtrack.main_window",
    "xtrack.command_builder",
    "xtrack.watermark_pipeline",
    "xtrack.wmtool",
    "xtrack.wmtool_window",
    "xtrack.cookies",
    "xtrack.download_paths",
    "xtrack.manifest",
    "xtrack.optional_date",
    "xtrack.url_utils",
    "gallery_dl",
] + list(gdl_hiddenimports)

wm_hidden = [
    "PyQt6",
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    *xtrack_core,
    "xtrack.wmtool",
    "xtrack.wmtool_window",
]

# --- Main GUI ---
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

# --- gallery-dl CLI companion ---
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

# --- Standalone batch watermark GUI ---
wm = Analysis(
    ["wmtool_main.py"],
    pathex=["."],
    binaries=[],
    datas=list(resource_datas),
    hiddenimports=list(wm_hidden),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["gallery_dl"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

MERGE(
    (gui, "X-Track", "X-Track"),
    (cli, "gallery-dl", "gallery-dl"),
    (wm, "X-Track-Watermark", "X-Track-Watermark"),
)

gui_pyz = PYZ(gui.pure, gui.zipped_data, cipher=block_cipher)
cli_pyz = PYZ(cli.pure, cli.zipped_data, cipher=block_cipher)
wm_pyz = PYZ(wm.pure, wm.zipped_data, cipher=block_cipher)

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
    upx=False,
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

wm_exe = EXE(
    wm_pyz,
    wm.scripts,
    [],
    exclude_binaries=True,
    name="X-Track-Watermark",
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
    icon=icon,
)

coll = COLLECT(
    gui_exe,
    cli_exe,
    wm_exe,
    gui.binaries,
    gui.zipfiles,
    gui.datas,
    cli.binaries,
    cli.zipfiles,
    cli.datas,
    wm.binaries,
    wm.zipfiles,
    wm.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="X-Track",
)
