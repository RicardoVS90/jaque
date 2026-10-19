"""Widget del tablero: 2D o 3D en perspectiva, a cualquier resolución.

Todo se dibuja en "coordenadas de tablero" (x = columna 0..8, y = fila 0..8,
y hacia las negras) y una QTransform las lleva a la pantalla: afín en 2D y
proyectiva (homografía) en 3D. Así resaltados, puntos y flechas funcionan
igual en las dos vistas.
"""
from __future__ import annotations

import math

import chess
import numpy as np
from PySide6.QtCore import QEasingCurve, QPointF, QRectF, Qt, QVariantAnimation, Signal
from PySide6.QtGui import (QAction, QBrush, QColor, QFont, QIcon, QPainter, QPainterPath, QPen,
                           QPixmap, QPolygonF, QRadialGradient, QTransform)
from PySide6.QtWidgets import QMenu, QSizePolicy, QWidget

from .escalado import a_tamano, preparar

LETRA = {chess.PAWN: "P", chess.KNIGHT: "N", chess.BISHOP: "B",
         chess.ROOK: "R", chess.QUEEN: "Q", chess.KING: "K"}


def _homografia(src, dst):
    A = []
    for (x, y), (u, v) in zip(src, dst):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y, -u])
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y, -v])
    _, _, vt = np.linalg.svd(np.array(A, float))
    h = vt[-1].reshape(3, 3)
    return h / h[2, 2]


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
        self._img_tablero = None
        self._q_tablero = None
        self._t3d = None             # dict de assets.tablero_3d
        self._q_t3d = None
        self._q_fondo = None
        self._piezas_pil = {}
        self._q_piezas = {}
        self._es_3d_set = False
        self._max_w = self._max_h = 1
        self._cache = {}
        self._hits = []
        self.sel = None
        self.destinos = []
        self.arrastre = None
        self.ultima = None
        self.flecha = None
        self._anim = None
        self._anim_t = 1.0
        self._anim_mv = None
        self._T = QTransform()
        self._Hinv = None
        self.fantasmas = []          # [(casilla, chess.Piece)] translúcidas (tutoriales)
        self.resaltadas = set()      # casillas marcadas (tutoriales)

    # ------------------------------------------------------------------ estilo
    @property
    def es_3d(self):
        return self._t3d is not None

    def set_tablero_img(self, im):
        self._t3d = None
        self._img_tablero = im
        self._q_tablero = preparar(im, self.filtro) if im is not None else None
        self._cache.clear()
        self.update()

    def set_tablero_3d(self, datos: dict):
        self._img_tablero = None
        self._q_tablero = None
        self._t3d = datos
        self._preparar_3d()
        self._cache.clear()
        self.update()

    def _preparar_3d(self):
        d = self._t3d
        self._q_t3d = preparar(d["imagen"], self.filtro)
        self._q_fondo = preparar(d["fondo"], "suave") if d.get("fondo") is not None else None

    def set_colores(self, claro: QColor, oscuro: QColor):
        self.claro, self.oscuro = claro, oscuro
        self.update()

    def set_piezas(self, piezas_pil: dict, es_3d: bool):
        self._piezas_pil = piezas_pil
        self._es_3d_set = es_3d
        self._max_w = max(im.width for im in piezas_pil.values())
        self._max_h = max(im.height for im in piezas_pil.values())
        self._q_piezas = {k: preparar(v, self.filtro) for k, v in piezas_pil.items()}
        self._cache.clear()
        self.update()

    def set_filtro(self, filtro: str):
        self.filtro = filtro
        if self._img_tablero is not None:
            self._q_tablero = preparar(self._img_tablero, filtro)
        if self._t3d is not None:
            self._preparar_3d()
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
    def _bxy(self, casilla):
        """Esquina inferior izquierda de la casilla en coordenadas de tablero."""
        f, r = chess.square_file(casilla), chess.square_rank(casilla)
        if self.orientacion == chess.WHITE:
            return f, r
        return 7 - f, 7 - r

    def _geom2d(self):
        w, h = self.width(), self.height()
        margen_rel = 0.42 if self.coordenadas else 0.12
        sq = math.floor(min(w, h) / (8 + 2 * margen_rel))
        lado = sq * 8
        return (w - lado) / 2, (h - lado) / 2, sq

    def _alto_piezas(self):
        if self.es_3d:
            return 1.55 if self._es_3d_set else 0.95
        return 1.22 if self._es_3d_set else 0.92

    def _layout(self):
        """Calcula la transformación tablero→pantalla para el tamaño actual."""
        W, H = self.width(), self.height()
        if not self.es_3d:
            x0, y0, sq = self._geom2d()
            self._T = QTransform(sq, 0, 0, -sq, x0, y0 + 8 * sq)
            self._Hinv = None
            self._lay = (x0, y0, sq)
            return
        d = self._t3d
        bw, bh = d["imagen"].size
        c = d["esquinas"]
        fondo_w = math.dist(c[2], c[3]) / 8
        extra = max(0.0, fondo_w * self._alto_piezas() * 0.9 - c[3][1] - fondo_w * 0.1)
        m = 12
        s = min((W - 2 * m) / bw, (H - 2 * m) / (bh + extra))
        ox = (W - bw * s) / 2
        oy = (H - (bh + extra) * s) / 2 + extra * s
        dst = [(ox + x * s, oy + y * s) for x, y in c]
        Hm = _homografia([(0, 0), (8, 0), (8, 8), (0, 8)], dst)
        self._Hinv = np.linalg.inv(Hm)
        # QTransform usa vectores fila: m11 m12 m13 / m21 m22 m23 / m31 m32 m33
        self._T = QTransform(Hm[0, 0], Hm[1, 0], Hm[2, 0],
                             Hm[0, 1], Hm[1, 1], Hm[2, 1],
                             Hm[0, 2], Hm[1, 2], Hm[2, 2])
        self._lay = (ox, oy, s)

    def _a_pantalla(self, x, y) -> QPointF:
        return self._T.map(QPointF(x, y))

    def _a_tablero(self, p: QPointF):
        if self._Hinv is None:
            inv, ok = self._T.inverted()
            q = inv.map(p)
            return q.x(), q.y()
        v = self._Hinv @ np.array([p.x(), p.y(), 1.0])
        return v[0] / v[2], v[1] / v[2]

    def _casilla_en_tablero(self, p: QPointF):
        x, y = self._a_tablero(p)
        bx, by = math.floor(x), math.floor(y)
        if not (0 <= bx < 8 and 0 <= by < 8):
            return None
        if self.orientacion == chess.WHITE:
            return chess.square(bx, by)
        return chess.square(7 - bx, 7 - by)

    def _casilla_en(self, p: QPointF, preferir_pieza=False):
        c = self._casilla_en_tablero(p)
        if preferir_pieza:
            for rect, casilla in reversed(self._hits):   # de adelante hacia atrás
                if rect.contains(p):
                    return casilla
        return c

    def _poligono(self, casilla) -> QPolygonF:
        bx, by = self._bxy(casilla)
        return QPolygonF([self._a_pantalla(bx, by), self._a_pantalla(bx + 1, by),
                          self._a_pantalla(bx + 1, by + 1), self._a_pantalla(bx, by + 1)])

    def _pix(self, k, w, h):
        clave = (k, w, h, self.filtro)
        pm = self._cache.get(clave)
        if pm is None:
            pm = a_tamano(self._q_piezas[k], w, h, self.filtro, self.devicePixelRatioF())
            if len(self._cache) > 600:
                self._cache.clear()
            self._cache[clave] = pm
        return pm

    def _rect_pieza(self, pieza: chess.Piece, bx: float, by: float):
        """Rectángulo en pantalla de una pieza parada en (bx, by) (esquina de casilla)."""
        k = ("w" if pieza.color else "b", LETRA[pieza.piece_type])
        im = self._piezas_pil[k]
        izq = self._a_pantalla(bx, by + 0.5)
        der = self._a_pantalla(bx + 1, by + 0.5)
        sq = math.hypot(der.x() - izq.x(), der.y() - izq.y())
        alto = self._alto_piezas()
        f = min(sq * 0.92 / self._max_w, sq * alto / self._max_h)
        w, h = max(1, round(im.width * f)), max(1, round(im.height * f))
        if self.es_3d:
            pie = self._a_pantalla(bx + 0.5, by + 0.38)
            return k, QRectF(pie.x() - w / 2, pie.y() - h, w, h)
        cen = self._a_pantalla(bx + 0.5, by + 0.5)
        if h < sq * 0.96:
            return k, QRectF(cen.x() - w / 2, cen.y() - h / 2 + sq * 0.02, w, h)
        base = self._a_pantalla(bx + 0.5, by + 0.04)
        return k, QRectF(cen.x() - w / 2, base.y() - h, w, h)

    def _dibujar_pieza(self, p, pieza, bx, by, hit_casilla=None):
        if not self._q_piezas:
            return
        k, r = self._rect_pieza(pieza, bx, by)
        p.drawPixmap(r.topLeft(), self._pix(k, round(r.width()), round(r.height())))
        if hit_casilla is not None:
            self._hits.append((r, hit_casilla))

    # ------------------------------------------------------------------ pintura
    def paintEvent(self, _ev):
        self._layout()
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform, self.filtro != "pixel")
        if self.es_3d:
            self._pintar_escena_3d(p)
        else:
            self._pintar_base_2d(p)

        # resaltados (polígonos: valen en 2D y 3D)
        p.setPen(Qt.NoPen)
        if self.ultima is not None:
            for c in (self.ultima.from_square, self.ultima.to_square):
                p.setBrush(QColor(255, 215, 0, 90))
                p.drawPolygon(self._poligono(c))
        for c in self.resaltadas:
            p.setBrush(QColor(255, 140, 30, 125))
            p.drawPolygon(self._poligono(c))
        if self.sel is not None:
            p.setBrush(QColor(90, 200, 255, 115))
            p.drawPolygon(self._poligono(self.sel))
        if self.board.is_check():
            p.save()
            p.setTransform(self._T, True)
            bx, by = self._bxy(self.board.king(self.board.turn))
            g = QRadialGradient(QPointF(bx + 0.5, by + 0.5), 0.6)
            g.setColorAt(0, QColor(255, 0, 0, 210))
            g.setColorAt(1, QColor(255, 0, 0, 0))
            p.fillRect(QRectF(bx, by, 1, 1), QBrush(g))
            p.restore()

        # destinos legales (debajo de las piezas en 3D, para que se vean "en el piso")
        if self.es_3d:
            self._pintar_destinos(p)

        # piezas, de atrás hacia adelante
        self._hits = []
        anim_dest = self._anim_mv.to_square if (self._anim_mv and self._anim_t < 1) else None
        lista = []
        for c in chess.SQUARES:
            pieza = self.board.piece_at(c)
            if pieza is None or c == anim_dest:
                continue
            if self.arrastre and self.arrastre[0] == c:
                continue
            bx, by = self._bxy(c)
            lista.append((self._a_pantalla(bx + 0.5, by + 0.4).y(), pieza, bx, by, c))
        if anim_dest is not None and self.board.piece_at(anim_dest):
            a = self._bxy(self._anim_mv.from_square)
            b = self._bxy(anim_dest)
            t = self._anim_t
            bx, by = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
            lista.append((self._a_pantalla(bx + 0.5, by + 0.4).y() + 0.01,
                          self.board.piece_at(anim_dest), bx, by, None))
        lista.sort(key=lambda t: t[0])
        for _y, pieza, bx, by, c in lista:
            self._dibujar_pieza(p, pieza, bx, by, c)
        if self.fantasmas:
            p.setOpacity(0.45)
            for c, pieza in sorted(self.fantasmas, key=lambda t: self._a_pantalla(
                    self._bxy(t[0])[0] + 0.5, self._bxy(t[0])[1] + 0.4).y()):
                bx, by = self._bxy(c)
                self._dibujar_pieza(p, pieza, bx, by)
            p.setOpacity(1.0)

        if not self.es_3d:
            self._pintar_destinos(p)
        if self.flecha is not None:
            self._dibujar_flecha(p, self.flecha)
        if self.coordenadas and not self.es_3d:
            self._pintar_coordenadas(p)

        # pieza arrastrada (a la escala de la casilla bajo el puntero)
        if self.arrastre:
            c, pos = self.arrastre
            pieza = self.board.piece_at(c)
            if pieza:
                x, y = self._a_tablero(pos)
                x = min(max(x, 0.0), 7.999)
                y = min(max(y, 0.0), 7.999)
                k, r = self._rect_pieza(pieza, math.floor(x), math.floor(y))
                r.moveCenter(QPointF(pos.x(), pos.y() - r.height() * 0.25))
                p.drawPixmap(r.topLeft(), self._pix(k, round(r.width()), round(r.height())))
        p.end()

    def _pintar_base_2d(self, p):
        x0, y0, sq = self._lay
        lado = sq * 8
        marco = QRectF(x0, y0, lado, lado)
        borde = sq * (0.38 if self.coordenadas else 0.08)
        p.fillRect(marco.adjusted(-borde, -borde, borde, borde), QColor(43, 31, 22))
        p.setPen(QPen(QColor(120, 90, 55), max(1.0, sq * 0.03)))
        p.drawRect(marco.adjusted(-borde * 0.5, -borde * 0.5, borde * 0.5, borde * 0.5))
        if self._q_tablero is not None:
            clave = ("tablero", lado, self.filtro)
            pm = self._cache.get(clave)
            if pm is None:
                pm = a_tamano(self._q_tablero, lado, lado, self.filtro, self.devicePixelRatioF())
                self._cache[clave] = pm
            p.drawPixmap(QPointF(x0, y0), pm)
        else:
            p.setPen(Qt.NoPen)
            for c in chess.SQUARES:
                claro = (chess.square_file(c) + chess.square_rank(c)) % 2 == 1
                p.setBrush(self.claro if claro else self.oscuro)
                p.drawPolygon(self._poligono(c))

    def _pintar_escena_3d(self, p):
        W, H = self.width(), self.height()
        d = self._t3d
        dpr = self.devicePixelRatioF()
        if self._q_fondo is not None:
            modo = d["modo"]
            if modo == "mosaico":
                clave = ("fondo", "mosaico")
                pm = self._cache.get(clave)
                if pm is None:
                    q = self._q_fondo
                    pm = a_tamano(q, q.width() * 2, q.height() * 2, "suave", 1.0)
                    self._cache[clave] = pm
                p.fillRect(self.rect(), QBrush(pm))
            elif modo == "cubrir":
                q = self._q_fondo
                s = max(W / q.width(), H / q.height())
                w, h = round(q.width() * s), round(q.height() * s)
                clave = ("fondo", w, h)
                pm = self._cache.get(clave)
                if pm is None:
                    pm = a_tamano(q, w, h, "suave", dpr)
                    self._cache[clave] = pm
                p.drawPixmap(QPointF((W - w) / 2, (H - h) / 2), pm)
            else:
                clave = ("fondo", W, H)
                pm = self._cache.get(clave)
                if pm is None:
                    pm = a_tamano(self._q_fondo, W, H, "suave", dpr)
                    self._cache[clave] = pm
                p.drawPixmap(0, 0, pm)
        else:
            p.fillRect(self.rect(), QColor(30, 24, 20))
        ox, oy, s = self._lay
        bw, bh = d["imagen"].size
        w, h = round(bw * s), round(bh * s)
        clave = ("t3d", w, h, self.filtro)
        pm = self._cache.get(clave)
        if pm is None:
            pm = a_tamano(self._q_t3d, w, h, self.filtro, dpr)
            self._cache[clave] = pm
        p.drawPixmap(QPointF(ox, oy), pm)

    def _pintar_destinos(self, p):
        if not self.destinos:
            return
        p.save()
        p.setTransform(self._T, True)
        p.setPen(Qt.NoPen)
        for dsq in self.destinos:
            bx, by = self._bxy(dsq)
            cen = QPointF(bx + 0.5, by + 0.5)
            if self.board.piece_at(dsq):
                path = QPainterPath()
                path.addEllipse(cen, 0.47, 0.47)
                path.addEllipse(cen, 0.38, 0.38)
                p.setBrush(QColor(20, 20, 20, 130))
                p.drawPath(path)
            else:
                p.setBrush(QColor(20, 20, 20, 110))
                p.drawEllipse(cen, 0.15, 0.15)
        p.restore()

    def _pintar_coordenadas(self, p):
        x0, y0, sq = self._lay
        lado = sq * 8
        borde = sq * 0.38
        f = QFont(self.font())
        f.setPixelSize(max(9, int(sq * 0.24)))
        f.setBold(True)
        p.setFont(f)
        p.setPen(QColor(230, 210, 170))
        for i in range(8):
            col = i if self.orientacion == chess.WHITE else 7 - i
            fila = 7 - i if self.orientacion == chess.WHITE else i
            p.drawText(QRectF(x0 + i * sq, y0 + lado, sq, borde), Qt.AlignCenter, "abcdefgh"[col])
            p.drawText(QRectF(x0 - borde, y0 + i * sq, borde, sq), Qt.AlignCenter, str(fila + 1))

    def _dibujar_flecha(self, p, mv):
        ax, ay = self._bxy(mv.from_square)
        bx, by = self._bxy(mv.to_square)
        a = QPointF(ax + 0.5, ay + 0.5)
        b = QPointF(bx + 0.5, by + 0.5)
        dx, dy = b.x() - a.x(), b.y() - a.y()
        L = math.hypot(dx, dy) or 1
        ux, uy = dx / L, dy / L
        ancho, punta = 0.16, 0.42
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
        p.save()
        p.setTransform(self._T, True)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(40, 200, 90, 175))
        p.drawPath(path)
        p.restore()

    # ------------------------------------------------------------------ animación
    def _animar(self, mv):
        if self._anim:
            self._anim.stop()
        self._anim_mv = mv
        self._anim_t = 0.0
        an = QVariantAnimation(self)
        an.setStartValue(0.0)
        an.setEndValue(1.0)
        an.setDuration(260 if self.es_3d else 230)
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

    def _propia(self, c):
        pz = self.board.piece_at(c) if c is not None else None
        return pz is not None and pz.color == self.board.turn

    def _destino_en(self, pos):
        c = self._casilla_en_tablero(pos)
        if c in self.destinos:
            return c
        c2 = self._casilla_en(pos, preferir_pieza=True)
        return c2 if c2 in self.destinos else None

    def mousePressEvent(self, ev):
        if ev.button() != Qt.LeftButton or not self._puede_mover():
            return
        pos = ev.position()
        if self.sel is not None:
            d = self._destino_en(pos)
            if d is not None:
                self._intentar(self.sel, d)
                return
        c = self._casilla_en_tablero(pos)
        if not self._propia(c):
            c2 = self._casilla_en(pos, preferir_pieza=True)
            if self._propia(c2):
                c = c2
        if self._propia(c):
            self._seleccionar(c)
            self.arrastre = (c, pos)
            self.flecha = None
        else:
            self.sel, self.destinos = None, []
        self.update()

    def mouseMoveEvent(self, ev):
        if self.arrastre:
            self.arrastre = (self.arrastre[0], ev.position())
            self.update()
        elif self._puede_mover():
            pos = ev.position()
            mano = self._propia(self._casilla_en(pos, True)) or self._destino_en(pos) is not None
            self.setCursor(Qt.PointingHandCursor if mano else Qt.ArrowCursor)

    def mouseReleaseEvent(self, ev):
        if ev.button() != Qt.LeftButton or not self.arrastre:
            return
        origen = self.arrastre[0]
        self.arrastre = None
        c = self._casilla_en_tablero(ev.position())
        if c is not None and c != origen and c in self.destinos:
            self._intentar(origen, c)
        self.update()

    def _intentar(self, a, b):
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
        acc = {}
        for tipo, n in [(chess.QUEEN, "Dama"), (chess.ROOK, "Torre"),
                        (chess.BISHOP, "Alfil"), (chess.KNIGHT, "Caballo")]:
            a = QAction(self.icono_pieza(self.board.turn, tipo), n, m)
            m.addAction(a)
            acc[a] = tipo
        bx, by = self._bxy(casilla)
        pt = self._a_pantalla(bx + 0.5, by + 0.5).toPoint()
        return acc.get(m.exec(self.mapToGlobal(pt)))
