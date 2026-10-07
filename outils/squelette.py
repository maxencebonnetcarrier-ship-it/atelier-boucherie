# Squelette 3D du bœuf, réaliste mais épuré, placé dans le corps de formes.py (mêmes coordonnées :
# x = longueur, tête vers -x ; y = hauteur, sol en 0 ; z = largeur, côté gauche = z > 0 ; 1 unité ≈ 1 m).
#
# Chaque os garde ses reliefs de boucher et d'anatomiste : corps, arc et apophyses des vertèbres,
# côtes plates et larges, palette avec son épine (l'arête) et sa cavité glénoïde, tubercules de
# l'humérus (pointe de l'épaule), olécrane (pointe du coude), os du bassin avec la pointe de la
# hanche, la pointe de la fesse et le trou obturé, tête et trochanter du fémur, rotule, crête du
# tibia, calcanéum (pointe du jarret), canons et doigts (deux onglons).
# Nombres d'os d'après la fiche « Le squelette du bovin » (École des Métiers Bigard) et le tableau
# « Le bœuf » n° 1 : 7 cervicales, 13 dorsales, 13 paires de côtes, 7 sternèbres, 6 lombaires,
# 5 sacrées soudées, 16 à 20 coccygiennes (18 ici).
#
# Les os pairs ne sont sculptés que du côté gauche : le côté droit est son reflet exact (z -> -z).
# Parties (couleur) : « corps » = os, « cartilage », « dent ».
import numpy as np

from sdf import Forme, Repere, boite, cap, courbe, cylindre, ell, loft, n_, plaque

Y = np.array([0.0, 1.0, 0.0])
Z = np.array([0.0, 0.0, 1.0])


def p3(x, y, z=0.0):
    return np.array([x, y, z], np.float64)


# ================================================================ colonne vertébrale
# Ligne passant par le centre du corps des vertèbres, de l'atlas au bout de la queue.
LIGNE = courbe([
    (-1.068, 1.318, 0), (-0.995, 1.25, 0), (-0.925, 1.186, 0), (-0.85, 1.128, 0), (-0.77, 1.085, 0),
    (-0.69, 1.078, 0), (-0.62, 1.108, 0), (-0.49, 1.165, 0), (-0.32, 1.213, 0), (-0.15, 1.238, 0),
    (0.02, 1.25, 0), (0.22, 1.256, 0), (0.42, 1.258, 0), (0.56, 1.262, 0), (0.74, 1.258, 0),
    (0.84, 1.27, 0), (0.93, 1.292, 0), (0.995, 1.285, 0), (1.045, 1.21, 0), (1.068, 1.04, 0),
    (1.078, 0.86, 0), (1.084, 0.70, 0)], n=400)
_long = np.r_[0, np.cumsum(np.linalg.norm(np.diff(LIGNE, axis=0), axis=1))]


def le_long(s):
    """Point et tangente de la ligne vertébrale à l'abscisse curviligne s (m)."""
    i = int(np.clip(np.searchsorted(_long, s) - 1, 0, len(LIGNE) - 2))
    t = (s - _long[i]) / (_long[i + 1] - _long[i])
    P = LIGNE[i] * (1 - t) + LIGNE[i + 1] * t
    return P, n_(LIGNE[i + 1] - LIGNE[i])


def abscisse_x(x):
    """Abscisse curviligne du point de la ligne le plus proche de l'abscisse x (pour le cou et le dos)."""
    i = int(np.argmin(np.abs(LIGNE[:60 * 4, 0] - x)))
    return _long[i]


# Longueur du corps de chaque vertèbre (m) et disque entre deux vertèbres.
L_CERV = [0.048, 0.098, 0.066, 0.064, 0.062, 0.056, 0.046]
L_DORS = [0.044, 0.044, 0.045, 0.046, 0.047, 0.048, 0.049, 0.05, 0.051, 0.052, 0.053, 0.054, 0.055]
L_LOMB = [0.058, 0.06, 0.062, 0.063, 0.063, 0.062]
DISQUE = 0.007
N_COCC = 18


def _positions():
    """Centre, tangente et longueur de chaque vertèbre, de l'atlas à la dernière coccygienne."""
    out = {}
    s = 0.0
    for nom, longueurs in (("C", L_CERV), ("T", L_DORS), ("L", L_LOMB)):
        for i, L in enumerate(longueurs):
            P, T = le_long(s + L / 2)
            out[f"{nom}{i + 1}"] = (P, T, L)
            s += L + DISQUE
    out["S"] = (le_long(s + 0.13)[0], le_long(s + 0.13)[1], 0.26)
    s += 0.26 + DISQUE
    for i in range(N_COCC):
        L = 0.046 - 0.024 * i / (N_COCC - 1)
        P, T = le_long(s + L / 2)
        out[f"Co{i + 1}"] = (P, T, L)
        s += L + 0.004
    return out


VERT = _positions()


def repere_vertebre(P, T):
    """u = tangente (vers la queue), v = haut, w = gauche."""
    V = n_(Y - (Y @ T) * T)
    W = np.cross(T, V)
    return T, V, W


def vertebre(f, nom, rc, haut_arc=0.026, canal=0.012, epine=None, larg_epine=0.03, ep_epine=0.0055,
             transv=None, articulaires=0.012):
    """Une vertèbre typique, ajoutée à la forme f.
    epine : point (x, y) du bout de l'apophyse épineuse (dans le plan du milieu) ou None.
    transv : (longueur latérale, largeur, épaisseur, inclinaison vers le haut, avancée) ou None."""
    P, T, L = VERT[nom]
    u, v, w = repere_vertebre(P, T)
    a, b = P - u * L / 2, P + u * L / 2
    # corps : cylindre un peu étranglé en son milieu, bouts légèrement bombés
    f.ajouter(loft([a, P, b], [rc * 0.93, rc * 0.8, rc * 0.93], [rc, rc * 0.84, rc], haut=v, arrondi=0.004), 0.003)
    # arc vertébral (toit du canal de la moelle épinière)
    c_arc = P + v * (rc + haut_arc * 0.45)
    f.ajouter(boite(c_arc, (L * 0.42, haut_arc * 0.55, rc * 0.82), arrondi=0.007, axes=(u, v, w)), 0.006)
    # apophyses articulaires (les « verrous » entre deux vertèbres)
    for sw in (1, -1):
        for su in (-1, 1):
            f.ajouter(ell(P + v * (rc + haut_arc * 0.75) + u * su * L * 0.48 + w * sw * rc * 0.72,
                          (articulaires * 0.9, articulaires * 0.6, articulaires * 0.7), axes=(u, v, w)), 0.004)
    # canal de la moelle
    f.creuser(cylindre(P - u * L, P + u * L, canal), 0.002)
    if epine is not None:
        base = P + v * (rc + haut_arc * 0.8)
        R = Repere(P, u, w, V_vers=v)          # plan (u, v) = plan du milieu
        bx, by = (base - P) @ R.U, (base - P) @ R.V
        tip = np.asarray([epine[0], epine[1], 0.0]) - P
        tx, ty = tip @ R.U, tip @ R.V
        lb = min(larg_epine, L * 0.95)
        pts = [(bx - lb * 0.55, by - 0.004), (bx + lb * 0.45, by - 0.004),
               (tx + larg_epine * 0.34, ty), (tx - larg_epine * 0.42, ty)]
        f.ajouter(plaque(R, pts, ep_epine, arrondi=0.0025), 0.006)
        f.ajouter(ell(P + R.U * tx + R.V * ty, (larg_epine * 0.4, 0.008, ep_epine * 1.6), axes=(u, v, w)), 0.004)
    if transv is not None:
        lg, lr, ep, monte, avance = transv
        for sw in (1, -1):
            depart = P + v * (rc * 0.35) + w * sw * rc * 0.6
            bout = depart + w * sw * lg + v * monte - u * avance
            f.ajouter(loft([depart, (depart + bout) / 2, bout], [lr * 0.8, lr, lr * 0.85], [ep * 1.4, ep, ep * 1.1],
                           haut=u, arrondi=0.0025), 0.006)
    return P, u, v, w


def cervicales():
    f = Forme()
    # atlas : anneau aux larges ailes, articulé avec le crâne
    P, T, L = VERT["C1"]
    u, v, w = repere_vertebre(P, T)
    f.ajouter(loft([P - u * L * 0.5, P + u * L * 0.5], [0.032, 0.032], [0.034, 0.034], haut=v, arrondi=0.008), 0.004)
    for sw in (1, -1):
        f.ajouter(plaque(Repere(P, u, v, V_vers=w * sw), [(-0.026, 0.02), (0.03, 0.02), (0.022, 0.092), (-0.022, 0.09)],
                         0.006, arrondi=0.004, decal=0.002), 0.008)
        f.ajouter(ell(P - u * 0.026 + w * sw * 0.026, (0.012, 0.018, 0.012), axes=(u, v, w)), 0.004)   # cavités pour le crâne
    f.creuser(cylindre(P - u * 0.06, P + u * 0.06, 0.017), 0.003)
    # axis : long corps et grande crête dorsale
    P2, u2, v2, w2 = vertebre(f, "C2", 0.026, haut_arc=0.028, canal=0.012, articulaires=0.011)
    L2 = VERT["C2"][2]
    R2 = Repere(P2, u2, w2, V_vers=v2)
    crete = [(-L2 * 0.62, 0.035), (L2 * 0.52, 0.042), (L2 * 0.58, 0.072), (L2 * 0.1, 0.082), (-L2 * 0.5, 0.06)]
    f.ajouter(plaque(R2, crete, 0.006, arrondi=0.003), 0.008)
    f.ajouter(ell(P2 - u2 * L2 * 0.56, (0.014, 0.016, 0.02), axes=(u2, v2, w2)), 0.004)        # dent de l'axis
    # C3 à C7 : apophyses transverses en « ailes », crête ventrale, épine qui grandit vers C7
    epines = {3: 0.035, 4: 0.042, 5: 0.05, 6: 0.065, 7: 0.10}
    for i in range(3, 8):
        nom = f"C{i}"
        P, T, L = VERT[nom]
        u, v, w = repere_vertebre(P, T)
        tip = P + v * (0.026 + 0.03 + epines[i]) + u * (0.006 if i < 7 else 0.012)
        vertebre(f, nom, 0.027 if i < 6 else 0.026, haut_arc=0.03, canal=0.013, epine=(tip[0], tip[1]),
                 larg_epine=0.016 if i < 7 else 0.022, ep_epine=0.005, articulaires=0.014)
        for sw in (1, -1):
            # apophyse transverse : lame dirigée vers l'avant et le bas, tubercule ventral
            a = P + w * sw * 0.024
            b = P + w * sw * 0.052 - v * 0.012 - u * 0.012
            lame = 0.016 if i < 6 else 0.026
            f.ajouter(loft([a, b], [0.012, lame], [0.007, 0.006], haut=u, arrondi=0.003), 0.006)
            if i == 6:      # C6 : grande lame ventrale
                f.ajouter(ell(P - v * 0.03 + w * sw * 0.035, (0.026, 0.014, 0.007), axes=(u, v, w)), 0.006)
        f.ajouter(ell(P - v * 0.022 + u * 0.01, (L * 0.36, 0.007, 0.007), axes=(u, v, w)), 0.006)   # crête ventrale
    return f


# Bout des apophyses épineuses des dorsales (x, y) : longues au garrot, penchées vers la queue.
EPINES_DORS = [(-0.618, 1.322), (-0.556, 1.375), (-0.496, 1.400), (-0.438, 1.408), (-0.378, 1.404),
               (-0.318, 1.396), (-0.258, 1.386), (-0.198, 1.376), (-0.138, 1.366), (-0.082, 1.356),
               (-0.028, 1.348), (0.024, 1.342), (0.074, 1.338)]


def dorsales():
    f = Forme()
    for i in range(13):
        nom = f"T{i + 1}"
        larg = 0.044 if i < 6 else 0.046
        vertebre(f, nom, 0.024 + 0.0008 * i, haut_arc=0.024, canal=0.011, epine=EPINES_DORS[i], larg_epine=larg,
                 ep_epine=0.006 - 0.0001 * i, transv=(0.04, 0.012, 0.009, 0.008, 0.0), articulaires=0.009)
        P, T, L = VERT[nom]
        u, v, w = repere_vertebre(P, T)
        for sw in (1, -1):    # facettes pour la tête et le tubercule des côtes
            f.ajouter(ell(P - u * L * 0.5 + v * 0.008 + w * sw * 0.02, (0.009, 0.009, 0.006), axes=(u, v, w)), 0.003)
    return f


def lombaires():
    f = Forme()
    for i in range(6):
        nom = f"L{i + 1}"
        P, T, L = VERT[nom]
        u, v, w = repere_vertebre(P, T)
        tip = P + v * 0.118 + u * (0.004 - 0.002 * i)
        lg = [0.098, 0.118, 0.13, 0.132, 0.122, 0.095][i]     # « étagères » : les plus longues au milieu
        vertebre(f, nom, 0.029, haut_arc=0.026, canal=0.012, epine=(tip[0], tip[1]), larg_epine=0.044,
                 ep_epine=0.0065, transv=(lg, 0.02 + 0.002 * (i == 2), 0.0055, 0.004, 0.012), articulaires=0.012)
    return f


def sacrum():
    """Sacrum : 5 vertèbres soudées en un coin triangulaire ; ailes articulées avec l'os du bassin,
    crête dorsale (épines soudées), 4 paires de trous sacrés."""
    f = Forme()
    P, T, L = VERT["S"]
    u, v, w = repere_vertebre(P, T)
    a, b = P - u * L / 2, P + u * L / 2
    f.ajouter(loft([a + v * 0.004, P - u * 0.04 + v * 0.002, P + u * 0.05, b - v * 0.003],
                   [0.027, 0.024, 0.02, 0.015], [0.04, 0.034, 0.026, 0.018], haut=v, arrondi=0.005), 0.012)
    R = Repere(P + v * 0.012, u, v, V_vers=w)
    tri = [(-L * 0.5, -0.03), (-L * 0.52, 0.0), (-L * 0.5, 0.105), (-L * 0.32, 0.105), (-L * 0.12, 0.06), (L * 0.5, 0.026),
           (L * 0.5, -0.026), (-L * 0.12, -0.06), (-L * 0.32, -0.105), (-L * 0.5, -0.105)]
    f.ajouter(plaque(R, tri, 0.013, arrondi=0.006), 0.012)
    for sw in (1, -1):    # surface d'articulation avec l'ilium, épaisse
        f.ajouter(ell(P - u * L * 0.38 + v * 0.02 + w * sw * 0.085, (0.04, 0.02, 0.022), axes=(u, v, w)), 0.012)
    Rc = Repere(P, u, w, V_vers=v)
    crete = [(-L * 0.48, 0.03), (L * 0.46, 0.02), (L * 0.42, 0.045), (-L * 0.1, 0.064), (-L * 0.46, 0.07)]
    f.ajouter(plaque(Rc, crete, 0.0055, arrondi=0.0025), 0.01)
    f.creuser(loft([a - u * 0.02 + v * 0.028, b + u * 0.02 + v * 0.022], [0.011, 0.007], [0.014, 0.008], haut=v), 0.002)
    for k in range(4):    # trous sacrés dorsaux
        c = a + u * (0.055 + 0.052 * k) + v * 0.02
        for sw in (1, -1):
            f.creuser(cylindre(c + w * sw * 0.034 - v * 0.05, c + w * sw * 0.034 + v * 0.05, 0.0065), 0.002)
    return f


def coccygiennes():
    f = Forme()
    for i in range(N_COCC):
        P, T, L = VERT[f"Co{i + 1}"]
        u, v, w = repere_vertebre(P, T)
        r = 0.02 - 0.0125 * i / (N_COCC - 1)
        # petit os en « bobine » : bouts élargis, milieu fin
        f.ajouter(loft([P - u * L / 2, P, P + u * L / 2], [r * 1.05, r * 0.72, r * 1.05], [r * 1.1, r * 0.75, r * 1.1],
                       haut=v, arrondi=0.003), 0.003)
        if i < 5:   # premières coccygiennes : arc, apophyses transverses et petite épine
            f.ajouter(ell(P + v * r * 1.1, (L * 0.35, r * 0.55, r * 0.7), axes=(u, v, w)), 0.004)
            for sw in (1, -1):
                f.ajouter(ell(P + w * sw * r * 1.5, (L * 0.32, r * 0.35, r * 0.8), axes=(u, v, w)), 0.004)
            f.creuser(cylindre(P - u * L, P + u * L, r * 0.38), 0.002)
    return f


# ================================================================ thorax
def _rib(i):
    """Points de contrôle de la côte i (0 = 1re côte), côté gauche ; renvoie (partie osseuse, cartilage)."""
    P, T, L = VERT[f"T{i + 1}"]
    x0, y0 = P[0] - L * 0.5, P[1] + 0.004             # tête de côte : entre T(i-1) et T(i)
    zmax = [0.17, 0.205, 0.235, 0.262, 0.283, 0.3, 0.312, 0.32, 0.326, 0.328, 0.326, 0.32, 0.31][i]
    ymax = [0.95, 0.96, 0.965, 0.97, 0.975, 0.98, 0.985, 0.99, 0.995, 1.0, 1.01, 1.02, 1.03][i]
    recul = 0.03 + 0.011 * i                          # la côte part vers l'arrière en descendant
    tete = (x0, y0, 0.026)
    tub = (x0 + 0.004, y0 + 0.012, 0.062)             # tubercule, sur l'apophyse transverse
    angle = (x0 + 0.012, y0 - 0.035, 0.06 + zmax * 0.3)
    milieu = (x0 + recul * 0.55, ymax, zmax)
    if i < 8:     # côtes « vraies » : le cartilage rejoint le sternum
        xs = [-0.648, -0.622, -0.564, -0.491, -0.418, -0.345, -0.272, -0.212][i]
        ys = 0.765 - 0.008 * i
        jonction = (x0 + recul * 0.85, 0.8 + 0.012 * i, 0.155 + 0.012 * i - 0.004 * max(0, i - 5) * 3)
        bas = (x0 + recul * 0.95, ymax - (ymax - jonction[1]) * 0.55, zmax * 0.82)
        fin = (xs, ys, 0.032)
        cart = [jonction, ((jonction[0] + xs) / 2, (jonction[1] + ys) / 2 - 0.012, (jonction[2] + 0.032) / 2 + 0.01), fin]
    else:         # côtes « asternales » : leurs cartilages forment l'arc costal
        k = i - 8
        jonction = (x0 + recul * 0.85, 0.83 + 0.035 * k, zmax * 0.72)
        bas = (x0 + recul * 0.95, ymax - (ymax - jonction[1]) * 0.55, zmax * 0.86)
        fin = (x0 + recul * 0.4 - 0.03, 0.75 + 0.05 * k, zmax * 0.48)
        cart = [jonction, ((jonction[0] + fin[0]) / 2 + 0.005, (jonction[1] + fin[1]) / 2 - 0.01, (jonction[2] + fin[2]) / 2 + 0.01), fin]
    if i == 0:    # 1re côte : courte et presque droite
        angle = (x0 + 0.006, y0 - 0.03, 0.09)
        milieu = (x0 + 0.012, 0.98, 0.14)
        bas = (x0 + 0.018, 0.87, 0.135)
        jonction = (x0 + 0.02, 0.82, 0.11)
        cart = [jonction, (x0 + 0.02, 0.79, 0.07), (-0.648, 0.772, 0.03)]
    return [tete, tub, angle, milieu, bas, jonction], cart


def cotes():
    """Les 13 côtes gauches : plates et larges (surtout en bas), tête et tubercule en haut, cartilage en bas."""
    f = Forme()
    for i in range(13):
        os_pts, cart = _rib(i)
        c = courbe(os_pts, n=26)
        n = len(c)
        t = np.linspace(0, 1, n)
        large = [0.014, 0.018, 0.021, 0.023, 0.024, 0.024, 0.023, 0.022, 0.021, 0.02, 0.018, 0.016, 0.013][i]
        a = 0.008 + (large - 0.008) * np.sin(np.clip(t * 1.25, 0, 1) * np.pi / 2)   # demi-largeur (le long du corps)
        b = 0.0075 - 0.002 * t                                                        # demi-épaisseur
        a[0], b[0] = 0.012, 0.011                                                    # tête de la côte
        f.ajouter(loft(c, a, b, haut=(1, 0, 0), arrondi=0.0025), 0.003)
        f.ajouter(ell(os_pts[1], (0.009, 0.008, 0.008)), 0.004)                      # tubercule
        cc = courbe(cart, n=10)
        ac = np.linspace(a[-1] * 0.85, 0.008, len(cc))
        f.ajouter(loft(cc, ac, np.full(len(cc), 0.0065), haut=(1, 0, 0), arrondi=0.002), 0.003, "cartilage")
    return f


def sternum():
    f = Forme()
    # manubrium (1re sternèbre) : aplati sur les côtés, pointe vers l'avant
    f.ajouter(loft([p3(-0.70, 0.79), p3(-0.665, 0.775), p3(-0.635, 0.765)], [0.022, 0.024, 0.02], [0.011, 0.014, 0.016],
                   haut=Y, arrondi=0.004), 0.006)
    # 6 sternèbres suivantes : de plus en plus larges et plates, séparées par du cartilage
    xs = np.linspace(-0.6, -0.235, 6)
    for k, x in enumerate(xs):
        y = 0.758 - 0.012 * k
        f.ajouter(boite(p3(x, y), (0.026, 0.012 - 0.0006 * k, 0.02 + 0.005 * k), arrondi=0.008), 0.004)
        if k < 5:
            f.ajouter(boite(p3(x + 0.036, y - 0.006), (0.01, 0.009, 0.017 + 0.005 * k), arrondi=0.006), 0.004, "cartilage")
    f.ajouter(boite(p3(-0.62, 0.762), (0.01, 0.01, 0.018), arrondi=0.006), 0.004, "cartilage")
    # appendice xiphoïde : cartilage large et plat
    f.ajouter(ell(p3(-0.15, 0.7), (0.065, 0.007, 0.045)), 0.01, "cartilage")
    f.ajouter(cap(p3(-0.215, 0.7), p3(-0.18, 0.7), 0.012, 0.01), 0.008)
    return f


# ================================================================ membre avant (côté gauche)
GLENE = p3(-0.745, 0.985, 0.25)          # cavité glénoïde (articulation de l'épaule)
DOS_PAL = p3(-0.505, 1.352, 0.152)       # milieu du bord dorsal de la palette
COUDE = p3(-0.575, 0.705, 0.236)         # condyle de l'humérus (articulation du coude)
CARPE = p3(-0.6, 0.40, 0.205)
BOULET_AV = p3(-0.611, 0.135, 0.2)


def repere_palette():
    U = DOS_PAL - GLENE
    return Repere(GLENE, U, (0.12, 0.05, 1.0), V_vers=(-1, 0, 0))     # v > 0 = vers l'avant


def palette():
    """Palette (omoplate, scapula) : lame triangulaire, épine (l'arête) qui sépare la petite fosse de
    devant (dessus de palette) de la grande fosse de derrière (paleron), acromion, col, cavité
    glénoïde, tubercule supraglénoïdien, cartilage de la palette."""
    f = Forme()
    R = repere_palette()
    L = np.linalg.norm(DOS_PAL - GLENE)
    lame = [(0.05, -0.03), (0.05, 0.026), (0.12, 0.048), (0.24, 0.07), (0.36, 0.088), (L - 0.012, 0.098),
            (L, 0.06), (L + 0.002, -0.04), (L - 0.01, -0.12), (L - 0.03, -0.145), (0.34, -0.128), (0.22, -0.094),
            (0.12, -0.06)]

    f.ajouter(plaque(R, lame, 0.0052, arrondi=0.0035), 0.004)
    bord_caudal = courbe([R.point(0.08, -0.042), R.point(0.16, -0.075), R.point(0.26, -0.104), R.point(0.36, -0.13),
                          R.point(L - 0.03, -0.142)], n=14)
    f.ajouter(loft(bord_caudal, [0.014, 0.012, 0.01, 0.008, 0.006], [0.013, 0.012, 0.01, 0.008, 0.006], haut=R.V,
                   arrondi=0.003), 0.012)
    bord_cranial = courbe([R.point(0.07, 0.03), R.point(0.18, 0.058), R.point(0.3, 0.08), R.point(L - 0.02, 0.097)], n=10)
    f.ajouter(loft(bord_cranial, [0.007, 0.006, 0.005, 0.005], [0.0075, 0.0065, 0.006, 0.006], haut=R.V, arrondi=0.002), 0.008)
    dehors = 1.0 if R.W[2] > 0 else -1.0
    epine = [(0.09, 0.0), (0.1, 0.022), (0.2, 0.036), (0.27, 0.04), (0.34, 0.03), (L - 0.02, 0.012), (L - 0.02, 0.0)]
    R_ep = Repere(R.point(0, 0.006), R.U, R.V, V_vers=R.W * dehors)
    f.ajouter(plaque(R_ep, epine, 0.0055, arrondi=0.0025), 0.006)
    f.ajouter(ell(R.point(0.255, 0.004, 0.042 * dehors), (0.04, 0.009, 0.007), axes=(R.U, R.V, R.W)), 0.008)   # tubérosité
    f.ajouter(ell(R.point(0.095, 0.004, 0.024 * dehors), (0.02, 0.007, 0.011), axes=(R.U, R.V, R.W)), 0.006)   # acromion
    f.ajouter(loft([R.point(0.13, -0.006), R.point(0.06, -0.002), R.point(0.015, 0.002)], [0.03, 0.03, 0.04],
                   [0.014, 0.018, 0.03], haut=R.V, arrondi=0.005), 0.012)                                       # col
    f.creuser(ell(R.point(-0.022, 0.0), (0.032, 0.03, 0.026), axes=(R.U, R.V, R.W)), 0.005)                      # cavité glénoïde
    f.ajouter(ell(R.point(0.022, 0.034, 0.002), (0.017, 0.013, 0.013), axes=(R.U, R.V, R.W)), 0.006)
    f.ajouter(ell(R.point(0.03, 0.03, -0.015 * dehors), (0.011, 0.009, 0.009), axes=(R.U, R.V, R.W)), 0.005)    # coracoïde
    cart = [(L - 0.004, 0.096), (L + 0.055, 0.09), (L + 0.062, -0.02), (L + 0.045, -0.13), (L - 0.012, -0.142),
            (L + 0.002, -0.04), (L, 0.06)]
    f.ajouter(plaque(R, cart, 0.0045, arrondi=0.0025), 0.004, "cartilage")
    return f


def os_long(f, axe, sections, haut, arrondi=0.004, k=0.006):
    """Corps d'un os long : section elliptique variable le long de l'axe (liste de points)."""
    a = [s[0] for s in sections]
    b = [s[1] for s in sections]
    f.ajouter(loft(axe, a, b, haut=haut, arrondi=arrondi), k)


def humerus():
    """Humérus (« boîte à moelle ») : tête en arrière, gros tubercule (pointe de l'épaule), corps tordu,
    tubérosité deltoïdienne, condyle en bobine et fosse de l'olécrane."""
    f = Forme()
    U = n_(DOS_PAL - GLENE)
    tete = GLENE - U * 0.03 + p3(0.006, 0.0, 0.0)
    axe = courbe([p3(-0.765, 0.955, 0.252), p3(-0.725, 0.88, 0.248), p3(-0.655, 0.8, 0.24), p3(-0.592, 0.728, 0.236)], n=12)
    sec = [(0.042, 0.046), (0.034, 0.038), (0.026, 0.028), (0.022, 0.024), (0.021, 0.022), (0.021, 0.023), (0.022, 0.025),
           (0.024, 0.028), (0.026, 0.032), (0.028, 0.036), (0.029, 0.04), (0.028, 0.04)]
    os_long(f, axe, sec, haut=(1, 0, 0), k=0.01)
    f.ajouter(ell(tete, (0.036, 0.034, 0.034)), 0.012)                                         # tête articulaire
    f.ajouter(ell(p3(-0.792, 0.972, 0.27), (0.026, 0.044, 0.024), rot=(0, 0, -25)), 0.014)   # gros tubercule, crânial
    f.ajouter(ell(p3(-0.772, 0.99, 0.28), (0.022, 0.03, 0.02)), 0.012)                        # gros tubercule, caudal
    f.ajouter(ell(p3(-0.776, 0.955, 0.222), (0.02, 0.03, 0.016)), 0.012)                      # petit tubercule (dedans)
    f.creuser(cap(p3(-0.812, 0.99, 0.247), p3(-0.79, 0.93, 0.247), 0.008), 0.004)             # gouttière du biceps
    f.ajouter(ell(p3(-0.712, 0.862, 0.264), (0.026, 0.012, 0.008), axes=((0.62, -0.78, 0), (0.78, 0.62, 0), Z)), 0.012)  # tubérosité deltoïdienne
    c = COUDE
    f.ajouter(ell(c + p3(0, 0, -0.022), (0.03, 0.03, 0.02)), 0.01)
    f.ajouter(ell(c + p3(0.002, 0.002, 0.019), (0.026, 0.027, 0.017)), 0.01)
    f.ajouter(cap(c + p3(0, 0, -0.03), c + p3(0, 0, 0.03), 0.021), 0.008)
    for sz, r in ((1, 0.014), (-1, 0.017)):                                                     # épicondyles
        f.ajouter(ell(c + p3(0.02, 0.022, sz * 0.03), (0.016, 0.024, r * 0.7)), 0.01)
    f.creuser(ell(c + p3(0.03, 0.034, 0.0), (0.016, 0.022, 0.014)), 0.005)                      # fosse de l'olécrane
    return f


def radius():
    """Radius (plat et large), cubitus soudé derrière avec l'olécrane (la pointe du coude), et les os du carpe."""
    f = Forme()
    z = 0.214
    axe = courbe([p3(-0.58, 0.674, z), p3(-0.592, 0.58, z - 0.002), p3(-0.597, 0.5, z - 0.005), p3(-0.6, 0.432, z - 0.008)], n=10)
    sec = [(0.024, 0.042), (0.019, 0.033), (0.016, 0.027), (0.015, 0.025), (0.015, 0.025), (0.0155, 0.026), (0.016, 0.028),
           (0.018, 0.032), (0.02, 0.037), (0.021, 0.04)]
    os_long(f, axe, sec, haut=(1, 0, 0), k=0.01)
    ul = courbe([p3(-0.494, 0.792, z + 0.008), p3(-0.522, 0.742, z + 0.01), p3(-0.55, 0.69, z + 0.012),
                 p3(-0.566, 0.635, z + 0.014), p3(-0.578, 0.56, z + 0.016), p3(-0.588, 0.48, z + 0.018),
                 p3(-0.593, 0.425, z + 0.02)], n=14)
    f.ajouter(loft(ul, [0.024, 0.03, 0.024, 0.013, 0.008, 0.006, 0.0085], [0.013, 0.013, 0.012, 0.009, 0.0065, 0.0055, 0.0065],
                   haut=(1, 0, 0), arrondi=0.003), 0.012)
    f.ajouter(ell(p3(-0.496, 0.796, z + 0.008), (0.017, 0.012, 0.016)), 0.008)                 # bout de la pointe du coude
    f.creuser(ell(COUDE + p3(0.002, 0.002, -0.02), (0.031, 0.03, 0.05)), 0.004)                 # échancrure pour le condyle
    for j, (y, h) in enumerate(((0.407, 0.0115), (0.381, 0.0105))):                            # carpe
        zs = (z - 0.026, z, z + 0.024) if j == 0 else (z - 0.016, z + 0.016)
        for zz in zs:
            f.ajouter(boite(p3(-0.6 - 0.002 * j, y, zz), (0.019, h, 0.0125 if j == 0 else 0.016), arrondi=0.006), 0.002)
    f.ajouter(ell(p3(-0.57, 0.405, z + 0.022), (0.016, 0.013, 0.008), rot=(0, 0, 20)), 0.004)   # os accessoire
    return f


def doigts(f, boulet, sens=-1, z0=0.2):
    """Deux doigts (III et IV) à 3 phalanges + sésamoïdes ; sens = -1 : onglons vers l'avant (-x)."""
    x0, y0 = boulet[0], boulet[1]
    for dz in (-0.0215, 0.0215):
        zz = z0 + dz * 1.12
        p1a = p3(x0 + sens * 0.004, y0 - 0.004, zz)
        p1b = p3(x0 + sens * 0.024, y0 - 0.058, zz)
        p2b = p3(x0 + sens * 0.038, y0 - 0.086, zz)
        f.ajouter(loft([p1a, (p1a + p1b) / 2, p1b], [0.0155, 0.012, 0.0135], [0.0155, 0.0125, 0.0135], haut=(1, 0, 0),
                       arrondi=0.003), 0.006)                                                     # 1re phalange
        f.ajouter(loft([p1b, p2b], [0.0135, 0.0125], [0.013, 0.0115], haut=(1, 0, 0), arrondi=0.003), 0.006)   # 2e
        R = Repere(p3(x0, 0, zz), (sens, 0, 0), (0, 0, 1), V_vers=(0, 1, 0))
        coin = [(0.026, 0.04), (0.018, 0.011), (0.078, 0.008), (0.05, 0.054)]
        f.ajouter(plaque(R, coin, 0.0105, arrondi=0.005, decal=-np.sign(dz) * 0.0015), 0.008)   # 3e : os de l'onglon
        f.ajouter(ell(p3(x0 - sens * 0.016, y0 + 0.006, zz - np.sign(dz) * 0.002), (0.009, 0.012, 0.0075)), 0.004)  # sésamoïde
    for dz in (-0.03, 0.03):     # ergots (doigts II et V, réduits)
        f.ajouter(ell(p3(x0 - sens * 0.034, y0 - 0.03, z0 + dz * 1.2), (0.007, 0.009, 0.006)), 0.002)


def canon_avant():
    """Métacarpe (canon : 2 os soudés, gouttière sur le devant) et doigts de l'avant."""
    f = Forme()
    z = 0.2
    haut, bas = p3(-0.602, 0.362, z + 0.002), p3(-0.61, 0.15, z)
    axe = courbe([haut, p3(-0.605, 0.3, z), p3(-0.608, 0.2, z), bas], n=8)
    sec = [(0.019, 0.03), (0.016, 0.026), (0.0145, 0.023), (0.014, 0.022), (0.014, 0.022), (0.0145, 0.023), (0.016, 0.027),
           (0.017, 0.031)]
    os_long(f, axe, sec, haut=(1, 0, 0), arrondi=0.003)
    f.creuser(cap(p3(-0.6265, 0.33, z), p3(-0.629, 0.18, z), 0.0035), 0.002)              # gouttière (2 os soudés)
    for dz in (-0.017, 0.017):                                                            # deux condyles en bas
        f.ajouter(ell(p3(-0.611, 0.14, z + dz), (0.017, 0.0165, 0.0135)), 0.003)
    f.ajouter(ell(p3(-0.6, 0.33, z + 0.03), (0.005, 0.03, 0.004)), 0.003)                  # 5e métacarpien, vestige
    doigts(f, BOULET_AV + p3(0, 0, 0), sens=-1, z0=z)
    return f


# ================================================================ membre arrière (côté gauche)
POINTE_HANCHE = p3(0.47, 1.318, 0.258)   # tubérosité coxale (la « hanche »)
SACREE = p3(0.552, 1.372, 0.052)         # tubérosité sacrée, près du sacrum
ACETABULE = p3(0.8, 1.0, 0.19)           # cavité de la hanche (articulation)
POINTE_FESSE = p3(1.04, 1.13, 0.112)     # tubérosité ischiatique
GRASSET = p3(0.69, 0.692, 0.215)         # condyles du fémur (articulation du grasset)
JARRET = p3(0.884, 0.418, 0.205)
BOULET_AR = p3(0.866, 0.132, 0.2)


def coxal():
    """Os coxal : aile de l'ilium (pointe de la hanche à trois bosses, tubérosité sacrée, crête),
    corps de l'ilium, cavité de la hanche, ischium et sa tubérosité (la pointe de la fesse),
    pubis, symphyse ; le trou obturé est le vide laissé au milieu du plancher."""
    f = Forme()
    col = p3(0.705, 1.11, 0.178)
    U = POINTE_HANCHE - col
    Ri = Repere(col, U, np.cross(U, SACREE - col), V_vers=(0, 0, -1))
    uv = lambda p: (float((np.asarray(p) - Ri.O) @ Ri.U), float((np.asarray(p) - Ri.O) @ Ri.V))
    aile = [uv(col + p3(0.03, -0.03, 0.02)), uv(POINTE_HANCHE + p3(0.03, -0.035, 0.0)), uv(POINTE_HANCHE + p3(-0.01, 0.0, 0.0)),
            uv((POINTE_HANCHE + SACREE) / 2 + p3(0.035, 0.0, 0.0)), uv(SACREE + p3(0.0, 0.0, 0.0)),
            uv(SACREE + p3(0.06, -0.06, 0.0)), uv(col + p3(0.04, 0.02, -0.06))]
    f.ajouter(plaque(Ri, aile, 0.0075, arrondi=0.004), 0.006)
    for chemin, r in (([POINTE_HANCHE, (POINTE_HANCHE + SACREE) / 2 + p3(0.03, 0.022, 0.0), SACREE], (0.016, 0.011, 0.013)),
                      ([POINTE_HANCHE, POINTE_HANCHE + p3(0.11, -0.09, -0.04), col + p3(0.015, -0.022, 0.012)], (0.02, 0.014, 0.018)),
                      ([SACREE, SACREE + p3(0.07, -0.07, 0.04), col + p3(0.02, 0.02, -0.02)], (0.012, 0.011, 0.016))):
        f.ajouter(loft(courbe(chemin, n=10), list(r), list(r), haut=Y, arrondi=0.003), 0.012)
    for d in (p3(0, 0.012, 0.0), p3(0.022, -0.026, 0.01), p3(-0.016, -0.022, -0.004)):     # 3 bosses de la hanche
        f.ajouter(ell(POINTE_HANCHE + d, (0.022, 0.019, 0.02)), 0.012)
    f.ajouter(ell(SACREE, (0.019, 0.017, 0.014)), 0.01)
    f.ajouter(loft(courbe([col + p3(-0.04, 0.05, 0.0), col, ACETABULE + p3(-0.024, 0.024, -0.008)], n=8),
                   [0.022, 0.022, 0.026], [0.017, 0.019, 0.024], haut=Y, arrondi=0.005), 0.014)
    f.ajouter(ell(ACETABULE, (0.045, 0.044, 0.038)), 0.012)
    f.creuser(ell(ACETABULE + p3(0.0, -0.012, 0.028), (0.033, 0.032, 0.025)), 0.005)          # cavité de la hanche
    sym_av, sym_mi, sym_ar = p3(0.848, 0.942, 0.012), p3(0.92, 0.952, 0.012), p3(0.99, 0.972, 0.012)
    anneau = [ACETABULE + p3(0.012, -0.034, -0.012), p3(0.832, 0.95, 0.11), sym_av + p3(0.004, 0.0, 0.016),
              sym_mi + p3(0, 0, 0.018), sym_ar + p3(0.0, 0.004, 0.016), p3(1.018, 1.02, 0.058),
              POINTE_FESSE + p3(-0.01, -0.03, -0.004), p3(0.97, 1.07, 0.148), p3(0.88, 1.02, 0.176),
              ACETABULE + p3(0.03, -0.01, -0.004)]
    rayons = np.array([0.024, 0.019, 0.021, 0.024, 0.024, 0.02, 0.022, 0.021, 0.023, 0.025])
    c = courbe(anneau, n=40)
    ra = np.interp(np.linspace(0, 1, 40), np.linspace(0, 1, 10), rayons)
    f.ajouter(loft(c, ra, ra * 0.75, haut=Y, arrondi=0.004), 0.012)
    f.ajouter(loft([sym_av + p3(0.0, 0.0, 0.03), sym_mi + p3(0, 0.002, 0.034), sym_ar + p3(0.0, 0.006, 0.03)],
                   [0.011, 0.012, 0.011], [0.036, 0.04, 0.036], haut=Y, arrondi=0.004), 0.012)
    for d, r in ((p3(0.0, 0.03, -0.004), 0.018), (p3(0.014, 0.0, 0.02), 0.016), (p3(-0.008, -0.04, 0.004), 0.016)):
        f.ajouter(ell(POINTE_FESSE + d, (r, r * 1.1, r * 0.9)), 0.012)
    f.ajouter(loft(courbe([ACETABULE + p3(0.034, 0.006, -0.004), p3(0.93, 1.07, 0.15), POINTE_FESSE + p3(-0.01, 0.0, 0.0)], n=8),
                   [0.022, 0.018, 0.02], [0.016, 0.014, 0.017], haut=Y, arrondi=0.004), 0.014)
    return f


def femur():
    """Fémur : tête dans la cavité de la hanche, grand trochanter, corps cylindrique,
    trochlée (gorge de la rotule) devant, deux condyles derrière."""
    f = Forme()
    tete = ACETABULE + p3(0.0, -0.004, 0.006)
    f.ajouter(ell(tete, (0.034, 0.034, 0.033)), 0.005)
    f.creuser(ell(tete + p3(0.0, -0.01, -0.032), (0.008, 0.008, 0.006)), 0.002)                   # fossette du ligament rond
    f.ajouter(loft([tete + p3(0.006, -0.008, 0.012), p3(0.818, 0.972, 0.232)], [0.022, 0.026], [0.02, 0.026], haut=Y,
                   arrondi=0.004), 0.008)                                                           # col
    f.ajouter(loft(courbe([p3(0.836, 1.048, 0.256), p3(0.848, 1.02, 0.262), p3(0.84, 0.98, 0.258)], n=5),
                   [0.022, 0.032, 0.026], [0.02, 0.022, 0.02], haut=(1, 0, 0), arrondi=0.005), 0.012)  # grand trochanter
    f.creuser(ell(p3(0.852, 1.0, 0.235), (0.012, 0.024, 0.012)), 0.004)                            # fosse trochantérique
    axe = courbe([p3(0.824, 0.985, 0.238), p3(0.79, 0.9, 0.232), p3(0.752, 0.82, 0.224), p3(0.712, 0.735, 0.217)], n=10)
    sec = [(0.036, 0.034), (0.03, 0.03), (0.025, 0.026), (0.023, 0.024), (0.0225, 0.0235), (0.023, 0.024), (0.024, 0.026),
           (0.027, 0.03), (0.031, 0.034), (0.034, 0.038)]
    os_long(f, axe, sec, haut=(1, 0, 0), k=0.012)
    f.ajouter(ell(p3(0.82, 0.93, 0.212), (0.014, 0.022, 0.01)), 0.008)                             # petit trochanter (dedans)
    # bas : trochlée en avant (lèvre interne plus grosse), condyles en arrière, fosse entre les deux
    f.ajouter(ell(p3(0.69, 0.712, 0.215), (0.038, 0.034, 0.036)), 0.016)                           # bloc du bas
    for dz, r in ((-0.022, 0.017), (0.019, 0.014)):
        f.ajouter(ell(p3(0.668, 0.735, 0.215 + dz), (r, 0.04, r * 0.75), rot=(0, 0, -20)), 0.01)
        f.ajouter(ell(p3(0.703, 0.695, 0.215 + dz * 1.1), (0.032, 0.032, 0.0185)), 0.01)
    f.creuser(ell(p3(0.708, 0.682, 0.215), (0.03, 0.02, 0.009)), 0.003)                            # fosse intercondylaire
    f.creuser(ell(p3(0.73, 0.77, 0.232), (0.01, 0.018, 0.008)), 0.003)                             # fosse supracondylaire
    return f


def rotule():
    f = Forme()
    c = p3(0.636, 0.735, 0.215)
    f.ajouter(ell(c, (0.02, 0.036, 0.024), rot=(0, 0, -22)), 0.004)
    f.ajouter(ell(c + p3(-0.004, 0.022, 0.0), (0.017, 0.012, 0.02)), 0.006)                         # base, en haut
    f.creuser(ell(c + p3(0.028, 0.0, 0.0), (0.012, 0.03, 0.03), rot=(0, 0, -22)), 0.003)           # face articulaire
    return f


def tibia():
    """Tibia : plateau avec deux condyles, tubérosité et crête devant, malléoles en bas ;
    péroné réduit ; tarse avec l'astragale et le calcanéum (pointe du jarret)."""
    f = Forme()
    z = 0.21
    axe = courbe([p3(0.688, 0.652, z), p3(0.75, 0.57, z), p3(0.82, 0.495, z - 0.002), p3(0.872, 0.45, z - 0.004)], n=10)
    sec = [(0.034, 0.046), (0.028, 0.034), (0.022, 0.025), (0.019, 0.021), (0.018, 0.02), (0.018, 0.02), (0.018, 0.021),
           (0.02, 0.024), (0.023, 0.03), (0.024, 0.034)]
    os_long(f, axe, sec, haut=(-0.75, -0.66, 0), k=0.01)
    for dz in (-0.022, 0.022):
        f.ajouter(ell(p3(0.692, 0.662, z + dz), (0.027, 0.012, 0.02)), 0.008)
    f.ajouter(ell(p3(0.662, 0.645, z), (0.014, 0.022, 0.016)), 0.01)                               # tubérosité tibiale
    f.ajouter(loft([p3(0.664, 0.64, z), p3(0.693, 0.6, z + 0.001), p3(0.728, 0.552, z)], [0.013, 0.01, 0.005],
                   [0.008, 0.007, 0.005], haut=(0, 0, 1), arrondi=0.002), 0.014)                   # crête tibiale
    f.ajouter(ell(p3(0.705, 0.648, z + 0.044), (0.01, 0.014, 0.008)), 0.008)                       # tête du péroné (soudée)
    f.ajouter(ell(p3(0.884, 0.432, z + 0.03), (0.012, 0.015, 0.008)), 0.006)                       # os malléolaire (dehors)
    f.ajouter(ell(p3(0.878, 0.436, z - 0.03), (0.013, 0.017, 0.008)), 0.006)                       # malléole interne
    f.ajouter(ell(p3(0.884, 0.41, z), (0.022, 0.024, 0.022)), 0.004)
    for dz in (-0.011, 0.011):
        f.ajouter(cap(p3(0.878, 0.41, z + dz), p3(0.89, 0.41, z + dz), 0.019), 0.004)
    f.ajouter(loft(courbe([p3(0.882, 0.385, z + 0.02), p3(0.915, 0.43, z + 0.022), p3(0.952, 0.48, z + 0.02)], n=6),
                   [0.017, 0.014, 0.016], [0.012, 0.011, 0.013], haut=(1, 0, 0), arrondi=0.004), 0.01)   # calcanéum
    f.ajouter(ell(p3(0.962, 0.492, z + 0.019), (0.017, 0.015, 0.017)), 0.008)                         # pointe du jarret
    f.ajouter(boite(p3(0.88, 0.383, z), (0.021, 0.0105, 0.026), arrondi=0.005), 0.004)                # os central et 4e tarsien
    return f


def canon_arriere():
    """Métatarse (canon arrière, plus long et plus carré que l'avant) et doigts de l'arrière."""
    f = Forme()
    z = 0.2
    haut, bas = p3(0.878, 0.37, z), p3(0.866, 0.148, z)
    axe = courbe([haut, p3(0.875, 0.3, z), p3(0.87, 0.2, z), bas], n=8)
    sec = [(0.019, 0.023), (0.0165, 0.02), (0.0155, 0.018), (0.015, 0.018), (0.015, 0.018), (0.0155, 0.019), (0.016, 0.024),
           (0.017, 0.029)]
    os_long(f, axe, sec, haut=(1, 0, 0), arrondi=0.003)
    f.creuser(cap(p3(0.859, 0.35, z), p3(0.851, 0.17, z), 0.004), 0.002)                         # gouttière, profonde
    for dz in (-0.017, 0.017):
        f.ajouter(ell(p3(0.866, 0.138, z + dz), (0.017, 0.0165, 0.0135)), 0.003)
    doigts(f, BOULET_AR, sens=-1, z0=z)
    return f


# ================================================================ tête
def crane():
    """Crâne de bovin : front large et plat (le plus grand os de la tête), chignon entre les cornes,
    chevilles osseuses des cornes, orbites fermées sur les côtés, arcades zygomatiques, nuque plate,
    face longue à section carrée, tubérosité faciale, os incisif sans dents ; mâchoire inférieure
    (corps, angle arrondi, branche montante, condyle et apophyse coronoïde) ; dents."""
    f = Forme()
    O = p3(-1.214, 1.438)                         # chignon (haut de la nuque)
    S = n_(p3(-1.598, 0.99) - O)                  # le long du chanfrein, vers le bout du nez
    D = n_(np.cross(Z, S))                        # vers l'arrière et le bas : sous la tête
    pt = lambda s, d, z=0.0: O + S * s + D * d + Z * z
    ax = (S, D, Z)
    # front : grande plaque épaisse, la plus large aux orbites
    fs = [0.0, 0.03, 0.08, 0.13, 0.2, 0.26, 0.33]
    f.ajouter(loft([pt(s_, 0.02) for s_ in fs], [0.02, 0.022, 0.022, 0.021, 0.02, 0.019, 0.016],
                   [0.072, 0.092, 0.084, 0.09, 0.1, 0.088, 0.068], haut=D, arrondi=0.008, carre=2.6), 0.012)
    f.ajouter(cap(pt(0.012, 0.012, -0.082), pt(0.012, 0.012, 0.082), 0.021), 0.014)          # chignon
    # boîte crânienne sous le front, nuque plate derrière, condyles de l'occipital en bas
    f.ajouter(ell(pt(0.075, 0.085), (0.075, 0.068, 0.072), axes=ax), 0.02)
    f.ajouter(loft([pt(0.004, 0.01), pt(0.0, 0.08), pt(0.012, 0.15)], [0.016, 0.017, 0.016], [0.08, 0.075, 0.055],
                   haut=S, arrondi=0.006, carre=3.0), 0.016)
    for sz in (1, -1):
        f.ajouter(ell(pt(0.018, 0.168, 0.031 * sz), (0.016, 0.022, 0.014), axes=ax), 0.006)  # condyles
        f.ajouter(ell(pt(0.035, 0.175, 0.062 * sz), (0.01, 0.026, 0.009), axes=ax), 0.006)   # apophyses paracondylaires
        f.ajouter(ell(pt(0.075, 0.15, 0.05 * sz), (0.016, 0.014, 0.016), axes=ax), 0.008)     # bulles tympaniques
    f.creuser(cylindre(pt(-0.03, 0.155), pt(0.06, 0.155), 0.016), 0.004)                        # trou occipital
    # face : section carrée qui s'amincit jusqu'au bout du nez, palais en dessous
    ss = [0.2, 0.26, 0.31, 0.37, 0.43, 0.49, 0.54, 0.585]
    dc = [0.068, 0.068, 0.065, 0.058, 0.05, 0.042, 0.034, 0.028]
    hd = [0.066, 0.068, 0.066, 0.058, 0.048, 0.038, 0.029, 0.022]
    lz = [0.082, 0.08, 0.077, 0.071, 0.063, 0.054, 0.046, 0.04]
    f.ajouter(loft([pt(a, b) for a, b in zip(ss, dc)], hd, lz, haut=D, arrondi=0.008, carre=2.5), 0.016)
    for sz in (1, -1):
        # orbite : rebord osseux complet, creux de l'œil, masse qui la relie au front
        oc = pt(0.205, 0.036, 0.108 * sz)
        regard = n_(Z * sz * 0.9 - S * 0.25 + D * 0.1)
        f.ajouter(ell(pt(0.2, 0.034, 0.085 * sz), (0.045, 0.04, 0.03), axes=ax), 0.014)
        f.ajouter(ell(oc, (0.038, 0.036, 0.024), axes=ax), 0.012)
        f.creuser(ell(oc + regard * 0.022, (0.031, 0.029, 0.032), axes=ax), 0.006)
        # arcade zygomatique : du bas de l'orbite vers l'articulation de la mâchoire
        f.ajouter(loft([pt(0.235, 0.072, 0.112 * sz), pt(0.18, 0.1, 0.108 * sz), pt(0.13, 0.128, 0.096 * sz)],
                       [0.012, 0.009, 0.011], [0.007, 0.006, 0.008], haut=D, arrondi=0.003), 0.008)
        f.creuser(ell(pt(0.135, 0.07, 0.092 * sz), (0.034, 0.03, 0.02), axes=ax), 0.008)       # fosse temporale
        f.ajouter(ell(pt(0.31, 0.078, 0.075 * sz), (0.024, 0.014, 0.01), axes=ax), 0.01)       # tubérosité faciale
        # chevilles osseuses des cornes (sous la corne), dirigées sur le côté puis vers le haut
        corne = courbe([pt(0.015, 0.012, 0.075 * sz), p3(-1.206, 1.46, 0.165 * sz), p3(-1.2, 1.49, 0.232 * sz),
                        p3(-1.222, 1.54, 0.28 * sz)], n=10)
        f.ajouter(loft(corne, np.linspace(0.032, 0.009, 10), np.linspace(0.027, 0.008, 10), haut=Y, arrondi=0.004), 0.014)
        # 6 dents du haut (3 prémolaires, 3 molaires), sous le maxillaire
        for j in range(6):
            t = j / 5
            f.ajouter(boite(pt(0.3 + 0.15 * t, 0.124 - 0.034 * t, (0.06 - 0.014 * t) * sz),
                            (0.011, 0.014, 0.0095), arrondi=0.004, axes=ax), 0.003, "dent")
    # ouverture du nez (entre os du nez et os incisifs) ; bout incisif sans dents (bourrelet)
    f.creuser(ell(pt(0.575, 0.0), (0.06, 0.03, 0.032), axes=ax), 0.008)
    f.ajouter(ell(pt(0.565, 0.045), (0.03, 0.013, 0.04), axes=ax), 0.01)
    # mâchoire inférieure
    for sz in (1, -1):
        Rm = Repere(p3(0, 0, 0.088 * sz), (1, 0, 0), (0, 0, 1), V_vers=(0, 1, 0))
        branche = [(-1.198, 1.11), (-1.192, 1.2), (-1.2, 1.232), (-1.222, 1.226), (-1.245, 1.215), (-1.252, 1.3),
                   (-1.268, 1.305), (-1.285, 1.22), (-1.305, 1.13), (-1.29, 1.075), (-1.25, 1.047), (-1.215, 1.058)]
        f.ajouter(plaque(Rm, branche, 0.0085, arrondi=0.004), 0.008)
        f.ajouter(ell(p3(-1.205, 1.236, 0.092 * sz), (0.013, 0.01, 0.019)), 0.005)          # condyle
        corps = courbe([p3(-1.262, 1.08, 0.088 * sz), p3(-1.33, 1.072, 0.08 * sz), p3(-1.42, 1.025, 0.066 * sz),
                        p3(-1.5, 0.983, 0.048 * sz), p3(-1.575, 0.952, 0.028 * sz), p3(-1.612, 0.952, 0.014 * sz)], n=12)
        f.ajouter(loft(corps, [0.034, 0.034, 0.03, 0.019, 0.016, 0.014], [0.013, 0.013, 0.012, 0.01, 0.009, 0.01],
                       haut=Y, arrondi=0.004), 0.01)
        for j in range(6):
            t = j / 5
            f.ajouter(boite(p3(-1.302 - 0.135 * t, 1.115 - 0.072 * t, (0.073 - 0.016 * t) * sz), (0.011, 0.012, 0.0085),
                            arrondi=0.004), 0.003, "dent")
    f.ajouter(ell(p3(-1.605, 0.948, 0.0), (0.016, 0.014, 0.022)), 0.008)                       # symphyse du menton
    for j, a in enumerate(np.linspace(-1, 1, 8)):                                              # 8 incisives, en bas seulement
        f.ajouter(ell(p3(-1.628 + 0.008 * abs(a), 0.968 + 0.006 * abs(a), 0.025 * a), (0.008, 0.014, 0.0045),
                      rot=(0, 0, -35)), 0.002, "dent")
    return f


OS_BOEUF = [
    ("crane", crane, False, 16000, 0.003), ("cervicales", cervicales, False, 10000, 0.003),
    ("dorsales", dorsales, False, 13000, 0.003), ("cotes", cotes, True, 11000, 0.003),
    ("sternum", sternum, False, 2500, 0.003), ("lombaires", lombaires, False, 7500, 0.003),
    ("sacrum", sacrum, False, 3600, 0.003), ("coccygiennes", coccygiennes, False, 4500, 0.003),
    ("palette", palette, True, 7000, 0.0025), ("humerus", humerus, True, 3800, 0.003),
    ("radius", radius, True, 4400, 0.003), ("canon-avant", canon_avant, True, 5000, 0.0025),
    ("coxal", coxal, True, 12000, 0.003), ("femur", femur, True, 4200, 0.003), ("rotule", rotule, True, 700, 0.003),
    ("tibia", tibia, True, 4800, 0.003), ("canon-arriere", canon_arriere, True, 5000, 0.0025),
]

SQUELETTES = {"boeuf": OS_BOEUF}

# Repères utiles aux muscles (côté gauche).
REPERES = {
    "glene": GLENE, "dos_palette": DOS_PAL, "coude": COUDE, "carpe": CARPE, "boulet_av": BOULET_AV,
    "pointe_hanche": POINTE_HANCHE, "sacree": SACREE, "acetabule": ACETABULE, "pointe_fesse": POINTE_FESSE,
    "grasset": GRASSET, "jarret": JARRET, "boulet_ar": BOULET_AR,
}
