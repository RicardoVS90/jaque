# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Carpetas de Jaque según el sistema operativo.

Linux:   ~/.local/share/jaque  (datos)   y  ~/.cache/jaque  (caché)
Windows: %LOCALAPPDATA%\\Jaque  (datos)   y  %LOCALAPPDATA%\\Jaque\\cache
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

WINDOWS = sys.platform.startswith("win")

if WINDOWS:
    _base = Path(os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local"))
    DATOS = _base / "Jaque"
    CACHE = DATOS / "cache"
else:
    DATOS = Path.home() / ".local" / "share" / "jaque"
    CACHE = Path.home() / ".cache" / "jaque"


def carpeta_programa() -> Path:
    """Carpeta donde está instalado el programa (junto al ejecutable si está congelado)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def recursos() -> Path:
    """Paquete de gráficos y sonidos: junto al programa (instalador) o en DATOS."""
    junto = carpeta_programa() / "recursos"
    if (junto / "JAQUE.RECURSOS").exists():
        return junto
    return DATOS / "recursos"
