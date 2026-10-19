# Jaque 0.2

Programa de ajedrez para Linux, en español, que usa los **tableros, piezas,
sonidos y rivales de tu propia copia de Chessmaster 4000 Turbo** y a
**Stockfish** como motor. Escala los gráficos a 1920×1080, 2560×1440 o lo que
tenga tu monitor.

Jaque no incluye ningún archivo del juego original: los lee del ISO o de la
carpeta instalada cada vez que arranca.

## Instalación (Debian 13 / KDE)

```bash
cd jaque
./instalar.sh
```

Instala Stockfish si falta (con `sudo apt`), crea un entorno de Python en
`~/.local/share/jaque/venv`, agrega el comando `jaque` y una entrada en el
menú de aplicaciones.

Para probar sin instalar nada:

```bash
sudo apt install stockfish
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m jaque --recursos /ruta/a/CM4000_WIN95-98.ISO
```

## Qué trae esta versión

- Tableros 2D del juego (madera grande y chico, mármol verde, mármol azul) y
  tableros de colores lisos.
- **Tableros 3D** del juego (madera, mármol verde y azul, ébano y marfil, teca
  china, metal y el paisaje surrealista de Dalí), con la perspectiva
  original reconstruida. Con los juegos de piezas 3D, las piezas se paran
  sobre el tablero.
- Los 17 juegos de piezas originales (Staunton, fantasía, dinosaurios,
  insectos, napoleónico, criaturas marinas, tuercas, letras…), recortados
  automáticamente de los BMP con sus máscaras.
- Tres modos de escalado: *Mejorado* (Scale2x + suavizado), *Suave* y
  *Píxel nítido*.
- Los 40 rivales del juego (Estilo Tal, Estilo Karpov, Kamikaze, Comepeones,
  Maestro de tablas, Novato…). Se leen sus parámetros reales de los `.CMX`:
  fuerza, aleatoriedad, ataque o defensa, actitud ante las tablas y el valor
  que le da a cada pieza. Stockfish propone las mejores jugadas y la
  personalidad elige entre ellas.
- Notación en español (R, D, T, A, C), sugerencias con flecha, evaluación y
  línea que piensa el rival.
- Relojes (blitz, rápida, clásica, con incremento), deshacer, ofrecer tablas,
  rendirse, girar el tablero, guardar y abrir PGN.
- Menú **Aprender**:
  - **Tutor** (Ctrl+T): las reglas, el curso en 10 niveles y los 10 capítulos
    de estrategia del juego original, traducidos al español, con diagramas,
    jugadas animadas y desafíos para resolver en el tablero.
  - **Partidas clásicas** (Ctrl+L): las 502 partidas comentadas del juego
    (desde 1790 hasta 1993), con todos los comentarios en español, visor
    jugada a jugada, reproducción automática y «Jugar desde aquí» contra
    cualquier rival.
- Sonidos originales (convertidos a 16 bits y guardados en `~/.cache/jaque`) y
  portada de inicio.

## Atajos

| Tecla | Acción |
|---|---|
| Ctrl+N | Nueva partida |
| Ctrl+Z | Deshacer |
| Ctrl+H | Sugerencia |
| Ctrl+M | Que el rival juegue por vos (cambia de bando) |
| F | Girar tablero |
| F11 | Pantalla completa |
| Ctrl+S / Ctrl+O | Guardar / abrir PGN |
| Ctrl+T | Tutor |
| Ctrl+L | Partidas clásicas |
| Espacio / → / ← | En el tutor: siguiente página / jugada / anterior |

## Problemas conocidos

- El libro de aperturas propio (`.OBK`) no se usa: Stockfish juega la apertura
  y los rivales con libro varían entre jugadas parejas.
- Si el audio da problemas, arrancá con `JAQUE_SIN_SONIDO=1 jaque`.
- Configuración guardada en `~/.config/Jaque/Jaque.conf`; para empezar de
  cero, borrá ese archivo y `~/.cache/jaque`.

## Sobre las traducciones

La carpeta `traducciones/` tiene la traducción al español de los textos del
tutor y de los comentarios de las partidas clásicas. Esos textos son obra de
los autores del Chessmaster original, así que la traducción es **solo para tu
uso personal** junto con tu copia del juego: no publiques esa carpeta.
También se puede poner en `~/.local/share/jaque/traducciones/es.json`.

## Estructura

```
jaque/
  assets.py     lectura del ISO/carpeta (CM.INI, BMP, CMX, WAV)
  sprites.py    recorte de juegos de piezas con sus máscaras
  escalado.py   Scale2x y escalado con Qt
  tablero.py    widget del tablero (dibujo, clic, arrastre, animación)
  rivales.py    formato CMX y cómo juega cada personalidad
  motor.py      Stockfish en un hilo aparte
  notacion.py   notación y textos en español
  sonidos.py    sonidos originales
  app.py        ventana, menús, relojes, PGN
  tutoriales.py lectura de los guiones de lecciones (.TUT)
  clasicas.py   lectura de las colecciones de partidas (.CML)
  traduccion.py carga de traducciones y notación en español
  ventanas.py   ventanas del Tutor y de Partidas clásicas
```

Chessmaster es marca de Ubisoft. Este proyecto no está afiliado con Ubisoft.
