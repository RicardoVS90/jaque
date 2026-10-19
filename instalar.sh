#!/usr/bin/env bash
# Instala Jaque para el usuario actual (sin sudo, salvo para Stockfish).
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV="$HOME/.local/share/jaque/venv"

if ! command -v stockfish >/dev/null && [ ! -x /usr/games/stockfish ]; then
  echo ">> Falta Stockfish. Instalándolo (pide tu contraseña)…"
  sudo apt install -y stockfish
fi
if ! python3 -c "import ensurepip" 2>/dev/null; then
  echo ">> Falta python3-venv. Instalándolo…"
  sudo apt install -y python3-venv
fi

echo ">> Creando entorno de Python en $VENV"
rm -rf "$VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install --upgrade pip >/dev/null
"$VENV/bin/pip" install -r "$DIR/requirements.txt"

mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications"
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
Comment=Ajedrez con los recursos de tu Chessmaster 4000
Exec=$HOME/.local/bin/jaque
Icon=applications-games
Terminal=false
Categories=Game;BoardGame;
Keywords=ajedrez;chess;chessmaster;
DESK
update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true

echo
echo "Listo. Abrí 'Jaque' desde el menú de KDE o ejecutá:  jaque"
echo "La primera vez te va a pedir el ISO o la carpeta de Chessmaster 4000."
