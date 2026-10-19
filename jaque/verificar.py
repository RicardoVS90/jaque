# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Chequeo completo de la instalación: jaque --verificar"""
from __future__ import annotations

import os
import subprocess
import sys


def verificar() -> int:
    ok = True
    informe = []

    def linea(bien, texto):
        nonlocal ok
        ok &= bool(bien)
        informe.append(f"[{'OK' if bien else 'FALTA'}] {texto}")
        print(f"  {informe[-1]}")

    print("Verificando Jaque…")
    try:
        from PySide6 import QtCore, QtGui, QtWidgets  # noqa: F401
        linea(True, f"Qt {QtCore.qVersion()} (interfaz)")
    except Exception as e:
        linea(False, f"Qt: {e}")
        return 1
    try:
        from PySide6 import QtMultimedia  # noqa: F401
        linea(True, "Qt Multimedia (sonido)")
    except Exception as e:
        linea(False, f"Qt Multimedia: {e}")
    for mod in ("numpy", "PIL", "chess", "scipy"):
        try:
            __import__(mod)
            linea(True, f"biblioteca {mod}")
        except Exception as e:
            linea(False, f"biblioteca {mod}: {e}")

    if sys.stdout is not None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["jaque"])  # noqa: F841

    from .preparar import DESTINO
    try:
        from .assets import Recursos
        rec = Recursos(DESTINO)
        linea(len(rec.juegos_piezas()) >= 17, f"{len(rec.juegos_piezas())} juegos de piezas")
        linea(len(rec.tableros_2d()) + len(rec.tableros_3d()) >= 11,
              f"{len(rec.tableros_2d())} tableros 2D y {len(rec.tableros_3d())} 3D")
        linea(len(rec.rivales()) >= 40, f"{len(rec.rivales())} rivales")
        cls = [f"CLASSIC{i}.CML" for i in range(1, 10) if rec.existe(f"CLASSIC{i}.CML")]
        linea(len(cls) == 9, f"{len(cls)} colecciones de partidas clásicas")
        tuts = [t for t in ("RULES.TUT", "TUTORIAL.TUT", "ICE.TUT") if rec.existe(t)]
        linea(len(tuts) == 3, f"{len(tuts)} tutoriales")
    except Exception as e:
        linea(False, f"gráficos y sonidos: {e}")

    from . import traduccion
    n = traduccion.cargar()
    if n:
        linea(True, f"{n} textos traducidos")
    else:
        informe.append("[--] Sin traducciones: el tutor y las partidas se muestran en inglés")
        print(f"  {informe[-1]}")

    from .motor import buscar_stockfish
    sf = buscar_stockfish()
    if sf:
        try:
            extra = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform.startswith("win") else {}
            r = subprocess.run([sf], input="uci\nquit\n", capture_output=True, text=True, timeout=20, **extra)
            nombre = next((l[8:] for l in r.stdout.splitlines() if l.startswith("id name ")), "")
            linea("uciok" in r.stdout, f"motor: {nombre or sf}")
        except Exception as e:
            linea(False, f"motor Stockfish: {e}")
    else:
        linea(False, "motor Stockfish")

    print("Todo en orden." if ok else "Hay problemas (ver arriba).")
    informe.append("Todo en orden." if ok else "Hay problemas.")
    try:
        from .rutas import DATOS
        DATOS.mkdir(parents=True, exist_ok=True)
        (DATOS / "verificacion.txt").write_text("\n".join(informe) + "\n", encoding="utf-8")
    except Exception:
        pass
    if sys.stdout is None and "--silencioso" not in sys.argv:   # Windows sin consola
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.information(None, "Jaque: verificación", "\n".join(informe))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(verificar())
