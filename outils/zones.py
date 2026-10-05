# Génère les zones cliquables (chemins SVG) de chaque planche à partir des images sources.
#
# Principe : chaque pièce est une région colorée délimitée par des traits. On repère la
# composante connexe qui contient un point « graine » de la pièce, on lui ajoute les
# éventuels polygones dessinés à la main (zones non fermées sur la planche), on la fait
# grossir de quelques pixels pour couvrir les traits de séparation, on bouche les trous
# laissés par le texte, puis on vectorise le contour.
#
# Usage : python outils/zones.py            -> écrit app/data/zones.js + app/img/* + outils/controle/*.png
import json
import os
import sys

import cv2
import numpy as np

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(RACINE, "sources")
APP = os.path.join(RACINE, "app")
CONTROLE = os.path.join(RACINE, "outils", "controle")

# Graines = points (x, y) en pixels de l'image source, à l'intérieur de chaque pièce.
# Plusieurs graines = une pièce dessinée en plusieurs morceaux (texte qui coupe la zone, etc.).
PLANCHES = {
    "boeuf": {
        "source": "boeuf.png", "image": "boeuf.png", "mode": "rouge", "fermeture": 3, "croissance": 4,
        "graines": {
            "langue": [(48, 183)], "plat-de-joue": [(92, 184)], "collier": [(196, 82)],
            "gros-bout-de-poitrine": [(216, 312)], "basses-cotes": [(337, 120)],
            "cotes-entrecotes": [(380, 87)], "faux-filet": [(499, 88)], "rumsteck": [(551, 123)],
            "filet": [(526, 180)], "onglet": [(592, 186), (563, 189)], "aiguillette-baronne": [(623, 199)],
            "hampe": [(605, 230)], "bavette-de-flanchet": [(517, 216)], "bavette-d-aloyau": [(634, 288)],
            "flanchet": [(520, 312)], "plat-de-cotes": [(378, 240)], "tendron": [(474, 287)],
            "jumeau-a-bifteck": [(247, 157)], "paleron": [(301, 213)], "macreuse-a-bifteck": [(334, 266)],
            "jumeau-a-pot-au-feu": [(252, 326)], "macreuse-a-pot-au-feu": [(311, 301)],
            "gite-avant": [(285, 351)], "tende-de-tranche": [(718, 158)],
            "tranche-grasse": [(665, 261), (666, 296)], "araignee": [(696, 234), (705, 289)],
            "gite-a-la-noix": [(732, 210)], "rond-de-gite": [(772, 199)],
            "gite-arriere": [(732, 327), (759, 332)],
        },
        "manuel": {},
    },
    "veau": {
        "source": "veau.png", "image": "veau.png", "mode": "blanc", "fermeture": 3, "croissance": 3,
        "graines": {
            "quasi": [(150, 159)], "longe": [(268, 117)], "cote-premiere": [(312, 210)],
            "cote-seconde": [(430, 114)], "cote-decouverte": [(552, 89)], "collier": [(589, 131)],
            "epaule": [(492, 318)], "noix": [(116, 309)], "filet": [(235, 250)],
            "flanchet": [(246, 346)], "tendron": [(302, 341)], "poitrine": [(387, 344), (606, 351)],
            "jarret-arriere": [(71, 374)], "jarret-avant": [(504, 410)],
        },
        "manuel": {},
        # La planche d'origine montre la longe déjà surlignée en rouge : on la repeint en blanc
        # pour qu'aucune pièce ne paraisse sélectionnée avant le clic.
        "repeindre": "longe",
    },
    "porc": {
        "source": "porc.jpeg", "image": "porc.jpg", "mode": "rose", "fermeture": 3, "croissance": 4,
        "graines": {
            "jambon": [(190, 249)], "pointe-de-filet": [(191, 172)], "cotes-de-filet": [(256, 162)],
            "filet": [(258, 192)], "carre-de-cotes": [(309, 179), (302, 209), (331, 179)],
            "echine": [(386, 183)], "palette": [(384, 214)], "epaule": [(375, 242)],
            # (293, 257) : petite zone sans nom sous le travers, rattachée à la poitrine (hypothèse).
            "poitrine": [(247, 283), (293, 257)], "plat-de-cotes": [(267, 229)], "travers": [(297, 231)],
            "jarret-arriere": [(189, 287)], "jarret-avant": [(340, 288)],
            "pied": [(152, 331), (194, 327), (344, 324), (306, 324)], "tete": [(425, 239)],
        },
        # La queue en tire-bouchon est trop fine pour être détectée : cercle posé à la main.
        "manuel": {"queue": [[(96, 170), (104, 164), (114, 164), (121, 171), (123, 181), (119, 190),
                              (127, 193), (125, 199), (113, 197), (102, 193), (95, 185), (94, 177)]]},
    },
    "agneau": {
        "source": "agneau.jpeg", "image": "agneau.jpg", "mode": "clair", "fermeture": 5, "croissance": 5,
        "graines": {
            "gigot": [(93, 63), (47, 72)], "selle": [(91, 28)], "filet": [(153, 55)], "carre": [(190, 63)],
            "epaule": [(240, 131)], "poitrine": [(175, 141)], "collet": [(308, 168)], "tete": [(340, 230)],
        },
        # Zones dont les pointillés ne se referment pas sur la gravure : tracées à la main.
        "manuel": {
            # Pattes hachurées : la souris (bas du gigot) et le jarret avant (bas de l'épaule).
            "gigot": [[(50, 106), (68, 108), (84, 135), (82, 175), (80, 214), (56, 214), (54, 175), (49, 140)]],
            "epaule": [[(238, 158), (262, 150), (277, 163), (272, 209), (248, 209), (240, 188)]],
            "haut-de-cotelettes":[[(174, 76), (217, 80), (210, 92), (203, 111), (172, 111), (171, 92)]],
            "pieds": [
                [(57, 217), (79, 217), (81, 234), (90, 249), (72, 256), (60, 246)],
                [(99, 214), (119, 212), (126, 234), (146, 250), (130, 258), (110, 246)],
                [(203, 209), (223, 209), (226, 235), (236, 252), (213, 258), (205, 240)],
                [(248, 211), (269, 213), (281, 232), (300, 245), (285, 253), (262, 241)],
            ],
        },
    },
}


def lire(chemin):
    im = cv2.imdecode(np.fromfile(chemin, np.uint8), cv2.IMREAD_UNCHANGED)
    alpha = im[:, :, 3] if im.ndim == 3 and im.shape[2] == 4 else None
    if alpha is not None:
        a = alpha[:, :, None] / 255.0
        plat = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
    else:
        plat = im[:, :, :3]
    return im, plat, alpha


def masques(plat, alpha, mode):
    b, g, r = [plat[:, :, i].astype(int) for i in range(3)]
    if mode == "rouge":
        interieur = (r - np.maximum(g, b)) > 60
        silhouette = interieur | (np.minimum(np.minimum(r, g), b) > 200)
        if alpha is not None:
            silhouette &= alpha > 0
    elif mode == "blanc":
        interieur = (np.minimum(np.minimum(r, g), b) > 200) | ((r - np.maximum(g, b)) > 60)
        silhouette = alpha > 0
    elif mode == "rose":
        interieur = (r > 200) & (g < 196) & (r - g > 40)
        silhouette = (r - g) > 12
    elif mode == "clair":
        interieur = np.minimum(np.minimum(r, g), b) > 140
        k = cv2.morphologyEx(interieur.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
        silhouette = remplir_trous(k.astype(bool))
    else:
        raise ValueError(mode)
    return interieur.astype(np.uint8), silhouette


def remplir_trous(m):
    m8 = m.astype(np.uint8) * 255
    h, w = m8.shape
    f = m8.copy()
    cv2.floodFill(f, np.zeros((h + 2, w + 2), np.uint8), (0, 0), 255)
    return m | (f == 0)


def graine_vers_composante(lab, x, y, rayon=8):
    if lab[y, x]:
        return lab[y, x]
    for r in range(1, rayon + 1):
        zone = lab[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
        nz = zone[zone > 0]
        if nz.size:
            return np.bincount(nz).argmax()
    raise RuntimeError(f"graine ({x},{y}) hors de toute zone")


def chemin_svg(masque):
    m8 = masque.astype(np.uint8) * 255
    contours, _ = cv2.findContours(m8, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    morceaux = []
    for c in contours:
        if cv2.contourArea(c) < 12:
            continue
        a = cv2.approxPolyDP(c, 0.8, True).reshape(-1, 2)
        if len(a) < 3:
            continue
        morceaux.append("M" + "L".join(f"{x},{y}" for x, y in a) + "Z")
    return "".join(morceaux)


def traiter(nom, cfg):
    im, plat, alpha = lire(os.path.join(SOURCES, cfg["source"]))
    h, w = plat.shape[:2]
    interieur, silhouette = masques(plat, alpha, cfg["mode"])
    k = cfg["fermeture"]
    erode = cv2.erode(interieur, np.ones((k, k), np.uint8)) if k else interieur
    n, lab, stats, _ = cv2.connectedComponentsWithStats(erode, connectivity=4)

    ids = list(cfg["graines"]) + [p for p in cfg["manuel"] if p not in cfg["graines"]]
    L = np.full((h, w), -1, np.int32)
    deja = {}
    for i, piece in enumerate(ids):
        for (x, y) in cfg["graines"].get(piece, []):
            comp = graine_vers_composante(lab, x, y)
            if stats[comp, cv2.CC_STAT_AREA] > 0.25 * w * h:
                raise RuntimeError(f"{nom}/{piece}: la graine ({x},{y}) tombe dans le fond")
            if comp in deja and deja[comp] != piece:
                raise RuntimeError(f"{nom}: {piece} et {deja[comp]} partagent la même zone")
            deja[comp] = piece
            L[lab == comp] = i
    for piece, polys in cfg["manuel"].items():
        i = ids.index(piece)
        for p in polys:
            tmp = np.zeros((h, w), np.uint8)
            cv2.fillPoly(tmp, [np.array(p, np.int32)], 1)
            L[(tmp > 0) & silhouette] = i

    # Croissance : couvre les traits de séparation (sans déborder de la silhouette).
    noyau = np.ones((3, 3), np.uint8)
    for _ in range(cfg["croissance"]):
        libre = (L == -1) & silhouette
        if not libre.any():
            break
        ajout = np.full((h, w), -1, np.int32)
        for i in range(len(ids)):
            d = cv2.dilate((L == i).astype(np.uint8), noyau).astype(bool) & libre & (ajout == -1)
            ajout[d] = i
        L = np.where(ajout >= 0, ajout, L)

    # Petits morceaux de couleur isolés par le texte (ex. entre deux mots) : rattachés à la
    # pièce qui les borde le plus. Un morceau qui ne touche aucune pièce (ex. la queue) reste libre.
    nr, lr = cv2.connectedComponents(((interieur > 0) & (L == -1)).astype(np.uint8), connectivity=4)
    for t in range(1, nr):
        zone = lr == t
        if zone.sum() > 0.004 * w * h or not silhouette[zone].all():
            continue  # fond de l'image ou grande zone sans nom : on n'y touche pas
        anneau = cv2.dilate(zone.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool) & ~zone
        voisins = L[anneau]
        voisins = voisins[voisins >= 0]
        if voisins.size:
            L[zone] = np.bincount(voisins).argmax()

    # Trous laissés par le texte : bouchés s'ils ne contiennent aucune autre pièce.
    for i in range(len(ids)):
        m = L == i
        plein = remplir_trous(m)
        trous = (plein & ~m).astype(np.uint8)
        nt, lt = cv2.connectedComponents(trous, connectivity=4)
        for t in range(1, nt):
            zone = lt == t
            if not ((L[zone] >= 0) & (L[zone] != i)).any():
                L[zone] = i

    zones = {}
    for i, piece in enumerate(ids):
        m = L == i
        if m.sum() < 30:
            raise RuntimeError(f"{nom}/{piece}: zone vide")
        d = cv2.distanceTransform(m.astype(np.uint8), cv2.DIST_L2, 3)
        cy, cx = np.unravel_index(np.argmax(d), d.shape)
        zones[piece] = {"d": chemin_svg(m), "centre": [int(cx), int(cy)], "aire": int(m.sum())}

    # Image publiée dans l'appli (avec repeinture éventuelle).
    sortie = im.copy()
    if cfg.get("repeindre"):
        i = ids.index(cfg["repeindre"])
        zone = cv2.dilate((L == i).astype(np.uint8), noyau, iterations=2).astype(bool)
        b, g, r = [sortie[:, :, c].astype(float) for c in range(3)]
        clair = (r > 150) & zone
        t = np.clip((g - 30) / 225.0, 0, 1)
        gris = (255 * (1 - t)).astype(np.uint8)
        for c in range(3):
            canal = sortie[:, :, c]
            canal[clair] = gris[clair]
    ext = os.path.splitext(cfg["image"])[1]
    os.makedirs(os.path.join(APP, "img"), exist_ok=True)
    params = [cv2.IMWRITE_JPEG_QUALITY, 92] if ext == ".jpg" else []
    cv2.imencode(ext, sortie, params)[1].tofile(os.path.join(APP, "img", cfg["image"]))

    # Image de contrôle : chaque pièce colorée + son identifiant.
    vis = cv2.cvtColor(sortie, cv2.COLOR_BGRA2BGR) if sortie.ndim == 3 and sortie.shape[2] == 4 else sortie.copy()
    if alpha is not None:
        vis = plat.copy()
    rng = np.random.default_rng(7)
    for i, piece in enumerate(ids):
        col = rng.integers(30, 230, 3)
        m = L == i
        vis[m] = (vis[m] * 0.35 + col * 0.65).astype(np.uint8)
    echelle = 3 if w < 450 else 2 if w < 600 else 1.5
    vis = cv2.resize(vis, None, fx=echelle, fy=echelle, interpolation=cv2.INTER_NEAREST)
    for piece, z in zones.items():
        x, y = int(z["centre"][0] * echelle), int(z["centre"][1] * echelle)
        for ep, coul in ((3, (0, 0, 0)), (1, (255, 255, 255))):
            cv2.putText(vis, piece, (x - 4 * len(piece), y + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.42, coul, ep)
    os.makedirs(CONTROLE, exist_ok=True)
    cv2.imencode(".png", vis)[1].tofile(os.path.join(CONTROLE, f"{nom}.png"))

    couverture = (L >= 0).sum() / max(1, silhouette.sum())
    print(f"{nom}: {len(zones)} pièces, couverture silhouette {couverture:.0%}")
    return {"largeur": w, "hauteur": h, "image": f"img/{cfg['image']}", "zones": zones}


def main():
    toutes = {nom: traiter(nom, cfg) for nom, cfg in PLANCHES.items()}
    js = ("// Fichier GÉNÉRÉ par outils/zones.py — ne pas modifier à la main.\n"
          "// Zones cliquables (chemins SVG en pixels de l'image) de chaque planche.\n"
          "window.ZONES = " + json.dumps(toutes, ensure_ascii=False, indent=1) + ";\n")
    os.makedirs(os.path.join(APP, "data"), exist_ok=True)
    with open(os.path.join(APP, "data", "zones.js"), "w", encoding="utf-8", newline="\n") as f:
        f.write(js)
    return 0


if __name__ == "__main__":
    sys.exit(main())
