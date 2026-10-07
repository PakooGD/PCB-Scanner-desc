"""
Локализация RU/EN.
"""
from __future__ import annotations

from source.config import SETTINGS


I18N = {
    "ru": {
        "app_title": "Техноулей",
        "app_sub": "PCB Scanner",
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
        "step_x": "Шаг X, мм",
        "step_y": "Шаг Y, мм",
        "settle_s": "Пауза, с",
        "snake": "Змейкой",
        "start": "Старт",
        "stop": "",
        "demo": "Демо",
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
        "app_title": "Technouley",
        "app_sub": "PCB Scanner",
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
        "step_x": "Step X, mm",
        "step_y": "Step Y, mm",
        "settle_s": "Settle, s",
        "snake": "Snake pattern",
        "start": "Start",
        "stop": "",
        "demo": "Demo",
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

LANG = SETTINGS.value("lang", "ru")


def t(key: str) -> str:
    return I18N.get(LANG, I18N["ru"]).get(key, key)


def set_lang(lang: str) -> None:
    global LANG
    if lang in ("ru", "en"):
        LANG = lang
        SETTINGS.setValue("lang", lang)


def toggle_lang() -> str:
    new = "en" if LANG == "ru" else "ru"
    set_lang(new)
    return new