"""Genera el Manual de usuario de Jaque en PDF (reportlab)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, "/home/claude/jaque")
import chess  # noqa: E402
import chess.engine  # noqa: E402,F401
from reportlab.lib import colors  # noqa: E402
from reportlab.lib.enums import TA_CENTER, TA_LEFT  # noqa: E402
from reportlab.lib.pagesizes import A4  # noqa: E402
from reportlab.lib.styles import ParagraphStyle  # noqa: E402
from reportlab.lib.units import cm  # noqa: E402
from reportlab.pdfbase import pdfmetrics  # noqa: E402
from reportlab.pdfbase.ttfonts import TTFont  # noqa: E402
from reportlab.platypus import (BaseDocTemplate, CondPageBreak, Frame, Image, KeepTogether,  # noqa: E402
                                NextPageTemplate, PageBreak, PageTemplate, Paragraph, Spacer,
                                Table, TableStyle)
from reportlab.platypus.tableofcontents import TableOfContents  # noqa: E402

from jaque import __version__  # noqa: E402
from jaque.assets import Recursos  # noqa: E402
from jaque.rivales import config_motor  # noqa: E402
from jaque.rutas import recursos  # noqa: E402

BASE = Path(__file__).resolve().parent
IMG = BASE / "img"
SALIDA = BASE / f"Jaque-{__version__}-manual-de-usuario.pdf"

# ------------------------------------------------------------------ fuentes y estilos
F = "/usr/share/fonts/truetype/dejavu/"
pdfmetrics.registerFont(TTFont("Sans", F + "DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("Sans-B", F + "DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Sans-I", F + "DejaVuSans-Oblique.ttf"))
pdfmetrics.registerFont(TTFont("Sans-BI", F + "DejaVuSans-BoldOblique.ttf"))
pdfmetrics.registerFont(TTFont("Serif-B", F + "DejaVuSerif-Bold.ttf"))
pdfmetrics.registerFont(TTFont("Mono", F + "DejaVuSansMono.ttf"))
pdfmetrics.registerFontFamily("Sans", normal="Sans", bold="Sans-B", italic="Sans-I", boldItalic="Sans-BI")

MARRON = colors.HexColor("#6b3f1a")
DORADO = colors.HexColor("#b07a3a")
OSCURO = colors.HexColor("#3a2a1e")
CLARO = colors.HexColor("#f7f0e4")
GRIS = colors.HexColor("#5a5048")
C_BUENA, C_IMP, C_ERR, C_GRAVE = "#2e7d32", "#a07800", "#d0661a", "#c62828"

st = {
    "body": ParagraphStyle("body", fontName="Sans", fontSize=10, leading=14.5, spaceAfter=6,
                           textColor=colors.HexColor("#222222")),
    "h1": ParagraphStyle("h1", fontName="Serif-B", fontSize=21, leading=26, textColor=MARRON,
                         spaceBefore=4, spaceAfter=12),
    "h2": ParagraphStyle("h2", fontName="Serif-B", fontSize=14.5, leading=19, textColor=MARRON,
                         spaceBefore=12, spaceAfter=6),
    "h3": ParagraphStyle("h3", fontName="Sans-B", fontSize=11, leading=15, textColor=OSCURO,
                         spaceBefore=8, spaceAfter=4),
    "bullet": ParagraphStyle("bullet", fontName="Sans", fontSize=10, leading=14, leftIndent=14,
                             bulletIndent=3, spaceAfter=3),
    "cap": ParagraphStyle("cap", fontName="Sans-I", fontSize=8.6, leading=11.5, textColor=GRIS,
                          alignment=TA_CENTER, spaceBefore=3, spaceAfter=8),
    "cell": ParagraphStyle("cell", fontName="Sans", fontSize=8.8, leading=11.5),
    "cellb": ParagraphStyle("cellb", fontName="Sans-B", fontSize=8.8, leading=11.5),
    "head": ParagraphStyle("head", fontName="Sans-B", fontSize=8.8, leading=11.5, textColor=colors.white),
    "nota": ParagraphStyle("nota", fontName="Sans", fontSize=9.5, leading=13.5),
    "toc1": ParagraphStyle("toc1", fontName="Sans-B", fontSize=10.5, leading=17, leftIndent=0),
    "toc2": ParagraphStyle("toc2", fontName="Sans", fontSize=9.5, leading=14, leftIndent=16),
}

story = []


def P(t, s="body"):
    story.append(Paragraph(t, st[s]))


def H1(t):
    if story and not isinstance(story[-1], PageBreak):
        story.append(PageBreak())
    p = Paragraph(t, st["h1"])
    p._toc = (0, t)
    story.append(p)


def H2(t):
    story.append(CondPageBreak(4 * cm))
    p = Paragraph(t, st["h2"])
    p._toc = (1, t)
    story.append(p)


def H3(t):
    story.append(CondPageBreak(3 * cm))
    P(t, "h3")


def B(items):
    for t in items:
        story.append(Paragraph(t, st["bullet"], bulletText="•"))
    story.append(Spacer(1, 4))


def celda(x, s="cell"):
    return x if not isinstance(x, str) else Paragraph(x, st[s])


def T(filas, anchos, cabecera=True, zebra=True, fuente=None):
    datos = []
    for i, f in enumerate(filas):
        datos.append([celda(c, "head" if (cabecera and i == 0) else "cell") for c in f])
    t = Table(datos, colWidths=[a * cm for a in anchos], repeatRows=1 if cabecera else 0)
    estilo = [("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9ccb8")),
              ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
              ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if cabecera:
        estilo += [("BACKGROUND", (0, 0), (-1, 0), OSCURO)]
    if zebra:
        for i in range(1 if cabecera else 0, len(datos)):
            if i % 2 == 0:
                estilo.append(("BACKGROUND", (0, i), (-1, i), CLARO))
    t.setStyle(TableStyle(estilo))
    story.append(t)
    story.append(Spacer(1, 8))


def NOTA(t, titulo="Para tener en cuenta"):
    cont = [Paragraph(f"<b>{titulo}</b>", st["nota"]), Paragraph(t, st["nota"])]
    tb = Table([[cont]], colWidths=[16.4 * cm])
    tb.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fbf3e3")),
                            ("LINEBEFORE", (0, 0), (0, -1), 3, DORADO),
                            ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(tb)
    story.append(Spacer(1, 9))


def IMG_(nombre, ancho_cm, pie=None):
    ruta = IMG / nombre
    from PIL import Image as PI
    w, h = PI.open(ruta).size
    im = Image(str(ruta), width=ancho_cm * cm, height=ancho_cm * cm * h / w)
    partes = [im]
    if pie:
        partes.append(Paragraph(pie, st["cap"]))
    story.append(KeepTogether(partes))


def DIAG(pares, lado=7.6):
    """Diagramas de tablero lado a lado: [(archivo, pie), ...]."""
    celdas = []
    for nombre, pie in pares:
        im = Image(str(IMG / f"d_{nombre}.png"), width=lado * cm, height=lado * cm)
        celdas.append([im, Paragraph(pie, st["cap"])])
    t = Table([celdas], colWidths=[(16.4 / len(pares)) * cm] * len(pares))
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(KeepTogether([t]))
    story.append(Spacer(1, 4))


def M(sim, color):
    return f'<font name="Sans-B" color="{color}">{sim}</font>'


BUENA = M("!", C_BUENA)
IMP = M("?!", C_IMP)
ERR = M("?", C_ERR)
GRAVE = M("??", C_GRAVE)

# ------------------------------------------------------------------ datos reales del programa
rec = Recursos(recursos())
RIVALES = sorted(rec.rivales(), key=lambda r: (r.fuerza, r.nombre))
POR_NOMBRE = {r.nombre: r for r in RIVALES}


def chances(cp):
    return 2 / (1 + math.exp(-0.00368208 * cp)) - 1


def porc(cp):
    return (chances(cp) + 1) / 2 * 100


def cp_para_porc(p):
    lo, hi = -3000, 3000
    for _ in range(60):
        mid = (lo + hi) / 2
        if porc(mid) < p:
            lo = mid
        else:
            hi = mid
    return mid


# ================================================================== CONTENIDO
# ------------------------------------------------------------------ portada
story.append(Spacer(1, 1.2 * cm))
story.append(Image(str(Path("/home/claude/jaque/jaque/datos/portada.png")), width=17 * cm, height=10.625 * cm))
story.append(Spacer(1, 1.2 * cm))
story.append(Paragraph("Manual de usuario", ParagraphStyle("t", fontName="Serif-B", fontSize=30, leading=36,
                                                          alignment=TA_CENTER, textColor=MARRON)))
story.append(Spacer(1, 0.3 * cm))
story.append(Paragraph(f"Versión {__version__}", ParagraphStyle("v", fontName="Sans", fontSize=14, leading=18,
                                                              alignment=TA_CENTER, textColor=GRIS)))
story.append(Spacer(1, 1.6 * cm))
story.append(Paragraph("Cómo se juega, qué significa cada comentario y cada símbolo, cómo se escriben "
                       "las jugadas, cómo funcionan las dificultades y quién es cada uno de los 40 rivales.",
                       ParagraphStyle("s", fontName="Sans-I", fontSize=11, leading=16, alignment=TA_CENTER,
                                      textColor=GRIS, leftIndent=1.5 * cm, rightIndent=1.5 * cm)))
story.append(NextPageTemplate("normal"))
story.append(PageBreak())

# ------------------------------------------------------------------ índice
story.append(Paragraph("Índice", st["h1"]))
toc = TableOfContents()
toc.levelStyles = [st["toc1"], st["toc2"]]
toc.dotsMinLevel = 0
story.append(toc)
story.append(PageBreak())

# ------------------------------------------------------------------ 1. bienvenida
H1("1. Bienvenida")
P("<b>Jaque</b> es un programa de ajedrez en español para Linux y Windows. Usa <b>Stockfish</b>, uno de los "
  "motores de ajedrez más fuertes del mundo, y encima de él aplica la personalidad de cada rival: unos atacan "
  "sin pensar en el material, otros se defienden como una muralla, otros buscan las tablas y otros apenas "
  "saben mover las piezas.")
P("Además de jugar, Jaque te ayuda a aprender: comenta tus jugadas mientras jugás, te avisa de las "
  "amenazas, te dice qué apertura estás jugando, trae un tutor con lecciones y desafíos y una colección de "
  "502 partidas clásicas comentadas.")
H2("Qué vas a encontrar en este manual")
B(["<b>Capítulos 2 a 4:</b> instalar, conocer la ventana y jugar una partida.",
   "<b>Capítulos 5 y 6:</b> las reglas del ajedrez resumidas y cómo se escriben las jugadas (la notación).",
   "<b>Capítulos 7 y 8:</b> los símbolos (!, ?!, ?, ??), los números de evaluación y la teoría detrás de "
   "cada comentario en vivo, con ejemplos en el tablero.",
   "<b>Capítulos 9 a 11:</b> el panel de análisis, cómo funcionan las dificultades y la ficha de cada uno "
   "de los 40 rivales.",
   "<b>Capítulos 12 a 17:</b> el tutor, las partidas clásicas, la apariencia, los menús y atajos, los archivos, "
   "la solución de problemas y un glosario."])
NOTA("En todo el manual las jugadas se escriben como las muestra Jaque, con las letras de las piezas en "
     "español: <b>R</b> rey, <b>D</b> dama, <b>T</b> torre, <b>A</b> alfil, <b>C</b> caballo. "
     "El capítulo 6 lo explica en detalle.", "Antes de empezar")

# ------------------------------------------------------------------ 2. instalación
H1("2. Instalación")
H2("En Linux (Debian, Ubuntu y similares)")
P("Jaque se instala con un único archivo, <font name='Mono'>Jaque-" + __version__ + "-instalador.run</font>, "
  "que trae todo adentro: el programa con su propio Python y bibliotecas, el motor Stockfish, los "
  "gráficos, los sonidos, las lecciones y las partidas. No necesita internet ni permisos de administrador.")
B(["Abrí una terminal en la carpeta donde está el archivo (por ejemplo <font name='Mono'>cd ~/Descargas</font>).",
   "Ejecutá <font name='Mono'>bash Jaque-" + __version__ + "-instalador.run</font>.",
   "Esperá alrededor de un minuto. Al final tiene que decir <b>«Todo en orden»</b>.",
   "Jaque queda en el menú de aplicaciones (sección Juegos), con un ícono en el escritorio y con el "
   "comando <font name='Mono'>jaque</font> en la terminal."])
P("Para actualizar a una versión nueva, instalala encima de la anterior: tus opciones se conservan. "
  "Si después de instalar no ves Jaque en el menú, cerrá sesión y volvé a entrar.")
H3("Desinstalar en Linux")
B(["Clic derecho sobre Jaque en el menú → <b>«Desinstalar Jaque»</b>, o",
   "en la terminal: <font name='Mono'>jaque --desinstalar</font>, o",
   "con el instalador: <font name='Mono'>bash Jaque-" + __version__ + "-instalador.run --desinstalar</font>."])
P("La opción «Desinstalar o administrar complementos» que agrega KDE en todos los programas no sirve para "
  "Jaque, porque Jaque no se instala como paquete del sistema. Tus opciones quedan en "
  "<font name='Mono'>~/.config/Jaque</font> por si reinstalás.")
H2("En Windows 11")
P("En Windows el instalador se arma una sola vez con el kit <font name='Mono'>jaque-windows-" + __version__ +
  ".zip</font>:")
B(["Descomprimí el kit en una ruta corta, por ejemplo <font name='Mono'>C:\\Jaque-fuente</font>.",
   "Hacé doble clic en <b>construir.bat</b>. Si falta Python o Inno Setup, los instala solo (aceptá el "
   "permiso que pida). La primera vez tarda entre 10 y 15 minutos.",
   "Al terminar se abre la carpeta <b>salida</b> con <b>Jaque-" + __version__ + "-instalador-windows.exe</b>.",
   "Ejecutá ese instalador. Si Windows muestra «Windows protegió su PC», tocá <b>Más información → "
   "Ejecutar de todas formas</b> (aparece porque el instalador no está firmado digitalmente)."])
P("Para desinstalar en Windows: <b>Configuración → Aplicaciones → Jaque</b>, o el acceso «Desinstalar Jaque» "
  "del menú Inicio.")
H2("Verificar que todo funciona")
P("El comando <font name='Mono'>jaque --verificar</font> (en Windows, el acceso «Verificar instalación de Jaque» "
  "del menú Inicio) revisa la interfaz, el sonido, las bibliotecas, los gráficos, los rivales, las lecciones, "
  "las traducciones y el motor, y deja el informe en <font name='Mono'>verificacion.txt</font>.")

# ------------------------------------------------------------------ 3. ventana principal
H1("3. La ventana principal")
IMG_("s_principal.png", 16.4, "La ventana principal durante una partida contra «Estilo Tal».")
P("La ventana tiene el tablero a la izquierda y el panel de información a la derecha. Podés cambiar el ancho "
  "de cada parte arrastrando la línea que las separa.")
T([["Zona", "Qué muestra"],
   ["<b>Rival</b>", "Nombre del rival, una descripción de su personalidad y su fuerza (0 a 100)."],
   ["<b>Relojes</b>", "El tiempo de cada bando. El reloj del bando que mueve se resalta en dorado. "
    "Si jugás sin reloj aparece una raya."],
   ["<b>Estado</b>", "A quién le toca mover, si estás en jaque, si el rival está pensando y el resultado "
    "al final de la partida."],
   ["<b>Apertura</b>", "Código y nombre de la apertura que se está jugando (por ejemplo «C45 · Apertura "
    "escocesa»)."],
   ["<b>Piezas capturadas</b>", "Las piezas que comió cada bando, agrupadas por tipo."],
   ["<b>Lista de jugadas</b>", "Todas las jugadas en notación española. Tus jugadas evaluadas llevan su "
    "símbolo en color (?!, ?, ??)."],
   ["<b>Comentarios</b>", "Los comentarios en vivo: aperturas, evaluación de tus jugadas, frases del rival "
    "y avisos de amenazas (capítulo 8)."],
   ["<b>Análisis</b>", "Cómo ve el rival la posición y qué jugadas piensa (capítulo 9)."],
   ["<b>Botones</b>", "Deshacer, Rehacer, Nueva partida, Sugerencia y Girar tablero."]],
  [3.4, 13.0])

IMG_("s_panel.png", 6.2, "El panel derecho en detalle.")

# ------------------------------------------------------------------ 4. jugar
H1("4. Cómo jugar una partida")
H2("Empezar una partida nueva")
P("Menú <b>Partida → Nueva partida</b> (Ctrl+N) o el botón <b>Nueva partida</b>. En la ventana que aparece "
  "elegís:")
IMG_("s_nueva.png", 10.5, "La ventana de partida nueva.")
B(["<b>Rival:</b> los 40 rivales, ordenados por fuerza. Debajo aparece la descripción de su estilo.",
   "<b>Jugás con:</b> blancas, negras o al azar. Las blancas mueven primero.",
   "<b>Control de tiempo:</b> sin reloj, o uno de los controles de la tabla siguiente."])
T([["Control", "Tiempo para cada jugador", "Incremento por jugada"],
   ["Sin reloj", "Ilimitado", "—"],
   ["Blitz 5 min", "5 minutos", "—"],
   ["Blitz 3 + 2", "3 minutos", "+2 segundos"],
   ["Rápida 10 min", "10 minutos", "—"],
   ["Rápida 15 + 10", "15 minutos", "+10 segundos"],
   ["Clásica 30 min", "30 minutos", "—"]], [4.5, 6, 5.9])
P("El <b>incremento</b> es tiempo que se suma a tu reloj cada vez que hacés una jugada. Si a un jugador se le "
  "acaba el tiempo, pierde, salvo que al rival no le quede material suficiente para dar mate: en ese caso "
  "es tablas. Con reloj, el rival también administra su tiempo y piensa menos cuando le queda poco.")
H2("Mover las piezas")
B(["<b>Arrastrar:</b> tomá la pieza con el mouse y soltala en la casilla de destino.",
   "<b>Dos clics:</b> clic en la pieza (se marcan las casillas a las que puede ir) y clic en el destino.",
   "Solo se aceptan jugadas legales. La última jugada queda resaltada en amarillo y el rey en jaque se "
   "marca en rojo."])
H3("Coronación")
P("Cuando un peón llega a la última fila aparece una ventana para elegir en qué se convierte. Casi siempre "
  "conviene la dama, pero a veces un caballo da jaque o evita un ahogado.")
IMG_("s_coronacion.png", 10, "La ventana de coronación.")
H2("Deshacer, rehacer y otras acciones")
T([["Acción", "Dónde", "Qué hace"],
   ["<b>Deshacer</b>", "Botón ◀ Deshacer, menú Jugada, Ctrl+Z",
    "Quita tu última jugada y la respuesta del rival. Sin límite: podés volver al principio."],
   ["<b>Rehacer</b>", "Botón Rehacer ▶, menú Jugada, Ctrl+Y o Ctrl+Shift+Z",
    "Vuelve a poner las jugadas deshechas, con sus marcas, comentarios y análisis. El rival no vuelve a "
    "pensar: repite la jugada que había hecho. Si jugás algo distinto, lo deshecho se descarta."],
   ["<b>Sugerencia</b>", "Botón, menú Jugada, Ctrl+H",
    "Stockfish busca la mejor jugada durante un segundo y medio y la muestra con una flecha verde y "
    "una explicación en el recuadro Análisis."],
   ["<b>Mover ahora</b>", "Menú Jugada, Ctrl+M",
    "El rival juega por vos: cambiás de bando y él sigue con el que tenías."],
   ["<b>Girar tablero</b>", "Botón, menú Ver, tecla F", "Ve el tablero desde el otro lado."],
   ["<b>Ofrecer tablas</b>", "Menú Partida", "El rival acepta o rechaza según su personalidad (abajo)."],
   ["<b>Rendirse</b>", "Menú Partida", "Abandonás la partida (pide confirmación)."]],
  [2.8, 4.6, 9.0])
H3("Cuándo acepta tablas el rival")
P("Ningún rival acepta tablas antes de la jugada 10. Después, cada uno decide según su <b>actitud ante las "
  "tablas</b> y según cómo ve la posición:")
B(["Los que <b>nunca aceptan tablas</b> (Kamikaze) las rechazan siempre.",
   "Los que <b>buscan las tablas</b> (Maestro de tablas, Cazadamas) las aceptan mientras no vayan ganando "
   "por más de un peón y medio.",
   "El resto las acepta solo si va perdiendo: como mínimo por medio peón, y por más cuanto más le gusta "
   "jugar a ganar. Por ejemplo, Estilo Kasparov solo acepta si va perdiendo por casi dos peones."])
H2("Fin de la partida")
P("La partida termina por <b>jaque mate</b>, <b>ahogado</b>, <b>material insuficiente</b>, <b>triple "
  "repetición</b>, <b>regla de los 50 movimientos</b>, falta de tiempo, tablas acordadas o abandono. "
  "Jaque detecta todos los casos solo y muestra el resultado. Después podés deshacer jugadas para "
  "revisar la partida o empezar otra.")
H2("Guardar y abrir partidas (PGN)")
P("<b>Partida → Guardar PGN</b> (Ctrl+S) guarda la partida en formato PGN, el estándar que entienden todos los "
  "programas y sitios de ajedrez (Lichess, Chess.com, ChessBase…). El archivo incluye los jugadores, la "
  "fecha, el resultado, la apertura con su código ECO y los símbolos ?!, ?, ?? de tus jugadas.")
P("<b>Partida → Abrir PGN</b> (Ctrl+O) carga una partida y te deja seguir jugándola desde la última "
  "posición, con el bando al que le toca mover.")
NOTA("Dentro del archivo PGN las jugadas se guardan con las letras inglesas (K, Q, R, B, N), porque así lo "
     "exige el formato. Jaque las vuelve a mostrar en español al abrirlas.")

# ------------------------------------------------------------------ 5. reglas
H1("5. Las reglas del ajedrez en resumen")
P("Este capítulo es un repaso rápido. El tutor (capítulo 12) explica cada regla con diagramas y desafíos.")
H2("Cómo se mueve cada pieza")
T([["Pieza", "Letra", "Valor", "Movimiento"],
   ["Rey", "R", "—", "Una casilla en cualquier dirección. Nunca puede quedar atacado."],
   ["Dama", "D", "9", "Cualquier cantidad de casillas en línea recta o en diagonal."],
   ["Torre", "T", "5", "Cualquier cantidad de casillas en línea recta (filas y columnas)."],
   ["Alfil", "A", "3", "Cualquier cantidad de casillas en diagonal. Siempre queda en casillas del mismo color."],
   ["Caballo", "C", "3", "En forma de L: dos casillas en una dirección y una al costado. Es la única pieza "
    "que salta por encima de otras."],
   ["Peón", "(sin letra)", "1", "Avanza una casilla (dos desde su casilla inicial) y captura en diagonal "
    "hacia adelante. Nunca retrocede."]],
  [2.2, 2.0, 1.6, 10.6])
P("Los <b>valores</b> son una guía para saber si un cambio conviene: entregar un alfil (3) por una torre (5) "
  "es ganar material; entregar una dama (9) por una torre (5) es perderlo. Jaque usa estos mismos valores "
  "para decidir si una pieza tuya está en peligro.")
H2("Jugadas especiales")
DIAG([("enroque", "<b>Enroque corto</b> (O-O): el rey va dos casillas hacia la torre y la torre salta al "
                  "otro lado. Se arrastra el rey dos casillas."),
      ("alpaso", "<b>Captura al paso:</b> el peón negro avanzó dos casillas (d7-d5) y quedó al lado del peón "
                 "blanco de e5, que puede comerlo como si hubiera avanzado una: exd6.")])
B(["<b>Enroque:</b> solo si el rey y esa torre no se movieron nunca, no hay piezas entre ellos, el rey no "
   "está en jaque y no pasa ni cae en una casilla atacada. Corto (O-O) hacia la torre de h, largo (O-O-O) "
   "hacia la de a.",
   "<b>Captura al paso:</b> solo en la jugada inmediata siguiente al avance doble.",
   "<b>Coronación:</b> el peón que llega a la última fila se convierte en dama, torre, alfil o caballo."])
DIAG([("coronacion_d", "<b>Coronación:</b> el peón de b7 llega a b8 y se convierte en otra pieza. "
                       "En notación: b8=D."),
      ("pastor", "<b>Jaque mate:</b> el mate del pastor. La dama en f7, protegida por el alfil, ataca al "
                 "rey negro, que no tiene escapatoria.")])
H2("Jaque, mate y tablas")
B(["<b>Jaque:</b> el rey está atacado. Hay que salir del jaque moviendo el rey, tapando o comiendo la "
   "pieza que da jaque.",
   "<b>Jaque mate:</b> jaque del que no se puede salir. Gana el que da mate.",
   "<b>Ahogado:</b> el que mueve no está en jaque pero no tiene ninguna jugada legal. Es tablas.",
   "<b>Material insuficiente:</b> ninguno de los dos puede dar mate (por ejemplo, rey contra rey, o rey y "
   "alfil contra rey). Tablas.",
   "<b>Triple repetición:</b> la misma posición se repite tres veces. Tablas.",
   "<b>Regla de los 50 movimientos:</b> 50 jugadas de cada bando sin capturas ni movimientos de peón. Tablas."])

# ------------------------------------------------------------------ 6. notación
H1("6. La notación: cómo se escriben las jugadas")
P("Jaque usa la <b>notación algebraica</b>, la oficial de la FIDE, con las letras de las piezas en español. "
  "Es la misma que vas a ver en la lista de jugadas, en los comentarios, en el análisis, en el tutor y en las "
  "partidas clásicas.")
H2("Las casillas")
DIAG([("inicial", "La posición inicial. Las <b>columnas</b> van de la <b>a</b> a la <b>h</b> (de izquierda a "
                  "derecha, vistas desde las blancas) y las <b>filas</b> del <b>1</b> al <b>8</b>.")], lado=8.5)
P("Cada casilla se nombra con su columna y su fila: el rey blanco empieza en <b>e1</b>, la dama negra en "
  "<b>d8</b>, y la casilla del centro donde suele ir el peón de rey es <b>e4</b>. Con el menú <b>Ver → "
  "Coordenadas</b> se muestran u ocultan las letras y números alrededor del tablero.")
H2("Cómo se escribe una jugada")
P("Una jugada se escribe con la <b>letra de la pieza</b> y la <b>casilla de destino</b>. Los peones no "
  "llevan letra.")
T([["Ejemplo", "Significa"],
   ["<b>e4</b>", "Un peón va a e4."],
   ["<b>Cf3</b>", "Un caballo va a f3."],
   ["<b>Axc6</b>", "Un alfil come (la <b>x</b> indica captura) la pieza de c6."],
   ["<b>exd5</b>", "El peón de la columna e come en d5 (en las capturas de peón se indica su columna)."],
   ["<b>Dh5+</b>", "La dama va a h5 y da <b>jaque</b> (signo +)."],
   ["<b>Dxf7#</b>", "La dama come en f7 y da <b>jaque mate</b> (signo #)."],
   ["<b>O-O</b>", "Enroque corto (del lado del rey)."],
   ["<b>O-O-O</b>", "Enroque largo (del lado de la dama)."],
   ["<b>b8=D</b>", "Un peón llega a b8 y corona dama."],
   ["<b>Cbd2</b>", "Si dos caballos pueden ir a d2, se agrega la columna de origen: el de la columna b."],
   ["<b>T1e2</b>", "Si las dos torres están en la misma columna, se agrega la fila de origen: la de la fila 1."]],
  [3.2, 13.2])
H2("Los números de jugada")
P("Una <b>jugada completa</b> es una de las blancas y una de las negras. Por eso se numeran de a pares:")
P("<b>1. e4 e5  2. Cf3 Cc6  3. Ac4</b>")
P("significa: primera jugada, blancas e4 y negras e5; segunda, blancas Cf3 y negras Cc6; tercera, blancas "
  "Ac4. Cuando una línea empieza con una jugada de las negras se escriben tres puntos: <b>3... Cf6</b> "
  "(«en la tercera, las negras juegan Cf6»). Así aparecen las líneas que piensa el rival en el recuadro "
  "Análisis.")
H2("Notación española e inglesa")
T([["Pieza", "Español (Jaque)", "Inglés (PGN, sitios web)"],
   ["Rey", "R", "K (King)"], ["Dama", "D", "Q (Queen)"], ["Torre", "T", "R (Rook)"],
   ["Alfil", "A", "B (Bishop)"], ["Caballo", "C", "N (Knight)"], ["Peón", "sin letra", "sin letra"]],
  [4, 6, 6.4])
NOTA("Ojo con la <b>R</b>: en español es el <b>rey</b> y en inglés la <b>torre</b> (rook). Si copiás una "
     "partida de un sitio en inglés, «Rf1» es una torre; en Jaque, «Rf1» es el rey.")

# ------------------------------------------------------------------ 7. símbolos y evaluación
H1("7. Símbolos y números de evaluación")
H2("Los símbolos de las jugadas")
P("Mientras jugás, Jaque evalúa cada jugada tuya y, si corresponde, le pone uno de estos símbolos. "
  "Son los símbolos de comentario que se usan en todo el mundo, en libros, revistas y programas de ajedrez.")
T([["Símbolo", "Nombre", "Significado", "Color en Jaque"],
   [BUENA, "Buena jugada", "Encontraste algo bueno: aprovechaste un error del rival o diste con un mate.",
    "Verde"],
   [IMP, "Imprecisión", "Había algo mejor. Tu posición empeoró un poco, pero no es grave.", "Amarillo"],
   [ERR, "Error", "Tu posición empeoró bastante: perdiste material o una buena parte de tu ventaja.",
    "Naranja"],
   [GRAVE, "Error grave", "Una jugada que cambia la partida: regalás una pieza importante, permitís un "
    "mate o dejás escapar una victoria.", "Rojo"]],
  [2.0, 2.8, 8.6, 3.0])
P("Los símbolos aparecen en la lista de jugadas (por ejemplo <b>Dh5" + ERR + "</b>) y al principio de cada "
  "comentario de evaluación, y se guardan en el archivo PGN. En los libros también vas a ver <b>!!</b> "
  "(jugada brillante) y <b>!?</b> (jugada interesante); Jaque no los usa.")
H2("La evaluación en números")
P("Stockfish mide la ventaja en <b>peones</b>. Una evaluación de <b>+1.00</b> significa que las blancas están "
  "como si tuvieran un peón de más; <b>−2.50</b>, que las negras tienen una ventaja equivalente a dos peones y "
  "medio. Internamente se cuenta en <b>centipeones</b> (centésimas de peón): +1.00 son 100 centipeones.")
B(["El signo indica quién está mejor: <b>+</b> las blancas, <b>−</b> las negras. En el recuadro Análisis la "
   "evaluación siempre se muestra desde el lado de las blancas.",
   "La ventaja no es solo material: también cuentan la seguridad del rey, la actividad de las piezas, los "
   "peones pasados y la estructura de peones.",
   "<b>«Mate en 3 para negras»</b>: el motor encontró un mate forzado en esa cantidad de jugadas.",
   "<b>«prof. 18»</b>: la profundidad de cálculo, cuántas jugadas hacia adelante (de cada bando) miró el motor."])
T([["Evaluación", "Cómo la describe Jaque"],
   ["Entre −0.30 y +0.30", "Posición igualada"],
   ["Entre 0.30 y 1.00", "Ligera ventaja (blanca o negra)"],
   ["Entre 1.00 y 2.50", "Clara ventaja"],
   ["Más de 2.50", "Ventaja decisiva"]], [6, 10.4])
H2("Cómo decide Jaque el símbolo de tu jugada")
P("Para cada jugada tuya, un segundo Stockfish (que corre aparte y no afecta al rival) analiza dos "
  "posiciones: la de <b>antes</b> de tu jugada, suponiendo que jugás lo mejor, y la de <b>después</b> de la "
  "jugada que hiciste. La diferencia entre las dos es lo que perdiste con tu jugada.")
P("Esa diferencia no se mide en peones sino en <b>probabilidad de ganar</b>, con la misma fórmula que usa "
  "Lichess. La razón: perder un peón cuando la partida está pareja es muy importante, pero perder un peón "
  "cuando ya tenés una dama de más casi no cambia nada.")
filas = [["Evaluación", "Probabilidad de ganar"]]
for cp in (0, 50, 100, 200, 300, 500, 800, 1200):
    filas.append([f"+{cp / 100:.2f}" if cp else "0.00", f"{porc(cp):.0f} %"])
T(filas, [6, 10.4])
p5, p10, p15 = (abs(cp_para_porc(50 - x)) / 100 for x in (5, 10, 15))
T([["Probabilidad que perdés con tu jugada", "Símbolo", "Ejemplo partiendo de una posición igualada"],
   ["5 puntos o más", IMP, f"Pasás de 0.00 a −{p5:.2f} aproximadamente"],
   ["10 puntos o más", ERR, f"Pasás de 0.00 a −{p10:.2f} aproximadamente"],
   ["15 puntos o más", GRAVE, f"Pasás de 0.00 a −{p15:.2f} aproximadamente"]], [5.6, 2.0, 8.8])
P("Hay tres reglas más:")
B(["<b>Permitir un mate</b> siempre es " + GRAVE + ", aunque la partida ya estuviera perdida.",
   "<b>Perder tres peones de material o más</b> (por ejemplo, regalar una pieza) es como mínimo " + ERR +
   ", aunque la probabilidad de ganar casi no cambie porque la partida ya estaba decidida.",
   "Las <b>jugadas de libro</b> (las que figuran en la base de aperturas) no se marcan como imprecisión: "
   "son jugadas aceptadas por la teoría aunque el motor prefiera otra."])
NOTA("Cuando la partida ya está decidida, para bien o para mal, Jaque marca menos imprecisiones: una jugada "
     "floja casi no cambia el resultado. Es a propósito, y es lo mismo que hacen Lichess y otros programas.")

# ------------------------------------------------------------------ 8. comentarios en vivo
H1("8. Los comentarios en vivo y su teoría")
P("El recuadro <b>Comentarios</b> va mostrando cuatro tipos de mensajes, cada uno con su ícono y su color. "
  "Cada comentario lleva adelante el número de jugada al que corresponde.")
T([["Ícono", "Tipo", "Cuándo aparece"],
   ["Libro abierto", "Apertura", "Cuando la partida entra en una apertura o variante conocida."],
   ["✔ / ?! / ✖ / ✖✖", "Evaluación de tu jugada", "Cuando tu jugada fue buena, imprecisa, un error o un "
    "error grave."],
   ["Globo de diálogo", "Frase del rival", "Cuando el rival tiene algo para decir según su personalidad."],
   ["Triángulo de aviso", "Aviso de amenaza", "Cuando te toca mover y tenés una pieza en peligro o el rival amenaza mate."]],
  [3.6, 3.8, 9.0])
P("Con el menú <b>Ver → Comentarios en vivo</b> podés apagar o prender cada tipo por separado. El cambio se "
  "aplica en el momento, en la misma partida, y Jaque lo recuerda para la próxima vez. Si apagás los "
  "cuatro, el recuadro desaparece.")
IMG_("s_menu_comentarios.png", 5.5, "Menú Ver → Comentarios en vivo.")
P("Los comentarios siguen a <b>Deshacer</b> y <b>Rehacer</b>: al deshacer desaparecen los de las jugadas "
  "quitadas, y al rehacer vuelven exactamente los mismos.")

H2("8.1 Las aperturas")
P("La <b>apertura</b> es la fase inicial de la partida, más o menos las primeras diez a quince jugadas, en "
  "la que los dos bandos sacan sus piezas, pelean por el centro y ponen el rey a salvo. Las aperturas más "
  "jugadas tienen nombre propio, muchas veces el del jugador que las popularizó o el de la ciudad donde se "
  "analizaron.")
P("Jaque reconoce 3.608 posiciones de apertura y muestra el nombre en español debajo del estado, por ejemplo "
  "<b>«B20 · Defensa siciliana: ataque Bowdler»</b>:")
B(["<b>B20</b> es el código <b>ECO</b> (<i>Encyclopaedia of Chess Openings</i>), la clasificación "
   "internacional que divide todas las aperturas en 500 códigos, de A00 a E99.",
   "<b>Defensa siciliana</b> es la apertura (la familia).",
   "<b>ataque Bowdler</b> es la variante dentro de esa familia (en este caso 2.Ac4 contra la siciliana)."])
P("Cuando la partida sale de las jugadas conocidas, queda el último nombre válido, porque esa sigue siendo la "
  "apertura que se jugó. Cada vez que se entra en una familia o una variante nueva, aparece además un "
  "comentario con el ícono del libro.")
T([["Letra ECO", "Qué abarca", "Ejemplos"],
   ["<b>A</b>", "Aperturas de flanco y jugadas iniciales poco comunes", "Apertura inglesa (1.c4), Réti "
    "(1.Cf3), defensa holandesa (1.d4 f5), apertura Bird"],
   ["<b>B</b>", "1.e4 con respuestas distintas de 1...e5 y 1...e6", "Defensa siciliana, Caro-Kann, Pirc, "
    "Alekhine, escandinava"],
   ["<b>C</b>", "1.e4 e5 y la defensa francesa (1.e4 e6)", "Apertura italiana, española (Ruy López), "
    "escocesa, gambito de rey, defensa francesa, Petrov"],
   ["<b>D</b>", "1.d4 d5 y la defensa Grünfeld", "Gambito de dama, defensa eslava y semieslava, "
    "sistema Londres, defensa Grünfeld"],
   ["<b>E</b>", "Defensas indias (1.d4 Cf6 sin 2...d5)", "Defensa nimzoindia, india de dama, india de "
    "rey, apertura catalana"]],
  [2.0, 6.0, 8.4])
H3("Los principios de la apertura")
P("Muchos comentarios de evaluación en las primeras jugadas tienen que ver con estos principios clásicos:")
B(["<b>Controlá el centro</b> (las casillas d4, e4, d5 y e5) con peones y piezas.",
   "<b>Desarrollá las piezas menores</b> (caballos y alfiles) antes que la dama y las torres.",
   "<b>Enrocá temprano</b> para poner el rey a salvo y conectar las torres.",
   "<b>No saques la dama demasiado pronto:</b> el rival la persigue sacando piezas con ganancia de tiempo.",
   "<b>No muevas la misma pieza dos veces</b> sin necesidad mientras el resto sigue sin salir."])
DIAG([("dh5", "Después de 1.e4 a5 2.Dh5 Jaque comenta «<b>Dh5" + ERR + "</b> Error. El rival podría responder "
              "Cf6, atacando tu dama. Era mejor d4»: la dama salió temprano y Cf6 la ataca mientras las negras "
              "desarrollan una pieza.")], lado=8)

H2("8.2 La evaluación de tus jugadas")
P("Cuando una jugada tuya merece un símbolo, el comentario dice tres cosas: el <b>símbolo</b> y su "
  "nombre, <b>por qué</b> (qué podría hacer el rival ahora) y <b>qué era mejor</b>. Por ejemplo:")
P("<i>✖ Dh5? Error. Recién llegado podría responder Cf6, atacando tu dama. Era mejor d4.</i>")
NOTA("El comentario se genera apenas hacés tu jugada, antes de que el rival responda. Por eso está en "
     "condicional («podría responder»): describe la mejor respuesta del rival, lo que te puede castigar. "
     "Los rivales débiles muchas veces no la ven y juegan otra cosa. La jugada que «era mejor» es la "
     "elección del motor: a veces no es lo que haría una persona, pero sirve de referencia.",
     "Es una advertencia, no algo que ya pasó")
P("Estas son las explicaciones posibles y la idea de ajedrez que hay detrás de cada una:")
H3("«Tu caballo en g5 no tiene defensa: el rival podría comerlo con Dxg5»")
P("Es una <b>pieza colgada</b>: está atacada y ninguna pieza tuya la protege, así que el rival la come gratis. "
  "Es el error más común en todos los niveles. Antes de cada jugada conviene preguntarse: <i>¿qué piezas "
  "mías quedan atacadas? ¿Están defendidas?</i>")
DIAG([("colgada", "1.e4 c5 2.Ac4 d5: el peón de d5 ataca al alfil de c4, que no tiene defensa. Jaque "
                  "avisa «Tu alfil en c4 está atacado y sin defensa»."),
      ("cxe5", "1.e4 e5 2.Cf3 Cc6 3.Ac4 Cd4 4.Cxe5" + GRAVE + " La dama negra va a g5 y ataca a la vez el "
               "caballo de e5 y el peón de g2.")])
H3("«El rival podría comer tu torre en e5 con… usando una pieza de menos valor»")
P("La pieza está defendida, pero la atacan con una pieza que vale menos. Aunque puedas recapturar, perdés en "
  "el cambio: si un caballo (3) come tu torre (5) y vos comés el caballo, perdiste 2 puntos de material. Por "
  "eso una torre atacada por un peón o por un alfil está en peligro aunque esté protegida.")
H3("«El rival podría cambiar en d5 con exd5 y mejorar un poco su posición»")
P("Es un <b>cambio</b>: el rival come, vos recapturás y el material queda parejo. El problema no es la pieza, "
  "sino que después del cambio la posición le queda mejor al rival: abre líneas para sus piezas, gana tiempo "
  "o te deja peones débiles.")
DIAG([("d5", "1.e4 d6 2.Ac4 a6 3.Df3 e6 4.d4 g6 5.d5" + IMP + " El peón de d5 está defendido por el peón de e4 y "
             "el alfil de c4. Después de 5...exd5 6.Axd5 Cf6 las negras sacan piezas atacando al alfil.")],
     lado=8)
H3("«El rival podría responder Cf6, atacando tu dama» / «atacando dos piezas a la vez»")
P("La respuesta del rival <b>ataca</b> una pieza tuya y te obliga a moverla, con lo que perdés tiempo. Si "
  "ataca <b>dos piezas a la vez</b> es un <b>ataque doble</b> y normalmente perdés una de las dos. Cuando lo "
  "hace un caballo se llama <b>horquilla</b>, porque el caballo «pincha» en dos direcciones.")
DIAG([("horquilla", "Horquilla: el caballo blanco de c7 da jaque al rey de e8 y ataca a la vez la torre de a8. "
                    "Las negras tienen que mover el rey y pierden la torre."),
      ("clavada", "Clavada: la torre negra de e5 ataca a la torre blanca de e2, que no puede moverse de esa "
                  "columna porque dejaría a su rey en jaque.")])
H3("«El rival podría responder Ah3+, con jaque»")
P("Tu jugada permite un jaque fuerte: el rival gana tiempo o empieza un ataque contra tu rey.")
H3("«Ahora el rival tendría mate en 2, empezando con…»")
P("Tu jugada permite un <b>mate forzado</b>: haga lo que hagas, el rival da mate en esa cantidad de jugadas si "
  "juega bien. Siempre se marca " + GRAVE + ".")
H3("«Tenías mate con Dxf7#» / «Tenías mate en 3 empezando con…»")
P("Tenías un mate forzado y jugaste otra cosa. Se marca " + ERR + ". Vale la pena revisar con <b>Deshacer</b> "
  "cuál era la secuencia.")
H3("Los comentarios positivos")
B(["<b>«¡Bien visto! Aprovechaste el error de…»</b> (" + BUENA + "): el rival se equivocó en su jugada anterior y "
   "vos encontraste la forma de castigarlo.",
   "<b>«¡Encontraste un mate en 3!»</b> (" + BUENA + "): tu jugada lleva a un mate forzado.",
   "<b>«Buena jugada, es la que elegiría el motor»</b>: jugaste exactamente lo mismo que Stockfish. No sale "
   "en todas las jugadas, para no llenar el recuadro."])
P("La jugada que da mate no recibe comentario: el resultado ya aparece en el estado de la partida.")

H2("8.3 Las frases del rival")
P("Cada rival habla según su personalidad. Jaque agrupa a los 40 rivales en seis estilos, según los mismos "
  "parámetros que usan para jugar (capítulo 11):")
T([["Estilo", "Quiénes", "Cómo habla"],
   ["<b>Novato</b>", "Fuerza menor que 35 (Recién llegado, Novato)", "Inseguro, sorprendido y con humor: "
    "«¿Me comí la dama? ¡¿Me comí la dama?!»"],
   ["<b>Agresivo</b>", "Ataque de +20 o más (Estilo Tal, Kamikaze, Marshall…)", "Fanfarrón y desafiante: "
    "«¡Jaque! Tu rey no va a tener descanso.»"],
   ["<b>Defensivo</b>", "Ataque de −20 o menos (Defensor, Petrosian, Karpov…)", "Paciente y cauto: "
    "«Primero, el rey bien guardado.»"],
   ["<b>Posicional</b>", "Posicional de +60 o más, sin ser agresivo ni defensivo (Posicional)",
    "Habla de planes y estructura: «Todo marcha según el plan.»"],
   ["<b>Materialista</b>", "Posicional de −30 o menos, o codicioso con los peones (Empujamaderas, "
    "Comepeones)", "Cuenta el material: «Una más para mi colección.»"],
   ["<b>Neutral</b>", "El resto", "Sobrio: «Jaque.», «Me gusta mi posición.»"]],
  [2.6, 6.0, 7.8])
P("El rival habla en estas situaciones:")
T([["Situación", "Cuándo"],
   ["Inicio", "Con su primera jugada."],
   ["Sacrificio", "Pone una pieza (caballo o más) donde la podés comer con ganancia de al menos dos "
    "puntos. Si el rival es fuerte, suele ser un sacrificio con idea; si es débil, puede ser un descuido."],
   ["Captura de tu dama", "Siempre que te come la dama."],
   ["Captura importante", "Cuando te come un caballo, alfil o torre."],
   ["Jaque", "Cuando te da jaque."],
   ["Enroque", "Cuando enroca."],
   ["Coronación", "Cuando corona un peón."],
   ["Ventaja o desventaja", "La primera vez que cree ir ganando o perdiendo por dos peones y medio o más."],
   ["Mate visto", "Cuando encuentra un mate forzado."],
   ["Busca tablas", "Los rivales que buscan las tablas, después de la jugada 15, si la posición está pareja."]],
  [4.2, 12.2])
P("Para no hablar en todas las jugadas, las situaciones menos importantes (jaques, enroques, capturas) solo "
  "se comentan a veces; los rivales agresivos y los novatos hablan más que el resto.")

H2("8.4 Los avisos de amenazas")
P("Cuando te toca mover, Jaque revisa la posición y avisa con el ícono del triángulo de aviso:")
B(["<b>«Tu alfil en c4 está atacado y sin defensa»</b>: una pieza tuya (caballo, alfil, torre o dama) está "
   "atacada y nadie la protege.",
   "<b>«Tu alfil en g5 está atacado por un peón»</b>: está defendida, pero la ataca algo de menos valor, así "
   "que perderías material en el cambio.",
   "<b>«¡Cuidado! El rival amenaza mate con Dxf2#»</b>: si no hacés nada, el rival da mate en la jugada "
   "siguiente."])
DIAG([("mate_amenaza", "Después de 1.e4 e5 2.Cf3 Ac5 3.Cxe5 Dh4 la dama y el alfil negros apuntan a f2. "
                       "Jaque avisa: «¡Cuidado! El rival amenaza mate con Dxf2#».")], lado=8)
P("Cada amenaza se avisa una sola vez, cuando aparece; no se repite en cada jugada mientras siga ahí. "
  "Los avisos son por caballos, alfiles, torres y dama (no por peones), y no cuentan como atacante a una "
  "pieza del rival que está clavada.")

# ------------------------------------------------------------------ 9. análisis
H1("9. El panel de análisis y las sugerencias")
P("El recuadro <b>Análisis</b> muestra lo que piensa el rival cada vez que juega:")
B(["<b>Evaluación del rival:</b> cómo ve la posición, desde el lado de las blancas (+ ventaja blanca, − "
   "ventaja negra), con la profundidad de cálculo.",
   "<b>Piensa:</b> la línea principal que calculó, es decir, las jugadas que espera para los dos bandos."])
P("Cuando pedís una <b>Sugerencia</b> (Ctrl+H), el recuadro muestra la jugada recomendada, qué pieza mover y "
  "adónde, la evaluación y la línea completa, y el tablero la marca con una flecha verde. El análisis también "
  "sigue a Deshacer y Rehacer: siempre muestra lo que correspondía a esa altura de la partida.")
NOTA("La evaluación del rival es la de Stockfish, pero el rival no siempre juega la jugada que más le "
     "conviene: elige entre las mejores según su personalidad (capítulo 10). Por eso a veces juega distinto de "
     "lo que muestra «Piensa».")

# ------------------------------------------------------------------ 10. dificultades
H1("10. Cómo funcionan las dificultades")
P("Cada rival tiene una <b>fuerza</b> de 0 a 100. A partir de ella Jaque decide tres cosas: qué tan bien juega "
  "Stockfish para ese rival, cuánto se aparta de la mejor jugada y con qué frecuencia comete errores al azar.")
H2("Los cuatro mecanismos")
B(["<b>Nivel de Stockfish</b> (de 0 a 20): con niveles bajos el motor comete errores deliberados. Fuerza 100 "
   "equivale al nivel 20 (el máximo).",
   "<b>Tiempo para pensar:</b> de 0,15 segundos por jugada para los más débiles a 2 segundos para los más "
   "fuertes. Con reloj, además, se ajusta al tiempo que le queda.",
   "<b>Margen de elección:</b> Stockfish propone varias jugadas candidatas y el rival puede elegir cualquiera "
   "que no sea peor que la mejor en más de cierto margen. Los débiles tienen mucho margen y se equivocan más; "
   "dentro del margen elige según sus gustos (atacar, comer, jugar posicional).",
   "<b>Azar:</b> los rivales débiles, de vez en cuando, juegan una jugada legal cualquiera, como un "
   "principiante que no vio nada."])
H2("La escala de los rivales graduados")
P("Ocho rivales forman una escala de dificultad, sin estilo especial:")
filas = [["Rival", "Fuerza", "Nivel Stockfish", "Tiempo por jugada", "Margen", "Jugada al azar"]]
for n in ("Recién llegado", "Novato", "Fácil", "Empujamaderas", "Ligero", "Moderado", "Difícil", "Experto"):
    r = POR_NOMBRE[n]
    c = config_motor(r)
    marg = 20 + (100 - r.fuerza) * 2.5
    az = r.azar / 250 * 100
    filas.append([f"<b>{n}</b>", str(r.fuerza), f"{c['skill']} de 20", f"{c['tiempo']:.2f} s".replace(".", ","),
                  f"{marg / 100:.2f} peones".replace(".", ","),
                  (f"{az:.1f} % de las jugadas".replace(".", ",") if az else "nunca")])
T(filas, [3.4, 1.5, 2.4, 2.5, 2.6, 4.0])
T([["Rival", "Para quién"],
   ["Recién llegado, Novato", "Para aprender a mover las piezas. Cometen errores groseros con frecuencia."],
   ["Fácil, Empujamaderas", "Para quien ya conoce las reglas y empieza a ver tácticas simples."],
   ["Ligero, Moderado", "Jugadores de club que ya no cuelgan piezas. Moderado todavía regala algo de vez en cuando."],
   ["Difícil, Experto", "Jugadores fuertes. Experto ya juega prácticamente sin errores."],
   ["Fuerza 100", "El nivel máximo de Stockfish: más fuerte que cualquier humano."]], [4.4, 12.0])
NOTA("La escala de Jaque todavía no está calibrada en puntos ELO. Como referencia práctica: en partidas de "
     "prueba, el programa original de 1995 en su nivel máximo, con 10 segundos por jugada, rindió más o menos "
     "como <b>Difícil</b>. 32 de los 40 rivales tienen fuerza 100: entre ellos no cambia la fuerza sino el "
     "estilo.", "Sobre el ELO")
H2("¿Cuál es el más difícil de vencer?")
P("Todos los rivales de fuerza 100 calculan igual de bien, así que la diferencia está en el estilo. "
  "<b>El Maestro</b>, <b>Experto</b> y <b>Fuerza bruta</b> son los más «puros»: juegan lo que dice el motor sin "
  "gustos que los desvíen. <b>Maestro de tablas</b> y <b>Estilo Andersson</b> son muy difíciles de ganar porque "
  "se defienden y buscan las tablas, aunque también arriesgan poco. Los agresivos como <b>Kamikaze</b> o "
  "<b>Estilo Tal</b> a veces se pasan de rosca, y eso abre alguna oportunidad.")

# ------------------------------------------------------------------ 11. personalidades
H1("11. Los 40 rivales y sus personalidades")
H2("Qué mide cada parámetro")
T([["Parámetro", "Escala", "Qué hace en el juego"],
   ["<b>Fuerza</b>", "0 a 100", "Qué tan bien juega (capítulo 10)."],
   ["<b>Ataque</b>", "−100 (defensivo) a +100 (agresivo)", "Los agresivos prefieren, entre las jugadas buenas, "
    "las que dan jaque o comen; los defensivos, las tranquilas."],
   ["<b>Posicional</b>", "Negativo (materialista) a +100 (posicional)", "Los posicionales prefieren las "
    "jugadas de maniobra, sin capturas ni jaques."],
   ["<b>Tablas</b>", "Negativo (las busca) a positivo (las evita)", "Decide si evita o busca repetir la "
    "posición, y si acepta tus ofertas de tablas."],
   ["<b>Azar</b>", "0 a 100", "Cuánto varía y con qué frecuencia comete errores al azar."],
   ["<b>Valor de las piezas</b>", "Dama 9, torre 5, alfil y caballo 3, peón 1 (valores normales)",
    "Algunos rivales valoran más ciertas piezas del rival y van detrás de ellas."],
   ["<b>Libro</b>", "Sí o no", "Con libro, varía sus primeras jugadas entre alternativas parejas."]],
  [3.0, 4.6, 8.8])
H2("La tabla completa")


def signo(x):
    return f"+{x}" if x > 0 else str(x)


def tablas_txt(x):
    if x >= 1000:
        return "nunca"
    if x <= -1000:
        return "las busca"
    return signo(x)


filas = [["Rival", "Fuerza", "Ataque", "Posic.", "Tablas", "Descripción en Jaque"]]
for r in RIVALES:
    filas.append([f"<b>{r.nombre}</b>", str(r.fuerza), signo(r.ataque), signo(r.posicional),
                  tablas_txt(r.desprecio_tablas), r.descripcion()])
T(filas, [3.3, 1.55, 1.8, 1.45, 1.75, 6.55])
H2("Los rivales graduados")
P("<b>Recién llegado, Novato, Fácil, Ligero, Moderado, Difícil y Experto</b> no tienen estilo: solo cambia la "
  "fuerza. <b>Empujamaderas</b> (fuerza 50) es además <b>materialista</b>: prefiere comer material antes que "
  "jugar por la posición. Son los mejores rivales para medir tu progreso.")
H2("Los especialistas")
T([["Rival", "Qué lo hace especial"],
   ["<b>El Maestro</b>", "El rival principal: fuerza máxima, sin gustos especiales. Juega lo que dice el motor."],
   ["<b>Fuerza bruta</b>", "Fuerza máxima y ningún rasgo especial en los parámetros que usa Jaque."],
   ["<b>Rebelde</b>", "Fuerza máxima, sin rasgos especiales en los parámetros que usa Jaque."],
   ["<b>Comepeones</b>", "Valora los peones rivales el triple de lo normal: si puede comer un peón, casi "
    "siempre lo hace. Se lo puede tentar con gambitos."],
   ["<b>Maestro de peones</b>", "Valora más los peones (1,5 en vez de 1), propios y ajenos: cuida su "
    "estructura y no los regala."],
   ["<b>Cazadamas</b>", "Valora tu dama casi el doble que la suya (7,5 contra 4,5): cambiar damas le encanta. "
    "Según sus datos, además, es muy defensivo y busca las tablas."],
   ["<b>Defensor</b>", "Totalmente defensivo: entre las jugadas buenas elige siempre las más seguras."],
   ["<b>Kamikaze</b>", "Totalmente agresivo y <b>nunca acepta tablas</b>: prefiere arriesgar hasta perder "
    "antes que empatar. Valora un poco más tus piezas, así que busca cambios."],
   ["<b>Maestro de tablas</b>", "Totalmente defensivo y <b>busca las tablas</b>: repite jugadas y acepta "
    "tus ofertas con gusto."],
   ["<b>Posicional</b>", "Posicional al máximo: prefiere maniobrar antes que comer o dar jaque."]], [3.4, 13.0])
H2("Los estilos de los grandes jugadores")
P("Veintidós rivales imitan el estilo de grandes jugadores de la historia. Todos tienen fuerza 100: lo que "
  "cambia es cómo eligen entre las jugadas buenas.")
BIOS = {
    "Estilo Alekhine": "Alexander Alekhine, campeón del mundo de 1927 a 1935 y de 1937 a 1946. Combinaciones "
                       "profundas y ataque, con base posicional.",
    "Estilo Andersson": "Ulf Andersson, gran maestro sueco famoso por su solidez. Muy defensivo y difícil de "
                        "ganar; prefiere las tablas a correr riesgos.",
    "Estilo Botvinnik": "Mijaíl Botvinnik, campeón del mundo entre 1948 y 1963. Juego equilibrado y "
                        "científico, sin preferencias marcadas.",
    "Estilo Capablanca": "José Raúl Capablanca, campeón del mundo de 1921 a 1927. Claridad posicional, "
                         "sencillez y finales impecables.",
    "Estilo Fischer": "Bobby Fischer, campeón del mundo de 1972 a 1975. Juego clásico y preciso, siempre "
                      "para ganar.",
    "Estilo Karpov": "Anatoli Kárpov, campeón del mundo de 1975 a 1985. Ahoga al rival con pequeñas ventajas "
                     "posicionales; juega a ganar.",
    "Estilo Kashdan": "Isaac Kashdan, gran maestro estadounidense de los años treinta. Sólido y defensivo.",
    "Estilo Kasparov": "Garri Kaspárov, campeón del mundo de 1985 a 2000. Dinámico, muy agresivo y "
                       "posicional a la vez; casi nunca acepta tablas.",
    "Estilo Lasker": "Emanuel Lasker, campeón del mundo de 1894 a 1921. Pragmático, gran defensor y "
                     "materialista.",
    "Estilo Marshall": "Frank Marshall, campeón de Estados Unidos y rey de los gambitos (el «ataque Marshall» "
                       "lleva su nombre). Agresivo al máximo.",
    "Estilo Morphy": "Paul Morphy, el mejor jugador de la década de 1850. Desarrollo rápido y ataque directo.",
    "Estilo Nimzovich": "Aron Nimzowitsch, padre del juego hipermoderno y autor de «Mi sistema». Profilaxis, "
                        "bloqueo y defensa; muy posicional.",
    "Estilo Petrosian": "Tigran Petrosián, campeón del mundo de 1963 a 1969. Maestro de la profilaxis: "
                        "evita los planes del rival antes de que aparezcan.",
    "Estilo Reshevsky": "Samuel Reshevsky, gran maestro estadounidense y gran calculador. Defensivo, pero "
                        "juega a ganar.",
    "Estilo Reti": "Richard Réti, uno de los creadores de la escuela hipermoderna; la apertura Réti lleva su "
                   "nombre. Posicional.",
    "Estilo Rubinstein": "Akiba Rubinstein, gran maestro polaco de principios del siglo XX, famoso por sus "
                         "finales de torres. Sólido y posicional.",
    "Estilo Seirawan": "Yasser Seirawan, gran maestro estadounidense. Sólido y posicional.",
    "Estilo Smyslov": "Vasili Smyslov, campeón del mundo de 1957 a 1958. Armonía entre las piezas y "
                      "finales muy finos.",
    "Estilo Spassky": "Borís Spaski, campeón del mundo de 1969 a 1972. Jugador universal, agresivo y práctico.",
    "Estilo Spielman": "Rudolf Spielmann, maestro austríaco famoso por sus sacrificios. Valora poco sus "
                       "propias piezas y las entrega por el ataque; casi nunca acepta tablas.",
    "Estilo Tal": "Mijaíl Tal, campeón del mundo de 1960 a 1961, «el mago de Riga». Sacrificios "
                  "especulativos y ataques imposibles de calcular.",
    "Estilo Tarrasch": "Siegbert Tarrasch, maestro alemán de la escuela clásica: movilidad de las piezas y "
                       "control del centro.",
}
filas = [["Rival", "Ataque", "Posic.", "Quién fue y cómo juega"]]
for n, bio in BIOS.items():
    r = POR_NOMBRE[n]
    filas.append([f"<b>{n}</b>", signo(r.ataque), signo(r.posicional), bio])
T(filas, [3.3, 1.8, 1.45, 9.85])
H2("¿Contra quién jugar?")
B(["<b>Para aprender:</b> empezá por Novato o Fácil con los cuatro tipos de comentarios prendidos, y subí de "
   "nivel cuando les ganes con facilidad.",
   "<b>Para practicar tácticas:</b> Estilo Tal, Kamikaze o Estilo Marshall crean posiciones complicadas, "
   "llenas de sacrificios.",
   "<b>Para practicar finales y juego posicional:</b> Estilo Capablanca, Estilo Karpov o Posicional.",
   "<b>Para probar tu paciencia:</b> Maestro de tablas o Estilo Andersson.",
   "<b>Para el desafío máximo:</b> El Maestro o Experto, con reloj."])

# ------------------------------------------------------------------ 12. aprender
H1("12. Aprender: el tutor y las partidas clásicas")
H2("El tutor de ajedrez (Ctrl+T)")
IMG_("s_tutor.png", 16.4, "El tutor, con un desafío del Nivel 5 (configuraciones de mate).")
P("El tutor tiene tres secciones, que se eligen en el árbol de la izquierda:")
B(["<b>Reglas del ajedrez:</b> cada pieza, jaque y mate, ahogado, jugadas especiales y las notaciones.",
   "<b>Curso en 10 niveles:</b> desde lo básico hasta combinaciones, ataques dobles, sacrificios y estrategia.",
   "<b>Estrategia y conceptos:</b> 10 capítulos sobre planes, coordinación de piezas, estructuras de peones, "
   "columnas abiertas y juego de piezas."])
P("Cada página tiene un texto y un tablero con diagramas, flechas, casillas resaltadas y jugadas animadas. "
  "Algunas páginas son <b>desafíos</b> (con el ícono de la diana): tenés que hacer en el tablero la jugada correcta. Si no te sale, "
  "<b>Ver solución</b> la muestra.")
T([["Botón o tecla", "Qué hace"],
   ["Siguiente ▶▶ o Espacio", "Página siguiente."],
   ["Jugada ▶ o flecha →", "Muestra la próxima jugada animada de la página."],
   ["◀ Anterior o flecha ←", "Página anterior."],
   ["Ver solución", "En los desafíos, muestra la jugada correcta."]], [5.0, 11.4])
H2("Las partidas clásicas comentadas (Ctrl+L)")
IMG_("s_clasicas.png", 16.4, "El visor de partidas clásicas.")
P("502 partidas célebres, desde 1790 hasta 1993, repartidas en nueve colecciones, con los comentarios "
  "traducidos al español. Elegí la colección arriba a la izquierda y la partida en la lista.")
B(["Los botones de abajo van al principio, a la jugada anterior, a la siguiente o al final.",
   "<b>Reproducir</b> avanza las jugadas solo; <b>Girar</b> da vuelta el tablero.",
   "Hacé clic en cualquier jugada del texto de la derecha para ir directamente a ella. Las jugadas con "
   "comentario muestran su texto arriba.",
   "<b>Jugar desde aquí</b> lleva la posición actual al tablero principal para que sigas la partida contra el "
   "rival que elijas."])

# ------------------------------------------------------------------ 13. apariencia
H1("13. Apariencia, sonido y portada")
IMG_("s_3d.png", 16.4, "Tablero de madera 3D con el juego de piezas «Napoleónico».")
H2("Tableros")
P("Menú <b>Ver → Tablero</b>:")
B(["<b>2D:</b> " + ", ".join(n for _, n, *_ in rec.tableros_2d()) + ".",
   "<b>3D</b>, con perspectiva: " + ", ".join(n for _, n in rec.tableros_3d()) + ".",
   "<b>Colores lisos:</b> clásico, torneo verde, azul y gris."])
H2("Juegos de piezas")
P("Menú <b>Ver → Piezas</b>, 17 juegos: " + ", ".join(n for _, n in rec.juegos_piezas()) + ". Los juegos 3D "
  "se ven mejor con los tableros 3D, porque las piezas se paran sobre el tablero en perspectiva.")
H2("Escalado de gráficos")
P("Los gráficos originales son de baja resolución y Jaque los agranda al tamaño de tu pantalla. En <b>Ver → "
  "Escalado de gráficos</b> elegís cómo:")
B(["<b>Mejorado</b> (Scale2x + suavizado): bordes limpios y suaves; es el recomendado.",
   "<b>Suave:</b> más difuminado.",
   "<b>Píxel nítido:</b> conserva los píxeles tal cual, con aspecto retro."])
H2("Otras opciones del menú Ver")
B(["<b>Coordenadas:</b> muestra u oculta las letras y números alrededor del tablero.",
   "<b>Pantalla completa</b> (F11).",
   "<b>Sonido:</b> prende o apaga los sonidos (jugadas, capturas, jaque, enroque, coronación, mate, tablas).",
   "<b>Comentarios en vivo:</b> capítulo 8."])
H2("Tu propia portada")
P("Guardá una imagen como <font name='Mono'>portada.png</font> (o .jpg) en la carpeta de datos de Jaque "
  "(capítulo 15) y aparece al arrancar en lugar de la que trae. Se ve mejor con proporción 16:10, por "
  "ejemplo 1600 × 1000 píxeles. Para volver a la original, borrá ese archivo.")

# ------------------------------------------------------------------ 14. menús y atajos
H1("14. Menús y atajos de teclado")
T([["Menú", "Opciones"],
   ["<b>Partida</b>", "Nueva partida · Abrir PGN · Guardar PGN · Ofrecer tablas · Rendirse · Salir"],
   ["<b>Jugada</b>", "Deshacer · Rehacer · Sugerencia · Mover ahora (que juegue el rival)"],
   ["<b>Ver</b>", "Girar tablero · Coordenadas · Pantalla completa · Tablero · Piezas · Escalado de gráficos · "
    "Comentarios en vivo · Sonido"],
   ["<b>Aprender</b>", "Tutor de ajedrez · Partidas clásicas comentadas"],
   ["<b>Opciones</b>", "Volver a preparar gráficos y sonidos · Ruta de Stockfish"],
   ["<b>Ayuda</b>", "Acerca de Jaque"]], [3.0, 13.4])
T([["Atajo", "Acción", "Atajo", "Acción"],
   ["Ctrl+N", "Nueva partida", "Ctrl+H", "Sugerencia"],
   ["Ctrl+O", "Abrir PGN", "Ctrl+M", "Mover ahora"],
   ["Ctrl+S", "Guardar PGN", "F", "Girar tablero"],
   ["Ctrl+Z", "Deshacer", "F11", "Pantalla completa"],
   ["Ctrl+Y / Ctrl+Shift+Z", "Rehacer", "Ctrl+T", "Tutor"],
   ["Ctrl+Q", "Salir", "Ctrl+L", "Partidas clásicas"]], [3.6, 4.6, 3.0, 5.2])
DIAG_MENUS = [("s_menu_partida.png", "Menú Partida"), ("s_menu_jugada.png", "Menú Jugada"),
              ("s_menu_ver.png", "Menú Ver")]
celdas = []
for nombre, pie in DIAG_MENUS:
    from PIL import Image as PI
    w, h = PI.open(IMG / nombre).size
    ancho = 5.0 if nombre != "s_menu_jugada.png" else 5.3
    celdas.append([Image(str(IMG / nombre), width=ancho * cm, height=ancho * cm * h / w),
                   Paragraph(pie, st["cap"])])
t = Table([celdas], colWidths=[5.45 * cm] * 3)
t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
story.append(t)

# ------------------------------------------------------------------ 15. archivos
H1("15. Archivos y carpetas")
T([["Qué", "Linux", "Windows"],
   ["Programa", "~/.local/share/jaque/programa", "%LOCALAPPDATA%\\Programs\\Jaque"],
   ["Gráficos, sonidos y textos", "~/.local/share/jaque/recursos", "Junto al programa (recursos)"],
   ["Piezas y sonidos preparados", "~/.cache/jaque", "%LOCALAPPDATA%\\Jaque\\cache"],
   ["Opciones", "~/.config/Jaque/Jaque.conf", "Registro de Windows (HKCU\\Software\\Jaque)"],
   ["Portada propia", "~/.local/share/jaque/portada.png", "%LOCALAPPDATA%\\Jaque\\portada.png"],
   ["Informe de verificación", "~/.local/share/jaque/verificacion.txt", "%LOCALAPPDATA%\\Jaque\\verificacion.txt"],
   ["Registro de la instalación", "~/.local/share/jaque/instalacion.log", "—"]], [4.4, 6.0, 6.0])
P("Jaque recuerda el último rival, el color, el control de tiempo, el tablero, las piezas, el escalado, el "
  "sonido, las opciones de comentarios y el tamaño de la ventana. Para volver a la configuración de fábrica, "
  "borrá el archivo de opciones con Jaque cerrado.")

# ------------------------------------------------------------------ 16. problemas
H1("16. Solución de problemas")
T([["Problema", "Qué hacer"],
   ["Jaque no aparece en el menú de Linux", "Cerrá sesión y volvé a entrar. Si sigue sin aparecer, reinstalá: "
    "el instalador quita las marcas de «oculto» que haya dejado el editor de menús de KDE."],
   ["Se cierra al arrancar", "El lanzador lo vuelve a abrir solo, sin sonido. También podés arrancarlo así: "
    "<font name='Mono'>JAQUE_SIN_SONIDO=1 jaque</font>."],
   ["No puedo mover las piezas", "Revisá que sea tu turno y que el rival no esté pensando (lo dice el "
    "estado). Si la partida terminó, empezá una nueva."],
   ["Las piezas se ven raras o recortadas", "Menú Opciones → Volver a preparar gráficos y sonidos."],
   ["El rival no responde", "Revisá Opciones → Ruta de Stockfish, o ejecutá "
    "<font name='Mono'>jaque --verificar</font>."],
   ["Windows dice «Windows protegió su PC»", "Más información → Ejecutar de todas formas. Pasa porque el "
    "instalador no está firmado digitalmente."],
   ["Un comentario no coincide con el tablero", "Recordá que describe lo que el rival <i>podría</i> hacer. "
    "Si igual parece equivocado, guardá la partida en PGN y revisala con Deshacer."]], [5.0, 11.4])

# ------------------------------------------------------------------ 17. glosario
H1("17. Glosario")
GLOS = [
    ("Ahogado", "El que mueve no está en jaque pero no tiene jugadas legales. Es tablas."),
    ("Apertura", "La fase inicial de la partida. Ver capítulo 8.1."),
    ("Ataque doble", "Una jugada que ataca dos piezas a la vez; normalmente se gana una de ellas."),
    ("Centipeón", "Centésima parte de un peón; la unidad con la que mide Stockfish."),
    ("Clavada", "Una pieza no puede moverse porque dejaría expuesta otra más valiosa (o al rey) detrás de ella."),
    ("Columna abierta", "Columna sin peones; ideal para las torres."),
    ("Desarrollo", "Sacar las piezas de su casilla inicial hacia casillas activas."),
    ("ECO", "Encyclopaedia of Chess Openings: el código de cinco letras y números de cada apertura (A00 a E99)."),
    ("Final", "La última fase de la partida, con pocas piezas en el tablero."),
    ("Gambito", "Una apertura en la que se entrega material (casi siempre un peón) a cambio de desarrollo o ataque."),
    ("Horquilla", "Ataque doble hecho por un caballo."),
    ("Jugada de libro", "Una jugada que figura en la teoría de aperturas."),
    ("Línea", "Una secuencia de jugadas posibles; la «línea principal» es la que el motor considera mejor."),
    ("Material", "El conjunto de piezas de cada bando, medido con sus valores (peón 1, caballo 3, alfil 3, torre 5, "
                 "dama 9)."),
    ("Medio juego", "La fase entre la apertura y el final, donde suelen darse los ataques y las combinaciones."),
    ("Peón pasado", "Un peón que no tiene peones rivales delante ni en las columnas vecinas: nada le impide "
                    "avanzar hasta coronar salvo las piezas."),
    ("Pieza colgada", "Una pieza atacada y sin defensa, que el rival puede comer gratis."),
    ("Pieza menor", "Caballo o alfil."),
    ("Profilaxis", "Jugar para impedir los planes del rival antes de que los lleve a cabo."),
    ("Profundidad", "Cuántas jugadas hacia adelante calculó el motor."),
    ("Sacrificio", "Entregar material a propósito a cambio de ataque, iniciativa o un mate."),
    ("Tiempo", "Una jugada. «Ganar un tiempo» es lograr algo útil mientras el rival pierde una jugada (por "
               "ejemplo, desarrollar una pieza atacando la dama rival)."),
    ("Variante", "Una rama de una apertura con nombre propio (por ejemplo, la variante Najdorf de la siciliana)."),
]
T([["Término", "Significado"]] + [[f"<b>{a}</b>", b] for a, b in GLOS], [3.6, 12.8])

# ------------------------------------------------------------------ historial
H1("Historial de versiones")
P("Las novedades principales de cada versión. El detalle completo está en el archivo "
  "<font name='Mono'>CHANGELOG.md</font> del código fuente.")
T([["Versión", "Novedades principales"],
   ["<b>0.7.6</b>", "«Acerca de Jaque» indica si es la versión para Linux o para Windows, con el nombre completo "
    "del autor. En Windows, Ricardo Vera figura como editor en la lista de aplicaciones instaladas."],
   ["<b>0.7.5</b>", "Permitir un mate siempre es error grave (??) y perder tres peones de material o más es "
    "como mínimo error (?), aunque la partida ya esté decidida. Primer manual de usuario."],
   ["<b>0.7.4</b>", "Comentarios y análisis siguen a Deshacer y Rehacer. Explicaciones en condicional. "
    "Arreglo del tablero bloqueado al empezar una partida nueva."],
   ["<b>0.7.3</b>", "Rehacer sin límite (Ctrl+Y) y botones reacomodados."],
   ["<b>0.7.2</b>", "Los comentarios distinguen un cambio de piezas de una pieza sin defensa."],
   ["<b>0.7.1</b>", "«Desinstalar Jaque» en el menú de aplicaciones y el comando jaque --desinstalar."],
   ["<b>0.7.0</b>", "Comentarios en vivo: nombre de la apertura, evaluación de tus jugadas, frases del rival y "
    "avisos de amenazas."],
   ["<b>0.6.0</b>", "Versión para Windows 11 y paquete de código fuente para compartir."],
   ["<b>0.5.1</b>", "Arreglo del acceso en el menú de KDE, ícono en el escritorio y arranque sin sonido si "
    "el audio falla."],
   ["<b>0.5.0</b>", "Instalador autosuficiente, sin internet, con verificación."],
   ["<b>0.4.0</b>", "Primer instalador con todo adentro. Portada con la versión, capturas y coronación más "
    "grandes, arreglo de las piezas de acero."],
   ["<b>0.3</b>", "Ya no depende del ISO. Portada e ícono propios."],
   ["<b>0.2</b>", "Tableros 3D, tutor y partidas clásicas comentadas."],
   ["<b>0.1</b>", "Primer prototipo: tableros 2D, 17 juegos de piezas, 40 rivales, Stockfish, relojes y PGN."]],
  [2.0, 14.4])

# ------------------------------------------------------------------ créditos
H1("Créditos")
B([f"<b>Jaque {__version__}</b>, de Ricardo Vera. Programa en Python con interfaz Qt (PySide6), licencia GPL v3.",
   "<b>Stockfish</b>, el motor de ajedrez (licencia GPL v3).",
   "<b>python-chess</b>, para las reglas y la notación.",
   "<b>Base de aperturas ECO:</b> paquete <i>chess-openings</i> de Guido Flohr (licencia WTFPL), traducida al "
   "español para Jaque.",
   "Los gráficos, sonidos, rivales, lecciones y partidas provienen de la copia personal del juego original "
   "de 1995. Este manual es para uso personal."])


# ================================================================== documento
class Doc(BaseDocTemplate):
    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        marco = Frame(2.3 * cm, 2.0 * cm, A4[0] - 4.6 * cm, A4[1] - 4.2 * cm, id="m")
        portada = Frame(2.0 * cm, 1.5 * cm, A4[0] - 4.0 * cm, A4[1] - 3.0 * cm, id="p")
        self.addPageTemplates([PageTemplate("portada", [portada], onPage=self._fondo_portada),
                               PageTemplate("normal", [marco], onPage=self._pagina)])

    def _fondo_portada(self, c, d):
        c.saveState()
        c.setFillColor(colors.HexColor("#fbf6ee"))
        c.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        c.setFillColor(OSCURO)
        c.rect(0, 0, A4[0], 0.9 * cm, fill=1, stroke=0)
        c.restoreState()

    def _pagina(self, c, d):
        c.saveState()
        c.setStrokeColor(DORADO)
        c.setLineWidth(0.6)
        c.line(2.3 * cm, A4[1] - 1.45 * cm, A4[0] - 2.3 * cm, A4[1] - 1.45 * cm)
        c.setFont("Sans", 8)
        c.setFillColor(GRIS)
        c.drawString(2.3 * cm, A4[1] - 1.25 * cm, f"Jaque {__version__} — Manual de usuario")
        c.drawRightString(A4[0] - 2.3 * cm, 1.2 * cm, str(d.page))
        c.restoreState()

    def afterFlowable(self, f):
        if hasattr(f, "_toc"):
            nivel, texto = f._toc
            clave = f"t{id(f)}"
            self.canv.bookmarkPage(clave)
            self.canv.addOutlineEntry(texto, clave, level=nivel)
            self.notify("TOCEntry", (nivel, texto, self.page, clave))


doc = Doc(str(SALIDA), pagesize=A4, title=f"Jaque {__version__} — Manual de usuario", author="Ricardo Vera",
          subject="Manual de usuario de Jaque")
doc.multiBuild(story)
print(SALIDA)
