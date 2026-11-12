[Setup]
AppName=Rack Designer
; Not derived from app.APP_VERSION (app/__init__.py) — this is build
; tooling (Inno Setup), not Python app code, so it can't import that
; constant. Bump this by hand on every version change; it won't follow
; APP_VERSION automatically. Same applies to OutputBaseFilename= below.
AppVersion=0.1.21
AppPublisher=Stage Tools
AppPublisherURL=https://stage-tools.github.io/stagetools/
AppSupportURL=https://stage-tools.github.io/stagetools/
AppUpdatesURL=https://stage-tools.github.io/stagetools/
DefaultDirName={autopf}\Stage Tools\Rack Designer
DefaultGroupName=Stage Tools\Rack Designer
AllowNoIcons=yes
OutputDir=release\v0.1.21
LicenseFile=LICENSE
OutputBaseFilename=RackDesigner_v0.1.21_Setup
SetupIconFile=RackDesigner_v0.1.21\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\RackDesigner_v0.1.21.exe
UninstallDisplayName=Rack Designer

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "RackDesigner_v0.1.21\dist\RackDesigner_v0.1.21.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "legal\THIRD-PARTY-NOTICES.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\Rack Designer"; Filename: "{app}\RackDesigner_v0.1.21.exe"
Name: "{group}\Uninstall Rack Designer"; Filename: "{uninstallexe}"
Name: "{commondesktop}\Rack Designer"; Filename: "{app}\RackDesigner_v0.1.21.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\RackDesigner_v0.1.21.exe"; Description: "Launch Rack Designer"; Flags: nowait postinstall skipifsilent
