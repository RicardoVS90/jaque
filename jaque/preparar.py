# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo Vera.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prepara el paquete de recursos de Jaque a partir del ISO o de la carpeta del juego.

Copia una sola vez los archivos de datos (tableros, piezas, sonidos, rivales,
lecciones y partidas) a ~/.local/share/jaque/recursos y genera de antemano las
piezas recortadas y los sonidos convertidos. Después Jaque arranca sin el ISO.

Uso:  python -m jaque.preparar /ruta/al/juego.iso   (o una carpeta)
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from .rutas import CACHE, DATOS, recursos as _recursos
DESTINO = _recursos()
MARCA = "JAQUE.RECURSOS"
# Solo datos: nada de ejecutables, DLL, ayuda ni la portada original.
EXTENSIONES = {"INI", "BMP", "WAV", "CMX", "TUT", "CML", "OBK"}
EXCLUIR = {"TITLEPIC.BMP"}


def preparar(origen, destino: Path = DESTINO, avisar=print) -> Path:
    from .assets import Recursos

    rec = Recursos(origen)
    tmp = destino.with_name(destino.name + ".nuevo")
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    n = 0
    for nombre in sorted(rec.src.listar()):
        ext = nombre.rsplit(".", 1)[-1]
        if ext in EXTENSIONES and nombre not in EXCLUIR:
            (tmp / nombre).write_bytes(rec.leer(nombre))
            n += 1
    (tmp / MARCA).write_text("Paquete de recursos de Jaque (uso personal).\n", encoding="utf-8")
    shutil.rmtree(destino, ignore_errors=True)
    tmp.rename(destino)
    avisar(f"   {n} archivos copiados a {destino}")

    generar_cache(destino, avisar)
    return destino


def generar_cache(destino: Path = DESTINO, avisar=print):
    """Recorta las piezas y convierte los sonidos de antemano (no necesita el ISO)."""
    from .assets import Recursos
    rec = Recursos(destino)
    juegos = rec.juegos_piezas()
    for i, (cod, nombre) in enumerate(juegos, 1):
        avisar(f"   Recortando piezas {i}/{len(juegos)}: {nombre}")
        rec.piezas(cod, CACHE)
    try:
        from .sonidos import convertir_todos
        convertir_todos(rec, CACHE / "sonidos")
        avisar("   Sonidos convertidos")
    except Exception as e:  # sin audio no es grave
        avisar(f"   (sonidos: {e})")


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print(__doc__)
        return 2
    try:
        if argv[0] == "--cache":
            generar_cache()
        else:
            preparar(argv[0])
    except Exception as e:
        print(f"No pude preparar los recursos: {e}")
        return 1
    print("Recursos listos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
