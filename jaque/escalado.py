"""Escalado de gráficos de 8 bits a resoluciones actuales."""
import numpy as np
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap

FILTROS = {
    "mejorado": "Mejorado (Scale2x + suavizado)",
    "suave": "Suave",
    "pixel": "Píxel nítido",
}


def scale2x(a: np.ndarray) -> np.ndarray:
    """Algoritmo EPX/Scale2x sobre un arreglo HxWxC: duplica sin difuminar bordes."""
    p = np.pad(a, ((1, 1), (1, 1), (0, 0)), mode="edge")
    B = p[:-2, 1:-1]; D = p[1:-1, :-2]; E = p[1:-1, 1:-1]; F = p[1:-1, 2:]; H = p[2:, 1:-1]

    def eq(x, y):
        return (x == y).all(axis=2)

    cond = ~eq(B, H) & ~eq(D, F)
    e0 = np.where((cond & eq(D, B))[..., None], D, E)
    e1 = np.where((cond & eq(B, F))[..., None], F, E)
    e2 = np.where((cond & eq(D, H))[..., None], D, E)
    e3 = np.where((cond & eq(H, F))[..., None], F, E)
    h, w, c = a.shape
    out = np.empty((h * 2, w * 2, c), dtype=a.dtype)
    out[0::2, 0::2] = e0; out[0::2, 1::2] = e1
    out[1::2, 0::2] = e2; out[1::2, 1::2] = e3
    return out


def pil_a_qimage(im: Image.Image) -> QImage:
    im = im.convert("RGBA")
    data = im.tobytes("raw", "RGBA")
    q = QImage(data, im.width, im.height, im.width * 4, QImage.Format_RGBA8888)
    return q.copy()  # desacoplar del buffer de Python


def preparar(im: Image.Image, filtro: str) -> QImage:
    """Imagen base para escalar luego con Qt (cacheable)."""
    if filtro == "mejorado":
        a = np.array(im.convert("RGBA"))
        factor = 1
        while factor < 4 and max(a.shape[:2]) * 2 <= 1600:
            a = scale2x(a)
            factor *= 2
        return pil_a_qimage(Image.fromarray(a, "RGBA"))
    return pil_a_qimage(im)


def a_tamano(q: QImage, w: int, h: int, filtro: str, dpr: float = 1.0) -> QPixmap:
    modo = Qt.FastTransformation if filtro == "pixel" else Qt.SmoothTransformation
    pw, ph = max(1, round(w * dpr)), max(1, round(h * dpr))
    pm = QPixmap.fromImage(q.scaled(pw, ph, Qt.IgnoreAspectRatio, modo))
    pm.setDevicePixelRatio(dpr)
    return pm
