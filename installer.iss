#define AppName "DesktopKioskCenter"
#define AppVersion "1.0"
#define AppExeName "DesktopKioskCenter.exe"
#define DistOutputDir "dist\DesktopKioskCenter"

[Setup]
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputDir=Output
OutputBaseFilename=Installer_DesktopKioskCenter
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Files]
; PyInstaller genera una distribución onedir: el EXE y todos los recursos
; deben instalarse conservando la carpeta _internal y sus subdirectorios.
Source: "{#DistOutputDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Certificado público usado por DesktopKioskCenter.
Source: "kioskoce_cert.cer"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\DesktopKioskCenter"; Filename: "{app}\{#AppExeName}"

[Run]
; Instalar el certificado en los almacenes de confianza del equipo.
Filename: "{sys}\certutil.exe"; Parameters: "-addstore -f ""Root"" ""{tmp}\kioskoce_cert.cer"""; StatusMsg: "Instalando certificado raíz..."; Flags: runhidden waituntilterminated
Filename: "{sys}\certutil.exe"; Parameters: "-addstore -f ""TrustedPublisher"" ""{tmp}\kioskoce_cert.cer"""; StatusMsg: "Instalando certificado de editor..."; Flags: runhidden waituntilterminated

; Permitir conexiones entrantes a la API REST de DesktopKioskCenter.
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall add rule name=""DesktopKioskCenter_In"" dir=in action=allow protocol=TCP localport=7085 program=""{app}\{#AppExeName}"" enable=yes"; StatusMsg: "Configurando el Firewall..."; Flags: runhidden waituntilterminated

; Iniciar la aplicación al finalizar la instalación interactiva.
Filename: "{app}\{#AppExeName}"; Description: "{cm:LaunchProgram,DesktopKioskCenter}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "{sys}\netsh.exe"; Parameters: "advfirewall firewall delete rule name=""DesktopKioskCenter_In"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveKioskCenterFirewall"

; El sujeto del certificado es exactamente "DesktopKioskCenter For UAQ".
Filename: "{sys}\certutil.exe"; Parameters: "-delstore ""Root"" ""DesktopKioskCenter For UAQ"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveKioskCenterRootCert"
Filename: "{sys}\certutil.exe"; Parameters: "-delstore ""TrustedPublisher"" ""DesktopKioskCenter For UAQ"""; Flags: runhidden waituntilterminated; RunOnceId: "RemoveKioskCenterPublisherCert"
