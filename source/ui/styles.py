"""
Все QSS-строки в одном месте.
"""
from __future__ import annotations


GLOBAL_QSS = """
    QWidget { background:#121212; color:#e6e6e6; font:13px system-ui; }
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
        background:#232327; border:1px solid #333; padding:4px 6px; border-radius:4px;
        selection-background-color:#FFAF26; selection-color:#121212;
    }
    QPushButton {
        background:#2a2a30;
        border:1px solid #333;
        padding:5px 8px;
        border-radius:4px;
        outline: none;
    }
    QPushButton:hover { background:#3a3a44; }
    QPushButton:pressed {
        background:#1f1f24;
        border-color:#FFAF26;
        padding-top:6px;
        padding-bottom:4px;
    }
    QPushButton:focus { outline: none; }

    QGroupBox { color:#FFAF26; }
    QCheckBox { color:#e6e6e6; }

    QSlider::groove:horizontal { height:4px; background:#333; border-radius:2px; }
    QSlider::handle:horizontal { background:#FFAF26; width:14px; margin:-6px 0; border-radius:7px; }
"""


def group_qss() -> str:
    return (
        "QGroupBox{color:#FFAF26;font-size:12px;font-weight:600;"
        "border:1px solid #2a2a2e;border-radius:4px;margin-top:10px;padding-top:8px;}"
        "QGroupBox::title{subcontrol-origin: margin;left:8px;padding:0 4px;}"
    )


def primary_qss() -> str:
    return (
        "QPushButton{background:#FFAF26;color:#121212;border:1px solid #FFAF26;"
        "padding:5px 8px;border-radius:4px;font-weight:600;outline:none;}"
        "QPushButton:hover{background:#ffc457;}"
        "QPushButton:pressed{background:#d99420;padding-top:6px;padding-bottom:4px;}"
        "QPushButton:focus{outline:none;border:1px solid #FFAF26;}"
    )


def small_primary_qss() -> str:
    return (
        "QPushButton{background:#FFAF26;color:#121212;border:1px solid #FFAF26;"
        "font-size:12px;font-weight:600;padding:4px 6px;border-radius:4px;outline:none;}"
        "QPushButton:hover{background:#ffc457;}"
        "QPushButton:pressed{background:#d99420;padding-top:5px;padding-bottom:3px;}"
        "QPushButton:focus{outline:none;border:1px solid #FFAF26;}"
    )


def danger_qss() -> str:
    return (
        "QPushButton{background:#7a2222;color:#fff;border:1px solid #7a2222;"
        "padding:5px 8px;border-radius:4px;outline:none;}"
        "QPushButton:hover{background:#9a2a2a;}"
        "QPushButton:pressed{background:#5a1818;padding-top:6px;padding-bottom:4px;}"
        "QPushButton:focus{outline:none;border:1px solid #FFAF26;}"
    )


def demo_qss() -> str:
    return (
        "QPushButton{background:#3a2a00;color:#FFAF26;border:1px solid #FFAF26;"
        "padding:5px 8px;border-radius:4px;font-weight:600;outline:none;}"
        "QPushButton:hover{background:#4a3600;}"
        "QPushButton:pressed{background:#2a1e00;padding-top:6px;padding-bottom:4px;}"
        "QPushButton:focus{outline:none;border:1px solid #FFAF26;}"
    )


def status_qss() -> str:
    return (
        "font-family: Consolas, monospace;color:#FFAF26;background:#0c0c0e;"
        "padding:6px;border:1px solid #222;border-radius:4px;"
    )