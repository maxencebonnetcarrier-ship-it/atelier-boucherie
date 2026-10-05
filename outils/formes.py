# Formes 3D des animaux : chaque animal est sculpté par union douce de volumes simples
# (ellipsoïdes et « os » arrondis), avec le MÊME vocabulaire de formes pour les quatre
# espèces, afin qu'ils aient tous le même style.
#
# Repère : x = longueur (tête vers -x), y = hauteur (sol en y = 0), z = largeur (symétrique).
import numpy as np


def _rot(deg):
    rx, ry, rz = np.radians(deg)
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def ellipsoide(P, c, r, rot=None):
    """Distance (approchée) à un ellipsoïde de centre c, demi-axes r, tourné de rot (degrés x,y,z)."""
    q = P - np.asarray(c, np.float32)
    if rot is not None:
        R = _rot(rot).astype(np.float32)
        q = q @ R  # = R^T appliqué à chaque point
    r = np.asarray(r, np.float32)
    k0 = np.linalg.norm(q / r, axis=-1)
    k1 = np.linalg.norm(q / (r * r), axis=-1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-6)


def os_(P, a, b, ra, rb):
    """Segment arrondi de a (rayon ra) à b (rayon rb) : membres, cou, queue."""
    a = np.asarray(a, np.float32); b = np.asarray(b, np.float32)
    pa = P - a; ba = b - a
    h = np.clip((pa @ ba) / float(ba @ ba), 0.0, 1.0)
    return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)


def union_douce(d1, d2, k):
    if k <= 0:
        return np.minimum(d1, d2)
    h = np.clip(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0)
    return d2 * (1 - h) + d1 * h - k * h * (1 - h)


def miroir(c):
    """Renvoie la position et son symétrique par rapport au plan z = 0."""
    x, y, z = c
    return [(x, y, z), (x, y, -z)]


class Sculpture:
    """Accumule des volumes ; chaque ajout se fond dans le corps avec un rayon de raccord k."""

    def __init__(self):
        self.pieces = []  # (fonction(P) -> distance, k, partie)
        self.trous = []   # (fonction(P) -> distance, k) : volumes creusés après coup (orbites, trous des os)
        self.yeux = []    # ((x, y, z), rayon) : billes posées sur la tête, côté +z (symétrisées à l'export)

    def creuser(self, f, k=0.004):
        self.trous.append((f, k))

    def oeil(self, c, r):
        self.yeux.append((c, r))

    def ajouter(self, f, k, partie="corps"):
        self.pieces.append((f, k, partie))

    def ell(self, c, r, k=0.08, rot=None, sym=False, partie="corps"):
        for cc in (miroir(c) if sym else [c]):
            rr = None
            if rot is not None and sym and cc[2] < 0:
                rr = (-rot[0], -rot[1], rot[2])
            elif rot is not None:
                rr = rot
            self.ajouter(lambda P, cc=cc, rr=rr: ellipsoide(P, cc, r, rr), k, partie)

    def seg(self, a, b, ra, rb, k=0.06, sym=False, partie="corps"):
        paires = list(zip(miroir(a), miroir(b))) if sym else [(a, b)]
        for aa, bb in paires:
            self.ajouter(lambda P, aa=aa, bb=bb: os_(P, aa, bb, ra, rb), k, partie)

    def chaine(self, points, rayons, k=0.03, sym=False, partie="corps"):
        for i in range(len(points) - 1):
            self.seg(points[i], points[i + 1], rayons[i], rayons[i + 1], k=k, sym=sym, partie=partie)

    def distance(self, P):
        d = None
        for f, k, _ in self.pieces:
            di = f(P)
            d = di if d is None else union_douce(d, di, k)
        for f, k in self.trous:  # soustraction douce
            t = f(P)
            h = np.clip(0.5 - 0.5 * (d + t) / k, 0.0, 1.0)
            d = d * (1 - h) + (-t) * h + k * h * (1 - h)
        return d

    def parties(self, P):
        """Pour chaque point, la partie du volume le plus proche (corps, sabot, corne…)."""
        noms = sorted({p for _, _, p in self.pieces})
        best = np.full(P.shape[:-1], np.inf, np.float32)
        lab = np.zeros(P.shape[:-1], np.int8)
        for f, _, partie in self.pieces:
            di = f(P)
            m = di < best
            best[m] = di[m]
            lab[m] = noms.index(partie)
        return noms, lab


def jambe_avant(s, x, z, haut, k_corps=0.1, r=(0.14, 0.085, 0.07), sabot=(0.085, 0.055, 0.075), y_sabot=0.05):
    """Avant-bras + canon + sabot, posés à la verticale."""
    yg = haut * 0.42
    s.seg((x, haut, z), (x + 0.01, yg, z), r[0], r[1], k=k_corps, sym=True)
    s.seg((x + 0.01, yg, z), (x, y_sabot + 0.06, z), r[1] * 0.92, r[2], k=0.04, sym=True)
    s.ell((x - 0.015, y_sabot, z), sabot, k=0.03, sym=True, partie="sabot")


def jambe_arriere(s, hanche, grasset, jarret, boulet, z, r=(0.22, 0.13, 0.085, 0.07), sabot=(0.085, 0.055, 0.075), y_sabot=0.05, k_corps=0.12):
    """Cuisse + jambe + canon + sabot, avec l'angle caractéristique du jarret."""
    s.seg((hanche[0], hanche[1], z), (grasset[0], grasset[1], z), r[0], r[1], k=k_corps, sym=True)
    s.seg((grasset[0], grasset[1], z), (jarret[0], jarret[1], z), r[1], r[2], k=0.06, sym=True)
    s.seg((jarret[0], jarret[1], z), (boulet[0], y_sabot + 0.06, z), r[2] * 0.9, r[3], k=0.04, sym=True)
    s.ell((boulet[0] - 0.015, y_sabot, z), sabot, k=0.03, sym=True, partie="sabot")


def boeuf():
    # Proportions de bovin à viande : garrot à 1,43, ventre à ~0,65, corps ~1,2 × la hauteur.
    s = Sculpture()
    s.ell((0.15, 1.05, 0), (0.95, 0.38, 0.40), k=0)              # tronc
    s.ell((-0.5, 1.02, 0), (0.48, 0.42, 0.40), k=0.14)           # poitrine
    s.ell((0.72, 1.12, 0), (0.40, 0.33, 0.40), k=0.14)           # croupe
    s.ell((-0.45, 1.28, 0), (0.36, 0.15, 0.25), k=0.14)          # garrot
    s.ell((0.15, 0.85, 0), (0.55, 0.22, 0.38), k=0.14)           # ventre
    s.ell((-0.95, 0.86, 0), (0.15, 0.22, 0.12), k=0.12)          # fanon
    s.ell((0.70, 0.92, 0.13), (0.30, 0.32, 0.28), k=0.12, sym=True)   # cuisses musclées
    s.ell((-0.55, 0.96, 0.18), (0.28, 0.33, 0.22), k=0.12, sym=True)  # épaules
    # cou court et épais, tête en coin : front large, mufle large
    s.seg((-0.6, 1.15, 0), (-1.1, 1.22, 0), 0.36, 0.25, k=0.12)
    s.ell((-1.22, 1.30, 0), (0.16, 0.16, 0.20), k=0.08)          # crâne
    s.seg((-1.22, 1.32, 0), (-1.52, 1.02, 0), 0.17, 0.13, k=0.07)
    s.ell((-1.30, 1.12, 0), (0.16, 0.13, 0.15), k=0.07)          # joues
    s.ell((-1.56, 0.99, 0), (0.11, 0.12, 0.16), k=0.05)          # mufle
    s.oeil((-1.33, 1.27, 0.15), 0.03)
    s.ell((-1.22, 1.31, 0.27), (0.06, 0.035, 0.13), rot=(0, 0, -15), k=0.03, sym=True, partie="oreille")
    s.chaine([(-1.21, 1.43, 0.12), (-1.2, 1.48, 0.25), (-1.25, 1.58, 0.32)], [0.05, 0.035, 0.018],
             k=0.02, sym=True, partie="corne")
    # membres
    s.seg((-0.6, 0.85, 0.2), (-0.6, 0.40, 0.2), 0.14, 0.085, k=0.1, sym=True)
    s.seg((-0.6, 0.40, 0.2), (-0.61, 0.11, 0.2), 0.078, 0.065, k=0.04, sym=True)
    s.ell((-0.63, 0.05, 0.2), (0.085, 0.055, 0.075), k=0.03, sym=True, partie="sabot")
    s.chaine([(0.72, 0.98, 0.2), (0.68, 0.66, 0.2), (0.9, 0.42, 0.2), (0.86, 0.11, 0.2)], [0.2, 0.14, 0.08, 0.065],
             k=0.05, sym=True)
    s.ell((0.85, 0.05, 0.2), (0.085, 0.055, 0.075), k=0.03, sym=True, partie="sabot")
    # queue
    s.chaine([(1.03, 1.38, 0), (1.09, 1.0, 0), (1.09, 0.62, 0)], [0.05, 0.035, 0.03], k=0.04, partie="queue")
    s.ell((1.09, 0.56, 0), (0.06, 0.11, 0.06), k=0.03, partie="queue")
    s.reperes = {
        "nez": (-1.67, 0.99), "nuque": (-1.22, 1.46), "gorge": (-1.2, 0.97), "garrot": (-0.45, 1.43),
        "dos": (0.15, 1.43), "hanche": (0.72, 1.45), "queue": (1.03, 1.38), "fesse": (1.11, 1.1),
        "jarret": (0.95, 0.42), "sabot_ar": (0.85, 0.0), "grasset": (0.54, 0.66), "ventre": (0.15, 0.63),
        "coude": (-0.46, 0.66), "poitrail": (-1.05, 0.8), "sabot_av": (-0.62, 0.0), "genou": (-0.69, 0.4),
    }
    return s


def veau():
    # Jeune bovin : corps plus fin, pattes plus longues en proportion, grosse tête, pas de cornes.
    s = Sculpture()
    s.ell((0.1, 0.93, 0), (0.75, 0.30, 0.30), k=0)
    s.ell((-0.4, 0.92, 0), (0.38, 0.33, 0.30), k=0.12)
    s.ell((0.55, 0.98, 0), (0.33, 0.27, 0.30), k=0.12)
    s.ell((-0.35, 1.12, 0), (0.28, 0.12, 0.20), k=0.12)
    s.ell((0.1, 0.78, 0), (0.45, 0.17, 0.28), k=0.12)
    s.ell((0.55, 0.82, 0.1), (0.24, 0.27, 0.22), k=0.1, sym=True)
    s.ell((-0.43, 0.85, 0.14), (0.22, 0.27, 0.17), k=0.1, sym=True)
    s.seg((-0.5, 1.02, 0), (-0.85, 1.15, 0), 0.25, 0.18, k=0.1)
    s.ell((-0.95, 1.22, 0), (0.13, 0.13, 0.15), k=0.07)
    s.seg((-0.95, 1.24, 0), (-1.18, 1.0, 0), 0.13, 0.095, k=0.06)
    s.ell((-1.0, 1.08, 0), (0.12, 0.10, 0.11), k=0.06)
    s.ell((-1.21, 0.97, 0), (0.08, 0.085, 0.11), k=0.04)
    s.oeil((-1.03, 1.20, 0.12), 0.027)
    s.ell((-0.93, 1.25, 0.23), (0.07, 0.03, 0.15), rot=(0, 0, -15), k=0.025, sym=True, partie="oreille")
    s.seg((-0.45, 0.75, 0.15), (-0.45, 0.36, 0.15), 0.10, 0.065, k=0.08, sym=True)
    s.seg((-0.45, 0.36, 0.15), (-0.46, 0.10, 0.15), 0.058, 0.05, k=0.03, sym=True)
    s.ell((-0.47, 0.045, 0.15), (0.065, 0.045, 0.058), k=0.025, sym=True, partie="sabot")
    s.chaine([(0.55, 0.85, 0.15), (0.52, 0.58, 0.15), (0.70, 0.36, 0.15), (0.67, 0.10, 0.15)], [0.15, 0.10, 0.06, 0.05],
             k=0.04, sym=True)
    s.ell((0.66, 0.045, 0.15), (0.065, 0.045, 0.058), k=0.025, sym=True, partie="sabot")
    s.chaine([(0.86, 1.18, 0), (0.92, 0.85, 0), (0.93, 0.55, 0)], [0.04, 0.03, 0.025], k=0.035, partie="queue")
    s.ell((0.93, 0.5, 0), (0.045, 0.08, 0.045), k=0.03, partie="queue")
    s.reperes = {
        "nez": (-1.29, 0.97), "nuque": (-0.95, 1.35), "gorge": (-0.9, 0.95), "garrot": (-0.35, 1.24),
        "dos": (0.1, 1.23), "hanche": (0.55, 1.25), "queue": (0.86, 1.18), "fesse": (0.88, 0.95),
        "jarret": (0.76, 0.36), "sabot_ar": (0.66, 0.0), "grasset": (0.42, 0.6), "ventre": (0.1, 0.61),
        "coude": (-0.35, 0.62), "poitrail": (-0.8, 0.75), "sabot_av": (-0.46, 0.0), "genou": (-0.51, 0.36),
    }
    return s


def porc():
    # Corps long et rond, pattes courtes, tête dans le prolongement, groin en disque, queue en vrille.
    s = Sculpture()
    s.ell((0.0, 0.68, 0), (0.82, 0.34, 0.36), k=0)
    s.ell((0.55, 0.70, 0), (0.40, 0.35, 0.37), k=0.15)        # jambons
    s.ell((-0.5, 0.68, 0), (0.38, 0.34, 0.35), k=0.15)        # épaules
    s.ell((0.0, 0.55, 0), (0.60, 0.24, 0.33), k=0.15)         # ventre
    s.ell((-0.98, 0.70, 0), (0.27, 0.25, 0.25), k=0.14)       # tête
    s.ell((-0.90, 0.55, 0), (0.20, 0.15, 0.22), k=0.12)       # bajoues
    s.seg((-1.08, 0.66, 0), (-1.33, 0.58, 0), 0.17, 0.105, k=0.08)
    s.ell((-1.37, 0.58, 0), (0.035, 0.10, 0.11), k=0.025, partie="groin")
    s.oeil((-1.13, 0.78, 0.18), 0.02)
    s.ell((-1.04, 0.95, 0.14), (0.13, 0.026, 0.085), rot=(25, 0, 55), k=0.03, sym=True, partie="oreille")
    s.seg((-0.52, 0.45, 0.19), (-0.52, 0.20, 0.19), 0.12, 0.075, k=0.08, sym=True)
    s.seg((-0.52, 0.20, 0.19), (-0.53, 0.09, 0.19), 0.07, 0.065, k=0.03, sym=True)
    s.ell((-0.54, 0.045, 0.19), (0.075, 0.05, 0.065), k=0.025, sym=True, partie="sabot")
    s.chaine([(0.6, 0.6, 0.19), (0.62, 0.38, 0.19), (0.68, 0.24, 0.19), (0.66, 0.09, 0.19)], [0.17, 0.11, 0.075, 0.065],
             k=0.04, sym=True)
    s.ell((0.65, 0.045, 0.19), (0.075, 0.05, 0.065), k=0.025, sym=True, partie="sabot")
    t = np.linspace(0, 2.2 * np.pi, 14)
    pts = [(0.93 + 0.05 * np.sin(a) + 0.012 * a, 0.9 + 0.05 * np.cos(a) - 0.01 * a, 0.0) for a in t]
    s.chaine([(0.88, 0.86, 0.0)] + pts, [0.034] + [0.03] * len(t), k=0.015, partie="queue")
    s.reperes = {
        "nez": (-1.40, 0.58), "nuque": (-0.98, 0.95), "gorge": (-0.8, 0.42), "garrot": (-0.5, 1.02),
        "dos": (0.0, 1.02), "hanche": (0.55, 1.05), "queue": (0.9, 0.9), "fesse": (0.95, 0.7),
        "jarret": (0.73, 0.24), "sabot_ar": (0.65, 0.0), "grasset": (0.42, 0.36), "ventre": (0.0, 0.31),
        "coude": (-0.38, 0.36), "poitrail": (-0.82, 0.48), "sabot_av": (-0.54, 0.0), "genou": (-0.6, 0.22),
    }
    return s


def agneau():
    # Corps rond et laineux, pattes fines, petite tête aux oreilles horizontales.
    s = Sculpture()
    s.ell((0.0, 0.88, 0), (0.60, 0.30, 0.30), k=0)
    s.ell((0.40, 0.88, 0), (0.32, 0.30, 0.31), k=0.13)        # gigots
    s.ell((-0.34, 0.90, 0), (0.32, 0.29, 0.30), k=0.13)       # épaules
    s.ell((0.0, 0.74, 0), (0.45, 0.18, 0.28), k=0.12)

    def laine(P):  # léger relief bosselé, sur le tronc seulement
        base = ellipsoide(P, (0.02, 0.88, 0), (0.68, 0.32, 0.33))
        x, y, z = P[..., 0], P[..., 1], P[..., 2]
        return base - 0.012 * (np.sin(30 * x) * np.sin(30 * y + 1.0) * np.sin(30 * z + 2.0))
    s.ajouter(laine, 0.1)
    s.seg((-0.45, 1.0, 0), (-0.68, 1.18, 0), 0.18, 0.13, k=0.1)
    s.ell((-0.74, 1.27, 0), (0.11, 0.10, 0.11), k=0.06)
    s.seg((-0.72, 1.28, 0), (-0.92, 1.12, 0), 0.12, 0.08, k=0.05)
    s.ell((-0.94, 1.10, 0), (0.07, 0.075, 0.08), k=0.035)
    s.oeil((-0.80, 1.29, 0.085), 0.02)
    s.seg((-0.75, 1.30, 0.1), (-0.77, 1.27, 0.3), 0.04, 0.028, k=0.02, sym=True, partie="oreille")
    s.seg((-0.36, 0.70, 0.13), (-0.36, 0.33, 0.13), 0.085, 0.05, k=0.07, sym=True)
    s.seg((-0.36, 0.33, 0.13), (-0.37, 0.09, 0.13), 0.046, 0.042, k=0.03, sym=True)
    s.ell((-0.375, 0.04, 0.13), (0.055, 0.04, 0.05), k=0.02, sym=True, partie="sabot")
    s.chaine([(0.42, 0.82, 0.13), (0.42, 0.55, 0.13), (0.54, 0.34, 0.13), (0.52, 0.09, 0.13)], [0.14, 0.075, 0.05, 0.042],
             k=0.035, sym=True)
    s.ell((0.515, 0.04, 0.13), (0.055, 0.04, 0.05), k=0.02, sym=True, partie="sabot")
    s.chaine([(0.68, 1.0, 0), (0.74, 0.86, 0)], [0.06, 0.045], k=0.04, partie="queue")
    s.reperes = {
        "nez": (-1.01, 1.1), "nuque": (-0.74, 1.38), "gorge": (-0.75, 1.05), "garrot": (-0.48, 1.16),
        "dos": (0.0, 1.18), "hanche": (0.4, 1.18), "queue": (0.66, 1.05), "fesse": (0.72, 0.88),
        "jarret": (0.58, 0.34), "sabot_ar": (0.52, 0.0), "grasset": (0.28, 0.58), "ventre": (0.0, 0.56),
        "coude": (-0.26, 0.6), "poitrail": (-0.62, 0.78), "sabot_av": (-0.37, 0.0), "genou": (-0.41, 0.33),
    }
    return s


ESPECES = {"boeuf": boeuf, "veau": veau, "porc": porc, "agneau": agneau}
