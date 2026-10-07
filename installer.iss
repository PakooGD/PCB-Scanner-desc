; ============================================================
;  PCB Microscope Scanner — Inno Setup script
;  Собирает установщик PCB-Scanner-Setup.exe для Windows.
;
;  Перед сборкой выполните build_windows.bat — в dist\ должен
;  лежать pcb-scanner.exe (и, при onedir-сборке, вся папка
;  dist\pcb-scanner\).
;
;  Откройте этот файл в Inno Setup Compiler (ISCC.exe) и нажмите F9.
; ============================================================

#define AppName        "PCB Microscope Scanner"
#define AppVersion     "1.0.0"
#define AppPublisher   "PCB Microscope"
#define AppExeName     "pcb-scanner.exe"

; ---- ПУТИ К СБОРКЕ -----------------------------------------
; Onefile:
#define SourceExe      "dist\pcb-scanner.exe"
; Onedir (раскомментируйте и закомментируйте строку выше):
; #define SourceDir   "dist\pcb-scanner"
; ----------------------------------------------

[Setup]
; Уникальный AppId — НЕ меняйте между версиями, иначе Windows
; будет считать обновления новой программой.
AppId={{B7A9C2E4-1D3F-4A6B-9E21-8C5F0A7B3D11}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
LicenseFile=
OutputDir=Output
OutputBaseFilename=PCB-Scanner-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
ArchitecturesAllowed=x64
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

; ---- Uninstall ----
Uninstallable=yes
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\logo.ico
UninstallFilesDir={app}

; ---- Иконка установщика (Windows ждёт .ico) ----
SetupIconFile=static\logo.ico

; Красивая картинка мастера (опционально)
; WizardImageFile=static\wizard.bmp
; WizardSmallImageFile=static\wizard-small.bmp

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1

[Files]
; --- Onefile ---
Source: "{#SourceExe}";        DestDir: "{app}"; Flags: ignoreversion

; --- Onedir (раскомментируйте и закомментируйте строку выше) ---
; Source: "{#SourceDir}\*";    DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Кладём иконку рядом с exe — используется для UninstallDisplayIcon
Source: "static\logo.ico";     DestDir: "{app}"; Flags: ignoreversion
Source: "static\logo.png";     DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
; Программы в меню Пуск
Name: "{group}\{#AppName}";                          Filename: "{app}\{#AppExeName}"; IconFilename: "{app}\logo.ico"
Name: "{group}\Снимки";                              Filename: "{localappdata}\PCB-Microscope-Scanner\captures"
Name: "{group}\{cm:UninstallProgram,{#AppName}}";    Filename: "{uninstallexe}"

; Ярлык на рабочем столе (по задаче)
Name: "{autodesktop}\{#AppName}";                    Filename: "{app}\{#AppExeName}"; Tasks: desktopicon; IconFilename: "{app}\logo.ico"

; Быстрый запуск (старые Windows)
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Что удалять при деинсталляции, помимо файлов, установленных инсталлятором.
Type: filesandordirs; Name: "{app}\static"
Type: filesandordirs; Name: "{app}\__pycache__"
Type: files;          Name: "{app}\*.log"
Type: files;          Name: "{app}\logo.ico"
Type: files;          Name: "{app}\logo.png"

[Code]
// Спрашиваем пользователя, удалять ли папку captures при деинсталляции.
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  CapturesDir: String;
  Res: Integer;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    CapturesDir := ExpandConstant('{localappdata}\PCB-Microscope-Scanner\captures');
    if DirExists(CapturesDir) then
    begin
      Res := MsgBox('Удалить папку со снимками?' + #13#10 + CapturesDir,
                    mbConfirmation, MB_YESNO);
      if Res = IDYES then
      begin
        DelTree(CapturesDir, True, True, True);
        RemoveDir(ExpandConstant('{localappdata}\PCB-Microscope-Scanner'));
      end;
    end;
  end;
end;