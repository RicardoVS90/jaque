# Jaque

Programa de ajedrez en español para **Linux** y **Windows**, escrito en Python
con Qt (PySide6) y con **Stockfish** como motor.

- Tableros 2D y 3D (con perspectiva reconstruida), escalados a cualquier
  resolución: 1080p, 1440p, 4K.
- 40 rivales con personalidad propia (agresivo, posicional, tablista, novato…)
  que eligen entre las jugadas que propone Stockfish.
- Tutor interactivo con desafíos sobre el tablero y visor de partidas clásicas
  comentadas, con reproducción automática y «Jugar desde aquí».
- Notación en español (R, D, T, A, C), relojes, sugerencias, deshacer y rehacer sin límite, PGN.
- Comentarios en vivo: nombre de la apertura (código ECO), evaluación de tus
  jugadas (!, ?!, ?, ??) con explicación, frases del rival según su estilo y
  avisos de piezas sin defensa o amenazas de mate.
- Instaladores autosuficientes: Linux (`.run`) y Windows (`.exe`), con su
  propio Python y bibliotecas adentro.

## Importante: el contenido gráfico no está incluido

Este repositorio contiene **solo el código**. Los tableros, piezas, sonidos,
rivales, lecciones y partidas se leen de una copia original del CD de
*Chessmaster 4000 Turbo* (1995) que tiene que aportar cada usuario. Jaque no
contiene ni distribuye ningún archivo de ese juego.

Chessmaster es marca registrada de su propietario; este proyecto no tiene
relación con él.

## Probar desde el código (Linux)

```bash
sudo apt install stockfish python3-venv
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m jaque.preparar /ruta/a/tu/cd.iso    # una sola vez
.venv/bin/python -m jaque
```

O todo junto: `./instalar.sh /ruta/a/tu/cd.iso`

Comprobar la instalación: `python -m jaque --verificar`

## Armar los instaladores

**Linux** (x86_64, glibc 2.39+):

```bash
pip install -r requirements.txt pyinstaller
empaquetado/linux/construir.sh /ruta/a/tu/cd.iso
# -> build/Jaque-0.7.4-instalador.run
```

**Windows 11:**

```bat
empaquetado\windows\construir.bat C:\ruta\a\tu\cd.iso
:: -> salida\Jaque-0.7.4-instalador-windows.exe
```

El script de Windows instala solo Python 3.13 e Inno Setup (con winget) si
faltan, descarga Stockfish y arma el instalador.

> Los instaladores resultantes llevan adentro el contenido de tu CD: son para
> uso personal y no deben publicarse (el `.gitignore` ya los excluye).

## Traducciones

Los textos del tutor y los comentarios de las partidas están en inglés en el CD.
Jaque busca una traducción opcional en `traducciones/es.json` (formato
`{"texto original": "traducción"}`); si no existe, los muestra en inglés.
Las traducciones son obra derivada del contenido original, así que tampoco se
incluyen en el repositorio.

## Estructura

```
jaque/
  app.py          ventana principal, menús, relojes, PGN
  tablero.py      dibujo del tablero 2D/3D, arrastre, animaciones
  assets.py       lectura de recursos (paquete preparado, ISO o carpeta)
  preparar.py     arma el paquete de recursos a partir del ISO
  sprites.py      recorte de piezas a partir de imagen + máscara
  escalado.py     Scale2x y escalado con Qt
  rivales.py      formato de personalidades y elección de jugadas
  motor.py        Stockfish en un hilo aparte
  comentarista.py comentarios en vivo (aperturas, evaluación, rival, amenazas)
  tutoriales.py   intérprete de los guiones de lecciones
  clasicas.py     lector de las colecciones de partidas
  ventanas.py     ventanas del Tutor y de Partidas clásicas
  traduccion.py   traducciones y notación en español
  notacion.py     notación y textos en español
  sonidos.py      sonidos (conversión y reproducción)
  rutas.py        carpetas según el sistema (Linux / Windows)
  verificar.py    chequeo completo:  jaque --verificar
  datos/          portada, ícono y base de aperturas en español
empaquetado/
  linux/          instalador .run autosuficiente (PyInstaller + bash)
  windows/        instalador .exe (PyInstaller + Inno Setup)
```

## Novedades

El registro de cambios de cada versión está en `CHANGELOG.md`.

## Licencia

GPL v3 (ver `LICENSE`). Copyright © 2026 Ricardo.
Stockfish se distribuye bajo GPL v3; PySide6/Qt bajo LGPL v3.
La base de aperturas (`jaque/datos/aperturas.json`) proviene del paquete
*chess-openings* de Guido Flohr (licencia WTFPL) y fue traducida al español.
