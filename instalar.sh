#!/usr/bin/env bash
# Instala Jaque para el usuario actual (sin sudo, salvo para Stockfish).
# Uso:  ./instalar.sh                 (busca el ISO solo)
#       ./instalar.sh /ruta/al/cd.iso (o la carpeta del juego)
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DATOS="$HOME/.local/share/jaque"
VENV="$DATOS/venv"

if ! command -v stockfish >/dev/null && [ ! -x /usr/games/stockfish ]; then
  echo ">> Falta Stockfish. Instalándolo (pide tu contraseña)…"
  sudo apt install -y stockfish
fi
if ! python3 -c "import ensurepip" 2>/dev/null; then
  echo ">> Falta python3-venv. Instalándolo…"
  sudo apt install -y python3-venv
fi

if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import PySide6, chess, pycdlib, numpy, scipy, PIL" 2>/dev/null; then
  echo ">> El entorno de Python ya existe, lo reutilizo."
else
  echo ">> Creando entorno de Python en $VENV"
  rm -rf "$VENV"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip >/dev/null
  "$VENV/bin/pip" install -r "$DIR/requirements.txt"
fi

# --- gráficos y sonidos: se preparan una sola vez a partir de tu ISO ---------
ORIGEN="${1:-}"
if [ -z "$ORIGEN" ]; then
  for f in "$DIR"/*.iso "$DIR"/*.ISO "$HOME"/Descargas/*.iso "$HOME"/Descargas/*.ISO \
           "$HOME"/Downloads/*.iso "$HOME"/Downloads/*.ISO; do
    [ -f "$f" ] || continue
    case "$(basename "$f" | tr '[:lower:]' '[:upper:]')" in
      CM4000*|*CHESS*) ORIGEN="$f"; break ;;
    esac
  done
fi
if [ -n "$ORIGEN" ]; then
  echo ">> Preparando gráficos y sonidos desde: $ORIGEN"
  (cd "$DIR" && "$VENV/bin/python" -m jaque.preparar "$ORIGEN")
elif [ -f "$DATOS/recursos/JAQUE.RECURSOS" ]; then
  echo ">> Los gráficos y sonidos ya estaban preparados."
else
  echo ">> No encontré el ISO. Jaque te lo va a pedir una sola vez al abrirlo."
fi

mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" \
         "$HOME/.local/share/icons/hicolor/256x256/apps"
cp "$DIR/jaque/datos/jaque.png" "$HOME/.local/share/icons/hicolor/256x256/apps/jaque.png"
cat > "$HOME/.local/bin/jaque" <<LANZ
#!/usr/bin/env bash
cd "$DIR" && exec "$VENV/bin/python" -m jaque "\$@"
LANZ
chmod +x "$HOME/.local/bin/jaque"

cat > "$HOME/.local/share/applications/jaque.desktop" <<DESK
[Desktop Entry]
Type=Application
Name=Jaque
GenericName=Ajedrez
Comment=Ajedrez en español
Exec=$HOME/.local/bin/jaque
Icon=jaque
Terminal=false
Categories=Game;BoardGame;
Keywords=ajedrez;chess;
DESK
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo
echo "Listo. Abrí 'Jaque' desde el menú de KDE o ejecutá:  jaque"
echo "Ya podés borrar el ISO si querés: Jaque usa su propia copia en $DATOS/recursos"
