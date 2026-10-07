"""
Контроллер GRBL: последовательный порт, отправка команд, статус.
"""
from __future__ import annotations

import queue
import threading
import time

import serial


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