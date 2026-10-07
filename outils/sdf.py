# Boîte à outils de formes 3D « implicites » (distance signée : < 0 dedans, > 0 dehors) pour
# sculpter les os et les muscles du bœuf de façon réaliste mais épurée.
#
# Chaque primitive connaît sa boîte englobante : une forme n'est évaluée que là où elle peut
# compter, ce qui permet une grille fine (3 à 4 mm) sans y passer des heures.
# Repère commun aux modèles : x = longueur (tête vers -x), y = hauteur (sol en 0), z = largeur
# (côté gauche de l'animal = z > 0).
import numpy as np

GRAND = 1.0e3   # « très loin » : valeur finie (un infini donnerait des NaN dans les unions douces)


def n_(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v)


# ---------------------------------------------------------------- combinaisons douces
def union_douce(d1, d2, k):
    if k <= 0:
        return np.minimum(d1, d2)
    h = np.clip(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0)
    return d2 * (1 - h) + d1 * h - k * h * (1 - h)


def soustraction_douce(d, t, k):
    """Retire le volume t du volume d (raccord arrondi de rayon k)."""
    if k <= 0:
        return np.maximum(d, -t)
    h = np.clip(0.5 - 0.5 * (d + t) / k, 0.0, 1.0)
    return d * (1 - h) + (-t) * h + k * h * (1 - h)


def intersection_douce(d, t, k):
    if k <= 0:
        return np.maximum(d, t)
    h = np.clip(0.5 - 0.5 * (t - d) / k, 0.0, 1.0)
    return t * (1 - h) + d * h + k * h * (1 - h)


# ---------------------------------------------------------------- primitives
class Prim:
    """Une forme élémentaire : f(P) -> distance, et sa boîte [lo, hi]."""

    def __init__(self, f, lo, hi):
        self.f = f
        self.lo = np.asarray(lo, np.float64)
        self.hi = np.asarray(hi, np.float64)


def _rot(deg):
    rx, ry, rz = np.radians(deg)
    cx, sx, cy, sy, cz, sz = np.cos(rx), np.sin(rx), np.cos(ry), np.sin(ry), np.cos(rz), np.sin(rz)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def _ell2(u, v, a, b, p=2.0):
    """Distance approchée à une ellipse pleine de demi-axes a, b (formule k0(k0-1)/k1) ;
    p > 2 : « superellipse », section plus carrée (face du crâne, os plats épais)."""
    if p != 2.0:
        k = (np.abs(u / a) ** p + np.abs(v / b) ** p) ** (1.0 / p)
        return (k - 1.0) * np.minimum(a, b)
    k0 = np.sqrt((u / a) ** 2 + (v / b) ** 2)
    k1 = np.sqrt((u / (a * a)) ** 2 + (v / (b * b)) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def ell(c, r, rot=None, axes=None):
    """Ellipsoïde de centre c, demi-axes r ; orientation par angles (rot, degrés) ou par 3 axes."""
    c = np.asarray(c, np.float64)
    r = np.asarray(r if not np.isscalar(r) else (r, r, r), np.float64)
    M = None
    if axes is not None:
        M = np.stack([n_(a) for a in axes], 1)       # colonnes = axes locaux
    elif rot is not None:
        M = _rot(rot)
    rf = r.astype(np.float32)

    def f(P):
        q = P - c.astype(np.float32)
        if M is not None:
            q = q @ M.astype(np.float32)
        k0 = np.linalg.norm(q / rf, axis=-1)
        k1 = np.linalg.norm(q / (rf * rf), axis=-1)
        return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)
    m = r.max()
    return Prim(f, c - m, c + m)


def cap(a, b, ra, rb=None):
    """Segment arrondi (cône à bouts ronds) de a (rayon ra) à b (rayon rb)."""
    rb = ra if rb is None else rb
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    af, ba = a.astype(np.float32), (b - a).astype(np.float32)
    bb = float(ba @ ba)

    def f(P):
        pa = P - af
        h = np.clip((pa @ ba) / bb, 0.0, 1.0)
        return np.linalg.norm(pa - h[..., None] * ba, axis=-1) - (ra + (rb - ra) * h)
    m = max(ra, rb)
    return Prim(f, np.minimum(a, b) - m, np.maximum(a, b) + m)


def boite(c, demi, arrondi=0.0, axes=None):
    """Pavé arrondi de centre c, demi-côtés demi (dans ses axes locaux)."""
    c = np.asarray(c, np.float64)
    demi = np.asarray(demi, np.float64)
    M = np.eye(3) if axes is None else np.stack([n_(a) for a in axes], 1)
    Mf, cf, df = M.astype(np.float32), c.astype(np.float32), (demi - arrondi).astype(np.float32)

    def f(P):
        q = np.abs((P - cf) @ Mf) - df
        dehors = np.linalg.norm(np.maximum(q, 0), axis=-1)
        return dehors + np.minimum(q.max(-1), 0) - arrondi
    m = np.linalg.norm(demi)
    return Prim(f, c - m, c + m)


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
        self.O = np.asarray(O, np.float64)
        self.U = n_(U)
        W = np.asarray(normale, np.float64)
        self.W = n_(W - (W @ self.U) * self.U)
        self.V = n_(np.cross(self.W, self.U))
        if V_vers is not None and self.V @ np.asarray(V_vers) < 0:
            self.V = -self.V
            self.W = -self.W

    def point(self, u, v, w=0.0):
        return self.O + u * self.U + v * self.V + w * self.W

    def local(self, P):
        q = P - self.O.astype(np.float32)
        return q @ self.U.astype(np.float32), q @ self.V.astype(np.float32), q @ self.W.astype(np.float32)


def plaque(R, pts, e, arrondi=0.003, decal=0.0, epaisseurs=None):
    """Os plat : polygone (u, v) dans le repère R, demi-épaisseur e (éventuellement variable :
    epaisseurs(u, v) -> demi-épaisseur), bords arrondis."""
    pts = np.asarray(pts, np.float64)

    def f(P):
        u, v, w = R.local(P)
        d2 = polygone2d(u, v, pts) + arrondi
        ee = e if epaisseurs is None else epaisseurs(u, v)
        dw = np.abs(w - decal) - (ee - arrondi)
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dw, 0) ** 2)
        return np.minimum(np.maximum(d2, dw), 0) + dehors - arrondi
    coins = [R.point(u, v, s * (e + decal)) for u, v in pts for s in (-1, 1)]
    emax = e if epaisseurs is None else 0.05
    lo = np.min(coins, 0) - emax - arrondi
    hi = np.max(coins, 0) + emax + arrondi
    return Prim(f, lo, hi)


def courbe(pts, n=24):
    """Catmull-Rom passant par les points de contrôle : n points régulièrement répartis."""
    P = np.asarray(pts, np.float64)
    P = np.vstack([2 * P[0] - P[1], P, 2 * P[-1] - P[-2]])
    out = []
    seg = len(P) - 3
    for i in range(n):
        t = i / (n - 1) * seg
        k = min(int(t), seg - 1)
        u = t - k
        p0, p1, p2, p3 = P[k], P[k + 1], P[k + 2], P[k + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u * u
                          + (-p0 + 3 * p1 - 3 * p2 + p3) * u ** 3))
    return np.array(out)


def loft(pts, a, b, haut=(0, 1, 0), arrondi=0.0, tors=None, carre=2.0):
    """Volume tiré le long d'une ligne (os long, côte, muscle) : en chaque point de contrôle,
    une section elliptique de demi-axes a[i] (le long de « haut », redressé perpendiculaire à la
    ligne) et b[i] (l'autre direction). « haut » peut être un vecteur ou une liste de vecteurs."""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    def reechantillonner(r):
        r = np.atleast_1d(np.asarray(r, np.float64))
        if len(r) == n:
            return r.copy()
        if len(r) == 1:
            return np.full(n, r[0])
        return np.interp(np.linspace(0, 1, n), np.linspace(0, 1, len(r)), r)   # moins de rayons que de points
    a, b = reechantillonner(a), reechantillonner(b)
    hauts = np.asarray(haut, np.float64)
    if hauts.ndim == 1:
        hauts = np.repeat(hauts[None], n, 0)
    T = np.zeros_like(pts)
    T[1:-1] = pts[2:] - pts[:-2]
    T[0], T[-1] = pts[1] - pts[0], pts[-1] - pts[-2]
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    N = hauts - (np.sum(hauts * T, 1, keepdims=True)) * T
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    B = np.cross(T, N)
    seg_a, seg_b = pts[:-1], pts[1:]
    L = np.linalg.norm(seg_b - seg_a, axis=1)
    f32 = lambda x: np.asarray(x, np.float32)

    def f(P):
        best = np.full(P.shape[:-1], np.inf, np.float32)
        out = np.full(P.shape[:-1], GRAND, np.float32)
        for i in range(n - 1):
            A, D = f32(seg_a[i]), f32(seg_b[i] - seg_a[i])
            q = P - A
            t = np.clip((q @ D) / float(D @ D), 0.0, 1.0)
            c = q - t[..., None] * D
            dist = np.linalg.norm(c, axis=-1)
            m = dist < best
            if not m.any():
                continue
            best = np.where(m, dist, best)
            tm = t[..., None]
            Ni = f32(N[i]) * (1 - tm) + f32(N[i + 1]) * tm
            Bi = f32(B[i]) * (1 - tm) + f32(B[i + 1]) * tm
            Ti = f32(T[i]) * (1 - tm) + f32(T[i + 1]) * tm
            ai = a[i] * (1 - t) + a[i + 1] * t
            bi = b[i] * (1 - t) + b[i + 1] * t
            u = np.sum(c * Ni, -1)
            v = np.sum(c * Bi, -1)
            if tors is not None:
                ang = tors[i] * (1 - t) + tors[i + 1] * t
                cu, su = np.cos(ang), np.sin(ang)
                u, v = u * cu + v * su, -u * su + v * cu
            drad = _ell2(u, v, ai - arrondi, bi - arrondi, carre)
            w = np.zeros_like(u)
            if i == 0:
                w = np.where(t <= 0, -np.sum(q * f32(T[0]), -1), w)
            if i == n - 2:
                w = np.where(t >= 1, np.sum((P - f32(seg_b[i])) * f32(T[-1]), -1), w)
            dehors = np.sqrt(np.maximum(drad, 0) ** 2 + np.maximum(w, 0) ** 2)
            d = np.minimum(np.maximum(drad, w), 0) + dehors - arrondi
            out = np.where(m, d, out)
        return out
    m = max(a.max(), b.max())
    return Prim(f, pts.min(0) - m, pts.max(0) + m)


def cylindre(a, b, r, arrondi=0.002):
    """Cylindre plein à bords arrondis, de l'axe a -> b."""
    a = np.asarray(a, np.float64); b = np.asarray(b, np.float64)
    ax = b - a
    L = np.linalg.norm(ax)
    T = (ax / L).astype(np.float32)
    C = ((a + b) / 2).astype(np.float32)

    def f(P):
        q = P - C
        h = np.abs(q @ T) - (L / 2 - arrondi)
        rad = np.linalg.norm(q - (q @ T)[..., None] * T, axis=-1) - (r - arrondi)
        return np.minimum(np.maximum(h, rad), 0) + np.sqrt(np.maximum(h, 0) ** 2 + np.maximum(rad, 0) ** 2) - arrondi
    m = r + 0.002
    return Prim(f, np.minimum(a, b) - m, np.maximum(a, b) + m)


def tore(c, axe, R, r):
    """Anneau : centre c, axe normal, grand rayon R, épaisseur r."""
    c = np.asarray(c, np.float32)
    A = n_(axe).astype(np.float32)

    def f(P):
        q = P - c
        h = q @ A
        rad = np.linalg.norm(q - h[..., None] * A, axis=-1)
        return np.sqrt((rad - R) ** 2 + h ** 2) - r
    m = R + r
    return Prim(f, np.asarray(c, np.float64) - m, np.asarray(c, np.float64) + m)


# ---------------------------------------------------------------- forme composée
class Forme:
    """Suite d'opérations : ajouter (union douce) ou creuser (soustraction douce), dans l'ordre.
    Chaque ajout porte une « partie » (os, cartilage, dent…) qui colore le maillage."""

    def __init__(self):
        self.ops = []

    def ajouter(self, prim, k=0.004, partie="corps"):
        self.ops.append(("+", prim, k, partie))
        return self

    def creuser(self, prim, k=0.003):
        self.ops.append(("-", prim, k, None))
        return self

    def couper(self, prim, k=0.0):
        """Garde seulement ce qui est dans prim (intersection)."""
        self.ops.append(("x", prim, k, None))
        return self

    def boite(self, marge=0.01):
        plus = [p for o, p, _, _ in self.ops if o == "+"]
        lo = np.min([p.lo for p in plus], 0) - marge
        hi = np.max([p.hi for p in plus], 0) + marge
        return lo, hi

    def grille(self, pas, marge=0.012):
        lo, hi = self.boite(marge)
        return [np.arange(lo[i], hi[i] + pas, pas, dtype=np.float32) for i in range(3)]

    def champ(self, axes):
        """Distance sur la grille régulière axes = (xs, ys, zs) ; chaque opération n'est
        calculée que dans sa boîte (élargie de son raccord)."""
        shape = tuple(len(a) for a in axes)
        vol = np.full(shape, GRAND, np.float32)
        pas = float(axes[0][1] - axes[0][0])
        for o, p, k, _ in self.ops:
            m = k + 3 * pas
            sl = []
            vide = False
            for i in range(3):
                i0 = int(np.searchsorted(axes[i], p.lo[i] - m))
                i1 = int(np.searchsorted(axes[i], p.hi[i] + m, side="right"))
                if o == "x":
                    i0, i1 = 0, shape[i]
                if i1 <= i0:
                    vide = True
                sl.append(slice(i0, i1))
            if vide:
                if o == "x":
                    vol[:] = GRAND
                continue
            X, Y, Z = np.meshgrid(axes[0][sl[0]], axes[1][sl[1]], axes[2][sl[2]], indexing="ij")
            P = np.stack([X, Y, Z], -1)
            d = p.f(P).astype(np.float32)
            v = vol[tuple(sl)]
            if o == "+":
                vol[tuple(sl)] = union_douce(v, d, k)
            elif o == "-":
                vol[tuple(sl)] = soustraction_douce(v, d, k)
            else:
                vol[tuple(sl)] = intersection_douce(v, d, k)
        return vol

    def distance(self, P):
        """Distance en des points quelconques (P : (..., 3))."""
        P = np.asarray(P, np.float32)
        d = np.full(P.shape[:-1], GRAND, np.float32)
        for o, p, k, _ in self.ops:
            m = k + 0.03
            dedans = np.all((P >= p.lo - m) & (P <= p.hi + m), -1)
            if o == "x":
                d = intersection_douce(d, p.f(P), k)
                continue
            if not dedans.any():
                continue
            v = p.f(P[dedans]).astype(np.float32)
            if o == "+":
                d[dedans] = union_douce(d[dedans], v, k)
            else:
                d[dedans] = soustraction_douce(d[dedans], v, k)
        return d

    def parties(self, P):
        """Pour chaque point, la partie de l'ajout le plus proche."""
        P = np.asarray(P, np.float32)
        noms = sorted({pa for o, _, _, pa in self.ops if o == "+"})
        best = np.full(P.shape[:-1], np.inf, np.float32)
        lab = np.zeros(P.shape[:-1], np.int8)
        for o, p, _, pa in self.ops:
            if o != "+":
                continue
            dedans = np.all((P >= p.lo - 0.03) & (P <= p.hi + 0.03), -1)
            if not dedans.any():
                continue
            v = np.full(P.shape[:-1], np.inf, np.float32)
            v[dedans] = p.f(P[dedans])
            m = v < best
            best[m] = v[m]
            lab[m] = noms.index(pa)
        return noms, lab


def miroir_z(prim):
    """Symétrique d'une primitive par rapport au plan z = 0 (côté droit de l'animal)."""
    S = np.array([1, 1, -1], np.float32)
    lo, hi = prim.lo * S, prim.hi * S
    return Prim(lambda P: prim.f(P * S), np.minimum(lo, hi), np.maximum(lo, hi))
