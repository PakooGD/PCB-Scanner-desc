"""
Камера через OpenCV VideoCapture с фоновым потоком чтения кадров.
"""
from __future__ import annotations

import threading
import time
from typing import Optional

import cv2
import numpy as np

from source.config import IS_WINDOWS, IS_LINUX


class Camera:
    def __init__(self, index: int = 0, w: int = 1920, h: int = 1080):
        self.cap = self._open(index)
        if self.cap is None or not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera index {index}")
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        for _ in range(5):
            self.cap.read()
        self.lock = threading.Lock()
        self.frame: Optional[np.ndarray] = None
        self._stop = False
        threading.Thread(target=self._loop, daemon=True).start()

    @staticmethod
    def _backends():
        if IS_WINDOWS:
            return [("MSMF", cv2.CAP_MSMF), ("DSHOW", cv2.CAP_DSHOW), ("ANY", cv2.CAP_ANY)]
        if IS_LINUX:
            return [("V4L2", cv2.CAP_V4L2),
                    ("GSTREAMER", getattr(cv2, "CAP_GSTREAMER", cv2.CAP_ANY)),
                    ("ANY", cv2.CAP_ANY)]
        return [("ANY", cv2.CAP_ANY)]

    @classmethod
    def _open(cls, index: int):
        for name, backend in cls._backends():
            try:
                cap = cv2.VideoCapture(index, backend)
                if cap.isOpened():
                    ok, _ = cap.read()
                    if ok:
                        print(f"[camera] opened index={index} via {name}")
                        return cap
                    cap.release()
            except Exception as e:
                print(f"[camera] backend {name}: {e}")
        return None

    def _loop(self):
        while not self._stop:
            try:
                ok, f = self.cap.read()
            except Exception:
                ok, f = False, None
            if ok and f is not None:
                with self.lock:
                    self.frame = f
            else:
                time.sleep(0.05)

    def get(self) -> Optional[np.ndarray]:
        with self.lock:
            return None if self.frame is None else self.frame.copy()

    def close(self):
        self._stop = True
        try:
            self.cap.release()
        except Exception:
            pass