# Muscles du bœuf en volumes, posés sur les os (côté gauche ; l'appli fait le côté droit par symétrie).
#
# Un volume par pièce de boucherie de l'appli, placé à sa place anatomique PAR RAPPORT AUX OS du
# squelette (squelette.py) : paleron dans la fosse sous l'épine de la palette, jumeau à bifteck dans
# la fosse au-dessus, macreuse à bifteck (boule de macreuse) entre le bord arrière de la palette et
# la pointe du coude, faux-filet sur les « étagères » des lombaires, filet dessous, rumsteck sur
# l'aile de l'os du bassin, tranche grasse devant le fémur, gîte à la noix et rond de gîte derrière,
# tende de tranche à l'intérieur de la cuisse, araignée sous le plancher du bassin, etc.
# Placement simplifié, « pour comprendre la structure » : à valider avec le formateur.
#
# Chaque muscle est ensuite coupé par la peau (il reste dans le corps) et creusé par les os
# (il les entoure sans les traverser).
import time

import numpy as np

from formes import boeuf as corps_boeuf
from sdf import Forme, Prim, Repere, courbe, ell, loft, n_, plaque, GRAND
from squelette import (ACETABULE, COUDE, EPINES_DORS, GLENE, GRASSET, JARRET, POINTE_FESSE, POINTE_HANCHE,
                       SACREE, OS_BOEUF, VERT, p3, repere_palette, repere_vertebre)

Y = np.array([0.0, 1.0, 0.0])
X = np.array([1.0, 0.0, 0.0])
Z = np.array([0.0, 0.0, 1.0])

_corps = None


def corps():
    global _corps
    if _corps is None:
        _corps = corps_boeuf()
    return _corps


def coque(e0, e1, region):
    """Couche sous la peau, entre les profondeurs e0 et e1 (m), limitée à une région (Prim) :
    pour les muscles de la paroi (flanchet, bavettes, plat de côtes, tendron)."""
    c = corps()

    def f(P):
        d = c.distance(P)
        return np.maximum(np.maximum(d + e0, -(d + e1)), region.f(P))
    return Prim(f, region.lo, region.hi)


def zone(x0, x1, y0, y1, arrondi=0.03):
    """Région de profil (rectangle arrondi dans le plan x-y, sur toute la largeur gauche) : les muscles
    de la paroi se partagent le flanc comme les pièces sur une planche."""
    cx, cy, hx, hy = (x0 + x1) / 2, (y0 + y1) / 2, (x1 - x0) / 2 - arrondi, (y1 - y0) / 2 - arrondi

    def f(P):
        qx = np.abs(P[..., 0] - cx) - hx
        qy = np.abs(P[..., 1] - cy) - hy
        return np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2) + np.minimum(np.maximum(qx, qy), 0) - arrondi
    return Prim(f, (x0, y0, 0.0), (x1, y1, 0.5))


def demi_espace_gauche(marge=0.003):
    return Prim(lambda P: marge - P[..., 2], (-3, -1, 0), (3, 3, 3))


def le_long_vertebres(noms, dy, dz=0.0):
    pts = []
    for n in noms:
        P, T, L = VERT[n]
        pts.append(P + Y * dy + Z * dz)
    return pts


# ---------------------------------------------------------------- avant
def collier():
    f = Forme()
    noms = ["C1", "C2", "C3", "C4", "C5", "C6", "C7"]
    pts = le_long_vertebres(noms, 0.05)
    pts.insert(0, pts[0] + p3(-0.02, 0.02))
    pts.append(VERT["T1"][0] + p3(0.0, 0.06))
    f.ajouter(loft(courbe(pts, n=12), [0.11, 0.12, 0.14, 0.15, 0.16, 0.17, 0.18, 0.18, 0.16],
                   [0.1, 0.11, 0.12, 0.13, 0.14, 0.14, 0.15, 0.15, 0.13], haut=Y, arrondi=0.02), 0.03)
    f.couper(demi_espace_gauche())
    return f


def basses_cotes():
    f = Forme()
    pts, a, b = [], [], []
    for i in range(0, 6):
        P, T, L = VERT[f"T{i + 1}"]
        tip = EPINES_DORS[i]
        haut = (tip[1] - P[1])
        pts.append(p3((P[0] + tip[0]) / 2, P[1] + haut * 0.45, 0.06))
        a.append(haut * 0.52)
        b.append(0.06)
    f.ajouter(loft(pts, a, b, haut=Y, arrondi=0.015, carre=2.4), 0.02)
    f.couper(demi_espace_gauche())
    return f


def entrecotes():
    f = Forme()
    pts, a, b = [], [], []
    for i in range(5, 11):
        P, T, L = VERT[f"T{i + 1}"]
        tip = EPINES_DORS[i]
        pts.append(p3((P[0] + tip[0]) / 2, P[1] + 0.07, 0.068))
        a.append(0.07)
        b.append(0.064)
    f.ajouter(loft(pts, a, b, haut=Y, arrondi=0.015, carre=2.4), 0.02)
    f.couper(demi_espace_gauche())
    return f


def faux_filet():
    f = Forme()
    noms = ["T11", "T12", "T13", "L1", "L2", "L3", "L4", "L5", "L6"]
    pts = [VERT[n][0] + p3(0.01, 0.062, 0.072) for n in noms]
    f.ajouter(loft(pts, [0.045, 0.05, 0.056, 0.06, 0.062, 0.062, 0.06, 0.056, 0.046],
                   [0.055, 0.058, 0.062, 0.066, 0.068, 0.068, 0.066, 0.06, 0.05], haut=Y, arrondi=0.012, carre=2.3), 0.02)
    f.couper(demi_espace_gauche())
    return f


def filet():
    f = Forme()
    chemin = [p3(0.0, 1.212, 0.036), p3(0.14, 1.198, 0.05), p3(0.3, 1.19, 0.062), p3(0.45, 1.18, 0.07),
              p3(0.58, 1.155, 0.088), p3(0.68, 1.1, 0.12), p3(0.74, 1.04, 0.15)]
    f.ajouter(loft(courbe(chemin, n=14), [0.016, 0.026, 0.033, 0.038, 0.04, 0.034, 0.02],
                   [0.022, 0.035, 0.044, 0.05, 0.05, 0.04, 0.022], haut=Y, arrondi=0.008), 0.015)
    return f


def onglet():
    f = Forme()
    chemin = [p3(0.2, 1.212, 0.016), p3(0.13, 1.17, 0.03), p3(0.06, 1.1, 0.045), p3(0.0, 1.03, 0.052)]
    f.ajouter(loft(courbe(chemin, n=8), [0.018, 0.026, 0.028, 0.02], [0.014, 0.02, 0.02, 0.014], haut=X, arrondi=0.006), 0.012)
    return f


def hampe():
    f = Forme()
    chemin = [p3(-0.12, 0.8, 0.2), p3(-0.04, 0.88, 0.27), p3(0.02, 0.98, 0.29), p3(0.05, 1.08, 0.27), p3(0.06, 1.17, 0.2)]
    f.ajouter(loft(courbe(chemin, n=12), [0.035, 0.045, 0.045, 0.04, 0.03], [0.011, 0.012, 0.012, 0.011, 0.01],
                   haut=X, arrondi=0.005), 0.012)
    return f


def gros_bout():
    f = Forme()
    f.ajouter(ell(p3(-0.8, 0.79, 0.07), (0.16, 0.16, 0.1)), 0.04)
    f.ajouter(ell(p3(-0.66, 0.72, 0.05), (0.12, 0.08, 0.08)), 0.04)
    f.couper(demi_espace_gauche())
    return f


def plat_de_cotes():
    return Forme().ajouter(coque(0.008, 0.075, zone(-0.42, 0.07, 0.855, 1.07)), 0.0)


def tendron():
    f = Forme().ajouter(coque(0.008, 0.09, zone(-0.5, 0.07, 0.6, 0.85)), 0.0)
    f.couper(demi_espace_gauche())
    return f


def flanchet():
    f = Forme().ajouter(coque(0.006, 0.05, zone(0.075, 0.6, 0.58, 0.83)), 0.0)
    f.couper(demi_espace_gauche())
    return f


def bavette_aloyau():
    return Forme().ajouter(coque(0.008, 0.055, zone(0.075, 0.52, 0.985, 1.2)), 0.0)


def bavette_flanchet():
    return Forme().ajouter(coque(0.008, 0.045, zone(0.075, 0.45, 0.835, 0.98)), 0.0)


def _palette_fosse(vmin, vmax, epaisseur, debord=0.0):
    """Muscle couché dans une fosse de la palette (entre v = vmin et vmax), sur sa face externe."""
    R = repere_palette()
    dehors = 1.0 if R.W[2] > 0 else -1.0
    L = np.linalg.norm(p3(-0.505, 1.352, 0.152) - GLENE)
    us = np.linspace(0.06, L - 0.02, 8)
    vc = (vmin + vmax) / 2
    pts = [R.point(u, vc + debord * (u / L), dehors * epaisseur * 0.75) for u in us]
    larg = (vmax - vmin) / 2
    a = [larg * f for f in (0.35, 0.65, 0.85, 0.95, 1.0, 1.0, 0.92, 0.75)]
    b = [epaisseur * f for f in (0.5, 0.8, 1.0, 1.0, 1.0, 0.92, 0.8, 0.6)]
    return R, loft(pts, a, b, haut=R.V, arrondi=0.008)


def paleron():
    f = Forme()
    R, l = _palette_fosse(-0.135, -0.004, 0.034)
    f.ajouter(l, 0.02)
    dehors = 1.0 if R.W[2] > 0 else -1.0
    f.ajouter(loft([R.point(0.08, -0.03, dehors * 0.03), p3(-0.77, 0.995, 0.3)], [0.02, 0.012], [0.018, 0.01],
                   haut=Y, arrondi=0.004), 0.015)                                 # tendon vers le gros tubercule
    return f


def jumeau_bifteck():
    f = Forme()
    R, l = _palette_fosse(0.006, 0.112, 0.03, debord=0.01)
    f.ajouter(l, 0.02)
    f.ajouter(ell(p3(-0.8, 1.01, 0.265), (0.035, 0.04, 0.03)), 0.02)             # vers le devant de l'épaule
    return f


def macreuse_bifteck():
    """Boule de macreuse : grosse masse dans l'angle entre le bord arrière de la palette et le coude."""
    f = Forme()
    R = repere_palette()
    chemin = [R.point(0.3, -0.13, 0.0), R.point(0.18, -0.115, 0.0), p3(-0.62, 0.88, 0.235), p3(-0.53, 0.82, 0.235),
              p3(-0.5, 0.8, 0.228)]
    f.ajouter(loft(courbe(chemin, n=12), [0.03, 0.058, 0.07, 0.05, 0.022], [0.028, 0.05, 0.058, 0.042, 0.02],
                   haut=Y, arrondi=0.01), 0.025)
    return f


def macreuse_pot():
    f = Forme()
    chemin = [p3(-0.72, 0.93, 0.29), p3(-0.64, 0.84, 0.29), p3(-0.56, 0.78, 0.27), p3(-0.51, 0.765, 0.245)]
    f.ajouter(loft(courbe(chemin, n=10), [0.035, 0.05, 0.045, 0.025], [0.028, 0.036, 0.032, 0.02], haut=Y, arrondi=0.01), 0.02)
    return f


def jumeau_pot():
    f = Forme()
    chemin = [p3(-0.82, 0.985, 0.245), p3(-0.77, 0.88, 0.25), p3(-0.7, 0.79, 0.24), p3(-0.635, 0.72, 0.232)]
    f.ajouter(loft(courbe(chemin, n=10), [0.032, 0.04, 0.035, 0.022], [0.03, 0.036, 0.032, 0.02], haut=X, arrondi=0.01), 0.02)
    return f


def gite_avant():
    f = Forme()
    chemin = [p3(-0.578, 0.68, 0.218), p3(-0.588, 0.6, 0.216), p3(-0.594, 0.52, 0.212), p3(-0.598, 0.45, 0.208)]
    f.ajouter(loft(courbe(chemin, n=10), [0.06, 0.055, 0.04, 0.026], [0.05, 0.048, 0.036, 0.026], haut=X, arrondi=0.01), 0.02)
    return f


# ---------------------------------------------------------------- arrière
def rumsteck():
    f = Forme()
    chemin = [p3(0.4, 1.33, 0.11), p3(0.52, 1.37, 0.15), p3(0.65, 1.34, 0.19), p3(0.77, 1.24, 0.235), p3(0.835, 1.1, 0.262)]
    f.ajouter(loft(courbe(chemin, n=14), [0.04, 0.062, 0.07, 0.055, 0.026], [0.065, 0.09, 0.085, 0.06, 0.03],
                   haut=Y, arrondi=0.012, carre=2.3), 0.025)
    return f


def aiguillette_baronne():
    f = Forme()
    chemin = [POINTE_HANCHE + p3(0.01, -0.02, 0.012), p3(0.53, 1.13, 0.3), p3(0.58, 0.96, 0.305), p3(0.62, 0.81, 0.28)]
    f.ajouter(loft(courbe(chemin, n=10), [0.045, 0.065, 0.058, 0.03], [0.022, 0.027, 0.024, 0.014], haut=X, arrondi=0.008), 0.018)
    return f


def tende_tranche():
    f = Forme()
    chemin = [p3(0.96, 1.0, 0.065), p3(0.89, 0.9, 0.095), p3(0.8, 0.79, 0.125), p3(0.72, 0.71, 0.15)]
    f.ajouter(loft(courbe(chemin, n=10), [0.08, 0.09, 0.07, 0.035], [0.05, 0.056, 0.046, 0.026], haut=X, arrondi=0.015), 0.025)
    return f


def tranche_grasse():
    f = Forme()
    chemin = [p3(0.765, 1.03, 0.225), p3(0.705, 0.92, 0.218), p3(0.66, 0.81, 0.215), p3(0.637, 0.76, 0.215)]
    f.ajouter(loft(courbe(chemin, n=10), [0.05, 0.075, 0.062, 0.026], [0.06, 0.072, 0.058, 0.026], haut=X, arrondi=0.015), 0.025)
    return f


def gite_noix():
    f = Forme()
    chemin = [p3(0.985, 1.19, 0.18), p3(0.92, 1.04, 0.255), p3(0.83, 0.88, 0.28), p3(0.745, 0.7, 0.27)]
    f.ajouter(loft(courbe(chemin, n=10), [0.06, 0.1, 0.09, 0.05], [0.04, 0.05, 0.046, 0.03], haut=X, arrondi=0.012), 0.025)
    return f


def rond_gite():
    f = Forme()
    chemin = [POINTE_FESSE + p3(0.02, -0.02, 0.01), p3(1.04, 0.98, 0.14), p3(0.98, 0.84, 0.16), p3(0.88, 0.72, 0.17)]
    f.ajouter(loft(courbe(chemin, n=10), [0.04, 0.055, 0.05, 0.03], [0.04, 0.055, 0.05, 0.03], haut=X, arrondi=0.01), 0.02)
    return f


def araignee():
    f = Forme()
    f.ajouter(ell(p3(0.915, 0.945, 0.095), (0.065, 0.02, 0.05), rot=(0, 0, 8)), 0.012)
    return f


def gite_arriere():
    f = Forme()
    chemin = [p3(0.73, 0.64, 0.214), p3(0.785, 0.575, 0.214), p3(0.84, 0.51, 0.212), p3(0.885, 0.47, 0.21)]
    f.ajouter(loft(courbe(chemin, n=10), [0.065, 0.06, 0.042, 0.025], [0.05, 0.046, 0.034, 0.022], haut=(0.66, 0.75, 0),
                   arrondi=0.01), 0.02)
    f.ajouter(loft([p3(0.86, 0.52, 0.218), p3(0.95, 0.49, 0.228)], [0.01, 0.008], [0.008, 0.007], haut=Y, arrondi=0.003), 0.012)  # tendon
    return f


# ---------------------------------------------------------------- tête
def plat_de_joue():
    f = Forme()
    f.ajouter(ell(p3(-1.275, 1.15, 0.108), (0.07, 0.07, 0.02), rot=(0, 0, 20)), 0.015)
    return f


def langue():
    f = Forme()
    chemin = [p3(-1.25, 1.13, 0.0), p3(-1.35, 1.09, 0.0), p3(-1.46, 1.03, 0.0), p3(-1.55, 0.99, 0.0)]
    f.ajouter(loft(courbe(chemin, n=10), [0.042, 0.038, 0.03, 0.016], [0.045, 0.042, 0.035, 0.02], haut=Y, arrondi=0.01), 0.015)
    return f


# id du muscle -> forme, pièce(s) de l'appli, pair ?
MUSCLES_BOEUF = {
    "collier": {"forme": collier, "pieces": ["collier"]},
    "basses-cotes": {"forme": basses_cotes, "pieces": ["basses-cotes"]},
    "cotes-entrecotes": {"forme": entrecotes, "pieces": ["cotes-entrecotes"]},
    "faux-filet": {"forme": faux_filet, "pieces": ["faux-filet"]},
    "filet": {"forme": filet, "pieces": ["filet"]},
    "onglet": {"forme": onglet, "pieces": ["onglet"]},
    "hampe": {"forme": hampe, "pieces": ["hampe"]},
    "gros-bout-de-poitrine": {"forme": gros_bout, "pieces": ["gros-bout-de-poitrine"]},
    "plat-de-cotes": {"forme": plat_de_cotes, "pieces": ["plat-de-cotes"]},
    "tendron": {"forme": tendron, "pieces": ["tendron"]},
    "flanchet": {"forme": flanchet, "pieces": ["flanchet"]},
    "bavette-d-aloyau": {"forme": bavette_aloyau, "pieces": ["bavette-d-aloyau"]},
    "bavette-de-flanchet": {"forme": bavette_flanchet, "pieces": ["bavette-de-flanchet"]},
    "paleron": {"forme": paleron, "pieces": ["paleron"]},
    "jumeau-a-bifteck": {"forme": jumeau_bifteck, "pieces": ["jumeau-a-bifteck"]},
    "macreuse-a-bifteck": {"forme": macreuse_bifteck, "pieces": ["macreuse-a-bifteck"]},
    "macreuse-a-pot-au-feu": {"forme": macreuse_pot, "pieces": ["macreuse-a-pot-au-feu"]},
    "jumeau-a-pot-au-feu": {"forme": jumeau_pot, "pieces": ["jumeau-a-pot-au-feu"]},
    "gite-avant": {"forme": gite_avant, "pieces": ["gite-avant"]},
    "rumsteck": {"forme": rumsteck, "pieces": ["rumsteck"]},
    "aiguillette-baronne": {"forme": aiguillette_baronne, "pieces": ["aiguillette-baronne"]},
    "tende-de-tranche": {"forme": tende_tranche, "pieces": ["tende-de-tranche"]},
    "tranche-grasse": {"forme": tranche_grasse, "pieces": ["tranche-grasse"]},
    "gite-a-la-noix": {"forme": gite_noix, "pieces": ["gite-a-la-noix"]},
    "rond-de-gite": {"forme": rond_gite, "pieces": ["rond-de-gite"]},
    "araignee": {"forme": araignee, "pieces": ["araignee"]},
    "gite-arriere": {"forme": gite_arriere, "pieces": ["gite-arriere"]},
    "plat-de-joue": {"forme": plat_de_joue, "pieces": ["plat-de-joue"]},
    "langue": {"forme": langue, "pieces": ["langue"], "pair": False},
}
MUSCLES = {"boeuf": MUSCLES_BOEUF}

_os_formes = {}


def formes_os():
    if not _os_formes:
        for oid, fn, pair, cible, pas in OS_BOEUF:
            _os_formes[oid] = fn()
    return _os_formes


def construire_muscle(animal, mid, spec, pas=0.006):
    from anatomie import lisser, occlusion
    from skimage.measure import marching_cubes
    import fast_simplification as fs
    t = time.time()
    forme = spec["forme"]()
    axes = forme.grille(pas, marge=0.02)
    vol = forme.champ(axes)
    X_, Y_, Z_ = np.meshgrid(*axes, indexing="ij")
    P = np.stack([X_, Y_, Z_], -1)
    # dans le corps (6 mm sous la peau) et autour des os, sans les traverser (2 mm d'écart)
    vol = np.maximum(vol, corps().distance(P) + 0.006)
    lo, hi = np.array([a[0] for a in axes]), np.array([a[-1] for a in axes])
    for oid, f_os in formes_os().items():
        blo, bhi = f_os.boite(0.0)
        if np.any(bhi < lo) or np.any(blo > hi):
            continue
        d_os = f_os.distance(P)
        vol = np.maximum(vol, -(d_os - 0.002))
    if vol.min() >= 0:
        raise ValueError(f"muscle {mid} vide")
    v, f, _, _ = marching_cubes(vol, 0.0, spacing=(pas, pas, pas))
    v = v + lo
    v = lisser(v, f, iterations=6)
    cible = spec.get("triangles", 3000)
    if len(f) > cible:
        v, f = fs.simplify(v.astype(np.float32), f.astype(np.int64), target_reduction=1 - cible / len(f), agg=3)
    v, f = v.astype(np.float64), f.astype(np.int64)
    ao = occlusion(forme, v, f, pas=0.012)
    print(f"   muscle {mid}: {len(v)} sommets, {len(f)} triangles ({time.time() - t:.0f} s)", flush=True)
    return {"v": v, "f": f, "code": np.zeros(len(v), np.uint8), "ao": ao}
