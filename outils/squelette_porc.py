# Squelette 3D du PORC, réaliste mais épuré, placé dans le corps de formes.py (porc) : mêmes coordonnées que
# le bœuf (x = longueur, tête vers -x ; y = hauteur, sol en 0 ; z = largeur, côté gauche = z > 0 ; 1 ≈ 1 m).
#
# FORMES : chaque os est construit d'après son dessin dans Sisson, « The Anatomy of the Domestic Animals »
# (1914), chapitre « Skeleton of the pig » (outils/planches_porc.py détoure les figures). Deux techniques :
#  - un os vu sous DEUX angles (crâne de profil et de dessus, vertèbres de profil et de face) est
#    l'intersection des deux silhouettes « extrudées » : sa forme est juste sous les deux angles ;
#  - un os long ou plat vu sous un seul angle est « gonflé » d'après sa silhouette (section ronde ou plate),
#    puis complété de ses reliefs (têtes articulaires, tubérosités, cavités).
# PLACE : les articulations sont relevées sur le squelette entier de Cuyer, « The Artistic Anatomy of
# Animals » (1905), fig. 38, calé dans la silhouette du porc 3D de l'appli (corps plus long et tête plus grosse
# qu'un vrai porc : les os des membres et de la tête sont posés là où sont la patte et la tête du modèle).
# Formule vertébrale (Sisson) : 7 cervicales, 14 dorsales, 7 lombaires, 4 sacrées, 20 coccygiennes ; 14 paires
# de côtes (7 sternales), sternum de 6 segments ; 4 doigts à chaque pied (2 grands, 2 petits « ergots »).
# Les os pairs ne sont sculptés que du côté gauche : le côté droit est leur reflet (z -> -z).
import cv2
import numpy as np

from sdf import (Forme, Placement, Prim, Repere, _bilineaire, boite, cap, courbe, cylindre, ell, intersection_douce,
                 lisser_contour, loft, n_, plaque, tore)
from planches_porc import FIGURES, figure

X = np.array([1.0, 0.0, 0.0])
Y = np.array([0.0, 1.0, 0.0])
Z = np.array([0.0, 0.0, 1.0])


def p3(x, y, z=0.0):
    return np.array([x, y, z], np.float64)


# ================================================================ silhouettes des figures
def silhouette_fig(nom, garder=(), retirer=(), sym=None):
    """Silhouette d'une figure de Sisson (pixels de page) : {"contour", "trous"}.
    garder / retirer : polygones (pixels de page) ; sym = (milieu x, « gauche » | « droite ») : on garde cette
    moitié de la figure et on la reflète (os symétrique dont une moitié est gâchée par une légende)."""
    d = figure(nom)
    x0, y0, x1, y1 = FIGURES[nom]["cadre"]
    marge = 6
    if sym is not None:                       # place pour le reflet de part et d'autre du milieu
        demi = max(sym[0] - x0, x1 - sym[0]) + marge
        x0, x1 = int(sym[0] - demi), int(sym[0] + demi)
    off = np.array([x0 - marge, y0 - marge])
    m = np.zeros((y1 - y0 + 2 * marge, x1 - x0 + 2 * marge), np.uint8)
    cv2.fillPoly(m, [np.asarray(d["contour"], np.int32) - off], 1)
    for t in d["trous"]:
        cv2.fillPoly(m, [np.asarray(t, np.int32) - off], 0)
    if garder:
        g = np.zeros_like(m)
        for p in garder:
            cv2.fillPoly(g, [np.asarray(p, np.int32) - off], 1)
        m &= g
    for p in retirer:
        cv2.fillPoly(m, [np.asarray(p, np.int32) - off], 0)
    if sym is not None:
        mil, cote = sym
        c = mil - off[0]
        xs = np.arange(m.shape[1])
        src = np.round(2 * c - xs).astype(int)
        refl = np.zeros_like(m)
        ok = (src >= 0) & (src < m.shape[1])
        refl[:, ok] = m[:, src[ok]]
        garde = xs <= c if cote == "gauche" else xs >= c
        m = np.where(garde[None, :], m, refl)
    cs, h = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    ext = [i for i, hh in enumerate(h[0]) if hh[3] < 0]
    i0 = max(ext, key=lambda i: cv2.contourArea(cs[i]))
    trous = [cs[i][:, 0, :] + off for i, hh in enumerate(h[0]) if hh[3] == i0 and cv2.contourArea(cs[i]) > 60]
    return {"contour": cs[i0][:, 0, :] + off, "trous": trous}


def cartes(sil, forme="plat", k=1.0, plat=None, zones=(), lissage=1.5, sigma=2.5, marge=14, flou=6):
    """Distance signée au contour (pixels de page) et demi-épaisseur, trous compris (comme
    sdf.cartes_silhouette, qui ne connaît pas les trous)."""
    cf = lisser_contour(sil["contour"], sigma=sigma)
    x0, y0 = np.floor(cf.min(0)).astype(int) - marge
    x1, y1 = np.ceil(cf.max(0)).astype(int) + marge
    S = 4
    mh = np.zeros(((y1 - y0 + 1) * S, (x1 - x0 + 1) * S), np.uint8)
    cv2.fillPoly(mh, [np.round((cf - [x0, y0]) * S + (S - 1) / 2).astype(np.int32)], 1)
    for t in sil.get("trous", []):
        ct = lisser_contour(t, sigma=1.2)
        cv2.fillPoly(mh, [np.round((ct - [x0, y0]) * S + (S - 1) / 2).astype(np.int32)], 0)
    sdh = (cv2.distanceTransform(1 - mh, cv2.DIST_L2, 5) - cv2.distanceTransform(mh, cv2.DIST_L2, 5)) / S
    sd = cv2.resize(sdh.astype(np.float32), (x1 - x0 + 1, y1 - y0 + 1), interpolation=cv2.INTER_AREA)
    din = np.maximum(-sd, 0).astype(np.float32)
    m = (sd < 0).astype(np.uint8)
    if forme == "rond":
        rmax = float(din.max())
        r = max(3, int(rmax * 0.9))
        rloc = cv2.dilate(din, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1)))
        rloc = np.maximum(cv2.GaussianBlur(rloc, (0, 0), r * 0.5), din)
        t = k * np.sqrt(np.maximum(din * (2 * rloc - din), 0))
    elif plat is None:                    # seulement le contour (extrusion) : pas d'épaisseur
        t = np.zeros_like(din)
    else:
        q = np.clip(din / max(plat * 1.2, 1e-3), 0, 1)
        t = plat * np.sqrt(q * (2 - q))
    if zones:
        fac = np.ones_like(t, np.float32)
        for poly, facteur in zones:
            zm = np.zeros_like(m)
            cv2.fillPoly(zm, [np.asarray(poly, np.int32) - [x0, y0]], 1)
            zm = cv2.GaussianBlur(zm.astype(np.float32), (0, 0), flou)
            fac = fac * (1 + (facteur - 1) * zm)
        t = t * fac
    if lissage:
        t = cv2.GaussianBlur(t.astype(np.float32), (0, 0), lissage)
    t[m == 0] = 0
    return {"sd": sd, "t": t.astype(np.float32), "origine": (x0, y0)}


def _coins(c, pose, epais):
    h, w = c["sd"].shape
    ox, oy = c["origine"]
    pts = np.array([pose.vers_modele(ox + a, oy + b) for a in (0, w) for b in (0, h)])
    return np.vstack([pts + pose.W * epais, pts - pose.W * epais])


def extrusion(c, pose, epais=0.35):
    """La silhouette c prolongée tout droit en travers de sa figure (le long de pose.W)."""
    sd, (ox, oy) = c["sd"], c["origine"]
    s = pose.s

    def f(P):
        u, v, _ = pose.local(P)
        px, py = pose.vers_planche(u, v)
        return _bilineaire(sd, px - ox, py - oy, 60.0) * s
    pts = _coins(c, pose, epais)
    return Prim(f, pts.min(0), pts.max(0))


def coque(prims, k=0.003):
    """Intersection (raccord arrondi k) : un os vu sous deux angles est dans les deux extrusions."""
    lo = np.max([p.lo for p in prims], 0)
    hi = np.min([p.hi for p in prims], 0)

    def f(P):
        d = prims[0].f(P)
        for q in prims[1:]:
            d = intersection_douce(d, q.f(P), k)
        return d
    return Prim(f, lo, hi)


def gonfle(c, pose, decal=None, epaisseur=1.0):
    """Os « gonflé » d'après sa silhouette : demi-épaisseur lue dans la carte, de part et d'autre du plan de la
    figure ; decal(u, v) (m) décale la surface moyenne le long de W (os tordu, aile du bassin…)."""
    sd, t, (ox, oy) = c["sd"], c["t"], c["origine"]
    s = pose.s

    def f(P):
        u, v, ww = pose.local(P)
        px, py = pose.vers_planche(u, v)
        d2 = _bilineaire(sd, px - ox, py - oy, 60.0) * s
        tt = _bilineaire(t, px - ox, py - oy, 0.0) * s * epaisseur
        dc = 0.0 if decal is None else decal(u, v)
        dw = np.abs(ww - dc) - tt
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dw, 0) ** 2)
        return np.minimum(np.maximum(d2, dw), 0) + dehors
    pts = _coins(c, pose, float(t.max()) * s * epaisseur + 0.04)
    return Prim(f, pts.min(0), pts.max(0))


def demi_plan(A, n):
    """Ce qui est du côté +n du plan passant par A (pour couper un os)."""
    A32, n32 = np.asarray(A, np.float32), np.asarray(n_(n), np.float32)
    return Prim(lambda P: -((P - A32) @ n32), (-5, -5, -5), (5, 5, 5))


def sd_boite2(u, v, cu, cv, hu, hv, r=0.0):
    """Distance 2D à un rectangle (centre, demi-tailles) aux coins arrondis de r."""
    qu = np.abs(u - cu) - (hu - r)
    qv = np.abs(v - cv) - (hv - r)
    return np.sqrt(np.maximum(qu, 0) ** 2 + np.maximum(qv, 0) ** 2) + np.minimum(np.maximum(qu, qv), 0) - r


def placer(sil, Ap, Bp, A, B, normale=Z, miroir=False, etirement=1.0):
    return Placement(Ap, Bp, A, B, normale=normale, miroir=miroir, etirement=etirement)


# ================================================================ colonne vertébrale
# Ligne du centre des corps vertébraux (z = 0), relevée sur Cuyer (fig. 38) calée dans le porc 3D : cou presque
# horizontal, dos qui monte doucement jusqu'aux reins, sacrum, puis la queue (qui suit la vrille du modèle).
_PTS_COL = [(-0.89, 0.786), (-0.80, 0.765), (-0.72, 0.752), (-0.64, 0.755), (-0.55, 0.768), (-0.40, 0.786),
            (-0.25, 0.80), (-0.10, 0.815), (0.05, 0.835), (0.20, 0.852), (0.35, 0.862), (0.50, 0.866), (0.60, 0.864),
            (0.70, 0.856), (0.78, 0.850), (0.85, 0.854), (0.885, 0.862)]
_t = np.linspace(0, 2.2 * np.pi, 14)
_QUEUE = [(0.93 + 0.05 * np.sin(a) + 0.012 * a, 0.9 + 0.05 * np.cos(a) - 0.01 * a) for a in _t]   # vrille de formes.porc
LIGNE = courbe([(x, y, 0.0) for x, y in _PTS_COL] + [(x, y, 0.0) for x, y in _QUEUE[1:]], n=900)
_long = np.r_[0, np.cumsum(np.linalg.norm(np.diff(LIGNE, axis=0), axis=1))]


def le_long(s):
    i = int(np.clip(np.searchsorted(_long, s) - 1, 0, len(LIGNE) - 2))
    t = (s - _long[i]) / (_long[i + 1] - _long[i])
    return LIGNE[i] * (1 - t) + LIGNE[i + 1] * t, n_(LIGNE[i + 1] - LIGNE[i])


L_CERV = [0.030, 0.046, 0.033, 0.033, 0.033, 0.033, 0.032]
L_DORS = [0.0416] * 14
L_LOMB = [0.060, 0.061, 0.062, 0.063, 0.063, 0.063, 0.062]
L_SACRUM = 0.180
N_COCC = 20
DISQUE = 0.006


def _positions():
    out = {}
    s = 0.0
    for nom, longueurs, disque in (("C", L_CERV, 0.005), ("T", L_DORS, DISQUE), ("L", L_LOMB, 0.007)):
        for i, L in enumerate(longueurs):
            P, T = le_long(s + L / 2)
            out[f"{nom}{i + 1}"] = (P, T, L)
            s += L + disque
    P, T = le_long(s + L_SACRUM / 2)
    out["S"] = (P, T, L_SACRUM)
    out["S_debut"] = s
    s += L_SACRUM + 0.005
    for i in range(N_COCC):
        L = 0.030 - 0.017 * i / (N_COCC - 1)
        P, T = le_long(s + L / 2)
        out[f"Co{i + 1}"] = (P, T, L)
        s += L + 0.004
    return out


VERT = _positions()


def repere_vertebre(P, T):
    """u = le long de la colonne (vers la queue), v = vers le haut, w = vers la gauche."""
    V = n_(Y - (Y @ T) * T)
    return T, V, np.cross(T, V)


def _pose_profil(nom, Ap, Bp, etirement=1.0):
    """Figure de profil d'une vertèbre : Ap -> bout crânial du corps, Bp -> bout caudal."""
    P, T, L = VERT[nom]
    u, v, w = repere_vertebre(P, T)
    return Placement(Ap, Bp, P - u * L / 2, P + u * L / 2, normale=w, etirement=etirement)


def _pose_face(nom, Ap, Bp, hauteur, base=0.0):
    """Figure de face d'une vertèbre : Ap (centre du corps, ou base) -> P + v*base, Bp (bout de l'épine) -> à
    « hauteur » au-dessus du corps."""
    P, T, L = VERT[nom]
    u, v, w = repere_vertebre(P, T)
    return Placement(Ap, Bp, P + v * base, P + v * (base + hauteur), normale=-u)


def cervicales():
    """Les 7 cervicales, courtes et larges : atlas (vu de dessus et de face), axis (de profil et de face),
    C3 à C6 (C4 de profil et C6 de face), C7 et sa haute épine (de profil, C6 de face)."""
    f = Forme()
    # atlas : ailes plates, arc dorsal ; vue de dessus (x-z) et de face (y-z)
    P, T, L = VERT["C1"]
    u, v, w = repere_vertebre(P, T)
    larg = 0.135
    s_d = larg / 675.0
    sd = silhouette_fig("atlas_dessus", sym=(535, "gauche"))
    pd = Placement((535, 1925), (535, 2025), P, P + u * (100 * s_d), normale=v)
    # de face (Sisson, fig. 168) : un anneau autour du canal de la moelle, et deux ailes PLATES, presque
    # horizontales, qui descendent un peu vers leur bord (la figure de face les montre en perspective)
    Pc, uu, vv, ww = (P + v * 0.012).astype(np.float32), u.astype(np.float32), v.astype(np.float32), w.astype(np.float32)

    def face_atlas(Pt):
        q = Pt - Pc
        b, c = q @ vv, np.abs(q @ ww)
        anneau = np.sqrt(b ** 2 + (c * 0.9) ** 2) - 0.031
        ailes = sd_boite2(c, b + 0.004 + 0.07 * np.clip(c - 0.03, 0, None), 0.0, 0.0, 0.075, 0.0065, 0.003)
        return np.minimum(anneau, ailes)
    f.ajouter(coque([extrusion(cartes(sd), pd), Prim(face_atlas, P - 0.12, P + 0.12)], k=0.003), 0.003)
    f.creuser(cylindre(P + v * 0.012 - u * 0.05, P + v * 0.012 + u * 0.05, 0.0135), 0.003)      # canal
    for sw in (1, -1):                                                                          # cavités pour le crâne
        f.creuser(ell(P - u * 0.02 + v * 0.006 + w * sw * 0.017, (0.011, 0.014, 0.01), axes=(u, v, w)), 0.003)
    # axis : grande épine en lame, dent qui entre dans l'atlas
    sp = silhouette_fig("axis_profil")
    pp = _pose_profil("C2", (255, 785), (540, 790))
    h = (790 - 250) * pp.s
    sfa = silhouette_fig("axis_face", sym=(1125, "gauche"))
    pfa = _pose_face("C2", (1125, 745), (1125, 215), h)
    f.ajouter(coque([extrusion(cartes(sp), pp), extrusion(cartes(sfa), pfa)], k=0.003), 0.003)
    # C3 à C6 : même forme (C4 de profil, C6 de face), épines de plus en plus hautes
    s4 = silhouette_fig("c4_profil", retirer=[[(195, 1235), (265, 1235), (265, 1320), (195, 1320)],
                                              [(80, 1035), (115, 1035), (115, 1085), (80, 1085)],
                                              [(95, 785), (150, 785), (150, 820), (95, 820)]])
    c4 = cartes(s4)
    s6 = cartes(silhouette_fig("c6_face", sym=(870, "gauche")))
    for i, et in zip(range(3, 7), (0.85, 0.92, 1.0, 1.08)):
        nom = f"C{i}"
        pp = _pose_profil(nom, (170, 1130), (400, 1150), etirement=et)
        h = (1140 - 800) * pp.s * et
        pf = _pose_face(nom, (870, 1100), (868, 605), h * 1.02)
        f.ajouter(coque([extrusion(c4, pp), extrusion(s6, pf)], k=0.003), 0.003)
    # C7 : longue épine (de profil) ; de face, la forme de C6 étirée en hauteur
    s7 = silhouette_fig("c7_profil", retirer=[[(1140, 1275), (1185, 1275), (1185, 1320), (1140, 1320)]])
    pp = _pose_profil("C7", (1185, 1250), (1460, 1230))
    h = (1240 - 420) * pp.s
    pf = Placement((870, 1100), (868, 605), VERT["C7"][0], VERT["C7"][0] + repere_vertebre(*VERT["C7"][:2])[1] * h,
                   normale=-repere_vertebre(*VERT["C7"][:2])[0], etirement=0.55)
    f.ajouter(coque([extrusion(cartes(s7), pp), extrusion(s6, pf)], k=0.003), 0.003)
    return f


# Épines des dorsales : hauteur du bout au-dessus du centre du corps (m) et recul du bout vers la queue (m),
# d'après Cuyer : les premières sont les plus hautes (garrot) et penchées vers l'arrière, puis elles raccourcissent ;
# la 11e est droite (vertèbre « anticlinale ») et les suivantes penchent un peu vers l'avant.
H_EPINES_T = [0.132, 0.138, 0.136, 0.13, 0.122, 0.112, 0.103, 0.095, 0.088, 0.083, 0.08, 0.078, 0.077, 0.077]
RECUL_EPINES_T = [0.03, 0.028, 0.026, 0.023, 0.02, 0.016, 0.012, 0.009, 0.006, 0.003, 0.0, -0.004, -0.007, -0.009]


def vertebre(f, nom, rc, haut_arc=0.016, canal=0.009, articulaires=0.007):
    """Corps (cylindre un peu étranglé), arc, apophyses articulaires, canal de la moelle."""
    P, T, L = VERT[nom]
    u, v, w = repere_vertebre(P, T)
    a, b = P - u * L / 2, P + u * L / 2
    f.ajouter(loft([a, P, b], [rc * 1.08, rc * 0.9, rc * 1.08], [rc * 0.95, rc * 0.8, rc * 0.95], haut=v, arrondi=0.003), 0.003)
    f.ajouter(boite(P + v * (rc + haut_arc * 0.45), (L * 0.42, haut_arc * 0.55, rc * 0.85), arrondi=0.005, axes=(u, v, w)), 0.005)
    for sw in (1, -1):
        for su in (-1, 1):
            f.ajouter(ell(P + v * (rc + haut_arc * 0.8) + u * su * L * 0.46 + w * sw * rc * 0.62,
                          (articulaires, articulaires * 0.6, articulaires * 0.75), axes=(u, v, w)), 0.003)
    f.creuser(cylindre(P - u * L, P + u * L, canal), 0.002)
    return P, u, v, w, L


def dorsales(premiere=1, derniere=14):
    """Les 14 dorsales : corps, arc, apophyses transverses (avec la facette du tubercule de la côte), facettes de la
    tête des côtes, et l'épine : une lame plate un peu élargie à son bout (Sisson, fig. 171), dont la hauteur et la
    pente suivent Cuyer."""
    f = Forme()
    for i in range(premiere - 1, derniere):
        nom = f"T{i + 1}"
        rc = 0.0155 + 0.0004 * i
        P, u, v, w, L = vertebre(f, nom, rc)
        base = P + v * (rc + 0.014)
        tip = P + v * H_EPINES_T[i] + u * RECUL_EPINES_T[i]
        R = Repere(P, u, w, V_vers=v)          # plan du milieu : (U, V) = (u, v)
        bx, by = (base - P) @ R.U, (base - P) @ R.V
        tx, ty = (tip - P) @ R.U, (tip - P) @ R.V
        lb = L * (0.62 if i < 10 else 0.72)
        lt = L * (0.78 if i < 10 else 0.82)
        pts = [(bx - lb * 0.5, by), (bx + lb * 0.5, by), (tx + lt * 0.5, ty - 0.006), (tx + lt * 0.42, ty),
               (tx - lt * 0.42, ty), (tx - lt * 0.5, ty - 0.006)]
        f.ajouter(plaque(R, pts, 0.0032, arrondi=0.0022), 0.005)
        f.ajouter(ell(tip - v * 0.004, (lt * 0.45, 0.006, 0.0055), axes=(u, v, w)), 0.003)      # bout de l'épine épaissi
        for sw in (1, -1):
            # apophyse transverse : courte et épaisse, sa facette porte le tubercule de la côte
            dep = P + v * (rc * 0.75) + w * sw * rc * 0.55
            bout = dep + w * sw * 0.026 + v * 0.008 + u * 0.004
            f.ajouter(loft([dep, bout], [0.009, 0.0075], [0.0065, 0.0065], haut=u, arrondi=0.003), 0.004)
            # facette pour la tête de la côte (entre deux vertèbres, en avant du corps)
            f.ajouter(ell(P - u * L * 0.5 + v * 0.004 + w * sw * rc * 0.95, (0.006, 0.006, 0.004), axes=(u, v, w)), 0.002)
            if i >= 8:   # apophyses mamillaires sur les dernières dorsales
                f.ajouter(ell(P + v * (rc + 0.02) - u * L * 0.25 + w * sw * 0.014, (0.008, 0.006, 0.005), axes=(u, v, w)), 0.004)
    return f


def lombaires():
    """Les 7 lombaires : de face (Sisson, fig. 172), le corps en cœur, l'arc, l'épine et les longues apophyses
    transverses qui descendent un peu vers leur bout (le « filet » est dessous) ; de profil, un corps long, une
    épine large et les apophyses transverses en lames minces."""
    f = Forme()
    face = cartes(silhouette_fig("lombaire_face"))
    for i in range(7):
        nom = f"L{i + 1}"
        P, T, L = VERT[nom]
        u, v, w = repere_vertebre(P, T)
        rc = 0.0195
        s = rc / 110.0
        h = (1510 - 970) * s * (1.0 - 0.012 * i)
        pf = _pose_face(nom, (915, 1510), (915, 970), h)
        R = P.astype(np.float32)
        uu, vv = u.astype(np.float32), v.astype(np.float32)

        ww = w.astype(np.float32)

        def profil(Pt, R=R, uu=uu, vv=vv, ww=ww, L=L, rc=rc, h=h, i=i):
            q = Pt - R
            a, b = q @ uu, q @ vv
            corps = sd_boite2(a, b, 0.0, 0.0, L / 2, rc, 0.006)
            arc = sd_boite2(a, b, 0.0, rc + 0.01, L * 0.42, 0.014, 0.004)
            c = np.abs((Pt - R) @ ww)
            avance = 0.006 * np.clip((b - rc) / max(h - rc, 1e-3), 0, 1)       # épines un peu penchées vers l'avant
            epine = sd_boite2(a + avance, b, 0.002, rc + 0.012 + (h - rc - 0.012) / 2, L * 0.27, (h - rc - 0.012) / 2, 0.005)
            larg_t = L * (0.25 - 0.15 * np.clip((c - 0.02) / 0.075, 0, 1))     # étroites au bout
            transv = sd_boite2(a + 0.004 * np.clip((c - 0.02) / 0.075, 0, 1), b, -0.002, 0.0, larg_t, rc * 0.7, 0.003)
            artic = np.minimum(sd_boite2(a, b, -L * 0.42, rc + 0.022, 0.01, 0.008, 0.004),
                               sd_boite2(a, b, L * 0.44, rc + 0.02, 0.009, 0.007, 0.004))
            return np.minimum.reduce([corps, arc, epine, transv, artic])
        lo, hi = P - 0.2, P + 0.2
        f.ajouter(coque([extrusion(face, pf), Prim(profil, lo, hi)], k=0.003), 0.003)
        f.creuser(cylindre(P - u * L, P + u * L, 0.0085), 0.002)
    return f


def sacrum():
    """Sacrum : 4 vertèbres soudées, plat et large devant (les ailes s'appuient sur l'os du bassin), aminci vers la
    queue, d'après sa vue de dessus (Sisson, fig. 173) ; épaisseur relevée sur Cuyer ; 4 paires de trous sacrés et,
    comme chez le porc, des épines presque absentes (de petits tubercules)."""
    f = Forme()
    s0 = VERT["S_debut"]
    a, Ta = le_long(s0)
    b, Tb = le_long(s0 + L_SACRUM)
    u = n_(b - a)
    v = n_(Y - (Y @ u) * u)
    w = np.cross(u, v)
    sil = silhouette_fig("sacrum_dessus", garder=[[(800, 560), (1560, 560), (1560, 1522), (800, 1522)]], sym=(1160, "gauche"))
    s = L_SACRUM / (1522 - 612)
    R = Repere(a, u, v, V_vers=w)          # (U, V) = (le long, en travers), W = vers le bas
    pts = [((py - 612) * s, (1160 - px) * s) for px, py in sil["contour"][::2]]

    def centre(uu, vv):
        return -(-0.004 + 0.006 * np.clip(uu / L_SACRUM, 0, 1)) - 0.004 * np.clip(np.abs(vv) / 0.06, 0, 1) ** 2

    def ep(uu, vv):
        t = np.clip(uu / L_SACRUM, 0, 1)
        milieu = 0.017 - 0.008 * t
        bords = 0.009 - 0.004 * t
        r = np.clip(np.abs(vv) / 0.05, 0, 1)
        return milieu + (bords - milieu) * r ** 1.5
    f.ajouter(plaque(R, pts, 0.017, arrondi=0.003, decal=centre, epaisseurs=ep), 0.006)
    # facettes articulaires craniales (contre la 7e lombaire) et petits tubercules des épines soudées
    for sw in (1, -1):
        f.ajouter(ell(a + u * 0.008 + v * 0.016 + w * sw * 0.017, (0.01, 0.006, 0.007), axes=(u, v, w)), 0.008)
    crete = [a + u * (0.012 + k * 0.04) + v * (0.0175 - 0.0035 * k) for k in range(5)]
    f.ajouter(loft(crete, [0.006, 0.005, 0.0045, 0.004, 0.003], [0.0035, 0.0032, 0.003, 0.0028, 0.0025], haut=v,
                   arrondi=0.0015), 0.006)
    # canal de la moelle et 4 paires de trous sacrés (positions relevées sur la figure)
    f.creuser(loft([a - u * 0.01 + v * 0.002, b + u * 0.01 - v * 0.002], [0.009, 0.005], [0.006, 0.004], haut=v), 0.002)
    for (px, py), r in (((1050, 850), 28), ((1065, 1050), 18), ((1095, 1225), 13), ((1090, 1480), 14)):
        uu, vv = (py - 612) * s, (1160 - px) * s
        for sw in (1, -1):
            c = a + u * uu + w * sw * vv
            f.creuser(cylindre(c - v * 0.04, c + v * 0.04, r * s), 0.0015)
    return f


def coccygiennes():
    """Les 20 coccygiennes, le long de la queue en vrille : petites « bobines », les 5 premières avec leur arc et
    leurs apophyses transverses."""
    f = Forme()
    for i in range(N_COCC):
        P, T, L = VERT[f"Co{i + 1}"]
        u, v, w = repere_vertebre(P, T)
        r = 0.0125 - 0.0075 * i / (N_COCC - 1)
        f.ajouter(loft([P - u * L / 2, P, P + u * L / 2], [r * 1.05, r * 0.72, r * 1.05], [r * 1.0, r * 0.7, r * 1.0],
                       haut=v, arrondi=0.002), 0.002)
        if i < 5:
            f.ajouter(ell(P + v * r * 1.05, (L * 0.32, r * 0.55, r * 0.65), axes=(u, v, w)), 0.003)
            for sw in (1, -1):
                f.ajouter(ell(P + w * sw * r * 1.45, (L * 0.3, r * 0.3, r * 0.75), axes=(u, v, w)), 0.003)
            f.creuser(cylindre(P - u * L, P + u * L, r * 0.36), 0.0015)
    return f


# ================================================================ thorax
# Sternum (6 segments) relevé sur Cuyer : du manubrium, devant l'entrée de la poitrine, à l'appendice xiphoïde.
STERNUM_A = p3(-0.745, 0.535)
STERNUM_B = p3(-0.42, 0.476)
XIPHOIDE = p3(-0.33, 0.47)
_corps_cache = None


def _corps():
    global _corps_cache
    if _corps_cache is None:
        from formes import porc
        _corps_cache = porc()
    return _corps_cache


def _z_paroi(x, y, epaisseur):
    """Côté gauche : le plus grand z tel que (x, y, z) soit à « epaisseur » sous la peau."""
    zs = np.linspace(0.0, 0.5, 201, dtype=np.float32)
    Pt = np.stack([np.full_like(zs, x), np.full_like(zs, y), zs], -1)
    d = _corps().distance(Pt)
    ok = zs[d < -epaisseur]
    return float(ok.max()) if len(ok) else 0.05


def _sternebre_x(k):
    """Abscisse de l'attache du cartilage de la côte sternale k (0 = 1re) sur le sternum."""
    return STERNUM_A[0] + 0.012 + k * (STERNUM_B[0] - STERNUM_A[0] - 0.012) / 6.0


def _y_sternum(x):
    t = np.clip((x - STERNUM_A[0]) / (STERNUM_B[0] - STERNUM_A[0]), 0, 1)
    return STERNUM_A[1] + (STERNUM_B[1] - STERNUM_A[1]) * t


# Jonction os / cartilage de chaque côte (x, y), relevée sur Cuyer : les premières côtes descendent vers l'avant, les
# suivantes penchent de plus en plus vers l'arrière ; les 7 premières ont leur cartilage jusqu'au sternum, les 7
# dernières un cartilage qui rejoint celui de la côte d'avant (l'arc costal).
JONCTIONS = [(-0.665, 0.585), (-0.62, 0.565), (-0.57, 0.548), (-0.515, 0.535), (-0.46, 0.527), (-0.40, 0.522),
             (-0.34, 0.522), (-0.275, 0.527), (-0.21, 0.537), (-0.14, 0.55), (-0.07, 0.566), (-0.005, 0.585),
             (0.055, 0.607), (0.11, 0.632)]
_cotes_cache = []


def _cote(i):
    """Ligne médiane de la côte i (0 = 1re), côté gauche : (points de la partie osseuse, du cartilage)."""
    P, T, L = VERT[f"T{i + 1}"]
    u, v, w = repere_vertebre(P, T)
    tete = P - u * (L * 0.5 + DISQUE * 0.5) + v * 0.004
    xj, yj = JONCTIONS[i]
    pts = []
    for t in np.linspace(0, 1, 11):
        x = tete[0] + (xj - tete[0]) * t ** 1.1 - 0.01 * np.sin(np.pi * t) * (i > 0)
        y = tete[1] + (yj - tete[1]) * t
        pts.append([x, y])
    zs = []
    for k, (x, y) in enumerate(pts):
        t = k / 10
        if t == 0:
            z = 0.022
        else:
            zp = _z_paroi(x, y, 0.035 + 0.04 * max(0.0, 0.35 - t))
            if x < -0.48 and y > 0.56:          # sous la palette : la côte reste en dedans de l'os de l'épaule
                zp = min(zp, z_sous_palette(x, y) - 0.022)
            zarc = 0.022 + (zp - 0.022) * np.sin(min(1.0, t / 0.45) * np.pi / 2) ** 0.8
            z = min(zarc, zp)
        zs.append(z)
    zs = np.convolve(np.r_[zs[0], zs, zs[-1]], [0.25, 0.5, 0.25], "valid").tolist()
    zs[0] = 0.022
    os_pts = [p3(x, y, z) for (x, y), z in zip(pts, zs)]
    j = os_pts[-1]
    if i < 7:
        xs = _sternebre_x(i)
        fin = p3(xs, _y_sternum(xs) + 0.006, 0.026)
        cart = [j, p3((j[0] + xs) / 2 + 0.01, (j[1] + fin[1]) / 2 - 0.012, (j[2] + 0.026) / 2 + 0.03), fin]
    else:
        prev = _cotes_cache[i - 1][1]
        cible = prev[min(len(prev) - 1, 2 if i > 8 else 1)]
        cart = [j, (j + cible) / 2 + p3(0.0, -0.015, 0.01), cible + p3(0.01, 0.006, 0.004)]
    return os_pts, cart


def _cotes():
    if not _cotes_cache:
        for i in range(14):
            _cotes_cache.append(_cote(i))
    return _cotes_cache


DEMI_LARGEUR_COTES = [0.0125, 0.010, 0.0105, 0.011, 0.0112, 0.0112, 0.011, 0.0105, 0.010, 0.0095, 0.009, 0.0085, 0.008, 0.0075]


def cotes(premiere=1, derniere=14):
    """Les 14 côtes gauches : tête et tubercule contre les vertèbres, corps courbé, plus large en bas (Sisson,
    fig. 175 : la 8e) ; la 1re, courte et prismatique, à gros bout sternal (fig. 176) ; cartilages costaux."""
    f = Forme()
    for i, (os_pts, cart) in enumerate(_cotes()):
        if not premiere - 1 <= i < derniere:
            continue
        c = courbe(os_pts, n=32)
        t = np.linspace(0, 1, len(c))
        lg = DEMI_LARGEUR_COTES[i]
        if i == 0:
            a = 0.008 + (lg - 0.008) * t ** 0.8
        else:
            a = 0.0065 + (lg - 0.0065) * np.sin(np.clip(t * 1.3, 0, 1) * np.pi / 2)
        b = 0.0062 - 0.0024 * np.clip(t * 1.4, 0, 1)
        a[0], b[0] = 0.0085, 0.0078                                               # tête de la côte
        f.ajouter(loft(c, a, b, haut=(1, 0, 0), arrondi=0.0018), 0.0025)
        f.ajouter(ell(os_pts[0] + p3(0.003, 0.009, 0.016), (0.0065, 0.006, 0.006)), 0.003)   # tubercule
        cc = courbe(cart, n=12)
        ac = np.linspace(a[-1] * 0.85, 0.006, len(cc))
        f.ajouter(loft(cc, ac, np.full(len(cc), 0.0045), haut=(1, 0, 0), arrondi=0.0015), 0.0025, "cartilage")
    return f


def sternum():
    """Sternum : 6 segments, le premier (manubrium) long et aplati sur les côtés, la pointe vers l'avant ;
    cartilages entre les segments ; appendice xiphoïde (cartilage plat) en arrière."""
    f = Forme()
    xs = [STERNUM_A[0] + k * (STERNUM_B[0] - STERNUM_A[0]) / 6.0 for k in range(7)]
    y = _y_sternum
    f.ajouter(loft([p3(xs[0] - 0.02, y(xs[0]) + 0.012), p3(xs[0] + 0.02, y(xs[0]) + 0.004), p3(xs[1] - 0.006, y(xs[1]))],
                   [0.008, 0.009, 0.01], [0.013, 0.014, 0.012], haut=Y, arrondi=0.003), 0.005)
    for k in range(1, 6):
        xm = (xs[k] + xs[k + 1]) / 2
        f.ajouter(boite(p3(xm, y(xm) - 0.002), (0.022, 0.009, 0.014 + 0.002 * k), arrondi=0.006,
                        axes=(n_(p3(1, (STERNUM_B[1] - STERNUM_A[1]) / (STERNUM_B[0] - STERNUM_A[0]))), Y, Z)), 0.003)
    for k in range(1, 6):
        f.ajouter(ell(p3(xs[k], y(xs[k]) - 0.002), (0.006, 0.008, 0.013 + 0.002 * k)), 0.003, "cartilage")
    f.ajouter(ell(p3(XIPHOIDE[0], XIPHOIDE[1] - 0.004), (0.045, 0.005, 0.03)), 0.008, "cartilage")
    f.ajouter(cap(p3(xs[-1], y(xs[-1]) - 0.002), p3(XIPHOIDE[0] - 0.03, XIPHOIDE[1] - 0.003), 0.008, 0.006), 0.006)
    return f


# ================================================================ membre avant (côté gauche)
GLENE = p3(-0.692, 0.548, 0.198)          # cavité glénoïde de la palette (articulation de l'épaule)
DOS_PAL = p3(-0.625, 0.835, 0.175)       # milieu du bord dorsal de la palette (os, sans le cartilage)
HUM_TETE = p3(-0.679, 0.533, 0.193)        # centre de la tête de l'humérus
COUDE = p3(-0.566, 0.432, 0.192)         # condyle de l'humérus (coude)
CARPE = p3(-0.541, 0.236, 0.19)          # bas du radius (dessus du carpe)
BOULET_AV = p3(-0.528, 0.095, 0.19)      # boulet (canons / 1res phalanges)
PINCE_AV = p3(-0.574, 0.026, 0.19)       # bout des grands doigts, dans l'onglon


def repere_palette():
    U = n_(DOS_PAL - GLENE)
    nrm = n_(np.cross(X, U))
    if nrm[2] < 0:
        nrm = -nrm
    return Repere(GLENE, U, nrm, V_vers=-X)


def z_sous_palette(x, y):
    """z de la face profonde de la palette au point (x, y) (côté gauche) ; 9 en dehors de l'os."""
    R = repere_palette()
    W = R.W
    z = R.O[2] - (W[0] * (x - R.O[0]) + W[1] * (y - R.O[1])) / W[2]
    return z - 0.006


# Limite os / cartilage de la palette sur la figure (Sisson, fig. 183, pixels de page)
LIMITE_CARTILAGE = [(470, 990), (554, 969), (649, 897), (777, 868), (888, 862), (1015, 889), (1127, 969), (1207, 1048),
                    (1400, 1060)]


def palette():
    """Palette (omoplate) d'après Sisson (fig. 183) : lame très large, épine (l'arête) au milieu avec sa grosse
    tubérosité recourbée vers l'arrière, acromion à peine marqué, col, cavité glénoïde et tubérosité de la
    palette ; cartilage le long du bord dorsal."""
    f = Forme()
    pose = pose_palette()
    mpx = pose.s
    haut = [(470, 650), (1400, 650)]
    os_ = silhouette_fig("palette", retirer=[haut + LIMITE_CARTILAGE[::-1]])
    cart = silhouette_fig("palette", garder=[haut + LIMITE_CARTILAGE[::-1]])
    # lame : os plat (~3 mm de demi-épaisseur), plus épais vers le col et le long des bords
    zones = [([(760, 1500), (1010, 1500), (1010, 1900), (760, 1900)], 3.2),         # col
             ([(470, 1000), (560, 1000), (650, 1650), (560, 1650)], 1.35),         # bord crânial
             ([(1060, 1100), (1200, 1050), (1020, 1650), (940, 1650)], 1.6)]       # bord caudal (épais)
    f.ajouter(gonfle(cartes(os_, forme="plat", plat=0.003 / mpx, zones=zones, flou=45), pose), 0.003)
    f.ajouter(gonfle(cartes(cart, forme="plat", plat=0.0022 / mpx), pose), 0.003, "cartilage")
    # épine : crête perpendiculaire à la lame, basse vers l'acromion, haute au milieu
    ep = [pose.vers_modele(x, y) for x, y in [(808, 1606), (793, 1486), (800, 1327), (832, 1168), (808, 1008), (777, 929)]]
    ce = courbe(ep, n=16)
    t = np.linspace(0, 1, len(ce))
    h = 0.004 + 0.02 * np.sin(np.clip(t / 0.9, 0, 1) * np.pi) ** 0.8
    f.ajouter(loft([p + pose.W * hh * 0.5 for p, hh in zip(ce, h)], h * 0.5 + 0.003, np.full(len(ce), 0.0042),
                   haut=pose.W, arrondi=0.002), 0.006)
    # tubérosité de l'épine (2) : grosse bosse rugueuse recourbée vers l'arrière
    tb = pose.vers_modele(905, 1150)
    f.ajouter(ell(tb + pose.W * 0.011 - pose.V * 0.004, (0.011, 0.03, 0.0065), axes=(pose.V, pose.U, pose.W)), 0.018)
    # col, cavité glénoïde (creux tourné vers l'humérus), tubérosité de la palette (devant)
    f.ajouter(ell(GLENE + pose.U * 0.022, (0.024, 0.022, 0.016), axes=(pose.U, pose.V, pose.W)), 0.01)
    f.creuser(ell(GLENE - pose.U * 0.012, (0.016, 0.02, 0.015), axes=(pose.U, pose.V, pose.W)), 0.004)
    f.ajouter(ell(pose.vers_modele(790, 1845), (0.01, 0.009, 0.009), axes=(pose.U, pose.V, pose.W)), 0.005)
    return f


def humerus():
    """Humérus d'après Sisson (fig. 185, face externe) : tête en arrière, grosse tubérosité devant (la pointe de
    l'épaule), gouttière du biceps, petite tubérosité deltoïdienne, condyle du coude et fosse de l'olécrane."""
    f = Forme()
    sil = silhouette_fig("humerus_profil")
    pose = pose_humerus()
    f.ajouter(gonfle(cartes(sil, forme="rond", k=0.95), pose), 0.006)
    U, V, W = pose.U, pose.V, pose.W
    f.ajouter(ell(HUM_TETE + U * 0.006 - W * 0.004, (0.026, 0.025, 0.023), axes=(U, V, W)), 0.012)              # tête
    f.ajouter(ell(pose.vers_modele(455, 380) - W * 0.012, (0.016, 0.014, 0.012), axes=(U, V, W)), 0.008)        # petite tubérosité (dedans)
    c = COUDE
    f.ajouter(cap(c - W * 0.024, c + W * 0.022, 0.016), 0.008)                                                 # condyle en bobine
    for sw, r in ((1, 0.01), (-1, 0.012)):
        f.ajouter(ell(c - U * 0.012 + V * 0.014 + W * sw * 0.022, (0.016, 0.012, r * 0.8), axes=(U, V, W)), 0.008)   # épicondyles
    f.creuser(ell(c - U * 0.02 + V * 0.02, (0.016, 0.011, 0.011), axes=(U, V, W)), 0.004)                     # fosse de l'olécrane
    f.creuser(cap(pose.vers_modele(470, 360) - W * 0.002, pose.vers_modele(470, 460) - W * 0.002, 0.005), 0.003)   # gouttière du biceps
    return f


def radius():
    """Radius (devant) et cubitus (derrière, plus long, qui monte en olécrane : la pointe du coude) d'après
    Sisson (fig. 187) ; échancrure où tourne le condyle de l'humérus."""
    f = Forme()
    sil = silhouette_fig("radius_profil")
    pose = pose_radius()
    zones = [([(470, 1400), (700, 1400), (700, 1700), (470, 1700)], 0.75)]   # olécrane : en lame
    f.ajouter(gonfle(cartes(sil, forme="rond", k=1.05, zones=zones), pose), 0.006)
    return f


class _Pied:
    """Pose les os d'un pied d'après sa figure de face (Sisson) : un point (px, py) de la figure va, au-dessus du
    boulet, sur le canon (haut -> boulet), en dessous sur la ligne des grands doigts (boulet -> pince) ; px donne
    l'écart en dehors / en dedans, « prof » (m) recule le point vers l'arrière (face plantaire ou palmaire)."""

    def __init__(self, haut, boulet, pince, y_haut, y_boulet, y_pince, milieu, dehors, serre=0.85):
        self.haut, self.boulet, self.pince = haut, boulet, pince
        self.yh, self.yb, self.yp, self.mil, self.dehors, self.serre = y_haut, y_boulet, y_pince, milieu, dehors, serre
        self.D = n_(boulet - haut)                      # le long du canon, vers le bas
        self.L = Z                                       # en dehors (côté gauche du modèle)
        self.Ar = n_(np.cross(self.L, self.D))           # vers l'arrière
        if self.Ar[0] < 0:
            self.Ar = -self.Ar
        self.ech = np.linalg.norm(boulet - haut) / (y_boulet - y_haut)
        self.Dg = n_(pince - boulet)                    # le long des grands doigts
        self.ech_d = np.linalg.norm(pince - boulet) / (y_pince - y_boulet)

    def pt(self, px, py, prof=0.0):
        if py <= self.yb:
            base = self.haut + (self.boulet - self.haut) * (py - self.yh) / (self.yb - self.yh)
        else:
            base = self.boulet + self.Dg * (py - self.yb) * self.ech_d
        return base + self.L * (px - self.mil) * self.ech * self.serre * self.dehors + self.Ar * prof

    def bloc(self, f, px, py, demi_l, demi_h, demi_p, prof=0.0, k=0.003):
        """Petit os cubique (carpe, tarse) : demi-largeur et demi-hauteur en pixels de figure, demi-profondeur en m."""
        c = self.pt(px, py, prof)
        hh, ll = demi_h * self.ech, demi_l * self.ech * self.serre
        f.ajouter(ell(c, (hh * 1.12, ll * 1.12, demi_p * 1.1), axes=(self.D, self.L, self.Ar)), k)

    def long(self, f, pts_px, demi_l, demi_p, prof=0.0, k=0.003, partie="corps"):
        """Os long (métacarpien, phalange) : points de la figure, demi-largeurs (px) et demi-profondeurs (m)."""
        pts = [self.pt(px, py, prof) for px, py in pts_px]
        larg = [w * self.ech * self.serre for w in demi_l]
        f.ajouter(loft(pts, demi_p, larg, haut=self.Ar, arrondi=0.0015), k, partie)
        return pts

    def onglon(self, f, base, direction, longueur, larg, haut_):
        """Phalange distale (os de l'onglon) : en coin, large et haute à sa base, pointue au bout, plate dessous."""
        d = n_(direction)
        pts = [base, base + d * longueur * 0.5, base + d * longueur]
        f.ajouter(loft(pts, [haut_, haut_ * 0.75, haut_ * 0.3], [larg, larg * 0.85, larg * 0.35], haut=-self.Ar,
                       arrondi=0.0015), 0.002)

    def ergot(self, f, depart, cote, longueurs=(0.019, 0.012, 0.013), rayon=0.0058):
        """Petit doigt (II ou V) : 3 phalanges qui pendent vers l'arrière, derrière le boulet."""
        d = n_(self.D * 0.8 + self.Ar * 0.6)
        a = depart
        for i, L in enumerate(longueurs):
            b = a + d * L
            r = rayon * (1 - 0.18 * i)
            if i < 2:
                f.ajouter(loft([a, b], [r, r * 0.85], [r * 0.9, r * 0.8], haut=self.Ar, arrondi=0.0012), 0.0018)
            else:
                self.onglon(f, a, d, L, r * 0.85, r * 0.9)
            a = b + d * 0.002


def pied_avant():
    """Pied avant d'après Sisson (fig. 189, face avant), os par os : carpe (2 rangées : radial, intermédiaire,
    ulnaire et, derrière, l'accessoire ; puis C1 à C4), 4 métacarpiens (les 2 grands, III et IV, et les 2 petits,
    II et V, plus en arrière), les 3 phalanges de chaque grand doigt, qui descendent en biais vers l'avant jusqu'à
    l'onglon, les sésamoïdes derrière le boulet, et les 2 ergots qui pendent derrière."""
    f = Forme()
    p = geom_pied_avant()
    # carpe : rangée du haut, rangée du bas, et l'os accessoire (en arrière, en dehors)
    for px, l in ((255, 34), (330, 38), (405, 34)):
        p.bloc(f, px, 935, l, 46, 0.012)
    p.bloc(f, 440, 935, 18, 30, 0.009, prof=0.021)
    for px, l in ((200, 14), (240, 22), (295, 30), (385, 40)):
        p.bloc(f, px, 1032, l, 40, 0.011)
    # métacarpiens : grands (III, IV), petits (II, V) plus courts et plus en arrière
    for x0, x1, l in ((237, 242, 52), (365, 370, 54)):
        pts = p.long(f, [(x0, 1080), (x0 + 2, 1240), (x1, 1385)], [l, l * 0.8, l * 0.92], [0.0115, 0.0095, 0.0105])
        f.ajouter(ell(pts[-1] + p.Ar * 0.002, (0.009, l * p.ech * 0.8, 0.011), axes=(p.D, p.L, p.Ar)), 0.003)   # tête
    for x0, x1, y0, y1 in ((100, 88, 1130, 1440), (498, 506, 1150, 1440)):
        p.long(f, [(x0, y0), (x1, y1)], [20, 16], [0.0062, 0.0055], prof=0.008)
    # grands doigts III et IV : 1re et 2e phalanges, phalange distale (os de l'onglon)
    for x in (245, 372):
        p.long(f, [(x, 1402), (x + 2, 1545)], [44, 36], [0.0105, 0.0085], prof=-0.002)
        p.long(f, [(x + 2, 1550), (x + 4, 1650)], [38, 32], [0.0088, 0.0075], prof=-0.002)
        for y, r in ((1402, 0.0115), (1548, 0.0098), (1654, 0.0085)):
            f.ajouter(ell(p.pt(x + 2, y, -0.002), (0.007, r, r * 0.95), axes=(p.Dg, p.L, p.Ar)), 0.003)
        b = p.pt(x + 4, 1658, -0.002)
        p.onglon(f, b, p.Dg, 0.040, 38 * p.ech * p.serre, 0.0105)
        for dz in (-12, 12):                                              # sésamoïdes, derrière le boulet
            f.ajouter(ell(p.pt(x + dz, 1395, 0.016), (0.008, 0.005, 0.0055), axes=(p.D, p.L, p.Ar)), 0.002)
    # ergots (doigts II et V)
    for x, y in ((88, 1440), (506, 1440)):
        p.ergot(f, p.pt(x, y, 0.007), 0)
    return f


# ================================================================ membre arrière (côté gauche)
ACETABULE = p3(0.66, 0.74, 0.105)        # cavité de la hanche (centre de la tête du fémur)
TUBER_ISCHII = p3(0.865, 0.765, 0.062)   # pointe de la fesse
TUBER_COXAE = p3(0.436, 0.786, 0.13)     # pointe de la hanche (calcul : position donnée par la figure, pour mémoire)
GRASSET = p3(0.606, 0.524, 0.168)        # condyles du fémur (articulation du grasset)
PLATEAU_TIBIA = p3(0.613, 0.49, 0.17)
JARRET = p3(0.68, 0.272, 0.185)          # bas du tibia (articulation du jarret)
CALCANEUM = p3(0.715, 0.33, 0.188)       # pointe du jarret (tubérosité du calcanéum)
BOULET_AR = p3(0.672, 0.095, 0.19)
PINCE_AR = p3(0.61, 0.02, 0.19)


def _normale_coxal():
    n = np.cross(TUBER_ISCHII - ACETABULE, TUBER_COXAE - ACETABULE)
    n = n_(n)
    return n if n[2] > 0 else -n


def pose_coxal():
    return Placement((944, 1533), (1465, 1388), ACETABULE, TUBER_ISCHII, normale=_normale_coxal())


def coxal():
    """Os coxal gauche d'après Sisson (fig. 191, face externe) : ilium long et étroit, presque dans le plan du corps,
    aile avec la pointe de la hanche (en bas) et la tubérosité sacrée (en haut), épine sciatique, cotyle (cavité
    de la hanche), ischium et pointe de la fesse ; plancher du bassin (pubis et ischium) percé du grand trou
    obturé, jusqu'à la symphyse au milieu."""
    f = Forme()
    pose = pose_coxal()
    mpx = pose.s
    sil = silhouette_fig("coxal_profil")
    zones = [([(780, 1350), (1080, 1350), (1080, 1600), (780, 1600)], 2.3),       # pourtour du cotyle
             ([(560, 1330), (800, 1330), (800, 1480), (560, 1480)], 1.8),         # col de l'ilium
             ([(1380, 1330), (1500, 1330), (1500, 1520), (1380, 1520)], 1.9)]     # pointe de la fesse
    W = pose.W

    def decal(u, v):
        # l'aile de l'ilium (devant le cotyle) se rapproche du sacrum vers le haut
        return -0.03 * np.clip(-u / 0.2, 0, 1) * np.clip(v / 0.1, 0, 1)
    f.ajouter(gonfle(cartes(sil, forme="plat", plat=0.0045 / mpx, zones=zones, flou=40), pose, decal=decal), 0.004)
    # pointe de la hanche et pointe de la fesse : bosses rugueuses
    f.ajouter(ell(pose.vers_modele(370, 1465), (0.012, 0.022, 0.009), axes=(pose.U, pose.V, W)), 0.014)
    f.ajouter(ell(pose.vers_modele(1435, 1420) + W * 0.003, (0.013, 0.024, 0.011), axes=(pose.U, pose.V, W)), 0.014)
    # cotyle : coupe épaisse autour de la tête du fémur, ouverte en dehors et en bas
    tf = ACETABULE
    f.ajouter(ell(tf + p3(0.0, 0.006, -0.012), (0.034, 0.032, 0.03)), 0.01)
    f.creuser(ell(tf, (0.026, 0.026, 0.025)), 0.003)
    f.creuser(ell(tf + p3(0.0, -0.022, 0.026), (0.026, 0.024, 0.022)), 0.005)
    # plancher du bassin : pubis (devant) et ischium (derrière), de part et d'autre du grand trou obturé ; il part
    # du bord inférieur de l'os (sous le cotyle et le long de l'ischium) et rejoint la symphyse, au milieu (z = 0)
    bord = [pose.vers_modele(x, y) - W * 0.002 for x, y in ((870, 1570), (985, 1598), (1110, 1590), (1255, 1560), (1395, 1505))]
    milieu = [p3(q[0] + dx, q[1] - 0.009, 0.003) for q, dx in zip(bord, (0.035, 0.0, 0.0, 0.0, -0.045))]
    pts = np.array(bord + milieu)
    O = pts.mean(0)
    _, _, vt = np.linalg.svd(pts - O)
    nrm = vt[2] if vt[2][1] > 0 else -vt[2]                    # normale vers le haut
    R = Repere(O, X, nrm, V_vers=Z)
    uv = lambda q: (float((q - O) @ R.U), float((q - O) @ R.V))
    # bord avant du pubis creusé (de la hanche à la symphyse), arcade ischiatique creusée à l'arrière
    av = (np.array(uv(bord[0])) + np.array(uv(milieu[0]))) / 2 + (0.016, 0.0)
    ar = (np.array(uv(bord[-1])) + np.array(uv(milieu[-1]))) / 2 + (-0.03, 0.0)
    contour_pl = [uv(q) for q in bord] + [tuple(ar)] + [uv(q) for q in milieu[::-1]] + [tuple(av)]
    f.ajouter(plaque(R, contour_pl, 0.0072, arrondi=0.0035), 0.01)
    trou = (bord[1] * 0.45 + milieu[1] * 0.55 + bord[2] * 0.45 + milieu[2] * 0.55) / 2
    f.creuser(ell(trou, (0.047, 0.02, 0.027), axes=(R.U, R.W, R.V)), 0.005)               # trou obturé
    f.ajouter(loft([milieu[0] + X * 0.01, milieu[-1]], [0.0085, 0.0085], [0.006, 0.006], haut=nrm, arrondi=0.003), 0.006)   # symphyse
    return f


def femur():
    """Fémur d'après Sisson (fig. 193, face avant) : tête sur un col net (dans le cotyle), grand trochanter massif,
    corps large, trochlée (gorge de la rotule) devant et deux condyles derrière."""
    f = Forme()
    sil = silhouette_fig("femur_face")
    pose = pose_femur()
    f.ajouter(gonfle(cartes(sil, forme="rond", k=0.95), pose), 0.006)
    U, V, W = pose.U, pose.V, pose.W
    f.ajouter(ell(ACETABULE, (0.023, 0.023, 0.022), axes=(U, V, W)), 0.01)                       # tête
    for sz, r in ((-1, 0.014), (1, 0.013)):                                                      # condyles (derrière)
        f.ajouter(ell(GRASSET + W * 0.008 + Z * sz * 0.016, (0.022, 0.02, r)), 0.007)
    for sz in (-1, 1):                                                                           # lèvres de la trochlée (devant)
        f.ajouter(ell(GRASSET - W * 0.022 - U * 0.012 + Z * sz * 0.011, (0.026, 0.009, 0.007), axes=(U, V, W)), 0.006)
    f.creuser(ell(GRASSET + W * 0.016 - U * 0.004, (0.018, 0.012, 0.006), axes=(U, V, W)), 0.003)   # fosse intercondylienne
    return f


def rotule():
    """Rotule : longue et étroite chez le porc (Sisson), large en haut (sa base), pointue en bas (son sommet),
    posée dans la gorge de la trochlée du fémur."""
    f = Forme()
    U = n_(GRASSET - ACETABULE)
    devant = n_(np.cross(U, Z))
    if devant[0] > 0:
        devant = -devant
    c = GRASSET - U * 0.012 + devant * 0.034
    pts = [c - U * 0.024, c - U * 0.006, c + U * 0.012, c + U * 0.026]
    f.ajouter(loft(pts, [0.0085, 0.0105, 0.009, 0.004], [0.012, 0.0125, 0.0095, 0.004], haut=devant, arrondi=0.003), 0.004)
    return f


def tibia():
    """Tibia et péroné d'après Sisson (fig. 195, face avant) : plateau à deux condyles, tubérosité et crête devant,
    péroné en dehors sur toute la longueur, séparé du tibia par l'espace interosseux ; malléoles en bas."""
    f = Forme()
    sil = silhouette_fig("tibia_face")
    sil["trous"] = list(sil["trous"]) + [np.array(t) for t in _espace_interosseux()]
    pose = pose_tibia()
    f.ajouter(gonfle(cartes(sil, forme="rond", k=0.85), pose), 0.004)
    U = pose.U
    devant = n_(np.cross(U, Z))
    if devant[0] > 0:
        devant = -devant
    f.ajouter(ell(PLATEAU_TIBIA - U * 0.004 - devant * 0.004, (0.012, 0.026, 0.03), axes=(U, devant, Z)), 0.008)   # plateau
    f.ajouter(ell(PLATEAU_TIBIA + U * 0.03 + devant * 0.018, (0.03, 0.009, 0.01), axes=(U, devant, Z)), 0.008)     # tubérosité, crête
    return f


def _espace_interosseux():
    """L'espace entre tibia et péroné (fig. 195), ouvert sur presque toute la longueur."""
    return [[(392, 950), (412, 940), (430, 1150), (440, 1400), (440, 1620), (425, 1690), (405, 1660), (396, 1400),
             (390, 1150)]]


def pied_arriere():
    """Pied arrière d'après Sisson (fig. 197, pied droit vu de face, reflété pour le côté gauche), os par os :
    tarse (l'astragale et sa poulie sous le tibia, le calcanéum qui monte derrière jusqu'à la pointe du jarret,
    l'os central et la rangée du bas, T1 à T4), 4 métatarsiens (III et IV grands, II et V petits et en arrière), les
    3 phalanges des grands doigts jusqu'aux onglons, les sésamoïdes et les 2 ergots."""
    f = Forme()
    p = geom_pied_arriere()
    # astragale : poulie à deux lèvres sous le tibia, puis son corps
    for px in (318, 392):
        f.ajouter(ell(p.pt(px, 915, -0.002), (0.012, 0.009, 0.016), axes=(p.D, p.L, p.Ar)), 0.003)
    p.bloc(f, 355, 965, 52, 34, 0.014)
    # calcanéum : en dehors et en arrière de l'astragale, monte jusqu'à sa tubérosité (la pointe du jarret)
    base = p.pt(290, 1045, 0.012)
    milieu = (base + CALCANEUM) / 2 + p.Ar * 0.004
    f.ajouter(loft([base, milieu, CALCANEUM - p.D * 0.004], [0.013, 0.0105, 0.012], [0.0095, 0.0075, 0.0095],
                   haut=p.Ar, arrondi=0.003), 0.004)
    f.ajouter(ell(CALCANEUM, (0.011, 0.012, 0.011)), 0.005)                                     # tubérosité
    # os central, puis la rangée du bas (T4 en dehors, le plus gros ; T3 ; T1 et T2 en dedans, petits)
    p.bloc(f, 380, 1028, 46, 26, 0.012)
    for px, l in ((290, 40), (378, 36), (455, 16), (486, 12)):
        p.bloc(f, px, 1098, l, 30, 0.011 if l > 20 else 0.007)
    # métatarsiens
    for x0, x1, l in ((300, 300, 46), (388, 392, 46)):
        pts = p.long(f, [(x0, 1132), (x0, 1300), (x1, 1468)], [l, l * 0.8, l * 0.92], [0.011, 0.0092, 0.0102])
        f.ajouter(ell(pts[-1] + p.Ar * 0.002, (0.009, l * p.ech * 0.8, 0.0105), axes=(p.D, p.L, p.Ar)), 0.003)
    for x0, x1, y0, y1 in ((215, 205, 1175, 1450), (488, 500, 1185, 1450)):
        p.long(f, [(x0, y0), (x1, y1)], [17, 14], [0.0058, 0.0052], prof=0.008)
    # grands doigts III et IV
    for x in (300, 392):
        p.long(f, [(x, 1482), (x - 2, 1630)], [40, 33], [0.0102, 0.0082], prof=-0.002)
        p.long(f, [(x - 2, 1636), (x - 4, 1728)], [35, 30], [0.0085, 0.0072], prof=-0.002)
        for y, r in ((1482, 0.011), (1633, 0.0095), (1731, 0.0082)):
            f.ajouter(ell(p.pt(x - 2, y, -0.002), (0.007, r, r * 0.95), axes=(p.Dg, p.L, p.Ar)), 0.003)
        b = p.pt(x - 4, 1735, -0.002)
        p.onglon(f, b, p.Dg, 0.038, 35 * p.ech * p.serre, 0.0102)
        for dz in (-12, 12):
            f.ajouter(ell(p.pt(x + dz, 1476, 0.016), (0.008, 0.005, 0.0055), axes=(p.D, p.L, p.Ar)), 0.002)
    for x in (205, 500):
        p.ergot(f, p.pt(x, 1450, 0.006), 0)
    return f


# ================================================================ tête
# Crâne : profil (Sisson, fig. 177) et dessus (fig. 179) ; mâchoire : profil et dessus (fig. 181).
# Calage dans la tête du modèle : bout de l'os du groin et sommet de la crête de la nuque.
R_CRANE = p3(-1.362, 0.616)              # bout de l'os du groin (os rostral)
N_CRANE = p3(-1.007, 0.932)              # sommet de la crête de la nuque
# zone de la mâchoire sur la figure de profil (pixels de page) : sous la ligne des dents et l'arcade zygomatique
MANDIBULE_PROFIL = [(30, 1700), (200, 1690), (330, 1660), (520, 1606), (800, 1560), (1021, 1500), (1063, 1400),
                    (1173, 1370), (1311, 1315), (1394, 1248), (1440, 1170), (1475, 1170), (1475, 1850), (30, 1850)]
# ce qui n'est pas de l'os sur la figure de profil : le papier au-dessus du chanfrein et sous les incisives
HORS_CRANE = [[(40, 590), (1080, 590), (1100, 625), (160, 1455), (40, 1455)], [(40, 1745), (330, 1745), (330, 1835), (40, 1835)]]


def pose_crane_profil():
    return Placement((45, 1640), (1110, 640), R_CRANE, N_CRANE, normale=Z)


def _skull_dessus_pose():
    d = n_(N_CRANE - R_CRANE)
    n = np.array([-d[1], d[0], 0.0])
    return Placement((838, 2090), (838, 650), R_CRANE, N_CRANE, normale=n)


def _arrondi_crane(pp, cp, pd, cd, p=3.0):
    """Arrondit la section du crâne : pour chaque abscisse le long de l'axe, une super-ellipse de la hauteur du
    profil et de la largeur de la vue de dessus."""
    def etendue(c, pose, axe_v):
        sd, (ox, oy) = c["sd"], c["origine"]
        yy, xx = np.nonzero(sd < 0)
        pts = np.array([pose.vers_modele(ox + x, oy + y) for x, y in zip(xx[::2], yy[::2])])
        q = pts - pp.A
        return q @ pp.U, q @ axe_v
    dirv = pp.V
    u1, v1 = etendue(cp, pp, dirv)
    u2, w2 = etendue(cd, pd, Z)
    pas = 0.002
    u0 = min(u1.min(), u2.min()) - 0.01
    nb = int((max(u1.max(), u2.max()) + 0.01 - u0) / pas) + 1
    k1 = np.clip(((u1 - u0) / pas).astype(int), 0, nb - 1)
    k2 = np.clip(((u2 - u0) / pas).astype(int), 0, nb - 1)
    lo, hi, lw = np.full(nb, np.inf), np.full(nb, -np.inf), np.zeros(nb)
    np.minimum.at(lo, k1, v1); np.maximum.at(hi, k1, v1); np.maximum.at(lw, k2, np.abs(w2))
    idx = np.arange(nb)
    ok = np.isfinite(lo)
    lo = np.interp(idx, idx[ok], lo[ok]).astype(np.float32)
    hi = np.interp(idx, idx[ok], hi[ok]).astype(np.float32)
    lw = np.maximum(lw, 0.01).astype(np.float32)
    A32, U32, V32 = pp.A.astype(np.float32), pp.U.astype(np.float32), dirv.astype(np.float32)

    def f(P):
        q = P - A32
        u, v = q @ U32, q @ V32
        i = np.clip((u - u0) / pas, 0, nb - 1).astype(np.int64)
        c = (lo[i] + hi[i]) / 2
        a = np.maximum((hi[i] - lo[i]) / 2, 0.005)
        # museau plus étroit en haut (os du nez) qu'au niveau des dents
        b = lw[i] * 1.08 * (1.0 - 0.28 * np.clip((v - c) / a, 0, 1))
        r = (np.abs(v - c) / a) ** p + (np.abs(P[..., 2]) / b) ** p
        return (r ** (1.0 / p) - 1.0) * np.minimum(a, b)
    return Prim(f, (-9, -9, -9), (9, 9, 9))


def crane():
    """Crâne de porc d'après Sisson : profil (fig. 177) et dessus (fig. 179) croisés, section arrondie ; long museau
    terminé par l'os du groin, chanfrein droit, haute crête de la nuque, orbite ouverte en arrière, grande fosse
    temporale sous l'arcade zygomatique, trou sous-orbitaire, condyles de l'occipital ; mâchoire (profil et
    dessus, fig. 181) ; dents : 3 incisives, la canine (« défense »), 4 prémolaires et 3 molaires de chaque côté,
    en haut et en bas."""
    f = Forme()
    pp = pose_crane_profil()
    pd = _skull_dessus_pose()
    profil = silhouette_fig("crane_profil", retirer=HORS_CRANE)
    cran_p = silhouette_fig("crane_profil", retirer=HORS_CRANE + [MANDIBULE_PROFIL])
    mand_p = silhouette_fig("crane_profil", retirer=HORS_CRANE, garder=[MANDIBULE_PROFIL])
    dessus = silhouette_fig("crane_dessus", sym=(838, "gauche"))
    cp, cd = cartes(cran_p), cartes(dessus)
    # 3e vue : de derrière (fig. 182) ; elle limite la largeur du crâne selon la hauteur (crête de la nuque étroite en
    # haut, conduits des oreilles, arcades zygomatiques au plus large)
    arr = silhouette_fig("crane_arriere", sym=(950, "gauche"))
    tete = coque([extrusion(cp, pp), extrusion(cd, pd), extrusion(cartes(arr), _pose_crane_arriere(pp), epais=0.75),
                  _arrondi_crane(pp, cp, pd, cd)], k=0.006)
    f.ajouter(tete, 0.004)
    U, V = pp.U, pp.V
    # fosse temporale (sur le côté de la boîte crânienne, au-dessus de l'arcade zygomatique) et orbite : creux
    # arrondis, à la profondeur relevée sur la vue de dessus (la boîte crânienne est bien plus étroite que les arcades)
    for (px, py), (ru, rv, rz), plus in (((1165, 895), (0.046, 0.07, 0.036), 0.012), ((965, 1092), (0.024, 0.034, 0.03), 0.009)):
        c = pp.vers_modele(px, py)
        zs = _z_surface(tete, c[0], c[1])
        for sz in (1, -1):
            f.creuser(ell(p3(c[0], c[1], sz * (zs + plus)), (ru, rv, rz), axes=(U, V, Z)), 0.008)
    # trou sous-orbitaire et condyles de l'occipital
    so = pp.vers_modele(621, 1422)
    zso = _z_surface(tete, so[0], so[1])
    oc = pp.vers_modele(1470, 1110)
    for sz in (1, -1):
        f.creuser(ell(p3(so[0], so[1], sz * zso), (0.009, 0.007, 0.012)), 0.002)
        f.ajouter(ell(p3(oc[0], oc[1], sz * 0.022), (0.012, 0.016, 0.011)), 0.004)
    # mâchoire : profil et vue de dessus
    pi = pp.vers_modele(180, 1715)            # bout des incisives du bas
    pc = pp.vers_modele(1380, 1180)           # condyle de la mâchoire
    dm = n_(pc - pi)
    nm = np.array([-dm[1], dm[0], 0.0])
    pmd = Placement((513, 1850), (513, 735), pi, pc, normale=nm)
    mand_d = silhouette_fig("mandibule_dessus", sym=(513, "gauche"))
    mand = _mandibule(pp, cartes(mand_p), mand_d, pmd, pi, dm)
    for sz in (1, -1):        # condyles de la mâchoire, en travers, et apophyses coronoïdes
        f.ajouter(ell(pc + Z * sz * 0.062 - Y * 0.004, (0.011, 0.008, 0.017)), 0.004)
    f.ajouter(mand, 0.003)
    _dents(f, pp, tete, mand)
    return f


def _pose_crane_arriere(pp):
    """Vue de derrière (fig. 182) : le trou occipital (entre les condyles) et le haut de la crête de la nuque, sur
    la verticale du crâne ; la vue regarde le long du palais (relevé sur le profil)."""
    d = n_(pp.vers_modele(1021, 1449) - pp.vers_modele(400, 1641))       # le long du palais
    haut = n_(np.array([-d[1], d[0], 0.0]))
    A = pp.vers_modele(1470, 1110)
    h = float((N_CRANE - A) @ haut)
    return Placement((950, 1130), (950, 610), A, A + haut * h, normale=d)


def _mandibule(pp, cprof, sil_d, pmd, pi, dm):
    """Mâchoire : une plaque courbe. Son contour est celui du profil (fig. 177) ; sa place en largeur et son
    épaisseur suivent les deux branches du « V » vu de dessus (fig. 181) : épaisse devant (le corps, qui porte les
    dents), mince en arrière (la branche montante, jusqu'au condyle) ; bords arrondis."""
    pts = np.asarray(sil_d["contour"], np.int32)
    x0, y0 = pts.min(0)
    x1, y1 = pts.max(0)
    m = np.zeros((y1 - y0 + 1, x1 - x0 + 1), np.uint8)
    cv2.fillPoly(m, [pts - [x0, y0]], 1)
    for t in sil_d.get("trous", []):
        cv2.fillPoly(m, [np.asarray(t, np.int32) - [x0, y0]], 0)
    U_m, ZC, HW = [], [], []
    for yy in range(int(y0), int(y1) + 1, 3):
        xs = np.nonzero(m[yy - y0])[0] + x0
        if len(xs) < 2:
            continue
        P = np.array([pmd.vers_modele(x, yy) for x in xs[::2]])
        zz = np.abs(P[:, 2])
        U_m.append(float(((P - pi) @ dm).mean()))
        ZC.append(float((zz.min() + zz.max()) / 2))
        HW.append(float((zz.max() - zz.min()) / 2))
    o = np.argsort(U_m)
    U_m, ZC, HW = (np.asarray(a, np.float32)[o] for a in (U_m, ZC, HW))
    # vue de dessus, la branche montante paraît aussi large que son condyle : sa plaque, elle, est mince
    u_dents = float((pp.vers_modele(1021, 1500) - pi) @ dm) + 0.015
    HW = np.minimum(HW, np.where(U_m < u_dents, 0.013, 0.0045)).astype(np.float32)
    sd, (ox, oy) = cprof["sd"], cprof["origine"]
    s = pp.s
    pi32, dm32 = pi.astype(np.float32), dm.astype(np.float32)

    def f(P):
        u, v, w = pp.local(P)
        px, py = pp.vers_planche(u, v)
        d2 = _bilineaire(sd, px - ox, py - oy, 60.0) * s
        um = (P - pi32) @ dm32
        zc, hw = np.interp(um, U_m, ZC), np.interp(um, U_m, HW)
        q = np.clip(np.maximum(-d2, 0) / 0.008, 0, 1)
        dw = np.abs(np.abs(w) - zc) - hw * np.sqrt(q * (2 - q))
        dehors = np.sqrt(np.maximum(d2, 0) ** 2 + np.maximum(dw, 0) ** 2)
        return np.minimum(np.maximum(d2, dw), 0) + dehors
    h, w = sd.shape
    coins = np.array([pp.vers_modele(ox + a, oy + b) for a in (0, w) for b in (0, h)])
    zmax = float((ZC + HW).max()) + 0.01
    lo = coins.min(0) - 0.01
    hi = coins.max(0) + 0.01
    lo[2], hi[2] = -zmax, zmax
    return Prim(f, lo, hi)


def _z_surface(prim, x, y, zmax=0.2):
    """Côté gauche : le z de la surface d'une forme au point (x, y) (le plus grand z encore dedans)."""
    zs = np.linspace(0.0, zmax, 801, dtype=np.float32)
    P = np.stack([np.full_like(zs, x), np.full_like(zs, y), zs], -1)
    d = prim.f(P)
    ok = zs[d < 0]
    return float(ok.max()) if len(ok) else 0.03


def _dents(f, pp, tete, mand):
    """Dents (partie « dent ») : 4 prémolaires et 3 molaires le long des rangées relevées sur le profil, posées à
    fleur de l'os (elles en dépassent de 1,5 mm) ; défenses (canines) et incisives."""
    occl = [(470, 1625), (700, 1575), (900, 1525), (1021, 1488)]
    pts = [pp.vers_modele(x, y) for x, y in occl]
    c = courbe(pts, n=60)
    L = np.r_[0, np.cumsum(np.linalg.norm(np.diff(c, axis=0), axis=1))]
    tailles = [0.012, 0.014, 0.016, 0.018, 0.021, 0.025, 0.032]           # P1 à P4, M1 à M3
    tot = sum(tailles)
    s = 0.0
    for j, t in enumerate(tailles):
        sm = (s + t / 2) / tot * L[-1]
        i = int(np.clip(np.searchsorted(L, sm), 1, len(c) - 1))
        P, T = c[i], n_(c[i] - c[i - 1])
        Nn = np.cross(Z, T)
        hl = t / tot * L[-1] * 0.44
        demi = 0.0075 + 0.001 * j
        for forme, signe in ((tete, 1), (mand, -1)):
            q = P + Nn * signe * 0.009
            zs = _z_surface(forme, q[0], q[1])
            for sz in (1, -1):
                f.ajouter(boite(p3(q[0], q[1], sz * (zs - demi + 0.0015)), (hl, 0.009, demi), arrondi=0.003,
                                axes=(T, Nn, Z)), 0.0015, "dent")
        s += t
    # canines (défenses) : en haut vers le bas et le dehors, en bas vers le haut et l'arrière
    h = pp.vers_modele(395, 1640)
    b = pp.vers_modele(375, 1700)
    zh, zb = _z_surface(tete, h[0], h[1]), _z_surface(mand, b[0], b[1])
    for sz in (1, -1):
        f.ajouter(cap(p3(h[0], h[1] + 0.012, sz * (zh - 0.004)), p3(h[0] + 0.006, h[1] - 0.026, sz * (zh + 0.004)), 0.0075, 0.0025),
                  0.002, "dent")
        f.ajouter(cap(p3(b[0] - 0.006, b[1] - 0.012, sz * (zb - 0.004)), p3(b[0] + 0.008, b[1] + 0.03, sz * (zb + 0.006)), 0.007, 0.0025),
                  0.002, "dent")
        # incisives : 3 en haut, 3 en bas (celles du bas couchées vers l'avant)
        for k in range(3):
            ih = pp.vers_modele(120 + 45 * k, 1700)
            f.ajouter(ell(p3(ih[0], ih[1], sz * (0.008 + 0.009 * k)), (0.005, 0.009, 0.004)), 0.0015, "dent")
            ib = pp.vers_modele(190 + 45 * k, 1722)
            f.ajouter(ell(p3(ib[0], ib[1], sz * (0.007 + 0.008 * k)), (0.011, 0.004, 0.0035), rot=(0, 0, -15)), 0.0015, "dent")


# ================================================================ calages (figure de Sisson -> modèle)
# Un point d'une figure se pose dans le modèle par le même calage que son os : les repères nommés de la page
# atelier (outils/atelier_porc.py) tombent ainsi exactement sur la forme.
def pose_palette():
    return Placement((880, 1860), (888, 865), GLENE, DOS_PAL, normale=repere_palette().W)


def pose_humerus():
    return Placement((650, 468), (502, 1178), HUM_TETE, COUDE, normale=Z)


def pose_radius():
    return Placement((415, 1752), (515, 2455), COUDE, CARPE, normale=Z)


def pose_femur():
    return Placement((493, 880), (403, 1890), ACETABULE, GRASSET, normale=-X, miroir=True)


def pose_tibia():
    return Placement((542, 830), (556, 1785), PLATEAU_TIBIA, JARRET, normale=-X, miroir=True)


def geom_pied_avant():
    return _Pied(CARPE, BOULET_AV, PINCE_AV, 880, 1400, 1790, 300, 1)


def geom_pied_arriere():
    return _Pied(JARRET, BOULET_AR, PINCE_AR, 895, 1480, 1850, 345, -1)


# ================================================================ liste des os du porc
OS_PORC = [
    ("crane", crane, False, 18000, 0.0025), ("cervicales", cervicales, False, 12000, 0.002),
    ("dorsales", dorsales, False, 14000, 0.0022), ("cotes", cotes, True, 12000, 0.0022),
    ("sternum", sternum, False, 2500, 0.002), ("lombaires", lombaires, False, 10000, 0.002),
    ("sacrum", sacrum, False, 4000, 0.002), ("coccygiennes", coccygiennes, False, 4500, 0.0018),
    ("palette", palette, True, 7000, 0.002), ("humerus", humerus, True, 4500, 0.002),
    ("radius", radius, True, 4500, 0.002), ("pied-avant", pied_avant, True, 6500, 0.0016),
    ("coxal", coxal, True, 9000, 0.0022), ("femur", femur, True, 4500, 0.002), ("rotule", rotule, True, 700, 0.0016),
    ("tibia", tibia, True, 4500, 0.002), ("pied-arriere", pied_arriere, True, 7000, 0.0016),
]

REPERES = {"glene": GLENE, "dos_palette": DOS_PAL, "coude": COUDE, "carpe": CARPE, "boulet_av": BOULET_AV,
           "acetabule": ACETABULE, "pointe_fesse": TUBER_ISCHII, "grasset": GRASSET, "jarret": JARRET,
           "calcaneum": CALCANEUM, "boulet_ar": BOULET_AR}
