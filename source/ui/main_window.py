"""
Главное окно. Собирает все виджеты, связывает их с состоянием и рабочими потоками.
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Optional

import cv2
from PySide6.QtCore import Qt, QTimer, QSize, Signal, QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
    QComboBox, QCheckBox, QSlider, QGridLayout, QHBoxLayout, QVBoxLayout,
    QGroupBox, QScrollArea, QSplitter, QMessageBox, QFileDialog, QSizePolicy,
)

from source.config import (
    IS_WINDOWS, IS_LINUX, SETTINGS,
    CAMERA_INDEX, CAM_WIDTH, CAM_HEIGHT,
    GRBL_BAUD, STATIC_DIR,
    default_captures_root,
)
from source.i18n import t, LANG, toggle_lang
from source.hardware.grbl import GRBLController
from source.hardware.camera import Camera
from source.image_utils import apply_adjust, bgr_to_qpixmap
from source.services.state import AppState
from source.services.capture_worker import UiSignals, run_scan, run_demo
from source.ui.capture_grid import CaptureGrid
from source.ui.icons import make_play_icon, make_stop_icon
from source.ui import styles
from source.ui.dxf_panel import DxfPanel



class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self.signals = UiSignals()
        self.scan_thread: Optional[threading.Thread] = None
        self.demo_thread: Optional[threading.Thread] = None
        self.scan_stop = {"stop": False}
        self.demo_stop = {"stop": False}

        self.setWindowTitle(t("app_title"))
        self.resize(1400, 900)

        self._build_ui()
        self._connect_signals()
        self._apply_i18n()

        self.timer_status = QTimer(self)
        self.timer_status.timeout.connect(self._poll_status)
        self.timer_status.start(700)

        self.timer_view = QTimer(self)
        self.timer_view.timeout.connect(self._update_preview)
        self.timer_view.start(33)

    # ---------- brand ----------
    def _apply_brand(self):
        html = (
            '<div style="'
            'color:#FFAF26;font-weight:700;font-size:26px;line-height:100%;'
            'padding:0;margin:0;'
            '">'
            f'{t("app_title")}'
            '</div>'
            '<div style="'
            'color:#8a8a92;font-size:11px;letter-spacing:1px;line-height:100%;'
            'padding:0;margin-top:4px;'
            '">'
            f'{t("app_sub")}'
            '</div>'
        )
        self.lbl_brand.setText(html)

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # --- left panel ---
        left = QWidget()
        left.setFixedWidth(340)
        left.setStyleSheet("background:#1E1E1E;")
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setWidget(left)
        left_scroll.setFixedWidth(360)
        left_scroll.setStyleSheet("QScrollArea{border:none;background:#1E1E1E;}")

        lv = QVBoxLayout(left)
        lv.setContentsMargins(10, 10, 10, 10)
        lv.setSpacing(6)

        self._build_header(lv)
        self._build_grbl_group(lv)
        self._build_jog_group(lv)
        self._build_camera_group(lv)
        self._build_scan_group(lv)
        self._build_captures_group(lv)
        self._build_dxf_group(lv)
        lv.addStretch(1)

        # --- right side ---
        right = QSplitter(Qt.Vertical)
        right.setStyleSheet("QSplitter::handle{background:#2a2a2e;}")

        preview_wrap = QWidget()
        preview_wrap.setStyleSheet("background:#000;")
        pv = QVBoxLayout(preview_wrap)
        pv.setContentsMargins(0, 0, 0, 0)
        self.lbl_preview = QLabel()
        self.lbl_preview.setAlignment(Qt.AlignCenter)
        self.lbl_preview.setStyleSheet("background:#000;")
        self.lbl_preview.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        pv.addWidget(self.lbl_preview)

        self.flash_overlay = QLabel(preview_wrap)
        self.flash_overlay.setStyleSheet("background:rgba(255,255,255,0.0);")
        self.flash_overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.flash_overlay.hide()

        grid_wrap = QWidget()
        grid_wrap.setStyleSheet("background:#0b0b0b;")
        gv = QVBoxLayout(grid_wrap)
        gv.setContentsMargins(0, 0, 0, 0)
        self.grid_scroll = QScrollArea()
        self.grid_scroll.setWidgetResizable(True)
        self.grid_scroll.setStyleSheet("QScrollArea{border:none;background:#0b0b0b;}")
        self.grid = CaptureGrid()
        self.grid_scroll.setWidget(self.grid)
        gv.addWidget(self.grid_scroll)

        right.addWidget(preview_wrap)
        right.addWidget(grid_wrap)
        right.setSizes([500, 400])

        root.addWidget(left_scroll)
        root.addWidget(right, 1)

        self._load_ports()

    def _build_header(self, parent_layout):
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 8)

        self.logo = QLabel()
        self.logo.setFixedSize(64, 64)
        self._load_logo()
        hl.addWidget(self.logo)

        self.lbl_brand = QLabel()
        self.lbl_brand.setTextFormat(Qt.RichText)
        self.lbl_brand.setContentsMargins(0, 0, 0, 0)
        self._apply_brand()
        hl.addWidget(self.lbl_brand)
        hl.addStretch(1)

        self.btn_lang = QPushButton("EN" if LANG == "ru" else "RU")
        self.btn_lang.setFixedWidth(44)
        self.btn_lang.setStyleSheet(
            "QPushButton{background:#232327;border:1px solid #FFAF26;color:#FFAF26;"
            "font-weight:600;padding:4px 8px;border-radius:4px;outline:none;}"
            "QPushButton:hover{background:#3a2a00;}"
            "QPushButton:pressed{background:#2a1e00;}"
            "QPushButton:focus{outline:none;}"
        )
        self.btn_lang.clicked.connect(self._toggle_lang)
        hl.addWidget(self.btn_lang)
        parent_layout.addWidget(header)

    def _build_grbl_group(self, parent_layout):
        self.gb_grbl = QGroupBox(t("grbl"))
        self.gb_grbl.setStyleSheet(styles.group_qss())
        f = QVBoxLayout(self.gb_grbl)
        f.setSpacing(4)

        row = QHBoxLayout()
        self.lbl_port = QLabel(t("port"))
        self.cmb_ports = QComboBox()
        self.cmb_ports.setEditable(False)
        row.addWidget(self.lbl_port)
        row.addWidget(self.cmb_ports, 1)
        btn_refresh = QPushButton("↻"); btn_refresh.setFixedWidth(30)
        btn_refresh.clicked.connect(self._load_ports)
        row.addWidget(btn_refresh)
        f.addLayout(row)

        row = QHBoxLayout()
        self.btn_grbl_conn = QPushButton(t("connect"))
        self.btn_grbl_conn.setStyleSheet(styles.small_primary_qss())
        self.btn_grbl_conn.clicked.connect(self._grbl_connect)
        self.btn_grbl_disc = QPushButton(t("disconnect"))
        self.btn_grbl_disc.clicked.connect(self._grbl_disconnect)
        row.addWidget(self.btn_grbl_conn, 1)
        row.addWidget(self.btn_grbl_disc)
        f.addLayout(row)

        row = QHBoxLayout()
        self.btn_home = QPushButton(t("home")); self.btn_home.clicked.connect(self._grbl_home)
        self.btn_unlock = QPushButton(t("unlock")); self.btn_unlock.clicked.connect(self._grbl_unlock)
        row.addWidget(self.btn_home, 1); row.addWidget(self.btn_unlock, 1)
        f.addLayout(row)

        self.lbl_grbl_status = QLabel(t("disconnected"))
        self.lbl_grbl_status.setStyleSheet(styles.status_qss())
        f.addWidget(self.lbl_grbl_status)
        parent_layout.addWidget(self.gb_grbl)

    def _build_jog_group(self, parent_layout):
        self.gb_jog = QGroupBox(t("jog"))
        self.gb_jog.setStyleSheet(styles.group_qss())
        jv = QVBoxLayout(self.gb_jog); jv.setSpacing(4)

        row = QHBoxLayout()
        self.lbl_step = QLabel(t("step_mm"))
        row.addWidget(self.lbl_step)
        self.sp_step = QDoubleSpinBox()
        self.sp_step.setRange(0.01, 1000)
        self.sp_step.setValue(1)
        self.sp_step.setSingleStep(0.1)
        self.sp_step.setDecimals(2)
        row.addWidget(self.sp_step, 1)
        self.lbl_feed1 = QLabel(t("feed"))
        row.addWidget(self.lbl_feed1)
        self.sp_feed = QDoubleSpinBox()
        self.sp_feed.setRange(1, 20000)
        self.sp_feed.setValue(3000)
        self.sp_feed.setDecimals(0)
        row.addWidget(self.sp_feed, 1)
        jv.addLayout(row)

        jog_grid = QGridLayout(); jog_grid.setSpacing(4)
        def mk(txt, sx, sy):
            b = QPushButton(txt)
            b.clicked.connect(lambda: self._jog(sx, sy))
            return b
        jog_grid.addWidget(mk("↖", -1,  1), 0, 0)
        jog_grid.addWidget(mk("↑",  0,  1), 0, 1)
        jog_grid.addWidget(mk("↗",  1,  1), 0, 2)
        jog_grid.addWidget(mk("←", -1,  0), 1, 0)
        jog_grid.addWidget(mk("·",  0,  0), 1, 1)
        jog_grid.addWidget(mk("→",  1,  0), 1, 2)
        jog_grid.addWidget(mk("↙", -1, -1), 2, 0)
        jog_grid.addWidget(mk("↓",  0, -1), 2, 1)
        jog_grid.addWidget(mk("↘",  1, -1), 2, 2)
        jv.addLayout(jog_grid)
        parent_layout.addWidget(self.gb_jog)

    def _build_camera_group(self, parent_layout):
        self.gb_cam = QGroupBox(t("camera"))
        self.gb_cam.setStyleSheet(styles.group_qss())
        cv = QVBoxLayout(self.gb_cam); cv.setSpacing(4)

        row = QHBoxLayout()
        self.lbl_camidx = QLabel(t("cam_index"))
        row.addWidget(self.lbl_camidx)
        self.sp_camidx = QSpinBox(); self.sp_camidx.setRange(0, 16); self.sp_camidx.setValue(CAMERA_INDEX)
        row.addWidget(self.sp_camidx, 1)
        self.btn_cam_conn = QPushButton(t("cam_connect"))
        self.btn_cam_conn.setStyleSheet(styles.small_primary_qss())
        self.btn_cam_conn.clicked.connect(self._cam_connect)
        row.addWidget(self.btn_cam_conn, 1)
        self.btn_cam_disc = QPushButton(t("cam_disconnect"))
        self.btn_cam_disc.clicked.connect(self._cam_disconnect)
        row.addWidget(self.btn_cam_disc)
        cv.addLayout(row)

        def slider_row(label_key, attr):
            row = QHBoxLayout()
            lbl = QLabel(t(label_key)); lbl.setFixedWidth(70)
            s = QSlider(Qt.Horizontal); s.setRange(-100, 100); s.setValue(0)
            s.valueChanged.connect(self._on_slider)
            setattr(self, attr, s)
            row.addWidget(lbl); row.addWidget(s, 1)
            cv.addLayout(row)
            return lbl
        self.lbl_bright = slider_row("bright", "sl_bright")
        self.lbl_contrast = slider_row("contrast", "sl_contrast")
        self.lbl_satur = slider_row("satur", "sl_satur")

        self.btn_capture = QPushButton(t("capture"))
        self.btn_capture.clicked.connect(self._capture_one)
        cv.addWidget(self.btn_capture)
        parent_layout.addWidget(self.gb_cam)

    def _build_scan_group(self, parent_layout):
        self.gb_scan = QGroupBox(t("auto_scan"))
        self.gb_scan.setStyleSheet(styles.group_qss())
        sv = QVBoxLayout(self.gb_scan); sv.setSpacing(4)

        form = QGridLayout()
        form.setHorizontalSpacing(6); form.setVerticalSpacing(4)
        self.sp_rows = QSpinBox(); self.sp_rows.setRange(1, 200); self.sp_rows.setValue(3)
        self.sp_cols = QSpinBox(); self.sp_cols.setRange(1, 200); self.sp_cols.setValue(5)
        self.sp_sx = QDoubleSpinBox(); self.sp_sx.setRange(0.01, 1000); self.sp_sx.setValue(5); self.sp_sx.setSingleStep(0.1); self.sp_sx.setDecimals(2)
        self.sp_sy = QDoubleSpinBox(); self.sp_sy.setRange(0.01, 1000); self.sp_sy.setValue(4); self.sp_sy.setSingleStep(0.1); self.sp_sy.setDecimals(2)
        self.sp_settle = QDoubleSpinBox(); self.sp_settle.setRange(0.0, 30); self.sp_settle.setValue(0.4); self.sp_settle.setSingleStep(0.1); self.sp_settle.setDecimals(2)

        self.lbl_rows = QLabel(t("rows")); self.lbl_cols = QLabel(t("cols"))
        self.lbl_sx = QLabel(t("step_x")); self.lbl_sy = QLabel(t("step_y"))
        self.lbl_settle = QLabel(t("settle_s"))
        form.addWidget(self.lbl_rows, 0, 0); form.addWidget(self.sp_rows, 0, 1)
        form.addWidget(self.lbl_cols, 0, 2); form.addWidget(self.sp_cols, 0, 3)
        form.addWidget(self.lbl_sx, 1, 0); form.addWidget(self.sp_sx, 1, 1)
        form.addWidget(self.lbl_sy, 1, 2); form.addWidget(self.sp_sy, 1, 3)
        form.addWidget(self.lbl_settle, 2, 0); form.addWidget(self.sp_settle, 2, 1)
        self.chk_snake = QCheckBox(t("snake")); self.chk_snake.setChecked(True)
        form.addWidget(self.chk_snake, 2, 2, 1, 2)
        sv.addLayout(form)

        sv.addSpacing(8)

        row = QHBoxLayout()
        self.btn_start = QPushButton(t("start"))
        self.btn_start.setStyleSheet(styles.primary_qss())
        self.btn_start.setIcon(make_play_icon(QColor("#121212")))
        self.btn_start.setIconSize(QSize(14, 14))
        self.btn_start.clicked.connect(self._start_scan)

        self.btn_stop = QPushButton("")
        self.btn_stop.setStyleSheet(styles.danger_qss())
        self.btn_stop.setIcon(make_stop_icon(QColor("#ffffff")))
        self.btn_stop.setIconSize(QSize(14, 14))
        self.btn_stop.clicked.connect(self._stop_scan)

        row.addWidget(self.btn_start, 3); row.addWidget(self.btn_stop, 1)
        sv.addLayout(row)

        sv.addSpacing(6)

        row = QHBoxLayout()
        self.btn_demo = QPushButton(t("demo"))
        self.btn_demo.setStyleSheet(styles.demo_qss())
        self.btn_demo.setIcon(make_play_icon(QColor("#FFAF26")))
        self.btn_demo.setIconSize(QSize(14, 14))
        self.btn_demo.clicked.connect(self._start_demo)

        self.btn_demo_stop = QPushButton("")
        self.btn_demo_stop.setStyleSheet(styles.danger_qss())
        self.btn_demo_stop.setIcon(make_stop_icon(QColor("#ffffff")))
        self.btn_demo_stop.setIconSize(QSize(14, 14))
        self.btn_demo_stop.clicked.connect(self._stop_demo)

        row.addWidget(self.btn_demo, 3); row.addWidget(self.btn_demo_stop, 1)
        sv.addLayout(row)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet("color:#FFAF26;font-size:12px;")
        sv.addWidget(self.lbl_progress)
        parent_layout.addWidget(self.gb_scan)

    def _build_captures_group(self, parent_layout):
        self.gb_cap = QGroupBox(t("captures"))
        self.gb_cap.setStyleSheet(styles.group_qss())
        cpv = QVBoxLayout(self.gb_cap); cpv.setSpacing(4)

        row = QHBoxLayout()
        self.lbl_folder = QLabel(t("save_folder"))
        row.addWidget(self.lbl_folder)
        self.edit_folder = QLineEdit(str(self.state.captures_root))
        self.edit_folder.setReadOnly(True)
        self.edit_folder.setToolTip(str(self.state.captures_root))
        row.addWidget(self.edit_folder, 1)
        self.btn_browse = QPushButton("…"); self.btn_browse.setFixedWidth(30)
        self.btn_browse.clicked.connect(self._choose_folder)
        row.addWidget(self.btn_browse)
        cpv.addLayout(row)

        row = QHBoxLayout()
        self.lbl_naming = QLabel(t("naming"))
        row.addWidget(self.lbl_naming)
        self.cmb_naming = QComboBox()
        self.cmb_naming.addItem(t("naming_coords"), "coords")
        self.cmb_naming.addItem(t("naming_seq"), "seq")
        idx = self.cmb_naming.findData(self.state.naming)
        if idx >= 0:
            self.cmb_naming.setCurrentIndex(idx)
        self.cmb_naming.currentIndexChanged.connect(self._set_naming)
        row.addWidget(self.cmb_naming, 1)
        cpv.addLayout(row)

        row = QHBoxLayout()
        self.btn_open = QPushButton(t("open_folder")); self.btn_open.clicked.connect(self._open_folder)
        self.btn_reset_folder = QPushButton(t("reset_folder")); self.btn_reset_folder.clicked.connect(self._reset_folder)
        self.btn_clear = QPushButton(t("clear")); self.btn_clear.setStyleSheet(styles.danger_qss())
        self.btn_clear.clicked.connect(self._clear_captures)
        row.addWidget(self.btn_open, 1); row.addWidget(self.btn_reset_folder, 1); row.addWidget(self.btn_clear, 1)
        cpv.addLayout(row)
        parent_layout.addWidget(self.gb_cap)

    def _build_dxf_group(self, parent_layout):
        self.dxf_panel = DxfPanel()
        parent_layout.addWidget(self.dxf_panel)

    # ---------- logo ----------
    def _load_logo(self):
        for name in ("logo.svg", "logo.png", "logo.ico"):
            p = STATIC_DIR / name
            if not p.exists():
                continue
            from PySide6.QtGui import QPixmap
            pix = QPixmap(str(p))
            if not pix.isNull():
                self.logo.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self.logo.setText("PCB")
        self.logo.setStyleSheet(
            "background:#121212; border-radius:8px; color:#FFAF26; "
            "font-weight:700; font-size:22px; qproperty-alignment: AlignCenter;"
        )

    # ---------- i18n ----------
    def _apply_i18n(self):
        self.setWindowTitle(t("app_title"))
        self._apply_brand()
        self.gb_grbl.setTitle(t("grbl"))
        self.gb_jog.setTitle(t("jog"))
        self.gb_cam.setTitle(t("camera"))
        self.gb_scan.setTitle(t("auto_scan"))
        self.gb_cap.setTitle(t("captures"))

        self.lbl_port.setText(t("port"))
        self.btn_grbl_conn.setText(t("connect"))
        self.btn_grbl_disc.setText(t("disconnect"))
        self.btn_home.setText(t("home"))
        self.btn_unlock.setText(t("unlock"))

        self.lbl_step.setText(t("step_mm"))
        self.lbl_feed1.setText(t("feed"))

        self.lbl_camidx.setText(t("cam_index"))
        self.btn_cam_conn.setText(t("cam_connect"))
        self.btn_cam_disc.setText(t("cam_disconnect"))
        self.lbl_bright.setText(t("bright"))
        self.lbl_contrast.setText(t("contrast"))
        self.lbl_satur.setText(t("satur"))
        self.btn_capture.setText(t("capture"))

        self.lbl_rows.setText(t("rows"))
        self.lbl_cols.setText(t("cols"))
        self.lbl_sx.setText(t("step_x"))
        self.lbl_sy.setText(t("step_y"))
        self.lbl_settle.setText(t("settle_s"))
        self.chk_snake.setText(t("snake"))
        self.btn_start.setText(t("start"))
        self.btn_demo.setText(t("demo"))

        self.lbl_folder.setText(t("save_folder"))
        self.lbl_naming.setText(t("naming"))
        self.cmb_naming.setItemText(0, t("naming_coords"))
        self.cmb_naming.setItemText(1, t("naming_seq"))
        self.btn_open.setText(t("open_folder"))
        self.btn_reset_folder.setText(t("reset_folder"))
        self.btn_clear.setText(t("clear"))

        if self.state.grbl is None:
            self.lbl_grbl_status.setText(t("disconnected"))
        
        if hasattr(self, "dxf_panel"):
            self.dxf_panel.retranslate()

    def _toggle_lang(self):
        new = toggle_lang()
        self.btn_lang.setText("EN" if new == "ru" else "RU")
        self._apply_i18n()

    # ---------- ports ----------
    def _load_ports(self):
        self.cmb_ports.clear()
        self.cmb_ports.addItem("AUTO", "AUTO")
        ports = []
        from serial.tools import list_ports
        for p in list_ports.comports():
            ports.append((p.device, f"{p.device} — {p.description or ''}"))
        if IS_LINUX:
            import glob
            known = {dev for dev, _ in ports}
            for pat in ("/dev/ttyUSB*", "/dev/ttyACM*"):
                for dev in sorted(glob.glob(pat)):
                    if dev not in known:
                        ports.append((dev, dev))
        for dev, label in ports:
            self.cmb_ports.addItem(label, dev)

    # ---------- GRBL actions ----------
    def _grbl_connect(self):
        port = self.cmb_ports.currentData() or "AUTO"

        if self.state.grbl is not None:
            if port == "AUTO" or port == self.state.grbl.port:
                return
            self.state.grbl.close()
            self.state.grbl = None

        from serial.tools import list_ports
        if port == "AUTO":
            cands = []
            for p in list_ports.comports():
                desc = (p.description or "").lower()
                dev = p.device or ""
                if any(k in desc for k in ("ch340", "cp210", "usb", "serial", "uart")):
                    cands.append(dev)
                elif IS_LINUX and (dev.startswith("/dev/ttyUSB") or dev.startswith("/dev/ttyACM")):
                    cands.append(dev)
            if not cands and IS_LINUX:
                import glob
                cands = sorted(glob.glob("/dev/ttyUSB*")) + sorted(glob.glob("/dev/ttyACM*"))
            if not cands:
                QMessageBox.warning(self, t("error"), t("no_ports"))
                return
            port = cands[0]

        try:
            self.state.grbl = GRBLController(port, GRBL_BAUD)
        except PermissionError:
            QMessageBox.critical(self, t("error"), f"{t('permission_hint')}\n\n{port}")
            return
        except Exception as e:
            QMessageBox.critical(self, t("error"), f"{t('port_open_failed')}: {port}\n{e}")
            return

    def _grbl_disconnect(self):
        if self.state.grbl:
            self.state.grbl.close()
            self.state.grbl = None

    def _grbl_home(self):
        if not self.state.grbl:
            QMessageBox.warning(self, t("error"), t("grbl_not_connected")); return
        try:
            self.state.grbl.home()
        except Exception as e:
            QMessageBox.warning(self, t("error"), str(e))

    def _grbl_unlock(self):
        if not self.state.grbl:
            QMessageBox.warning(self, t("error"), t("grbl_not_connected")); return
        try:
            self.state.grbl.unlock()
        except Exception as e:
            QMessageBox.warning(self, t("error"), str(e))

    def _jog(self, sx: float, sy: float):
        if not self.state.grbl:
            return
        step = float(self.sp_step.value())
        feed = float(self.sp_feed.value())
        try:
            self.state.grbl.move_rel(sx * step, sy * step, feed)
        except Exception as e:
            print("jog:", e)

    def _poll_status(self):
        g = self.state.grbl
        if g:
            s = g.status
            self.lbl_grbl_status.setText(
                f"{s.get('state','?')}  X:{s.get('x',0):.3f}  Y:{s.get('y',0):.3f}"
            )
        else:
            self.lbl_grbl_status.setText(t("disconnected"))

    # ---------- Camera ----------
    def _cam_connect(self):
        idx = int(self.sp_camidx.value())
        if self.state.camera:
            self.state.camera.close()
            self.state.camera = None
        try:
            self.state.camera = Camera(idx, CAM_WIDTH, CAM_HEIGHT)
        except Exception as e:
            QMessageBox.critical(self, t("error"), f"{t('camera_open_failed')}: {idx}\n{e}")

    def _cam_disconnect(self):
        if self.state.camera:
            self.state.camera.close()
            self.state.camera = None
        self.lbl_preview.clear()

    def _on_slider(self):
        self.state.brightness = int(self.sl_bright.value())
        self.state.contrast = int(self.sl_contrast.value())
        self.state.saturation = int(self.sl_satur.value())

    def _update_preview(self):
        cam = self.state.camera
        if not cam:
            return
        frame = cam.get()
        if frame is None:
            return
        frame = apply_adjust(frame, self.state.brightness, self.state.contrast, self.state.saturation)
        pix = bgr_to_qpixmap(frame)
        lbl_size = self.lbl_preview.size()
        if lbl_size.width() > 10 and lbl_size.height() > 10:
            pix = pix.scaled(lbl_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.lbl_preview.setPixmap(pix)
        self.flash_overlay.setGeometry(0, 0, self.lbl_preview.width(), self.lbl_preview.height())

    def _capture_one(self):
        cam = self.state.camera
        if not cam:
            QMessageBox.warning(self, t("error"), t("cam_not_connected")); return
        frame = cam.get()
        if frame is None:
            return
        frame = apply_adjust(frame, self.state.brightness, self.state.contrast, self.state.saturation)
        if self.state.session_dir is None:
            self.state.new_session()
        idx = len(self.state.captures)
        cols = max(1, self.state.grid_cols or 1)
        r, c = idx // cols, idx % cols
        fname = self.state.make_filename(r, c, tag=f"manual_{idx:04d}")
        fpath = self.state.session_dir / fname
        cv2.imwrite(str(fpath), frame)
        self.state.captures.append({
            "row": r, "col": c, "file": fname, "path": str(fpath)
        })
        self._rebuild_grid()

    # ---------- Scan ----------
    def _read_scan_params(self):
        return dict(
            rows=int(self.sp_rows.value()),
            cols=int(self.sp_cols.value()),
            step_x=float(self.sp_sx.value()),
            step_y=float(self.sp_sy.value()),
            feed=float(self.sp_feed.value()),
            snake=bool(self.chk_snake.isChecked()),
            settle=float(self.sp_settle.value()),
        )

    def _start_scan(self):
        if self.scan_thread and self.scan_thread.is_alive():
            return
        if not self.state.grbl:
            QMessageBox.warning(self, t("error"), t("grbl_not_connected")); return
        if not self.state.camera:
            QMessageBox.warning(self, t("error"), t("cam_not_connected")); return

        params = self._read_scan_params()
        self.scan_stop["stop"] = False
        self.btn_start.setEnabled(False)
        self.btn_demo.setEnabled(False)
        self.scan_thread = threading.Thread(
            target=run_scan,
            args=(self.state, self.signals),
            kwargs={**params, "stop_flag": self.scan_stop},
            daemon=True)
        self.scan_thread.start()

    def _stop_scan(self):
        self.scan_stop["stop"] = True

    # ---------- Demo ----------
    def _start_demo(self):
        if self.demo_thread and self.demo_thread.is_alive():
            return
        if not self.state.grbl:
            QMessageBox.warning(self, t("error"), t("grbl_not_connected")); return
        if not self.state.camera:
            QMessageBox.warning(self, t("error"), t("cam_not_connected")); return
        self.demo_stop["stop"] = False
        params = self._read_scan_params()
        self.demo_thread = threading.Thread(
            target=run_demo,
            args=(self.state, self.signals),
            kwargs={**params, "stop_flag": self.demo_stop},
            daemon=True)
        self.demo_thread.start()

    def _stop_demo(self):
        self.demo_stop["stop"] = True

    # ---------- Captures ----------
    def _choose_folder(self):
        start = str(self.state.captures_root)
        chosen = QFileDialog.getExistingDirectory(self, t("choose_folder_title"), start)
        if not chosen:
            return
        p = Path(chosen)
        try:
            p.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, t("error"), str(e)); return
        self.state.captures_root = p
        self.edit_folder.setText(str(p))
        self.edit_folder.setToolTip(str(p))
        SETTINGS.setValue("captures_root", str(p))

    def _reset_folder(self):
        p = default_captures_root()
        self.state.captures_root = p
        self.edit_folder.setText(str(p))
        self.edit_folder.setToolTip(str(p))
        SETTINGS.setValue("captures_root", "")

    def _set_naming(self):
        data = self.cmb_naming.currentData()
        self.state.naming = data
        SETTINGS.setValue("naming", data)

    def _clear_captures(self):
        if QMessageBox.question(self, t("captures"), t("confirm_clear")) != QMessageBox.Yes:
            return
        self.state.captures = []
        self.state.session_dir = None
        self.state.grid_rows = 0
        self.state.grid_cols = 0
        self._rebuild_grid()

    def _open_folder(self):
        p = self.state.session_dir or self.state.captures_root
        try:
            if IS_WINDOWS:
                os.startfile(str(p))  # type: ignore
            elif sys.platform == "darwin":
                os.system(f'open "{p}"')
            else:
                os.system(f'xdg-open "{p}"')
        except Exception as e:
            QMessageBox.warning(self, t("error"), str(e))

    def _rebuild_grid(self):
        rows = self.state.grid_rows
        cols = self.state.grid_cols
        if not rows or not cols:
            n = len(self.state.captures)
            cols = max(1, int(n ** 0.5) or 1)
            rows = max(1, (n + cols - 1) // cols or 1)
        self.grid.rebuild(rows, cols, self.state.captures, self.state.session_dir)

    # ---------- signals ----------
    def _connect_signals(self):
        self.signals.scan_progress.connect(self._on_scan_progress)
        self.signals.scan_done.connect(self._on_scan_done)
        self.signals.captures_changed.connect(self._rebuild_grid)
        self.signals.demo_phase.connect(self._on_demo_phase)
        self.signals.demo_tick.connect(self._on_demo_tick)
        self.signals.demo_state.connect(self._on_demo_state)
        self.signals.log.connect(lambda s: print("[log]", s))

    def _on_scan_progress(self, done: int, total: int, msg: str):
        self.lbl_progress.setText(f"⏳ {t('scan_running')} {done}/{total}")

    def _on_scan_done(self, msg: str):
        self.lbl_progress.setText(msg)
        self.btn_start.setEnabled(True)
        self.btn_demo.setEnabled(True)

    def _on_demo_phase(self, r: int, c: int, phase: str):
        if self.state.grid_rows and self.state.grid_cols:
            self.grid.mark_demo(r, c, flash=False)
        self.lbl_progress.setText(f"🎬 {t('demo')}  r{r} c{c}  ({phase})")

    def _on_demo_tick(self, tick: int, r: int, c: int, phase: str):
        if self.state.grid_rows and self.state.grid_cols:
            self.grid.mark_demo(r, c, flash=True)
        self.lbl_progress.setText(f"🎬 {t('demo')}  {t('pass')} {tick}  r{r} c{c}  ({phase})")
        self._trigger_flash()

    def _on_demo_state(self, running: bool):
        self.btn_demo.setEnabled(not running)
        self.btn_start.setEnabled(not running)
        self.btn_demo_stop.setEnabled(running)

    def _trigger_flash(self):
        self.flash_overlay.setStyleSheet("background:rgba(255,255,255,0.55);")
        self.flash_overlay.show()
        QTimer.singleShot(120, self._flash_off)

    def _flash_off(self):
        self.flash_overlay.setStyleSheet("background:rgba(255,255,255,0.0);")
        self.flash_overlay.hide()

    # ---------- close ----------
    def closeEvent(self, e):
        try:
            self.scan_stop["stop"] = True
            self.demo_stop["stop"] = True
            if self.state.grbl:
                self.state.grbl.close()
            if self.state.camera:
                self.state.camera.close()
        finally:
            e.accept()