"""Genera jaque/datos/aperturas.json (nombres de aperturas en español) a partir de eco_en.json.
Origen de los datos: paquete npm chess-openings 0.1.1 (Guido Flohr, licencia WTFPL)."""
import json, re, sys
from collections import Counter

src, dst = sys.argv[1], sys.argv[2]
d = json.load(open(src, encoding="utf-8"))

# Frases de varias palabras -> una ficha.  (tipo, texto)  tipo: 'mod' = va después del núcleo tal cual
FRASES = [
    ("Main Line", ("head", "línea principal", "f")),
    ("Move Order", ("head", "orden de jugadas", "m")),
    ("Grand Prix", ("prop", "Grand Prix")),
    ("Cambridge Springs", ("prop", "Cambridge Springs")),
    ("King's Indian", ("adj", "indio de rey", "india de rey")),
    ("Queen's Indian", ("adj", "indio de dama", "india de dama")),
    ("Two Knights", ("mod", "de los dos caballos")),
    ("Three Knights", ("mod", "de los tres caballos")),
    ("Four Knights", ("mod", "de los cuatro caballos")),
    ("Two Pawns", ("mod", "de los dos peones")),
    ("Three Pawns", ("mod", "de los tres peones")),
    ("Four Pawns", ("mod", "de los cuatro peones")),
    ("Double Fianchetto", ("mod", "del doble fianchetto")),
    ("King's Knight", ("mod", "del caballo de rey")),
    ("Queen's Knight", ("mod", "del caballo de dama")),
    ("King's Pawn", ("mod", "del peón de rey")),
    ("Queen's Pawn", ("mod", "del peón de dama")),
    ("Queen's Bishop", ("mod", "del alfil de dama")),
    ("King's Bishop", ("mod", "del alfil de rey")),
    ("Poisoned Pawn", ("mod", "del peón envenenado")),
    ("Wing Gambit", ("head2", "gambito del flanco", "m")),
    ("St. George", ("prop", "San Jorge")),
    ("Ruy Lopez", ("prop", "Ruy López")),
    ("Lasker Simul Special", ("head", "especial de simultáneas de Lasker", "m")),
    ("English Orangutan", ("head", "orangután inglés", "m")),
    ("El Columpio", ("prop", "El Columpio")),
    ("Max Lange", ("prop", "Max Lange")),
]

# Sustantivos núcleo: (español, género)
NUCLEOS = {
    "Variation": ("variante", "f"), "Variations": ("variantes", "f"), "Attack": ("ataque", "m"),
    "Gambit": ("gambito", "m"), "Countergambit": ("contragambito", "m"), "Defense": ("defensa", "f"),
    "Line": ("línea", "f"), "System": ("sistema", "m"), "Formation": ("formación", "f"),
    "Trap": ("trampa", "f"), "Opening": ("apertura", "f"), "Game": ("partida", "f"),
    "Sacrifice": ("sacrificio", "m"), "Counterattack": ("contraataque", "m"), "Bind": ("esquema", "m"),
    "Retreat": ("retirada", "f"), "Pin": ("clavada", "f"), "Endgame": ("final", "m"),
    "Check": ("jaque", "m"), "Invitation": ("invitación", "f"), "Hedgehog": ("erizo", "m"),
    "Dragon": ("dragón", "m"), "Exchange": ("cambio", "m"), "Advance": ("avance", "m"),
    "Fianchetto": ("fianchetto", "m"), "Stonewall": ("Stonewall", "m"), "Bayonet": ("bayoneta", "f"),
    "Spike": ("espiga", "f"), "Claw": ("garra", "f"), "Hunt": ("cacería", "f"),
    "Transfer": ("traslado", "m"), "Fingerslip": ("desliz", "m"), "Hybrid": ("híbrido", "m"),
    "Pawn": ("peón", "m"), "Pawns": ("peones", "m"), "Knight": ("caballo", "m"), "Knights": ("caballos", "m"),
    "Bishop": ("alfil", "m"), "Queen": ("dama", "f"), "King": ("rey", "m"), "Center": ("centro", "m"),
    "Lion": ("león", "m"), "Rat": ("rata", "f"), "Vulture": ("buitre", "m"), "Kangaroo": ("canguro", "m"),
    "Hippopotamus": ("hipopótamo", "m"), "Elephant": ("elefante", "m"), "Pterodactyl": ("pterodáctilo", "m"),
    "Special": ("especial", "m"), "Indian": ("india", "f"), "Accelerated": None,
}
# Adjetivos: (masc, fem)
ADJ = {
    "Classical": ("clásico", "clásica"), "Modern": ("moderno", "moderna"), "Closed": ("cerrado", "cerrada"),
    "Open": ("abierto", "abierta"), "Normal": ("normal", "normal"), "Symmetrical": ("simétrico", "simétrica"),
    "Accepted": ("aceptado", "aceptada"), "Declined": ("rehusado", "rehusada"), "Orthodox": ("ortodoxo", "ortodoxa"),
    "Reversed": ("invertido", "invertida"), "Accelerated": ("acelerado", "acelerada"), "Deferred": ("diferido", "diferida"),
    "Delayed": ("retrasado", "retrasada"), "Quiet": ("tranquilo", "tranquila"), "Central": ("central", "central"),
    "Traditional": ("tradicional", "tradicional"), "Old": ("antiguo", "antigua"), "Positional": ("posicional", "posicional"),
    "Early": ("temprano", "temprana"), "Long": ("largo", "larga"), "Short": ("corto", "corta"), "New": ("nuevo", "nueva"),
    "Full": ("completo", "completa"), "Flexible": ("flexible", "flexible"), "Standard": ("estándar", "estándar"),
    "Kingside": ("del flanco de rey", "del flanco de rey"), "Queenside": ("del flanco de dama", "del flanco de dama"),
    "Eastern": ("oriental", "oriental"), "Western": ("occidental", "occidental"), "East": ("oriental", "oriental"),
    "Main": ("principal", "principal"), "Double": ("doble", "doble"), "Semi-Classical": ("semiclásico", "semiclásica"),
    "Hyperaccelerated": ("hiperacelerado", "hiperacelerada"), "Wayward": ("caprichoso", "caprichosa"),
    "Global": ("global", "global"),
    # gentilicios
    "English": ("inglés", "inglesa"), "French": ("francés", "francesa"), "Sicilian": ("siciliano", "siciliana"),
    "Italian": ("italiano", "italiana"), "Spanish": ("español", "española"), "Scotch": ("escocés", "escocesa"),
    "Russian": ("ruso", "rusa"), "Dutch": ("holandés", "holandesa"), "Polish": ("polaco", "polaca"),
    "Czech": ("checo", "checa"), "Danish": ("danés", "danesa"), "Hungarian": ("húngaro", "húngara"),
    "Austrian": ("austriaco", "austriaca"), "Swiss": ("suizo", "suiza"), "Norwegian": ("noruego", "noruega"),
    "Portuguese": ("portugués", "portuguesa"), "Latvian": ("letón", "letona"), "Irish": ("irlandés", "irlandesa"),
    "Mexican": ("mexicano", "mexicana"), "Australian": ("australiano", "australiana"), "American": ("americano", "americana"),
    "Siberian": ("siberiano", "siberiana"), "Catalan": ("catalán", "catalana"), "Scandinavian": ("escandinavo", "escandinava"),
    "Slav": ("eslavo", "eslava"), "Semi-Slav": ("semieslavo", "semieslava"), "Vienna": ("vienés", "vienesa"),
    "Indian": ("indio", "india"), "Nimzo-Indian": ("nimzoindio", "nimzoindia"), "Bogo-Indian": ("bogoindio", "bogoindia"),
    "Anglo-Indian": ("angloindio", "angloindia"), "Anglo-Slav": ("angloeslavo", "angloeslava"),
    "Anglo-Dutch": ("angloholandés", "angloholandesa"), "Anglo-Scandinavian": ("angloescandinavo", "angloescandinava"),
    "Neo-Catalan": ("neocatalán", "neocatalana"), "Yugoslav": ("yugoslavo", "yugoslava"),
    "Venice": ("veneciano", "veneciana"), "Moscow": ("de Moscú", "de Moscú"), "Paris": ("de París", "de París"),
    "Brooklyn": ("de Brooklyn", "de Brooklyn"), "Leningrad": ("Leningrado", "Leningrado"),
    "Stockholm": ("de Estocolmo", "de Estocolmo"), "Warsaw": ("de Varsovia", "de Varsovia"),
    "London": ("Londres", "Londres"), "Cambridge": ("Cambridge", "Cambridge"),
    "Petersburg": ("de San Petersburgo", "de San Petersburgo"), "Valencian": ("valenciano", "valenciana"),
    "Poisoned": ("envenenado", "envenenada"), "Pseudo": ("pseudo", "pseudo"),
    "Two": ("de dos", "de dos"), "Three": ("de tres", "de tres"), "Four": ("de cuatro", "de cuatro"),
}
MOD = {"King's": "de rey", "Queen's": "de dama", "Bishop's": "de alfil", "Knight's": "de caballo",
       "Lion's": "del león", "with": "con", "the": "", "The": ""}
FAMILIAS_FIJAS = {
    "Ruy Lopez": "Apertura española (Ruy López)", "Italian Game": "Apertura italiana",
    "Center Game": "Apertura del centro", "Center Game Accepted": "Apertura del centro aceptada",
    "Scotch Game": "Apertura escocesa", "Vienna Game": "Partida vienesa", "Saragossa Opening": "Apertura Zaragoza",
    "Dresden Opening": "Apertura Dresde", "Amsterdam Attack": "Ataque Ámsterdam", "Amazon Attack": "Ataque Amazonas",
    "Paleface Attack": "Ataque Rostro Pálido", "Petrov's Defense": "Defensa Petrov",
    "Anderssen's Opening": "Apertura Anderssen", "Queen's Indian Accelerated": "India de dama acelerada",
    "Slav Indian": "India eslava", "Queen's Pawn": "Peón de dama", "Pseudo Queen's Indian Defense": "Defensa pseudoindia de dama", "London System": "Sistema Londres",
    "Formation": "Formación", "Queen's Pawn, Mengarini Attack": "Peón de dama, ataque Mengarini",
}
SAN = re.compile(r"^([KQRBN])([a-h]?[1-8]?x?[a-h][1-8])$")
LETRA = {"K": "R", "Q": "D", "R": "T", "B": "A", "N": "C"}


def fichas(texto):
    for en, f in FRASES:
        texto = texto.replace(en, "\x00" + str(FRASES.index((en, f))) + "\x00")
    out = []
    for t in re.split(r"(\x00\d+\x00| )", texto):
        if not t or t == " ":
            continue
        if t.startswith("\x00"):
            out.append(FRASES[int(t.strip("\x00"))][1])
        else:
            out.append(t)
    return out


def traducir_segmento(seg):
    toks = fichas(seg.strip())
    # 'with X' -> 'con X' al final
    if "with" in toks:
        i = toks.index("with")
        cola = "con " + " ".join(traducir_san(t) for t in toks[i + 1:] if isinstance(t, str))
        if any(isinstance(t, tuple) for t in toks[i + 1:]):
            cola = "con " + traducir_segmento(" ".join(x if isinstance(x, str) else x[1] for x in toks[i + 1:]))
        toks = toks[:i]
    else:
        cola = ""
    # núcleo = último sustantivo núcleo
    idx = None
    for i, t in enumerate(toks):
        if (isinstance(t, tuple) and t[0] in ("head", "head2")) or (isinstance(t, str) and NUCLEOS.get(t)):
            idx = i
    if idx is None:
        props = [palabra(t, "f") for t in toks if isinstance(t, str) and t not in ADJ and t not in MOD]
        otras = [palabra(t, "f") for t in toks if not (isinstance(t, str) and t not in ADJ and t not in MOD)]
        res = " ".join(p for p in props + otras if p)
    else:
        n = toks[idx]
        if isinstance(n, tuple):
            nucleo, gen = n[1], n[2]
        else:
            nucleo, gen = NUCLEOS[n]
        pre = toks[:idx]
        post = toks[idx + 1:]
        adjs, props, mods = [], [], []
        for t in reversed(pre):
            if isinstance(t, tuple):
                if t[0] == "adj":
                    adjs.append(t[1] if gen == "m" else t[2])
                elif t[0] == "mod":
                    mods.append(t[1])
                elif t[0] == "prop":
                    props.insert(0, t[1])
                else:
                    mods.append(("del " if t[2] == "m" else "de la ") + t[1])
            elif t in ADJ:
                adjs.append(ADJ[t][0 if gen == "m" else 1])
            elif t in MOD:
                if MOD[t]:
                    mods.append(MOD[t])
            elif NUCLEOS.get(t):
                s, g = NUCLEOS[t]
                mods.append(("del " if g == "m" else "de la ") + s)
            else:
                props.insert(0, traducir_san(t))
        if nucleo.endswith("s") and " " not in nucleo:
            adjs = [a + ("s" if a[-1] in "aeo" else "es") for a in adjs]
        res = nucleo
        # orden: núcleo + nombres propios + adjetivos + complementos
        if props:
            res += " " + " ".join(props)
        if adjs:
            res += " " + " ".join(adjs)
        if mods:
            res += " " + " ".join(reversed(mods))
        for t in post:
            p = palabra(t, gen)
            if p:
                res += " " + p
    if cola:
        res += " " + cola
    return re.sub(r"\s+", " ", res).strip()


def palabra(t, gen):
    if isinstance(t, tuple):
        if t[0] == "adj":
            return t[1] if gen == "m" else t[2]
        return t[1]
    if t in ADJ:
        return ADJ[t][0 if gen == "m" else 1]
    if t in MOD:
        return MOD[t]
    if NUCLEOS.get(t):
        return NUCLEOS[t][0]
    return traducir_san(t)


def traducir_san(t):
    if t.endswith("'s") and t[:1].isupper():
        t = t[:-2]
    m = SAN.match(t)
    if m:
        return LETRA[m.group(1)] + m.group(2)
    return t


def traducir(nombre):
    if ":" in nombre:
        fam, var = nombre.split(":", 1)
    else:
        fam, var = nombre, ""
    if fam in FAMILIAS_FIJAS:
        f = FAMILIAS_FIJAS[fam]
    else:
        segs = fam.split(",")
        f = ", ".join(traducir_segmento(s) for s in segs)
        f = f[:1].upper() + f[1:]
    if not var.strip():
        return f
    v = ", ".join(traducir_segmento(s) for s in var.split(","))
    return f + ": " + v


out = {}
for epd, (eco, nombre) in d.items():
    out[epd] = [eco, traducir(nombre)]
json.dump({"fuente": "chess-openings 0.1.1 (Guido Flohr), licencia WTFPL; traducción al español de Jaque",
           "aperturas": out}, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
if "-v" in sys.argv:
    import random
    random.seed(int(sys.argv[-1]) if sys.argv[-1].isdigit() else 1)
    fams = sorted({traducir(n.split(":")[0]) + "  <=  " + n.split(":")[0] for _, n in d.values()})
    print("\n".join(fams))
    print("-----")
    for epd in random.sample(list(d), 60):
        print(d[epd][1], " ==> ", out[epd][1])
