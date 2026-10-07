# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files

ROOT   = Path(SPECPATH).resolve()
STATIC = ROOT / "static"

datas = []
if STATIC.exists():
    datas.append((str(STATIC), "static"))

datas += collect_data_files(
    "PySide6",
    includes=["Qt/plugins/**/*"],
    excludes=["**/*.debug", "**/*.pdb"],
)

hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtSvg",
    "PySide6.QtNetwork",
    "serial.tools.list_ports_linux",
]

icon = None
p = STATIC / "logo.png"
if p.exists():
    icon = str(p)

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "tkinter", "matplotlib",
        "PyQt5", "PyQt6", "PySide2",
        "serial.tools.list_ports_windows",
        "serial.tools.list_ports_osx",
    ],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="pcb-scanner",
    debug=False, strip=False, upx=False,
    console=False,
    disable_windowed_traceback=False,
    icon=icon,
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=False, upx_exclude=[],
    name="pcb-scanner",
)