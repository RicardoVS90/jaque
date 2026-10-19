# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Stockfish en un hilo aparte, con la personalidad del rival aplicada encima."""
from __future__ import annotations

import random
import shutil
import sys

import chess
import chess.engine
from PySide6.QtCore import QObject, QThread, Signal, Slot

from .rivales import Rival, config_motor, elegir_jugada


def _stockfish_incluido():
    """Stockfish que viene dentro del instalador (carpeta motor/ junto al programa)."""
    import sys
    from pathlib import Path
    from .rutas import DATOS, WINDOWS
    bases = [Path(sys.executable).resolve().parent,
             Path(__file__).resolve().parent.parent,
             DATOS / "programa"]
    nombre = "stockfish.exe" if WINDOWS else "stockfish"
    for b in bases:
        p = b / "motor" / nombre
        if p.is_file():
            return str(p)
    return None


def buscar_stockfish(preferida: str | None = None) -> str | None:
    for c in (preferida, "stockfish", "/usr/games/stockfish", "/usr/bin/stockfish"):
        if c and shutil.which(c):
            return shutil.which(c)
    return _stockfish_incluido()


class _Trabajador(QObject):
    jugada = Signal(int, str, object)       # id, uci, info (dict)
    sugerencia = Signal(int, object)         # id, dict
    error = Signal(str)

    def __init__(self, ruta):
        super().__init__()
        self.ruta = ruta
        self.eng = None

    def _motor(self):
        if self.eng is None:
            extra = {}
            if sys.platform.startswith("win"):
                import subprocess
                extra["creationflags"] = subprocess.CREATE_NO_WINDOW   # sin ventana negra
            self.eng = chess.engine.SimpleEngine.popen_uci(self.ruta, **extra)
            try:
                self.eng.configure({"Threads": 2, "Hash": 64})
            except Exception:
                pass
        return self.eng

    @Slot(int, str, object, float)
    def pensar(self, pid, fen, rival: Rival, tiempo_max):
        try:
            board = chess.Board(fen)
            cfg = config_motor(rival)
            eng = self._motor()
            eng.configure({"Skill Level": cfg["skill"]})
            t = min(cfg["tiempo"], tiempo_max) if tiempo_max > 0 else cfg["tiempo"]
            infos = eng.analyse(board, chess.engine.Limit(time=max(0.05, t)),
                                multipv=cfg["multipv"])
            cand = []
            for inf in infos:
                if "pv" not in inf or not inf["pv"]:
                    continue
                cp = inf["score"].pov(board.turn).score(mate_score=100000)
                cand.append((inf["pv"][0], cp))
            # variedad en la apertura para los rivales fuertes
            if board.ply() < 10 and rival.libro and cand:
                tope = cand[0][1]
                cerca = [c for c in cand if c[1] >= tope - 25]
                random.shuffle(cerca)
                cand = cerca + [c for c in cand if c not in cerca]
            mv = elegir_jugada(rival, board, cand)
            if mv is None:
                mv = next(iter(board.legal_moves))
            info0 = infos[0] if infos else {}
            self.jugada.emit(pid, mv.uci(), {"score": info0.get("score"),
                                              "pv": info0.get("pv", []),
                                              "depth": info0.get("depth")})
        except Exception as e:  # pragma: no cover
            self.error.emit(f"Error del motor: {e}")

    @Slot(int, str, float)
    def analizar(self, pid, fen, tiempo):
        try:
            board = chess.Board(fen)
            eng = self._motor()
            eng.configure({"Skill Level": 20})
            inf = eng.analyse(board, chess.engine.Limit(time=tiempo))
            self.sugerencia.emit(pid, {"score": inf.get("score"), "pv": inf.get("pv", []),
                                       "depth": inf.get("depth")})
        except Exception as e:  # pragma: no cover
            self.error.emit(f"Error del motor: {e}")

    @Slot()
    def cerrar(self):
        if self.eng:
            try:
                self.eng.quit()
            except Exception:
                pass
            self.eng = None


class Motor(QObject):
    """Fachada usada por la ventana. Cada pedido lleva un id para descartar respuestas viejas."""
    jugada = Signal(str, object)
    sugerencia = Signal(object)
    error = Signal(str)
    _pedir_jugada = Signal(int, str, object, float)
    _pedir_analisis = Signal(int, str, float)
    _cerrar = Signal()

    def __init__(self, ruta: str):
        super().__init__()
        self._id = 0
        self.hilo = QThread()
        self.t = _Trabajador(ruta)
        self.t.moveToThread(self.hilo)
        self._pedir_jugada.connect(self.t.pensar)
        self._pedir_analisis.connect(self.t.analizar)
        self._cerrar.connect(self.t.cerrar)
        self.t.jugada.connect(self._on_jugada)
        self.t.sugerencia.connect(self._on_sug)
        self.t.error.connect(self.error)
        self.hilo.start()

    def cancelar(self):
        self._id += 1

    def pedir_jugada(self, board: chess.Board, rival: Rival, tiempo_max: float = 0):
        self._id += 1
        self._pedir_jugada.emit(self._id, board.fen(), rival, float(tiempo_max))

    def pedir_sugerencia(self, board: chess.Board, tiempo: float = 1.5):
        self._id += 1
        self._pedir_analisis.emit(self._id, board.fen(), float(tiempo))

    def _on_jugada(self, pid, uci, info):
        if pid == self._id:
            self.jugada.emit(uci, info)

    def _on_sug(self, pid, info):
        if pid == self._id:
            self.sugerencia.emit(info)

    def apagar(self):
        self._id += 1
        self.hilo.quit()
        self.hilo.wait(5000)
        self.t.cerrar()  # el hilo ya terminó: seguro llamarlo desde aquí
