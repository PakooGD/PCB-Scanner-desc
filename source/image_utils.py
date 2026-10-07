"""
Утилиты работы с изображениями: настройки яркости/контраста/насыщенности,
конвертация OpenCV BGR → QPixmap.
"""
from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtGui import QImage, QPixmap


def apply_adjust(frame: np.ndarray,
                 brightness: int,
                 contrast: int,
                 saturation: int) -> np.ndarray:
    if brightness == 0 and contrast == 0 and saturation == 0:
        return frame
    img = frame.astype(np.float32)
    if brightness != 0:
        img += brightness
    if contrast != 0:
        c = contrast * 1.28
        f = (259.0 * (c + 255.0)) / (255.0 * (259.0 - c))
        img = f * (img - 128.0) + 128.0
    img = np.clip(img, 0, 255).astype(np.uint8)
    if saturation != 0:
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[..., 1] = np.clip(hsv[..., 1] * (1.0 + saturation / 100.0), 0, 255)
        img = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    return img


def bgr_to_qpixmap(bgr: np.ndarray) -> QPixmap:
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    return QPixmap.fromImage(qimg.copy())