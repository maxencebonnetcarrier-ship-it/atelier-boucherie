# Fabrique les modèles 3D de l'appli à partir des formes (formes.py) et des planches de cours.
#
#   python outils/modeles3d.py apercu [animal]   -> outils/controle/forme_<animal>.png (vues de profil/dessus quadrillées)
#   python outils/modeles3d.py                   -> app/data/modeles3d.js (maillages + cartes des pièces)
#
# Étapes : volume signé sur une grille -> surface (marching cubes) -> simplification ;
# carte des pièces = la planche de cours déformée (spline « plaque mince ») sur le profil du modèle.
import base64
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from formes import ESPECES  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTROLE = os.path.join(RACINE, "outils", "controle")
CACHE = os.path.join(RACINE, "outils", "cache")
APP = os.path.join(RACINE, "app")
PAS = 0.011  # taille d'une case de la grille 3D (unités du modèle)


def boite(s):
    """Boîte englobante du modèle, mesurée sur une grille grossière."""
    xs, ys, zs = np.arange(-2.0, 1.8, 0.03), np.arange(-0.05, 1.9, 0.03), np.arange(-0.8, 0.8, 0.03)
    P = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), -1).astype(np.float32)
    d = s.distance(P)
    idx = np.argwhere(d < 0.03)
    lo = np.array([xs[idx[:, 0].min()], ys[idx[:, 1].min()], zs[idx[:, 2].min()]]) - 0.06
    hi = np.array([xs[idx[:, 0].max()], ys[idx[:, 1].max()], zs[idx[:, 2].max()]]) + 0.06
    return lo, hi


def volume(s, pas=PAS):
    lo, hi = boite(s)
    axes = [np.arange(lo[i], hi[i] + pas, pas, dtype=np.float32) for i in range(3)]
    vol = np.empty([len(a) for a in axes], np.float32)
    # par tranches de x pour limiter la mémoire
    Y, Z = np.meshgrid(axes[1], axes[2], indexing="ij")
    for i, x in enumerate(axes[0]):
        P = np.stack([np.full_like(Y, x), Y, Z], -1)
        vol[i] = s.distance(P)
    return vol, axes


def profil(vol, axes):
    """Silhouette de profil (vue depuis +z) : masque et profondeur, indexés [y, x] (y vers le haut)."""
    dedans = vol < 0
    masque = dedans.any(axis=2)
    nz = vol.shape[2]
    zmax = np.where(masque, nz - 1 - np.argmax(dedans[:, :, ::-1], axis=2), 0)
    prof = axes[2][zmax]
    return masque.T, np.where(masque, prof, np.nan).T


def ombrer(prof, pas):
    gy, gx = np.gradient(np.nan_to_num(prof, nan=0.0), pas)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    lum = np.clip(n @ np.array([0.35, 0.5, 0.8]) / np.linalg.norm([0.35, 0.5, 0.8]), 0, 1)
    img = (60 + 180 * lum).astype(np.uint8)
    img[np.isnan(prof)] = 255
    return img


def quadriller(img, axes_x, axes_y, pas_grille=0.1, echelle=3):
    """Agrandit l'image (indexée [y bas->haut, x]) et ajoute une grille en unités du modèle."""
    im = cv2.cvtColor(img[::-1], cv2.COLOR_GRAY2BGR) if img.ndim == 2 else img[::-1].copy()
    im = cv2.resize(im, None, fx=echelle, fy=echelle, interpolation=cv2.INTER_NEAREST)
    H = im.shape[0]
    for v in np.arange(np.ceil(axes_x[0] / pas_grille) * pas_grille, axes_x[-1], pas_grille):
        c = int((v - axes_x[0]) / (axes_x[1] - axes_x[0]) * echelle)
        fort = abs(round(v / 0.5) * 0.5 - v) < 1e-6
        cv2.line(im, (c, 0), (c, H), (0, 120, 255) if fort else (255, 200, 120), 1)
        if fort:
            cv2.putText(im, f"{v:.1f}", (c + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 80, 200), 1)
    for v in np.arange(np.ceil(axes_y[0] / pas_grille) * pas_grille, axes_y[-1], pas_grille):
        r = H - int((v - axes_y[0]) / (axes_y[1] - axes_y[0]) * echelle)
        fort = abs(round(v / 0.5) * 0.5 - v) < 1e-6
        cv2.line(im, (0, r), (im.shape[1], r), (0, 120, 255) if fort else (255, 200, 120), 1)
        if fort:
            cv2.putText(im, f"{v:.1f}", (2, r - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 80, 200), 1)
    return im


def apercu(nom):
    s = ESPECES[nom]()
    vol, axes = volume(s, pas=0.012)
    _, prof = profil(vol, axes)
    cote = quadriller(ombrer(prof, 0.012), axes[0], axes[1])
    # vue de dessus : profondeur selon y
    dedans = vol < 0
    m = dedans.any(axis=1)
    ymax = np.where(m, vol.shape[1] - 1 - np.argmax(dedans[:, ::-1, :], axis=1), 0)
    haut = np.where(m, axes[1][ymax], np.nan).T  # [z, x]
    dessus = quadriller(ombrer(haut, 0.012), axes[0], axes[2])
    w = max(cote.shape[1], dessus.shape[1])
    pad = lambda im: cv2.copyMakeBorder(im, 0, 0, 0, w - im.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))
    os.makedirs(CONTROLE, exist_ok=True)
    cv2.imencode(".png", np.vstack([pad(cote), pad(dessus)]))[1].tofile(os.path.join(CONTROLE, f"forme_{nom}.png"))
    print(f"{nom}: grille {vol.shape}, boîte x[{axes[0][0]:.2f},{axes[0][-1]:.2f}] y[{axes[1][0]:.2f},{axes[1][-1]:.2f}] z[{axes[2][0]:.2f},{axes[2][-1]:.2f}]")


# ---------------------------------------------------------------------------------------------
# Repères anatomiques : (position sur le modèle en unités, position sur la planche en pixels).
# La planche de cours est déformée pour que ses repères tombent sur ceux du modèle : chaque
# pièce de la planche se retrouve ainsi à sa place anatomique sur le corps 3D.
# Les positions sur le modèle sont dans formes.py (attribut « reperes » de chaque animal).
REPERES_PLANCHE = {
    "boeuf": {
        "nez": (8, 162), "nuque": (103, 44), "gorge": (94, 200), "garrot": (219, 36), "dos": (450, 59),
        "hanche": (719, 50), "queue": (790, 88), "fesse": (784, 162), "jarret": (756, 369), "sabot_ar": (719, 494),
        "grasset": (656, 312), "ventre": (406, 340), "coude": (300, 340), "poitrail": (156, 250),
        "sabot_av": (240, 494), "genou": (256, 400),
    },
    "veau": {  # planche tournée vers la droite
        "nez": (797, 166), "nuque": (719, 31), "gorge": (672, 222), "garrot": (562, 69), "dos": (312, 91),
        "hanche": (112, 69), "queue": (37, 78), "fesse": (25, 187), "jarret": (22, 431), "sabot_ar": (100, 625),
        "grasset": (156, 350), "ventre": (312, 375), "coude": (450, 400), "poitrail": (625, 350),
        "sabot_av": (525, 625), "genou": (522, 475),
    },
    "porc": {
        "nez": (475, 246), "nuque": (408, 173), "gorge": (400, 275), "garrot": (369, 152), "dos": (250, 144),
        "hanche": (162, 154), "queue": (123, 173), "fesse": (121, 215), "jarret": (144, 296), "sabot_ar": (154, 352),
        "grasset": (200, 285), "ventre": (250, 300), "coude": (296, 296), "poitrail": (362, 277),
        "sabot_av": (338, 352), "genou": (352, 319),
    },
    "agneau": {  # gravure : l'agneau broute, tête en bas à droite
        "nez": (343, 250), "nuque": (347, 170), "gorge": (300, 190), "garrot": (293, 87), "dos": (150, 13),
        "hanche": (93, 10), "queue": (47, 47), "fesse": (40, 77), "jarret": (55, 167), "sabot_ar": (73, 253),
        "grasset": (130, 143), "ventre": (167, 152), "coude": (205, 147), "poitrail": (263, 160),
        "sabot_av": (233, 257), "genou": (240, 207),
    },
}


def reperes(nom, s):
    """Paires (position modèle, position planche) des repères connus des deux côtés."""
    pl = REPERES_PLANCHE[nom]
    return {k: (s.reperes[k], pl[k]) for k in s.reperes if k in pl}


TOUT_DECOUPE = {"porc", "agneau"}

CORRECTIONS = {
    "porc": [("sous", 0.17, "pied")],      # sous le genou et le jarret : pieds
    "agneau": [("sous", 0.28, "pieds")],
}

# Parties qui ne sont pas des pièces de boucherie (affichées en couleur neutre, non cliquables).
# Code par sommet : 0 = suit la carte des pièces, 1 = sabot, 2 = corne, 3 = robe (pelage), 4 = œil.
NEUTRES = {
    "boeuf": {"sabot": 1, "corne": 2, "oreille": 3, "queue": 3, "oeil": 4},
    "veau": {"sabot": 1, "oreille": 3, "queue": 3, "oeil": 4},
    "porc": {"oeil": 4},
    "agneau": {"queue": 3, "oeil": 4},
}


def occlusion(s, v, f, pas=0.035, n=5):
    """Ombrage des creux précalculé par sommet (1 = à découvert, 0 = au fond d'un creux) :
    on sonde le volume le long de la normale ; si la matière revient vite, le point est abrité."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    fn = np.cross(b - a, c - a)
    nor = np.zeros_like(v)
    for k in range(3):
        np.add.at(nor, f[:, k], fn)
    nor /= np.linalg.norm(nor, axis=1, keepdims=True) + 1e-9
    occ = np.zeros(len(v))
    poids = 1.0
    for i in range(1, n + 1):
        h = pas * i
        d = s.distance((v + nor * h).astype(np.float32)[None])[0]
        occ += poids * np.clip(h - d, 0, None) / h
        poids *= 0.6
    return np.clip(1.0 - 0.9 * occ, 0.0, 1.0)


def tps(src, dst, lam=1e-3):
    """Spline « plaque mince » 2D : renvoie une fonction qui envoie src -> dst."""
    src = np.asarray(src, float); dst = np.asarray(dst, float)
    n = len(src)
    def U(r2):
        with np.errstate(divide="ignore", invalid="ignore"):
            return np.where(r2 > 0, r2 * np.log(r2), 0.0)
    d2 = ((src[:, None, :] - src[None, :, :]) ** 2).sum(-1)
    K = U(d2) + lam * np.eye(n)
    P = np.hstack([np.ones((n, 1)), src])
    A = np.zeros((n + 3, n + 3)); A[:n, :n] = K; A[:n, n:] = P; A[n:, :n] = P.T
    b = np.zeros((n + 3, 2)); b[:n] = dst
    coef = np.linalg.solve(A, b)
    w, a = coef[:n], coef[n:]
    def f(pts):
        pts = np.asarray(pts, float)
        d2p = ((pts[:, None, :] - src[None, :, :]) ** 2).sum(-1)
        return U(d2p) @ w + a[0] + pts @ a[1:]
    return f


def carte_pieces(nom, s, masque, axes, largeur=1024):
    """Carte 2D (profil) des pièces sur le modèle : étiquette par pixel, -1 = aucune pièce."""
    eti = np.load(os.path.join(CACHE, f"etiquettes_{nom}.npz"))
    L, ids = eti["L"], [str(i) for i in eti["ids"]]
    x0, x1 = float(axes[0][0]), float(axes[0][-1])
    y0, y1 = float(axes[1][0]), float(axes[1][-1])
    hauteur = int(round(largeur * (y1 - y0) / (x1 - x0)))
    xs = x0 + (np.arange(largeur) + 0.5) * (x1 - x0) / largeur
    ys = y1 - (np.arange(hauteur) + 0.5) * (y1 - y0) / hauteur      # ligne 0 = haut
    # silhouette du modèle ré-échantillonnée à la résolution de la carte, un peu élargie
    m = cv2.resize(masque[::-1].astype(np.uint8), (largeur, hauteur), interpolation=cv2.INTER_NEAREST)
    m = cv2.dilate(m, np.ones((7, 7), np.uint8)).astype(bool)
    rep = reperes(nom, s)
    f = tps([v[0] for v in rep.values()], [v[1] for v in rep.values()])
    yy, xx = np.nonzero(m)
    src = f(np.stack([xs[xx], ys[yy]], -1))
    px = np.clip(np.round(src[:, 0]).astype(int), 0, L.shape[1] - 1)
    py = np.clip(np.round(src[:, 1]).astype(int), 0, L.shape[0] - 1)
    dehors = (src[:, 0] < 0) | (src[:, 0] >= L.shape[1]) | (src[:, 1] < 0) | (src[:, 1] >= L.shape[0])
    C = np.full((hauteur, largeur), -1, np.int16)
    C[yy, xx] = np.where(dehors, -1, L[py, px])
    # Les traits noirs épais de la planche laissent des bandes sans pièce : on les comble en
    # faisant grandir les pièces voisines de quelques pixels (les grandes zones neutres,
    # tête ou pattes grises de la planche, restent neutres).
    noyau = np.ones((3, 3), np.uint8)
    for _ in range(9):
        libre = (C == -1) & m
        if not libre.any():
            break
        ajout = np.full(C.shape, -1, np.int16)
        for i in range(len(ids)):
            d = cv2.dilate((C == i).astype(np.uint8), noyau).astype(bool) & libre & (ajout == -1)
            ajout[d] = i
        C = np.where(ajout >= 0, ajout, C)
    # lissage des bords (vote majoritaire) pour effacer l'escalier de la déformation
    C = vote(C, 5)
    # Corrections : sur les planches, les pattes se chevauchent et le bas des membres se
    # reporte mal ; on y pose directement la pièce attendue.
    for regle, y_max, piece in CORRECTIONS.get(nom, []):
        if regle == "sous":
            C[(ys < y_max)[:, None] & m] = ids.index(piece)
    # Porc et agneau : la planche découpe l'animal entier (tête, pieds compris), donc aucun
    # point du corps ne doit rester sans pièce.
    if nom in TOUT_DECOUPE:
        for _ in range(300):
            libre = (C == -1) & m
            if not libre.any():
                break
            ajout = np.full(C.shape, -1, np.int16)
            for i in range(len(ids)):
                d = cv2.dilate((C == i).astype(np.uint8), noyau).astype(bool) & libre & (ajout == -1)
                ajout[d] = i
            C = np.where(ajout >= 0, ajout, C)
    C[~m] = -1
    return C, ids, (x0, x1, y0, y1)


def vote(C, k):
    vals = np.unique(C)
    best = np.full(C.shape, -1e9, np.float32); out = C.copy()
    for v in vals:
        s = cv2.boxFilter((C == v).astype(np.float32), -1, (k, k), normalize=False)
        mieux = s > best
        best[mieux] = s[mieux]; out[mieux] = v
    return out


def rle(arr):
    """Codage par plages (valeur, longueur) d'un tableau d'octets, longueurs sur 2 octets."""
    a = arr.ravel()
    fins = np.flatnonzero(np.diff(a)) + 1
    debuts = np.concatenate([[0], fins]); longs = np.diff(np.concatenate([debuts, [len(a)]]))
    out = []
    for d, l in zip(debuts, longs):
        while l > 0:
            n = min(l, 65535)
            out.append((a[d], n)); l -= n
    buf = np.zeros(len(out), dtype=[("v", "u1"), ("n", "<u2")])
    buf["v"] = [o[0] for o in out]; buf["n"] = [o[1] for o in out]
    return base64.b64encode(buf.tobytes()).decode()


def poser_yeux(s):
    """Place chaque œil à fleur de tête : on cherche la surface le long de z, puis on enfonce
    la bille d'un tiers de son rayon. Renvoie [[x, y, z, r], ...] pour les deux côtés."""
    yeux = []
    for (x, y, z), r in s.yeux:
        zs = np.linspace(z - 0.08, z + 0.15, 400, dtype=np.float32)
        P = np.stack([np.full_like(zs, x), np.full_like(zs, y), zs], -1)[None]
        d = s.distance(P)[0]
        dehors = np.nonzero(d > 0)[0]
        zsurf = float(zs[dehors[0]]) if len(dehors) else z
        zc = zsurf - r * 0.35
        yeux += [[round(x, 4), round(y, 4), round(zc, 4), r], [round(x, 4), round(y, 4), round(-zc, 4), r]]
    return yeux


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def exporter(nom, triangles=16000):
    from skimage.measure import marching_cubes
    import fast_simplification as fs
    s = ESPECES[nom]()
    vol, axes = volume(s)
    pas = float(axes[0][1] - axes[0][0])
    v, f, _, _ = marching_cubes(vol, 0.0, spacing=(pas, pas, pas))
    v += np.array([axes[0][0], axes[1][0], axes[2][0]])
    v, f = fs.simplify(v.astype(np.float32), f.astype(np.int64), target_reduction=1 - triangles / len(f))
    noms, lab = s.parties(v.astype(np.float32)[None])
    code = np.array([NEUTRES[nom].get(noms[i], 0) for i in lab[0]], np.uint8)
    ao = np.round(occlusion(s, v.astype(np.float64), f) * 255).astype(np.uint8)

    lo, hi = v.min(0), v.max(0)
    q = np.round((v - lo) / (hi - lo) * 65535).astype("<u2")

    masque, _ = profil(vol, axes)
    C, ids, (x0, x1, y0, y1) = carte_pieces(nom, s, masque, axes)
    centres, aires = {}, {}
    for i, piece in enumerate(ids):
        mi = (C == i).astype(np.uint8)
        aires[piece] = int(mi.sum())
        if mi.sum() == 0:
            continue
        d = cv2.distanceTransform(mi, cv2.DIST_L2, 3)
        r, c = np.unravel_index(np.argmax(d), d.shape)
        centres[piece] = [round(x0 + (c + 0.5) * (x1 - x0) / C.shape[1], 4), round(y1 - (r + 0.5) * (y1 - y0) / C.shape[0], 4)]
    controle_carte(nom, s, C, ids, masque, axes)
    return {
        "boite": [lo.round(5).tolist(), hi.round(5).tolist()],
        "sommets": b64(q), "triangles": b64(f.astype("<u2" if len(v) < 65536 else "<u4")),
        "indices32": len(v) >= 65536, "parties": b64(code), "ombre": b64(ao), "yeux": poser_yeux(s),
        "carte": {"largeur": C.shape[1], "hauteur": C.shape[0], "x0": x0, "x1": x1, "y0": y0, "y1": y1,
                  "rle": rle((C + 1).astype(np.uint8))},
        "pieces": ids, "centres": centres, "aires": aires,
    }, len(v), len(f)


def controle_carte(nom, s, C, ids, masque, axes):
    """Image de contrôle : carte des pièces sur le profil du modèle, nom au centre de chaque pièce."""
    h, w = C.shape
    rng = np.random.default_rng(5)
    pal = rng.integers(60, 235, (len(ids) + 1, 3)).astype(np.uint8)
    img = np.full((h, w, 3), 255, np.uint8)
    m = cv2.resize(masque[::-1].astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST).astype(bool)
    img[m] = (200, 200, 200)
    sel = C >= 0
    img[sel] = pal[C[sel]]
    bord = (cv2.morphologyEx(C.astype(np.float32), cv2.MORPH_GRADIENT, np.ones((3, 3))) > 0) & m
    img[bord] = (40, 40, 40)
    for i, piece in enumerate(ids):
        mi = (C == i).astype(np.uint8)
        if not mi.any():
            continue
        d = cv2.distanceTransform(mi, cv2.DIST_L2, 3)
        r, c = np.unravel_index(np.argmax(d), d.shape)
        for ep, coul in ((3, (0, 0, 0)), (1, (255, 255, 255))):
            cv2.putText(img, piece, (int(c) - 3 * len(piece), int(r) + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.38, coul, ep)
    # repères du modèle
    x0, x1, y0, y1 = axes[0][0], axes[0][-1], axes[1][0], axes[1][-1]
    for nomr, ((xm, ym), _) in reperes(nom, s).items():
        c = int((xm - x0) / (x1 - x0) * w); r = int((y1 - ym) / (y1 - y0) * h)
        cv2.circle(img, (c, r), 4, (0, 0, 255), -1)
        cv2.putText(img, nomr, (c + 5, r - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 200), 1)
    os.makedirs(CONTROLE, exist_ok=True)
    cv2.imencode(".png", img)[1].tofile(os.path.join(CONTROLE, f"carte_{nom}.png"))


def main(noms):
    chemin = os.path.join(APP, "data", "modeles3d.js")
    tous = {}
    if os.path.exists(chemin):  # régénération partielle : on garde les autres animaux
        txt = open(chemin, encoding="utf-8").read()
        tous = json.loads(txt[txt.index("{"):txt.rindex("}") + 1])
    for nom in noms:
        tous[nom], nv, nf = exporter(nom)
        vides = [p for p, a in tous[nom]["aires"].items() if a < 150]
        print(f"{nom}: {nv} sommets, {nf} triangles ; pièces trop petites ou absentes : {vides or 'aucune'}")
    with open(chemin, "w", encoding="utf-8", newline="\n") as fo:
        fo.write("// Fichier GÉNÉRÉ par outils/modeles3d.py — ne pas modifier à la main.\n"
                 "// Modèles 3D (maillage compressé) et carte des pièces de chaque animal.\n"
                 "window.MODELES3D = " + json.dumps(tous, ensure_ascii=False) + ";\n")
    print("écrit", os.path.relpath(chemin, RACINE), f"({os.path.getsize(chemin) // 1024} Ko)")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "apercu":
        for n in (sys.argv[2:] or list(ESPECES)):
            apercu(n)
    else:
        main(sys.argv[1:] or [n for n in ESPECES if n in REPERES_PLANCHE])
