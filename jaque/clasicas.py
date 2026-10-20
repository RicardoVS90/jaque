# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo Vera.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Lectura de las colecciones de partidas clásicas (.CML) del juego original.

Formato deducido del archivo:
  cabecera: título de la colección (32 bytes), 1A 04, cantidad de partidas
            y una tabla de desplazamientos en ASCII (campos de 8 bytes).
  partida:  "The Chessmaster 4000 Turbo (c) " (32 bytes), 1A 04,
            título (80), blancas (33), negras (33), evento (100), fecha (100),
            ... tablero inicial (64 bytes, a8..h1) en +0x180,
            cantidad de medias jugadas (uint32) en +0x1C0,
            texto de introducción terminado en 0 en +0x1C4,
            y luego registros de 4 bytes por jugada:
              bits 0-5 destino, 6-11 origen (0 = a8 ... 63 = h1),
              12-14 coronación, bit 15 = sigue un comentario terminado en 0.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

import chess

MARCA = b"The Chessmaster 4000 Turbo (c) "
PIEZA = {0: chess.KING, 1: chess.QUEEN, 2: chess.ROOK, 3: chess.BISHOP, 4: chess.KNIGHT, 5: chess.PAWN}
CORONA = {1: chess.QUEEN, 2: chess.ROOK, 3: chess.BISHOP, 4: chess.KNIGHT}


@dataclass
class Partida:
    titulo: str
    blancas: str
    negras: str
    evento: str
    fecha: str
    fen: str
    intro: str
    jugadas: list = field(default_factory=list)      # chess.Move
    comentarios: dict = field(default_factory=dict)  # índice de media jugada -> texto
    errores: int = 0


def _cad(b: bytes) -> str:
    return b.split(b"\0")[0].decode("latin-1").strip()


def _sq(idx):
    # 0 = a8 ... 63 = h1  ->  python-chess (0 = a1)
    fila, col = divmod(idx, 8)
    return chess.square(col, 7 - fila)


def _tablero(b64: bytes):
    tb = chess.Board(None)
    for i, v in enumerate(b64):
        if v == 0:
            continue
        color = chess.WHITE if v & 0xF0 == 0x10 else chess.BLACK
        tipo = PIEZA.get(v & 0x0F)
        if tipo:
            tb.set_piece_at(_sq(i), chess.Piece(tipo, color))
    return tb


def leer_coleccion(datos: bytes):
    titulo = _cad(datos[:32])
    partidas = []
    pos = datos.find(MARCA)
    inicios = []
    while pos != -1:
        inicios.append(pos)
        pos = datos.find(MARCA, pos + 1)
    for n, ini in enumerate(inicios):
        fin = inicios[n + 1] if n + 1 < len(inicios) else len(datos)
        partidas.append(_leer_partida(datos[ini:fin]))
    return titulo, partidas


def _leer_partida(g: bytes) -> Partida:
    tit = _cad(g[0x22:0x72])
    bl, ng = _cad(g[0x72:0x93]), _cad(g[0x93:0xB4])
    ev, fe = _cad(g[0xB4:0x118]), _cad(g[0x118:0x17C])
    tb = _tablero(g[0x180:0x1C0])
    inicial = chess.Board()
    if tb.board_fen() == inicial.board_fen():
        board = chess.Board()
    else:
        board = tb
        board.turn = chess.WHITE
        board.castling_rights = board.clean_castling_rights()
    p = Partida(tit, bl, ng, ev, fe, board.fen(), "")
    i = 0x1C4
    j = g.find(b"\0", i)
    p.intro = g[i:j].decode("latin-1").strip()
    i = j + 1
    while i + 4 <= len(g):
        (v,) = struct.unpack("<I", g[i:i + 4])
        i += 4
        if v == 0 and i >= len(g) - 4:
            break
        destino, origen = v & 63, (v >> 6) & 63
        cor = (v >> 12) & 7
        mv = chess.Move(_sq(origen), _sq(destino), promotion=CORONA.get(cor))
        if mv.promotion is None and board.piece_type_at(mv.from_square) == chess.PAWN \
                and chess.square_rank(mv.to_square) in (0, 7):
            mv.promotion = chess.QUEEN
        if mv in board.legal_moves:
            board.push(mv)
            p.jugadas.append(mv)
        else:
            p.errores += 1
            break
        if v & 0x8000:
            j = g.find(b"\0", i)
            if j == -1:
                j = len(g)
            p.comentarios[len(p.jugadas) - 1] = g[i:j].decode("latin-1").strip()
            i = j + 1
    return p
