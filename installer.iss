[Setup]
AppName=DesktopKioskCenter
AppVersion=1.0
DefaultDirName={commonpf}\DesktopKioskCenter
DefaultGroupName=DesktopKioskCenter
PrivilegesRequired=admin
OutputDir=.\Output
OutputBaseFilename=Installer_DesktopKioskCenter

[Files]
; 1. Se incluye el ejecutable principal desde la estructura real de dist
Source: ".\dist\DesktopKioskCenter\DesktopKioskCenter.exe"; DestDir: "{app}"; Flags: ignoreversion
; 2. Se incluye absolutamente todo el contenido de la carpeta (incluyendo _internal y css) para que no falte nada al ejecutar
Source: ".\dist\DesktopKioskCenter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; 3. El certificado público necesario para instalar la confianza local
Source: ".\kioskoce_cert.cer"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
; Acceso directo en el Menú de Inicio para todos los usuarios
Name: "{group}\DesktopKioskCenter"; Filename: "{app}\DesktopKioskCenter.exe"


[Run]
Filename: "certutil.exe"; Parameters: "-addstore -f ""Root"" ""{tmp}\kioskoce_cert.cer"""; StatusMsg: "Configurando certificado de confianza (Raíz)..."; Flags: runhidden
Filename: "certutil.exe"; Parameters: "-addstore -f ""TrustedPublisher"" ""{tmp}\kioskoce_cert.cer"""; StatusMsg: "Configurando certificado de confianza (Editor)..."; Flags: runhidden
Filename: "netsh.exe"; Parameters: "advfirewall firewall add rule name=""DesktopKioskCenter_In"" dir=in action=allow protocol=TCP localport=7085 program=""{app}\DesktopKioskCenter.exe"" enable=yes"; StatusMsg: "Configurando reglas de red en el Firewall..."; Flags: runhidden

Filename: "{app}\DesktopKioskCenter.exe"; Description: "{cm:LaunchProgram,DesktopKioskCenter}"; Flags: nowait postinstall skipifsilent

[UninstallRun]
; Limpieza exclusiva del certificado al desinstalar
Filename: "netsh.exe"; Parameters: "advfirewall firewall delete rule name=""DesktopKioskCenter_In"""; Flags: runhidden; RunOnceId: "RemoveKioskFirewall"
Filename: "certutil.exe"; Parameters: "-delstore ""Root"" ""DesktopKioskCenter"""; Flags: runhidden; RunOnceId: "RemoveKioskRootCert"
Filename: "certutil.exe"; Parameters: "-delstore ""TrustedPublisher"" ""DesktopKioskCenter"""; Flags: runhidden; RunOnceId: "RemoveKioskPubCert"
