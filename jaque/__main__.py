# Jaque — ajedrez en español. Copyright (C) 2026 Ricardo.
# SPDX-License-Identifier: GPL-3.0-or-later
import sys


def arrancar():
    if "--verificar" in sys.argv:
        from .verificar import verificar
        return verificar()
    if "--preparar-cache" in sys.argv:
        from .preparar import main as preparar
        return preparar(["--cache"])
    from .app import main
    return main()


if __name__ == "__main__":
    sys.exit(arrancar())
