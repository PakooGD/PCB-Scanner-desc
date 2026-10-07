"""
Глобальное состояние приложения: подключения, настройки, текущая сессия.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from source.config import SETTINGS, get_captures_root
from source.hardware.grbl import GRBLController
from source.hardware.camera import Camera


class AppState:
    def __init__(self):
        self.grbl: Optional[GRBLController] = None
        self.camera: Optional[Camera] = None

        self.brightness = 0
        self.contrast = 0
        self.saturation = 0

        self.captures_root: Path = get_captures_root()
        self.session_dir: Optional[Path] = None
        self.captures: List[Dict[str, Any]] = []

        self.grid_cols = 0
        self.grid_rows = 0

        self.naming = SETTINGS.value("naming", "coords")
        self.seq = 0

    def new_session(self) -> Path:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        p = self.captures_root / f"session_{ts}"
        p.mkdir(parents=True, exist_ok=True)
        self.session_dir = p
        self.captures = []
        self.grid_cols = 0
        self.grid_rows = 0
        self.seq = 0
        return p

    def make_filename(self, row: int, col: int, tag: Optional[str] = None) -> str:
        if self.naming == "seq":
            name = f"{self.seq:04d}.png"
            self.seq += 1
            return name
        if tag is None:
            return f"r{row:03d}_c{col:03d}.png"
        return f"{tag}.png"