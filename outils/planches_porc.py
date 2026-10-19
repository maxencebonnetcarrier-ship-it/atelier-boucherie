# Délimite chaque os du PORC sur ses gravures de référence (sources/anatomie/porc/, domaine public), pour
# construire ensuite les os 3D d'après leur vrai contour (outils/squelette_porc.py).
#
# Deux sources :
#  - Cuyer, « The Artistic Anatomy of Animals » (1905), fig. 38 : squelette entier de profil (côté gauche),
#    avec le contour du corps. Sert à placer les os les uns par rapport aux autres (articulations).
#  - Sisson, « The Anatomy of the Domestic Animals » (1914), « Skeleton of the pig » : chaque os dessiné
#    seul, ombré sur fond blanc, sous un ou deux angles. Sert à la FORME de chaque os.
# Les figures de Sisson sont des os gris sur papier blanc : la silhouette se détoure toute seule (tout ce qui
# est plus sombre que le papier, sans les traits fins des légendes), puis on bouche les trous (chiffres,
# ombres). Les pages ne sont gardées que recadrées sur leurs figures ; les coordonnées des fiches ci-dessous
# restent celles de la page entière (le recadrage est l'union des cadres de la page, plus 20 px).
#
#   python outils/planches_porc.py              -> outils/cache/os_planches_porc.json + outils/controle/porc-figures-*.jpg
#   python outils/planches_porc.py --recadrer   -> recadre d'abord les pages entières de sources/anatomie/porc/
import hashlib
import json
import os
import sys

import cv2
import numpy as np

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(RACINE, "sources", "anatomie", "porc")
CONTROLE = os.path.join(RACINE, "outils", "controle")
SORTIE = os.path.join(RACINE, "outils", "cache", "os_planches_porc.json")
CUYER = os.path.join(SOURCES, "cuyer-1905-fig38.jpg")

# Figures : page de Sisson (1914), cadre (x0, y0, x1, y1) en pixels de la page, vue.
# Réglages facultatifs : « retirer » / « ajouter » (polygones en pixels de page : légende collée à l'os, partie
# trop pâle), « trous » (points dans un vrai trou de l'os à garder ouvert), « composantes » (nombre de
# morceaux gardés), « delta » (écart au papier), « ouvre » / « ferme » (nettoyage).
FIGURES = {
    "c4_profil": {"page": 170, "cadre": (100, 740, 610, 1360), "delta": 5, "ferme": 25, "vue": "fig. 164, 4e cervicale, côté gauche"},
    "c6_face": {"page": 170, "cadre": (640, 590, 1110, 1320), "vue": "fig. 165, 6e cervicale, de face (avant)"},
    "c7_profil": {"page": 170, "cadre": (1140, 390, 1580, 1320), "vue": "fig. 166, 7e cervicale, côté gauche"},
    "atlas_dessus": {"page": 170, "cadre": (160, 1690, 910, 2150), "delta": 7, "ferme": 21, "vue": "fig. 167, atlas, de dessus"},
    "atlas_face": {"page": 170, "cadre": (990, 1720, 1640, 2160), "vue": "fig. 168, atlas, de face"},
    "axis_profil": {"page": 171, "cadre": (170, 200, 590, 840), "vue": "fig. 169, axis, côté gauche"},
    "axis_face": {"page": 171, "cadre": (920, 200, 1340, 830), "vue": "fig. 170, axis, de face"},
    "dorsale_profil": {"page": 171, "cadre": (1225, 1190, 1530, 2420), "vue": "fig. 171, 3e dorsale, côté gauche"},
    "lombaire_face": {"page": 172, "cadre": (340, 950, 1490, 1600), "vue": "fig. 172, lombaire, de face"},
    "sacrum_dessus": {"page": 173, "cadre": (800, 560, 1560, 1780), "vue": "fig. 173, sacrum et 1re coccygienne, de dessus"},
    "cote8": {"page": 174, "cadre": (90, 370, 720, 1800), "vue": "fig. 175, 8e côte, de profil"},
    "cote1": {"page": 174, "cadre": (1080, 940, 1320, 1760), "vue": "fig. 176, 1re côte, de profil"},
    "crane_profil": {"page": 175, "cadre": (20, 590, 1580, 1849), "ferme": 9, "tolerance": 2,
                     # la mâchoire (presque aussi claire que le papier) : bord inférieur et bord arrière tracés à la main
                     "ajouter": [[(200, 1700), (320, 1824), (500, 1840), (800, 1846), (1100, 1846), (1300, 1840), (1400, 1810),
                                  (1450, 1760), (1470, 1660), (1476, 1520), (1470, 1400), (1440, 1280), (1400, 1220),
                                  (1300, 1250), (1000, 1500), (600, 1600), (300, 1680)]],
                     "papier": [(30, 600), (600, 600), (1570, 600), (30, 1000), (30, 1400), (30, 1830), (700, 1835), (1570, 1835),
                                (1570, 1300), (1520, 1600), (300, 900)], "vue": "fig. 177, crâne, côté gauche"},
    "crane_dessous": {"page": 176, "cadre": (470, 580, 1350, 2080), "ouvre": 9, "vue": "fig. 178, crâne, de dessous"},
    "crane_dessus": {"page": 177, "cadre": (420, 610, 1240, 2160), "ouvre": 9, "vue": "fig. 179, crâne, de dessus"},
    "crane_arriere": {"page": 182, "cadre": (380, 560, 1500, 1990), "vue": "fig. 182, crâne et mâchoire, de derrière"},
    "mandibule_dessus": {"page": 180, "cadre": (180, 670, 880, 1890), "ouvre": 9, "vue": "fig. 181, mâchoire, de dessus"},
    "palette": {"page": 184, "cadre": (490, 690, 1380, 1900), "ouvre": 9, "vue": "fig. 183, palette gauche, face externe"},
    "humerus_profil": {"page": 186, "cadre": (320, 280, 720, 1270), "vue": "fig. 185, humérus gauche, face externe"},
    "humerus_dedans": {"page": 186, "cadre": (1110, 240, 1500, 1260), "vue": "fig. 186, humérus gauche, face interne"},
    "radius_profil": {"page": 186, "cadre": (340, 1390, 690, 2560), "vue": "fig. 187, radius et cubitus gauches, face externe"},
    "radius_dedans": {"page": 186, "cadre": (1140, 1460, 1470, 2550), "vue": "fig. 188, radius et cubitus gauches, face interne"},
    "main_dessus": {"page": 187, "cadre": (120, 630, 610, 1850), "ouvre": 7, "retirer": [[(120, 630), (610, 630), (610, 874), (120, 874)]], "vue": "fig. 189, carpe, métacarpe et doigts gauches, de face"},
    "main_dessous": {"page": 187, "cadre": (870, 630, 1440, 1850), "ouvre": 7, "retirer": [[(870, 630), (1440, 630), (1440, 874), (870, 874)]], "vue": "fig. 190, même pied, de derrière"},
    "coxal_profil": {"page": 188, "cadre": (280, 1130, 1490, 1590), "ouvre": 9, "vue": "fig. 191, os coxal gauche, face externe"},
    "coxal_dedans": {"page": 188, "cadre": (330, 1740, 1462, 2220), "ouvre": 9, "vue": "fig. 192, os coxal gauche, face interne"},
    "femur_face": {"page": 189, "cadre": (190, 790, 570, 1990), "vue": "fig. 193, fémur droit, de face"},
    "femur_dos": {"page": 189, "cadre": (1010, 790, 1355, 1955), "vue": "fig. 194, fémur droit, de derrière"},
    "tibia_face": {"page": 190, "cadre": (335, 775, 690, 1825), "vue": "fig. 195, tibia et péroné droits, de face"},
    "tibia_dos": {"page": 190, "cadre": (1115, 760, 1460, 1830), "vue": "fig. 196, tibia et péroné droits, de derrière"},
    "pied_dessus": {"page": 191, "cadre": (190, 660, 570, 1850), "ouvre": 9, "vue": "fig. 197, tarse, métatarse et doigts droits, de face"},
    "pied_dessous": {"page": 191, "cadre": (1015, 665, 1395, 1850), "ouvre": 9, "vue": "fig. 198, même pied, de derrière"},
}


# Coin (x0, y0, x1, y1) en pixels de page du recadrage gardé de chaque page de Sisson (fixe : les fichiers de
# sources/anatomie/porc/ ont cette taille ; changer un cadre de figure ne déplace pas la page).
RECADRAGES = {170: (80, 370, 1680, 2180), 171: (150, 180, 1550, 2440), 172: (320, 930, 1510, 1620), 173: (780, 540, 1580, 1800), 174: (70, 350, 1340, 1820), 175: (10, 570, 1600, 1850), 176: (450, 560, 1370, 2100), 177: (400, 590, 1260, 2180), 180: (160, 650, 900, 1910), 182: (360, 540, 1520, 2010), 184: (470, 670, 1400, 1920), 186: (300, 220, 1520, 2580), 187: (100, 610, 1460, 1870), 188: (260, 1110, 1510, 2240), 189: (170, 770, 1375, 2010), 190: (315, 740, 1480, 1850), 191: (170, 640, 1415, 1870)}


def _cadre_page(page):
    return RECADRAGES[page]


def chemin_page(page):
    return os.path.join(SOURCES, f"sisson-1914-p{page}.jpg")


def lire_page(page):
    """Image de la page (gris), dans les coordonnées de la page entière (hors recadrage : blanc)."""
    g = cv2.imread(chemin_page(page), 0)
    x0, y0, x1, y1 = _cadre_page(page)
    if g.shape == (y1 - y0, x1 - x0):            # page recadrée (dépôt)
        page_g = np.full((y1 + 10, x1 + 10), 255, np.uint8)
        page_g[y0:y1, x0:x1] = g
        return page_g
    return g


def recadrer_sources():
    """Remplace chaque page entière par son recadrage (une seule fois, à l'import des gravures)."""
    for page, (x0, y0, x1, y1) in RECADRAGES.items():
        g = cv2.imread(chemin_page(page), 0)
        if g.shape != (y1 - y0, x1 - x0):
            cv2.imwrite(chemin_page(page), g[y0:y1, x0:x1], [cv2.IMWRITE_JPEG_QUALITY, 88])


def detourer(g, spec):
    """Silhouette de l'os : plus sombre que le papier, sans les traits fins, trous bouchés."""
    x0, y0, x1, y1 = spec["cadre"]
    s = g[y0:y1, x0:x1]
    if spec.get("papier"):
        # papier qui s'assombrit (vers la reliure) jusqu'à être plus sombre qu'un os pâle : on le remplit depuis des
        # points de papier, en suivant son dégradé de proche en proche, et on s'arrête au bord net de l'os
        lisse = cv2.medianBlur(s, 5)
        inonde = np.zeros((s.shape[0] + 2, s.shape[1] + 2), np.uint8)
        tol = spec.get("tolerance", 2)
        for x, y in spec["papier"]:
            cv2.floodFill(lisse.copy(), inonde, (x - x0, y - y0), 0, tol, tol, 4 | cv2.FLOODFILL_MASK_ONLY | (1 << 8))
        m = (inonde[1:-1, 1:-1] == 0).astype(np.uint8)
    else:
        fond = float(spec.get("fond", np.percentile(s, 92)))
        m = (s < fond - spec.get("delta", 14)).astype(np.uint8)
    ouvre = spec.get("ouvre", 5)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ouvre, ouvre)))
    for p in spec.get("retirer", []):
        cv2.fillPoly(m, [np.asarray(p, np.int32) - [x0, y0]], 0)
    ferme = spec.get("ferme", 11)
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ferme, ferme)))
    k, lab, st, _ = cv2.connectedComponentsWithStats(m)
    garder = spec.get("composantes", 1)
    ordre = 1 + np.argsort(-st[1:, 4])[:garder]
    m = np.isin(lab, ordre).astype(np.uint8)
    for p in spec.get("ajouter", []):
        cv2.fillPoly(m, [np.asarray(p, np.int32) - [x0, y0]], 1)
    h = m.copy()
    cv2.floodFill(h, np.zeros((m.shape[0] + 2, m.shape[1] + 2), np.uint8), (0, 0), 2)
    plein = (h != 2).astype(np.uint8)
    if spec.get("trous"):                            # vrais trous de l'os (trou vertébral...) : on les rouvre
        vide = ((plein == 1) & (m == 0)).astype(np.uint8)
        _, lt = cv2.connectedComponents(vide)
        for x, y in spec["trous"]:
            i = lt[y - y0, x - x0]
            if i:
                plein[lt == i] = 0
    out = np.zeros(g.shape, np.uint8)
    out[y0:y1, x0:x1] = plein
    return out


def contours(m):
    cs, h = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    ext = [c for c, hh in zip(cs, h[0]) if hh[3] < 0]
    ext.sort(key=cv2.contourArea, reverse=True)
    trous = [cv2.approxPolyDP(c, 1.0, True)[:, 0, :].tolist() for c, hh in zip(cs, h[0]) if hh[3] >= 0 and cv2.contourArea(c) > 80]
    return [cv2.approxPolyDP(c, 1.0, True)[:, 0, :].tolist() for c in ext], trous


def empreinte(spec):
    return hashlib.sha1(json.dumps(spec, sort_keys=True, default=list).encode()).hexdigest()[:16]


def main(noms=()):
    sortie = json.load(open(SORTIE, encoding="utf-8")) if os.path.exists(SORTIE) else {}
    pages = {}
    for nom, spec in FIGURES.items():
        if noms and nom not in noms:
            continue
        g = pages.setdefault(spec["page"], lire_page(spec["page"]))
        m = detourer(g, spec)
        ext, trous = contours(m)
        sortie[nom] = {"page": spec["page"], "contour": ext[0], "autres": ext[1:], "trous": trous, "aire": int(m.sum()),
                       "empreinte": empreinte(spec)}
        print(f"{nom:18s} p{spec['page']} aire {int(m.sum()):7d} px, {len(ext[0])} points, {len(ext) - 1} autres, {len(trous)} trous")
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8", newline="") as fh:
        json.dump(sortie, fh)
    if not noms:
        controle(sortie)


def controle(sortie):
    """Planches de contrôle : chaque figure avec son contour (rouge), ses trous (vert) et une grille en pixels
    de page (un trait tous les 50 px, numéroté tous les 100 px)."""
    vues = []
    for nom, spec in FIGURES.items():
        if nom not in sortie:
            continue
        x0, y0, x1, y1 = spec["cadre"]
        c = cv2.cvtColor(lire_page(spec["page"])[y0:y1, x0:x1], cv2.COLOR_GRAY2BGR)
        for x in range((x0 // 50 + 1) * 50, x1, 50):
            cv2.line(c, (x - x0, 0), (x - x0, y1 - y0), (255, 200, 150) if x % 100 else (255, 120, 0), 1)
            if x % 100 == 0:
                cv2.putText(c, str(x), (x - x0 + 2, 14), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 80, 0), 1)
        for y in range((y0 // 50 + 1) * 50, y1, 50):
            cv2.line(c, (0, y - y0), (x1 - x0, y - y0), (255, 200, 150) if y % 100 else (255, 120, 0), 1)
            if y % 100 == 0:
                cv2.putText(c, str(y), (2, y - y0 - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 80, 0), 1)
        d = sortie[nom]
        for cc in [d["contour"]] + d["autres"]:
            cv2.polylines(c, [np.asarray(cc, np.int32) - [x0, y0]], True, (0, 0, 230), 2)
        for t in d["trous"]:
            cv2.polylines(c, [np.asarray(t, np.int32) - [x0, y0]], True, (0, 160, 0), 2)
        cv2.putText(c, nom, (6, y1 - y0 - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)
        vues.append(c)
    os.makedirs(CONTROLE, exist_ok=True)
    for i in range(0, len(vues), 6):
        h = 900
        imgs = [cv2.resize(c, (max(1, c.shape[1] * h // c.shape[0]), h)) for c in vues[i:i + 6]]
        cv2.imwrite(os.path.join(CONTROLE, f"porc-figures-{i // 6 + 1}.jpg"), np.hstack(imgs))


_cache = None


def figure(nom):
    """Contour (pixels de page) d'une figure, depuis le cache (recalculé si sa fiche a changé)."""
    global _cache
    if _cache is None:
        _cache = json.load(open(SORTIE, encoding="utf-8")) if os.path.exists(SORTIE) else {}
    if nom not in _cache or _cache[nom].get("empreinte") != empreinte(FIGURES[nom]):
        main([nom])
        _cache = json.load(open(SORTIE, encoding="utf-8"))
    return _cache[nom]


if __name__ == "__main__":
    if "--recadrer" in sys.argv:
        recadrer_sources()
    main([a for a in sys.argv[1:] if not a.startswith("--")])
