"""
Иконки для кнопок, рисуются вручную через QPainter.
"""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QPolygon


def make_play_icon(color: QColor) -> QIcon:
    """Треугольник ▶ 16×16, отрисованный в центре pixmap."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    poly = QPolygon([QPoint(9, 6), QPoint(9, 26), QPoint(25, 16)])
    p.drawPolygon(poly)
    p.end()
    return QIcon(pix)


def make_stop_icon(color: QColor) -> QIcon:
    """Квадрат ■ 16×16, отрисованный в центре pixmap."""
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setBrush(color)
    p.setPen(Qt.NoPen)
    p.drawRect(8, 8, 16, 16)
    p.end()
    return QIcon(pix)