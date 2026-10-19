# ============================================================================
#  Construye el instalador de Jaque para Windows 11.
#  Uso:  empaquetado\windows\construir.bat  C:\ruta\a\tu\cd.iso
#  (el ISO solo hace falta la primera vez, para preparar la carpeta recursos\)
#
#  Pasos que hace solo:
#    1. Busca Python 3.13 (si no está, lo instala con winget)
#    2. Busca Inno Setup 6 (si no está, lo instala con winget)
#    3. Crea un entorno de Python aislado e instala las bibliotecas
#    4. Descarga Stockfish para Windows
#    5. Congela Jaque con PyInstaller (Python y bibliotecas adentro)
#    6. Arma el instalador .exe con Inno Setup
#  Resultado: salida\Jaque-<versión>-instalador-windows.exe
# ============================================================================
param([string]$Iso = "")
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"   # descargas mucho más rápidas
$Aqui = $PSScriptRoot
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location -LiteralPath $Raiz

function Titulo($t) { Write-Host ""; Write-Host "== $t ==" -ForegroundColor Yellow }
function Bien($t)   { Write-Host "  [OK] $t" -ForegroundColor Green }
function Mal($t)    { Write-Host "  [X]  $t" -ForegroundColor Red }
function Refrescar-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}

$Version = (Select-String -Path "jaque\__init__.py" -Pattern '"(.+)"').Matches[0].Groups[1].Value
Write-Host "Construyendo Jaque $Version para Windows" -ForegroundColor Cyan

# --- 1. Python 3.13 -----------------------------------------------------------
Titulo "Python"
function Buscar-Python {
    foreach ($c in @(
        { & py -3.13 -c "import sys; print(sys.executable)" 2>$null },
        { & python -c "import sys; assert sys.version_info[:2]==(3,13); print(sys.executable)" 2>$null })) {
        try { $r = & $c; if ($LASTEXITCODE -eq 0 -and $r) { return ($r | Select-Object -Last 1).Trim() } } catch {}
    }
    $tip = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"
    if (Test-Path $tip) { return $tip }
    return $null
}
$Py = Buscar-Python
if (-not $Py) {
    Write-Host "  Python 3.13 no está instalado. Instalándolo con winget…"
    winget install -e --id Python.Python.3.13 --scope user --accept-package-agreements --accept-source-agreements
    Refrescar-Path
    $Py = Buscar-Python
    if (-not $Py) { Mal "No pude instalar Python. Instalalo desde python.org (3.13, 64 bits) y volvé a ejecutar."; exit 1 }
}
Bien "Python: $Py"

# --- 2. Inno Setup 6 ------------------------------------------------------------
Titulo "Inno Setup"
function Buscar-ISCC {
    foreach ($p in @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
                     "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe")) { if (Test-Path $p) { return $p } }
    $c = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($c) { return $c.Source }
    return $null
}
$Iscc = Buscar-ISCC
if (-not $Iscc) {
    Write-Host "  Inno Setup no está instalado. Instalándolo con winget (puede pedir permiso)…"
    winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
    Refrescar-Path
    $Iscc = Buscar-ISCC
    if (-not $Iscc) { Mal "No pude instalar Inno Setup. Bajalo de jrsoftware.org/isdl.php y volvé a ejecutar."; exit 1 }
}
Bien "Inno Setup: $Iscc"

# --- 3. Entorno de Python y bibliotecas ---------------------------------------
Titulo "Bibliotecas de Python"
$Venv = Join-Path $Raiz ".venv"
if (-not (Test-Path "$Venv\Scripts\python.exe")) { & $Py -m venv $Venv }
$VPy = "$Venv\Scripts\python.exe"
& $VPy -m pip install --upgrade pip --quiet
& $VPy -m pip install --quiet -r "$Aqui\requirements-windows.txt"
if ($LASTEXITCODE -ne 0) { Mal "Falló la instalación de bibliotecas (¿hay internet?)."; exit 1 }
Bien "PySide6, numpy, scipy, Pillow, python-chess y PyInstaller instalados"

# --- 3b. Gráficos y sonidos (de TU copia del juego) ---------------------------
Titulo "Gráficos y sonidos"
if (Test-Path "recursos\JAQUE.RECURSOS") {
    Bien "Carpeta recursos\ ya preparada"
} else {
    if (-not $Iso -or -not (Test-Path $Iso)) {
        Mal "Falta la carpeta recursos\. Ejecutá:  empaquetado\windows\construir.bat C:\ruta\a\tu\cd.iso"
        exit 1
    }
    & $VPy -c "from pathlib import Path; from jaque.preparar import preparar; preparar(r'$Iso', Path('recursos'), avisar=lambda t: None)"
    if ($LASTEXITCODE -ne 0) { Mal "No pude leer el ISO."; exit 1 }
    Bien "Recursos preparados desde $Iso"
}

# --- 4. Stockfish -------------------------------------------------------------
Titulo "Motor Stockfish"
New-Item -ItemType Directory -Force -Path "motor" | Out-Null
if (Test-Path "motor\stockfish.exe") {
    Bien "Ya estaba descargado (motor\stockfish.exe)"
} else {
    $url = $null
    try {
        $rel = Invoke-RestMethod "https://api.github.com/repos/official-stockfish/Stockfish/releases/latest" -Headers @{ "User-Agent" = "jaque" }
        $url = ($rel.assets | Where-Object { $_.name -like "stockfish-windows-x86-64-sse41-popcnt.zip" } | Select-Object -First 1).browser_download_url
        if (-not $url) { $url = ($rel.assets | Where-Object { $_.name -like "stockfish-windows-x86-64*.zip" } | Select-Object -First 1).browser_download_url }
    } catch {}
    if (-not $url) { $url = "https://github.com/official-stockfish/Stockfish/releases/download/sf_17.1/stockfish-windows-x86-64-sse41-popcnt.zip" }
    Write-Host "  Descargando $url"
    $zip = Join-Path $env:TEMP "stockfish-jaque.zip"
    $tmp = Join-Path $env:TEMP "stockfish-jaque"
    try {
        Invoke-WebRequest $url -OutFile $zip
        if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
        Expand-Archive $zip -DestinationPath $tmp
        $exe = Get-ChildItem $tmp -Recurse -Filter "stockfish*.exe" | Select-Object -First 1
        Copy-Item $exe.FullName "motor\stockfish.exe"
        $lic = Get-ChildItem $tmp -Recurse -Include "Copying.txt","COPYING*","LICENSE*" | Select-Object -First 1
        if ($lic) { Copy-Item $lic.FullName "motor\stockfish-licencia.txt" }
        Bien "Stockfish descargado"
    } catch {
        Mal "No pude descargar Stockfish."
        Write-Host "  Bajalo a mano de https://stockfishchess.org/download/ (Windows),"
        Write-Host "  copiá el .exe a la carpeta 'motor' con el nombre stockfish.exe y volvé a ejecutar."
        exit 1
    }
}

# --- 5. PyInstaller -------------------------------------------------------------
Titulo "Congelando Jaque (Python y bibliotecas adentro)"
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist")  { Remove-Item "dist" -Recurse -Force }
$excluir = @("tkinter","matplotlib","pycdlib","PySide6.QtWebEngineCore","PySide6.QtWebEngineWidgets",
             "PySide6.Qt3DCore","PySide6.QtCharts","PySide6.QtDataVisualization") | ForEach-Object { "--exclude-module=$_" }
$datos = @("--add-data", "jaque\datos;jaque\datos")
if (Test-Path "traducciones\es.json") { $datos += @("--add-data", "traducciones;traducciones") }
Copy-Item "$Aqui\lanzar.py" "lanzar.py" -Force
& $VPy -m PyInstaller --noconfirm --clean --log-level WARN --name jaque --onedir --windowed `
    --icon "$Aqui\jaque.ico" `
    @datos `
    --hidden-import jaque.ventanas --hidden-import jaque.preparar --hidden-import jaque.verificar `
    --hidden-import PySide6.QtMultimedia @excluir lanzar.py
if ($LASTEXITCODE -ne 0 -or -not (Test-Path "dist\jaque\jaque.exe")) { Mal "PyInstaller falló (ver mensajes arriba)."; exit 1 }
Bien "dist\jaque\jaque.exe"

# Prueba rápida del programa congelado (sin abrir ventanas)
Copy-Item -Recurse -Force "motor" "dist\jaque\motor"
Copy-Item -Recurse -Force "recursos" "dist\jaque\recursos"
$env:QT_QPA_PLATFORM = "offscreen"
& "dist\jaque\jaque.exe" --verificar --silencioso | Out-Null
Remove-Item Env:\QT_QPA_PLATFORM
$inf = Join-Path $env:LOCALAPPDATA "Jaque\verificacion.txt"
if (Test-Path $inf) { Get-Content $inf | ForEach-Object { Write-Host "  $_" } }

# --- 6. Instalador --------------------------------------------------------------
Titulo "Armando el instalador"
New-Item -ItemType Directory -Force -Path "salida" | Out-Null
& $Iscc "/DMiVersion=$Version" "/DRaiz=$Raiz" "/Qp" "$Aqui\jaque.iss"
if ($LASTEXITCODE -ne 0) { Mal "Inno Setup falló."; exit 1 }
$final = "salida\Jaque-$Version-instalador-windows.exe"
Bien $final
Write-Host ""
Write-Host "Listo. Ejecutá $final para instalar Jaque." -ForegroundColor Cyan
explorer.exe /select,"$Raiz\$final"
