@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

REM ============================================================
REM  PCB Microscope Scanner - Linux AppImage build (via Docker)
REM  Double-click: builds Output\PCB_Microscope_Scanner-x86_64.AppImage
REM ============================================================

set "APP_NAME=PCB Microscope Scanner"
set "APP_SLUG=pcb-scanner"
set "APPIMAGE_NAME=PCB_Microscope_Scanner-x86_64.AppImage"
set "DOCKER_IMAGE=pcb-scanner-builder"

REM --- Paths ---
REM %~dp0 always ends with a backslash.
REM   ROOT        - with trailing backslash, for local file paths
REM   ROOT_DOCKER - without trailing backslash, for docker -v / build args
set "ROOT=%~dp0"
set "ROOT_DOCKER=%ROOT:~0,-1%"
cd /d "%ROOT%"

set "BUILD_DIR=%ROOT%build\linux"
set "DIST_DIR=%ROOT%build\linux\dist-linux"
set "OUT_DIR=%ROOT%Output"

echo ============================================================
echo   PCB Microscope Scanner - LINUX AppImage build
echo ============================================================
echo.

REM --- 0. Docker ---
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker not found.
    echo         Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/
    pause
    exit /b 1
)
docker info >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Start Docker Desktop first.
    pause
    exit /b 1
)

REM --- 1. Required files ---
for %%F in (main.py requirements.txt source\static\logo.png) do (
    if not exist "%%F" (
        echo [ERROR] Missing required file: %%F
        pause
        exit /b 1
    )
)

REM --- 2. Folders ---
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if not exist "%OUT_DIR%"  mkdir "%OUT_DIR%"

REM --- 3. Generate helper files ---
echo [1/5] Generating .desktop, Dockerfile, spec...
call :gen_desktop
if errorlevel 1 ( echo [ERROR] .desktop generation failed & pause & exit /b 1 )
call :gen_dockerfile
if errorlevel 1 ( echo [ERROR] Dockerfile generation failed & pause & exit /b 1 )
call :gen_spec
if errorlevel 1 ( echo [ERROR] spec generation failed & pause & exit /b 1 )

REM --- 4. Docker image ---
echo [2/5] Building Docker image (first run may take several minutes)...
docker build -f "%BUILD_DIR%\Dockerfile.appimage" -t %DOCKER_IMAGE% "%ROOT_DOCKER%"
if errorlevel 1 ( echo [ERROR] Docker build failed & pause & exit /b 1 )

REM --- 5. PyInstaller (onedir) ---
echo [3/5] Running PyInstaller inside container...
docker run --rm -v "%ROOT_DOCKER%:/src" -w /src %DOCKER_IMAGE% bash -c "rm -rf build/linux/dist build/linux/pyi && pyinstaller --clean --noconfirm --distpath build/linux/dist --workpath build/linux/pyi build/linux/pcb-scanner-linux.spec"
if errorlevel 1 ( echo [ERROR] PyInstaller failed & pause & exit /b 1 )

echo       Checking libqxcb.so...
docker run --rm -v "%ROOT_DOCKER%:/src" -w /src %DOCKER_IMAGE% bash -c "find build/linux/dist/pcb-scanner -name 'libqxcb.so' | grep -q . || (echo 'qxc plugin missing'; exit 1)"
if errorlevel 1 ( echo [ERROR] Qt platform plugin libqxcb.so not found & pause & exit /b 1 )

REM --- 6. AppImage ---
echo [4/5] Packaging AppImage...
if exist "%BUILD_DIR%\AppDir" rmdir /s /q "%BUILD_DIR%\AppDir"
docker run --rm -v "%ROOT_DOCKER%:/src" -w /src %DOCKER_IMAGE% bash -c "mkdir -p build/linux/AppDir/usr/bin && cp -r build/linux/dist/pcb-scanner/. build/linux/AppDir/usr/bin/ && cp build/linux/pcb-scanner.desktop build/linux/AppDir/pcb-scanner.desktop && linuxdeploy --appdir build/linux/AppDir --executable build/linux/AppDir/usr/bin/pcb-scanner --desktop-file build/linux/pcb-scanner.desktop --icon-file source/static/logo.png --output appimage"
if errorlevel 1 ( echo [ERROR] linuxdeploy/appimagetool failed & pause & exit /b 1 )

REM --- 7. Move result to Output ---
echo [5/5] Copying AppImage to Output...
if exist "%ROOT%%APPIMAGE_NAME%" (
    move /y "%ROOT%%APPIMAGE_NAME%" "%OUT_DIR%\%APPIMAGE_NAME%" >nul
)

set "APPIMAGE_PATH=%OUT_DIR%\%APPIMAGE_NAME%"
if exist "!APPIMAGE_PATH!" (
    echo(
    echo ============================================================
    echo   DONE [Linux]
    echo ============================================================
    echo   AppImage: !APPIMAGE_PATH!
    echo(
    echo   To give to a Linux user:
    echo     chmod +x %APPIMAGE_NAME%
    echo     ./%APPIMAGE_NAME%
    echo ============================================================
) else (
    echo(
    echo [WARN] AppImage not found at: !APPIMAGE_PATH!
    echo        Check the log above.
)
echo(
pause
exit /b 0

REM ============================================================
:gen_desktop
powershell -NoProfile -Command ^
  "$c = \"[Desktop Entry]`nType=Application`nName=%APP_NAME%`nComment=PCB inspection scanner`nExec=%APP_SLUG%`nIcon=logo`nTerminal=false`nCategories=Utility;Science;`n\"; [IO.File]::WriteAllText('%BUILD_DIR%\pcb-scanner.desktop', $c, (New-Object Text.UTF8Encoding $false))"
exit /b 0

:gen_dockerfile
(
echo FROM ubuntu:22.04
echo ENV DEBIAN_FRONTEND=noninteractive
echo ENV LANG=C.UTF-8
echo ENV LC_ALL=C.UTF-8
echo ENV APPIMAGE_EXTRACT_AND_RUN=1
echo RUN apt-get update ^&^& apt-get install -y ^\
echo     python3 python3-pip python3-venv patchelf wget file fuse ^\
echo     libegl1 libgl1 libglx0 libgles2 libopengl0 ^\
echo     libx11-6 libxext6 libxrender1 libxi6 libxtst6 ^\
echo     libxkbcommon0 libxkbcommon-x11-0 ^\
echo     libxcb1 libxcb-cursor0 libxcb-xinerama0 libxcb-icccm4 ^\
echo     libxcb-image0 libxcb-keysyms1 libxcb-randr0 ^\
echo     libxcb-render-util0 libxcb-shape0 libxcb-xfixes0 ^\
echo     libxcb-sync1 libxcb-shm0 libxcb-glx0 libxcb-util1 ^\
echo     libfontconfig1 libfreetype6 libdbus-1-3 ^\
echo     libgtk-3-0 libpango-1.0-0 libpangocairo-1.0-0 ^\
echo     libcairo2 libcairo-gobject2 libgdk-pixbuf-2.0-0 ^\
echo     libharfbuzz0b libatk1.0-0 libatk-bridge2.0-0 ^\
echo     libglib2.0-0 ca-certificates ^\
echo     ^&^& rm -rf /var/lib/apt/lists/*
echo RUN wget -q https://github.com/linuxdeploy/linuxdeploy/releases/download/continuous/linuxdeploy-x86_64.AppImage -O /usr/local/bin/linuxdeploy ^\
echo  ^&^& wget -q https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage -O /usr/local/bin/appimagetool ^\
echo  ^&^& chmod +x /usr/local/bin/linuxdeploy /usr/local/bin/appimagetool
echo WORKDIR /src
echo COPY requirements.txt .
echo RUN pip3 install --upgrade pip ^&^& pip3 install -r requirements.txt
echo CMD ["bash"]
) > "%BUILD_DIR%\Dockerfile.appimage"
exit /b 0

:gen_spec
(
echo # -*- mode: python ; coding: utf-8 -*-
echo from pathlib import Path
echo from PyInstaller.utils.hooks import collect_data_files
echo ROOT = Path^(r"/src"^)
echo STATIC = ROOT / "source" / "static"
echo datas = [^(str^(STATIC^), "source/static"^)] if STATIC.exists^(^) else []
echo datas += collect_data_files^("PySide6", includes=["Qt/plugins/**/*"], excludes=["**/*.debug","**/*.pdb"]^)
echo hiddenimports = ["PySide6.QtCore","PySide6.QtGui","PySide6.QtWidgets","PySide6.QtSvg","PySide6.QtNetwork","serial.tools.list_ports_linux"]
echo a = Analysis^(
echo     ["/src/main.py"],
echo     pathex=[str^(ROOT^)],
echo     datas=datas,
echo     hiddenimports=hiddenimports,
echo     excludes=["tkinter","matplotlib","PyQt5","PyQt6","PySide2",
echo               "serial.tools.list_ports_windows","serial.tools.list_ports_osx"],
echo ^)
echo pyz = PYZ^(a.pure, a.zipped_data^)
echo exe = EXE^(pyz, a.scripts, [], exclude_binaries=True, name="pcb-scanner",
echo     debug=False, strip=False, upx=False, console=False^)
echo coll = COLLECT^(exe, a.binaries, a.zipfiles, a.datas,
echo     strip=False, upx=False, upx_exclude=[], name="pcb-scanner"^)
) > "%BUILD_DIR%\pcb-scanner-linux.spec"
exit /b 0