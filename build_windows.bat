@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul

REM ============================================================
REM  PCB Microscope Scanner - Windows build
REM  Double-click: builds dist-win\pcb-scanner.exe
REM  and Output\PCB-Scanner-Setup.exe (if Inno Setup is installed).
REM ============================================================

set "APP_NAME=PCB Microscope Scanner"
set "APP_VERSION=1.0.0"
set "APP_PUBLISHER=PCB Microscope"
set "APP_EXE=pcb-scanner.exe"

REM %~dp0 always ends with a backslash.
REM   ROOT    - with trailing backslash, for local file paths (e.g. %ROOT%main.py)
REM   ROOT_PY - without trailing backslash, for Python strings (e.g. Path(r"%ROOT_PY%"))
set "ROOT=%~dp0"
set "ROOT_PY=%ROOT:~0,-1%"
cd /d "%ROOT%"

set "BUILD_DIR=%ROOT%build\windows"
set "DIST_DIR=%ROOT%dist-win"
set "OUT_DIR=%ROOT%Output"

echo ============================================================
echo   PCB Microscope Scanner - WINDOWS build
echo ============================================================
echo.

REM --- 0. Python ---
where python >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.10+ and enable "Add to PATH".
    pause
    exit /b 1
)

REM --- 1. Required files ---
for %%F in (main.py requirements.txt static\logo.ico) do (
    if not exist "%%F" (
        echo [ERROR] Missing required file: %%F
        pause
        exit /b 1
    )
)

REM --- 2. venv + dependencies ---
if not exist ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 ( echo [ERROR] venv creation failed & pause & exit /b 1 )
)
call ".venv\Scripts\activate.bat"

echo Upgrading pip...
python -m pip install --upgrade pip >nul

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 ( echo [ERROR] pip install failed & pause & exit /b 1 )

REM --- 3. Folders ---
if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%"
if not exist "%OUT_DIR%"  mkdir "%OUT_DIR%"

REM --- 4. Generate spec ---
echo [1/3] Preparing spec...
call :gen_spec
if errorlevel 1 ( echo [ERROR] spec generation failed & pause & exit /b 1 )

REM --- 5. PyInstaller ---
echo [2/3] Running PyInstaller...
if exist "%BUILD_DIR%\pyi" rmdir /s /q "%BUILD_DIR%\pyi"
pyinstaller --clean --noconfirm ^
    --distpath "%DIST_DIR%" ^
    --workpath "%BUILD_DIR%\pyi" ^
    "%BUILD_DIR%\pcb-scanner.spec"
if errorlevel 1 ( echo [ERROR] PyInstaller failed & pause & exit /b 1 )

echo       Binary ready: %DIST_DIR%\%APP_EXE%

REM --- 6. Inno Setup ---
echo [3/3] Building installer...
set "ISCC="

REM 1) Try PATH
for /f "delims=" %%I in ('where ISCC 2^>nul') do (
    set "ISCC=%%I"
    goto :iscc_found
)

REM 2) Standard install locations (newest first)
for %%P in (
    "%ProgramFiles%\Inno Setup 7\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 7\ISCC.exe"
    "%LocalAppData%\Programs\Inno Setup 7\ISCC.exe"
    "%ProgramFiles%\Inno Setup 6\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
    "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
    "%ProgramFiles%\Inno Setup 5\ISCC.exe"
    "%ProgramFiles(x86)%\Inno Setup 5\ISCC.exe"
) do (
    if exist %%P (
        set "ISCC=%%~P"
        goto :iscc_found
    )
)

:iscc_found
if not defined ISCC (
    echo [WARN] Inno Setup not found.
    echo        Install: https://jrsoftware.org/isdl.php
    echo        Binary is ready at %DIST_DIR%\%APP_EXE%
    echo.
    pause
    exit /b 0
)

if not defined ISCC (
    echo [WARN] Inno Setup not found.
    echo        Install: https://jrsoftware.org/isdl.php
    echo        Binary is ready at %DIST_DIR%\%APP_EXE%
    echo.
    pause
    exit /b 0
)

call :gen_iss
if errorlevel 1 ( echo [ERROR] iss generation failed & pause & exit /b 1 )

"%ISCC%" /Qp "%BUILD_DIR%\installer.iss"
if errorlevel 1 ( echo [ERROR] ISCC failed & pause & exit /b 1 )

echo.
echo ============================================================
echo   DONE (Windows)
echo ============================================================
echo   Binary:    %DIST_DIR%\%APP_EXE%
echo   Installer: %OUT_DIR%\PCB-Scanner-Setup.exe
echo ============================================================
echo.
pause
exit /b 0

REM ============================================================
:gen_spec
(
echo # -*- mode: python ; coding: utf-8 -*-
echo from pathlib import Path
echo ROOT = Path^(r"%ROOT_PY%"^)
echo STATIC = ROOT / "static"
echo datas = [^(str^(STATIC^), "static"^)] if STATIC.exists^(^) else []
echo icon = None
echo p = STATIC / "logo.ico"
echo if p.exists^(^): icon = str^(p^)
echo a = Analysis^(
echo     ["%ROOT%main.py"],
echo     pathex=[str^(ROOT^)],
echo     datas=datas,
echo     excludes=["tkinter", "matplotlib"],
echo ^)
echo pyz = PYZ^(a.pure, a.zipped_data^)
echo exe = EXE^(
echo     pyz, a.scripts, a.binaries, a.zipfiles, a.datas, [],
echo     name="pcb-scanner", debug=False, strip=False, upx=True,
echo     console=False, icon=icon,
echo ^)
) > "%BUILD_DIR%\pcb-scanner.spec"
exit /b 0

:gen_iss
(
echo #define AppName "%APP_NAME%"
echo #define AppVersion "%APP_VERSION%"
echo #define AppPublisher "%APP_PUBLISHER%"
echo #define AppExeName "%APP_EXE%"
echo.
echo [Setup]
echo AppId={{B7A9C2E4-1D3F-4A6B-9E21-8C5F0A7B3D11}
echo AppName={#AppName}
echo AppVersion={#AppVersion}
echo AppVerName={#AppName} {#AppVersion}
echo AppPublisher={#AppPublisher}
echo DefaultDirName={autopf}\{#AppName}
echo DefaultGroupName={#AppName}
echo DisableProgramGroupPage=yes
echo OutputDir=%OUT_DIR%
echo OutputBaseFilename=PCB-Scanner-Setup
echo Compression=lzma2
echo SolidCompression=yes
echo ArchitecturesInstallIn64BitMode=x64
echo ArchitecturesAllowed=x64
echo WizardStyle=modern
echo PrivilegesRequired=admin
echo Uninstallable=yes
echo UninstallDisplayName={#AppName}
echo UninstallDisplayIcon={app}\logo.ico
echo UninstallFilesDir={app}
echo SetupIconFile=%ROOT%static\logo.ico
echo.
echo [Languages]
echo Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
echo Name: "english"; MessagesFile: "compiler:Default.isl"
echo.
echo [Tasks]
echo Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
echo.
echo [Files]
echo Source: "%DIST_DIR%\%APP_EXE%"; DestDir: "{app}"; Flags: ignoreversion
echo Source: "%ROOT%static\logo.ico"; DestDir: "{app}"; Flags: ignoreversion
echo Source: "%ROOT%static\logo.png"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
echo.
echo [Icons]
echo Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"
echo Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
echo Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon; IconFilename: "{app}\logo.ico"
echo.
echo [Run]
echo Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
echo.
echo [UninstallDelete]
echo Type: filesandordirs; Name: "{app}\static"
echo Type: files; Name: "{app}\logo.ico"
echo Type: files; Name: "{app}\logo.png"
echo.
echo [Code]
echo procedure CurUninstallStepChanged^(CurUninstallStep: TUninstallStep^);
echo var D: String; R: Integer;
echo begin
echo   if CurUninstallStep = usPostUninstall then begin
echo     D := ExpandConstant^('{localappdata}\PCB-Microscope-Scanner\captures'^);
echo     if DirExists^(D^) then begin
echo       R := MsgBox^('Удалить папку со снимками?' + #13#10 + D, mbConfirmation, MB_YESNO^);
echo       if R = IDYES then begin
echo         DelTree^(D, True, True, True^);
echo         RemoveDir^(ExpandConstant^('{localappdata}\PCB-Microscope-Scanner'^)^);
echo       end;
echo     end;
echo   end;
echo end;
) > "%BUILD_DIR%\installer.iss"
exit /b 0