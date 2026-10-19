"""Intérprete de los tutoriales .TUT de Chessmaster 4000.

El formato es un pequeño guion: cada capítulo es una secuencia de órdenes
(BOARD, DIAGRAM, MOVELIST, MOVE, SLIDE, CHALLENGE, GHOST, NEWHIGH, …) y
textos entre comillas; la orden OK separa una "página" de la siguiente.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import chess

ARCHIVOS = [("RULES.TUT", "Reglas del ajedrez"),
            ("TUTORIAL.TUT", "Curso en 10 niveles"),
            ("ICE.TUT", "Estrategia y conceptos")]

PIEZAS = {"KING": chess.KING, "QUEEN": chess.QUEEN, "ROOK": chess.ROOK,
          "BISHOP": chess.BISHOP, "KNIGHT": chess.KNIGHT, "PAWN": chess.PAWN}


@dataclass
class Pagina:
    acciones: list = field(default_factory=list)


@dataclass
class Capitulo:
    nombre: str
    paginas: list = field(default_factory=list)


@dataclass
class Tutorial:
    titulo: str
    capitulos: list = field(default_factory=list)


# ----------------------------------------------------------------------------
def fen_tut(texto: str):
    """'rnbqkbnr/pppppppp/32/PPPPPPPP/RNBQKBNR' -> board_fen estándar."""
    if texto.strip() == "64":
        return "8/8/8/8/8/8/8/8"
    flujo = ""
    for tok in re.findall(r"\d+|[prnbqkPRNBQK]", texto):
        flujo += "." * int(tok) if tok.isdigit() else tok
    flujo = (flujo + "." * 64)[:64]
    filas = []
    for i in range(8):
        fila, vac = "", 0
        for ch in flujo[i * 8:(i + 1) * 8]:
            if ch == ".":
                vac += 1
            else:
                if vac:
                    fila += str(vac)
                    vac = 0
                fila += ch
        if vac:
            fila += str(vac)
        filas.append(fila)
    return "/".join(filas)


def fen_diagrama(texto: str):
    """'Ke1,Qd1 v Ke8,Qd8' o 'a2,b2,Ke2 v a7,Ke7' -> board_fen."""
    b = chess.Board(None)
    partes = texto.split(" v ")
    for idx, parte in enumerate(partes):
        color = chess.WHITE if idx == 0 else chess.BLACK
        for tok in re.split(r"[,\s]+", parte.strip()):
            if not tok:
                continue
            m = re.fullmatch(r"([KQRBNPkqrbnp]?)([a-h][1-8])", tok)
            if not m:
                continue
            letra, casilla = m.groups()
            c = color
            if letra and letra.islower():
                c = chess.BLACK
            tipo = chess.PIECE_SYMBOLS.index(letra.lower()) if letra else chess.PAWN
            b.set_piece_at(chess.parse_square(casilla), chess.Piece(tipo, c))
    return b.board_fen()


def parsear(texto: str) -> Tutorial:
    texto = texto.replace("\r", "").replace("\x1a", "")
    lineas = [l for l in texto.split("\n") if not l.strip().startswith("//")]
    texto = "\n".join(lineas)
    tit = re.search(r'TITLE\s+"([^"]*)"', texto)
    tut = Tutorial(tit.group(1) if tit else "")
    nombres = []
    m = re.search(r"BEGIN NAMES(.*?)END NAMES", texto, re.S)
    if m:
        nombres = re.findall(r'"([^"]*)"', m.group(1))
    for m in re.finditer(r"BEGIN CHAPTER\s+(\d+)(.*?)END CHAPTER", texto, re.S):
        n = int(m.group(1))
        cap = Capitulo(nombres[n] if n < len(nombres) else f"Capítulo {n}")
        cap.paginas = _paginas(m.group(2))
        tut.capitulos.append(cap)
    return tut


_ES_SAN = re.compile(r"^(?:\d+\.+)?(?:[KQRBN]?[a-h]?[1-8]?x?[a-h][1-8](?:=?[QRBN])?|O-O(?:-O)?)"
                     r"[+#!?]*$")


def _paginas(cuerpo: str):
    paginas, actual = [], Pagina()
    # recorrer línea a línea, pero los textos pueden ocupar varias líneas
    i = 0
    n = len(cuerpo)
    while i < n:
        while i < n and cuerpo[i] in " \t\n":
            i += 1
        if i >= n:
            break
        if cuerpo[i] == '"':
            j = cuerpo.find('"', i + 1)
            if j == -1:
                j = n
            actual.acciones.append(("texto", cuerpo[i + 1:j]))
            i = j + 1
            # descartar basura hasta fin de línea (p. ej. una 'L' suelta)
            k = cuerpo.find("\n", i)
            resto = cuerpo[i:k if k != -1 else n]
            if not resto.strip() or len(resto.strip()) <= 2:
                i = k if k != -1 else n
            continue
        k = cuerpo.find("\n", i)
        linea = cuerpo[i:k if k != -1 else n]
        # una orden puede llevar un texto entre comillas que sigue en otras líneas
        if linea.count('"') % 2 == 1:
            k2 = cuerpo.find('"', cuerpo.find('"', i) + 1)
            k = cuerpo.find("\n", k2)
            linea = cuerpo[i:k if k != -1 else n]
        i = k if k != -1 else n
        accion = _orden(linea.strip())
        if accion is None:
            continue
        if accion == ("ok",):
            paginas.append(actual)
            actual = Pagina()
        else:
            actual.acciones.append(accion)
    if actual.acciones:
        paginas.append(actual)
    return paginas


def _orden(linea: str):
    if not linea:
        return None
    partes = linea.split(None, 1)
    cmd = partes[0].upper()
    arg = partes[1] if len(partes) > 1 else ""
    turno = chess.BLACK if re.search(r"\bBLACK\b", arg) else chess.WHITE
    if cmd == "OK":
        return ("ok",)
    if cmd == "BOARD":
        pos = arg.split()[0] if arg.split() else "64"
        return ("tablero", fen_tut(pos), turno)
    if cmd == "DIAGRAM":
        m = re.search(r'"([^"]*)"', arg)
        return ("tablero", fen_diagrama(m.group(1) if m else ""), turno)
    if cmd == "MOVELIST":
        m = re.search(r'"([^"]*)"', arg)
        toks = (m.group(1) if m else "").split()
        movs = []
        for i, tk in enumerate(toks):
            if not _ES_SAN.match(tk):
                # comilla de cierre faltante en el original: el resto es texto
                return ("lista", movs, " ".join(toks[i:]))
            movs.append(tk)
        return ("lista", movs, "")
    if cmd == "MOVE":
        return ("mover", arg.strip())
    if cmd == "SLIDE":
        a = arg.split()
        if len(a) >= 2:
            return ("deslizar", a[0], a[1])
        return None
    if cmd == "CHALLENGE":
        m = re.match(r'(\S+)\s*(?:"([^"]*)")?', arg)
        if m:
            return ("desafio", m.group(1), m.group(2) or "")
        return None
    if cmd == "GHOST":
        a = arg.split()
        if len(a) >= 3 and a[1].upper() in PIEZAS:
            color = chess.WHITE if a[0].upper() == "WHITE" else chess.BLACK
            return ("fantasma", color, PIEZAS[a[1].upper()], a[2])
        return None
    if cmd == "NOGHOST":
        return ("sin_fantasmas",)
    if cmd == "NEWHIGH":
        return ("resaltar", re.findall(r"[a-h][1-8]", arg))
    if cmd == "CLRHIGH":
        return ("sin_resaltar",)
    return None  # TITLE, NOTATION, BEGIN ..., texto suelto: se ignoran


# ----------------------------------------------------------------------------
def limpiar_san(s: str) -> str:
    s = s.replace("++", "#").replace("e.p.", "")
    s = re.sub(r"[!?]+", "", s)
    s = re.sub(r"^\d+\.+", "", s)
    return s.strip()


def jugada(board: chess.Board, san: str):
    """Interpreta SAN con tolerancia (tableros sin rey, turno mal indicado)."""
    s = limpiar_san(san)
    if not s:
        return None
    for intento in range(2):
        try:
            return board.parse_san(s)
        except Exception:
            pass
        # pseudo-legales (p. ej. posiciones didácticas sin rey)
        for mv in board.pseudo_legal_moves:
            try:
                if board.san(mv).rstrip("+#") == s.rstrip("+#"):
                    return mv
            except Exception:
                pass
        # ambigua en el original (p. ej. "Rc8" con dos torres): la primera que sirva
        m = re.fullmatch(r"([KQRBN])x?([a-h][1-8])[+#]?", s)
        if m:
            tipo = chess.PIECE_SYMBOLS.index(m.group(1).lower())
            dest = chess.parse_square(m.group(2))
            for mv in board.legal_moves:
                if mv.to_square == dest and board.piece_type_at(mv.from_square) == tipo:
                    return mv
        if intento == 0:
            board.turn = not board.turn
    board.turn = not board.turn
    return None


@dataclass
class Estado:
    board: chess.Board
    textos: list
    fantasmas: list
    resaltadas: set
    lista: list            # jugadas pendientes de la MOVELIST
    desafio: tuple | None  # (san, mensaje)
    ultima: chess.Move | None = None
    deslizar: list = field(default_factory=list)


def aplicar(estado: Estado | None, pagina: Pagina) -> Estado:
    """Estado al mostrar una página, partiendo del estado al terminar la anterior."""
    if estado is None:
        estado = Estado(chess.Board(None), [], [], set(), [], None)
    b = estado.board.copy(stack=False)
    e = Estado(b, [], list(estado.fantasmas), set(estado.resaltadas), [], None)
    for acc in pagina.acciones:
        tipo = acc[0]
        if tipo == "texto":
            e.textos.append(acc[1])
        elif tipo == "tablero":
            e.board = chess.Board(None)
            e.board.set_board_fen(acc[1])
            e.board.turn = acc[2]
            e.board.set_castling_fen("KQkq")
            e.board.castling_rights = e.board.clean_castling_rights()
            e.fantasmas = []
            e.ultima = None
        elif tipo == "lista":
            e.lista = list(acc[1])
            if len(acc) > 2 and acc[2]:
                e.textos.append(acc[2])
        elif tipo == "mover":
            mv = jugada(e.board, acc[1])
            if mv:
                e.board.push(mv)
                e.ultima = mv
        elif tipo == "deslizar":
            try:
                a, d = chess.parse_square(acc[1]), chess.parse_square(acc[2])
            except ValueError:
                continue
            pz = e.board.piece_at(a)
            if pz:
                e.board.remove_piece_at(a)
                e.board.set_piece_at(d, pz)
                e.board.turn = not pz.color
                e.ultima = chess.Move(a, d)
        elif tipo == "desafio":
            e.desafio = (acc[1], acc[2])
        elif tipo == "fantasma":
            try:
                e.fantasmas.append((chess.parse_square(acc[3]), chess.Piece(acc[2], acc[1])))
            except ValueError:
                pass
        elif tipo == "sin_fantasmas":
            e.fantasmas = []
        elif tipo == "resaltar":
            e.resaltadas = {chess.parse_square(c) for c in acc[1]}
        elif tipo == "sin_resaltar":
            e.resaltadas = set()
    if e.desafio and e.lista:
        mv = jugada(e.board.copy(), e.desafio[0])
        mv2 = jugada(e.board.copy(), e.lista[0])
        if mv and mv == mv2:
            e.lista = e.lista[1:]
            e.lista_tras_desafio = True
    return e


def cerrar(e: Estado) -> Estado:
    """Estado al salir de la página: se aplican desafío y jugadas pendientes."""
    e2 = Estado(e.board.copy(stack=False), [], list(e.fantasmas), set(e.resaltadas), [], None)
    if e.desafio:
        mv = jugada(e2.board, e.desafio[0])
        if mv and mv in e2.board.pseudo_legal_moves:
            e2.board.push(mv)
    for san in e.lista:
        mv = jugada(e2.board, san)
        if mv:
            e2.board.push(mv)
    return e2


def estado_en(capitulo: Capitulo, k: int) -> Estado:
    e = None
    for i in range(k):
        e = cerrar(aplicar(e, capitulo.paginas[i]))
    return aplicar(e, capitulo.paginas[k])
