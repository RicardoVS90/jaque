import sys, random
sys.path.insert(0, '/home/claude/jaque')
from PySide6.QtCore import QTimer, QSettings, QPoint
from PySide6.QtWidgets import QApplication, QDialog, QToolButton, QMenu
import chess
import jaque.app as A
from jaque.tablero import Tablero
OUT = '/tmp/claude-0/-home-claude/068c496e-6bfc-5f96-8373-e70a177dcd81/scratchpad/manual/img'
s = QSettings("Jaque", "Jaque")
s.setValue("piezas", "2DL"); s.setValue("tablero", "2DWDBRD.BMP"); s.setValue("coordenadas", True)
for k in ("apertura", "evaluar", "rival", "amenazas"): s.setValue(f"comentarios/{k}", True)
s.sync()
A.VentanaPrincipal._inicio = lambda self: None
A.QMessageBox.information = staticmethod(lambda *a, **k: 0)
random.seed(6)

def diag(w, nombre, sans, flecha=None, fen=None, girar=False, lado=520):
    tb = Tablero()
    w._estilizar(tb)
    tb.coordenadas = True
    b = chess.Board(fen) if fen else chess.Board()
    ult = None
    for x in sans:
        ult = b.push_san(x)
    tb.resize(lado, lado)
    if girar:
        tb.orientacion = chess.BLACK
    tb.set_posicion(b, ult)
    if flecha:
        tb.flecha = chess.Move.from_uci(flecha)
    tb.show(); QApplication.processEvents()
    tb.grab().save(f"{OUT}/d_{nombre}.png"); tb.close()
    print("diag", nombre, b.fen())

def fin():
    w = [x for x in QApplication.topLevelWidgets() if isinstance(x, A.VentanaPrincipal)][0]
    w.resize(1600, 1000); w.show(); QApplication.processEvents()
    # ---- diagramas
    diag(w, "inicial", [])
    diag(w, "d5", "e4 d6 Bc4 a6 Qf3 e6 d4 g6 d5".split(), "e6d5")
    diag(w, "dh5", "e4 a5 Qh5".split(), "g8f6")
    diag(w, "cxe5", "e4 e5 Nf3 Nc6 Bc4 Nd4 Nxe5".split(), "d8g5")
    diag(w, "colgada", "e4 c5 Bc4 d5".split(), "d5c4")
    diag(w, "mate_amenaza", "e4 e5 Nf3 Bc5 Nxe5 Qh4".split(), "h4f2")
    diag(w, "pastor", "e4 e5 Bc4 Nc6 Qh5 Nf6 Qxf7#".split())
    diag(w, "horquilla", [], "c7e8", fen="r3k2r/ppN2ppp/8/8/8/8/PPP2PPP/R3K2R b KQkq - 0 1")
    diag(w, "clavada", [], None, fen="4k3/8/8/4r3/8/8/4R3/4K2B w - - 0 1")
    diag(w, "enroque", [], "e1g1", fen="r3k2r/pppq1ppp/2npbn2/2b1p3/2B1P3/2NPBN2/PPPQ1PPP/R3K2R w KQkq - 0 1")
    diag(w, "alpaso", "e4 a6 e5 d5".split(), "e5d6")
    diag(w, "coronacion_d", [], "b7b8", fen="4k3/1P6/8/8/8/8/6p1/4K3 w - - 0 1")
    # ---- diálogo nueva partida
    d = A.DialogoNuevaPartida(w.rivales, w.tablero, {"rival": "TALSTYLE.CMX", "color": "w", "reloj": 0}, w)
    i = next(i for i, r in enumerate(w.rivales) if r.nombre == "Estilo Tal")
    d.cb_rival.setCurrentIndex(i); d.show(); QApplication.processEvents()
    d.grab().save(f"{OUT}/s_nueva.png"); d.close()
    # ---- menú Ver
    for titulo, nombre in (("&Ver", "s_menu_ver"), ("&Jugada", "s_menu_jugada"), ("&Partida", "s_menu_partida")):
        m = next(a.menu() for a in w.menuBar().actions() if a.text() == titulo)
        m.popup(QPoint(100, 100)); QApplication.processEvents()
        m.grab().save(f"{OUT}/{nombre}.png")
        if titulo == "&Ver":
            sub = next(a.menu() for a in m.actions() if a.menu() and "mentarios" in a.text())
            sub.popup(QPoint(400, 100)); QApplication.processEvents(); sub.grab().save(f"{OUT}/s_menu_comentarios.png"); sub.close()
        m.close()
    # ---- partida con comentarios
    r = next(x for x in w.rivales if x.nombre == "Estilo Tal")
    w._empezar({"rival": r, "color": "w", "tiempo": (600, 0)})
    plan = ["e4", "Nf3", "d4", "Nxd4", "Nc3", "Qh5"]
    def esperar(f):
        def g():
            if w.pensando or (w.board.turn != w.humano and not w.terminada) or w.com._pendientes:
                QTimer.singleShot(150, g); return
            QTimer.singleShot(400, f)
        QTimer.singleShot(150, g)
    def jugar(i=0):
        if i == len(plan) or w.terminada:
            esperar(final); return
        try: mv = w.board.parse_san(plan[i])
        except ValueError: mv = random.choice(list(w.board.legal_moves))
        w._jugada_humano(mv)
        esperar(lambda: jugar(i + 1))
    def final():
        w.grab().save(f"{OUT}/s_principal.png")
        w.grab(w.centralWidget().widget(1).geometry()).save(f"{OUT}/s_panel.png")
        print(w.txt_com.toPlainText())
        # 3D
        t3 = w.rec.tableros_3d()[0][0]
        w._set_tablero(t3); w._set_piezas("3DN"); QApplication.processEvents()
        w.grab().save(f"{OUT}/s_3d.png")
        w._set_tablero("2DWDBRD.BMP"); w._set_piezas("2DL")
        # coronación
        b = chess.Board('r3k2r/1P3ppp/8/8/8/8/5PPP/R3K2R w KQkq - 0 25')
        w._cargar_posicion(b); QApplication.processEvents()
        def mirar():
            for dd in QApplication.topLevelWidgets():
                if isinstance(dd, QDialog) and dd.isVisible():
                    dd.grab().save(f'{OUT}/s_coronacion.png'); dd.findChildren(QToolButton)[0].click()
        QTimer.singleShot(500, mirar)
        w.tablero._elegir_coronacion(chess.B8)
        # tutor y clásicas
        w.abrir_tutor(); v = w._v_tutor; v.resize(1500, 950); QApplication.processEvents()
        QTimer.singleShot(1500, lambda: tutor(w))
    jugar()

def tutor(w):
    v = w._v_tutor
    hecho = False
    for (i, j) in ((1, 5), (1, 7), (1, 3)):
        v._abrir(i, j)
        for k in range(len(v.cap.paginas)):
            v._ir(k)
            e = v.estado
            if e.desafio and len(e.board.piece_map()) >= 6 and len(e.textos) >= 1:
                hecho = True; break
        if hecho: break
    print("tutor", v.lbl_cap.text(), v.lbl_pag.text())
    QApplication.processEvents()
    w._v_tutor.grab().save(f"{OUT}/s_tutor.png"); w._v_tutor.close()
    w.abrir_clasicas(); w._v_clas.resize(1500, 950); QApplication.processEvents()
    QTimer.singleShot(1500, lambda: clas(w))

def clas(w):
    try: w._v_clas._ir(24)
    except Exception as e: print("clas", e)
    QApplication.processEvents()
    w._v_clas.grab().save(f"{OUT}/s_clasicas.png"); w._v_clas.close()
    w.close(); QApplication.quit()

_init = A.VentanaPrincipal.__init__
def init(self, *a):
    _init(self, *a); QTimer.singleShot(1500, fin)
A.VentanaPrincipal.__init__ = init
sys.exit(A.main(['jaque']))
