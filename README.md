# PCB Microscope Scanner

Сканер плат под микроскопом: управление GRBL, камера, автосъёмка сетки,
сетка снимков, RU/EN, демо-режим.

Проект собирается в два нативных приложения:

- **Windows** — установщик `PCB-Scanner-Setup.exe` (Inno Setup).
- **Linux** — портативный `PCB_Microscope_Scanner-x86_64.AppImage` (один файл, без установки).

Оба билда запускаются **двойным кликом** по `.bat` из корня проекта.

---

## 1. Требования

### Для Windows-сборки (`build_windows.bat`)

- **Python 3.10+** с галочкой *Add Python to PATH*
  [python.org/downloads/windows](https://www.python.org/downloads/windows/)
- **Inno Setup 7** — для сборки `.exe`-инсталлятора
  [jrsoftware.org/isdl.php](https://jrsoftware.org/isdl.php)
  Если Inno Setup не установлен — соберётся только `build\windows\dist-win\pcb-scanner.exe` без установщика.

### Для Linux-сборки (`build_linux.bat`)

- **Docker Desktop для Windows**
  [docs.docker.com/desktop/setup/install/windows-install](https://docs.docker.com/desktop/setup/install/windows-install/)

---

## 2. Сборка

Двойной клик по нужному `.bat` в корне проекта:

| Файл | Что получается |
|---|---|
| `build_windows.bat` | `build\windows\dist-win\pcb-scanner.exe`<br>`Output\PCB-Scanner-Setup.exe` |
| `build_linux.bat` | `Output\PCB_Microscope_Scanner-x86_64.AppImage` |

- Первый запуск **Linux-сборки** занимает 3–8 минут — скачивается Ubuntu-образ и инструменты.
- Последующие — 1–2 минуты.
- Все промежуточные файлы складываются в `build\windows\` и `build\linux\` — **корень проекта остаётся чистым**.

---

## 3. Что появляется в `Output\`

### `PCB-Scanner-Setup.exe`

Установщик для Windows. Двойной клик — установка в
`C:\Program Files\PCB Microscope Scanner\`, ярлыки в меню «Пуск» и на
рабочем столе, запись в «Программы и компоненты», деинсталлятор
`unins000.exe`.

### `PCB_Microscope_Scanner-x86_64.AppImage`

Портативное приложение для Linux. Один файл, без установки.

---

## 4. Как пользоваться после сборки

### Windows

Запустите `Output\PCB-Scanner-Setup.exe` и следуйте мастеру.

### Linux

На целевой машине:

```bash
chmod +x PCB_Microscope_Scanner-x86_64.AppImage
./PCB_Microscope_Scanner-x86_64.AppImage
```

Если система просит FUSE:

```bash
sudo apt install libfuse2      # Ubuntu / Debian
sudo dnf install fuse          # Fedora
sudo pacman -S fuse2           # Arch
```

Доступ к GRBL-порту (один раз, затем перелогиниться):

```bash
sudo usermod -aG dialout $USER
```

---

## 5. Где хранятся снимки

### Windows

```
%LOCALAPPDATA%\PCB-Microscope-Scanner\captures\
```

то есть

```
C:\Users\<Имя>\AppData\Local\PCB-Microscope-Scanner\captures\
```

### Linux

```
~/.local/share/PCB-Microscope-Scanner/captures/
```

Папку можно изменить прямо в приложении:
раздел **«Снимки» → «Папка сохранения» → кнопка «…»**.
Выбор сохраняется между запусками.

---

## 6. Корень проекта

```
main.py
requirements.txt
static\logo.png       (256×256, RGBA, 8-bit — для AppImage)
static\logo.ico       (для иконки Windows .exe и установщика)
static\logo.svg       (опционально, для UI)
build_windows.bat
build_linux.bat
README.md
```

---

## 7. Очистка

Удалить папки `build\`, `Output\`

```bat
rmdir /s /q build Output
```

Виртуальное окружение `.venv` тоже можно удалить:

```bat
rmdir /s /q .venv
```

При следующей сборке оно создастся заново.

---

## 8. Типичные проблемы

| Симптом | Решение |
|---|---|
| **[Windows]** `Python not found` | Переустановите Python, отметив *Add Python to PATH*. |
| **[Windows]** `Inno Setup not found` | Установите Inno Setup 7 или используйте только `build\windows\dist-win\pcb-scanner.exe` без установщика. |
| **[Linux]** `Docker daemon is not running` | Запустите Docker Desktop и дождитесь статуса *Running*. |
| **[Linux]** `Could not find suitable icon` | `static\logo.png` должен быть **квадратным 256×256 RGBA 8-bit**. |
| **[Linux]** AppImage не запускается | Установите `libfuse2` (см. раздел 4). |
| **[GRBL]** `Permission denied` | Linux: `sudo usermod -aG dialout $USER` и перелогиниться.<br>Windows: драйвер CH340/CP210x + проверить COM-порт. |

---

## 9. Обновление версии

Откройте `*.bat` и измените:

```bat
set "APP_VERSION=1.0.0"     →     set "APP_VERSION=1.0.1"
```

> **Важно:** `AppId` в `installer.iss` (генерируется автоматически)
> **не меняйте** между версиями — иначе Windows посчитает обновление
> новой программой и поставит её рядом, а не поверх.