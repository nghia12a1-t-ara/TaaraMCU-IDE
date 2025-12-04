; Taara IDE Installer Script
; Created with Inno Setup 6

#define MyAppName "Taara IDE"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Taara MCU"
#define MyAppURL "https://github.com/yourusername/taara-ide"
#define MyAppExeName "TaaraIDE.exe"

[Setup]
; Basic app information
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
LicenseFile=LICENSE
; Output configuration
OutputDir=installer_output
OutputBaseFilename=TaaraIDE-{#MyAppVersion}-Setup
SetupIconFile=taara_ide\icons\app_icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

; Windows version requirements
MinVersion=10.0.17763
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

; Privileges
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 0,6.1

[Files]
; Main executable
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

; All DLL files and dependencies
Source: "dist\*.dll"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Qt plugins
Source: "dist\platforms\*"; DestDir: "{app}\platforms"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "dist\styles\*"; DestDir: "{app}\styles"; Flags: ignoreversion recursesubdirs createallsubdirs; AfterInstall: CreateEmptyDirs

; Icons and resources
Source: "taara_ide\icons\*"; DestDir: "{app}\taara_ide\icons"; Flags: ignoreversion recursesubdirs createallsubdirs

; Documentation
Source: "BUILD.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\taara_ide\.cache"
Type: filesandordirs; Name: "{localappdata}\TaaraIDE"

[Code]
procedure CreateEmptyDirs;
begin
  // Create necessary directories that might not exist
  ForceDirectories(ExpandConstant('{app}\taara_ide\.cache'));
  ForceDirectories(ExpandConstant('{app}\taara_ide\.cache\ctags'));
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
  // Check if another version is already installed
  if RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1') or
     RegKeyExists(HKEY_CURRENT_USER, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#SetupSetting("AppId")}_is1') then
  begin
    if MsgBox('Another version of Taara IDE is already installed. Do you want to uninstall it first?', mbConfirmation, MB_YESNO) = IDYES then
    begin
      // User chose to uninstall the old version first
      Result := True;
    end
    else
    begin
      // User chose not to uninstall, proceed with installation anyway
      Result := True;
    end;
  end;
end;
