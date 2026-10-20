#!/usr/bin/env bash
# ============================================================================
#  Arma el instalador autosuficiente de Jaque para Linux (x86_64).
#
#  Uso:
#      empaquetado/linux/construir.sh                  usa la carpeta recursos/ del repositorio
#      empaquetado/linux/construir.sh /ruta/cd.iso     prepara los recursos desde el ISO
#      empaquetado/linux/construir.sh /ruta/carpeta    desde la carpeta del juego instalado
#                                                      o desde un paquete de recursos ya preparado
#
#  Requisitos en la máquina que construye:
#    - Python 3 con:  pip install -r requirements.txt pyinstaller
#    - Stockfish instalado (o la variable STOCKFISH=/ruta/al/ejecutable)
#  Resultado: build/Jaque-<versión>-instalador.run  (uso personal: lleva los
#  gráficos y sonidos de TU copia del juego; no lo publiques).
# ============================================================================
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
AQUI="$REPO/empaquetado/linux"
B="$REPO/build"
PY="${PYTHON:-python3}"
MARCA="JAQUE.RECURSOS"

# --- ¿De dónde salen los gráficos, sonidos, rivales, lecciones y partidas? ---
ORIGEN="${1:-}"
if [ -z "$ORIGEN" ]; then
  if [ -f "$REPO/recursos/$MARCA" ]; then
    ORIGEN="$REPO/recursos"
  else
    echo "No hay una carpeta recursos/ preparada en el repositorio."
    echo "Uso: $0 [/ruta/a/tu/cd.iso | /ruta/a/la/carpeta/del/juego]"
    exit 1
  fi
fi
[ -e "$ORIGEN" ] || { echo "No existe: $ORIGEN"; exit 1; }
ORIGEN="$(cd "$(dirname "$ORIGEN")" && pwd)/$(basename "$ORIGEN")"
if [ -d "$ORIGEN" ] && [ -f "$ORIGEN/$MARCA" ]; then MODO="preparado"; else MODO="juego"; fi

SF="${STOCKFISH:-$(command -v stockfish || echo /usr/games/stockfish)}"
[ -x "$SF" ] || { echo "No encuentro Stockfish (instalalo con: sudo apt install stockfish, o usá STOCKFISH=/ruta)."; exit 1; }
"$PY" -c "import PyInstaller" 2>/dev/null || { echo "Falta PyInstaller: pip install pyinstaller"; exit 1; }
VER=$("$PY" -c "import sys; sys.path.insert(0,'$REPO'); import jaque; print(jaque.__version__)")

echo ">> Jaque $VER — recursos: $ORIGEN ($MODO)"
echo ">> Congelando el programa con PyInstaller"
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

echo ">> Agregando Stockfish y licencias"
mkdir -p dist/jaque/motor dist/jaque/licencias
cp "$SF" dist/jaque/motor/stockfish
cp "$REPO/LICENSE" dist/jaque/licencias/jaque-GPL-3.0.txt 2>/dev/null || true
for f in /usr/share/doc/stockfish/copyright; do [ -f "$f" ] && cp "$f" dist/jaque/licencias/stockfish-copyright.txt; done
if [ -f "$REPO/jaque/datos/aperturas.json" ]; then
  printf "Base de aperturas ECO: paquete chess-openings 0.1.1, de Guido Flohr.\nLicencia WTFPL, versión 2.\nTraducción de los nombres al español: Jaque.\n" \
    > dist/jaque/licencias/aperturas-chess-openings.txt
fi
"$PY" - <<'PY' || true
import importlib.metadata as m, pathlib
d = pathlib.Path("dist/jaque/licencias")
for p in ("PySide6", "shiboken6", "numpy", "scipy", "pillow", "chess"):
    try:
        dist = m.distribution(p)
        lic = [f for f in (dist.files or []) if any(k in f.name.upper() for k in ("LICENSE", "COPYING"))]
        txt = "\n\n".join(f.read_text() for f in lic[:3] if f.locate().exists()) or (dist.metadata.get("License") or "")
        (d / f"{p}.txt").write_text(f"{p} {dist.version}\n\n{txt}")
    except Exception as e:
        print("   (licencia de", p, "no encontrada:", e, ")")
PY
mv dist/jaque "$B/payload/programa"

if [ "$MODO" = "preparado" ]; then
  echo ">> Copiando los recursos ya preparados"
  cp -r "$ORIGEN" "$B/payload/recursos"
else
  echo ">> Preparando gráficos y sonidos desde $ORIGEN"
  (cd "$REPO" && JAQUE_SIN_SONIDO=1 "$PY" -c "
from pathlib import Path; from jaque.preparar import preparar
preparar(r'''$ORIGEN''', Path(r'''$B/payload/recursos'''), avisar=lambda t: None)")
fi
[ -f "$B/payload/recursos/$MARCA" ] || { echo "Los recursos no quedaron bien preparados."; exit 1; }

echo ">> Empaquetando"
OUT="$B/Jaque-$VER-instalador.run"
sed "s/@VERSION@/$VER/g" "$AQUI/cabecera-instalador.sh" > "$OUT"
tar -czf - -C "$B/payload" programa recursos >> "$OUT"
chmod +x "$OUT"
du -sh "$OUT"
echo "Listo: $OUT"
