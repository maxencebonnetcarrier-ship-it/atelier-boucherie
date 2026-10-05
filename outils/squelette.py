# Squelette 3D du bœuf, placé à l'intérieur du modèle de formes.py (mêmes coordonnées :
# x = longueur, tête vers -x ; y = hauteur ; z = largeur ; côté gauche = z > 0).
#
# Les os gardent leurs VRAIES FORMES (tête du fémur, palette avec son arête, bassin avec le
# trou obturé, crâne avec orbites et chevilles osseuses, pointe du coude, pointe du jarret,
# deux doigts…), simplifiées et arrondies pour un rendu « dessin animé ».
# Places d'après la fiche « Le squelette du bovin » (École des Métiers Bigard, sources/) :
# 7 cervicales, 13 dorsales, 13 paires de côtes, sternum, 6 lombaires, 5 sacrées,
# 16 à 20 coccygiennes, palette, humérus, radius-cubitus, carpe, métacarpe, coxal (ilium,
# ischium, pubis), fémur, rotule, tibia, tarse (calcanéum), métatarse, phalanges.
#
# Parties : « corps » = os, « cartilage » (bout des côtes, bord de la palette), « dent ».
import numpy as np

from formes import Sculpture, ellipsoide, os_

# ---------------------------------------------------------------- primitives

def _n(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v)


def polygone2d(px, py, pts):
    """Distance signée à un polygone 2D (négative dedans)."""
    v = np.asarray(pts, np.float32)
    d = (px - v[0, 0]) ** 2 + (py - v[0, 1]) ** 2
    s = np.ones_like(px)
    j = len(v) - 1
    for i in range(len(v)):
        ex, ey = v[j, 0] - v[i, 0], v[j, 1] - v[i, 1]
        wx, wy = px - v[i, 0], py - v[i, 1]
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0, 1)
        bx, by = wx - ex * t, wy - ey * t
        d = np.minimum(d, bx * bx + by * by)
        c1, c2, c3 = py >= v[i, 1], py < v[j, 1], ex * wy > ey * wx
        s = np.where((c1 & c2 & c3) | (~c1 & ~c2 & ~c3), -s, s)
        j = i
    return s * np.sqrt(d)


class Repere:
    """Plan local : origine O, axe U, axe V (dans le plan), normale W."""

    def __init__(self, O, U, normale, V_vers=None):
        self.O = np.asarray(O, np.float32)
        self.U = _n(U)
        W = np.asarray(normale, np.float64)
        self.W = _n(W - (W @ self.U) * self.U)
        self.V = _n(np.cross(self.W, self.U))
        if V_vers is not None and self.V @ np.asarray(V_vers) < 0:
            self.V = -self.V
            self.W = -self.W

    def point(self, u, v, w=0.0):
        return tuple((self.O + u * self.U + v * self.V + w * self.W).tolist())

    def local(self, P):
        q = P - self.O
        return q @ self.U.astype(np.float32), q @ self.V.astype(np.float32), q @ self.W.astype(np.float32)


def plaque(R, pts, e, r=0.004, decal=0.0):
    """Os plat : polygone (u, v) du repère R, épaisseur 2e, bords arrondis de r."""
    def f(P):
        u, v, w = R.local(P)
        d2 = polygone2d(u, v, pts)
        dw = np.abs(w - decal) - e
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dw, 0) ** 2)
        return np.minimum(np.maximum(d2, dw), 0) + dehors - r
    return f


def capsule(a, b, ra, rb):
    return lambda P: os_(P, a, b, ra, rb)


def boule(c, r, rot=None):
    if np.isscalar(r):
        r = (r, r, r)
    return lambda P: ellipsoide(P, c, r, rot)


def diaphyse(s, a, b, ra, rb, taille=0.82, k=0.012):
    """Corps d'un os long : deux capsules qui s'affinent vers le milieu (taille de guêpe)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    m = (a + b) / 2
    rm = min(ra, rb) * taille
    s.ajouter(capsule(tuple(a), tuple(m), ra, rm), k)
    s.ajouter(capsule(tuple(m), tuple(b), rm, rb), k)


def trou_traversant(s, c, n, r, k=0.004):
    """Perce un trou rond de rayon r centré en c, dans la direction n."""
    c, n = np.asarray(c, float), _n(n)
    s.creuser(capsule(tuple(c - n * 0.2), tuple(c + n * 0.2), r, r), k)


# ---------------------------------------------------------------- colonne vertébrale
X_DORS = [-0.64 + 0.055 * i for i in range(13)]
Y_DORS = [float(np.interp(i, [0, 5, 12], [1.17, 1.24, 1.25])) for i in range(13)]
EPINES = [1.36, 1.40, 1.41, 1.41, 1.40, 1.385, 1.37, 1.36, 1.355, 1.345, 1.34, 1.335, 1.33]
X_LOMB = [0.09 + 0.068 * j for j in range(6)]
RXY = Repere((0, 0, 0), (1, 0, 0), (0, 0, 1), V_vers=(0, 1, 0))   # plan du milieu (x, y)


def vertebre(s, x, y, rc=0.025, long=0.022, haut_epine=None, incl=0.03, larg_epine=0.016, transv=0.05, transv_plat=False):
    """Une vertèbre : corps (cylindre arrondi), arc, apophyse épineuse en lame, apophyses transverses."""
    s.ajouter(capsule((x - long, y, 0), (x + long, y, 0), rc, rc), 0.004)
    s.ajouter(boule((x, y + rc * 0.95, 0), (long * 0.9, rc * 0.55, rc * 0.75)), 0.008)       # arc
    if haut_epine:
        h = haut_epine - y
        pts = [(x - larg_epine, y + rc), (x + larg_epine * 0.7, y + rc),
               (x + incl + larg_epine * 0.45, y + h), (x + incl - larg_epine * 0.55, y + h)]
        s.ajouter(plaque(RXY, pts, 0.0045, r=0.003), 0.006)
        s.ajouter(boule((x + incl, y + h, 0), (larg_epine * 0.62, 0.008, 0.008)), 0.004)     # bout arrondi
    if transv_plat:   # lombaires : longues « étagères » horizontales
        s.ajouter(boule((x, y + 0.002, 0), (0.017, 0.0055, transv)), 0.006)
    else:
        s.ajouter(boule((x, y + rc * 0.5, 0), (0.012, 0.01, transv)), 0.006)


def cervicales():
    s = Sculpture()
    pts = [(-1.12, 1.27), (-1.06, 1.22), (-0.995, 1.17), (-0.93, 1.135), (-0.86, 1.11), (-0.785, 1.105), (-0.705, 1.13)]
    for i, (x, y) in enumerate(pts):
        if i == 0:   # atlas : un anneau à larges ailes
            s.ajouter(boule((x, y, 0), (0.026, 0.03, 0.04)), 0.004)
            s.ajouter(boule((x + 0.004, y + 0.004, 0), (0.024, 0.012, 0.085)), 0.01)
            trou_traversant(s, (x, y, 0), (1, 0, 0), 0.014)
        elif i == 1:  # axis : longue crête
            vertebre(s, x, y, rc=0.027, long=0.03, transv=0.04)
            pts_crete = [(x - 0.035, y + 0.02), (x + 0.03, y + 0.02), (x + 0.035, y + 0.06), (x - 0.025, y + 0.055)]
            s.ajouter(plaque(RXY, pts_crete, 0.006, r=0.004), 0.006)
        else:
            vertebre(s, x, y, rc=0.028, long=0.026, haut_epine=y + (0.10 if i == 6 else 0.035 + 0.008 * i),
                     incl=0.01, larg_epine=0.013, transv=0.055)
            for sz in (1, -1):   # apophyses articulaires (les « ailes » des cervicales)
                s.ajouter(boule((x + 0.022, y + 0.022, 0.03 * sz), (0.014, 0.012, 0.016)), 0.006)
    return s


def dorsales():
    s = Sculpture()
    for x, y, h in zip(X_DORS, Y_DORS, EPINES):
        vertebre(s, x, y, rc=0.024, long=0.019, haut_epine=h, incl=0.045, larg_epine=0.017, transv=0.042)
    return s


def lombaires():
    s = Sculpture()
    for x in X_LOMB:
        vertebre(s, x, 1.25, rc=0.027, long=0.024, haut_epine=1.33, incl=0.012, larg_epine=0.02, transv=0.125, transv_plat=True)
    return s


def sacrum():
    s = Sculpture()
    for i, x in enumerate(np.linspace(0.50, 0.78, 5)):
        s.ajouter(boule((x, 1.262 - 0.004 * i, 0), (0.034, 0.025 - 0.002 * i, 0.055 - 0.007 * i)), 0.02)
    pts = [(0.48, 1.285), (0.80, 1.27), (0.79, 1.30), (0.50, 1.325)]   # crête sacrée
    s.ajouter(plaque(RXY, pts, 0.006, r=0.004), 0.01)
    s.ajouter(boule((0.51, 1.262, 0), (0.035, 0.02, 0.105)), 0.02)       # ailes du sacrum
    return s


def coccygiennes():
    s = Sculpture()
    pts = np.array([(0.82, 1.27), (0.9, 1.3), (0.98, 1.33), (1.03, 1.33), (1.06, 1.25),
                    (1.075, 1.12), (1.085, 0.98), (1.09, 0.84), (1.09, 0.70)])
    longueurs = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    n = 18
    pas = longueurs[-1] / n
    for i in range(n):
        t0, t1 = i * pas + pas * 0.12, (i + 1) * pas - pas * 0.12
        a = (float(np.interp(t0, longueurs, pts[:, 0])), float(np.interp(t0, longueurs, pts[:, 1])), 0)
        b = (float(np.interp(t1, longueurs, pts[:, 0])), float(np.interp(t1, longueurs, pts[:, 1])), 0)
        r = 0.022 - 0.014 * i / (n - 1)
        s.ajouter(capsule(a, b, r, r), 0.004)                            # petit os en « osselet »
        s.ajouter(boule(a, r * 1.18), 0.006)
        s.ajouter(boule(b, r * 1.18), 0.006)
    return s


# ---------------------------------------------------------------- thorax
def cotes(sz):
    s = Sculpture()
    for i, (x0, y0) in enumerate(zip(X_DORS, Y_DORS)):
        rz = [0.22, 0.27, 0.30, 0.32, 0.33, 0.335, 0.34, 0.34, 0.34, 0.335, 0.33, 0.33, 0.32][i]
        fin = 0.97 if i < 8 else [0.86, 0.79, 0.73, 0.67, 0.61][i - 8]
        pente = 0.06 + 0.008 * i
        yc, haut, bas = 0.98, y0 - 0.98, 0.28
        pts = []
        for t in np.linspace(0.05, fin, 16):
            phi = np.pi * t
            c = np.cos(phi)
            pts.append((x0 + pente * t, yc + (haut if c > 0 else bas) * c, sz * rz * np.sin(phi)))
        pts = [(x0 + 0.004, y0, sz * 0.03)] + pts
        n_os = int(len(pts) * (0.74 if i < 8 else 0.8))
        for j in range(len(pts) - 1):
            partie = "corps" if j < n_os else "cartilage"
            a, b = np.array(pts[j]), np.array(pts[j + 1])
            for dx in (-0.006, 0.006):    # deux brins côte à côte : une côte plate et large
                s.ajouter(capsule(tuple(a + (dx, 0, 0)), tuple(b + (dx, 0, 0)), 0.0105, 0.0105), 0.004, partie)
        s.ajouter(boule((x0 + 0.004, y0 + 0.004, sz * 0.03), (0.014, 0.014, 0.014)), 0.006)    # tête de la côte
    return s


def sternum():
    s = Sculpture()
    xs = np.linspace(-0.62, -0.17, 7)
    for i, x in enumerate(xs):
        s.ajouter(boule((x, 0.73 - 0.04 * i / 6, 0), (0.03, 0.016, 0.03)), 0.008)
    s.ajouter(capsule((-0.66, 0.75, 0), (-0.62, 0.73, 0), 0.016, 0.02), 0.01)                  # manubrium
    s.ajouter(boule((-0.10, 0.685, 0), (0.05, 0.007, 0.04)), 0.01, "cartilage")               # cartilage xiphoïde
    return s


# ---------------------------------------------------------------- tête
def crane():
    s = Sculpture()
    # boîte crânienne et front large et plat (le chignon en haut, entre les cornes)
    s.ajouter(boule((-1.235, 1.33, 0), (0.105, 0.105, 0.105)), 0.03)
    s.ajouter(boule((-1.26, 1.38, 0), (0.07, 0.07, 0.13), rot=(0, 0, -35)), 0.03)
    s.ajouter(capsule((-1.205, 1.44, -0.12), (-1.205, 1.44, 0.12), 0.03, 0.03), 0.03)        # chignon
    # face : longue et fine, os du nez, mâchoire supérieure
    s.ajouter(capsule((-1.32, 1.26, 0), (-1.555, 1.0, 0), 0.075, 0.045), 0.04)
    s.ajouter(capsule((-1.30, 1.31, 0), (-1.53, 1.05, 0), 0.035, 0.025), 0.03)
    s.ajouter(boule((-1.565, 0.985, 0), (0.035, 0.03, 0.055)), 0.02)
    for sz in (1, -1):
        # chevilles osseuses des cornes
        s.ajouter(capsule((-1.205, 1.44, 0.11 * sz), (-1.19, 1.49, 0.22 * sz), 0.03, 0.017), 0.015)
        s.ajouter(capsule((-1.19, 1.49, 0.22 * sz), (-1.215, 1.565, 0.28 * sz), 0.017, 0.008), 0.01)
        # rebord des orbites, puis orbite creusée
        s.ajouter(boule((-1.31, 1.30, 0.098 * sz), (0.045, 0.042, 0.03)), 0.015)
        s.creuser(boule((-1.315, 1.30, 0.125 * sz), (0.032, 0.03, 0.035)), 0.006)
        # arcade zygomatique
        s.ajouter(capsule((-1.29, 1.22, 0.1 * sz), (-1.39, 1.20, 0.085 * sz), 0.013, 0.011), 0.01)
        # mâchoire inférieure : branche montante, angle, corps jusqu'au menton
        s.ajouter(capsule((-1.29, 1.26, 0.095 * sz), (-1.30, 1.13, 0.092 * sz), 0.012, 0.02), 0.01)
        s.ajouter(boule((-1.30, 1.125, 0.09 * sz), (0.04, 0.03, 0.01)), 0.01)
        s.ajouter(capsule((-1.32, 1.115, 0.088 * sz), (-1.56, 0.94, 0.03 * sz), 0.02, 0.013), 0.01)
        # dents de joue (molaires), en haut et en bas
        for j, t in enumerate(np.linspace(0, 1, 6)):
            x = -1.36 - 0.11 * t
            s.ajouter(boule((x, 1.135 - 0.08 * t + 0.02, 0.085 * sz - 0.02 * t * sz), (0.009, 0.01, 0.008)), 0.003, "dent")
            s.ajouter(boule((x, 1.135 - 0.08 * t + 0.045, 0.085 * sz - 0.02 * t * sz), (0.009, 0.01, 0.008)), 0.003, "dent")
    s.creuser(boule((-1.585, 1.01, 0), (0.02, 0.018, 0.03)), 0.006)                              # ouverture du nez
    # incisives (en bas seulement : le bœuf n'en a pas en haut)
    for j, a in enumerate(np.linspace(-1, 1, 8)):
        s.ajouter(boule((-1.585 + 0.006 * abs(a), 0.935 + 0.005 * abs(a), 0.03 * a), (0.008, 0.012, 0.005)), 0.002, "dent")
    return s


# ---------------------------------------------------------------- membre avant
def palette(sz):
    s = Sculpture()
    O = np.array((-0.745, 0.985, 0.27 * sz))
    haut = np.array((-0.50, 1.38, 0.205 * sz))
    R = Repere(O, haut - O, (0.12, 0.1, sz), V_vers=(-1, 0, 0))   # v > 0 = vers l'avant
    # lame : étroite au col, large en haut ; le bord arrière est plus long
    lame = [(0.045, -0.032), (0.045, 0.03), (0.13, 0.06), (0.26, 0.095), (0.40, 0.105),
            (0.425, 0.06), (0.43, -0.06), (0.415, -0.16), (0.30, -0.14), (0.17, -0.085), (0.08, -0.05)]
    s.ajouter(plaque(R, lame, 0.006, r=0.004), 0.004)
    # arête (épine) : crête en relief, plus haute au milieu ; l'acromion en bas
    epine = [(0.075, 0.0), (0.085, 0.02), (0.20, 0.032), (0.34, 0.026), (0.405, 0.01), (0.405, 0.0)]

    dehors = 1.0 if R.W[2] * sz > 0 else -1.0       # la crête se dresse vers l'extérieur de l'animal

    def crete(P):
        u, v, w = R.local(P)
        d2 = polygone2d(u, w * dehors, epine)         # profil de la crête dans le plan (u, w)
        dv = np.abs(v - 0.012) - 0.0045
        return np.minimum(np.maximum(d2, dv), 0) + np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dv, 0) ** 2) - 0.003
    s.ajouter(crete, 0.006)
    # col et cavité glénoïde (l'articulation avec l'humérus)
    s.ajouter(capsule(R.point(0.06, 0.0), R.point(0.015, 0.0), 0.024, 0.03), 0.01)
    s.ajouter(boule(R.point(0.0, 0.01), (0.035, 0.035, 0.035)), 0.01)
    s.creuser(boule(R.point(-0.03, 0.0), 0.03), 0.006)
    s.ajouter(boule(R.point(0.02, 0.04), 0.014), 0.008)                         # tubercule de la palette
    # cartilage de la palette (bord du haut), en couleur cartilage
    cart = [(0.415, 0.10), (0.47, 0.095), (0.475, -0.08), (0.455, -0.17), (0.405, -0.155), (0.425, -0.06), (0.425, 0.06)]
    s.ajouter(plaque(R, cart, 0.004, r=0.003), 0.004, "cartilage")
    return s


def humerus(sz):
    s = Sculpture()
    z = 0.265 * sz
    s.ajouter(boule((-0.752, 0.955, z), (0.044, 0.042, 0.04)), 0.01)                     # tête (articulaire, en arrière)
    s.ajouter(boule((-0.80, 0.985, 0.282 * sz), (0.03, 0.042, 0.028)), 0.012)            # gros tubercule (pointe de l'épaule)
    diaphyse(s, (-0.765, 0.93, 0.262 * sz), (-0.585, 0.725, 0.222 * sz), 0.032, 0.03)
    s.ajouter(boule((-0.715, 0.875, 0.29 * sz), (0.02, 0.03, 0.012), rot=(0, 0, 40)), 0.012)   # tubérosité deltoïdienne
    # condyle en bobine (articulation du coude)
    s.ajouter(boule((-0.573, 0.703, 0.198 * sz), (0.03, 0.027, 0.024)), 0.006)
    s.ajouter(boule((-0.573, 0.703, 0.243 * sz), (0.028, 0.026, 0.02)), 0.006)
    s.ajouter(capsule((-0.573, 0.703, 0.198 * sz), (-0.573, 0.703, 0.243 * sz), 0.021, 0.021), 0.004)
    return s


def radius(sz):
    s = Sculpture()
    z = 0.208 * sz
    # radius : tête large sous le coude, corps légèrement bombé vers l'avant, bout large au carpe
    s.ajouter(boule((-0.582, 0.668, z), (0.026, 0.014, 0.038)), 0.006)
    diaphyse(s, (-0.585, 0.665, z), (-0.598, 0.43, z), 0.024, 0.026, taille=0.86)
    s.ajouter(boule((-0.598, 0.425, z), (0.03, 0.017, 0.04)), 0.008)
    # cubitus : la pointe du coude (olécrane) monte derrière l'humérus
    R = Repere((0, 0, z), (1, 0, 0), (0, 0, 1), V_vers=(0, 1, 0))
    olecrane = [(-0.525, 0.79), (-0.497, 0.78), (-0.51, 0.74), (-0.552, 0.66), (-0.575, 0.66), (-0.57, 0.70), (-0.545, 0.77)]
    s.ajouter(plaque(R, olecrane, 0.011, r=0.006), 0.008)
    s.ajouter(boule((-0.51, 0.785, z), (0.018, 0.013, 0.015)), 0.006)
    s.ajouter(capsule((-0.57, 0.66, z), (-0.588, 0.50, z), 0.011, 0.005), 0.006)
    # carpe : deux rangées de petits os
    for j, (y, r) in enumerate([(0.402, 0.013), (0.378, 0.012)]):
        for dz in (-0.022, 0.0, 0.022):
            s.ajouter(boule((-0.60 + 0.002 * j, y, z + dz), (0.016, r, 0.011)), 0.004)
    return s


def pied(s, x0, y0, z, sens=-1):
    """Canon (os double soudé) + deux doigts à trois phalanges ; sens = -1 : doigts vers l'avant (-x)."""
    for dz in (-0.017, 0.017):   # deux condyles au bas du canon
        s.ajouter(boule((x0, y0, z + dz), (0.017, 0.016, 0.015)), 0.006)
        zz = z + dz * 1.15
        p1 = (x0 + sens * 0.012, y0 - 0.04, zz)
        p2 = (x0 + sens * 0.026, y0 - 0.068, zz)
        p3 = (x0 + sens * 0.052, y0 - 0.088, zz)
        s.ajouter(capsule((x0, y0 - 0.008, zz), p1, 0.012, 0.011), 0.006)
        s.ajouter(capsule(p1, p2, 0.011, 0.01), 0.006)
        s.ajouter(capsule(p2, p3, 0.012, 0.006), 0.006)                       # os du sabot, pointu
        s.ajouter(boule((x0 + sens * 0.03, y0 - 0.08, zz), (0.022, 0.009, 0.011)), 0.008)


def canon_avant(sz):
    s = Sculpture()
    z = 0.2 * sz
    s.ajouter(capsule((-0.601, 0.36, z), (-0.61, 0.135, z), 0.019, 0.019), 0.004)
    s.ajouter(boule((-0.602, 0.355, z), (0.024, 0.012, 0.032)), 0.008)
    s.ajouter(boule((-0.61, 0.135, z), (0.02, 0.012, 0.034)), 0.008)
    pied(s, -0.61, 0.122, z)
    return s


# ---------------------------------------------------------------- membre arrière
def coxal(sz):
    s = Sculpture()
    ace = np.array((0.80, 1.0, 0.19 * sz))           # cavité de la hanche
    hanche = np.array((0.48, 1.335, 0.262 * sz))     # pointe de la hanche (tuber coxae)
    sacree = np.array((0.56, 1.36, 0.06 * sz))       # près du sacrum (tuber sacrale)
    col = np.array((0.73, 1.08, 0.18 * sz))
    ischion = np.array((1.03, 1.12, 0.115 * sz))     # pointe de la fesse
    sym_av, sym_ar = np.array((0.84, 0.955, 0.012 * sz)), np.array((0.985, 0.975, 0.012 * sz))
    # aile de l'ilium : large plaque avec une crête épaisse entre la hanche et le sacrum
    Ri = Repere(col, hanche - col, np.cross(hanche - col, sacree - col) * (1 if sz > 0 else -1), V_vers=(0, 0, -sz))
    def uv(p, R):
        q = np.asarray(p) - R.O
        return (float(q @ R.U), float(q @ R.V))
    aile = [uv(col + (0, -0.02, 0.012 * sz), Ri), uv(hanche, Ri), uv(sacree, Ri), uv(col + (0, 0.03, -0.03 * sz), Ri)]
    s.ajouter(plaque(Ri, aile, 0.009, r=0.005), 0.008)
    s.ajouter(capsule(tuple(hanche), tuple(sacree), 0.017, 0.014), 0.012)
    s.ajouter(boule(tuple(hanche), (0.034, 0.03, 0.03)), 0.012)
    s.ajouter(boule(tuple(sacree), (0.022, 0.02, 0.02)), 0.01)
    s.ajouter(capsule(tuple(col), tuple(ace), 0.026, 0.03), 0.012)
    # cavité de la hanche : cupule ouverte vers l'extérieur
    s.ajouter(boule(tuple(ace), 0.043), 0.01)
    s.creuser(boule(tuple(ace + (0, -0.01, 0.03 * sz)), 0.032), 0.006)
    # ischium et pubis : le plancher du bassin, percé du trou obturé
    Rp = Repere(ace, ischion - ace, np.cross(ischion - ace, sym_ar - ace), V_vers=(0, 0, -sz))
    plancher = [uv(ace + (0, 0, -0.02 * sz), Rp), uv(ischion, Rp), uv(ischion + (-0.02, -0.06, -0.05 * sz), Rp),
                uv(sym_ar, Rp), uv(sym_av, Rp)]
    s.ajouter(plaque(Rp, plancher, 0.0085, r=0.005), 0.008)
    s.ajouter(capsule(tuple(ace), tuple(ischion), 0.021, 0.021), 0.01)
    s.ajouter(boule(tuple(ischion), (0.026, 0.036, 0.03)), 0.012)
    s.ajouter(capsule(tuple(sym_av), tuple(sym_ar), 0.012, 0.012), 0.008)
    trou = ace * 0.35 + sym_ar * 0.35 + ischion * 0.10 + sym_av * 0.20
    trou_traversant(s, tuple(trou), Rp.W, 0.034)
    return s


def femur(sz):
    s = Sculpture()
    z = 0.21 * sz
    s.ajouter(boule((0.80, 0.998, 0.19 * sz), 0.037), 0.006)                                   # tête, dans la cavité de la hanche
    s.ajouter(capsule((0.80, 0.995, 0.19 * sz), (0.815, 0.975, 0.225 * sz), 0.024, 0.028), 0.01)   # col
    s.ajouter(boule((0.845, 1.03, 0.238 * sz), (0.03, 0.045, 0.028)), 0.012)                   # grand trochanter
    diaphyse(s, (0.815, 0.965, 0.225 * sz), (0.69, 0.735, z), 0.033, 0.034, taille=0.82)
    # bas du fémur : deux condyles en arrière, la trochlée (gorge de la rotule) en avant
    for dz in (-0.022, 0.022):
        s.ajouter(boule((0.69, 0.692, z + dz * sz), (0.036, 0.034, 0.02)), 0.006)
        s.ajouter(boule((0.648, 0.715, z + dz * 0.8 * sz), (0.016, 0.038, 0.011)), 0.006)
    s.ajouter(boule((0.668, 0.72, z), (0.028, 0.035, 0.022)), 0.012)
    return s


def rotule(sz):
    s = Sculpture()
    s.ajouter(boule((0.622, 0.722, 0.21 * sz), (0.017, 0.033, 0.021), rot=(0, 0, -20)), 0.004)
    s.ajouter(boule((0.626, 0.745, 0.21 * sz), (0.014, 0.012, 0.016)), 0.006)
    return s


def tibia(sz):
    s = Sculpture()
    z = 0.205 * sz
    s.ajouter(boule((0.685, 0.652, z), (0.042, 0.02, 0.046)), 0.008)                           # plateau sous le genou
    s.ajouter(capsule((0.655, 0.645, z), (0.715, 0.55, z), 0.017, 0.008), 0.012)               # crête du tibia
    diaphyse(s, (0.69, 0.635, z), (0.875, 0.445, z), 0.027, 0.024, taille=0.8)
    s.ajouter(boule((0.882, 0.432, z), (0.028, 0.02, 0.033)), 0.008)
    s.ajouter(capsule((0.705, 0.635, 0.232 * sz), (0.76, 0.565, 0.226 * sz), 0.008, 0.003), 0.006)   # péroné (réduit)
    # tarse : astragale, et calcanéum qui monte en arrière (la pointe du jarret)
    s.ajouter(boule((0.884, 0.405, z), (0.024, 0.02, 0.026)), 0.006)
    s.ajouter(capsule((0.89, 0.40, z), (0.955, 0.495, z), 0.017, 0.02), 0.008)
    s.ajouter(boule((0.958, 0.5, z), (0.019, 0.017, 0.02)), 0.006)
    for dz in (-0.018, 0.018):
        s.ajouter(boule((0.88, 0.378, z + dz), (0.016, 0.01, 0.014)), 0.004)
    return s


def canon_arriere(sz):
    s = Sculpture()
    z = 0.2 * sz
    s.ajouter(capsule((0.879, 0.365, z), (0.866, 0.135, z), 0.018, 0.018), 0.004)
    s.ajouter(boule((0.879, 0.36, z), (0.022, 0.011, 0.03)), 0.008)
    s.ajouter(boule((0.866, 0.135, z), (0.019, 0.012, 0.033)), 0.008)
    pied(s, 0.866, 0.122, z)
    return s


# (identifiant, fonction, pair ?, triangles visés par côté)
OS_BOEUF = [
    ("crane", crane, False, 4200), ("cervicales", cervicales, False, 2600), ("dorsales", dorsales, False, 3600),
    ("cotes", cotes, True, 3600), ("sternum", sternum, False, 700), ("lombaires", lombaires, False, 2000),
    ("sacrum", sacrum, False, 900), ("coccygiennes", coccygiennes, False, 1600),
    ("palette", palette, True, 1600), ("humerus", humerus, True, 1300), ("radius", radius, True, 1600),
    ("canon-avant", canon_avant, True, 1300), ("coxal", coxal, True, 2400), ("femur", femur, True, 1400),
    ("rotule", rotule, True, 300), ("tibia", tibia, True, 1500), ("canon-arriere", canon_arriere, True, 1300),
]

SQUELETTES = {"boeuf": OS_BOEUF}


def sculptures(nom):
    """Liste (id, côté, sculpture, triangles) ; côté = 'g' (z > 0), 'd' (z < 0) ou '' pour les os du milieu."""
    out = []
    for oid, f, pair, cible in SQUELETTES[nom]:
        if pair:
            out += [(oid, "g", f(1), cible), (oid, "d", f(-1), cible)]
        else:
            out.append((oid, "", f(), cible))
    return out
