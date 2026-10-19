"""Notación algebraica en español: R rey, D dama, T torre, A alfil, C caballo."""
import chess

_TABLA = str.maketrans({"K": "R", "Q": "D", "R": "T", "B": "A", "N": "C"})

NOMBRE_PIEZA = {
    chess.PAWN: "peón", chess.KNIGHT: "caballo", chess.BISHOP: "alfil",
    chess.ROOK: "torre", chess.QUEEN: "dama", chess.KING: "rey",
}


def san_es(board: chess.Board, move: chess.Move) -> str:
    return board.san(move).translate(_TABLA)


def linea_es(board: chess.Board, moves, max_jugadas=8) -> str:
    """Variante principal en español con números de jugada."""
    b = board.copy()
    partes = []
    for i, mv in enumerate(moves[:max_jugadas]):
        if mv not in b.legal_moves:
            break
        if b.turn == chess.WHITE:
            partes.append(f"{b.fullmove_number}.")
        elif i == 0:
            partes.append(f"{b.fullmove_number}...")
        partes.append(san_es(b, mv))
        b.push(mv)
    return " ".join(partes)


def evaluacion_es(score: chess.engine.PovScore | None, turno_blancas: bool) -> str:
    """Texto de evaluación desde el punto de vista de las blancas."""
    if score is None:
        return ""
    s = score.white()
    if s.is_mate():
        m = s.mate()
        return f"Mate en {abs(m)} para {'blancas' if m > 0 else 'negras'}"
    cp = s.score() / 100
    if abs(cp) < 0.3:
        juicio = "posición igualada"
    elif abs(cp) < 1.0:
        juicio = f"ligera ventaja {'blanca' if cp > 0 else 'negra'}"
    elif abs(cp) < 2.5:
        juicio = f"clara ventaja {'blanca' if cp > 0 else 'negra'}"
    else:
        juicio = f"ventaja decisiva {'blanca' if cp > 0 else 'negra'}"
    return f"{cp:+.2f} ({juicio})"


import chess.engine  # noqa: E402  (para el type hint)
