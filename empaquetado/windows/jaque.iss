; Instalador de Jaque para Windows (Inno Setup 6).
; Lo compila construir.ps1:  ISCC /DMiVersion=0.6.0 jaque.iss

#ifndef Raiz
  #define Raiz ".."
#endif
#ifndef MiVersion
  #define MiVersion "0.0.0"
#endif

[Setup]
AppId={{6E7A2B1C-4D3F-4A8B-9C5E-1F2A3B4C5D6E}
AppName=Jaque
AppVersion={#MiVersion}
AppVerName=Jaque {#MiVersion}
AppPublisher=Ricardo
DefaultDirName={localappdata}\Programs\Jaque
DefaultGroupName=Jaque
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir={#Raiz}\salida
OutputBaseFilename=Jaque-{#MiVersion}-instalador-windows
SetupIconFile={#Raiz}\empaquetado\windows\jaque.ico
UninstallDisplayIcon={app}\jaque.exe
UninstallDisplayName=Jaque {#MiVersion}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0.17763

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "escritorio"; Description: "Crear un ícono en el escritorio"; GroupDescription: "Accesos directos:"

[Files]
; dist\jaque ya contiene motor\ (Stockfish) y recursos\ (gráficos, sonidos, partidas)
Source: "{#Raiz}\dist\jaque\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Jaque"; Filename: "{app}\jaque.exe"; Comment: "Ajedrez en español"
Name: "{group}\Verificar instalación de Jaque"; Filename: "{app}\jaque.exe"; Parameters: "--verificar"
Name: "{group}\Desinstalar Jaque"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Jaque"; Filename: "{app}\jaque.exe"; Tasks: escritorio

[Run]
Filename: "{app}\jaque.exe"; Parameters: "--preparar-cache"; StatusMsg: "Preparando piezas y sonidos…"; Flags: runhidden waituntilterminated
Filename: "{app}\jaque.exe"; Description: "Abrir Jaque ahora"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{localappdata}\Jaque\cache"
Type: files; Name: "{localappdata}\Jaque\verificacion.txt"
