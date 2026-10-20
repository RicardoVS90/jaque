# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo Vera.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Recorte de juegos de piezas.

Cada juego viene en dos BMP: la imagen (6 piezas x 2 colores) y una mascara
de 1 bit con la silueta de cada pieza. Las grillas no son uniformes entre
juegos, asi que se segmenta la mascara en siluetas y luego se busca el
desplazamiento que mejor encaja cada silueta sobre la imagen.
"""
import numpy as np
from PIL import Image
from scipy import ndimage

ORDEN = ["P", "R", "N", "B", "Q", "K"]  # peon, torre, caballo, alfil, dama, rey


def _siluetas(m):
    """m: bool (True = pieza). Devuelve 12 bboxes ordenadas (fila, columna)."""
    m = _sin_grilla(m)
    H, W = m.shape
    m[_corte_filas(m), :] = False   # separar fila blanca de fila negra
    lab, n = ndimage.label(m, structure=np.ones((3, 3)))
    objs = ndimage.find_objects(lab)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    comps = [(sizes[i], objs[i]) for i in range(n)]
    comps.sort(key=lambda c: -c[0])
    big = [list((s[1].start, s[0].start, s[1].stop, s[0].stop)) for _, s in comps[:12]]
    # fragmentos pequenos (cetros, banderas): unir a la pieza grande mas cercana
    for _, s in comps[12:]:
        x0, y0, x1, y1 = s[1].start, s[0].start, s[1].stop, s[0].stop
        if min(x1 - x0, y1 - y0) <= 2 and max(x1 - x0, y1 - y0) > 12:
            continue  # resto de linea de grilla
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        def dist(b):
            dx = max(b[0] - cx, 0, cx - b[2]); dy = max(b[1] - cy, 0, cy - b[3])
            return dx * dx + dy * dy
        b = min(big, key=dist)
        if dist(b) < (W / 12) ** 2:
            b[0], b[1], b[2], b[3] = min(b[0], x0), min(b[1], y0), max(b[2], x1), max(b[3], y1)
    ymin = min(b[1] for b in big); ymax = max(b[3] for b in big)
    mid = (ymin + ymax) / 2
    arriba = [b for b in big if (b[1] + b[3]) / 2 < mid]
    abajo = [b for b in big if (b[1] + b[3]) / 2 >= mid]
    if len(arriba) != 6:  # respaldo: ordenar por centro vertical
        big.sort(key=lambda b: (b[1] + b[3]) / 2)
        arriba, abajo = big[:6], big[6:]
    return [sorted(arriba, key=lambda b: b[0]), sorted(abajo, key=lambda b: b[0])]


def _lineas(frac):
    """Indices de lineas finas de grilla (casi completas y con vecinos vacios)."""
    n = len(frac)
    out = []
    for i in range(n):
        if frac[i] > 0.97:
            a = frac[i - 2] if i >= 2 else 0
            b = frac[i + 2] if i + 2 < n else 0
            if min(a, b) < 0.7:
                out.append(i)
    return out


def _sin_grilla(m):
    m = m.copy()
    m[:, _lineas(m.mean(axis=0))] = False
    m[_lineas(m.mean(axis=1)), :] = False
    return m


def _corte_filas(m):
    """Fila con menos pixeles de pieza cerca del centro vertical del contenido."""
    ys = np.nonzero(m.any(axis=1))[0]
    y0, y1 = ys.min(), ys.max()
    mid = (y0 + y1) // 2
    band = max(2, (y1 - y0) // 10)
    cuenta = m.sum(axis=1)
    rango = range(max(0, mid - band), min(len(cuenta), mid + band + 1))
    return min(rango, key=lambda y: (cuenta[y], abs(y - mid)))


def _recortar_bordes(rgba):
    """Quita filas/columnas del borde que son una linea de un solo color."""
    a = rgba
    for _ in range(3):
        cambio = False
        for lado in ("top", "bottom", "left", "right"):
            if min(a.shape[:2]) < 4:
                break
            fila = {"top": a[0], "bottom": a[-1], "left": a[:, 0], "right": a[:, -1]}[lado]
            op = fila[fila[:, 3] > 0][:, :3]
            if len(op) > 0.6 * len(fila) and (op == op[0]).all():
                a = {"top": a[1:], "bottom": a[:-1], "left": a[:, 1:], "right": a[:, :-1]}[lado]
                cambio = True
        if not cambio:
            break
    return a


def _colores_linea(p):
    """Colores de las lineas de grilla dibujadas en la imagen."""
    cols = set()
    for arr in (p, p.transpose(1, 0, 2)):
        for row in arr:
            vals, cnt = np.unique(row.reshape(-1, 3), axis=0, return_counts=True)
            if cnt.max() > 0.9 * len(row):
                c = tuple(int(v) for v in vals[cnt.argmax()])
                if max(c) - min(c) > 60:      # solo colores saturados (no fondo negro/blanco)
                    cols.add(c)
    return cols


def _lineas_imagen(p):
    """Filas y columnas de la imagen que son lineas de grilla: {indice: color}."""
    res = []
    for arr in (p, p.transpose(1, 0, 2)):
        d = {}
        for i, row in enumerate(arr):
            vals, cnt = np.unique(row.reshape(-1, 3), axis=0, return_counts=True)
            if cnt.max() > 0.85 * len(row):
                d[i] = vals[cnt.argmax()]
        res.append(d)
    return res  # (filas, columnas)


def _quitar_fondo_borde(sub, alpha, bg):
    """Quita los pixeles del color de fondo conectados con el borde del recorte."""
    esbg = (np.abs(sub - bg).sum(axis=2) < 9) | ~alpha
    lab, _ = ndimage.label(esbg)
    borde = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    if borde:
        alpha &= ~np.isin(lab, list(borde))
    return alpha


def _sin_restos(alpha):
    """Descarta fragmentos sueltos chicos (restos de lineas o de la pieza vecina)."""
    lab, n = ndimage.label(alpha, structure=np.ones((3, 3)))
    if n <= 1:
        return alpha
    tam = ndimage.sum(alpha, lab, range(1, n + 1))
    grande = tam.max()
    ok = [i + 1 for i, t in enumerate(tam) if t >= 0.03 * grande]
    return np.isin(lab, ok)


def recortar(pic: Image.Image, mask: Image.Image):
    """Devuelve {('w'|'b', 'P'..'K'): Image RGBA recortada}."""
    p = np.array(pic.convert("RGB")).astype(np.int16)
    m = np.array(mask.convert("L")) < 128
    filas = _siluetas(m)
    # sin lineas de grilla para el recorte final
    mc = _sin_grilla(m)
    mc[_corte_filas(mc), :] = False
    lineas = _colores_linea(p)
    filas_l, cols_l = _lineas_imagen(p)
    vals, cnt = np.unique(p.reshape(-1, 3), axis=0, return_counts=True)
    fondo = vals[cnt.argmax()]
    # Algunos juegos traen el dibujo unos pixeles mas chico que la mascara:
    # se completa con fondo para que la alineacion no quede forzada.
    H = max(p.shape[0], m.shape[0]) + 6
    W = max(p.shape[1], m.shape[1]) + 6
    if p.shape[:2] != (H, W):
        q = np.empty((H, W, 3), p.dtype)
        q[...] = fondo
        q[:p.shape[0], :p.shape[1]] = p
        p = q
    out = {}
    for color, fila in zip(("w", "b"), filas):
        for letra, (x0, y0, x1, y1) in zip(ORDEN, fila):
            mk = mc[y0:y1, x0:x1]
            best, bestd = -1e9, (0, 0)
            for dy in range(-5, 6):
                for dx in range(-5, 6):
                    X0, Y0 = x0 + dx, y0 + dy
                    X1, Y1 = X0 + mk.shape[1], Y0 + mk.shape[0]
                    if X0 < 0 or Y0 < 0 or X1 > p.shape[1] or Y1 > p.shape[0]:
                        continue
                    sub = p[Y0:Y1, X0:X1]
                    outside = sub[~mk]
                    if len(outside) < 4:
                        continue
                    vals, cnt = np.unique(outside.reshape(-1, 3), axis=0, return_counts=True)
                    bg = vals[cnt.argmax()]
                    isbg = np.abs(sub - bg).sum(axis=2) < 12
                    score = (isbg & ~mk).mean() + (~isbg & mk).mean() - 2 * (isbg & mk).mean()
                    if score > best:
                        best, bestd = score, (dx, dy)
            dx, dy = bestd
            X0, Y0 = max(0, x0 + dx), max(0, y0 + dy)
            sub = p[Y0:Y0 + mk.shape[0], X0:X0 + mk.shape[1]]
            h, w = sub.shape[:2]
            alpha = mk[:h, :w].copy()
            for c in lineas:
                alpha &= ~(np.abs(sub - np.array(c)).sum(axis=2) < 6)
            # lineas de grilla dibujadas en la imagen (aunque no sean de color saturado)
            for y, c in filas_l.items():
                if Y0 <= y < Y0 + h:
                    alpha[y - Y0] &= ~(np.abs(sub[y - Y0] - c).sum(axis=1) < 6)
            for x, c in cols_l.items():
                if X0 <= x < X0 + w:
                    alpha[:, x - X0] &= ~(np.abs(sub[:, x - X0] - c).sum(axis=1) < 6)
            alpha = _quitar_fondo_borde(sub, alpha, fondo)
            alpha = _sin_restos(alpha)
            rgba = np.dstack([sub.astype(np.uint8), (alpha * 255).astype(np.uint8)])
            out[(color, letra)] = Image.fromarray(_recortar_bordes(rgba), "RGBA")
    return out
