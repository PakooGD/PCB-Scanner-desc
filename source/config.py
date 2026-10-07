"""
Пути, переменные окружения, QSettings, дефолтные директории.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtGui import QIcon
from PySide6.QtCore import QSettings


# ======================= OS =======================
IS_WINDOWS = (os.name == "nt")
IS_LINUX   = (os.name == "posix")
IS_MAC     = (sys.platform == "darwin")


# ======================= Пути =======================
def app_root() -> Path:
    """Корень проекта (там, где main.py и source/)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


def source_root() -> Path:
    """Папка source/ — в dev это source/, во frozen — _MEIPASS/source/."""
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        # PyInstaller кладёт source/ в _internal/source/ или в _MEIPASS/source/
        cand = base / "source"
        if cand.exists():
            return cand
        cand2 = base / "_internal" / "source"
        if cand2.exists():
            return cand2
        return cand
    return Path(__file__).parent


BASE_DIR   = app_root()
SOURCE_DIR = source_root()
STATIC_DIR = SOURCE_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)


# ======================= Настройки =======================
GRBL_BAUD    = int(os.environ.get("GRBL_BAUD", "115200"))
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
CAM_WIDTH    = int(os.environ.get("CAM_WIDTH", "1920"))
CAM_HEIGHT   = int(os.environ.get("CAM_HEIGHT", "1080"))

SETTINGS = QSettings("PCB-Microscope", "Scanner")


# ======================= Иконка приложения =======================
def _app_icon_path() -> Optional[Path]:
    if IS_WINDOWS:
        for name in ("logo.ico", "logo.png", "logo.svg"):
            p = STATIC_DIR / name
            if p.exists():
                return p
    else:
        for name in ("logo.png", "logo.svg", "logo.ico"):
            p = STATIC_DIR / name
            if p.exists():
                return p
    return None


def load_app_icon() -> Optional[QIcon]:
    p = _app_icon_path()
    if p is None:
        return None
    ic = QIcon(str(p))
    return ic if not ic.isNull() else None


# ======================= Папка снимков =======================
def default_captures_root() -> Path:
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif IS_MAC:
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME") or (Path.home() / ".local" / "share"))
    p = base / "PCB-Microscope-Scanner" / "captures"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_captures_root() -> Path:
    saved = SETTINGS.value("captures_root", "", type=str)
    if saved:
        p = Path(saved).expanduser()
        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass
    return default_captures_root()