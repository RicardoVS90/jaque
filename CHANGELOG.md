# Registro de cambios de Jaque

Todas las novedades de cada versión, de la más nueva a la más vieja.
Cada número de versión tiene tres partes (0.7.4): la del medio cambia cuando
hay novedades grandes y la última cuando hay arreglos o mejoras chicas.

---

## 0.7.4 — Deshacer y rehacer coherentes

### Arreglado
- Al **deshacer**, ahora desaparecen los comentarios de las jugadas quitadas
  (evaluaciones, frases del rival, avisos y aperturas); al **rehacer** vuelven
  exactamente los mismos, sin repetirse.
- El recuadro **Análisis** también sigue a deshacer y rehacer: muestra la
  evaluación y la línea que el rival tenía en ese punto de la partida.
- Si después de deshacer se juega algo distinto, se descartan las jugadas,
  marcas, comentarios y análisis de la rama vieja.
- **Nueva partida** después de una partida terminada dejaba el tablero
  bloqueado (no se podían mover las piezas hasta tocar «Deshacer»).

### Cambiado
- Las explicaciones de los errores pasan al condicional, para que no parezca
  que la jugada ya ocurrió: «el rival **podría responder** Cf6, atacando tu
  dama».

## 0.7.3 — Rehacer

### Nuevo
- **Rehacer** sin límite: menú *Jugada → Rehacer* (Ctrl+Y o Ctrl+Shift+Z) y
  botón al costado del tablero. Vuelve a poner tu jugada y la respuesta del
  rival, con sus marcas.
- Si después de deshacer jugás la misma jugada que habías deshecho, se
  conserva el resto para seguir rehaciendo.

### Cambiado
- Botones reacomodados: arriba **◀ Deshacer | Rehacer ▶**; abajo Nueva
  partida, Sugerencia y Girar tablero.
- Los botones y menús deshabilitados se ven apagados (gris).

## 0.7.2 — Comentarios más precisos

### Arreglado
- El comentarista confundía un **cambio de piezas** con una pieza sin defensa
  (por ejemplo, un peón en d5 defendido por el peón de e4 y el alfil de c4).
  Ahora distingue tres casos: pieza sin defensa, pieza defendida pero atacada
  por algo de menos valor, y cambio parejo.

## 0.7.1 — Desinstalar desde el menú

### Nuevo
- **«Desinstalar Jaque»** en el clic derecho de la entrada del menú de
  aplicaciones, con confirmación en una ventana.
- Comando `jaque --desinstalar` en la terminal.
- Desinstalador propio en `~/.local/share/jaque/desinstalar.sh`: borra el
  programa, los gráficos, la caché, el comando, la entrada del menú y el ícono
  del escritorio, y conserva tus opciones.

### Nota
- La opción «Desinstalar o administrar complementos» que agrega KDE no sirve
  para Jaque, porque Jaque no se instala como paquete del sistema.

## 0.7.0 — Comentarios en vivo

### Nuevo
- Recuadro **Comentarios** al costado del tablero:
  - **Nombre de la apertura** en español con su código ECO (3.608 posiciones,
    por ejemplo «C50 · Apertura italiana: gambito Blackburne-Kostić»).
  - **Evaluación de tus jugadas** con un segundo Stockfish en segundo plano:
    **?!** imprecisión, **?** error, **??** error grave, con explicación y la
    jugada que era mejor. También avisa si se te escapó un mate y te felicita
    cuando aprovechás un error del rival.
  - **Frases del rival** según su personalidad (agresivo, defensivo,
    posicional, materialista, novato), ante jaques, sacrificios, capturas,
    enroques, coronaciones y cambios en la evaluación.
  - **Avisos de amenazas**: piezas atacadas sin defensa o por algo de menos
    valor, y amenazas de mate en una jugada.
- Las marcas aparecen en color en la lista de jugadas y se guardan en el PGN
  (junto con la apertura y su código ECO).
- Menú *Ver → Comentarios en vivo* para activar o desactivar cada tipo por
  separado; se aplica al instante y se recuerda.
- Créditos de la base de aperturas (*chess-openings*, licencia WTFPL) en
  *Ayuda → Acerca de*.

## 0.6.0 — Versión para Windows y código fuente

### Nuevo
- **Jaque para Windows 11**: kit con `construir.bat` que instala lo que falte
  (Python e Inno Setup), congela el programa y arma un instalador `.exe` que
  funciona sin internet, con accesos en el menú Inicio y desinstalador.
- Carpetas según el sistema: `~/.local/share/jaque` en Linux y
  `%LOCALAPPDATA%\Jaque` en Windows.
- Stockfish incluido junto al programa; en Windows corre sin abrir una
  ventana negra.
- **Paquete de código fuente** para compartir: licencia GPL v3, encabezados de
  licencia en cada archivo y scripts para armar los instaladores de Linux y
  Windows. No incluye nada del juego original.

## 0.5.1 — Accesos directos confiables

### Arreglado
- El instalador a veces no creaba la entrada del menú (falla al leer la
  versión de glibc del sistema). Ahora los accesos se crean apenas se copia el
  programa.
- Si Jaque se había quitado alguna vez con el editor de menús de KDE, KDE lo
  seguía ocultando aunque se reinstalara. El instalador quita esa marca y
  actualiza el menú de KDE en el momento.

### Nuevo
- Ícono en el escritorio.
- Si el programa se cierra de golpe al iniciar el sonido, se vuelve a abrir
  solo, sin sonido.
- Registro de la instalación en `~/.local/share/jaque/instalacion.log`.

## 0.5.0 — Instalador autosuficiente

### Nuevo
- El instalador `.run` trae **todo adentro**: su propio Python y bibliotecas
  (Qt, numpy, scipy, Pillow, python-chess), el motor Stockfish, gráficos,
  sonidos, lecciones, partidas y traducciones. No usa internet, ni pip, ni el
  ISO: se puede instalar en una PC recién formateada.
- Escaneo de las bibliotecas del sistema que hacen falta, con el comando
  exacto para instalarlas si falta alguna.
- Modo `--verificar` en el instalador y opción `jaque --verificar`: revisa Qt,
  sonido, bibliotecas, recursos, traducciones y motor.
- Piezas y sonidos preparados durante la instalación (el primer arranque es
  inmediato).

## 0.4.0 — Todo en un solo instalador, portada propia

### Nuevo
- Primer instalador `.run` con todo incluido: programa, gráficos, sonidos y
  textos. Después de instalar, el ISO ya no hace falta.
- Portada nueva con «Jaque» y el número de versión en letras más chicas.
- Las traducciones del tutor y de las partidas clásicas (5.853 textos) viajan
  dentro del instalador.

### Cambiado
- Piezas capturadas más grandes y agrupadas por tipo.
- Ventana de coronación más grande, con cuatro botones grandes (Dama, Torre,
  Alfil, Caballo) centrados sobre el tablero.

### Arreglado
- Juego de piezas **Moderno de acero**: la línea negra debajo de la dama
  blanca y de todas las piezas negras, los restos de la cuadrícula y el rey
  recortado.

## 0.3 — Sin depender del ISO

### Nuevo
- Los gráficos y sonidos se preparan **una sola vez** en
  `~/.local/share/jaque/recursos` y las piezas se recortan de antemano;
  después el ISO se puede borrar.
- El instalador busca el ISO solo (en la misma carpeta o en Descargas).
- Opción *Opciones → Volver a preparar gráficos y sonidos*.
- **Portada e ícono propios**, y portada personalizable: guardá una imagen
  como `~/.local/share/jaque/portada.png`.
- Se quitaron las menciones al juego original de la interfaz (por ejemplo, el
  rival principal pasa a llamarse «El Maestro»).

## 0.2 — Tableros 3D, tutor y partidas clásicas

### Nuevo
- **Tableros 3D** (madera, mármol verde y azul, ébano y marfil, teca china,
  metal y el paisaje surrealista) con la perspectiva reconstruida; con las
  piezas 3D, las piezas se paran sobre el tablero.
- Menú **Aprender**:
  - **Tutor** (Ctrl+T): reglas, curso en 10 niveles y 10 capítulos de
    estrategia, con diagramas, jugadas animadas y desafíos en el tablero.
  - **Partidas clásicas** (Ctrl+L): 502 partidas comentadas (de 1790 a 1993),
    visor jugada a jugada, reproducción automática y «Jugar desde aquí».
- Lecciones y comentarios de las partidas traducidos al español.

## 0.1 — Primer prototipo

### Nuevo
- Ajedrez en español para Linux con **Stockfish** como motor, con los gráficos
  escalados a cualquier resolución (1080p, 1440p, 4K).
- Tableros 2D (madera grande y chico, mármol verde y azul) y tableros de
  colores lisos.
- Los 17 juegos de piezas, recortados automáticamente de las imágenes con sus
  máscaras.
- Tres modos de escalado: Mejorado (Scale2x + suavizado), Suave y Píxel nítido.
- Los **40 rivales** con su personalidad (fuerza, azar, ataque o defensa,
  actitud ante las tablas, valor de cada pieza): Stockfish propone las
  jugadas y la personalidad elige entre ellas.
- Notación en español (R, D, T, A, C), sugerencias con flecha, evaluación y
  línea que piensa el rival.
- Relojes (blitz, rápida, clásica, con incremento), deshacer, ofrecer tablas,
  rendirse, girar el tablero, guardar y abrir PGN.
- Sonidos y portada de inicio.
