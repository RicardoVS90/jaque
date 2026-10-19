"""Sonidos del juego original, convertidos a 16 bits / 44,1 kHz en caché."""
import io
import wave
from pathlib import Path

import numpy as np
from PySide6.QtCore import QUrl

EVENTOS = {
    "mueve_blancas": "WMOVE.WAV", "mueve_negras": "BMOVE.WAV",
    "captura": "CAPTURE.WAV", "jaque": "CHECK.WAV", "mate": "MATE.WAV",
    "enroque": "CASTLE.WAV", "corona": "PROMOTE.WAV", "tablas": "DRAW.WAV",
    "error": "BUZZ.WAV", "campana": "BELL.WAV", "titulo": "TITLE.WAV",
}


def _convertir(datos: bytes, destino: Path):
    with wave.open(io.BytesIO(datos)) as w:
        ch, sw, fr, n = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(n)
    if sw == 1:
        a = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128) / 128
    else:
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    a = a.reshape(-1, ch).mean(axis=1)
    dst_fr = 44100
    t_src = np.arange(len(a)) / fr
    t_dst = np.arange(int(len(a) * dst_fr / fr)) / dst_fr
    b = np.interp(t_dst, t_src, a)
    pcm = (np.clip(b, -1, 1) * 32000).astype(np.int16)
    with wave.open(str(destino), "wb") as o:
        o.setnchannels(1); o.setsampwidth(2); o.setframerate(dst_fr)
        o.writeframes(pcm.tobytes())


def convertir_todos(recursos, cache: Path):
    cache.mkdir(parents=True, exist_ok=True)
    for arch in EVENTOS.values():
        dst = cache / arch.lower()
        if recursos.existe(arch) and not dst.exists():
            _convertir(recursos.leer(arch), dst)


class Sonidos:
    def __init__(self, recursos, cache: Path):
        self.activos = True
        self._efectos = {}
        import os
        if os.environ.get("JAQUE_SIN_SONIDO"):
            return
        try:
            from PySide6.QtMultimedia import QMediaDevices, QSoundEffect
            if not QMediaDevices.audioOutputs():
                return
        except Exception:
            return
        cache.mkdir(parents=True, exist_ok=True)
        for ev, arch in EVENTOS.items():
            if not recursos.existe(arch):
                continue
            dst = cache / (arch.lower())
            try:
                if not dst.exists():
                    _convertir(recursos.leer(arch), dst)
                e = QSoundEffect()
                e.setSource(QUrl.fromLocalFile(str(dst)))
                e.setVolume(0.8)
                self._efectos[ev] = e
            except Exception:
                pass

    def tocar(self, evento: str):
        if self.activos and evento in self._efectos:
            self._efectos[evento].play()
