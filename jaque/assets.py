"""Acceso a los recursos de una copia original de Chessmaster 4000 Turbo.

Este programa NO incluye ningun recurso del juego: los lee en tiempo de
ejecucion desde el ISO o la carpeta de instalacion del propio usuario.
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
            raise FuenteError("El ISO no contiene la carpeta de Chessmaster 4000.")

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
        if "CM.INI" in up and ("CM4000.EXE" in up or "CMDEFALT.INI" in up):
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
                raise FuenteError("No encontre los archivos de Chessmaster 4000 en esa carpeta.")
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
            d = Path(cache) / "piezas" / f"{codigo}-v2"
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

    def portada(self) -> Image.Image | None:
        return self.imagen("TITLEPIC.BMP").convert("RGB") if self.existe("TITLEPIC.BMP") else None
