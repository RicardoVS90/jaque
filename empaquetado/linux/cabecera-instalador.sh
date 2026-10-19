#!/usr/bin/env bash
# ============================================================================
#  Instalador autosuficiente de Jaque @VERSION@
#
#  Trae TODO adentro: el programa con su propio Python y bibliotecas (Qt, numpy,
#  scipy, Pillow, python-chess), el motor Stockfish, gráficos, sonidos,
#  lecciones, partidas y traducciones. No usa internet, ni pip, ni el ISO.
#
#  Uso:  bash Jaque-@VERSION@-instalador.run              instalar / actualizar / reparar
#        bash Jaque-@VERSION@-instalador.run --verificar  solo revisar la instalación
#        bash Jaque-@VERSION@-instalador.run --desinstalar
#
#  Uso personal.
# ============================================================================
set -uo pipefail
trap 'echo "  ✘ Error en la línea $LINENO: $BASH_COMMAND" >&2' ERR
VERSION="@VERSION@"
DATOS="$HOME/.local/share/jaque"
PROG="$DATOS/programa"
c_ok=$'\e[32m'; c_mal=$'\e[31m'; c_tit=$'\e[1;33m'; c_0=$'\e[0m'
titulo() { echo; echo "${c_tit}== $* ==${c_0}"; }
bien()   { echo "  ${c_ok}✔${c_0} $*"; }
mal()    { echo "  ${c_mal}✘${c_0} $*"; }

desinstalar() {
  titulo "Desinstalando Jaque"
  rm -rf "$PROG" "$DATOS/recursos" "$DATOS/venv" "$HOME/.cache/jaque"
  rm -f "$HOME/.local/bin/jaque" "$HOME/.local/share/applications/jaque.desktop" \
        "$HOME/.local/share/icons/hicolor/256x256/apps/jaque.png" \
        "$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Escritorio")/jaque.desktop" \
        "$HOME/Escritorio/jaque.desktop" "$HOME/Desktop/jaque.desktop"
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
  bien "Listo. Tu configuración quedó en ~/.config/Jaque (borrala si querés)."
  exit 0
}

# Paquete de Debian que provee cada biblioteca del sistema que Qt necesita.
declare -A PAQUETE=(
  [libxcb-cursor.so.0]=libxcb-cursor0 [libxcb.so.1]=libxcb1 [libxcb-icccm.so.4]=libxcb-icccm4
  [libxcb-image.so.0]=libxcb-image0 [libxcb-keysyms.so.1]=libxcb-keysyms1
  [libxcb-render-util.so.0]=libxcb-render-util0 [libxcb-xkb.so.1]=libxcb-xkb1
  [libxkbcommon.so.0]=libxkbcommon0 [libxkbcommon-x11.so.0]=libxkbcommon-x11-0
  [libX11.so.6]=libx11-6 [libX11-xcb.so.1]=libx11-xcb1 [libXext.so.6]=libxext6
  [libXrender.so.1]=libxrender1 [libXi.so.6]=libxi6 [libXrandr.so.2]=libxrandr2
  [libXfixes.so.3]=libxfixes3 [libXcursor.so.1]=libxcursor1
  [libfontconfig.so.1]=libfontconfig1 [libfreetype.so.6]=libfreetype6
  [libharfbuzz.so.0]=libharfbuzz0b [libglib-2.0.so.0]=libglib2.0-0t64
  [libgobject-2.0.so.0]=libglib2.0-0t64 [libgio-2.0.so.0]=libglib2.0-0t64
  [libgthread-2.0.so.0]=libglib2.0-0t64 [libdbus-1.so.3]=libdbus-1-3
  [libEGL.so.1]=libegl1 [libGL.so.1]=libgl1 [libGLX.so.0]=libglx0 [libOpenGL.so.0]=libopengl0
  [libpulse.so.0]=libpulse0 [libasound.so.2]=libasound2t64 [libstdc++.so.6]=libstdc++6
  [libgcc_s.so.1]=libgcc-s1 [libz.so.1]=zlib1g [libexpat.so.1]=libexpat1
  [libwayland-client.so.0]=libwayland-client0 [libwayland-cursor.so.0]=libwayland-cursor0
  [libwayland-egl.so.1]=libwayland-egl1 [libpng16.so.16]=libpng16-16t64
  [libsystemd.so.0]=libsystemd0 [libgpg-error.so.0]=libgpg-error0 [libffi.so.8]=libffi8
  [libpcre2-8.so.0]=libpcre2-8-0 [libuuid.so.1]=libuuid1 [libdrm.so.2]=libdrm2
  [libsndfile.so.1]=libsndfile1 [libkrb5.so.3]=libkrb5-3 [libgssapi_krb5.so.2]=libgssapi-krb5-2
)

escanear() {
  # Revisa con ldd las bibliotecas principales del programa y del motor.
  local raiz="$1"; local -a archivos=()
  archivos+=("$raiz/jaque" "$raiz/motor/stockfish")
  while IFS= read -r f; do archivos+=("$f"); done < <(
    find "$raiz/_internal" -maxdepth 1 -name '*.so*' -type f
    find "$raiz/_internal/PySide6" -maxdepth 1 -name '*.so*' -type f
    find "$raiz/_internal/PySide6/Qt/lib" -name 'libQt6*.so*' -type f
    ls "$raiz"/_internal/PySide6/Qt/plugins/platforms/libq{xcb,wayland,offscreen}.so 2>/dev/null
    find "$raiz/_internal/PySide6/Qt/plugins/"{multimedia,imageformats,xcbglintegrations} -name '*.so' 2>/dev/null)
  local -A faltan=()
  for f in "${archivos[@]}"; do
    while read -r lib; do faltan[$lib]=1; done < <(LD_LIBRARY_PATH="$raiz/_internal" ldd "$f" 2>/dev/null | awk '/not found/ {print $1}')
  done
  printf '%s\n' "${!faltan[@]}"
}

verificar_sistema() {
  titulo "Revisando tu sistema"
  local arq; arq="$(uname -m)"
  if [ "$arq" != "x86_64" ]; then mal "Este instalador es para PC de 64 bits (x86_64); tu equipo es $arq."; exit 1; fi
  bien "Procesador de 64 bits (x86_64)"
  local glibc; glibc="$(getconf GNU_LIBC_VERSION 2>/dev/null | awk '{print $2}')"
  [ -n "$glibc" ] || glibc="$(ldd --version 2>/dev/null | awk 'NR==1 {print $NF}')"
  if [ "$(printf '%s\n2.39\n' "$glibc" | sort -V | head -1)" != "2.39" ]; then
    mal "Tu sistema tiene glibc $glibc; Jaque necesita 2.39 o más nueva (Debian 13 trae 2.41)."; exit 1
  fi
  bien "Biblioteca C del sistema (glibc $glibc)"
  if [ -n "${WAYLAND_DISPLAY:-}" ]; then bien "Escritorio: Wayland"; elif [ -n "${DISPLAY:-}" ]; then bien "Escritorio: X11"; fi
}

revisar_bibliotecas() {
  titulo "Escaneando las bibliotecas que necesita Jaque"
  local faltan; faltan="$(escanear "$PROG")"
  local total; total=$(find "$PROG/_internal" -name '*.so*' -type f | wc -l)
  bien "$total bibliotecas incluidas dentro de Jaque (Python, Qt, numpy, scipy, Pillow, sonido)"
  if [ -z "$faltan" ]; then
    bien "Todas las bibliotecas del sistema que usa Qt están presentes"
    return 0
  fi
  local -a pkgs=()
  for lib in $faltan; do
    mal "Falta en el sistema: $lib"
    [ -n "${PAQUETE[$lib]:-}" ] && pkgs+=("${PAQUETE[$lib]}")
  done
  if [ ${#pkgs[@]} -gt 0 ] && command -v apt-get >/dev/null; then
    local unicos; unicos="$(printf '%s\n' "${pkgs[@]}" | sort -u | tr '\n' ' ')"
    echo "  Se pueden instalar con:  sudo apt install $unicos"
    if [ -t 0 ]; then
      read -r -p "  ¿Instalarlas ahora? (necesita internet) [S/n] " r
      if [[ ! "$r" =~ ^[nN] ]]; then sudo apt-get install -y $unicos && return 0; fi
    fi
  fi
  return 1
}

crear_accesos() {
  titulo "Creando los accesos directos"
  mkdir -p "$HOME/.local/bin" "$HOME/.local/share/applications" "$HOME/.local/share/icons/hicolor/256x256/apps"
  cp "$PROG/_internal/jaque/datos/jaque.png" "$HOME/.local/share/icons/hicolor/256x256/apps/jaque.png"
  cp "$PROG/_internal/jaque/datos/jaque.png" "$DATOS/jaque.png"
  cat > "$HOME/.local/bin/jaque" <<LANZ
#!/usr/bin/env bash
# Lanzador de Jaque. Si el programa se cierra de golpe al arrancar (por ejemplo,
# por un problema de audio), lo vuelve a abrir sin sonido.
export LANG="\${LANG:-C.UTF-8}"
inicio=\$(date +%s)
"$PROG/jaque" "\$@"; codigo=\$?
if [ \$codigo -ge 128 ] && [ \$((\$(date +%s) - inicio)) -lt 15 ] && [ -z "\${JAQUE_SIN_SONIDO:-}" ]; then
  command -v notify-send >/dev/null && notify-send "Jaque" "Se cerró al iniciar el sonido; lo abro sin sonido."
  JAQUE_SIN_SONIDO=1 exec "$PROG/jaque" "\$@"
fi
exit \$codigo
LANZ
  chmod +x "$HOME/.local/bin/jaque"
  local entrada
  entrada="[Desktop Entry]
Type=Application
Version=1.0
Name=Jaque
GenericName=Ajedrez
Comment=Ajedrez en español
Exec=$HOME/.local/bin/jaque
Icon=$DATOS/jaque.png
Terminal=false
StartupNotify=true
StartupWMClass=jaque
Categories=Game;BoardGame;
Keywords=ajedrez;chess;"
  printf '%s\n' "$entrada" > "$HOME/.local/share/applications/jaque.desktop"
  chmod +x "$HOME/.local/share/applications/jaque.desktop"
  bien "Menú de aplicaciones → Juegos → Jaque"
  # Ícono en el escritorio
  local escritorio
  escritorio="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
  [ -z "$escritorio" ] || [ "$escritorio" = "$HOME" ] && escritorio="$HOME/Escritorio"
  [ -d "$escritorio" ] || escritorio="$HOME/Desktop"
  if [ -d "$escritorio" ]; then
    printf '%s\n' "$entrada" > "$escritorio/jaque.desktop"
    chmod +x "$escritorio/jaque.desktop"
    command -v gio >/dev/null && gio set "$escritorio/jaque.desktop" metadata::trusted true 2>/dev/null || true
    bien "Ícono en el escritorio ($escritorio)"
  fi
  # Si alguna vez se borró Jaque con el Editor de menús de KDE, KDE lo sigue ocultando
  # (lo anota en ~/.config/menus/*.menu). Se quita esa marca para que vuelva a aparecer.
  local m
  for m in "$HOME"/.config/menus/*.menu; do
    [ -f "$m" ] || continue
    if grep -q 'jaque\.desktop' "$m"; then
      cp "$m" "$m.antes-de-jaque" && sed -i '/jaque\.desktop/d' "$m" && bien "Quitada la marca de «oculto» que KDE tenía para Jaque"
    fi
  done
  # Que KDE (y otros escritorios) relean el menú ahora mismo
  update-desktop-database "$HOME/.local/share/applications" 2>/dev/null || true
  gtk-update-icon-cache -q "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
  for k in kbuildsycoca6 kbuildsycoca5; do
    if command -v "$k" >/dev/null; then "$k" >/dev/null 2>&1 && bien "Menú de KDE actualizado"; break; fi
  done
  bien "Comando en la terminal: jaque"
}

[ "${1:-}" = "--desinstalar" ] && desinstalar
if [ "${1:-}" = "--verificar" ]; then
  verificar_sistema
  [ -x "$PROG/jaque" ] || { mal "Jaque no está instalado."; exit 1; }
  revisar_bibliotecas || true
  titulo "Probando el programa"
  QT_QPA_PLATFORM=offscreen JAQUE_SIN_SONIDO=1 "$PROG/jaque" --verificar 2>/dev/null | sed 's/^/ /'
  exit 0
fi

mkdir -p "$DATOS"
REGISTRO="$DATOS/instalacion.log"
exec > >(tee "$REGISTRO") 2>&1
echo "${c_tit}Jaque $VERSION — instalador autosuficiente${c_0}  ($(date '+%F %T'))"
verificar_sistema

titulo "Copiando el programa"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
LINEA=$(awk '/^__CONTENIDO__$/ {print NR + 1; exit 0}' "$0")
tail -n +"$LINEA" "$0" | tar -xz -C "$TMP" 2>/dev/null
if [ ! -x "$TMP/programa/jaque" ] || [ ! -f "$TMP/recursos/JAQUE.RECURSOS" ]; then
  mal "El instalador está incompleto o dañado (¿se cortó la descarga?). Volvé a descargarlo."
  exit 1
fi
mkdir -p "$DATOS"
rm -rf "$PROG" "$DATOS/recursos" "$DATOS/venv"     # venv: de versiones anteriores, ya no se usa
mv "$TMP/programa" "$PROG"
mv "$TMP/recursos" "$DATOS/recursos"
bien "Programa en $PROG"
bien "Gráficos, sonidos, lecciones y partidas en $DATOS/recursos"
crear_accesos

PROBLEMAS=0
revisar_bibliotecas || PROBLEMAS=1

titulo "Preparando piezas y sonidos"
rm -rf "$HOME/.cache/jaque/piezas"
if QT_QPA_PLATFORM=offscreen JAQUE_SIN_SONIDO=1 "$PROG/jaque" --preparar-cache >/dev/null 2>&1; then
  bien "17 juegos de piezas recortados y sonidos convertidos"
else
  mal "No pude preparar las piezas ahora; Jaque lo hará al abrirse."
fi

titulo "Prueba final"
if QT_QPA_PLATFORM=offscreen JAQUE_SIN_SONIDO=1 "$PROG/jaque" --verificar 2>/dev/null | sed 's/^/ /'; then :; else PROBLEMAS=1; fi

echo
if [ $PROBLEMAS -eq 0 ]; then
  echo "${c_ok}Listo: Jaque $VERSION instalado y funcionando.${c_0}"
else
  echo "${c_mal}Jaque quedó instalado, pero hay algo para revisar (ver arriba).${c_0}"
fi
echo "Registro de la instalación: $REGISTRO"
echo "Si no ves Jaque en el menú, cerrá sesión y volvé a entrar."
echo "Guardá este archivo como respaldo: con él reinstalás Jaque sin nada más."
exit 0
__CONTENIDO__
