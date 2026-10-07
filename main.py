"""
PCB Microscope Scanner — Desktop (PySide6).

Функционал полностью повторяет веб-версию:
 - GRBL: connect/disconnect/home/unlock/jog/status
 - Камера: connect/disconnect, яркость/контраст/насыщенность, live-превью, одиночный снимок
 - Автосканирование сетки (rows/cols/step/snake/settle) с прогрессом
 - Demo-режим: каретка бесконечно ходит по сетке (циклично), пока не нажат «Стоп»
 - Сетка снимков, два режима именования (coords/seq), сессии + meta.json
 - RU/EN локализация с сохранением выбора
 - Пользователь сам выбирает папку сохранения снимков (сохраняется в QSettings)
"""

from __future__ import annotations

import os
import sys
import time
import json
import queue
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

import cv2
import numpy as np
import serial
from serial.tools import list_ports

from PySide6.QtCore import Qt, QTimer, QSize, Signal, QObject, QSettings
from PySide6.QtGui import QImage, QPixmap, QIcon, QFont, QPainter, QColor, QPen, QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QLineEdit, QSpinBox,
    QDoubleSpinBox, QComboBox, QCheckBox, QSlider, QGridLayout, QHBoxLayout,
    QVBoxLayout, QFormLayout, QGroupBox, QScrollArea, QSplitter, QMessageBox,
    QFileDialog, QSizePolicy, QFrame, QToolButton
)


# ======================= Пути =======================
IS_WINDOWS = (os.name == "nt")
IS_LINUX   = (os.name == "posix")


def app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


def resource_path(rel: str) -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    else:
        base = Path(__file__).parent
    return base / rel


BASE_DIR   = app_root()
STATIC_DIR = resource_path("static")
STATIC_DIR.mkdir(parents=True, exist_ok=True)


def _app_icon_path() -> Optional[Path]:
    """Возвращает путь к иконке приложения в зависимости от ОС."""
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


def _load_app_icon() -> Optional[QIcon]:
    p = _app_icon_path()
    if p is None:
        return None
    ic = QIcon(str(p))
    return ic if not ic.isNull() else None


# ======================= Настройки =======================
GRBL_BAUD    = int(os.environ.get("GRBL_BAUD", "115200"))
CAMERA_INDEX = int(os.environ.get("CAMERA_INDEX", "0"))
CAM_WIDTH    = int(os.environ.get("CAM_WIDTH", "1920"))
CAM_HEIGHT   = int(os.environ.get("CAM_HEIGHT", "1080"))


# ======================= i18n =======================
I18N = {
    "ru": {
        "app_title": "PCB Microscope Scanner",
        "app_sub": "Сканер",
        "grbl": "GRBL",
        "port": "Порт",
        "connect": "Подключить",
        "disconnect": "Отключить",
        "home": "Домой ($H)",
        "unlock": "Разблок. ($X)",
        "disconnected": "не подключено",
        "jog": "Ручное управление",
        "step_mm": "Шаг, мм",
        "feed": "Подача",
        "camera": "Камера",
        "cam_index": "Индекс",
        "cam_connect": "Подключить",
        "cam_disconnect": "Отключить",
        "bright": "Яркость",
        "contrast": "Контраст",
        "satur": "Насыщ.",
        "capture": "📸 Снимок",
        "auto_scan": "Автосканирование",
        "rows": "Строк",
        "cols": "Столбцов",
        "step_x": "Шаг X",
        "step_y": "Шаг Y",
        "settle_s": "Пауза, с",
        "snake": "Змейкой",
        "start": "▶ Старт",
        "stop": "■",
        "demo": "▶ Демо",
        "naming": "Имена файлов",
        "naming_coords": "Координаты (r000_c000)",
        "naming_seq": "Порядковый (0000)",
        "save_folder": "Папка сохранения",
        "choose_folder_title": "Выберите папку для сохранения снимков",
        "reset_folder": "Сбросить",
        "clear": "Очистить",
        "open_folder": "Открыть папку",
        "captures": "Снимки",
        "homing": "Хомирование...",
        "done": "Готово",
        "grbl_not_connected": "GRBL не подключён",
        "cam_not_connected": "Камера не подключена",
        "demo_running": "Демо запущено",
        "demo_stopped": "Демо остановлено",
        "scan_running": "Сканирование...",
        "error": "Ошибка",
        "move_error": "Ошибка движения",
        "phase_moving": "движение",
        "phase_settling": "стабилизация",
        "phase_shooting": "снимок",
        "phase_idle": "ожидание",
        "pass": "проход",
        "port_open_failed": "Не удалось открыть порт",
        "camera_open_failed": "Не удалось открыть камеру",
        "no_ports": "Последовательные порты не найдены",
        "permission_hint": "Permission denied. На Linux: sudo usermod -aG dialout $USER (перелогиньтесь) или sudo chmod 666 <порт>",
        "confirm_clear": "Очистить список снимков?",
    },
    "en": {
        "app_title": "PCB Microscope Scanner",
        "app_sub": "Scanner",
        "grbl": "GRBL",
        "port": "Port",
        "connect": "Connect",
        "disconnect": "Disconnect",
        "home": "Home ($H)",
        "unlock": "Unlock ($X)",
        "disconnected": "disconnected",
        "jog": "Jog",
        "step_mm": "Step, mm",
        "feed": "Feed",
        "camera": "Camera",
        "cam_index": "Index",
        "cam_connect": "Connect",
        "cam_disconnect": "Disconnect",
        "bright": "Brightness",
        "contrast": "Contrast",
        "satur": "Saturation",
        "capture": "📸 Capture",
        "auto_scan": "Auto Scan",
        "rows": "Rows",
        "cols": "Cols",
        "step_x": "Step X",
        "step_y": "Step Y",
        "settle_s": "Settle, s",
        "snake": "Snake pattern",
        "start": "▶ Start",
        "stop": "■",
        "demo": "▶ Demo",
        "naming": "Naming",
        "naming_coords": "Coordinates (r000_c000)",
        "naming_seq": "Sequential (0000)",
        "save_folder": "Save folder",
        "choose_folder_title": "Choose folder for captures",
        "reset_folder": "Reset",
        "clear": "Clear",
        "open_folder": "Open folder",
        "captures": "Captures",
        "homing": "Homing...",
        "done": "Done",
        "grbl_not_connected": "GRBL not connected",
        "cam_not_connected": "Camera not connected",
        "demo_running": "Demo running",
        "demo_stopped": "Demo stopped",
        "scan_running": "Scanning...",
        "error": "Error",
        "move_error": "Move error",
        "phase_moving": "moving",
        "phase_settling": "settling",
        "phase_shooting": "shooting",
        "phase_idle": "idle",
        "pass": "pass",
        "port_open_failed": "Failed to open port",
        "camera_open_failed": "Failed to open camera",
        "no_ports": "No serial ports found",
        "permission_hint": "Permission denied. On Linux: sudo usermod -aG dialout $USER (re-login) or sudo chmod 666 <port>",
        "confirm_clear": "Clear captures list?",
    },
}

SETTINGS = QSettings("PCB-Microscope", "Scanner")
LANG = SETTINGS.value("lang", "ru")


def t(key: str) -> str:
    return I18N.get(LANG, I18N["ru"]).get(key, key)


# ======================= Дефолтная папка снимков =======================
def default_captures_root() -> Path:
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    elif sys.platform == "darwin":
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


# ======================= GRBL =======================
class GRBLController:
    def __init__(self, port: str, baud: int = 115200):
        self.port = port
        self.ser = serial.Serial(port, baud, timeout=1)
        time.sleep(2)
        self.q: "queue.Queue[str]" = queue.Queue()
        self.cmd_lock = threading.Lock()
        self.status = {"state": "Unknown", "x": 0.0, "y": 0.0, "z": 0.0}
        self._stop = False
        self._wake()
        threading.Thread(target=self._read_loop, daemon=True).start()
        threading.Thread(target=self._poll_loop, daemon=True).start()

    def _wake(self):
        try:
            self.ser.write(b"\r\n\r\n")
            time.sleep(1)
            self.ser.reset_input_buffer()
        except Exception as e:
            print(f"[grbl] wake: {e}")

    def _read_loop(self):
        buf = ""
        while not self._stop:
            try:
                data = self.ser.read(512)
            except Exception:
                time.sleep(0.1); continue
            if not data:
                continue
            buf += data.decode(errors="ignore")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.strip()
                if not line:
                    continue
                if line.startswith("<"):
                    self._parse_status(line)
                else:
                    self.q.put(line)

    def _poll_loop(self):
        while not self._stop:
            try:
                self.ser.write(b"?")
            except Exception:
                pass
            time.sleep(0.25)

    def _parse_status(self, line: str):
        try:
            body = line[1:-1]
            parts = body.split("|")
            state = parts[0]
            mpos = None
            for p in parts:
                if p.startswith("MPos:"):
                    mpos = [float(v) for v in p[5:].split(",")]
            if mpos:
                self.status = {"state": state, "x": mpos[0], "y": mpos[1], "z": mpos[2]}
            else:
                self.status["state"] = state
        except Exception:
            pass

    def send(self, cmd: str, timeout: float = 60.0, wait_ok: bool = True) -> bool:
        with self.cmd_lock:
            self.ser.write((cmd + "\n").encode())
            if not wait_ok:
                return True
            deadline = time.time() + timeout
            while time.time() < deadline:
                try:
                    line = self.q.get(timeout=0.3)
                except queue.Empty:
                    continue
                if line == "ok":
                    return True
                if line.startswith("error") or line.startswith("ALARM"):
                    raise RuntimeError(line)
            raise TimeoutError(f"No OK for {cmd!r}")

    def home(self):
        self.send("$H", timeout=180)

    def unlock(self):
        self.send("$X", timeout=10)

    def move_abs(self, x: float, y: float, feed: float):
        self.send(f"G90 G0 X{x:.3f} Y{y:.3f} F{feed:.0f}", timeout=120)

    def move_rel(self, dx: float, dy: float, feed: float):
        self.send(f"G91 G0 X{dx:.3f} Y{dy:.3f} F{feed:.0f}", timeout=120)

    def wait_idle(self, timeout: float = 120.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.status.get("state") in ("Idle", "Check"):
                return
            time.sleep(0.1)
        raise TimeoutError("GRBL not idle")

    def close(self):
        self._stop = True
        try:
            self.ser.close()
        except Exception:
            pass


# ======================= Camera =======================
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


# ======================= Image adjustments =======================
def apply_adjust(frame: np.ndarray, brightness: int, contrast: int, saturation: int) -> np.ndarray:
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


# ======================= App state =======================
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


# ======================= Signals =======================
class UiSignals(QObject):
    log = Signal(str)
    scan_progress = Signal(int, int, str)
    scan_done = Signal(str)
    demo_tick = Signal(int, int, int, str)
    demo_phase = Signal(int, int, str)
    demo_state = Signal(bool)
    captures_changed = Signal()


# ======================= Grid widget =======================
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

    def rebuild(self, rows: int, cols: int, captures: List[Dict[str, Any]],
                session_dir: Optional[Path], demo_row=-1, demo_col=-1, flash=False):
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


# ======================= Scan / Demo workers =======================
def run_scan(state: AppState, signals: UiSignals,
             rows: int, cols: int, step_x: float, step_y: float,
             feed: float, snake: bool, settle: float,
             stop_flag: Dict[str, bool]):
    grbl = state.grbl
    cam = state.camera
    if grbl is None:
        signals.scan_done.emit(t("grbl_not_connected"))
        return
    if cam is None:
        signals.scan_done.emit(t("cam_not_connected"))
        return

    total = rows * cols
    signals.scan_progress.emit(0, total, t("homing"))
    session = state.new_session()
    state.grid_rows = rows
    state.grid_cols = cols

    try:
        grbl.wait_idle()
        x0 = grbl.status.get("x", 0.0)
        y0 = grbl.status.get("y", 0.0)

        done = 0
        aborted = False
        for r in range(rows):
            if stop_flag["stop"]:
                aborted = True
                break
            seq = list(range(cols))
            if snake and r % 2 == 1:
                seq.reverse()
            for c in seq:
                if stop_flag["stop"]:
                    aborted = True
                    break
                x = x0 + c * step_x
                y = y0 + r * step_y
                grbl.move_abs(x, y, feed)
                try:
                    grbl.wait_idle(timeout=60)
                except Exception:
                    pass
                t_end = time.time() + max(0.0, settle)
                while not stop_flag["stop"] and time.time() < t_end:
                    time.sleep(0.02)
                if stop_flag["stop"]:
                    aborted = True
                    break

                frame = cam.get()
                if frame is None:
                    continue
                frame = apply_adjust(frame, state.brightness, state.contrast, state.saturation)
                fname = state.make_filename(r, c)
                fpath = session / fname
                cv2.imwrite(str(fpath), frame)
                state.captures.append({
                    "row": r, "col": c, "file": fname,
                    "path": str(fpath), "x": x, "y": y
                })
                done += 1
                signals.scan_progress.emit(done, total, f"{done}/{total}")
                signals.captures_changed.emit()
            if aborted:
                break

        with open(session / "meta.json", "w", encoding="utf-8") as f:
            json.dump({
                "rows": rows, "cols": cols,
                "step_x": step_x, "step_y": step_y,
                "brightness": state.brightness,
                "contrast": state.contrast,
                "saturation": state.saturation,
                "aborted": aborted,
                "captures": state.captures,
            }, f, indent=2)
        signals.scan_done.emit(t("done"))
    except Exception as e:
        signals.scan_done.emit(f"{t('error')}: {e}")


def run_demo(state: AppState, signals: UiSignals,
             rows: int, cols: int, step_x: float, step_y: float,
             feed: float, snake: bool, settle: float,
             stop_flag: Dict[str, bool]):
    """Демо-режим: каретка бесконечно ходит по сетке rows×cols (циклично),
    пока не будет нажата кнопка «Стоп». Стартовая точка фиксируется один раз,
    поэтому каждый новый круг начинается из того же места."""
    grbl = state.grbl
    if grbl is None:
        signals.scan_done.emit(t("grbl_not_connected"))
        signals.demo_state.emit(False)
        return

    state.grid_rows = rows
    state.grid_cols = cols
    signals.demo_state.emit(True)

    tick = 0
    try:
        # запоминаем стартовую точку — от неё считаем все смещения
        try:
            grbl.wait_idle(timeout=5)
        except Exception:
            pass
        x0 = grbl.status.get("x", 0.0)
        y0 = grbl.status.get("y", 0.0)

        # внешний бесконечный цикл — «круг» демо-прохода
        while not stop_flag["stop"]:
            for r in range(rows):
                if stop_flag["stop"]:
                    break
                seq = list(range(cols))
                if snake and r % 2 == 1:
                    seq.reverse()
                for c in seq:
                    if stop_flag["stop"]:
                        break

                    x = x0 + c * step_x
                    y = y0 + r * step_y

                    signals.demo_phase.emit(r, c, t("phase_moving"))
                    try:
                        grbl.move_abs(x, y, feed)
                        grbl.wait_idle(timeout=120)
                    except Exception as e:
                        signals.log.emit(f"{t('move_error')}: {e}")

                    if stop_flag["stop"]:
                        break

                    signals.demo_phase.emit(r, c, t("phase_settling"))
                    t_end = time.time() + max(0.05, settle)
                    while not stop_flag["stop"] and time.time() < t_end:
                        time.sleep(0.02)

                    if stop_flag["stop"]:
                        break

                    tick += 1
                    signals.demo_tick.emit(tick, r, c, t("phase_shooting"))
                    t_end = time.time() + 0.12
                    while not stop_flag["stop"] and time.time() < t_end:
                        time.sleep(0.02)
                if stop_flag["stop"]:
                    break
            # конец круга — внешний while запускает новый
    finally:
        signals.demo_state.emit(False)
        signals.scan_done.emit(t("demo_stopped"))


# ======================= Main window =======================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.state = AppState()
        self.signals = UiSignals()
        self.scan_thread: Optional[threading.Thread] = None
        self.demo_thread: Optional[threading.Thread] = None
        # флаги остановки создаются один раз и живут всё время работы приложения
        self.scan_stop = {"stop": False}
        self.demo_stop = {"stop": False}
        self.last_demo_tick = 0

        self.setWindowTitle(t("app_title"))
        self.resize(1400, 900)

        self._build_ui()
        self._connect_signals()
        self._apply_i18n()

        self.timer_status = QTimer(self); self.timer_status.timeout.connect(self._poll_status)
        self.timer_status.start(700)
        self.timer_view = QTimer(self); self.timer_view.timeout.connect(self._update_preview)
        self.timer_view.start(33)

    # ---------- UI ----------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ----- left panel -----
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

        # logo header
        header = QWidget()
        hl = QHBoxLayout(header)
        hl.setContentsMargins(0, 0, 0, 8)
        self.logo = QLabel()
        self.logo.setFixedSize(32, 32)
        self._load_logo()
        hl.addWidget(self.logo)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        self.lbl_title = QLabel(t("app_title"))
        self.lbl_title.setStyleSheet("color:#FFAF26;font-weight:700;")
        self.lbl_sub = QLabel(t("app_sub"))
        self.lbl_sub.setStyleSheet("color:#8a8a92;font-size:10px;letter-spacing:1px;")
        title_box.addWidget(self.lbl_title)
        title_box.addWidget(self.lbl_sub)
        hl.addLayout(title_box)
        hl.addStretch(1)
        self.btn_lang = QPushButton("EN" if LANG == "ru" else "RU")
        self.btn_lang.setFixedWidth(44)
        self.btn_lang.setStyleSheet(
            "QPushButton{background:#232327;border:1px solid #FFAF26;color:#FFAF26;"
            "font-weight:600;padding:4px 8px;border-radius:4px;}"
            "QPushButton:hover{background:#3a2a00;}"
        )
        self.btn_lang.clicked.connect(self._toggle_lang)
        hl.addWidget(self.btn_lang)
        lv.addWidget(header)

        # ----- GRBL -----
        self.gb_grbl = QGroupBox(t("grbl"))
        self.gb_grbl.setStyleSheet(self._group_qss())
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
        self.btn_grbl_conn.setStyleSheet(self._primary_qss())
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
        self.lbl_grbl_status.setStyleSheet(self._status_qss())
        f.addWidget(self.lbl_grbl_status)
        lv.addWidget(self.gb_grbl)

        # ----- Jog -----
        self.gb_jog = QGroupBox(t("jog"))
        self.gb_jog.setStyleSheet(self._group_qss())
        jv = QVBoxLayout(self.gb_jog); jv.setSpacing(4)

        row = QHBoxLayout()
        self.lbl_step = QLabel(t("step_mm"))
        row.addWidget(self.lbl_step)
        self.sp_step = QDoubleSpinBox(); self.sp_step.setRange(0.01, 1000); self.sp_step.setValue(1); self.sp_step.setSingleStep(0.1)
        row.addWidget(self.sp_step, 1)
        self.lbl_feed1 = QLabel(t("feed"))
        row.addWidget(self.lbl_feed1)
        self.sp_feed = QDoubleSpinBox(); self.sp_feed.setRange(1, 20000); self.sp_feed.setValue(3000)
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
        lv.addWidget(self.gb_jog)

        # ----- Camera -----
        self.gb_cam = QGroupBox(t("camera"))
        self.gb_cam.setStyleSheet(self._group_qss())
        cv = QVBoxLayout(self.gb_cam); cv.setSpacing(4)

        row = QHBoxLayout()
        self.lbl_camidx = QLabel(t("cam_index"))
        row.addWidget(self.lbl_camidx)
        self.sp_camidx = QSpinBox(); self.sp_camidx.setRange(0, 16); self.sp_camidx.setValue(CAMERA_INDEX)
        row.addWidget(self.sp_camidx, 1)
        self.btn_cam_conn = QPushButton(t("cam_connect"))
        self.btn_cam_conn.setStyleSheet(self._primary_qss())
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
        lv.addWidget(self.gb_cam)

        # ----- Auto Scan -----
        self.gb_scan = QGroupBox(t("auto_scan"))
        self.gb_scan.setStyleSheet(self._group_qss())
        sv = QVBoxLayout(self.gb_scan); sv.setSpacing(4)

        form = QGridLayout()
        form.setHorizontalSpacing(6); form.setVerticalSpacing(4)
        self.sp_rows = QSpinBox(); self.sp_rows.setRange(1, 200); self.sp_rows.setValue(3)
        self.sp_cols = QSpinBox(); self.sp_cols.setRange(1, 200); self.sp_cols.setValue(5)
        self.sp_sx = QDoubleSpinBox(); self.sp_sx.setRange(0.01, 1000); self.sp_sx.setValue(5); self.sp_sx.setSingleStep(0.1)
        self.sp_sy = QDoubleSpinBox(); self.sp_sy.setRange(0.01, 1000); self.sp_sy.setValue(4); self.sp_sy.setSingleStep(0.1)
        self.sp_settle = QDoubleSpinBox(); self.sp_settle.setRange(0.0, 30); self.sp_settle.setValue(0.4); self.sp_settle.setSingleStep(0.1)

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

        row = QHBoxLayout()
        self.btn_start = QPushButton(t("start")); self.btn_start.setStyleSheet(self._primary_qss())
        self.btn_start.clicked.connect(self._start_scan)
        self.btn_stop = QPushButton(t("stop")); self.btn_stop.setStyleSheet(self._danger_qss())
        self.btn_stop.clicked.connect(self._stop_scan)
        row.addWidget(self.btn_start, 3); row.addWidget(self.btn_stop, 1)
        sv.addLayout(row)

        row = QHBoxLayout()
        self.btn_demo = QPushButton(t("demo")); self.btn_demo.setStyleSheet(self._demo_qss())
        self.btn_demo.clicked.connect(self._start_demo)
        self.btn_demo_stop = QPushButton(t("stop")); self.btn_demo_stop.setStyleSheet(self._danger_qss())
        self.btn_demo_stop.clicked.connect(self._stop_demo)
        row.addWidget(self.btn_demo, 3); row.addWidget(self.btn_demo_stop, 1)
        sv.addLayout(row)

        self.lbl_progress = QLabel("")
        self.lbl_progress.setStyleSheet("color:#FFAF26;font-size:12px;")
        sv.addWidget(self.lbl_progress)
        lv.addWidget(self.gb_scan)

        # ----- Captures -----
        self.gb_cap = QGroupBox(t("captures"))
        self.gb_cap.setStyleSheet(self._group_qss())
        cpv = QVBoxLayout(self.gb_cap); cpv.setSpacing(4)

        # save folder
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

        # naming
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
        self.btn_clear = QPushButton(t("clear")); self.btn_clear.setStyleSheet(self._danger_qss())
        self.btn_clear.clicked.connect(self._clear_captures)
        row.addWidget(self.btn_open, 1); row.addWidget(self.btn_reset_folder, 1); row.addWidget(self.btn_clear, 1)
        cpv.addLayout(row)
        lv.addWidget(self.gb_cap)

        lv.addStretch(1)

        # ----- right side -----
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

    def _load_logo(self):
        for name in ("logo.svg", "logo.png", "logo.ico"):
            p = STATIC_DIR / name
            if not p.exists():
                continue
            pix = QPixmap(str(p))
            if not pix.isNull():
                self.logo.setPixmap(pix.scaled(32, 32, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                return
        self.logo.setText("PCB")
        self.logo.setStyleSheet(
            "background:#121212; border-radius:6px; color:#FFAF26; "
            "font-weight:700; font-size:16px; qproperty-alignment: AlignCenter;"
        )

    def _group_qss(self):
        return (
            "QGroupBox{color:#FFAF26;font-size:12px;font-weight:600;"
            "border:1px solid #2a2a2e;border-radius:4px;margin-top:10px;padding-top:8px;}"
            "QGroupBox::title{subcontrol-origin: margin;left:8px;padding:0 4px;}"
        )

    def _primary_qss(self):
        return (
            "QPushButton{background:#FFAF26;color:#121212;border:1px solid #FFAF26;"
            "padding:5px 8px;border-radius:4px;font-weight:600;}"
            "QPushButton:hover{background:#ffc457;}"
        )

    def _danger_qss(self):
        return (
            "QPushButton{background:#7a2222;color:#fff;border:1px solid #7a2222;"
            "padding:5px 8px;border-radius:4px;}"
            "QPushButton:hover{background:#9a2a2a;}"
        )

    def _demo_qss(self):
        return (
            "QPushButton{background:#3a2a00;color:#FFAF26;border:1px solid #FFAF26;"
            "padding:5px 8px;border-radius:4px;font-weight:600;}"
            "QPushButton:hover{background:#4a3600;}"
        )

    def _status_qss(self):
        return (
            "font-family: Consolas, monospace;color:#FFAF26;background:#0c0c0e;"
            "padding:6px;border:1px solid #222;border-radius:4px;"
        )

    # ---------- i18n ----------
    def _apply_i18n(self):
        self.setWindowTitle(t("app_title"))
        self.lbl_title.setText(t("app_title"))
        self.lbl_sub.setText(t("app_sub"))
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
        self.btn_stop.setText(t("stop"))
        self.btn_demo.setText(t("demo"))
        self.btn_demo_stop.setText(t("stop"))

        self.lbl_folder.setText(t("save_folder"))
        self.lbl_naming.setText(t("naming"))
        self.cmb_naming.setItemText(0, t("naming_coords"))
        self.cmb_naming.setItemText(1, t("naming_seq"))
        self.btn_open.setText(t("open_folder"))
        self.btn_reset_folder.setText(t("reset_folder"))
        self.btn_clear.setText(t("clear"))

        if self.state.grbl is None:
            self.lbl_grbl_status.setText(t("disconnected"))

    def _toggle_lang(self):
        global LANG
        LANG = "en" if LANG == "ru" else "ru"
        SETTINGS.setValue("lang", LANG)
        self.btn_lang.setText("EN" if LANG == "ru" else "RU")
        self._apply_i18n()

    # ---------- ports ----------
    def _load_ports(self):
        self.cmb_ports.clear()
        self.cmb_ports.addItem("AUTO", "AUTO")
        ports = []
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
        self.state.captures.append({"row": r, "col": c, "file": fname, "path": str(fpath)})
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


# ======================= Run =======================
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("""
        QWidget { background:#121212; color:#e6e6e6; font:13px system-ui; }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background:#232327; border:1px solid #333; padding:4px 6px; border-radius:4px;
        }
        QPushButton { background:#2a2a30; border:1px solid #333; padding:5px 8px; border-radius:4px; }
        QPushButton:hover { background:#3a3a44; }
        QGroupBox { color:#FFAF26; }
        QCheckBox { color:#e6e6e6; }
        QSlider::groove:horizontal { height:4px; background:#333; border-radius:2px; }
        QSlider::handle:horizontal { background:#FFAF26; width:14px; margin:-6px 0; border-radius:7px; }
    """)

    icon = _load_app_icon()
    if icon is not None:
        app.setWindowIcon(icon)

    w = MainWindow()
    if icon is not None:
        w.setWindowIcon(icon)
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()