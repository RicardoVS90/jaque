"""Ventana principal de Jaque."""
from __future__ import annotations

import datetime
import random
import sys
from pathlib import Path

import chess
import chess.pgn
from PySide6.QtCore import QLibraryInfo, QSettings, Qt, QTimer, QTranslator
from PySide6.QtGui import QAction, QActionGroup, QColor, QFont, QKeySequence, QPalette, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QComboBox, QDialog,
                               QProgressDialog,
                               QDialogButtonBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
                               QGroupBox, QHBoxLayout, QHeaderView, QLabel, QMainWindow,
                               QMessageBox, QProgressBar, QPushButton, QSizePolicy, QSplashScreen,
                               QSplitter, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from . import __version__
from .assets import FuenteError, Recursos
from .escalado import FILTROS, pil_a_qimage
from .motor import Motor, buscar_stockfish
from .notacion import NOMBRE_PIEZA, evaluacion_es, linea_es, san_es
from .sonidos import Sonidos
from .tablero import Tablero

CACHE = Path.home() / ".cache" / "jaque"

CONTROLES = [
    ("Sin reloj", 0, 0), ("Blitz 5 min", 300, 0), ("Blitz 3 + 2", 180, 2),
    ("Rápida 10 min", 600, 0), ("Rápida 15 + 10", 900, 10), ("Clásica 30 min", 1800, 0),
]

COLORES_PLANOS = {
    "colores:clasico": ("Colores: clásico", QColor(232, 208, 166), QColor(160, 114, 74)),
    "colores:verde": ("Colores: torneo verde", QColor(238, 238, 210), QColor(118, 150, 86)),
    "colores:azul": ("Colores: azul", QColor(222, 227, 230), QColor(120, 150, 180)),
    "colores:gris": ("Colores: gris", QColor(210, 210, 210), QColor(120, 120, 128)),
}


def _fmt_reloj(seg):
    seg = max(0, seg)
    if seg < 20:
        return f"{int(seg // 60)}:{seg % 60:04.1f}"
    return f"{int(seg // 60)}:{int(seg % 60):02d}"


# ----------------------------------------------------------------------------
class DialogoRecursos(QDialog):
    def __init__(self, parent=None, mensaje=""):
        super().__init__(parent)
        self.setWindowTitle("Archivos del juego original")
        self.ruta = None
        lay = QVBoxLayout(self)
        t = QLabel(
            "<h3>Falta preparar los gráficos y sonidos</h3>"
            "<p>Elegí la imagen <b>.ISO</b> de tu CD (o la carpeta donde está "
            "instalado). Jaque va a copiar lo que necesita una sola vez y después "
            "no te lo vuelve a pedir.</p>"
            + (f"<p style='color:#e66'>{mensaje}</p>" if mensaje else ""))
        t.setWordWrap(True)
        lay.addWidget(t)
        fila = QHBoxLayout()
        b1 = QPushButton("Abrir imagen ISO…")
        b2 = QPushButton("Elegir carpeta…")
        b1.clicked.connect(self._iso)
        b2.clicked.connect(self._dir)
        fila.addWidget(b1)
        fila.addWidget(b2)
        lay.addLayout(fila)
        bb = QDialogButtonBox(QDialogButtonBox.Cancel)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.resize(520, 220)

    def _iso(self):
        r, _ = QFileDialog.getOpenFileName(self, "Imagen del CD", str(Path.home()),
                                           "Imágenes de CD (*.iso *.ISO);;Todos (*)")
        if r:
            self.ruta = r
            self.accept()

    def _dir(self):
        r = QFileDialog.getExistingDirectory(self, "Carpeta del juego", str(Path.home()))
        if r:
            self.ruta = r
            self.accept()


def _preparar_con_progreso(origen, parent=None) -> Path:
    """Arma el paquete de recursos mostrando una ventanita de progreso."""
    from .preparar import preparar
    dlg = QProgressDialog("Preparando gráficos y sonidos…", None, 0, 0, parent)
    dlg.setWindowTitle("Jaque")
    dlg.setMinimumDuration(0)
    dlg.setWindowModality(Qt.ApplicationModal)
    dlg.show()
    QApplication.processEvents()

    def avisar(txt):
        dlg.setLabelText(txt.strip())
        QApplication.processEvents()
    try:
        return preparar(origen, avisar=avisar)
    finally:
        dlg.close()


class DialogoNuevaPartida(QDialog):
    def __init__(self, rivales, tablero: Tablero, previo: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva partida")
        self.rivales = rivales
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.cb_rival = QComboBox()
        for r in rivales:
            self.cb_rival.addItem(f"{r.nombre}   ·   fuerza {r.fuerza}", r)
        idx = next((i for i, r in enumerate(rivales) if r.archivo == previo.get("rival")), 0)
        self.cb_rival.setCurrentIndex(idx)
        self.desc = QLabel()
        self.desc.setWordWrap(True)
        self.desc.setStyleSheet("color:#cbb; font-style:italic")
        self.cb_rival.currentIndexChanged.connect(self._desc)
        self.cb_color = QComboBox()
        self.cb_color.addItem(tablero.icono_pieza(chess.WHITE, chess.KING, 48), "Blancas", "w")
        self.cb_color.addItem(tablero.icono_pieza(chess.BLACK, chess.KING, 48), "Negras", "b")
        self.cb_color.addItem("Al azar", "r")
        self.cb_color.setCurrentIndex({"w": 0, "b": 1, "r": 2}.get(previo.get("color", "w"), 0))
        self.cb_reloj = QComboBox()
        for n, base, inc in CONTROLES:
            self.cb_reloj.addItem(n, (base, inc))
        self.cb_reloj.setCurrentIndex(int(previo.get("reloj", 0)))
        form.addRow("Rival:", self.cb_rival)
        form.addRow("", self.desc)
        form.addRow("Jugás con:", self.cb_color)
        form.addRow("Control de tiempo:", self.cb_reloj)
        lay.addLayout(form)
        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setText("Jugar")
        bb.button(QDialogButtonBox.Cancel).setText("Cancelar")
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._desc()
        self.resize(560, 260)

    def _desc(self):
        r = self.cb_rival.currentData()
        self.desc.setText(r.descripcion() if r else "")

    def resultado(self):
        color = self.cb_color.currentData()
        if color == "r":
            color = random.choice("wb")
        return {"rival": self.cb_rival.currentData(), "color": color,
                "color_elegido": self.cb_color.currentData(),
                "reloj": self.cb_reloj.currentIndex(), "tiempo": self.cb_reloj.currentData()}


# ----------------------------------------------------------------------------
class VentanaPrincipal(QMainWindow):
    def __init__(self, recursos: Recursos, settings: QSettings):
        super().__init__()
        self.rec = recursos
        self.cfg = settings
        self.setWindowTitle("Jaque")
        self.rivales = sorted(recursos.rivales(), key=lambda r: (r.fuerza, r.nombre))
        self.rival = self._rival_por_archivo(self.cfg.value("rival", "CHESMSTR.CMX"))
        self.sonidos = Sonidos(recursos, CACHE / "sonidos")
        self.sonidos.activos = self.cfg.value("sonido", True, type=bool)

        ruta_sf = buscar_stockfish(self.cfg.value("stockfish", None))
        self.motor = Motor(ruta_sf) if ruta_sf else None
        if self.motor:
            self.motor.jugada.connect(self._jugada_motor)
            self.motor.sugerencia.connect(self._sugerencia_lista)
            self.motor.error.connect(lambda m: self.statusBar().showMessage(m, 8000))

        self.board = chess.Board()
        self.humano = chess.WHITE
        self.pensando = False
        self.terminada = False
        self.eval_rival = 0
        self.reloj = [0.0, 0.0]          # [negras, blancas] (índice = chess.Color)
        self.incremento = 0
        self.con_reloj = False

        self._construir_ui()
        self._construir_menus()
        self._aplicar_apariencia()
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tic)
        self.timer.start()
        geo = self.cfg.value("geometria")
        if geo:
            self.restoreGeometry(geo)
        else:
            self.resize(1500, 950)
        QTimer.singleShot(0, self._inicio)

    # ------------------------------------------------------------------ UI
    def _construir_ui(self):
        self.tablero = Tablero()
        self.tablero.jugada_hecha.connect(self._jugada_humano)
        self.tablero.coordenadas = self.cfg.value("coordenadas", True, type=bool)

        panel = QWidget()
        panel.setMinimumWidth(330)
        v = QVBoxLayout(panel)
        v.setContentsMargins(10, 10, 10, 10)
        v.setSpacing(10)

        g_rival = QGroupBox("Rival")
        gr = QVBoxLayout(g_rival)
        self.lbl_rival = QLabel()
        self.lbl_rival.setStyleSheet("font-size:20px; font-weight:bold; color:#f0d9a8")
        self.lbl_desc = QLabel()
        self.lbl_desc.setWordWrap(True)
        self.lbl_desc.setStyleSheet("color:#cbb")
        self.bar_fuerza = QProgressBar()
        self.bar_fuerza.setRange(0, 100)
        self.bar_fuerza.setFormat("Fuerza %v/100")
        gr.addWidget(self.lbl_rival)
        gr.addWidget(self.lbl_desc)
        gr.addWidget(self.bar_fuerza)
        v.addWidget(g_rival)

        relojes = QGridLayout()
        self.lbl_reloj = {}
        for col, color in enumerate((chess.WHITE, chess.BLACK)):
            caja = QFrame()
            caja.setObjectName("reloj")
            cl = QVBoxLayout(caja)
            cl.setContentsMargins(8, 4, 8, 4)
            t = QLabel("Blancas" if color else "Negras")
            t.setAlignment(Qt.AlignCenter)
            r = QLabel("—")
            r.setAlignment(Qt.AlignCenter)
            r.setStyleSheet("font-size:28px; font-family:monospace; font-weight:bold")
            cl.addWidget(t)
            cl.addWidget(r)
            relojes.addWidget(caja, 0, col)
            self.lbl_reloj[color] = (caja, r)
        v.addLayout(relojes)

        self.lbl_estado = QLabel()
        self.lbl_estado.setAlignment(Qt.AlignCenter)
        self.lbl_estado.setStyleSheet("font-size:16px; padding:6px; background:#3a2a1e;"
                                      "border-radius:6px")
        v.addWidget(self.lbl_estado)

        self.capt = {chess.WHITE: QLabel(), chess.BLACK: QLabel()}
        for c in (chess.BLACK, chess.WHITE):
            self.capt[c].setMinimumHeight(52)
            v.addWidget(self.capt[c])

        self.tabla = QTableWidget(0, 3)
        self.tabla.setHorizontalHeaderLabels(["N.º", "Blancas", "Negras"])
        self.tabla.verticalHeader().setVisible(False)
        self.tabla.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabla.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tabla.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.tabla.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabla.setSelectionMode(QAbstractItemView.NoSelection)
        self.tabla.setStyleSheet("font-size:15px")
        v.addWidget(self.tabla, 1)

        g_an = QGroupBox("Análisis")
        ga = QVBoxLayout(g_an)
        self.lbl_eval = QLabel("—")
        self.lbl_eval.setWordWrap(True)
        self.lbl_linea = QLabel("")
        self.lbl_linea.setWordWrap(True)
        self.lbl_linea.setStyleSheet("color:#bca")
        ga.addWidget(self.lbl_eval)
        ga.addWidget(self.lbl_linea)
        v.addWidget(g_an)

        botones = QGridLayout()
        self.b_nueva = QPushButton("Nueva partida")
        self.b_deshacer = QPushButton("Deshacer")
        self.b_sug = QPushButton("Sugerencia")
        self.b_girar = QPushButton("Girar tablero")
        self.b_nueva.clicked.connect(self.nueva_partida)
        self.b_deshacer.clicked.connect(self.deshacer)
        self.b_sug.clicked.connect(self.sugerencia)
        self.b_girar.clicked.connect(self.tablero.girar)
        for i, b in enumerate((self.b_nueva, self.b_deshacer, self.b_sug, self.b_girar)):
            b.setMinimumHeight(36)
            botones.addWidget(b, i // 2, i % 2)
        v.addLayout(botones)

        sp = QSplitter()
        sp.addWidget(self.tablero)
        sp.addWidget(panel)
        sp.setStretchFactor(0, 3)
        sp.setStretchFactor(1, 1)
        sp.setSizes([1100, 400])
        self.setCentralWidget(sp)

    def _construir_menus(self):
        mb = self.menuBar()

        def accion(menu, texto, slot, atajo=None, checkable=False, checked=False):
            a = QAction(texto, self)
            if atajo:
                a.setShortcut(QKeySequence(atajo))
            a.setCheckable(checkable)
            if checkable:
                a.setChecked(checked)
                a.toggled.connect(slot)
            else:
                a.triggered.connect(slot)
            menu.addAction(a)
            return a

        m = mb.addMenu("&Partida")
        accion(m, "&Nueva partida…", self.nueva_partida, "Ctrl+N")
        m.addSeparator()
        accion(m, "&Abrir PGN…", self.abrir_pgn, "Ctrl+O")
        accion(m, "&Guardar PGN…", self.guardar_pgn, "Ctrl+S")
        m.addSeparator()
        accion(m, "Ofrecer &tablas", self.ofrecer_tablas)
        accion(m, "&Rendirse", self.rendirse)
        m.addSeparator()
        accion(m, "&Salir", self.close, "Ctrl+Q")

        m = mb.addMenu("&Jugada")
        accion(m, "&Deshacer", self.deshacer, "Ctrl+Z")
        accion(m, "&Sugerencia", self.sugerencia, "Ctrl+H")
        accion(m, "&Mover ahora (que juegue el rival)", self.mover_ahora, "Ctrl+M")

        m = mb.addMenu("&Ver")
        accion(m, "&Girar tablero", self.tablero.girar, "F")
        accion(m, "&Coordenadas", self._set_coords, None, True, self.tablero.coordenadas)
        accion(m, "&Pantalla completa", self._pantalla_completa, "F11")
        m.addSeparator()

        sub = m.addMenu("&Tablero")
        grp = QActionGroup(self)
        actual = self.cfg.value("tablero", "2DWDBRD.BMP")
        grupos = [[(a, n) for a, n, *_ in self.rec.tableros_2d()],
                  [(a, n) for a, n in self.rec.tableros_3d()],
                  [(k, v[0]) for k, v in COLORES_PLANOS.items()]]
        for i, opciones in enumerate(grupos):
            if i:
                sub.addSeparator()
            for clave, nombre in opciones:
                a = QAction(nombre, self, checkable=True)
                a.setChecked(clave == actual)
                a.triggered.connect(lambda _=False, c=clave: self._set_tablero(c))
                grp.addAction(a)
                sub.addAction(a)

        sub = m.addMenu("&Piezas")
        grp = QActionGroup(self)
        actual = self.cfg.value("piezas", "2DL")
        for cod, nombre in self.rec.juegos_piezas():
            a = QAction(f"{nombre}", self, checkable=True)
            a.setChecked(cod == actual)
            a.triggered.connect(lambda _=False, c=cod: self._set_piezas(c))
            grp.addAction(a)
            sub.addAction(a)

        sub = m.addMenu("&Escalado de gráficos")
        grp = QActionGroup(self)
        actual = self.cfg.value("filtro", "mejorado")
        for k, n in FILTROS.items():
            a = QAction(n, self, checkable=True)
            a.setChecked(k == actual)
            a.triggered.connect(lambda _=False, c=k: self._set_filtro(c))
            grp.addAction(a)
            sub.addAction(a)
        m.addSeparator()
        accion(m, "&Sonido", self._set_sonido, None, True, self.sonidos.activos)

        m = mb.addMenu("&Aprender")
        accion(m, "&Tutor de ajedrez…", self.abrir_tutor, "Ctrl+T")
        accion(m, "&Partidas clásicas comentadas…", self.abrir_clasicas, "Ctrl+L")

        m = mb.addMenu("&Opciones")
        accion(m, "Volver a preparar &gráficos y sonidos…", self._cambiar_recursos)
        accion(m, "Ruta de &Stockfish…", self._cambiar_stockfish)

        m = mb.addMenu("A&yuda")
        accion(m, "&Acerca de Jaque", self._acerca)

    def _aplicar_apariencia(self):
        self._set_filtro(self.cfg.value("filtro", "mejorado"), guardar=False)
        self._set_piezas(self.cfg.value("piezas", "2DL"), guardar=False)
        self._set_tablero(self.cfg.value("tablero", "2DWDBRD.BMP"), guardar=False)
        if self.tablero._piezas_pil:
            self.setWindowIcon(self.tablero.icono_pieza(chess.WHITE, chess.KNIGHT, 128))

    # ------------------------------------------------------------------ apariencia
    def _set_tablero(self, clave, guardar=True):
        if clave in COLORES_PLANOS:
            _, cl, osc = COLORES_PLANOS[clave]
            self.tablero.set_tablero_img(None)
            self.tablero.set_colores(cl, osc)
        elif clave in self.rec.ESQUINAS_3D:
            try:
                self.tablero.set_tablero_3d(self.rec.tablero_3d(clave))
            except Exception as e:
                self.statusBar().showMessage(f"No pude cargar el tablero 3D: {e}", 8000)
                self.tablero.set_tablero_img(None)
        else:
            try:
                self.tablero.set_tablero_img(self.rec.tablero_2d(clave))
            except Exception:
                self.tablero.set_tablero_img(None)
        if guardar:
            self.cfg.setValue("tablero", clave)

    def _set_piezas(self, cod, guardar=True):
        try:
            CACHE.mkdir(parents=True, exist_ok=True)
            piezas = self.rec.piezas(cod, CACHE)
        except Exception as e:
            self.statusBar().showMessage(f"No pude cargar el juego de piezas {cod}: {e}", 8000)
            return
        self.tablero.set_piezas(piezas, es_3d=cod.startswith("3D"))
        if guardar:
            self.cfg.setValue("piezas", cod)
        self._actualizar_capturas()

    def _set_filtro(self, k, guardar=True):
        self.tablero.set_filtro(k)
        if guardar:
            self.cfg.setValue("filtro", k)

    def _set_coords(self, on):
        self.tablero.coordenadas = on
        self.cfg.setValue("coordenadas", on)
        self.tablero.update()

    def _set_sonido(self, on):
        self.sonidos.activos = on
        self.cfg.setValue("sonido", on)

    def _pantalla_completa(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    # ------------------------------------------------------------------ partida
    def _rival_por_archivo(self, arch):
        for r in self.rivales:
            if r.archivo == arch:
                return r
        return self.rivales[-1] if self.rivales else None

    def _inicio(self):
        if not self.motor:
            QMessageBox.warning(self, "Falta Stockfish",
                                "No encontré el motor Stockfish.\n\nInstalalo con:\n"
                                "    sudo apt install stockfish\n\no indicá su ruta en "
                                "Opciones → Ruta de Stockfish.")
        self._empezar({"rival": self.rival, "color": "w", "tiempo": (0, 0)})

    def nueva_partida(self):
        previo = {"rival": self.rival.archivo if self.rival else None,
                  "color": self.cfg.value("color", "w"), "reloj": self.cfg.value("reloj", 0)}
        d = DialogoNuevaPartida(self.rivales, self.tablero, previo, self)
        if d.exec() != QDialog.Accepted:
            return
        r = d.resultado()
        self.cfg.setValue("rival", r["rival"].archivo)
        self.cfg.setValue("color", r["color_elegido"])
        self.cfg.setValue("reloj", r["reloj"])
        self._empezar(r)

    def _empezar(self, r):
        if self.motor:
            self.motor.cancelar()
        self.rival = r["rival"]
        self.humano = chess.WHITE if r["color"] == "w" else chess.BLACK
        base, inc = r["tiempo"]
        self.con_reloj = base > 0
        self.reloj = [float(base), float(base)]
        self.incremento = inc
        self.board = chess.Board()
        self.terminada = False
        self.pensando = False
        self.eval_rival = 0
        self.tablero.humanos = {self.humano}
        self.tablero.orientacion = self.humano
        self.tablero.set_posicion(self.board)
        self.tabla.setRowCount(0)
        self._actualizar_capturas()
        self.resultado = "*"
        self.lbl_eval.setText("—")
        self.lbl_linea.setText("")
        self._actualizar_panel()
        self._turno()

    def _turno(self):
        self._actualizar_panel()
        if self.terminada:
            return
        if self._fin_de_partida():
            return
        if self.board.turn != self.humano:
            self._pedir_motor()

    def _pedir_motor(self):
        if not self.motor or not self.rival:
            return
        self.pensando = True
        self.tablero.interactivo = False
        lim = 0
        if self.con_reloj:
            lim = max(0.1, self.reloj[self.board.turn] / 35 + self.incremento * 0.8)
        self.motor.pedir_jugada(self.board, self.rival, lim)
        self._actualizar_panel()

    def _hacer(self, mv: chess.Move, animar: bool):
        color = self.board.turn
        captura = self.board.is_capture(mv)
        enroque = self.board.is_castling(mv)
        self.board.push(mv)
        if self.con_reloj and len(self.board.move_stack) > 2:
            self.reloj[color] += self.incremento
        if self.board.is_checkmate():
            snd = "mate"
        elif self.board.is_check():
            snd = "jaque"
        elif mv.promotion:
            snd = "corona"
        elif enroque:
            snd = "enroque"
        elif captura:
            snd = "captura"
        else:
            snd = "mueve_blancas" if color == chess.WHITE else "mueve_negras"
        self.sonidos.tocar(snd)
        self.tablero.set_posicion(self.board, mv, animar=animar)
        self._agregar_a_tabla()
        self._actualizar_capturas()

    def _jugada_humano(self, mv):
        if self.terminada or self.pensando:
            return
        self._hacer(mv, animar=False)
        self._turno()

    def _jugada_motor(self, uci, info):
        self.pensando = False
        self.tablero.interactivo = True
        if self.terminada:
            return
        mv = chess.Move.from_uci(uci)
        if mv not in self.board.legal_moves:
            return
        sc = info.get("score")
        if sc is not None:
            self.eval_rival = sc.pov(self.board.turn).score(mate_score=100000)
            self.lbl_eval.setText(f"Evaluación del rival: {evaluacion_es(sc, True)}"
                                  + (f"  ·  prof. {info['depth']}" if info.get("depth") else ""))
            self.lbl_linea.setText("Piensa: " + linea_es(self.board, info.get("pv", [])))
        self._hacer(mv, animar=True)
        self._turno()

    def mover_ahora(self):
        if not self.terminada and not self.pensando and self.board.turn == self.humano:
            self.humano = not self.humano
            self.tablero.humanos = {self.humano}
            self._turno()

    def deshacer(self):
        if self.motor:
            self.motor.cancelar()
        self.pensando = False
        self.tablero.interactivo = True
        if not self.board.move_stack:
            return
        self.terminada = False
        self.board.pop()
        while self.board.move_stack and self.board.turn != self.humano:
            self.board.pop()
        ultima = self.board.move_stack[-1] if self.board.move_stack else None
        self.tablero.set_posicion(self.board, ultima)
        self._reconstruir_tabla()
        self._actualizar_capturas()
        self._turno()

    def sugerencia(self):
        if not self.motor or self.terminada or self.pensando or self.board.turn != self.humano:
            return
        self.lbl_estado.setText("Buscando una buena jugada…")
        self.motor.pedir_sugerencia(self.board, 1.5)

    def _sugerencia_lista(self, info):
        pv = info.get("pv") or []
        self._actualizar_panel()
        if not pv:
            return
        mv = pv[0]
        if mv not in self.board.legal_moves:
            return
        pieza = self.board.piece_at(mv.from_square)
        self.tablero.flecha = mv
        self.tablero.update()
        self.lbl_eval.setText(f"Sugerencia: <b>{san_es(self.board, mv)}</b> "
                              f"(mover {NOMBRE_PIEZA[pieza.piece_type]} de "
                              f"{chess.square_name(mv.from_square)} a "
                              f"{chess.square_name(mv.to_square)})<br>"
                              f"{evaluacion_es(info.get('score'), True)}")
        self.lbl_linea.setText("Línea: " + linea_es(self.board, pv))

    def ofrecer_tablas(self):
        if self.terminada or not self.rival:
            return
        r = self.rival
        acepta = False
        if r.desprecio_tablas < 1000 and len(self.board.move_stack) >= 20:
            umbral = -50 - r.desprecio_tablas * 0.5
            if r.desprecio_tablas <= -1000:
                umbral = 150
            acepta = self.eval_rival <= umbral
        if acepta:
            self._terminar("½-½", f"{r.nombre} acepta las tablas.")
        else:
            QMessageBox.information(self, "Tablas", f"{r.nombre} rechaza las tablas.")

    def rendirse(self):
        if self.terminada:
            return
        if QMessageBox.question(self, "Rendirse", "¿Seguro que querés abandonar la partida?") \
                == QMessageBox.Yes:
            res = "0-1" if self.humano == chess.WHITE else "1-0"
            self._terminar(res, "Abandonaste la partida.")

    def _fin_de_partida(self):
        b = self.board
        if b.is_checkmate():
            gana = not b.turn
            msg = "¡Jaque mate! " + ("Ganaste." if gana == self.humano
                                     else f"Ganó {self.rival.nombre}.")
            self._terminar("1-0" if gana else "0-1", msg)
        elif b.is_stalemate():
            self._terminar("½-½", "Rey ahogado: tablas.")
        elif b.is_insufficient_material():
            self._terminar("½-½", "Tablas por material insuficiente.")
        elif b.can_claim_threefold_repetition():
            self._terminar("½-½", "Tablas por triple repetición.")
        elif b.can_claim_fifty_moves():
            self._terminar("½-½", "Tablas por la regla de los 50 movimientos.")
        else:
            return False
        return True

    def _terminar(self, resultado, mensaje):
        self.terminada = True
        self.resultado = resultado
        if self.motor:
            self.motor.cancelar()
        self.pensando = False
        self.tablero.interactivo = False
        if resultado == "½-½":
            self.sonidos.tocar("tablas")
        self._actualizar_panel()
        self.lbl_estado.setText(mensaje)
        QTimer.singleShot(350, lambda: QMessageBox.information(self, "Fin de la partida",
                                                               f"{mensaje}\n\nResultado: {resultado}"))

    # ------------------------------------------------------------------ reloj
    def _tic(self):
        if not self.con_reloj or self.terminada or not self.board.move_stack:
            self._pintar_relojes()
            return
        c = self.board.turn
        self.reloj[c] -= 0.1
        if self.reloj[c] <= 0:
            self.reloj[c] = 0
            otro = not c
            if not self.board.has_insufficient_material(otro):
                res = "1-0" if otro == chess.WHITE else "0-1"
                quien = "Se te acabó el tiempo." if c == self.humano else \
                    f"A {self.rival.nombre} se le acabó el tiempo. ¡Ganaste!"
                self._terminar(res, quien)
            else:
                self._terminar("½-½", "Se acabó el tiempo, pero no hay material para dar mate: tablas.")
        self._pintar_relojes()

    def _pintar_relojes(self):
        for c, (caja, lbl) in self.lbl_reloj.items():
            lbl.setText(_fmt_reloj(self.reloj[c]) if self.con_reloj else "—")
            activo = (c == self.board.turn) and not self.terminada
            caja.setStyleSheet("#reloj{border-radius:6px; background:%s; border:2px solid %s}"
                               % (("#5a4026", "#e8c070") if activo else ("#2c2119", "#4a3a2a")))

    # ------------------------------------------------------------------ panel
    def _actualizar_panel(self):
        if self.rival:
            self.lbl_rival.setText(self.rival.nombre)
            self.lbl_desc.setText(self.rival.descripcion())
            self.bar_fuerza.setValue(self.rival.fuerza)
        if not self.terminada:
            if self.pensando:
                self.lbl_estado.setText(f"{self.rival.nombre} está pensando…")
            elif self.board.turn == self.humano:
                self.lbl_estado.setText("Te toca mover" + (" — ¡estás en jaque!"
                                                           if self.board.is_check() else ""))
            else:
                self.lbl_estado.setText("Turno del rival")
        nombre_b = "Vos" if self.humano == chess.WHITE else (self.rival.nombre if self.rival else "")
        nombre_n = "Vos" if self.humano == chess.BLACK else (self.rival.nombre if self.rival else "")
        self.setWindowTitle(f"Jaque — {nombre_b} contra {nombre_n}")
        self._pintar_relojes()

    def _agregar_a_tabla(self):
        n = len(self.board.move_stack)
        tmp = self.board.copy()
        mv = tmp.pop()
        texto = san_es(tmp, mv)
        fila = (n - 1) // 2
        if self.tabla.rowCount() <= fila:
            self.tabla.insertRow(fila)
            num = QTableWidgetItem(f"{fila + 1}.")
            num.setForeground(QColor(160, 140, 110))
            self.tabla.setItem(fila, 0, num)
        self.tabla.setItem(fila, 1 if n % 2 == 1 else 2, QTableWidgetItem(texto))
        self.tabla.scrollToBottom()

    def _reconstruir_tabla(self):
        self.tabla.setRowCount(0)
        movs = list(self.board.move_stack)
        b = self.board.root()
        for i, mv in enumerate(movs):
            fila = i // 2
            if self.tabla.rowCount() <= fila:
                self.tabla.insertRow(fila)
                self.tabla.setItem(fila, 0, QTableWidgetItem(f"{fila + 1}."))
            self.tabla.setItem(fila, 1 + i % 2, QTableWidgetItem(san_es(b, mv)))
            b.push(mv)

    def _actualizar_capturas(self):
        if not hasattr(self, "capt") or not self.tablero._piezas_pil:
            return
        inicial = {chess.PAWN: 8, chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 2, chess.QUEEN: 1}
        for color in (chess.WHITE, chess.BLACK):
            # piezas de 'color' que le comieron
            faltan = []
            for t, n in inicial.items():
                faltan += [t] * max(0, n - len(self.board.pieces(t, color)))
            faltan.sort(key=lambda t: -[1, 3, 3, 5, 9][t - 1] if t <= 5 else 0)
            alto = 48
            dpr = self.devicePixelRatioF()
            disp = max(200, self.capt[not color].width() - 8)
            grupos = []
            for t in faltan:
                if grupos and grupos[-1][0] == t:
                    grupos[-1][1].append(self.tablero.pixmap_pieza(color, t, alto))
                else:
                    grupos.append((t, [self.tablero.pixmap_pieza(color, t, alto)]))

            def medir(solape, hueco):
                x = 0.0
                for _, pms in grupos:
                    for k, pm in enumerate(pms):
                        x += pm.width() / dpr * (solape if k < len(pms) - 1 else 1.0)
                    x += hueco
                return x
            solape, hueco = 0.72, 10.0
            while medir(solape, hueco) > disp and solape > 0.3:
                solape -= 0.04
                hueco = max(3.0, hueco - 1)
            ancho = medir(solape, hueco) + 4
            lienzo = QPixmap(int(max(ancho, 10) * dpr), int(alto * dpr))
            lienzo.setDevicePixelRatio(dpr)
            lienzo.fill(Qt.transparent)
            from PySide6.QtGui import QPainter
            p = QPainter(lienzo)
            x = 0.0
            for _, pms in grupos:
                for k, pm in enumerate(pms):
                    p.drawPixmap(int(x), int(alto - pm.height() / dpr), pm)
                    x += pm.width() / dpr * (solape if k < len(pms) - 1 else 1.0)
                x += hueco
            p.end()
            # mostrar junto al bando que capturó
            self.capt[not color].setPixmap(lienzo)

    # ------------------------------------------------------------------ PGN
    def guardar_pgn(self):
        ruta, _ = QFileDialog.getSaveFileName(self, "Guardar partida",
                                              str(Path.home() / "partida.pgn"), "PGN (*.pgn)")
        if not ruta:
            return
        g = chess.pgn.Game.from_board(self.board)
        g.headers["Event"] = "Partida amistosa"
        g.headers["Site"] = "Jaque"
        g.headers["Date"] = datetime.date.today().strftime("%Y.%m.%d")
        nombre_r = self.rival.nombre if self.rival else "?"
        g.headers["White"] = "Jugador" if self.humano == chess.WHITE else nombre_r
        g.headers["Black"] = "Jugador" if self.humano == chess.BLACK else nombre_r
        g.headers["Result"] = getattr(self, "resultado", "*") if self.terminada else "*"
        Path(ruta).write_text(str(g) + "\n", encoding="utf-8")
        self.statusBar().showMessage(f"Partida guardada en {ruta}", 5000)

    def abrir_pgn(self):
        ruta, _ = QFileDialog.getOpenFileName(self, "Abrir partida", str(Path.home()),
                                              "PGN (*.pgn);;Todos (*)")
        if not ruta:
            return
        with open(ruta, encoding="utf-8", errors="replace") as f:
            g = chess.pgn.read_game(f)
        if g is None:
            QMessageBox.warning(self, "PGN", "No pude leer ninguna partida en ese archivo.")
            return
        b = g.board()
        for mv in g.mainline_moves():
            b.push(mv)
        self._cargar_posicion(b)
        self.statusBar().showMessage("Partida cargada: seguís jugando con el bando que mueve.", 6000)

    def _cargar_posicion(self, b: chess.Board):
        if self.motor:
            self.motor.cancelar()
        self.board = b
        self.terminada = False
        self.pensando = False
        self.con_reloj = False
        self.humano = b.turn
        self.tablero.humanos = {self.humano}
        self.tablero.orientacion = self.humano
        self.tablero.interactivo = True
        self.tablero.set_posicion(self.board, b.move_stack[-1] if b.move_stack else None)
        self._reconstruir_tabla()
        self._actualizar_capturas()
        self._turno()

    # ------------------------------------------------------------------ aprender
    def _estilizar(self, tb):
        tb.coordenadas = self.tablero.coordenadas
        tb.set_filtro(self.tablero.filtro)
        if self.tablero._piezas_pil:
            tb.set_piezas(self.tablero._piezas_pil, self.tablero._es_3d_set)
        if self.tablero._t3d is not None:
            tb.set_tablero_3d(self.tablero._t3d)
        else:
            tb.set_tablero_img(self.tablero._img_tablero)
            tb.set_colores(self.tablero.claro, self.tablero.oscuro)

    def abrir_tutor(self):
        from .ventanas import VentanaTutor
        if getattr(self, "_v_tutor", None) is None:
            self._v_tutor = VentanaTutor(self.rec, self._estilizar, self.sonidos)
        self._v_tutor.show()
        self._v_tutor.raise_()
        self._v_tutor.activateWindow()

    def abrir_clasicas(self):
        from .ventanas import VentanaClasicas
        if getattr(self, "_v_clas", None) is None:
            self._v_clas = VentanaClasicas(self.rec, self._estilizar, self.sonidos)
            self._v_clas.jugar_desde.connect(self._jugar_desde_clasica)
        self._v_clas.show()
        self._v_clas.raise_()
        self._v_clas.activateWindow()

    def _jugar_desde_clasica(self, b):
        self._cargar_posicion(b.copy())
        self.raise_()
        self.activateWindow()
        self.statusBar().showMessage(
            f"Posición cargada: jugás con las {'blancas' if b.turn else 'negras'} contra "
            f"{self.rival.nombre}.", 8000)

    # ------------------------------------------------------------------ opciones
    def _cambiar_recursos(self):
        d = DialogoRecursos(self)
        if d.exec() == QDialog.Accepted and d.ruta:
            try:
                _preparar_con_progreso(d.ruta, self)
            except Exception as e:
                QMessageBox.warning(self, "Recursos", str(e))
                return
            QMessageBox.information(self, "Recursos", "Listo. Reiniciá Jaque para usarlos.")

    def _cambiar_stockfish(self):
        r, _ = QFileDialog.getOpenFileName(self, "Ejecutable de Stockfish", "/usr/games")
        if r:
            self.cfg.setValue("stockfish", r)
            QMessageBox.information(self, "Stockfish", "Listo. Reiniciá Jaque para usar ese motor.")

    def _acerca(self):
        QMessageBox.about(self, "Acerca de Jaque",
                          f"<h3>Jaque {__version__}</h3>"
                          "<p>Ajedrez en español para Linux, de Ricardo.</p>"
                          "<p>Motor: <b>Stockfish</b>. Interfaz: Python y Qt.</p>"
                          "<p>Atajos: Ctrl+N nueva partida · Ctrl+T tutor · "
                          "Ctrl+L partidas clásicas · F11 pantalla completa.</p>")

    def closeEvent(self, ev):
        self.cfg.setValue("geometria", self.saveGeometry())
        for v in (getattr(self, "_v_tutor", None), getattr(self, "_v_clas", None)):
            if v:
                v.close()
        if self.motor:
            self.motor.apagar()
        super().closeEvent(ev)


# ----------------------------------------------------------------------------
def _tema_oscuro(app: QApplication):
    app.setStyle("Fusion")
    p = QPalette()
    p.setColor(QPalette.Window, QColor(38, 29, 22))
    p.setColor(QPalette.WindowText, QColor(236, 224, 205))
    p.setColor(QPalette.Base, QColor(28, 22, 17))
    p.setColor(QPalette.AlternateBase, QColor(46, 36, 28))
    p.setColor(QPalette.Text, QColor(236, 224, 205))
    p.setColor(QPalette.Button, QColor(70, 52, 38))
    p.setColor(QPalette.ButtonText, QColor(240, 228, 210))
    p.setColor(QPalette.Highlight, QColor(196, 146, 70))
    p.setColor(QPalette.HighlightedText, QColor(20, 14, 10))
    p.setColor(QPalette.ToolTipBase, QColor(60, 45, 33))
    p.setColor(QPalette.ToolTipText, QColor(240, 228, 210))
    p.setColor(QPalette.PlaceholderText, QColor(150, 135, 115))
    app.setPalette(p)
    app.setStyleSheet("QGroupBox{font-weight:bold; border:1px solid #5a4430; border-radius:6px;"
                      "margin-top:12px; padding-top:8px} QGroupBox::title{subcontrol-origin:margin;"
                      "left:10px; padding:0 4px; color:#e8c070}"
                      "QProgressBar{border:1px solid #5a4430; border-radius:4px; text-align:center}"
                      "QProgressBar::chunk{background:#b07a3a}")


def main(argv=None):
    argv = sys.argv if argv is None else argv
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(argv)
    app.setApplicationName("Jaque")
    app.setOrganizationName("Jaque")
    app.setDesktopFileName("jaque")
    icono = Path(__file__).resolve().parent / "datos" / "jaque.png"
    if icono.exists():
        from PySide6.QtGui import QIcon
        app.setWindowIcon(QIcon(str(icono)))
    tr = QTranslator(app)
    if tr.load("qtbase_es", QLibraryInfo.path(QLibraryInfo.TranslationsPath)):
        app.installTranslator(tr)
    _tema_oscuro(app)
    f = app.font()
    f.setPointSizeF(max(f.pointSizeF(), 10.5))
    app.setFont(f)

    cfg = QSettings()
    from .preparar import DESTINO
    ruta = None
    if "--recursos" in argv:
        ruta = argv[argv.index("--recursos") + 1]
    if ruta is None and DESTINO.exists():
        ruta = str(DESTINO)
    ruta = ruta or cfg.value("recursos", None)
    rec, msg = None, ""
    while rec is None:
        if ruta:
            try:
                rec = Recursos(ruta)
                break
            except Exception as e:
                msg = str(e)
        d = DialogoRecursos(None, msg)
        if d.exec() != QDialog.Accepted:
            return 0
        try:
            ruta = str(_preparar_con_progreso(d.ruta))
        except Exception as e:
            msg, ruta = str(e), None
    if not DESTINO.exists():
        # Fuente vieja (ISO guardado en la configuración): armar el paquete para la próxima.
        try:
            _preparar_con_progreso(ruta)
            rec = Recursos(DESTINO)
        except Exception:
            pass
    cfg.remove("recursos")

    splash = None
    if "--sin-portada" not in argv:
        portada, de_jaque = rec.portada()
        if portada is not None:
            scr = app.primaryScreen().availableGeometry()
            alto = int(scr.height() * 0.55)
            q = pil_a_qimage(portada).scaledToHeight(alto, Qt.SmoothTransformation)
            if de_jaque:
                from PySide6.QtGui import QPainter
                pq = QPainter(q)
                pq.setRenderHint(QPainter.TextAntialiasing)
                fv = QFont("DejaVu Serif")
                fv.setPixelSize(max(12, round(q.height() * 0.036)))
                fv.setLetterSpacing(QFont.PercentageSpacing, 140)
                pq.setFont(fv)
                pq.setPen(QColor(226, 200, 160))
                y = round(q.height() * 0.80)
                pq.drawText(0, y, q.width(), round(q.height() * 0.08),
                            Qt.AlignHCenter | Qt.AlignTop, f"versión {__version__}")
                pq.end()
            splash = QSplashScreen(QPixmap.fromImage(q))
            splash.showMessage("cargando…  ", Qt.AlignBottom | Qt.AlignRight, QColor(236, 224, 205))
            splash.show()
            app.processEvents()

    w = VentanaPrincipal(rec, cfg)
    if splash:
        w.sonidos.tocar("titulo")
        QTimer.singleShot(1800, lambda: (splash.finish(w), w.show()))
    else:
        w.show()
    return app.exec()
