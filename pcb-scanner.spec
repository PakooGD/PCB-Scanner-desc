# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

IS_WIN   = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")
IS_MAC   = sys.platform.startswith("darwin")

ROOT   = Path(SPECPATH).resolve()
STATIC = ROOT / "static"

datas = []
if STATIC.exists():
    datas.append((str(STATIC), "static"))

hiddenimports = []
if IS_LINUX:
    hiddenimports += ["PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"]

# ---- Иконка exe ----
# Windows: logo.ico (правильный формат для exe).
# Linux/macOS: PyInstaller icon= игнорирует, но не помешает.
icon = None
if IS_WIN:
    for name in ("logo.ico", "logo.png"):
        p = STATIC / name
        if p.exists():
            icon = str(p)
            break
elif IS_MAC:
    for name in ("logo.icns", "logo.png"):
        p = STATIC / name
        if p.exists():
            icon = str(p)
            break

a = Analysis(
    ["main.py"],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "matplotlib"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
    name="pcb-scanner",
    debug=False,
    strip=False,
    upx=True,
    console=False if IS_WIN else True,
    icon=icon,
)

# --- Onedir-вариант (вместо onefile) ---
# Закомментируйте EXE выше и используйте это:
#
# exe = EXE(
#     pyz, a.scripts, [],
#     exclude_binaries=True,
#     name="pcb-scanner",
#     debug=False, strip=False, upx=True,
#     console=False if IS_WIN else True,
#     icon=icon,
# )
# coll = COLLECT(
#     exe, a.binaries, a.zipfiles, a.datas,
#     strip=False, upx=True, upx_exclude=[],
#     name="pcb-scanner",
# )