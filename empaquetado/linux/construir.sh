#!/usr/bin/env bash
# ============================================================================
#  Arma el instalador autosuficiente de Jaque para Linux (x86_64):
#      empaquetado/linux/construir.sh /ruta/a/tu/cd.iso
#
#  Requisitos en la máquina que construye:
#    - Python 3 con:  pip install -r requirements.txt pyinstaller
#    - Stockfish instalado (o la variable STOCKFISH=/ruta/al/ejecutable)
#  Resultado: build/Jaque-<versión>-instalador.run  (uso personal: lleva los
#  gráficos y sonidos de TU copia del juego; no lo publiques).
# ============================================================================
set -euo pipefail
ISO="${1:?Uso: $0 /ruta/a/tu/cd.iso}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AQUI="$REPO/empaquetado/linux"
B="$REPO/build"
PY="${PYTHON:-python3}"
SF="${STOCKFISH:-$(command -v stockfish || echo /usr/games/stockfish)}"
[ -x "$SF" ] || { echo "No encuentro Stockfish (instalalo o usá STOCKFISH=/ruta)."; exit 1; }
VER=$("$PY" -c "import sys; sys.path.insert(0,'$REPO'); import jaque; print(jaque.__version__)")

echo ">> Congelando Jaque $VER con PyInstaller"
rm -rf "$B/pyi" "$B/payload"; mkdir -p "$B/pyi" "$B/payload"
cd "$B/pyi"
cp -r "$REPO/jaque" "$AQUI/lanzar.py" .
datos=(--add-data "jaque/datos:jaque/datos")
if [ -f "$REPO/traducciones/es.json" ]; then cp -r "$REPO/traducciones" .; datos+=(--add-data "traducciones:traducciones"); fi
find . -name __pycache__ -prune -exec rm -rf {} +
"$PY" -m PyInstaller --noconfirm --clean --log-level ERROR --name jaque --onedir --windowed "${datos[@]}" \
  --hidden-import jaque.ventanas --hidden-import jaque.preparar --hidden-import jaque.verificar \
  --hidden-import PySide6.QtMultimedia \
  --exclude-module tkinter --exclude-module matplotlib --exclude-module pycdlib \
  --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets \
  --exclude-module PySide6.Qt3DCore --exclude-module PySide6.QtCharts --exclude-module PySide6.QtDataVisualization \
  lanzar.py
"$AQUI/podar.sh" "$B/pyi/dist/jaque"

echo ">> Agregando Stockfish"
mkdir -p dist/jaque/motor
cp "$SF" dist/jaque/motor/stockfish
mv dist/jaque "$B/payload/programa"

echo ">> Preparando gráficos y sonidos desde $ISO"
(cd "$REPO" && JAQUE_SIN_SONIDO=1 "$PY" -c "
from pathlib import Path; from jaque.preparar import preparar
preparar(r'''$ISO''', Path(r'''$B/payload/recursos'''), avisar=lambda t: None)")

echo ">> Empaquetando"
OUT="$B/Jaque-$VER-instalador.run"
sed "s/@VERSION@/$VER/g" "$AQUI/cabecera-instalador.sh" > "$OUT"
tar -czf - -C "$B/payload" programa recursos >> "$OUT"
chmod +x "$OUT"
du -sh "$OUT"
