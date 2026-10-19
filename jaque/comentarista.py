# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Comentarios en vivo durante la partida.

- Nombre de la apertura (código ECO y nombre en español).
- Evaluación de las jugadas del jugador con un Stockfish aparte, en segundo plano.
- Frases del rival según su personalidad (agresivo, defensivo, posicional...).
- Avisos de amenazas: piezas sin defensa y amenazas de mate.
"""
from __future__ import annotations

import json
import math
import random
import sys
from pathlib import Path

import chess
import chess.engine
from PySide6.QtCore import QObject, QThread, Signal, Slot

from .notacion import san_es

VALOR = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}
CON_ARTICULO = {chess.PAWN: "el peón", chess.KNIGHT: "el caballo", chess.BISHOP: "el alfil",
                chess.ROOK: "la torre", chess.QUEEN: "la dama", chess.KING: "el rey"}
TU_PIEZA = {chess.PAWN: "tu peón", chess.KNIGHT: "tu caballo", chess.BISHOP: "tu alfil",
            chess.ROOK: "tu torre", chess.QUEEN: "tu dama", chess.KING: "tu rey"}
FEM = {chess.ROOK, chess.QUEEN}
UN = {chess.PAWN: "un peón", chess.KNIGHT: "un caballo", chess.BISHOP: "un alfil",
      chess.ROOK: "una torre", chess.QUEEN: "la dama", chess.KING: "el rey"}

# Anotaciones de las jugadas del jugador
BUENA, IMPRECISION, ERROR, GRAVE = "!", "?!", "?", "??"
COLOR_ANOTACION = {BUENA: "#7fd67f", IMPRECISION: "#e8d070", ERROR: "#f0a050", GRAVE: "#ff6b6b"}
NAG = {BUENA: 1, IMPRECISION: 6, ERROR: 2, GRAVE: 4}


def _chances(cp: int) -> float:
    """Probabilidad de ganar en [-1, 1] a partir de centipeones (misma curva que usa Lichess)."""
    cp = max(-1500, min(1500, cp))
    return 2 / (1 + math.exp(-0.00368208 * cp)) - 1


def _cp(score: chess.engine.PovScore, color: bool) -> int:
    return score.pov(color).score(mate_score=10000)


# ---------------------------------------------------------------------------- aperturas
class Aperturas:
    def __init__(self):
        self.tabla: dict[str, list] = {}
        ruta = Path(__file__).resolve().parent / "datos" / "aperturas.json"
        try:
            self.tabla = json.loads(ruta.read_text(encoding="utf-8"))["aperturas"]
        except Exception:
            self.tabla = {}

    def buscar(self, board: chess.Board):
        if not self.tabla:
            return None
        return self.tabla.get(board.epd()) or self.tabla.get(board.epd(en_passant="fen"))

    def de_partida(self, board: chess.Board):
        """(eco, nombre, en_libro) de la última posición conocida de la partida, o None."""
        b = board.root()
        ultima = self.buscar(b) if b.fen() != chess.STARTING_FEN else None
        en_libro = False
        for mv in board.move_stack:
            b.push(mv)
            e = self.buscar(b)
            en_libro = e is not None
            if e:
                ultima = e
        if not ultima:
            return None
        return ultima[0], ultima[1], en_libro


# ---------------------------------------------------------------------------- amenazas
def piezas_colgando(board: chess.Board, color: bool):
    """Piezas de `color` (no peones ni rey) atacadas y sin defensa, o atacadas por algo de menos valor."""
    res = []
    for tipo in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT):
        for sq in board.pieces(tipo, color):
            atac = [a for a in board.attackers(not color, sq) if not board.is_pinned(not color, a)]
            if not atac:
                continue
            defs = board.attackers(color, sq)
            atac_val = [VALOR[board.piece_type_at(a)] or 100 for a in atac]
            menor = min(atac_val)
            if menor == 100 and defs:          # solo la ataca el rey y está defendida
                continue
            if not defs or menor < VALOR[tipo]:
                res.append((sq, tipo, bool(defs), atac[atac_val.index(menor)]))
    return res


def amenaza_de_mate(board: chess.Board, color: bool):
    """Si le toca a `color` y el rival amenaza mate en 1 (si `color` pasara), devuelve esa jugada en español."""
    if board.turn != color or board.is_check():
        return None
    b = board.copy(stack=False)
    b.push(chess.Move.null())
    for mv in list(b.legal_moves):
        san = san_es(b, mv)
        b.push(mv)
        mate = b.is_checkmate()
        b.pop()
        if mate:
            return san
    return None


def es_sacrificio(antes: chess.Board, mv: chess.Move) -> bool:
    """La pieza movida (caballo o más) queda en una casilla donde se la pueden comer con ganancia."""
    pieza = antes.piece_at(mv.from_square)
    if not pieza or pieza.piece_type in (chess.PAWN, chess.KING):
        return False
    capturada = antes.piece_at(mv.to_square)
    gano = VALOR[capturada.piece_type] if capturada else 0
    b = antes.copy(stack=False)
    b.push(mv)
    if b.is_checkmate():
        return False
    atac = b.attackers(b.turn, mv.to_square)
    if not atac:
        return False
    defs = b.attackers(not b.turn, mv.to_square)
    menor = min(VALOR[b.piece_type_at(a)] or 100 for a in atac)
    valor = VALOR[pieza.piece_type]
    pierde = valor if not defs else max(0, valor - menor)
    return pierde - gano >= 2


# ---------------------------------------------------------------------------- frases del rival
FRASES = {
    "inicio_blancas": {
        "agresivo": ["¡Que empiece la batalla! No pienso esperar.", "Hoy vengo con ganas de atacar.",
                     "Preparate, que esto se va a poner picante."],
        "defensivo": ["Vamos con calma. Primero, una posición sólida.", "Sin apuros: el que se apura, pierde.",
                      "Construyamos de a poco."],
        "posicional": ["Una buena partida empieza con un buen plan.", "Controlar el centro es lo primero.",
                       "Veamos quién entiende mejor la posición."],
        "materialista": ["Cada peón cuenta. No pienso regalar nada.", "Material es material."],
        "debil": ["Uy, a ver… ¿cómo era que se movía el caballo?", "¡Suerte! La vas a necesitar… o yo.",
                  "Hoy me siento inspirado. Creo."],
        "neutral": ["Buena suerte.", "Empecemos.", "Que gane el mejor."],
    },
    "inicio_negras": {
        "agresivo": ["Mové nomás. Después voy yo, y no voy a ser amable.", "Vos empezás, yo termino."],
        "defensivo": ["Te dejo la iniciativa. A ver qué hacés con ella.", "Atacá si querés. Te espero."],
        "posicional": ["Las blancas mueven primero, pero eso no decide nada.", "Veamos tu plan."],
        "materialista": ["Adelante. Cualquier cosa que dejes suelta, me la llevo."],
        "debil": ["¿Ya empezamos? Esperá que me acomodo…", "¡Uh, me tocaron las negras otra vez!"],
        "neutral": ["Adelante, te toca.", "Buena suerte."],
    },
    "jaque": {
        "agresivo": ["¡Jaque! Tu rey no va a tener descanso.", "¡Jaque! Y esto recién empieza.",
                     "¡Jaque! ¿Sentís el calor?"],
        "defensivo": ["Jaque. Un poco de presión no viene mal.", "Jaque, solo para ganar tiempo."],
        "posicional": ["Jaque, con idea.", "Jaque. Tu rey estaba muy expuesto."],
        "materialista": ["Jaque… y algo más se cae, ya vas a ver.", "Jaque. Cuidado con lo que dejás atrás."],
        "debil": ["¡Jaque! ¿Eso era jaque, no? ¡Sí!", "¡Jaque! Siempre quise decir eso."],
        "neutral": ["Jaque.", "Jaque al rey."],
    },
    "sacrificio": {
        "agresivo": ["¡Te regalo una pieza! A cambio quiero tu rey.", "¿Material? El ataque vale más.",
                     "¡Sacrificio! Comé si te animás."],
        "defensivo": ["Esto no es un regalo, es una prueba.", "Pensalo dos veces antes de tomar."],
        "posicional": ["Una pieza por la iniciativa. Me parece justo.", "La compensación está a la vista… para quien la vea."],
        "materialista": ["Esto me duele más a mí que a vos.", "Una inversión. Ya la voy a recuperar."],
        "debil": ["Ups… ¿la dejé ahí? Digo… ¡es una trampa!", "Mmm, eso no salió como esperaba."],
        "neutral": ["Ofrezco material. ¿Lo tomás?", "A ver qué hacés con esto."],
    },
    "captura_grande": {
        "agresivo": ["¡Fuera del tablero!", "¡Una menos! El ataque sigue."],
        "defensivo": ["Gracias, me la quedo.", "Material ganado. Ahora, a consolidar."],
        "posicional": ["Eso debilita bastante tu posición.", "Un cambio que me favorece."],
        "materialista": ["¡Mía! Me encanta el sonido de las piezas cayendo.", "Gracias por el regalo.",
                         "Una más para mi colección."],
        "debil": ["¡Gané una pieza! ¡Ja! No lo puedo creer.", "¡Mirá lo que capturé!"],
        "neutral": ["Capturo.", "Esa pieza se va."],
    },
    "come_dama": {
        "agresivo": ["¡Tu dama cayó! Ahora no hay quién me pare.", "¡Adiós, dama!"],
        "defensivo": ["Tu dama se fue. Ahora juego tranquilo.", "Sin dama vas a sufrir."],
        "posicional": ["Sin la dama, tu posición se desmorona.", "Eso decide bastante."],
        "materialista": ["¡La dama! ¡La pieza más valiosa! ¡Mía!", "Nueve puntos de material. Gracias."],
        "debil": ["¿Me comí la dama? ¡¿Me comí la dama?!", "¡La dama! ¡Hoy es mi día!"],
        "neutral": ["Me llevo tu dama.", "La dama cae."],
    },
    "enroque": {
        "agresivo": ["Rey a salvo. Ahora sí, al ataque.", "Enroco y voy por vos."],
        "defensivo": ["Primero, el rey bien guardado.", "Enroque. La seguridad ante todo."],
        "posicional": ["Enroque: el rey seguro y la torre al juego.", "Ahora conecto las torres."],
        "materialista": ["Enroco. Mis piezas están bien cuidadas.", "Enroque, sin perder nada."],
        "debil": ["Me dijeron que enrocar es bueno. ¡Ahí va!", "Enroco… creo que lo hice bien."],
        "neutral": ["Enroco.", "Pongo el rey a salvo."],
    },
    "corona": {
        "agresivo": ["¡Dama nueva! Esto se terminó.", "¡Corono! Preparate."],
        "defensivo": ["Coronación. Paciencia recompensada.", "El peón llegó. Paso a paso."],
        "posicional": ["El peón pasado hizo su trabajo.", "Coronación lógica."],
        "materialista": ["¡Más material! Me encanta.", "¡Una dama gratis!"],
        "debil": ["¡Coroné! ¡¿Viste?! ¡Coroné!", "¡Mi peoncito se hizo dama!"],
        "neutral": ["Corono.", "Nueva dama."],
    },
    "ventaja": {
        "agresivo": ["Siento olor a victoria.", "Tu rey ya está temblando.", "No vas a aguantar mucho más."],
        "defensivo": ["La posición está de mi lado. Sin errores, la gano.", "Ahora solo tengo que no equivocarme."],
        "posicional": ["Mi posición es claramente superior.", "Todo marcha según el plan."],
        "materialista": ["Tengo más material. Esto es cuestión de tiempo.", "Los números no mienten."],
        "debil": ["¿Estoy ganando? ¡Estoy ganando!", "¡Esto va bien! No me lo creo."],
        "neutral": ["La cosa pinta bien para mí.", "Me gusta mi posición."],
    },
    "desventaja": {
        "agresivo": ["Todavía tengo trucos guardados.", "Herido, pero no vencido.", "Esto no terminó."],
        "defensivo": ["Las posiciones difíciles se defienden. Y yo sé defender.", "Resistiré."],
        "posicional": ["Debo reconocer que jugaste bien.", "Mmm, algo se me escapó en el plan."],
        "materialista": ["Me falta material… no me gusta nada.", "¡Mis piezas! ¿Dónde quedaron?"],
        "debil": ["Ay, ay, ay…", "Creo que me estás ganando. ¿Podemos empezar de nuevo?"],
        "neutral": ["Estás jugando bien.", "Complicado…"],
    },
    "busca_tablas": ["Un empate no estaría nada mal, ¿no?", "Las tablas son un resultado honroso."],
    "mate_visto": {
        "agresivo": ["Ya veo el mate. No hay escapatoria.", "Contá las jugadas que te quedan."],
        "defensivo": ["Se terminó. Veo el final.", "Lo siento, pero ya está decidido."],
        "posicional": ["El mate es inevitable.", "Todo lleva al mate."],
        "materialista": ["Mate en camino. Y con material de sobra.", "Ya no importa el material: es mate."],
        "debil": ["¡Creo que veo un mate! ¿Será?", "¡Oh! ¿Eso es mate? ¡Es mate!"],
        "neutral": ["Hay mate.", "Veo el mate."],
    },
}


def estilo(rival) -> str:
    if rival is None:
        return "neutral"
    if rival.fuerza < 35:
        return "debil"
    if rival.ataque >= 20:
        return "agresivo"
    if rival.ataque <= -20:
        return "defensivo"
    if rival.posicional >= 60:
        return "posicional"
    if rival.posicional <= -30 or rival.valor(chess.PAWN, False) > 15:
        return "materialista"
    return "neutral"


def frase(clave: str, rival) -> str:
    p = FRASES[clave]
    if isinstance(p, list):
        return random.choice(p)
    return random.choice(p.get(estilo(rival)) or p["neutral"])


# ---------------------------------------------------------------------------- analista en segundo plano
class _Analista(QObject):
    listo = Signal(int, object)

    def __init__(self, ruta):
        super().__init__()
        self.ruta = ruta
        self.eng = None

    def _motor(self):
        if self.eng is None:
            extra = {}
            if sys.platform.startswith("win"):
                import subprocess
                extra["creationflags"] = subprocess.CREATE_NO_WINDOW
            self.eng = chess.engine.SimpleEngine.popen_uci(self.ruta, **extra)
            try:
                self.eng.configure({"Threads": 1, "Hash": 32})
            except Exception:
                pass
        return self.eng

    @Slot(int, str, str)
    def evaluar(self, pid, fen, uci):
        try:
            board = chess.Board(fen)
            mv = chess.Move.from_uci(uci)
            color = board.turn
            eng = self._motor()
            lim = chess.engine.Limit(depth=14, time=1.2)
            a = eng.analyse(board, lim)
            board.push(mv)
            if board.is_checkmate():
                d = {"score": chess.engine.PovScore(chess.engine.Mate(0), board.turn), "pv": []}
            elif board.is_game_over():
                d = {"score": chess.engine.PovScore(chess.engine.Cp(0), board.turn), "pv": []}
            else:
                d = eng.analyse(board, lim)
            self.listo.emit(pid, {"antes": a["score"].pov(color), "pv_antes": a.get("pv", []),
                                  "despues": d["score"].pov(color), "pv_despues": d.get("pv", [])})
        except Exception as e:  # pragma: no cover
            self.listo.emit(pid, {"error": str(e)})

    @Slot()
    def cerrar(self):
        if self.eng:
            try:
                self.eng.quit()
            except Exception:
                pass
            self.eng = None


class Comentarista(QObject):
    """Genera comentarios. La ventana conecta `comentario` y `anotacion`."""
    comentario = Signal(str, str, int)   # tipo (apertura|bien|imprecision|error|grave|rival|amenaza), html, ply
    anotacion = Signal(int, str)         # ply (1 = primera jugada), símbolo
    apertura = Signal(str)               # texto para la etiqueta de apertura ('' si ninguna)
    _pedir = Signal(int, str, str)
    _cerrar = Signal()

    def __init__(self, ruta_stockfish: str | None):
        super().__init__()
        self.aperturas = Aperturas()
        self.ruta = ruta_stockfish
        self.hilo = None
        self.analista = None
        self._id = 0
        self._pendientes: dict[int, tuple] = {}
        self.mostrar = {"apertura": True, "evaluar": True, "rival": True, "amenazas": True}
        self.reiniciar()

    # -- estado por partida
    def reiniciar(self):
        self._id += 1
        self._pendientes.clear()
        self._ultima_apertura = None
        self._ultima_familia = None
        self._ult_wc = None                  # chances del jugador tras su última jugada evaluada
        self._avisadas: set = set()
        self._jugadas_rival = 0
        self._ultimo_comentario_rival = -10
        self._dijo = set()                   # frases de estado ya dichas (ventaja, mate...)
        self._elogios = -10
        self._explicada = None
        self._amenaza_diferida = None
        self._cola = []

    def descartar_desde(self, ply: int):
        """Tras deshacer: olvida evaluaciones pendientes de jugadas que ya no existen."""
        self._pendientes = {k: v for k, v in self._pendientes.items() if v[0] < ply}
        self._amenaza_diferida = None
        self._explicada = None
        self._cola = []
        self._ult_wc = None
        self._avisadas = set()

    def _arrancar_analista(self):
        if self.hilo or not self.ruta:
            return
        self.hilo = QThread()
        self.analista = _Analista(self.ruta)
        self.analista.moveToThread(self.hilo)
        self._pedir.connect(self.analista.evaluar)
        self._cerrar.connect(self.analista.cerrar)
        self.analista.listo.connect(self._resultado)
        self.hilo.start()

    def apagar(self):
        if self.hilo:
            self.hilo.quit()
            self.hilo.wait(5000)
            self.analista.cerrar()
            self.hilo = None

    # -- aperturas
    def actualizar_apertura(self, board: chess.Board):
        if not self.mostrar["apertura"]:
            self.apertura.emit("")
            return
        r = self.aperturas.de_partida(board)
        if not r:
            self.apertura.emit("")
            return
        eco, nombre, en_libro = r
        self.apertura.emit(f"{eco} · {nombre}")
        if nombre != self._ultima_apertura and en_libro:
            self._ultima_apertura = nombre
            familia = nombre.split(":")[0]
            if familia != self._ultima_familia:
                self._ultima_familia = familia
                self.comentario.emit("apertura", f"Apertura: <b>{nombre}</b> ({eco})", 0)
            elif ":" in nombre:
                self.comentario.emit("apertura", f"Variante: <b>{nombre.split(':', 1)[1].strip()}</b> ({eco})", 0)

    # -- jugadas del jugador
    def jugada_humano(self, board_antes: chess.Board, mv: chess.Move, ply: int, prefijo: list, rival):
        if not self.mostrar["evaluar"] or not self.ruta:
            return
        self._arrancar_analista()
        self._id += 1
        despues = board_antes.copy(stack=False)
        despues.push(mv)
        en_libro = self.aperturas.buscar(despues) is not None
        self._pendientes[self._id] = (ply, list(prefijo), board_antes.copy(stack=False), mv, en_libro, rival)
        self._pedir.emit(self._id, board_antes.fen(), mv.uci())

    def vigente(self, board: chess.Board):
        self._tablero_actual = board

    def _resultado(self, pid, r):
        dato = self._pendientes.pop(pid, None)
        if not dato or "error" in r:
            return
        try:
            self._evaluar(dato, r)
        finally:
            if not self._pendientes:
                for c in self._cola:
                    self.comentario.emit(*c)
                self._cola = []
            dif = self._amenaza_diferida
            if dif and not self._pendientes:
                actual = getattr(self, "_tablero_actual", None)
                if actual is not None and actual.move_stack == dif[0].move_stack:
                    self.amenazas(actual, dif[1], dif[2])

    def _evaluar(self, dato, r):
        ply, prefijo, antes, mv, en_libro, rival = dato
        actual = getattr(self, "_tablero_actual", None)
        if actual is None or list(actual.move_stack[:ply]) != prefijo:
            return                                   # se deshizo o cambió la partida
        nombre_r = rival.nombre if rival else "El rival"
        s_antes, s_desp = r["antes"], r["despues"]
        wc_a = _chances(s_antes.score(mate_score=10000))
        wc_d = _chances(s_desp.score(mate_score=10000))
        caida = wc_a - wc_d                          # escala [-1, 1], umbrales como Lichess
        mejor = r["pv_antes"][0] if r["pv_antes"] else None
        jugada = san_es(antes, mv)
        mejor_san = san_es(antes, mejor) if mejor and mejor in antes.legal_moves else None
        es_mejor = mejor == mv
        prev = self._ult_wc
        self._ult_wc = wc_d

        despues = antes.copy(stack=False)
        despues.push(mv)
        if despues.is_checkmate():
            return

        # ¿desperdició un mate?
        if s_antes.is_mate() and s_antes.mate() > 0 and not (s_desp.is_mate() and s_desp.mate() > 0):
            self.anotacion.emit(ply, ERROR)
            n = s_antes.mate()
            txt = f"Tenías mate con <b>{mejor_san}</b>." if n == 1 else \
                f"Tenías mate en {n} empezando con <b>{mejor_san}</b>."
            self.comentario.emit("error", f"<b>{jugada}?</b> {txt}", ply)
            return

        simbolo = None
        if caida >= 0.30:
            simbolo = GRAVE
        elif caida >= 0.20:
            simbolo = ERROR
        elif caida >= 0.10:
            simbolo = IMPRECISION

        if simbolo == IMPRECISION and en_libro:
            simbolo = None                           # jugadas de libro: no molestamos por poco
        if simbolo:
            self.anotacion.emit(ply, simbolo)
            titulo = {GRAVE: "Error grave", ERROR: "Error", IMPRECISION: "Imprecisión"}[simbolo]
            expl = self._explicar(despues, r["pv_despues"], s_desp, nombre_r, mv, simbolo == IMPRECISION)
            if mejor_san and not es_mejor:
                expl += f" Era mejor <b>{mejor_san}</b>."
            tipo = {GRAVE: "grave", ERROR: "error", IMPRECISION: "imprecision"}[simbolo]
            self.comentario.emit(tipo, f"<b>{jugada}{simbolo}</b> {titulo}. {expl}".strip(), ply)
            if r["pv_despues"]:
                self._explicada = (ply + 1, r["pv_despues"][0])
            return

        # castigó un error del rival
        if prev is not None and wc_a - prev >= 0.30 and caida < 0.08:
            self.anotacion.emit(ply, BUENA)
            self.comentario.emit("bien", f"<b>{jugada}!</b> ¡Bien visto! Aprovechaste el error de {nombre_r}.", ply)
            self._elogios = ply
            return
        if s_desp.is_mate() and s_desp.mate() > 0 and not en_libro and ply - self._elogios >= 4:
            self.anotacion.emit(ply, BUENA)
            self.comentario.emit("bien", f"<b>{jugada}!</b> ¡Encontraste un mate en {s_desp.mate()}!", ply)
            self._elogios = ply
            return
        if es_mejor and not en_libro and ply - self._elogios >= 8 and \
                (antes.is_capture(mv) or antes.gives_check(mv) or random.random() < 0.25):
            self.comentario.emit("bien", f"<b>{jugada}</b> — buena jugada, es la que elegiría el motor.", ply)
            self._elogios = ply

    @staticmethod
    def _capturada(despues: chess.Board, mv: chess.Move):
        """Tipo de pieza que capturó la jugada `mv` (ya hecha en `despues`), o None."""
        b = despues.copy()
        try:
            b.pop()
        except IndexError:
            return None
        if b.is_en_passant(mv):
            return chess.PAWN
        return b.piece_type_at(mv.to_square)

    def _explicar(self, despues: chess.Board, pv, score, nombre_r, mv, leve=False) -> str:
        if score.is_mate() and score.mate() < 0:
            n = -score.mate()
            if pv and pv[0] in despues.legal_moves:
                return f"Ahora {nombre_r} tiene mate en {n}, empezando con <b>{san_es(despues, pv[0])}</b>."
            return f"Ahora {nombre_r} tiene mate en {n}."
        if not pv or pv[0] not in despues.legal_moves:
            return ""
        r = pv[0]
        san = san_es(despues, r)
        mejora = "su posición mejora un poco" if leve else "queda mejor"
        if despues.is_capture(r):
            sq = r.to_square
            tipo = despues.piece_type_at(sq) or chess.PAWN
            casilla = chess.square_name(sq)
            lo = "la" if tipo in FEM else "lo"
            atac = VALOR[despues.piece_type_at(r.from_square)] or 100
            defendida = bool(despues.attackers(not despues.turn, sq))   # defensores del jugador
            if not defendida:
                return (f"{TU_PIEZA[tipo].capitalize()} en {casilla} no tiene defensa: "
                        f"{nombre_r} puede comer{lo} con <b>{san}</b>.")
            if atac < VALOR[tipo]:
                return (f"{nombre_r} puede comer {TU_PIEZA[tipo]} en {casilla} con <b>{san}</b>, "
                        f"usando una pieza de menos valor.")
            # captura defendida y pareja: es un cambio, no una pieza perdida
            return f"{nombre_r} puede cambiar en {casilla} con <b>{san}</b> y {mejora}."
        b = despues.copy(stack=False)
        b.push(r)
        colg = piezas_colgando(b, b.turn)      # piezas del jugador atacadas tras la respuesta
        if b.is_check():
            return f"Permitís <b>{san}</b>, con jaque."
        if len(colg) >= 2:
            return f"{nombre_r} responde <b>{san}</b> y ataca dos piezas a la vez."
        if colg:
            return f"{nombre_r} responde <b>{san}</b> y ataca {TU_PIEZA[colg[0][1]]}."
        return f"{nombre_r} responde <b>{san}</b> y {mejora}."

    # -- jugadas del rival
    def jugada_rival(self, antes: chess.Board, mv: chess.Move, info: dict, rival, humano: bool):
        if not self.mostrar["rival"] or rival is None:
            return
        self._jugadas_rival += 1
        n = self._jugadas_rival
        clave = None
        importante = False
        pieza_cap = antes.piece_at(mv.to_square)
        despues = antes.copy(stack=False)
        despues.push(mv)
        if despues.is_checkmate():
            return
        sc = info.get("score")
        ev = sc.pov(antes.turn) if sc is not None else None

        if n == 1:
            clave = "inicio_blancas" if antes.turn == chess.WHITE else "inicio_negras"
            importante = True
        elif pieza_cap and pieza_cap.piece_type == chess.QUEEN:
            clave, importante = "come_dama", True
        elif mv.promotion:
            clave, importante = "corona", True
        elif ev is not None and ev.is_mate() and ev.mate() > 0 and "mate" not in self._dijo:
            self._dijo.add("mate")
            clave, importante = "mate_visto", True
        elif es_sacrificio(antes, mv):
            clave, importante = "sacrificio", True
        elif despues.is_check():
            clave = "jaque"
        elif antes.is_castling(mv):
            clave = "enroque"
        elif pieza_cap and VALOR[pieza_cap.piece_type] >= 3:
            clave = "captura_grande"
        elif ev is not None and not ev.is_mate():
            cp = ev.score()
            if cp >= 250 and "ventaja" not in self._dijo:
                self._dijo.add("ventaja")
                self._dijo.discard("desventaja")
                clave, importante = "ventaja", True
            elif cp <= -250 and "desventaja" not in self._dijo:
                self._dijo.add("desventaja")
                self._dijo.discard("ventaja")
                clave, importante = "desventaja", True
            elif -80 <= cp <= 0 and rival.desprecio_tablas <= -1000 and "tablas" not in self._dijo \
                    and len(antes.move_stack) > 30:
                self._dijo.add("tablas")
                clave, importante = "busca_tablas", True
        if not clave:
            return
        # no hablar en todas las jugadas: más charlatanes los agresivos y los débiles
        hablador = 0.55 if estilo(rival) in ("agresivo", "debil") else 0.35
        if not importante and (n - self._ultimo_comentario_rival < 3 or random.random() > hablador):
            return
        self._ultimo_comentario_rival = n
        html = f"<b>{rival.nombre}:</b> «{frase(clave, rival)}»"
        if self._pendientes:                     # que primero salga la evaluación de tu jugada
            self._cola.append(("rival", html, 0))
        else:
            self.comentario.emit("rival", html, 0)

    # -- amenazas, cuando le toca al jugador
    def amenazas(self, board: chess.Board, humano: bool, rival):
        if not self.mostrar["amenazas"] or board.turn != humano or board.is_game_over():
            return
        if self._pendientes:                     # primero que salga la evaluación de tu jugada
            self._amenaza_diferida = (board.copy(), humano, rival)
            return
        self._amenaza_diferida = None
        ex = self._explicada
        if ex and len(board.move_stack) == ex[0] and board.move_stack[-1] == ex[1]:
            # la evaluación ya explicó esta respuesta del rival: no repetir el aviso
            self._avisadas = {(sq, t) for sq, t, *_ in piezas_colgando(board, humano)}
            return
        nombre_r = rival.nombre if rival else "El rival"
        mate = amenaza_de_mate(board, humano)
        if mate:
            clave = ("mate", mate)
            if clave not in self._avisadas:
                self._avisadas = {clave}
                self.comentario.emit("amenaza", f"¡Cuidado! {nombre_r} amenaza mate con <b>{mate}</b>.", 0)
            return
        colg = piezas_colgando(board, humano)
        actuales = {(sq, tipo) for sq, tipo, *_ in colg}
        nuevas = [c for c in colg if (c[0], c[1]) not in self._avisadas]
        self._avisadas = actuales
        if not nuevas:
            return
        nuevas.sort(key=lambda c: -VALOR[c[1]])
        textos = []
        for sq, tipo, defendida, atacante in nuevas[:2]:
            atac = board.piece_type_at(atacante)
            if defendida:
                a = "atacada" if tipo in FEM else "atacado"
                textos.append(f"{TU_PIEZA[tipo]} en {chess.square_name(sq)} está {a} por "
                              f"{UN[atac]}")
            else:
                a = "atacada" if tipo in FEM else "atacado"
                textos.append(f"{TU_PIEZA[tipo]} en {chess.square_name(sq)} está {a} y sin defensa")
        txt = "; ".join(textos)
        txt = txt[:1].upper() + txt[1:]
        self.comentario.emit("amenaza", txt + ".", 0)
