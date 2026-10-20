# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo Vera.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Rivales: lectura de los .CMX originales y su traduccion a un estilo de juego.

Formato CMX (144 bytes), deducido comparando los 40 archivos:
  0..32   nombre (ASCII, terminado en 0 y relleno con espacios)
  33..35  firma 1A 04 81
  36..    enteros de 16 bits con signo:
    [0] usa libro de aperturas      [1] piensa en el tiempo del rival
    [2] ataque(-100) .. defensa(+100)
    [3] fuerza 0..100               [4] aleatoriedad 0..100
    [5] busqueda selectiva          [6] profundidad/modo
    [7] desprecio por las tablas (9999 nunca acepta, -9999 las busca)
    [8] juego posicional (+) / material (-)
    [9..13] centro, movilidad, seguridad del rey, estructura, peones pasados
    [14..23] valor de D, T, A, C, P (propias / rivales, en decenas de centipeon)
"""
from __future__ import annotations

import random
import struct
from dataclasses import dataclass, field

import chess

NOMBRES_ES = {
    "Brute Force": "Fuerza bruta",
    "Chessmaster": "El Maestro",
    "Defender": "Defensor",
    "Difficult": "Difícil",
    "Drawmaster": "Maestro de tablas",
    "Easy": "Fácil",
    "Expert": "Experto",
    "Kamikaze": "Kamikaze",
    "Light": "Ligero",
    "Maverick": "Rebelde",
    "Moderate": "Moderado",
    "Newcomer": "Recién llegado",
    "Novice": "Novato",
    "Pawngrabber": "Comepeones",
    "Pawnmaster": "Maestro de peones",
    "Positional": "Posicional",
    "Queentaker": "Cazadamas",
    "Woodpusher": "Empujamaderas",
}


@dataclass
class Rival:
    archivo: str
    nombre_original: str
    v: list = field(default_factory=list)

    @property
    def nombre(self) -> str:
        n = self.nombre_original
        if n.endswith("-Style"):
            return "Estilo " + n[:-6]
        return NOMBRES_ES.get(n, n)

    # parametros con nombre
    libro = property(lambda s: bool(s.v[0]))
    ataque = property(lambda s: -s.v[2])           # +100 = muy agresivo
    fuerza = property(lambda s: max(0, min(100, s.v[3])))
    azar = property(lambda s: max(0, min(100, s.v[4])))
    desprecio_tablas = property(lambda s: s.v[7])
    posicional = property(lambda s: s.v[8])

    def valor(self, pieza: int, propia: bool) -> int:
        idx = {chess.QUEEN: 14, chess.ROOK: 16, chess.BISHOP: 18,
               chess.KNIGHT: 20, chess.PAWN: 22}[pieza] + (0 if propia else 1)
        return self.v[idx]

    def descripcion(self) -> str:
        r = []
        f = self.fuerza
        r.append("Muy débil" if f < 25 else "Débil" if f < 50 else "Intermedio"
                 if f < 80 else "Fuerte" if f < 97 else "Fuerza máxima")
        if self.ataque >= 60:
            r.append("muy agresivo, sacrifica por el ataque")
        elif self.ataque >= 20:
            r.append("agresivo")
        elif self.ataque <= -60:
            r.append("muy defensivo")
        elif self.ataque <= -20:
            r.append("sólido y defensivo")
        if self.desprecio_tablas >= 1000:
            r.append("nunca acepta tablas")
        elif self.desprecio_tablas <= -1000:
            r.append("busca las tablas")
        elif self.desprecio_tablas >= 150:
            r.append("juega a ganar")
        if self.posicional >= 60:
            r.append("posicional")
        elif self.posicional <= -30:
            r.append("materialista")
        if self.valor(chess.PAWN, False) > 15:
            r.append("codicioso con los peones")
        if self.valor(chess.QUEEN, False) - self.valor(chess.QUEEN, True) > 15:
            r.append("obsesionado con la dama rival")
        if self.azar >= 30:
            r.append("impredecible")
        return ", ".join(r).capitalize() + "."


def leer_cmx(archivo: str, datos: bytes) -> Rival:
    if len(datos) < 144 or datos[33:36] != b"\x1a\x04\x81":
        raise ValueError("CMX no reconocido")
    nombre = datos[:33].split(b"\0")[0].decode("latin-1").strip()
    v = list(struct.unpack("<54h", datos[36:144]))
    return Rival(archivo, nombre, v)


# ----------------------------------------------------------------------------
# Como juega cada rival con Stockfish
# ----------------------------------------------------------------------------
def config_motor(r: Rival) -> dict:
    """Opciones UCI y limites de busqueda segun la fuerza."""
    f = r.fuerza
    if f >= 98 and r.azar == 0:
        return {"skill": 20, "tiempo": 2.0, "multipv": 4}
    skill = round((f / 100) ** 1.6 * 20)
    tiempo = 0.15 + 1.6 * (f / 100) ** 2
    return {"skill": skill, "tiempo": tiempo, "multipv": 6}


def elegir_jugada(r: Rival, board: chess.Board, candidatos, rng=random):
    """candidatos: [(chess.Move, cp desde el punto de vista del que mueve)].

    Aplica los gustos del rival sobre las mejores jugadas de Stockfish.
    """
    if not candidatos:
        return None
    mejor_cp = candidatos[0][1]
    tolerancia = 20 + (100 - r.fuerza) * 2.5        # centipeones de margen
    agresion = r.ataque / 100.0
    puntuadas = []
    for mv, cp in candidatos:
        if cp < mejor_cp - tolerancia:
            continue
        bono = 0.0
        captura = board.piece_at(mv.to_square) if board.is_capture(mv) else None
        if board.is_en_passant(mv):
            captura = chess.Piece(chess.PAWN, not board.turn)
        da_jaque = board.gives_check(mv)
        bono += agresion * (25 * da_jaque + 15 * (captura is not None))
        if not captura and not da_jaque:
            bono += max(0, r.posicional) * 0.1
        if captura:
            extra = r.valor(captura.piece_type, False) - _base(captura.piece_type)
            bono += extra * 4
        # actitud frente a las tablas
        board.push(mv)
        tablas = board.can_claim_draw() or board.is_stalemate() or board.is_insufficient_material()
        board.pop()
        if tablas:
            if r.desprecio_tablas >= 1000:
                bono -= 300
            elif r.desprecio_tablas <= -1000:
                bono += 300
            else:
                bono -= r.desprecio_tablas * 0.3
        puntuadas.append((cp + bono, mv))
    puntuadas.sort(key=lambda t: -t[0])
    # aleatoriedad: a veces una jugada no tan buena, o (muy debiles) una cualquiera
    if r.azar and rng.random() < r.azar / 250:
        legales = list(board.legal_moves)
        return rng.choice(legales)
    if r.azar or r.fuerza < 90:
        temp = 8 + r.azar * 1.5 + (100 - r.fuerza) * 0.8
        import math
        top = puntuadas[0][0]
        pesos = [math.exp((s - top) / temp) for s, _ in puntuadas]
        return rng.choices([m for _, m in puntuadas], weights=pesos)[0]
    return puntuadas[0][1]


def _base(pieza):
    return {chess.QUEEN: 90, chess.ROOK: 50, chess.BISHOP: 30,
            chess.KNIGHT: 30, chess.PAWN: 10}[pieza]
