@echo off
setlocal EnableDelayedExpansion

echo ============================================================
echo   PCB Microscope Scanner - Linux AppImage build
echo ============================================================
echo.

REM --- 0. Проверка Docker ---
where docker >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker not found in PATH.
    echo         Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/
    exit /b 1
)

docker info >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Docker daemon is not running. Start Docker Desktop first.
    exit /b 1
)

REM --- 1. Проверка обязательных файлов ---
for %%F in (Dockerfile.appimage pcb-scanner-linux.spec pcb-scanner.desktop requirements.txt main.py static\logo.png) do (
    if not exist "%%F" (
        echo [ERROR] Missing file: %%F
        exit /b 1
    )
)

REM --- 2. .desktop в LF (иначе linuxdeploy не найдёт иконку) ---
echo [1/4] Normalizing pcb-scanner.desktop to LF...
powershell -NoProfile -Command ^
  "$p = 'pcb-scanner.desktop'; $c = [IO.File]::ReadAllText($p) -replace \"`r`n\", \"`n\" -replace \"`r\", \"`n\"; [IO.File]::WriteAllText($p, $c, (New-Object Text.UTF8Encoding $false))"
if errorlevel 1 (
    echo [ERROR] Failed to normalize .desktop
    exit /b 1
)

REM --- 3. Сборка Docker-образа ---
echo.
echo [2/4] Building Docker image (pcb-scanner-builder)...
docker build -f Dockerfile.appimage -t pcb-scanner-builder .
if errorlevel 1 (
    echo [ERROR] Docker build failed.
    exit /b 1
)

REM --- 4. PyInstaller ---
echo.
echo [3/4] Running PyInstaller (onedir)...
docker run --rm -v "%CD%:/src" -w /src pcb-scanner-builder bash -c "rm -rf build dist AppDir && pyinstaller --clean --noconfirm pcb-scanner-linux.spec"
if errorlevel 1 (
    echo [ERROR] PyInstaller failed.
    exit /b 1
)

REM --- 5. Проверка Qt-плагина ---
echo.
echo       Checking libqxcb.so...
docker run --rm -v "%CD%:/src" -w /src pcb-scanner-builder bash -c "find dist/pcb-scanner -name 'libqxcb.so' | grep -q . || (echo 'qxc plugin missing'; exit 1)"
if errorlevel 1 (
    echo [ERROR] Qt platform plugin libqxcb.so not found in dist.
    exit /b 1
)

REM --- 6. AppImage ---
echo.
echo [4/4] Packaging AppImage...
docker run --rm -v "%CD%:/src" -w /src pcb-scanner-builder bash -c "rm -rf AppDir; mkdir -p AppDir/usr/bin; cp -r dist/pcb-scanner/. AppDir/usr/bin/; linuxdeploy --appdir AppDir --executable AppDir/usr/bin/pcb-scanner --desktop-file pcb-scanner.desktop --icon-file static/logo.png --output appimage"
if errorlevel 1 (
    echo [ERROR] linuxdeploy/appimagetool failed.
    exit /b 1
)

REM --- 7. Итог ---
echo.
echo ============================================================
echo   DONE
echo ============================================================
for %%F in (PCB_Microscope_Scanner-x86_64.AppImage) do (
    if exist "%%F" (
        echo File:  %%F
        for %%A in ("%%F") do echo Size:  %%~zA bytes
    ) else (
        echo [WARN] AppImage not found - check log above.
    )
)
echo.
echo To give to a Linux user:
echo   chmod +x PCB_Microscope_Scanner-x86_64.AppImage
echo   ./PCB_Microscope_Scanner-x86_64.AppImage
echo.
endlocal
pause