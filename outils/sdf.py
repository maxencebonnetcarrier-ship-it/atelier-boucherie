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
    epaisseurs(u, v) -> demi-épaisseur), décalé de « decal » le long de la normale (nombre ou decal(u, v)),
    bords arrondis."""
    pts = np.asarray(pts, np.float64)

    def f(P):
        u, v, w = R.local(P)
        d2 = polygone2d(u, v, pts) + arrondi
        ee = e if epaisseurs is None else epaisseurs(u, v)
        dc = decal(u, v) if callable(decal) else decal
        dw = np.abs(w - dc) - (ee - arrondi)
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dw, 0) ** 2)
        return np.minimum(np.maximum(d2, dw), 0) + dehors - arrondi
    dmax = 0.06 if callable(decal) else abs(decal)
    coins = [R.point(u, v, s * (e + dmax)) for u, v in pts for s in (-1, 1)]
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


# ---------------------------------------------------------------- os d'après une planche anatomique
def _bilineaire(img, px, py, dehors):
    """Échantillonne l'image img (2D float) aux positions (px, py) en pixels ; dehors = valeur hors image."""
    h, w = img.shape
    x0 = np.floor(px).astype(np.int64)
    y0 = np.floor(py).astype(np.int64)
    fx, fy = (px - x0).astype(np.float32), (py - y0).astype(np.float32)
    ok = (x0 >= 0) & (y0 >= 0) & (x0 < w - 1) & (y0 < h - 1)
    xc, yc = np.clip(x0, 0, w - 2), np.clip(y0, 0, h - 2)
    v = (img[yc, xc] * (1 - fx) * (1 - fy) + img[yc, xc + 1] * fx * (1 - fy)
         + img[yc + 1, xc] * (1 - fx) * fy + img[yc + 1, xc + 1] * fx * fy)
    return np.where(ok, v, dehors).astype(np.float32)


class Placement:
    """Pose une figure de planche (pixels) dans le modèle : le point A_p de la planche va en A, B_p en B ;
    la figure est dans le plan qui contient AB et qui est perpendiculaire à « normale » (redressée).
    Sur une planche de profil, x de la planche = +x du modèle et y de la planche = -y du modèle :
    « miroir » inverse ce sens (planche vue de l'autre côté)."""

    def __init__(self, A_p, B_p, A, B, normale=(0, 0, 1), miroir=False, etirement=1.0):
        A_p, B_p = np.asarray(A_p, np.float64), np.asarray(B_p, np.float64)
        self.A, B = np.asarray(A, np.float64), np.asarray(B, np.float64)
        self.U = n_(B - self.A)
        Nn = np.asarray(normale, np.float64)
        self.W = n_(Nn - (Nn @ self.U) * self.U)
        self.V = np.cross(self.W, self.U)            # (U, V, W) direct ; V « en haut » dans le plan
        d = B_p - A_p
        dp = np.array([d[0], -d[1]])                 # planche : y vers le bas
        if miroir:
            dp[0] = -dp[0]
        self.s = np.linalg.norm(B - self.A) / np.linalg.norm(dp)        # mètres par pixel (le long de AB)
        self.e = etirement                                               # étirement en travers (épaisseur relative)
        ang = np.arctan2(dp[1], dp[0])
        self.c, self.sn = np.cos(ang), np.sin(ang)
        self.A_p, self.miroir = A_p, miroir
        self.longueur = float(np.linalg.norm(B - self.A))

    def vers_planche(self, u, v):
        """(u, v) en mètres dans le repère (U, V) depuis A -> pixels de la planche."""
        a, b = u / self.s, v / (self.s * self.e)
        qx, qy = a * self.c - b * self.sn, a * self.sn + b * self.c
        if self.miroir:
            qx = -qx
        return self.A_p[0] + qx, self.A_p[1] - qy

    def vers_modele(self, px, py):
        qx, qy = px - self.A_p[0], -(py - self.A_p[1])
        if self.miroir:
            qx = -qx
        a = qx * self.c + qy * self.sn
        b = -qx * self.sn + qy * self.c
        return self.A + self.U * a * self.s + self.V * b * self.s * self.e

    def local(self, P):
        q = P - self.A.astype(np.float32)
        return q @ self.U.astype(np.float32), q @ self.V.astype(np.float32), q @ self.W.astype(np.float32)


def lisser_contour(contour_px, pas=2.0, sigma=3.0):
    """Contour fermé rééchantillonné tous les « pas » pixels puis lissé (gaussienne circulaire de sigma
    points) : efface le tremblé du trait dessiné sans changer la forme."""
    c = np.asarray(contour_px, np.float64)
    c = np.vstack([c, c[:1]])
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
    n = max(16, int(L[-1] / pas))
    t = np.linspace(0, L[-1], n, endpoint=False)
    r = np.stack([np.interp(t, L, c[:, 0]), np.interp(t, L, c[:, 1])], 1)
    if sigma > 0:
        k = int(3 * sigma)
        w = np.exp(-0.5 * (np.arange(-k, k + 1) / sigma) ** 2)
        w /= w.sum()
        r = np.stack([np.convolve(np.r_[r[-k:, i], r[:, i], r[:k, i]], w, "valid") for i in range(2)], 1)
    return r


def cartes_silhouette(contour_px, forme="rond", k=1.0, plat=None, marge=12, lissage=1.5, sigma_contour=3.0, zones=()):
    """Prépare, en pixels de planche, la distance signée au contour et la demi-épaisseur :
    « rond » : section ronde (os long, k = rapport épaisseur / largeur) ;
    « plat » : épaisseur constante plat (pixels) loin du bord, bord arrondi (os plat)."""
    import cv2
    cf = lisser_contour(contour_px, sigma=sigma_contour)
    x0, y0 = np.floor(cf.min(0)).astype(int) - marge
    x1, y1 = np.ceil(cf.max(0)).astype(int) + marge
    # masque sur-échantillonné x4 (bord net), puis distances en pixels de planche
    S = 4
    mh = np.zeros(((y1 - y0 + 1) * S, (x1 - x0 + 1) * S), np.uint8)
    cv2.fillPoly(mh, [np.round((cf - [x0, y0]) * S + (S - 1) / 2).astype(np.int32)], 1)
    dinh = cv2.distanceTransform(mh, cv2.DIST_L2, 5) / S
    douth = cv2.distanceTransform(1 - mh, cv2.DIST_L2, 5) / S
    sdh = (douth - dinh).astype(np.float32)
    sd = cv2.resize(sdh, (x1 - x0 + 1, y1 - y0 + 1), interpolation=cv2.INTER_AREA)
    din = np.maximum(-sd, 0).astype(np.float32)
    m = (sd < 0).astype(np.uint8)
    if forme == "rond":
        rmax = float(din.max())
        r = max(3, int(rmax * 0.9))
        rloc = cv2.dilate(din, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        rloc = cv2.GaussianBlur(rloc, (0, 0), r * 0.5)
        rloc = np.maximum(rloc, din)
        t = k * np.sqrt(np.maximum(din * (2 * rloc - din), 0))
    else:
        t = plat * np.sqrt(np.clip(din / max(plat * 1.2, 1e-3), 0, 1) * (2 - np.clip(din / max(plat * 1.2, 1e-3), 0, 1)))
    # zones d'épaisseur : [(polygone en pixels de planche, facteur), ...] (raccord progressif)
    if zones:
        fac = np.ones_like(t, np.float32)
        for poly, facteur in zones:
            zm = np.zeros_like(m)
            cv2.fillPoly(zm, [np.asarray(poly, np.int32) - [x0, y0]], 1)
            zm = cv2.GaussianBlur(zm.astype(np.float32), (0, 0), 6)
            fac = fac * (1 + (facteur - 1) * zm)
        t = t * fac
    if lissage:
        t = cv2.GaussianBlur(t.astype(np.float32), (0, 0), lissage)
    t[m == 0] = 0
    return {"sd": sd, "t": t.astype(np.float32), "origine": (x0, y0)}


def silhouette(cartes, pose, decal=0.0, epaisseur=1.0, decal_b=None):
    """Os « gonflé » d'après sa silhouette de planche : distance au contour dans le plan, demi-épaisseur
    lue dans la carte (en travers du plan, décalée de « decal » mètres le long de W ; si decal_b est
    donné, le décalage passe progressivement de decal en A à decal_b en B)."""
    sd, t, (ox, oy) = cartes["sd"], cartes["t"], cartes["origine"]
    s = pose.s
    h, w = sd.shape
    coins = [pose.vers_modele(ox + a, oy + b) for a in (0, w) for b in (0, h)]
    tmax = float(t.max()) * s * epaisseur

    def f(P):
        u, v, ww = pose.local(P)
        px, py = pose.vers_planche(u, v)
        d2 = _bilineaire(sd, px - ox, py - oy, 50.0) * s
        tt = _bilineaire(t, px - ox, py - oy, 0.0) * s * epaisseur
        if decal_b is None:
            dc = decal
        else:
            dc = decal + (decal_b - decal) * np.clip(u / pose.longueur, 0.0, 1.0)
        dw = np.abs(ww - dc) - tt
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dw, 0) ** 2)
        return np.minimum(np.maximum(d2, dw), 0) + dehors
    dmax = max(abs(decal), abs(decal_b or 0.0))
    lo = np.min(coins, 0) - tmax - dmax - 0.01
    hi = np.max(coins, 0) + tmax + dmax + 0.01
    return Prim(f, lo, hi)



def relief(contour_px, trous_px, px_vers_xz, appuis_y, appuis_e, pas=0.003, marge=0.03):
    """Os « en relief » d'après sa silhouette vue de DESSUS (bassin) : le contour (pixels de planche) est
    reporté dans le plan (x, z) du modèle par px_vers_xz (affine 2x3) ; chaque point (x, z) de l'os est
    à la hauteur y lue sur une surface lisse passant par les points d'appui (x, z, y), avec une
    demi-épaisseur (normale à la surface) interpolée de même dans appuis_e (x, z, e)."""
    import cv2
    from scipy.interpolate import RBFInterpolator
    M = np.asarray(px_vers_xz, np.float64)                      # [[ax, bx, cx], [az, bz, cz]]
    Mi = np.linalg.inv(np.vstack([M, [0, 0, 1]]))[:2]           # (x, z) -> pixels
    s_moy = np.sqrt(abs(np.linalg.det(M[:, :2])))               # mètres par pixel (moyen)
    c = lisser_contour(contour_px, sigma=1.5)
    x0, y0 = np.floor(c.min(0)).astype(int) - 10
    x1, y1 = np.ceil(c.max(0)).astype(int) + 10
    S = 4
    mh = np.zeros(((y1 - y0 + 1) * S, (x1 - x0 + 1) * S), np.uint8)
    cv2.fillPoly(mh, [np.round((c - [x0, y0]) * S + (S - 1) / 2).astype(np.int32)], 1)
    for t in trous_px:
        ct = lisser_contour(t, sigma=1.0)
        cv2.fillPoly(mh, [np.round((ct - [x0, y0]) * S + (S - 1) / 2).astype(np.int32)], 0)
    sdh = (cv2.distanceTransform(1 - mh, cv2.DIST_L2, 5) - cv2.distanceTransform(mh, cv2.DIST_L2, 5)) / S
    sd = cv2.resize(sdh.astype(np.float32), (x1 - x0 + 1, y1 - y0 + 1), interpolation=cv2.INTER_AREA)
    coins = np.array([[x0, y0, 1], [x1, y0, 1], [x0, y1, 1], [x1, y1, 1]], np.float64) @ M.T
    xz_lo, xz_hi = coins.min(0) - marge, coins.max(0) + marge
    gx = np.arange(xz_lo[0], xz_hi[0] + pas, pas)
    gz = np.arange(xz_lo[1], xz_hi[1] + pas, pas)
    GX, GZ = np.meshgrid(gx, gz, indexing="ij")
    q = np.stack([GX.ravel(), GZ.ravel()], 1)
    ay = np.asarray(appuis_y, np.float64)
    ae = np.asarray(appuis_e, np.float64)
    Ygrid = RBFInterpolator(ay[:, :2], ay[:, 2], kernel="thin_plate_spline", smoothing=1e-4)(q).reshape(GX.shape)
    Egrid = RBFInterpolator(ae[:, :2], ae[:, 2], kernel="thin_plate_spline", smoothing=1e-4)(q).reshape(GX.shape)
    Egrid = np.clip(Egrid, 0.004, 0.06)
    gyx, gyz = np.gradient(Ygrid, pas, pas)
    Ev = (Egrid * np.sqrt(1 + gyx ** 2 + gyz ** 2)).astype(np.float32)      # épaisseur mesurée à la verticale
    Ygrid = Ygrid.astype(np.float32)
    ylo, yhi = float((Ygrid - Ev).min()), float((Ygrid + Ev).max())
    Mi32 = Mi.astype(np.float32)
    YT, ET = np.ascontiguousarray(Ygrid.T), np.ascontiguousarray(Ev.T)

    def f(P):
        x, y, z = P[..., 0], P[..., 1], P[..., 2]
        px = Mi32[0, 0] * x + Mi32[0, 1] * z + Mi32[0, 2]
        py = Mi32[1, 0] * x + Mi32[1, 1] * z + Mi32[1, 2]
        d2 = _bilineaire(sd, px - x0, py - y0, 50.0) * s_moy
        ix = (x - gx[0]) / pas
        iz = (z - gz[0]) / pas
        yc = _bilineaire(YT, ix, iz, 0.0)
        ev = _bilineaire(ET, ix, iz, 0.0)
        dy = np.abs(y - yc) - ev
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dy, 0) ** 2)
        return np.minimum(np.maximum(d2, dy), 0) + dehors
    lo = np.array([xz_lo[0], ylo - 0.01, xz_lo[1]])
    hi = np.array([xz_hi[0], yhi + 0.01, xz_hi[1]])
    return Prim(f, lo, hi)



def volume_profil(contour_px, pose, largeur, p=2.6, haut_etroit=0.7, pas_u=0.002):
    """Volume dont le PROFIL est la silhouette de planche (posée par « pose ») et la LARGEUR une demi-largeur
    donnée le long de l'axe A -> B (tableau [(u 0..1, demi-largeur m)]) : section en super-ellipse (exposant p)
    qui suit la hauteur locale du profil, un peu plus étroite en haut (haut_etroit) qu'en bas. Pour le crâne."""
    import cv2
    cartes = cartes_silhouette(contour_px, forme="plat", plat=1.0)
    sd, (ox, oy) = cartes["sd"], cartes["origine"]
    s = pose.s
    L = pose.longueur
    larg = np.asarray(largeur, np.float64)
    # étendue verticale (v) du profil pour chaque u (tranche de 2 mm)
    h, w = sd.shape
    yy, xx = np.nonzero(sd < 0)
    Pm = np.array([pose.vers_modele(ox + x, oy + y) for x, y in zip(xx[::3], yy[::3])])
    q = Pm - pose.A
    uu, vv = q @ pose.U, q @ pose.V
    u0, u1 = uu.min() - 0.01, uu.max() + 0.01
    nb = int((u1 - u0) / pas_u) + 1
    k = np.clip(((uu - u0) / pas_u).astype(int), 0, nb - 1)
    vlo = np.full(nb, np.inf); vhi = np.full(nb, -np.inf)
    np.minimum.at(vlo, k, vv); np.maximum.at(vhi, k, vv)
    ok = np.isfinite(vlo)
    idx = np.arange(nb)
    vlo = np.interp(idx, idx[ok], vlo[ok]).astype(np.float32)
    vhi = np.interp(idx, idx[ok], vhi[ok]).astype(np.float32)
    lu = np.interp(u0 + idx * pas_u, larg[:, 0] * L, larg[:, 1]).astype(np.float32)
    coins = [pose.vers_modele(ox + a, oy + b) for a in (0, w) for b in (0, h)]
    wmax = float(larg[:, 1].max())

    def f(P):
        u, v, ww = pose.local(P)
        px, py = pose.vers_planche(u, v)
        d2 = _bilineaire(sd, px - ox, py - oy, 50.0) * s
        i = np.clip((u - u0) / pas_u, 0, nb - 1).astype(np.int64)
        lo_, hi_, lw = vlo[i], vhi[i], lu[i]
        eta = np.clip((2 * v - lo_ - hi_) / np.maximum(hi_ - lo_, 1e-4), -1, 1)
        forme = (1 - np.abs(eta) ** p) ** (1.0 / p)
        hw = lw * forme * (1 - (1 - haut_etroit) * np.clip(eta, 0, 1))
        dw = np.abs(ww) - hw
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dw, 0) ** 2)
        return np.minimum(np.maximum(d2, dw), 0) + dehors
    lo = np.min(coins, 0) - wmax - 0.01
    hi = np.max(coins, 0) + wmax + 0.01
    return Prim(f, lo, hi)
