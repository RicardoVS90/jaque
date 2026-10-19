"""Widget del tablero: dibuja a cualquier resolución y maneja clic y arrastre."""
from __future__ import annotations

import math

import chess
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen,
                           QPolygonF, QRadialGradient)
from PySide6.QtWidgets import QMenu, QSizePolicy, QWidget

from .escalado import a_tamano, preparar

LETRA = {chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
         chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K"}


class Tablero(QWidget):
    jugada_hecha = Signal(object)  # chess.Move

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(360, 360)
        self.setMouseTracking(True)
        self.board = chess.Board()
        self.orientacion = chess.WHITE
        self.humanos = {chess.WHITE}
        self.interactivo = True
        self.coordenadas = True
        self.filtro = "mejorado"
        self.claro = QColor(222, 196, 150)
        self.oscuro = QColor(140, 96, 60)
        self._img_tablero = None   # PIL
        self._q_tablero = None
        self._piezas_pil = {}
        self._q_piezas = {}
        self._alto = 0.92
        self._max_w = self._max_h = 1
        self._cache = {}
        self.sel = None
        self.destinos = []
        self.arrastre = None       # (casilla, QPointF)
        self.ultima = None
        self.flecha = None
        self._anim = None
        self._anim_t = 1.0
        self._anim_mv = None

    # ------------------------------------------------------------------ estilo
    def set_tablero_img(self, im):
        self._img_tablero = im
        self._q_tablero = preparar(im, self.filtro) if im is not None else None
        self._cache.clear()
        self.update()

    def set_colores(self, claro: QColor, oscuro: QColor):
        self.claro, self.oscuro = claro, oscuro
        self.update()

    def set_piezas(self, piezas_pil: dict, es_3d: bool):
        self._piezas_pil = piezas_pil
        self._alto = 1.22 if es_3d else 0.92
        self._max_w = max(im.width for im in piezas_pil.values())
        self._max_h = max(im.height for im in piezas_pil.values())
        self._q_piezas = {k: preparar(v, self.filtro) for k, v in piezas_pil.items()}
        self._cache.clear()
        self.update()

    def set_filtro(self, filtro: str):
        self.filtro = filtro
        if self._img_tablero is not None:
            self._q_tablero = preparar(self._img_tablero, filtro)
        self._q_piezas = {k: preparar(v, filtro) for k, v in self._piezas_pil.items()}
        self._cache.clear()
        self.update()

    def icono_pieza(self, color: bool, tipo: int, lado=64) -> QIcon:
        k = ("w" if color else "b", LETRA[tipo])
        im = self._piezas_pil[k]
        f = lado / max(im.width, im.height)
        return QIcon(a_tamano(self._q_piezas[k], max(1, round(im.width * f)),
                              max(1, round(im.height * f)), self.filtro, self.devicePixelRatioF()))

    def pixmap_pieza(self, color: bool, tipo: int, alto: int):
        k = ("w" if color else "b", LETRA[tipo])
        im = self._piezas_pil[k]
        f = alto / self._max_h
        return self._pix(k, max(1, round(im.width * f)), max(1, round(im.height * f)))

    # ------------------------------------------------------------------ estado
    def set_posicion(self, board: chess.Board, ultima=None, animar=False):
        self.board = board
        self.ultima = ultima
        self.sel, self.destinos, self.arrastre = None, [], None
        self.flecha = None
        if animar and ultima is not None:
            self._animar(ultima)
        self.update()

    def girar(self):
        self.orientacion = not self.orientacion
        self.update()

    # ------------------------------------------------------------------ geometría
    def _geom(self):
        w, h = self.width(), self.height()
        margen_rel = 0.42 if self.coordenadas else 0.12
        sq = math.floor(min(w, h) / (8 + 2 * margen_rel))
        lado = sq * 8
        x0 = (w - lado) / 2
        y0 = (h - lado) / 2
        return x0, y0, sq

    def _rect(self, casilla):
        x0, y0, sq = self._geom()
        f, r = chess.square_file(casilla), chess.square_rank(casilla)
        if self.orientacion == chess.WHITE:
            cx, cy = f, 7 - r
        else:
            cx, cy = 7 - f, r
        return QRectF(x0 + cx * sq, y0 + cy * sq, sq, sq)

    def _casilla_en(self, p: QPointF):
        x0, y0, sq = self._geom()
        cx = math.floor((p.x() - x0) / sq)
        cy = math.floor((p.y() - y0) / sq)
        if not (0 <= cx < 8 and 0 <= cy < 8):
            return None
        if self.orientacion == chess.WHITE:
            return chess.square(cx, 7 - cy)
        return chess.square(7 - cx, cy)

    def _pix(self, k, w, h):
        clave = (k, w, h, self.filtro)
        pm = self._cache.get(clave)
        if pm is None:
            pm = a_tamano(self._q_piezas[k], w, h, self.filtro, self.devicePixelRatioF())
            self._cache[clave] = pm
        return pm

    def _dibujar_pieza(self, p: QPainter, pieza: chess.Piece, rect: QRectF):
        if not self._q_piezas:
            return
        k = ("w" if pieza.color else "b", LETRA[pieza.piece_type])
        im = self._piezas_pil[k]
        sq = rect.width()
        f = min(sq * 0.92 / self._max_w, sq * self._alto / self._max_h)
        w, h = max(1, round(im.width * f)), max(1, round(im.height * f))
        x = rect.center().x() - w / 2
        y = rect.bottom() - sq * 0.04 - h
        if h < sq * 0.96:   # piezas bajas: centradas verticalmente
            y = rect.center().y() - h / 2 + sq * 0.02
        p.drawPixmap(QPointF(x, y), self._pix(k, w, h))

    # ------------------------------------------------------------------ pintura
    def paintEvent(self, _ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.filtro != "pixel")
        x0, y0, sq = self._geom()
        lado = sq * 8
        marco = QRectF(x0, y0, lado, lado)

        # marco
        borde = sq * (0.38 if self.coordenadas else 0.08)
        p.fillRect(marco.adjusted(-borde, -borde, borde, borde), QColor(43, 31, 22))
        p.setPen(QPen(QColor(120, 90, 55), max(1.0, sq * 0.03)))
        p.drawRect(marco.adjusted(-borde * 0.5, -borde * 0.5, borde * 0.5, borde * 0.5))

        # casillas
        if self._q_tablero is not None:
            clave = ("tablero", lado, self.filtro)
            pm = self._cache.get(clave)
            if pm is None:
                pm = a_tamano(self._q_tablero, lado, lado, self.filtro, self.devicePixelRatioF())
                self._cache[clave] = pm
            p.drawPixmap(QPointF(x0, y0), pm)
        else:
            for c in chess.SQUARES:
                claro = (chess.square_file(c) + chess.square_rank(c)) % 2 == 1
                p.fillRect(self._rect(c), self.claro if claro else self.oscuro)

        # resaltados
        if self.ultima is not None:
            for c in (self.ultima.from_square, self.ultima.to_square):
                p.fillRect(self._rect(c), QColor(255, 215, 0, 85))
        if self.sel is not None:
            p.fillRect(self._rect(self.sel), QColor(90, 200, 255, 110))
        if self.board.is_check():
            r = self._rect(self.board.king(self.board.turn))
            g = QRadialGradient(r.center(), sq * 0.6)
            g.setColorAt(0, QColor(255, 0, 0, 200))
            g.setColorAt(1, QColor(255, 0, 0, 0))
            p.fillRect(r, QBrush(g))

        # piezas: de atrás hacia adelante para que las altas se superpongan bien
        orden = sorted(chess.SQUARES, key=lambda c: self._rect(c).top())
        anim_dest = self._anim_mv.to_square if (self._anim_mv and self._anim_t < 1) else None
        for c in orden:
            pieza = self.board.piece_at(c)
            if pieza is None or c == anim_dest:
                continue
            if self.arrastre and self.arrastre[0] == c:
                continue
            self._dibujar_pieza(p, pieza, self._rect(c))

        # pieza animada
        if anim_dest is not None:
            pieza = self.board.piece_at(anim_dest)
            if pieza:
                a, b = self._rect(self._anim_mv.from_square), self._rect(anim_dest)
                t = self._anim_t
                r = QRectF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t, sq, sq)
                self._dibujar_pieza(p, pieza, r)

        # destinos legales
        p.setPen(Qt.NoPen)
        for d in self.destinos:
            r = self._rect(d)
            if self.board.piece_at(d):
                p.setPen(QPen(QColor(20, 20, 20, 120), sq * 0.07))
                p.setBrush(Qt.NoBrush)
                p.drawEllipse(r.adjusted(sq * 0.06, sq * 0.06, -sq * 0.06, -sq * 0.06))
                p.setPen(Qt.NoPen)
            else:
                p.setBrush(QColor(20, 20, 20, 105))
                p.drawEllipse(r.center(), sq * 0.15, sq * 0.15)

        # flecha de sugerencia
        if self.flecha is not None:
            self._dibujar_flecha(p, self.flecha, sq)

        # coordenadas
        if self.coordenadas:
            f = QFont(self.font())
            f.setPixelSize(max(9, int(sq * 0.24)))
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(230, 210, 170))
            for i in range(8):
                col = i if self.orientacion == chess.WHITE else 7 - i
                fila = 7 - i if self.orientacion == chess.WHITE else i
                letra = "abcdefgh"[col]
                p.drawText(QRectF(x0 + i * sq, y0 + lado, sq, borde), Qt.AlignCenter, letra)
                p.drawText(QRectF(x0 - borde, y0 + i * sq, borde, sq), Qt.AlignCenter, str(fila + 1))

        # pieza arrastrada
        if self.arrastre:
            c, pos = self.arrastre
            pieza = self.board.piece_at(c)
            if pieza:
                r = QRectF(pos.x() - sq / 2, pos.y() - sq * 0.6, sq, sq)
                self._dibujar_pieza(p, pieza, r)
        p.end()

    def _dibujar_flecha(self, p, mv, sq):
        a = self._rect(mv.from_square).center()
        b = self._rect(mv.to_square).center()
        dx, dy = b.x() - a.x(), b.y() - a.y()
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        ancho = sq * 0.16
        punta = sq * 0.42
        fin = QPointF(b.x() - ux * punta, b.y() - uy * punta)
        nx, ny = -uy, ux
        path = QPainterPath()
        path.moveTo(a.x() + nx * ancho / 2, a.y() + ny * ancho / 2)
        path.lineTo(fin.x() + nx * ancho / 2, fin.y() + ny * ancho / 2)
        path.lineTo(fin.x() + nx * ancho * 1.6, fin.y() + ny * ancho * 1.6)
        path.lineTo(b.x(), b.y())
        path.lineTo(fin.x() - nx * ancho * 1.6, fin.y() - ny * ancho * 1.6)
        path.lineTo(fin.x() - nx * ancho / 2, fin.y() - ny * ancho / 2)
        path.lineTo(a.x() - nx * ancho / 2, a.y() - ny * ancho / 2)
        path.closeSubpath()
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(40, 200, 90, 170))
        p.drawPath(path)

    # ------------------------------------------------------------------ animación
    def _animar(self, mv):
        if self._anim:
            self._anim.stop()
        self._anim_mv = mv
        self._anim_t = 0.0
        an = QVariantAnimation(self)
        an.setStartValue(0.0)
        an.setEndValue(1.0)
        an.setDuration(230)
        an.setEasingCurve(QEasingCurve.OutCubic)
        an.valueChanged.connect(self._paso_anim)
        an.start()
        self._anim = an

    def _paso_anim(self, v):
        self._anim_t = float(v)
        self.update()

    # ------------------------------------------------------------------ ratón
    def _puede_mover(self):
        return self.interactivo and self.board.turn in self.humanos and not self.board.is_game_over()

    def _seleccionar(self, c):
        self.sel = c
        self.destinos = sorted({m.to_square for m in self.board.legal_moves if m.from_square == c})

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton or not self._puede_mover():
            return
        c = self._casilla_en(ev.position())
        if c is None:
            return
        if self.sel is not None and c in self.destinos:
            self._intentar(self.sel, c)
            return
        pieza = self.board.piece_at(c)
        if pieza and pieza.color == self.board.turn:
            self._seleccionar(c)
            self.arrastre = (c, ev.position())
            self.flecha = None
        else:
            self.sel, self.destinos = None, []
        self.update()

    def mouseMoveEvent(self, ev):
        if self.arrastre:
            self.arrastre = (self.arrastre[0], ev.position())
            self.update()
        elif self._puede_mover():
            c = self._casilla_en(ev.position())
            pieza = self.board.piece_at(c) if c is not None else None
            mano = pieza and pieza.color == self.board.turn or (c in self.destinos)
            self.setCursor(Qt.PointingHandCursor if mano else Qt.ArrowCursor)

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.LeftButton or not self.arrastre:
            return
        origen = self.arrastre[0]
        self.arrastre = None
        c = self._casilla_en(ev.position())
        if c is not None and c != origen and c in self.destinos:
            self._intentar(origen, c, sin_anim=True)
        self.update()

    def _intentar(self, a, b, sin_anim=False):
        mv = chess.Move(a, b)
        pieza = self.board.piece_at(a)
        if pieza and pieza.piece_type == chess.PAWN and chess.square_rank(b) in (0, 7):
            tipo = self._elegir_coronacion(b)
            if tipo is None:
                return
            mv = chess.Move(a, b, promotion=tipo)
        if mv in self.board.legal_moves:
            self.sel, self.destinos = None, []
            self.jugada_hecha.emit(mv)

    def _elegir_coronacion(self, casilla):
        m = QMenu(self)
        m.setStyleSheet("QMenu{font-size:15px} QMenu::item{padding:6px 18px 6px 8px}")
        nombres = [(chess.QUEEN, "Dama"), (chess.ROOK, "Torre"),
                   (chess.BISHOP, "Alfil"), (chess.KNIGHT, "Caballo")]
        acc = {}
        for tipo, n in nombres:
            a = QAction(self.icono_pieza(self.board.turn, tipo), n, m)
            m.addAction(a)
            acc[a] = tipo
        m.setTitle("Coronar")
        r = self._rect(casilla)
        elegido = m.exec(self.mapToGlobal(r.center().toPoint()))
        return acc.get(elegido)
