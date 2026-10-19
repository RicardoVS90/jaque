#!/usr/bin/env bash
# Quita del paquete congelado las bibliotecas base que deben venir del sistema.
set -euo pipefail
I="$1/_internal"
cd "$I"
for pat in 'libstdc++.so.*' 'libgcc_s.so.*' 'libX11.so.*' 'libX11-xcb.so.*' 'libXau.so.*' 'libXdmcp.so.*' \
  'libXext.so.*' 'libXrender.so.*' 'libXfixes.so.*' 'libXi.so.*' 'libXrandr.so.*' 'libXcursor.so.*' \
  'libXinerama.so.*' 'libXcomposite.so.*' 'libXdamage.so.*' \
  'libfontconfig.so.*' 'libfreetype.so.*' 'libharfbuzz.so.*' 'libexpat.so.*' 'libz.so.*' 'libuuid.so.*' \
  'libcom_err.so.*' 'libgpg-error.so.*' 'libgcrypt.so.*' 'libthai.so.*' 'libdatrie.so.*' 'libgtk-3.so.*' 'libgdk-3.so.*' \
  'libatk-1.0.so.*' 'libatk-bridge-2.0.so.*' 'libatspi.so.*' 'libcairo.so.*' 'libcairo-gobject.so.*' \
  'libpango-1.0.so.*' 'libpangocairo-1.0.so.*' 'libpangoft2-1.0.so.*' 'libgdk_pixbuf-2.0.so.*' 'libepoxy.so.*' \
  'libsystemd.so.*' 'libselinux.so.*' 'libmount.so.*' 'libblkid.so.*' 'libdbus-1.so.*' 'libapparmor.so.*' \
  'libglib-2.0.so.*' 'libgio-2.0.so.*' 'libgobject-2.0.so.*' 'libgmodule-2.0.so.*' 'libgthread-2.0.so.*' \
  'libpcre2-8.so.*' 'libffi.so.*' 'libpixman-1.so.*' 'libpng16.so.*' 'libgraphite2.so.*' 'libfribidi.so.*' \
  'libbrotlicommon.so.*' 'libbrotlidec.so.*' 'libbsd.so.*' 'libmd.so.*' 'libcap.so.*' 'liblz4.so.*' \
  'libpulse.so.*' 'libpulsecommon-*.so' 'libasyncns.so.*' 'libsndfile.so.*' 'libFLAC.so.*' 'libogg.so.*' \
  'libvorbis.so.*' 'libvorbisenc.so.*' 'libopus.so.*' 'libmpg123.so.*' 'libmp3lame.so.*' \
  'libkrb5.so.*' 'libkrb5support.so.*' 'libk5crypto.so.*' 'libgssapi_krb5.so.*' 'libkeyutils.so.*' \
  'libxkbcommon.so.*' 'libtinfo.so.*' 'libncursesw.so.*' 'libreadline.so.*'; do
  rm -f $pat
done
rm -f PySide6/Qt/plugins/platformthemes/libqgtk3.so
rm -rf yaml
