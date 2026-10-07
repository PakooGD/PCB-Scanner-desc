"""
Сетка снимков с подсветкой активной демо-ячейки.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Dict, Any, List

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget, QLabel, QGridLayout, QSizePolicy


class CaptureGrid(QWidget):
    def __init__(self):
        super().__init__()
        self._layout = QGridLayout(self)
        self._layout.setSpacing(0)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._cells: List[QLabel] = []
        self._cols = 0
        self._rows = 0
        self._demo_idx = -1
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def rebuild(self,
                rows: int, cols: int,
                captures: List[Dict[str, Any]],
                session_dir: Optional[Path],
                demo_row: int = -1,
                demo_col: int = -1,
                flash: bool = False):
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        self._cells.clear()
        self._cols = max(1, cols)
        self._rows = max(1, rows)
        self._demo_idx = -1

        cells_map = {}
        for c in captures:
            cells_map[(c["row"], c["col"])] = c

        for r in range(self._rows):
            for c in range(self._cols):
                lbl = QLabel()
                lbl.setMinimumSize(80, 60)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet("background:#111; color:#555; border:1px solid #1a1a1a;")
                info = cells_map.get((r, c))
                if info:
                    path: Optional[Path] = None
                    if info.get("path"):
                        path = Path(info["path"])
                    elif session_dir:
                        path = session_dir / info["file"]
                    if path and path.exists():
                        pix = QPixmap(str(path))
                        lbl.setPixmap(pix.scaled(400, 300, Qt.KeepAspectRatio,
                                                 Qt.SmoothTransformation))
                    else:
                        pix = info.get("pixmap")
                        if isinstance(pix, QPixmap) and not pix.isNull():
                            lbl.setPixmap(pix.scaled(400, 300, Qt.KeepAspectRatio,
                                                     Qt.SmoothTransformation))
                        else:
                            lbl.setText("?")
                if demo_row == r and demo_col == c:
                    if flash:
                        lbl.setStyleSheet("background:#ffffff; border:2px solid #FFAF26;")
                    else:
                        lbl.setStyleSheet("background:#000; border:2px solid #FFAF26;")
                    self._demo_idx = r * self._cols + c
                self._layout.addWidget(lbl, r, c)
                self._cells.append(lbl)

    def mark_demo(self, row: int, col: int, flash: bool = False):
        for i, lbl in enumerate(self._cells):
            if i == self._demo_idx:
                lbl.setStyleSheet("background:#111; color:#555; border:1px solid #1a1a1a;")
        if row < 0 or col < 0 or row >= self._rows or col >= self._cols:
            self._demo_idx = -1
            return
        idx = row * self._cols + col
        if 0 <= idx < len(self._cells):
            lbl = self._cells[idx]
            if flash:
                lbl.setStyleSheet("background:#ffffff; border:2px solid #FFAF26;")
            else:
                lbl.setStyleSheet("background:#000; border:2px solid #FFAF26;")
            self._demo_idx = idx