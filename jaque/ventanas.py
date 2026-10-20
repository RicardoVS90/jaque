# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo Vera.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Ventanas del Tutor y de las Partidas clásicas."""
from __future__ import annotations

import html

import chess
from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QLabel, QListWidget, QMainWindow,
                               QPushButton, QSplitter, QTextBrowser, QTreeWidget,
                               QTreeWidgetItem, QVBoxLayout, QWidget)

from . import tutoriales as T
from .clasicas import leer_coleccion
from .notacion import san_es
from .tablero import Tablero
from .traduccion import hay_traducciones, t

ESTILO_TEXTO = ("QTextBrowser{font-size:17px; padding:10px; background:#1e1712;"
                "border:1px solid #4a3a2a; border-radius:6px}")

AVISO_SIN_TRAD = ("<p style='color:#e8a060'><i>Todavía no hay traducción instalada para estos "
                  "textos: se muestran en inglés.</i></p>")


def _parrafos(textos):
    return "".join(f"<p>{html.escape(x)}</p>" for x in textos)


# ============================================================================
class VentanaTutor(QMainWindow):
    def __init__(self, recursos, estilizar, sonidos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jaque — Tutor de ajedrez")
        self.rec = recursos
        self.sonidos = sonidos
        self.tuts = []
        for arch, nombre in T.ARCHIVOS:
            if recursos.existe(arch):
                tut = T.parsear(recursos.leer(arch).decode("latin-1"))
                self.tuts.append((nombre, tut))
        self.cap = None
        self.k = 0
        self.estado = None
        self.resuelto = False

        self.arbol = QTreeWidget()
        self.arbol.setHeaderHidden(True)
        self.arbol.setMinimumWidth(270)
        for i, (nombre, tut) in enumerate(self.tuts):
            raiz = QTreeWidgetItem([nombre])
            raiz.setFlags(raiz.flags() & ~Qt.ItemIsSelectable)
            for j, cap in enumerate(tut.capitulos):
                it = QTreeWidgetItem([t(cap.nombre)])
                it.setData(0, Qt.UserRole, (i, j))
                raiz.addChild(it)
            self.arbol.addTopLevelItem(raiz)
        self.arbol.expandAll()
        self.arbol.itemClicked.connect(self._elegir)

        self.tablero = Tablero()
        estilizar(self.tablero)
        self.tablero.interactivo = False
        self.tablero.jugada_hecha.connect(self._jugada_usuario)

        self.texto = QTextBrowser()
        self.texto.setStyleSheet(ESTILO_TEXTO)
        self.lbl_cap = QLabel()
        self.lbl_cap.setStyleSheet("font-size:18px; font-weight:bold; color:#f0d9a8")
        self.lbl_pag = QLabel()
        self.lbl_jug = QLabel()
        self.lbl_jug.setWordWrap(True)
        self.lbl_jug.setStyleSheet("color:#cdb; font-size:15px")
        self.lbl_desafio = QLabel()
        self.lbl_desafio.setWordWrap(True)
        self.lbl_desafio.setTextFormat(Qt.RichText)
        self.lbl_desafio.setStyleSheet("font-size:16px; padding:6px; border-radius:6px")

        self.b_ant = QPushButton("◀  Anterior")
        self.b_jug = QPushButton("Jugada  ▶")
        self.b_sol = QPushButton("Ver solución")
        self.b_sig = QPushButton("Siguiente  ▶▶")
        for b in (self.b_ant, self.b_jug, self.b_sol, self.b_sig):
            b.setMinimumHeight(38)
        self.b_ant.clicked.connect(lambda: self._ir(self.k - 1))
        self.b_sig.clicked.connect(self._siguiente)
        self.b_jug.clicked.connect(self._paso_lista)
        self.b_sol.clicked.connect(self._solucion)
        QShortcut(QKeySequence(Qt.Key_Space), self, self._siguiente)
        QShortcut(QKeySequence(Qt.Key_Right), self, self._paso_lista)
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self._ir(self.k - 1))
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close)

        der = QWidget()
        v = QVBoxLayout(der)
        v.addWidget(self.lbl_cap)
        v.addWidget(self.lbl_pag)
        v.addWidget(self.texto, 1)
        v.addWidget(self.lbl_desafio)
        v.addWidget(self.lbl_jug)
        fila = QHBoxLayout()
        for b in (self.b_ant, self.b_jug, self.b_sol, self.b_sig):
            fila.addWidget(b)
        v.addLayout(fila)
        ayuda = QLabel("Espacio: siguiente · →: jugada · ←: anterior")
        ayuda.setStyleSheet("color:#988")
        v.addWidget(ayuda)

        sp = QSplitter()
        sp.addWidget(self.arbol)
        sp.addWidget(self.tablero)
        sp.addWidget(der)
        sp.setStretchFactor(1, 3)
        sp.setStretchFactor(2, 2)
        sp.setSizes([280, 900, 560])
        self.setCentralWidget(sp)
        self.resize(1700, 950)
        if self.tuts:
            self._abrir(0, 0)

    # ------------------------------------------------------------------
    def _elegir(self, item, _col):
        d = item.data(0, Qt.UserRole)
        if d:
            self._abrir(*d)

    def _abrir(self, i, j):
        self.ti, self.ci = i, j
        self.cap = self.tuts[i][1].capitulos[j]
        self.lbl_cap.setText(f"{self.tuts[i][0]} — {t(self.cap.nombre)}")
        self._ir(0)

    def _ir(self, k):
        if self.cap is None or not (0 <= k < len(self.cap.paginas)):
            return
        self.k = k
        self.estado = T.estado_en(self.cap, k)
        self.resuelto = False
        self.mostradas = []
        e = self.estado
        b = e.board.copy(stack=False)
        self.tablero.fantasmas = list(e.fantasmas)
        self.tablero.resaltadas = set(e.resaltadas)
        self.tablero.orientacion = chess.WHITE
        self.tablero.set_posicion(b, e.ultima, animar=e.ultima is not None)
        self.tablero_actual = b
        txt = [t(x) for x in e.textos]
        aviso = "" if hay_traducciones() else AVISO_SIN_TRAD
        self.texto.setHtml(aviso + _parrafos(txt))
        self.lbl_pag.setText(f"Página {k + 1} de {len(self.cap.paginas)}")
        if e.desafio:
            quien = "blancas" if b.turn == chess.WHITE else "negras"
            self.lbl_desafio.setText(f"🎯  Desafío: hacé en el tablero la jugada correcta "
                                     f"(juegan las {quien}).")
            self.lbl_desafio.setStyleSheet("font-size:16px; padding:6px; border-radius:6px;"
                                           "background:#4a3415")
            self.lbl_desafio.show()
            self.tablero.humanos = {b.turn}
            self.tablero.interactivo = True
        else:
            self.lbl_desafio.hide()
            self.tablero.interactivo = False
        self._actualizar_botones()

    def _pendientes(self):
        e = self.estado
        if e is None:
            return []
        if e.desafio and not self.resuelto:
            return []
        return e.lista[len(self.mostradas):]

    def _actualizar_botones(self):
        self.b_ant.setEnabled(self.k > 0)
        self.b_jug.setEnabled(bool(self._pendientes()))
        self.b_sol.setEnabled(bool(self.estado and self.estado.desafio and not self.resuelto))
        ultimo_cap = self.ci + 1 >= len(self.tuts[self.ti][1].capitulos)
        fin = self.k + 1 >= len(self.cap.paginas)
        self.b_sig.setText("Terminar" if (fin and ultimo_cap) else
                           "Siguiente capítulo  ▶▶" if fin else "Siguiente  ▶▶")
        self.lbl_jug.setText(("Jugadas: " + " ".join(self.mostradas)) if self.mostradas else "")

    def _siguiente(self):
        if self.cap is None:
            return
        if self.k + 1 < len(self.cap.paginas):
            self._ir(self.k + 1)
        elif self.ci + 1 < len(self.tuts[self.ti][1].capitulos):
            self._abrir(self.ti, self.ci + 1)
            self._seleccionar_en_arbol()
        else:
            self.close()

    def _seleccionar_en_arbol(self):
        raiz = self.arbol.topLevelItem(self.ti)
        if raiz and self.ci < raiz.childCount():
            self.arbol.setCurrentItem(raiz.child(self.ci))

    def _empujar(self, mv):
        b = self.tablero_actual
        texto = san_es(b, mv)
        captura = b.is_capture(mv)
        b.push(mv)
        self.mostradas.append(texto)
        self.tablero.set_posicion(b, mv, animar=True)
        if self.sonidos:
            self.sonidos.tocar("jaque" if b.is_check() else "captura" if captura else
                               "mueve_negras" if b.turn == chess.WHITE else "mueve_blancas")

    def _paso_lista(self):
        pend = self._pendientes()
        if not pend:
            return
        mv = T.jugada(self.tablero_actual, pend[0])
        if mv is None:
            self.mostradas.append("?")
        else:
            self._empujar(mv)
        self._actualizar_botones()

    def _esperada(self):
        return T.jugada(self.tablero_actual.copy(stack=False), self.estado.desafio[0])

    def _jugada_usuario(self, mv):
        if not self.estado or not self.estado.desafio or self.resuelto:
            return
        if mv == self._esperada():
            self.resuelto = True
            self.tablero.interactivo = False
            self._empujar(mv)
            if self.sonidos:
                self.sonidos.tocar("campana")
            msg = t(self.estado.desafio[1]) if self.estado.desafio[1] else "¡Correcto!"
            self.lbl_desafio.setText(f"✔  {html.escape(msg)}")
            self.lbl_desafio.setStyleSheet("font-size:16px; padding:6px; border-radius:6px;"
                                           "background:#25502a")
        else:
            if self.sonidos:
                self.sonidos.tocar("error")
            self.lbl_desafio.setText("✘  Esa no es la jugada. Probá otra vez "
                                     "(o tocá «Ver solución»).")
            self.lbl_desafio.setStyleSheet("font-size:16px; padding:6px; border-radius:6px;"
                                           "background:#5a2020")
            self.tablero.set_posicion(self.tablero_actual, self.estado.ultima)
        self._actualizar_botones()

    def _solucion(self):
        if not self.estado or not self.estado.desafio or self.resuelto:
            return
        mv = self._esperada()
        self.resuelto = True
        self.tablero.interactivo = False
        if mv:
            self._empujar(mv)
        self.lbl_desafio.setText("La jugada correcta era " + (self.mostradas[-1] if mv else
                                                               self.estado.desafio[0]) + ".")
        self.lbl_desafio.setStyleSheet("font-size:16px; padding:6px; border-radius:6px;"
                                       "background:#3a3a3a")
        self._actualizar_botones()


# ============================================================================
class VentanaClasicas(QMainWindow):
    jugar_desde = Signal(object)   # chess.Board

    def __init__(self, recursos, estilizar, sonidos, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Jaque — Partidas clásicas comentadas")
        self.rec = recursos
        self.sonidos = sonidos
        self.archivos = [f"CLASSIC{i}.CML" for i in range(1, 10) if recursos.existe(f"CLASSIC{i}.CML")]
        self._cache = {}
        self.partida = None
        self.k = 0

        self.cb_col = QComboBox()
        self.lista = QListWidget()
        self.lista.setMinimumWidth(320)
        self.lista.currentRowChanged.connect(self._elegir_partida)
        self.cb_col.currentIndexChanged.connect(self._elegir_coleccion)

        self.tablero = Tablero()
        estilizar(self.tablero)
        self.tablero.interactivo = False

        self.lbl_tit = QLabel()
        self.lbl_tit.setWordWrap(True)
        self.lbl_tit.setStyleSheet("font-size:18px; font-weight:bold; color:#f0d9a8")
        self.coment = QTextBrowser()
        self.coment.setStyleSheet(ESTILO_TEXTO)
        self.movs = QTextBrowser()
        self.movs.setOpenLinks(False)
        self.movs.anchorClicked.connect(lambda url: self._ir(int(url.toString().lstrip("#"))))
        self.movs.setStyleSheet("QTextBrowser{font-size:15px; padding:6px}")

        botones = QHBoxLayout()
        self.b_ini = QPushButton("⏮")
        self.b_ant = QPushButton("◀")
        self.b_sig = QPushButton("▶")
        self.b_fin = QPushButton("⏭")
        self.b_auto = QPushButton("Reproducir")
        self.b_auto.setCheckable(True)
        self.b_girar = QPushButton("Girar")
        self.b_jugar = QPushButton("Jugar desde aquí")
        self.b_ini.clicked.connect(lambda: self._ir(0))
        self.b_ant.clicked.connect(lambda: self._ir(self.k - 1))
        self.b_sig.clicked.connect(lambda: self._ir(self.k + 1))
        self.b_fin.clicked.connect(lambda: self._ir(len(self.partida.jugadas) if self.partida else 0))
        self.b_auto.toggled.connect(self._auto)
        self.b_girar.clicked.connect(self.tablero.girar)
        self.b_jugar.clicked.connect(self._jugar)
        for b in (self.b_ini, self.b_ant, self.b_sig, self.b_fin, self.b_auto, self.b_girar,
                  self.b_jugar):
            b.setMinimumHeight(36)
            botones.addWidget(b)
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self._ir(self.k + 1))
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self._ir(self.k - 1))
        QShortcut(QKeySequence(Qt.Key_Home), self, lambda: self._ir(0))
        QShortcut(QKeySequence(Qt.Key_End), self, lambda: self.b_fin.click())
        QShortcut(QKeySequence(Qt.Key_Escape), self, self.close)
        self.timer = QTimer(self)
        self.timer.setInterval(1600)
        self.timer.timeout.connect(self._tic)

        izq = QWidget()
        vi = QVBoxLayout(izq)
        vi.addWidget(QLabel("Colección:"))
        vi.addWidget(self.cb_col)
        vi.addWidget(self.lista, 1)

        centro = QWidget()
        vc = QVBoxLayout(centro)
        vc.addWidget(self.tablero, 1)
        vc.addLayout(botones)

        der = QWidget()
        vd = QVBoxLayout(der)
        vd.addWidget(self.lbl_tit)
        vd.addWidget(self.coment, 2)
        vd.addWidget(self.movs, 3)

        sp = QSplitter()
        sp.addWidget(izq)
        sp.addWidget(centro)
        sp.addWidget(der)
        sp.setStretchFactor(1, 3)
        sp.setStretchFactor(2, 2)
        sp.setSizes([330, 900, 520])
        self.setCentralWidget(sp)
        self.resize(1750, 980)

        for arch in self.archivos:
            titulo, _ = self._coleccion(arch)
            self.cb_col.addItem(t(titulo), arch)

    def _coleccion(self, arch):
        if arch not in self._cache:
            self._cache[arch] = leer_coleccion(self.rec.leer(arch))
        return self._cache[arch]

    def _elegir_coleccion(self, idx):
        arch = self.cb_col.itemData(idx)
        if not arch:
            return
        _, partidas = self._coleccion(arch)
        self.partidas = partidas
        self.lista.clear()
        for p in partidas:
            fecha = f" ({p.fecha})" if p.fecha else ""
            self.lista.addItem(f"{p.blancas} – {p.negras}{fecha}")
        if partidas:
            self.lista.setCurrentRow(0)

    def _elegir_partida(self, fila):
        if fila < 0 or fila >= len(getattr(self, "partidas", [])):
            return
        self.partida = self.partidas[fila]
        p = self.partida
        partes = [f"{p.blancas} – {p.negras}"]
        if p.evento:
            partes.append(t(p.evento))
        if p.fecha and p.fecha not in (p.evento or ""):
            partes.append(p.fecha)
        self.lbl_tit.setText(", ".join(partes))
        self.tablero.orientacion = chess.WHITE
        self._html_movs()
        self._ir(0)

    def _html_movs(self):
        p = self.partida
        b = chess.Board(p.fen)
        out = []
        for i, mv in enumerate(p.jugadas):
            if b.turn == chess.WHITE:
                out.append(f"<b style='color:#a98'>{b.fullmove_number}.</b>")
            elif i == 0:
                out.append(f"<b style='color:#a98'>{b.fullmove_number}...</b>")
            out.append(f"<a name='m{i + 1}'></a><a href='#{i + 1}' "
                       f"style='color:#f0e0c8; text-decoration:none'>"
                       f"<span id='m{i + 1}'>{html.escape(san_es(b, mv))}</span></a>")
            b.push(mv)
            if i in p.comentarios:
                out.append(f"<span style='color:#9c8'>💬</span>")
        self._movs_base = out
        self.movs.setHtml(" ".join(out))

    def _ir(self, k):
        p = self.partida
        if p is None:
            return
        k = max(0, min(k, len(p.jugadas)))
        avanza = k == self.k + 1
        self.k = k
        b = chess.Board(p.fen)
        for mv in p.jugadas[:k]:
            b.push(mv)
        ultima = p.jugadas[k - 1] if k else None
        self.tablero.set_posicion(b, ultima, animar=avanza)
        if avanza and self.sonidos and ultima is not None:
            self.sonidos.tocar("jaque" if b.is_check() else "mueve_negras" if b.turn else "mueve_blancas")
        # comentario
        aviso = "" if hay_traducciones() else AVISO_SIN_TRAD
        if k == 0:
            cuerpo = _parrafos([t(p.intro)]) if p.intro else "<p><i>Sin introducción.</i></p>"
        else:
            tmp = chess.Board(p.fen)
            for mv in p.jugadas[:k - 1]:
                tmp.push(mv)
            num = f"{tmp.fullmove_number}{'.' if tmp.turn == chess.WHITE else '...'} "
            cab = f"<p style='color:#e8c070'><b>{num}{html.escape(san_es(tmp, ultima))}</b></p>"
            com = p.comentarios.get(k - 1)
            cuerpo = cab + (_parrafos([t(com)]) if com else "")
        if k == len(p.jugadas) and k:
            cuerpo += "<p style='color:#bbb'><i>Fin de la partida.</i></p>"
        self.coment.setHtml(aviso + cuerpo)
        # resaltar jugada actual
        out = list(self._movs_base)
        if k:
            out = [x.replace(f"<span id='m{k}'>", f"<span id='m{k}' style='background:#8a6a2a'>")
                   for x in out]
        self.movs.setHtml(" ".join(out))
        if k:
            self.movs.scrollToAnchor(f"m{k}")

    def _auto(self, on):
        self.b_auto.setText("Pausa" if on else "Reproducir")
        self.timer.start() if on else self.timer.stop()

    def _tic(self):
        if not self.partida or self.k >= len(self.partida.jugadas):
            self.b_auto.setChecked(False)
            return
        self._ir(self.k + 1)

    def _jugar(self):
        if not self.partida:
            return
        b = chess.Board(self.partida.fen)
        for mv in self.partida.jugadas[:self.k]:
            b.push(mv)
        self.jugar_desde.emit(b)
