; Glossa installer — CI builds it with:
;   iscc /DAppVersion=<version> installer\glossa.iss
; Per-user install (no UAC prompt), Start-menu shortcut, optional desktop
; shortcut, uninstaller. The app keeps its settings next to the exe.

#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{D7C3A9E1-4B2F-4E8A-9C5D-2F6B8A1E3C70}
AppName=Glossa
AppVersion={#AppVersion}
AppPublisher=Astislav Bozhevolnov
AppPublisherURL=https://github.com/Astislav/glossa
AppSupportURL=https://github.com/Astislav/glossa/issues
DefaultDirName={autopf}\Glossa
PrivilegesRequired=lowest
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=Glossa-Setup
SetupIconFile=..\resources\icon.ico
UninstallDisplayIcon={app}\Glossa.exe
AppMutex=Local\Glossa
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
; The onedir build (folder of plain DLLs) — far fewer antivirus false
; positives than the self-extracting onefile exe.
Source: "..\dist\Glossa\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Glossa"; Filename: "{app}\Glossa.exe"
Name: "{autodesktop}\Glossa"; Filename: "{app}\Glossa.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Glossa.exe"; Description: "{cm:LaunchProgram,Glossa}"; Flags: nowait postinstall skipifsilent
