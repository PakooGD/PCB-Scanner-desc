"""
Фоновые задачи: автосканирование сетки и демо-режим.
Общаются с UI через сигналы UiSignals.
"""
from __future__ import annotations

import json
import time
from typing import Dict

import cv2
from PySide6.QtCore import QObject, Signal

from source.i18n import t
from source.image_utils import apply_adjust, bgr_to_qpixmap
from source.services.state import AppState


class UiSignals(QObject):
    log = Signal(str)
    scan_progress = Signal(int, int, str)
    scan_done = Signal(str)
    demo_tick = Signal(int, int, int, str)
    demo_phase = Signal(int, int, str)
    demo_state = Signal(bool)
    captures_changed = Signal()


def run_scan(state: AppState,
             signals: UiSignals,
             rows: int, cols: int,
             step_x: float, step_y: float,
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


def run_demo(state: AppState,
             signals: UiSignals,
             rows: int, cols: int,
             step_x: float, step_y: float,
             feed: float, snake: bool, settle: float,
             stop_flag: Dict[str, bool]):
    """
    Демо: бесконечный проход, снимок → сохранить → удалить, кадр остаётся в сетке.
    """
    grbl = state.grbl
    cam = state.camera
    if grbl is None:
        signals.scan_done.emit(t("grbl_not_connected"))
        signals.demo_state.emit(False)
        return
    if cam is None:
        signals.scan_done.emit(t("cam_not_connected"))
        signals.demo_state.emit(False)
        return

    if state.session_dir is None:
        state.new_session()
    session = state.session_dir

    state.grid_rows = rows
    state.grid_cols = cols
    signals.demo_state.emit(True)

    tick = 0
    try:
        try:
            grbl.wait_idle(timeout=5)
        except Exception:
            pass
        x0 = grbl.status.get("x", 0.0)
        y0 = grbl.status.get("y", 0.0)

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

                    frame = cam.get()
                    if frame is None:
                        continue
                    frame = apply_adjust(frame,
                                         state.brightness,
                                         state.contrast,
                                         state.saturation)

                    fname = state.make_filename(r, c)
                    fpath = session / fname
                    cv2.imwrite(str(fpath), frame)

                    pix = bgr_to_qpixmap(frame)

                    state.captures = [
                        cap for cap in state.captures
                        if not (cap["row"] == r and cap["col"] == c)
                    ]
                    state.captures.append({
                        "row": r, "col": c,
                        "file": fname,
                        "pixmap": pix,
                    })

                    tick += 1
                    signals.demo_tick.emit(tick, r, c, t("phase_shooting"))
                    signals.captures_changed.emit()

                    t_end = time.time() + 0.12
                    while not stop_flag["stop"] and time.time() < t_end:
                        time.sleep(0.02)

                    try:
                        if fpath.exists():
                            fpath.unlink()
                    except Exception as e:
                        signals.log.emit(f"demo unlink: {e}")

                if stop_flag["stop"]:
                    break
    finally:
        signals.demo_state.emit(False)
        signals.scan_done.emit(t("demo_stopped"))