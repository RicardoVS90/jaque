# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Acceso a los recursos del juego original del usuario.

Se leen del paquete de recursos preparado (~/.local/share/jaque/recursos),
o directamente del ISO o de la carpeta del juego.
"""
from __future__ import annotations

import configparser
import io
import os
import re
from pathlib import Path

from PIL import Image


class FuenteError(Exception):
    pass


class _Directorio:
    """Carpeta que contiene CM.INI (busqueda sin distinguir mayusculas)."""

    def __init__(self, raiz: Path):
        self.raiz = raiz
        self._idx = {p.name.upper(): p for p in raiz.iterdir() if p.is_file()}

    def listar(self):
        return list(self._idx)

    def leer(self, nombre: str) -> bytes:
        p = self._idx.get(nombre.upper())
        if p is None:
            raise FileNotFoundError(nombre)
        return p.read_bytes()


class _Iso:
    """Imagen ISO 9660/Joliet del CD original."""

    def __init__(self, ruta: Path):
        import pycdlib

        self.iso = pycdlib.PyCdlib()
        self.iso.open(str(ruta))
        try:
            self.iso.get_record(joliet_path="/")
            self.clave = "joliet_path"
        except Exception:
            self.clave = "iso_path"
        self.dir = None
        self._idx = {}
        for root, _dirs, files in self.iso.walk(**{self.clave: "/"}):
            nombres = {f.split(";")[0].upper(): f for f in files}
            if "CM.INI" in nombres and "CM4000.EXE" in nombres:
                self.dir = root.rstrip("/")
                self._idx = nombres
                break
        if self.dir is None:
            raise FuenteError("Ese ISO no contiene los archivos del juego.")

    def listar(self):
        return list(self._idx)

    def leer(self, nombre: str) -> bytes:
        real = self._idx.get(nombre.upper())
        if real is None:
            raise FileNotFoundError(nombre)
        buf = io.BytesIO()
        self.iso.get_file_from_iso_fp(buf, **{self.clave: f"{self.dir}/{real}"})
        return buf.getvalue()


def _buscar_dir(raiz: Path) -> Path | None:
    for dirpath, _dirs, files in os.walk(raiz):
        up = {f.upper() for f in files}
        if "CM.INI" in up and ("CM4000.EXE" in up or "CMDEFALT.INI" in up or "JAQUE.RECURSOS" in up):
            return Path(dirpath)
    return None


class Recursos:
    """Punto unico de acceso a tableros, piezas, sonidos y rivales."""

    def __init__(self, ruta: str | os.PathLike):
        ruta = Path(ruta).expanduser()
        if not ruta.exists():
            raise FuenteError(f"No existe: {ruta}")
        if ruta.is_file():
            self.src = _Iso(ruta)
        else:
            d = _buscar_dir(ruta)
            if d is None:
                raise FuenteError("No encontré los archivos del juego en esa carpeta.")
            self.src = _Directorio(d)
        self.ruta = ruta
        self._ini = None

    # --- utilidades -------------------------------------------------------
    def existe(self, nombre: str) -> bool:
        return nombre.upper() in self.src.listar()

    def leer(self, nombre: str) -> bytes:
        return self.src.leer(nombre)

    def imagen(self, nombre: str) -> Image.Image:
        im = Image.open(io.BytesIO(self.leer(nombre)))
        im.load()
        return im

    @property
    def ini(self) -> configparser.ConfigParser:
        if self._ini is None:
            cp = configparser.ConfigParser(interpolation=None, strict=False)
            cp.optionxform = str.lower
            texto = self.leer("CMDEFALT.INI" if self.existe("CMDEFALT.INI") else "CM.INI")
            cp.read_string(texto.decode("latin-1"))
            self._ini = cp
        return self._ini

    # --- tableros ---------------------------------------------------------
    NOMBRES_TABLERO = {
        "2DWDBRD.BMP": "Madera 2D (grande)",
        "2DWDSBRD.BMP": "Madera 2D (chico)",
        "2DGRNBRD.BMP": "Mármol verde 2D",
        "2DBLUBRD.BMP": "Mármol azul 2D",
        "3DWDBRD.BMP": "Madera 3D",
        "3DGRNBRD.BMP": "Mármol verde 3D",
        "3DBLUBRD.BMP": "Mármol azul 3D",
        "EBNIBRD.BMP": "Ébano y marfil 3D",
        "CHINBRD.BMP": "Teca china 3D",
        "METALBRD.BMP": "Metal 3D",
        "DALIBRD.BMP": "Paisaje surrealista",
    }

    def tableros_2d(self):
        """[(archivo, nombre_es, centro_x, centro_y, lado)] para tableros planos."""
        out = []
        for sec in self.ini.sections():
            if not sec.upper().startswith("2D") or not sec.upper().endswith("BRD.BMP"):
                continue
            s = self.ini[sec]
            if "size" not in s:
                continue
            arch = sec.upper()
            if not self.existe(arch):
                continue
            out.append((arch, self.NOMBRES_TABLERO.get(arch, arch),
                        int(s["center_x"]), int(s["center_y"]), int(s["size"])))
        return out

    def tablero_2d(self, archivo: str) -> Image.Image:
        """Recorta solo las 64 casillas del BMP del tablero."""
        for arch, _n, cx, cy, lado in self.tableros_2d():
            if arch == archivo.upper():
                im = self.imagen(arch).convert("RGB")
                h = lado / 2
                return im.crop((round(cx - h), round(cy - h), round(cx + h), round(cy + h)))
        raise KeyError(archivo)

    # Esquinas de las 64 casillas en cada BMP 3D (a1, h1, h8, a8), en píxeles.
    # Obtenidas ajustando una homografía al damero de cada imagen original.
    ESQUINAS_3D = {
        "3DWDBRD.BMP": [(38.0, 264.4), (568.6, 264.7), (516.8, 12.6), (89.2, 12.8)],
        "3DGRNBRD.BMP": [(27.4, 260.6), (560.0, 260.1), (509.3, 10.5), (77.4, 10.5)],
        "3DBLUBRD.BMP": [(24.6, 260.2), (558.6, 259.7), (509.2, 10.8), (77.8, 10.4)],
        "EBNIBRD.BMP": [(49.7, 269.4), (582.1, 269.5), (532.8, 21.2), (100.4, 21.4)],
        "CHINBRD.BMP": [(39.9, 259.6), (568.3, 259.3), (521.0, 10.9), (88.7, 10.5)],
        "METALBRD.BMP": [(37.9, 261.2), (566.1, 261.2), (520.3, 14.2), (87.1, 14.0)],
        "DALIBRD.BMP": [(75.4, 321.0), (613.8, 78.0), (303.1, 0.6), (0.8, 39.1)],
    }

    def tableros_3d(self):
        out = []
        for arch in self.ESQUINAS_3D:
            if self.existe(arch):
                out.append((arch, self.NOMBRES_TABLERO.get(arch, arch)))
        return out

    def tablero_3d(self, archivo: str) -> dict:
        """Imagen RGBA del tablero (fondo transparente), esquinas y fondo de escena."""
        arch = archivo.upper()
        sec = next((s for s in self.ini.sections() if s.upper() == arch), None)
        cfg = self.ini[sec] if sec else {}
        im = self.imagen(arch).convert("RGBA")
        masc = cfg.get("mask", "").strip('"').upper()
        if masc and self.existe(masc):
            m = self.imagen(masc).convert("L").resize(im.size)
            alpha = m.point(lambda v: 255 if v < 128 else 0)
            im.putalpha(alpha)
        fondo, modo = None, "estirar"
        wb = cfg.get("wayback", "").strip('"').upper()
        if wb and self.existe(wb):
            fondo = self.imagen(wb).convert("RGB")
            if fondo.width <= 32:
                modo = "estirar"          # degradé vertical
            elif fondo.width >= 600:
                modo = "cubrir"           # escena completa (Dalí)
            else:
                modo = "mosaico"
        return {"imagen": im, "esquinas": self.ESQUINAS_3D[arch], "fondo": fondo, "modo": modo}

    # --- piezas -----------------------------------------------------------
    NOMBRES_PIEZAS = {
        "2DL": "Staunton clasico", "2DM": "Staunton mini", "2DF": "Fantasía",
        "2DR": "Formas abstractas", "2DA": "Letras", "3DL": "Staunton 3D",
        "3DM": "Staunton 3D chico", "3DC": "Chino", "3DD": "Moderno de acero",
        "3DF": "Fantasía 3D", "3DI": "Insectos", "3DJ": "Dinosaurios",
        "3DK": "Tuercas y tubos", "3DN": "Napoleónico", "3DO": "Criaturas marinas",
        "3DR": "Formas abstractas 3D", "3DA": "Letras 3D",
    }

    def juegos_piezas(self):
        out = []
        for n in sorted(self.src.listar()):
            m = re.fullmatch(r"256_(\w{3})P\.BMP", n)
            if m and self.existe(f"256_{m.group(1)}M.BMP"):
                c = m.group(1)
                out.append((c, self.NOMBRES_PIEZAS.get(c, c)))
        return out

    def piezas(self, codigo: str, cache: Path | None = None):
        """Sprites RGBA por (color, letra). El recorte se guarda en caché local."""
        from .sprites import ORDEN, recortar

        pic, msk = f"256_{codigo}P.BMP", f"256_{codigo}M.BMP"
        claves = [(c, l) for c in "wb" for l in ORDEN]
        if cache is not None:
            d = Path(cache) / "piezas" / f"{codigo}-v4"
            archivos = {k: d / f"{k[0]}_{k[1]}.png" for k in claves}
            if all(p.exists() for p in archivos.values()):
                out = {}
                for k, p in archivos.items():
                    im = Image.open(p)
                    im.load()
                    out[k] = im
                return out
        out = recortar(self.imagen(pic), self.imagen(msk))
        if cache is not None and len(out) == 12:
            d.mkdir(parents=True, exist_ok=True)
            for k, im in out.items():
                im.save(archivos[k])
        return out

    # --- otros ------------------------------------------------------------
    def rivales(self):
        from .rivales import leer_cmx

        out = []
        for n in sorted(self.src.listar()):
            if n.endswith(".CMX"):
                try:
                    out.append(leer_cmx(n, self.leer(n)))
                except Exception:
                    pass
        return out

    @staticmethod
    def portada():
        """(imagen, es_la_de_jaque). Se puede reemplazar con
        ~/.local/share/jaque/portada.png (o .jpg)."""
        from .rutas import DATOS as base
        propia = Path(__file__).resolve().parent / "datos" / "portada.png"
        for p in (base / "portada.png", base / "portada.jpg", base / "portada.jpeg", propia):
            if p.exists():
                try:
                    im = Image.open(p)
                    im.load()
                    return im.convert("RGB"), p == propia
                except Exception:
                    pass
        return None, False
