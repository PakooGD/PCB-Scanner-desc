================================================================
 PCB Microscope Scanner — README
================================================================

Сканер плат под микроскопом: управление GRBL, камера, автосъёмка
сетки, сетка снимков, RU/EN, демо-режим.

----------------------------------------------------------------
1. ЧТО НУЖНО ДЛЯ СБОРКИ
----------------------------------------------------------------

Windows-сборка (build_windows.bat):
  • Python 3.10+ с галочкой "Add to PATH"
    https://www.python.org/downloads/windows/
  • Inno Setup 6 (для .exe-инсталлятора)
    https://jrsoftware.org/isdl.php
    Если Inno Setup не установлен — соберётся только
    dist-win\pcb-scanner.exe без инсталлятора.

Linux-сборка (build_linux.bat):
  • Docker Desktop для Windows
    https://docs.docker.com/desktop/setup/install/windows-install/
    После установки — переключить в режим "Linux containers".

----------------------------------------------------------------
2. КАК СОБРАТЬ
----------------------------------------------------------------

Двойной клик по нужному файлу:

  build_windows.bat   →  dist-win\pcb-scanner.exe
                         Output\PCB-Scanner-Setup.exe

  build_linux.bat     →  Output\PCB_Microscope_Scanner-x86_64.AppImage

Первый запуск Linux-сборки занимает 3–8 минут (скачивается
Ubuntu-образ и инструменты). Последующие — 1–2 минуты.

Все промежуточные файлы складываются в build\windows\ и
build\linux\ — корень проекта остаётся чистым.

----------------------------------------------------------------
3. ЧТО ПОЯВЛЯЕТСЯ В OUTPUT
----------------------------------------------------------------

  PCB-Scanner-Setup.exe
      Установщик для Windows. Двойной клик — установка в
      "C:\Program Files\PCB Microscope Scanner\", ярлыки в
      меню Пуск и на рабочем столе, запись в "Программы и
      компоненты", деинсталлятор unins000.exe.

  PCB_Microscope_Scanner-x86_64.AppImage
      Портативное приложение для Linux. Один файл, без установки.

----------------------------------------------------------------
4. КАК ПОЛЬЗОВАТЬСЯ ПОСЛЕ СБОРКИ
----------------------------------------------------------------

Windows:
  Запустить Output\PCB-Scanner-Setup.exe, следовать мастеру.

Linux:
  Передать пользователю один файл PCB_Microscope_Scanner-x86_64.AppImage.
  На целевой машине:

      chmod +x PCB_Microscope_Scanner-x86_64.AppImage
      ./PCB_Microscope_Scanner-x86_64.AppImage

  Если система просит FUSE:
      sudo apt install libfuse2      # Ubuntu / Debian
      sudo dnf install fuse          # Fedora
      sudo pacman -S fuse2           # Arch

  Доступ к GRBL-порту (один раз, затем перелогиниться):
      sudo usermod -aG dialout $USER

----------------------------------------------------------------
5. ГДЕ ХРАНЯТСЯ СНИМКИ
----------------------------------------------------------------

Windows:
  %LOCALAPPDATA%\PCB-Microscope-Scanner\captures\
  (C:\Users\<Имя>\AppData\Local\PCB-Microscope-Scanner\captures\)

Linux:
  ~/.local/share/PCB-Microscope-Scanner/captures/

Папку можно изменить прямо в приложении: раздел "Снимки" →
"Папка сохранения" → кнопка «…». Выбор запоминается.

----------------------------------------------------------------
6. КОРЕНЬ ПРОЕКТА
----------------------------------------------------------------

  main.py
  requirements.txt
  static\logo.png       (256×256, RGBA, 8-bit — для AppImage)
  static\logo.ico       (для иконки Windows .exe и установщика)
  static\logo.svg       (опционально, для UI)
  build_windows.bat
  build_linux.bat
  README.md

----------------------------------------------------------------
7. ОЧИСТКА
----------------------------------------------------------------

Удалить папки build\, dist-win\, dist-linux\, Output\, AppDir\
и файл *.AppImage вручную, либо через:

  rmdir /s /q build dist-win dist-linux Output
  del /q *.AppImage

Виртуальное окружение .venv тоже можно удалить:
  rmdir /s /q .venv

----------------------------------------------------------------
8. ТИПИЧНЫЕ ПРОБЛЕМЫ
----------------------------------------------------------------

[Windows] "Python not found"
  → Переустановите Python, отметив "Add Python to PATH".

[Windows] Inno Setup не найден
  → Установите Inno Setup 6 или используйте только
    dist-win\pcb-scanner.exe без установщика.

[Linux] "Docker daemon is not running"
  → Запустите Docker Desktop и дождитесь статуса Running.

[Linux] "Could not find suitable icon"
  → static\logo.png должен быть квадратным 256×256 RGBA 8-bit.
    Пересоздайте: python -c "from PIL import Image; im=Image.open('static/logo.png').convert('RGBA'); im.resize((256,256), Image.LANCZOS).save('static/logo.png')"

[Linux] AppImage не запускается у пользователя
  → Установите libfuse2 (см. раздел 4).

[GRBL] "Permission denied"
  → Linux: sudo usermod -aG dialout $USER и перелогиниться.
    Windows: драйвер CH340/CP210x + проверить COM-порт.

----------------------------------------------------------------
9. ОБНОВЛЕНИЕ ВЕРСИИ
----------------------------------------------------------------

Откройте build_windows.bat, измените:
    set "APP_VERSION=1.0.0"  →  set "APP_VERSION=1.0.1"

Аналогично в build_linux.bat, если там есть версия.
AppId в installer.iss НЕ меняйте — иначе Windows
посчитает обновление новой программой.

================================================================