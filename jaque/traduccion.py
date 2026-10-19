# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Traducciones locales de los textos del juego original.

Las traducciones viven en un archivo JSON {texto original normalizado: traducción}
que se guarda solo en la máquina del usuario (no forma parte del código).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_TABLA = None
_LETRAS = str.maketrans({"K": "R", "Q": "D", "R": "T", "B": "A", "N": "C"})
_SAN = re.compile(r"(?<![A-Za-z])([KQRBN])([a-h]?[1-8]?x?[a-h][1-8](?:=[QRBN])?[+#]*)"
                  r"|(?<==)([QRBN])\b")
_CORONA = re.compile(r"(?<=[1-8])\(([QRBN])\)")


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def rutas_posibles():
    base = Path(__file__).resolve().parent.parent
    from .rutas import DATOS
    return [DATOS / "traducciones" / "es.json",
            base / "traducciones" / "es.json"]


def cargar():
    global _TABLA
    _TABLA = {}
    for r in reversed(rutas_posibles()):
        if r.exists():
            try:
                _TABLA.update(json.loads(r.read_text(encoding="utf-8")))
            except Exception:
                pass
    return len(_TABLA)


def notacion_es(texto: str) -> str:
    """Cambia las letras de pieza en la notación incrustada: Nf3 -> Cf3, Qxd8+ -> Dxd8+."""
    def rep(m):
        if m.group(1):
            return m.group(1).translate(_LETRAS) + m.group(2).translate(_LETRAS)
        return m.group(3).translate(_LETRAS)
    texto = _SAN.sub(rep, texto)
    # Coronación entre paréntesis: f8(Q) -> f8(D)
    return _CORONA.sub(lambda m: "(" + m.group(1).translate(_LETRAS) + ")", texto)


def t(texto: str) -> str:
    """Traduce un texto del juego; si no hay traducción, lo devuelve tal cual."""
    if _TABLA is None:
        cargar()
    n = norm(texto)
    es = _TABLA.get(n)
    if es is None:
        return n
    return notacion_es(es)


def hay_traducciones() -> bool:
    if _TABLA is None:
        cargar()
    return bool(_TABLA)
