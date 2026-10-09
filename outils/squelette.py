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

from sdf import (Forme, Placement, Prim, Repere, boite, cap, cartes_silhouette, courbe, cylindre, ell, loft, n_, plaque, relief,
                 silhouette, tore, volume_profil)
from planches_os import OS as OS_PLANCHES, os_planche

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


# Cou d'après la planche 3 : il part des condyles de l'occipital (derrière le crâne) en descendant en
# pente douce, puis se redresse à l'entrée de la poitrine pour rejoindre la 1re dorsale.
NUQUE = courbe([(-1.136, 1.272, 0), (-1.06, 1.215, 0), (-0.975, 1.163, 0), (-0.89, 1.122, 0), (-0.8, 1.093, 0),
                (-0.725, 1.083, 0), (-0.672, 1.09, 0)], n=200)
_long_nuque = np.r_[0, np.cumsum(np.linalg.norm(np.diff(NUQUE, axis=0), axis=1))]


def _positions():
    """Centre, tangente et longueur de chaque vertèbre, de l'atlas à la dernière coccygienne.
    Les cervicales sont réparties sur la courbe du cou (longueurs à l'échelle) ; les dorsales et la suite
    sur la ligne vertébrale."""
    out = {}
    k = (_long_nuque[-1] - 0.5 * DISQUE) / (sum(L_CERV) + 7 * DISQUE)
    s = 0.0
    for i, L0 in enumerate(L_CERV):
        L = L0 * k
        sc = s + L / 2
        j = int(np.clip(np.searchsorted(_long_nuque, sc) - 1, 0, len(NUQUE) - 2))
        t = (sc - _long_nuque[j]) / (_long_nuque[j + 1] - _long_nuque[j])
        out[f"C{i + 1}"] = (NUQUE[j] * (1 - t) + NUQUE[j + 1] * t, n_(NUQUE[j + 1] - NUQUE[j]), L)
        s += L + DISQUE * k
    s = sum(L_CERV) + 7 * DISQUE
    for nom, longueurs in (("T", L_DORS), ("L", L_LOMB)):
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


# ---------------------------------------------------------------- colonne d'après les planches
# Échelles : planche 3 = S_PL3 m/px (celle du membre avant) ; lombaires et sacrum calés sur les 6 corps de
# lombaires du modèle (S_LOMB) ; thorax du modèle plus court que celui de la planche : les épines y sont
# rapprochées (KX_THORAX) sans changer leur hauteur. Planche 13, fig. 57 (vue de dessus) : S_57 m/px.
S_PL3 = 0.00094
S_LOMB = 0.000898
KX_THORAX = 0.8
S_57 = 0.0018
R_SAG = Repere(np.zeros(3), (1, 0, 0), (0, 0, 1), V_vers=(0, 1, 0))     # plan du milieu : (u, v) = (x, y)


def _lisse(t):
    t = np.clip(t, 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _base_dorsale(i):
    """Pied de l'épine de la dorsale i (0 = T1) dans le modèle : sur l'arc vertébral."""
    P, T, L = VERT[f"T{i + 1}"]
    u, v, w = repere_vertebre(P, T)
    rc = 0.024 + 0.0008 * i
    return P + v * (rc + 0.024 * 0.8)


def _vers_modele_T(i, px, py):
    """Point de la planche 3 -> modèle (x, y), pour l'épine de la dorsale i, ancrée à son pied."""
    from planches_os import BASES_T
    bx, by = BASES_T[f"T{i + 1}"]
    B = _base_dorsale(i)
    return np.array([B[0] + KX_THORAX * S_PL3 * (px - bx), B[1] + S_PL3 * (by - py)])


def _vers_modele_L(nom, px, py):
    """Point de la planche 3 -> modèle (x, y), pour la lombaire « nom », ancrée au centre de son corps."""
    from planches_os import CORPS_L
    cx, cy = CORPS_L[nom]
    P = VERT[nom][0]
    return np.array([P[0] + S_LOMB * (px - cx), P[1] + S_LOMB * (cy - py)])


def _epines_dorsales():
    """Bouts des épines des dorsales dans le modèle (x, y) : pour les muscles (basses côtes, entrecôtes)."""
    from planches_os import EPINES_T
    out = []
    for i in range(13):
        nom = f"T{i + 1}"
        if nom in EPINES_T:
            out.append(tuple(float(c) for c in _vers_modele_T(i, *EPINES_T[nom][0])))
        else:   # T12, T13 : milieu du bord supérieur de l'épine rectangulaire
            c = np.asarray(OS_PLANCHES[f"epine_{nom}"]["ajouter"][0], float)
            haut = c[np.argsort(c[:, 1])[:2]].mean(0)
            out.append(tuple(float(v) for v in _vers_modele_T(i, *haut)))
    return out


EPINES_DORS = _epines_dorsales()


def _plaque_sagittale(contour_px, vers, e, bout=None, e_bout=0.0, r_bout=0.025, haut=None, e_haut=0.0, arrondi=0.0025):
    """Os plat dans le plan du milieu d'après un contour de planche (vers : pixel -> modèle (x, y)).
    Épaississements : autour du point « bout » (tubérosité) ou le long du bord supérieur (y > haut)."""
    pts = np.array([vers(x, y) for x, y in contour_px])

    def ep(u, v):
        out = np.full(np.shape(u), e, np.float32)
        if bout is not None:
            dd = np.sqrt((u - bout[0]) ** 2 + (v - bout[1]) ** 2)
            out = out + e_bout * (1 - _lisse(dd / r_bout))
        if haut is not None:
            out = out + e_haut * _lisse((v - haut) / 0.016)
        return out
    return plaque(R_SAG, pts, e, arrondi=arrondi, epaisseurs=ep)


def dorsales():
    """Les 13 dorsales : corps courts, arc, apophyses articulaires et transverses (facettes des côtes) ;
    épines hautes et penchées vers la queue au garrot, de plus en plus courtes et droites vers les reins,
    d'après la planche 3 (T12 et T13 déjà rectangulaires comme celles des lombaires)."""
    f = Forme()
    from planches_os import EPINES_T
    for i in range(13):
        nom = f"T{i + 1}"
        vertebre(f, nom, 0.024 + 0.0008 * i, haut_arc=0.024, canal=0.011, epine=None,
                 transv=(0.04, 0.012, 0.009, 0.008, 0.0), articulaires=0.009)
        P, T, L = VERT[nom]
        u, v, w = repere_vertebre(P, T)
        for sw in (1, -1):    # facettes pour la tête et le tubercule des côtes
            f.ajouter(ell(P - u * L * 0.5 + v * 0.008 + w * sw * 0.02, (0.009, 0.009, 0.006), axes=(u, v, w)), 0.003)
        contour = os_planche(f"epine_{nom}")["contour"]
        vers = lambda x, y, i=i: _vers_modele_T(i, x, y)
        if nom in EPINES_T:
            bout = vers(*EPINES_T[nom][0])
            f.ajouter(_plaque_sagittale(contour, vers, 0.0042 + 0.0001 * i, bout=bout, e_bout=0.0045), 0.006)
        else:
            haut = max(vers(x, y)[1] for x, y in contour)
            f.ajouter(_plaque_sagittale(contour, vers, 0.0048, haut=haut - 0.016, e_haut=0.004), 0.006)
    return f


def lombaires():
    """Les 6 lombaires : corps longs, épines rectangulaires à bord supérieur épaissi (planche 3), grandes
    apophyses articulaires (mamillaires) au pied des épines, et les longues apophyses transverses plates,
    les « étagères » du faux-filet et du filet (planche 13, vue de dessus)."""
    f = Forme()
    from planches_os import ARTICULAIRES_L, CORPS_L, MILIEU_57
    for i in range(6):
        nom = f"L{i + 1}"
        P, T, L = VERT[nom]
        u, v, w = repere_vertebre(P, T)
        vertebre(f, nom, 0.029, haut_arc=0.026, canal=0.012, epine=None, transv=None, articulaires=0.01)
        vers = lambda x, y, nom=nom: _vers_modele_L(nom, x, y)
        contour = os_planche(f"epine_{nom}")["contour"]
        haut = max(vers(x, y)[1] for x, y in contour)
        f.ajouter(_plaque_sagittale(contour, vers, 0.0052, haut=haut - 0.018, e_haut=0.0055), 0.006)
        # apophyses articulaires craniales avec leur tubercule mamillaire : grosses bosses en dehors, devant l'épine
        a = vers(*ARTICULAIRES_L[nom])
        for sw in (1, -1):
            f.ajouter(ell(p3(a[0] + 0.004, a[1] - 0.004, sw * 0.022), (0.017, 0.009, 0.0095)), 0.012)
        # apophyse transverse (vue de dessus) : plaque horizontale qui remonte un peu vers son bout
        d = os_planche(f"transverse_{nom}")
        niv = d["reperes"]["niveau"]
        for sw in (1, -1):
            pts = [(P[0] + S_57 * (py - niv), sw * S_57 * (MILIEU_57 - px)) for px, py in d["contour"]]
            R = Repere(p3(0, P[1], 0), (1, 0, 0), (0, 1, 0), V_vers=(0, 0, 1))     # (u, v) = (x, z), w = -(y - P.y)
            centre = lambda uu, vv: -(0.008 + 0.09 * np.clip(np.abs(vv) - 0.03, 0, None))
            epaisseur = lambda uu, vv: 0.0058 - 0.012 * np.clip(np.abs(vv) - 0.03, 0, 0.13)
            f.ajouter(plaque(R, pts, 0.0058, arrondi=0.002, decal=centre, epaisseurs=epaisseur), 0.008)
    return f


def sacrum():
    """Sacrum : 5 vertèbres soudées. D'après la planche 3 (profil) : la crête sacrée médiane, haute et festonnée
    (épines soudées, au niveau de celles des reins), la face dorsale et les 4 paires de trous sacrés ; d'après
    la planche 13 (dessus) : le contour en coin, les ailes devant (articulées avec l'os du bassin) et les
    parties latérales qui s'amincissent vers la queue. Corps et canal de la moelle dessous."""
    f = Forme()
    d = os_planche("sacrum_crete")
    rp = d["reperes"]
    P, T, L = VERT["S"]
    u, v, w = repere_vertebre(P, T)
    a, b = P - u * L / 2, P + u * L / 2
    pose = Placement(rp["axe_avant"], rp["axe_arriere"], a, b, normale=Z)
    vers = lambda x, y: pose.vers_modele(x, y)[:2]
    # corps (promontoire épais devant), sous la face dorsale
    f.ajouter(loft([a + v * 0.004, P - u * 0.06 + v * 0.002, P + u * 0.05, b - v * 0.002],
                   [0.026, 0.023, 0.018, 0.013], [0.036, 0.03, 0.022, 0.015], haut=v, arrondi=0.005), 0.012)
    # face dorsale (hauteur au-dessus de l'axe, le long de l'axe) relevée sur la planche 3
    fd = np.array([[float((pose.vers_modele(x, y) - a) @ u), float((pose.vers_modele(x, y) - a) @ v)]
                   for x, y in rp["face_dorsale"]])
    haut_dos = lambda uu: np.interp(uu, fd[:, 0], fd[:, 1])
    # contour vu de dessus (moitié gauche + son reflet) : u le long de l'axe, w en travers
    dd = os_planche("sacrum_dessus")
    av, ar = dd["reperes"]["avant"], dd["reperes"]["arriere"]
    ku = L / (ar - av)
    from planches_os import MILIEU_57
    gauche = [((py - av) * ku, (MILIEU_57 - px) * 0.0017) for px, py in dd["contour"]]
    gauche = [(uu, ww) for uu, ww in gauche if ww > 0.001]
    gauche.sort(key=lambda t: t[0])
    contour = [(0.0, 0.0)] + gauche + [(L, 0.0)] + [(uu, -ww) for uu, ww in gauche[::-1]]
    R = Repere(a, u, v, V_vers=w)       # (U, V) = (le long, en travers), W = vers le bas
    gu = np.array([g[0] for g in gauche]); gw = np.array([g[1] for g in gauche])
    demi_l = lambda uu: np.maximum(np.interp(uu, gu, gw), 0.02)
    # face dorsale un peu bombée au milieu ; face ventrale creusée (bassin) qui remonte vers les bords : les
    # parties latérales du sacrum sont minces, le corps (au milieu) est épais
    def dessus(uu, ww):
        return haut_dos(uu) - 0.008 * np.clip(np.abs(ww) / demi_l(uu), 0, 1) ** 2
    def dessous(uu, ww):
        fond = -(0.012 + 0.02 * (1 - np.clip(uu / L, 0, 1)))      # 9 cm d'épaisseur devant, 4 à 5 cm au bout
        r = np.clip(np.abs(ww) / demi_l(uu), 0, 1)
        return fond + (dessus(uu, ww) - 0.01 - fond) * r ** 1.6
    centre = lambda uu, ww: -((dessus(uu, ww) + dessous(uu, ww)) / 2)
    ep = lambda uu, ww: np.maximum((dessus(uu, ww) - dessous(uu, ww)) / 2, 0.0045)
    f.ajouter(plaque(R, contour, 0.03, arrondi=0.004, decal=centre, epaisseurs=ep), 0.012)
    # crête sacrée médiane, épaissie au sommet (tubercules des épines soudées)
    crete = d["contour"]
    sommet = max(vers(x, y)[1] for x, y in crete)
    f.ajouter(_plaque_sagittale(crete, vers, 0.0055, haut=sommet - 0.03, e_haut=0.0035), 0.008)
    # apophyses articulaires craniales (contre la 6e lombaire)
    for sw in (1, -1):
        f.ajouter(ell(a + u * 0.014 + v * (haut_dos(0.014) - 0.002) + w * sw * 0.024, (0.016, 0.008, 0.01), axes=(u, v, w)), 0.012)
    # canal de la moelle, et 4 paires de trous sacrés dorsaux (relevés sur la planche 3)
    f.creuser(loft([a - u * 0.02 + v * 0.03, b + u * 0.02 + v * 0.02], [0.011, 0.006], [0.014, 0.007], haut=v), 0.002)
    for q in rp["trous"]:
        c = pose.vers_modele(*q)
        uu = float((c - a) @ u)
        c = a + u * uu + v * haut_dos(uu)
        for sw in (1, -1):
            f.creuser(cylindre(c + w * sw * 0.032 - v * 0.03, c + w * sw * 0.032 + v * 0.03, 0.0062), 0.002)
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
# Cage thoracique d'après la planche 3 (Ellenberger-Baum) : côtes larges (5 à 6 cm en bas) et presque
# jointives, penchées vers l'arrière de 12 à 17°, jonction os / cartilage près du sternum pour les 8 côtes
# « vraies », de plus en plus haute pour les 5 « asternales » (à mi-hauteur pour la 13e) dont les
# cartilages forment l'arc costal. La largeur de la cage suit l'intérieur de la paroi du corps (sous
# le plat de côtes, 4 à 5 cm de viande) ; sous l'épaule, les côtes restent en dedans de la palette.
Y_STERNUM = 0.69                      # face dorsale des sternèbres
X_STERNEBRES = [-0.705, -0.64, -0.565, -0.49, -0.415, -0.34, -0.265]       # 7 sternèbres (manubrium d'abord)
X_XIPHOIDE = -0.13

_corps_cache = None


def _corps():
    global _corps_cache
    if _corps_cache is None:
        from formes import boeuf
        _corps_cache = boeuf()
    return _corps_cache


def _z_paroi(x, y, epaisseur):
    """Côté gauche : plus grand z tel que le point (x, y, z) soit à « epaisseur » sous la peau."""
    zs = np.linspace(0.0, 0.55, 221, dtype=np.float32)
    P = np.stack([np.full_like(zs, x), np.full_like(zs, y), zs], -1)
    d = _corps().distance(P)
    ok = zs[d < -epaisseur]
    return float(ok.max()) if len(ok) else 0.05


def _z_sous_palette(x, y):
    """Plan de la palette (côté gauche) : les côtes de devant passent 4 cm en dedans."""
    R = repere_palette()
    W = R.W
    # point du plan à (x, y) : W . (P - O) = 0
    z = R.O[2] - (W[0] * (x - R.O[0]) + W[1] * (y - R.O[1])) / W[2]
    dans = (x < DOS_PAL[0] + 0.16) and (y > GLENE[1] - 0.2)
    return z - 0.045 if dans else 9.0


def _rib(i):
    """Ligne médiane de la côte i (0 = 1re), côté gauche : (points de la partie osseuse, du cartilage)."""
    P, T, L = VERT[f"T{i + 1}"]
    x0, y0 = P[0] - L * 0.5, P[1] + 0.004                      # tête de côte : entre deux vertèbres
    prof = y0 - Y_STERNUM
    fj = [0.86, 0.87, 0.875, 0.88, 0.88, 0.88, 0.875, 0.865, 0.83, 0.77, 0.7, 0.62, 0.52][i]   # hauteur de la jonction
    recul = [0.012, 0.035, 0.055, 0.075, 0.09, 0.105, 0.12, 0.135, 0.15, 0.162, 0.172, 0.18, 0.186][i]
    xj, yj = x0 + recul, y0 - prof * fj
    pts = []
    for t in np.linspace(0, 1, 9):
        x = x0 + recul * (t ** 1.15) - 0.012 * np.sin(np.pi * t) * (i > 0)   # légère courbure, bombée vers l'avant
        y = y0 - prof * fj * t
        pts.append([x, y])
    # la cage est étroite devant (1re côte) et s'élargit jusqu'à la 7e ; elle se resserre vers le sternum
    zlim = [0.125, 0.165, 0.2, 0.228, 0.255, 0.28, 0.305, 0.325, 0.345, 0.36, 0.37, 0.375, 0.375][i]
    zs = []
    for k, (x, y) in enumerate(pts):
        t = k / 8
        if t == 0:
            z = 0.026
        else:
            zp = min(_z_paroi(x, y, 0.045 + 0.05 * max(0, 0.3 - t)), _z_sous_palette(x, y))
            zp = min(zp, zlim * (1 - 0.28 * np.clip((t - 0.62) / 0.38, 0, 1) ** 1.5 * (i < 9)))
            zarc = 0.026 + (zp - 0.026) * np.sin(min(1.0, t / 0.42) * np.pi / 2) ** 0.8     # angle de la côte puis la paroi
            z = min(zarc, zp)
        zs.append(z)
    zs = np.convolve(np.r_[zs[0], zs, zs[-1]], [0.25, 0.5, 0.25], "valid").tolist()           # sans à-coups
    zs[0] = 0.026
    os_pts = [p3(x, y, z) for (x, y), z in zip(pts, zs)]
    if i < 8:                       # côtes « vraies » : cartilage jusqu'au sternum
        xs = X_STERNEBRES[min(i, 6)] + (0.035 if i == 7 else 0.0)
        fin = p3(xs, Y_STERNUM + 0.012, 0.035)
        j = os_pts[-1]
        cart = [j, p3((j[0] + xs) / 2 + 0.015, (j[1] + fin[1]) / 2 - 0.01, (j[2] + 0.035) / 2 + 0.02), fin]
    else:                           # côtes « asternales » : leur cartilage rejoint celui de la côte d'avant (arc costal)
        j = os_pts[-1]
        prev = _rib_cache[i - 1][1]
        cible = prev[len(prev) // 2] if len(prev) > 2 else prev[-1]
        cart = [j, (j + cible) / 2 + p3(0.0, -0.02, 0.0), cible + p3(0.012, 0.006, 0.004)]
    return os_pts, cart


_rib_cache = []


def _ribs():
    if not _rib_cache:
        for i in range(13):
            _rib_cache.append(_rib(i))
    return _rib_cache


def cotes():
    """Les 13 côtes gauches : tête et tubercule contre les vertèbres, corps large et plat, cartilage en bas."""
    f = Forme()
    for i, (os_pts, cart) in enumerate(_ribs()):
        c = courbe(os_pts, n=30)
        n = len(c)
        t = np.linspace(0, 1, n)
        large = [0.016, 0.02, 0.023, 0.025, 0.027, 0.028, 0.028, 0.028, 0.027, 0.025, 0.023, 0.02, 0.016][i]
        a = 0.009 + (large - 0.009) * np.sin(np.clip(t * 1.4, 0, 1) * np.pi / 2)      # demi-largeur (le long du corps)
        a = a * (1 - 0.12 * np.clip((t - 0.8) / 0.2, 0, 1))
        b = 0.0085 - 0.0042 * np.clip(t * 1.3, 0, 1)                                   # demi-épaisseur : plate en bas
        a[0], b[0] = 0.012, 0.011                                                     # tête de la côte
        # « haut » = direction qui pointe vers l'avant dans le plan de la paroi : la côte est plate contre la paroi
        f.ajouter(loft(c, a, b, haut=(1, 0, 0), arrondi=0.0025), 0.003)
        f.ajouter(ell(os_pts[0] + p3(0.004, 0.012, 0.03), (0.009, 0.008, 0.008)), 0.004)   # tubercule
        cc = courbe(cart, n=12)
        ac = np.linspace(a[-1] * 0.8, 0.008, len(cc))
        f.ajouter(loft(cc, ac, np.full(len(cc), 0.006), haut=(1, 0, 0), arrondi=0.002), 0.003, "cartilage")
    return f


def sternum():
    """Sternum : 7 sternèbres (la 1re, le manubrium, pointe vers l'avant), cartilages entre elles,
    appendice xiphoïde (cartilage large et plat) en arrière."""
    f = Forme()
    xs = X_STERNEBRES
    f.ajouter(loft([p3(xs[0] - 0.035, Y_STERNUM + 0.03), p3(xs[0], Y_STERNUM + 0.008), p3(xs[0] + 0.025, Y_STERNUM)],
                   [0.022, 0.024, 0.02], [0.011, 0.014, 0.016], haut=Y, arrondi=0.004), 0.006)
    for k, x in enumerate(xs[1:]):
        y = Y_STERNUM - 0.006 - 0.004 * k
        f.ajouter(boite(p3(x, y), (0.027, 0.013 - 0.0005 * k, 0.022 + 0.005 * k), arrondi=0.008), 0.004)
    for k in range(len(xs) - 1):
        xm = (xs[k] + xs[k + 1]) / 2
        f.ajouter(boite(p3(xm, Y_STERNUM - 0.008 - 0.004 * k), (0.01, 0.009, 0.018 + 0.005 * k), arrondi=0.006), 0.004, "cartilage")
    f.ajouter(ell(p3(X_XIPHOIDE, Y_STERNUM - 0.04), (0.07, 0.007, 0.05)), 0.01, "cartilage")       # appendice xiphoïde
    f.ajouter(cap(p3(xs[-1] + 0.03, Y_STERNUM - 0.035), p3(X_XIPHOIDE - 0.04, Y_STERNUM - 0.04), 0.012, 0.01), 0.008)
    return f


# ================================================================ membre avant (côté gauche)
GLENE = p3(-0.745, 0.985, 0.25)          # cavité glénoïde (articulation de l'épaule)
DOS_PAL = p3(-0.505, 1.352, 0.152)       # milieu du bord dorsal de la palette
BOULET_AV = p3(-0.611, 0.135, 0.2)       # boulet (articulation canon / 1re phalange)
# Longueurs des os du membre avant d'après la planche 3 (Ellenberger-Baum), à une même échelle :
# S_AV mètres par pixel de planche (palette, radius, canon et doigt y tombent juste ensemble).
S_AV = 0.00094
HUM_TETE = GLENE - n_(DOS_PAL - GLENE) * 0.03 + p3(0.006, 0.0, 0.0)     # centre de la tête de l'humérus
COUDE = HUM_TETE + n_(p3(0.18, -0.256, -0.0205)) * (253 * S_AV)          # condyle de l'humérus (coude)
CARPE = COUDE + n_(p3(BOULET_AV[0] - 0.002 - COUDE[0], -0.328, 0.208 - COUDE[2])) * (352 * S_AV)   # bas du radius (carpe), d'aplomb
CANON_AV_HAUT = CARPE + n_(BOULET_AV - CARPE) * (56 * S_AV)                 # haut du canon, sous le carpe
PINCE_AV = BOULET_AV + p3(-0.068, -0.12, 0.0)                             # bout de l'onglon, dans le sabot


def repere_palette():
    U = DOS_PAL - GLENE
    return Repere(GLENE, U, (0.12, 0.05, 1.0), V_vers=(-1, 0, 0))     # v > 0 = vers l'avant


def _decale(prim, t):
    """Primitive translatée de t."""
    from sdf import Prim
    t32 = np.asarray(t, np.float32)
    return Prim(lambda P: prim.f(P - t32), prim.lo + t, prim.hi + t)


def _pts(pose, liste):
    return [pose.vers_modele(x, y) for x, y in liste]


def _uv(pose, P):
    q = np.asarray(P) - pose.A
    return float(q @ pose.U), float(q @ pose.V)


def palette():
    """Palette (omoplate, scapula) d'après son contour sur la planche 3 (Ellenberger-Baum, domaine public) :
    lame triangulaire, épine (l'arête) qui sépare la petite fosse de devant (dessus de palette) de la
    grande fosse de derrière (paleron), acromion, col, cavité glénoïde, tubercule supraglénoïdien,
    cartilage de la palette le long du bord dorsal."""
    f = Forme()
    d = os_planche("palette")
    rp = d["reperes"]
    G_p = np.asarray(rp["glene"], float)
    D_p = (np.asarray(rp["angle_cranial"], float) + np.asarray(rp["angle_caudal"], float)) / 2
    R = repere_palette()
    pose = Placement(G_p, D_p, GLENE, DOS_PAL, normale=R.W)
    mpx = pose.s                                         # mètres par pixel
    # lame : os plat, ~5 mm de demi-épaisseur, bords arrondis
    lame = cartes_silhouette(d["contour"], forme="plat", plat=0.0052 / mpx)
    f.ajouter(silhouette(lame, pose), 0.004)
    # bords épaissis : bord caudal (le plus épais, en bourrelet), bord crânial plus mince
    for nom_bord, e0, e1 in (("bord_caudal", 0.006, 0.0125), ("bord_cranial", 0.0048, 0.008)):
        pts = _pts(pose, rp[nom_bord])
        cb = courbe(pts, n=18)
        e = np.linspace(e0, e1, len(cb))
        f.ajouter(loft(cb, e, e * 0.9, haut=pose.W, arrondi=0.0025), 0.012)
    # épine : crête perpendiculaire à la lame, la plus haute au tiers inférieur, qui finit en acromion
    ep = _pts(pose, rp["epine"])                        # du bas (près du col) vers le haut
    ce = courbe(ep, n=18)
    t = np.linspace(0, 1, len(ce))
    haut_ep = 0.006 + 0.028 * np.sin(np.clip((t - 0.04) / 0.86, 0, 1) * np.pi) ** 0.7 * (1 - 0.5 * t)
    f.ajouter(loft([p_ + pose.W * h * 0.5 for p_, h in zip(ce, haut_ep)], haut_ep * 0.5 + 0.003, np.full(len(ce), 0.0042),
                   haut=pose.W, arrondi=0.002), 0.006)
    # tubérosité de l'épine (bourrelet au bord libre) et acromion (court, au-dessus de l'articulation)
    k = int(len(ce) * 0.42)
    f.ajouter(ell(ce[k] + pose.W * (haut_ep[k] + 0.002), (0.045, 0.008, 0.007), axes=(n_(ce[k + 2] - ce[k - 2]), pose.V, pose.W)), 0.008)
    f.ajouter(ell(ce[1] + pose.W * 0.02 + pose.U * 0.004, (0.018, 0.008, 0.012), axes=(pose.U, pose.V, pose.W)), 0.008)
    # col et cavité glénoïde (creux ovale tourné vers l'humérus), tubercule supraglénoïdien, coracoïde
    f.ajouter(ell(GLENE + pose.U * 0.03, (0.034, 0.03, 0.022), axes=(pose.U, pose.V, pose.W)), 0.014)
    f.ajouter(ell(GLENE + pose.U * 0.012, (0.024, 0.034, 0.03), axes=(pose.U, pose.V, pose.W)), 0.01)
    f.creuser(ell(GLENE - pose.U * 0.016, (0.02, 0.028, 0.024), axes=(pose.U, pose.V, pose.W)), 0.005)
    f.ajouter(ell(GLENE + pose.U * 0.028 + pose.V * 0.03, (0.016, 0.012, 0.013), axes=(pose.U, pose.V, pose.W)), 0.006)
    f.ajouter(ell(GLENE + pose.U * 0.03 + pose.V * 0.026 - pose.W * 0.016, (0.01, 0.008, 0.008), axes=(pose.U, pose.V, pose.W)), 0.005)
    # cartilage de la palette : bande qui prolonge le bord dorsal (environ 4 cm)
    bord = np.asarray(OS_PLANCHES["palette"]["barrieres"][0], float)
    centre_p = G_p
    hors = []
    for q in bord:
        dq = q - centre_p
        hors.append(q + dq / np.linalg.norm(dq) * (0.04 / mpx))
    poly = [_uv(pose, pose.vers_modele(*q)) for q in list(bord) + hors[::-1]]
    f.ajouter(plaque(Repere(pose.A, pose.U, pose.W, V_vers=pose.V), poly, 0.0042, arrondi=0.0025), 0.004, "cartilage")
    return f


def os_long(f, axe, sections, haut, arrondi=0.004, k=0.006):
    """Corps d'un os long : section elliptique variable le long de l'axe (liste de points)."""
    a = [s[0] for s in sections]
    b = [s[1] for s in sections]
    f.ajouter(loft(axe, a, b, haut=haut, arrondi=arrondi), k)


def os_planche3d(f, nom, cle_a, cle_b, A, B, forme="rond", k=1.0, plat=None, zones=(), normale=Z, kj=0.006,
                 partie="corps", epaisseur=1.0, decal=0.0, decal_b=None):
    """Ajoute à f l'os « nom » d'après sa silhouette de planche, posé de A (repère cle_a) à B (repère cle_b)."""
    d = os_planche(nom)
    rp = d["reperes"]
    pose = Placement(rp[cle_a], rp[cle_b], A, B, normale=normale)
    cartes = cartes_silhouette(d["contour"], forme=forme, k=k, plat=plat, zones=zones)
    f.ajouter(silhouette(cartes, pose, decal=decal, epaisseur=epaisseur, decal_b=decal_b), kj, partie)
    return pose


def humerus():
    """Humérus (« boîte à moelle ») d'après la planche 3 : tête en arrière, gros tubercule (la pointe de
    l'épaule), tubérosité deltoïdienne, condyle en bobine du coude et fosse de l'olécrane."""
    f = Forme()
    pose = os_planche3d(f, "humerus", "tete", "coude", HUM_TETE, COUDE, k=0.92, kj=0.008,
                        zones=[([(1190, 1060), (1270, 1060), (1270, 1130), (1190, 1130)], 0.82)])
    U, V, W = pose.U, pose.V, pose.W
    f.ajouter(ell(HUM_TETE + U * 0.014 - V * 0.004 - W * 0.006, (0.036, 0.035, 0.032), axes=(U, V, W)), 0.02)   # tête articulaire
    f.ajouter(ell(HUM_TETE + U * 0.012 + V * 0.045 - W * 0.022, (0.022, 0.018, 0.016), axes=(U, V, W)), 0.012)  # petit tubercule (dedans)
    c = COUDE
    f.ajouter(cap(c - W * 0.034, c + W * 0.03, 0.022), 0.01)                                        # condyle en bobine
    f.ajouter(ell(c - W * 0.026, (0.027, 0.03, 0.016), axes=(U, V, W)), 0.008)                      # lèvre interne (plus grosse)
    for sw, r in ((1, 0.013), (-1, 0.016)):                                                         # épicondyles
        f.ajouter(ell(c - U * 0.02 - V * 0.022 + W * sw * 0.03, (0.022, 0.016, r * 0.8), axes=(U, V, W)), 0.01)
    f.creuser(ell(c - U * 0.03 - V * 0.03, (0.022, 0.016, 0.015), axes=(U, V, W)), 0.005)            # fosse de l'olécrane
    f.creuser(cap(HUM_TETE + V * 0.06 + U * 0.01, HUM_TETE + V * 0.05 + U * 0.07, 0.007), 0.004)     # gouttière du biceps
    return f


def radius():
    """Radius (large, aplati d'avant en arrière) et cubitus soudé derrière, qui monte en olécrane (la pointe
    du coude), d'après la planche 3 ; os du carpe (deux rangées) et os accessoire."""
    f = Forme()
    pose = os_planche3d(f, "radius", "coude", "carpe", COUDE, CARPE, k=1.45, kj=0.01,
                        zones=[([(1480, 1220), (1620, 1220), (1620, 1360), (1480, 1360)], 0.42),     # olécrane : lame
                               ([(1438, 1380), (1470, 1380), (1470, 1700), (1438, 1700)], 0.7)])     # cubitus fin
    # l'échancrure où tourne le condyle de l'humérus est déjà dans la silhouette de la planche
    os_planche3d(f, "carpe_avant", "haut", "bas", CARPE, CANON_AV_HAUT, k=1.5, kj=0.004)
    return f


def canon_avant():
    """Métacarpe (canon : 2 os soudés, gouttière sur le devant) d'après la planche 3, et les deux doigts."""
    f = Forme()
    pose = os_planche3d(f, "canon_avant", "haut", "boulet", CANON_AV_HAUT, BOULET_AV, k=1.3, kj=0.006)
    U, V, W = pose.U, pose.V, pose.W
    f.creuser(cap(CANON_AV_HAUT - U * 0.03 - V * 0.026, BOULET_AV + U * 0.03 - V * 0.021, 0.0035), 0.002)  # gouttière dorsale
    for sw in (-1, 1):                                                                              # deux condyles
        f.ajouter(ell(BOULET_AV + U * 0.006 + W * sw * 0.017, (0.017, 0.0165, 0.0135), axes=(U, V, W)), 0.003)
    f.creuser(cap(BOULET_AV + U * 0.03 + V * 0.03, BOULET_AV + U * 0.03 - V * 0.03, 0.003), 0.002)  # entre les condyles
    for dz in (-0.0235, 0.0235):
        z = BOULET_AV[2] + dz
        os_planche3d(f, "doigt_avant", "boulet", "pince", p3(BOULET_AV[0], BOULET_AV[1], z), p3(PINCE_AV[0], PINCE_AV[1], z),
                     k=0.72, kj=0.003)
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


# ================================================================ membre arrière (côté gauche)
POINTE_HANCHE = p3(0.47, 1.318, 0.258)   # tubérosité coxale (la « hanche »)
SACREE = p3(0.552, 1.372, 0.052)         # tubérosité sacrée, près du sacrum
ACETABULE = p3(0.8, 1.0, 0.19)           # cavité de la hanche (articulation)
POINTE_FESSE = p3(1.04, 1.13, 0.112)     # tubérosité ischiatique
GRASSET = p3(0.69, 0.692, 0.215)         # condyles du fémur (articulation du grasset)
JARRET = p3(0.884, 0.418, 0.205)         # articulation du jarret (tibia / astragale)
BOULET_AR = p3(0.866, 0.132, 0.2)
TETE_FEMUR = ACETABULE + p3(0.0, -0.004, -0.006)                       # centre de la tête du fémur (dans le cotyle)
PLATEAU_TIBIA = GRASSET + p3(0.008, -0.048, -0.003)                       # haut du tibia, sous les condyles du fémur
CANON_AR_HAUT = p3(0.878, 0.355, 0.2)                                     # haut du métatarse, sous le tarse
PINCE_AR = BOULET_AR + p3(-0.07, -0.118, 0.0)                             # bout de l'onglon, dans le sabot


def _affine_xz(paires):
    """Affine (2x3) pixels de planche vue de dessus -> (x, z) du modèle, au sens des moindres carrés."""
    A = np.array([[px, py, 1.0] for (px, py), _ in paires])
    Bx = np.array([xz[0] for _, xz in paires])
    Bz = np.array([xz[1] for _, xz in paires])
    return np.vstack([np.linalg.lstsq(A, Bx, rcond=None)[0], np.linalg.lstsq(A, Bz, rcond=None)[0]])


def _affine_coxal():
    rp = os_planche("coxal_dessus")["reperes"]
    return _affine_xz([(rp["hanche"], (POINTE_HANCHE[0], POINTE_HANCHE[2] - 0.03)),
                       (rp["acetabule"], (ACETABULE[0], ACETABULE[2] + 0.02)),
                       (rp["fesse"], (POINTE_FESSE[0], POINTE_FESSE[2])), (rp["symphyse"], (0.92, 0.0)),
                       (rp["sacree"], (SACREE[0], SACREE[2]))])


def coxal():
    """Os coxal gauche d'après le bassin vu de dessus (planche 13, fig. 62) et de profil (planche 3) :
    aile de l'ilium (pointe de la hanche à trois bosses, tubérosité sacrée), col de l'ilium, cavité de la
    hanche (cotyle), plancher du bassin (pubis et ischion) percé du trou obturé, symphyse, et la pointe de
    la fesse (tubérosité ischiatique). Le contour vient de la vue de dessus ; la hauteur de chaque point
    suit une surface lisse calée sur les repères de profil."""
    f = Forme()
    d = os_planche("coxal_dessus")
    M = _affine_coxal()
    # hauteur (y) de la surface de l'os : (x, z, y)
    appuis_y = [
        (0.47, 0.258, 1.312), (0.552, 0.052, 1.362), (0.5, 0.16, 1.322), (0.48, 0.09, 1.34), (0.56, 0.22, 1.265),
        (0.62, 0.2, 1.2), (0.64, 0.12, 1.2), (0.7, 0.19, 1.11), (0.72, 0.1, 1.09), (0.8, 0.2, 1.0), (0.8, 0.06, 0.985),
        (0.85, 0.0, 0.955), (0.92, 0.0, 0.952), (0.99, 0.0, 0.975), (0.9, 0.1, 0.975), (0.95, 0.16, 1.02),
        (1.04, 0.112, 1.12), (1.0, 0.04, 1.02), (1.06, 0.14, 1.14), (0.6, 0.0, 1.3),
    ]
    # demi-épaisseur (normale) : aile et plancher minces, col de l'ilium et pourtour du cotyle épais
    appuis_e = [
        (0.47, 0.258, 0.011), (0.552, 0.052, 0.014), (0.5, 0.16, 0.008), (0.56, 0.22, 0.01), (0.62, 0.19, 0.016),
        (0.68, 0.18, 0.019), (0.72, 0.12, 0.012), (0.8, 0.2, 0.026), (0.8, 0.06, 0.012), (0.88, 0.02, 0.01),
        (0.95, 0.1, 0.008), (0.92, 0.0, 0.012), (1.04, 0.112, 0.02), (0.99, 0.15, 0.01), (1.0, 0.04, 0.009),
        (0.6, 0.0, 0.01),
    ]
    f.ajouter(relief(d["contour"], d["trous"], M, appuis_y, appuis_e), 0.004)
    # pointe de la hanche à trois bosses, tubérosité sacrée, pointe de la fesse (trois bosses)
    for dd in (p3(0, 0.01, 0.0), p3(0.024, -0.024, 0.008), p3(-0.016, -0.02, -0.004)):    # juste sous la peau
        f.ajouter(ell(POINTE_HANCHE + p3(0.0, -0.006, -0.016) + dd, (0.02, 0.017, 0.018)), 0.012)
    f.ajouter(ell(SACREE + p3(0.0, 0.004, 0.0), (0.02, 0.016, 0.014)), 0.01)
    for dd, r in ((p3(0.0, 0.026, -0.004), 0.016), (p3(0.014, 0.0, 0.018), 0.015), (p3(-0.008, -0.034, 0.004), 0.014)):
        f.ajouter(ell(POINTE_FESSE + dd, (r, r * 1.1, r * 0.9)), 0.012)
    # cavité de la hanche (cotyle) : coupe épaisse autour de la tête du fémur, ouverte en dehors et en bas,
    # échancrure en bas
    tf = TETE_FEMUR
    f.ajouter(ell(tf + p3(0.0, 0.012, -0.014), (0.048, 0.046, 0.04)), 0.014)
    f.creuser(ell(tf, (0.037, 0.037, 0.036)), 0.004)
    f.creuser(ell(tf + p3(0.0, -0.032, 0.036), (0.036, 0.034, 0.032)), 0.006)
    f.creuser(ell(tf + p3(0.012, -0.044, 0.006), (0.012, 0.012, 0.03)), 0.003)
    # symphyse (soudure des deux moitiés) un peu épaissie en dessous
    f.ajouter(loft([p3(0.86, 0.948, 0.01), p3(0.93, 0.946, 0.012), p3(0.985, 0.968, 0.01)], [0.012, 0.013, 0.012],
                   [0.012, 0.014, 0.012], haut=Y, arrondi=0.004), 0.01)
    # articulation sacro-iliaque : l'os du bassin s'appuie sur le sacrum (relevé sur les planches) sans le traverser
    sac = sacrum()
    lo, hi = sac.boite(0.006)
    f.creuser(Prim(lambda P: sac.distance(P) - 0.002, lo, hi), 0.003)
    return f


def femur():
    """Fémur d'après la planche 3 : tête dans la cavité de la hanche, grand trochanter, corps épais,
    trochlée (gorge de la rotule) devant, deux condyles derrière."""
    f = Forme()
    tete = ACETABULE + p3(0.0, -0.004, 0.006)
    pose = os_planche3d(f, "femur", "tete", "grasset", tete, GRASSET, k=0.95, kj=0.008, decal=0.03, decal_b=0.0)
    U, V, W = pose.U, pose.V, pose.W
    f.ajouter(ell(TETE_FEMUR, (0.034, 0.034, 0.033), axes=(U, V, W)), 0.016)                         # tête (vers le dedans)
    f.creuser(ell(TETE_FEMUR - W * 0.032 + U * 0.004, (0.008, 0.008, 0.006), axes=(U, V, W)), 0.002)  # fossette du ligament rond
    f.ajouter(ell(tete + U * 0.1 - V * 0.0 - W * 0.022, (0.022, 0.012, 0.012), axes=(U, V, W)), 0.01)   # petit trochanter (dedans)
    for sw, r in ((-1, 0.019), (1, 0.016)):                                                         # deux condyles, bien séparés
        f.ajouter(ell(GRASSET + V * -0.012 + W * sw * 0.024, (0.033, 0.032, r), axes=(U, V, W)), 0.008)
    f.creuser(ell(GRASSET - V * 0.03 + U * 0.005, (0.03, 0.02, 0.009), axes=(U, V, W)), 0.003)      # fosse intercondylaire
    for sw, r in ((-1, 0.012), (1, 0.01)):                                                          # lèvres de la trochlée
        f.ajouter(ell(GRASSET + V * 0.036 - U * 0.02 + W * sw * 0.017, (0.04, 0.012, r), axes=(U, V, W)), 0.008)
    return f


def rotule():
    """Rotule d'après la planche 3, posée devant la trochlée du fémur."""
    f = Forme()
    rp = os_planche("femur")["reperes"]
    tete = ACETABULE + p3(0.0, -0.004, 0.006)
    d = os_planche("rotule")
    pose = Placement(rp["tete"], rp["grasset"], tete, GRASSET)
    f.ajouter(silhouette(cartes_silhouette(d["contour"], forme="rond", k=1.15), pose, decal=0.004), 0.004)
    f.ops[-1] = ("+", _decale(f.ops[-1][1], -pose.V * 0.016), f.ops[-1][2], f.ops[-1][3])
    return f


def tibia():
    """Tibia d'après la planche 3 : plateau à deux condyles, tubérosité et crête devant, malléoles en bas ;
    péroné réduit ; tarse avec l'astragale et le calcanéum (la pointe du jarret)."""
    f = Forme()
    pose = os_planche3d(f, "tibia", "plateau", "jarret", PLATEAU_TIBIA, JARRET, k=1.05, kj=0.008,
                        zones=[([(2840, 1190), (2960, 1190), (2960, 1260), (2840, 1260)], 1.3)])    # plateau large
    U, V, W = pose.U, pose.V, pose.W
    for sw in (-1, 1):                                                                              # deux condyles du plateau
        f.ajouter(ell(PLATEAU_TIBIA - U * 0.004 + W * sw * 0.024, (0.012, 0.03, 0.022), axes=(U, V, W)), 0.008)
    f.ajouter(ell(PLATEAU_TIBIA + U * 0.012 + W * 0.046, (0.012, 0.01, 0.008), axes=(U, V, W)), 0.008)   # tête du péroné (soudée)
    f.ajouter(ell(JARRET - U * 0.006 + W * 0.03, (0.016, 0.012, 0.008), axes=(U, V, W)), 0.006)       # os malléolaire (dehors)
    f.ajouter(ell(JARRET - U * 0.008 - W * 0.03, (0.018, 0.013, 0.008), axes=(U, V, W)), 0.006)       # malléole interne
    os_planche3d(f, "tarse", "haut", "bas", JARRET, CANON_AR_HAUT, k=1.35, kj=0.004,
                 zones=[([(3135, 1490), (3215, 1490), (3215, 1590), (3135, 1590)], 0.6)])           # calcanéum : lame
    return f


def canon_arriere():
    """Métatarse (canon arrière, plus long et plus carré que l'avant) d'après la planche 3, et les doigts."""
    f = Forme()
    pose = os_planche3d(f, "canon_arriere", "haut", "boulet", CANON_AR_HAUT, BOULET_AR, k=1.15, kj=0.006)
    U, V, W = pose.U, pose.V, pose.W
    f.creuser(cap(CANON_AR_HAUT + U * 0.03 + V * 0.022, BOULET_AR - U * 0.035 + V * 0.018, 0.004), 0.002)  # gouttière, profonde
    for sw in (-1, 1):
        f.ajouter(ell(BOULET_AR + U * 0.006 + W * sw * 0.017, (0.017, 0.0165, 0.0135), axes=(U, V, W)), 0.003)
    f.creuser(cap(BOULET_AR + U * 0.03 + V * 0.03, BOULET_AR + U * 0.03 - V * 0.03, 0.003), 0.002)
    for dz in (-0.0235, 0.0235):
        z = BOULET_AR[2] + dz
        os_planche3d(f, "doigt_arriere", "boulet", "pince", p3(BOULET_AR[0], BOULET_AR[1], z), p3(PINCE_AR[0], PINCE_AR[1], z),
                     k=0.72, kj=0.003)
    return f


# ================================================================ tête
def _similitude(paires):
    """Similitude 2D (échelle, rotation, translation) planche -> plan (x, y) du modèle, au sens des moindres
    carrés ; la planche a son y vers le bas."""
    P = np.array([[p[0], -p[1]] for p, _ in paires], float)
    Q = np.array([q for _, q in paires], float)
    mp, mq = P.mean(0), Q.mean(0)
    A, B = P - mp, Q - mq
    U_, S_, Vt = np.linalg.svd(B.T @ A)
    R = U_ @ Vt
    if np.linalg.det(R) < 0:
        R = U_ @ np.diag([1, -1]) @ Vt
    s = S_.sum() / (A ** 2).sum()
    return lambda p: mq + s * R @ (np.array([p[0], -p[1]], float) - mp)


def _pose_tete():
    rp = os_planche("crane")["reperes"]
    # calage dans la tête du modèle (recherché pour que tout l'os reste sous la peau) : bout de l'os incisif
    # sous le mufle, orbite sous l'œil, chignon entre les cornes ; crâne de 56 cm
    vers = _similitude([(rp["incisif"], (-1.575, 0.989)), (rp["orbite"], (-1.346, 1.274)), (rp["nuque"], (-1.188, 1.397))])
    A = p3(*vers(rp["incisif"]))
    B = p3(*vers(rp["nuque"]))
    return Placement(rp["incisif"], rp["nuque"], A, B), vers


# demi-largeur du crâne (m) le long de l'axe bout du nez -> nuque (0 -> 1) : museau 4,5 cm, tubérosités faciales
# 7 cm, orbites 10,5 cm, rétrécissement derrière les orbites, nuque et base des cornes 9 cm
KZ = 0.9                # le crâne est à 90 % d'un crâne de 62 cm : largeurs et écarts réduits d'autant
LARGEUR_CRANE = [(u, KZ * w) for u, w in [(0.0, 0.04), (0.1, 0.044), (0.2, 0.05), (0.3, 0.057), (0.4, 0.066), (0.5, 0.072),
                                          (0.6, 0.082), (0.68, 0.096), (0.76, 0.106), (0.84, 0.09), (0.92, 0.088), (1.0, 0.085),
                                          (1.2, 0.07)]]


def crane():
    """Crâne de bovin d'après la planche 9 (fig. 31, Ellenberger-Baum) : profil exact (os incisif sans dents,
    os nasal, front large et plat, chignon entre les cornes, nuque), largeur d'un crâne réel ; orbites
    fermées avec leur rebord, fosses temporales et arcades zygomatiques, ouverture du nez, trou
    sous-orbitaire, condyles de l'occipital et trou occipital, chevilles osseuses des cornes, molaires ;
    mâchoire inférieure (corps, barre, branche montante, angle, apophyse coronoïde, condyle) et incisives."""
    f = Forme()
    d = os_planche("crane")
    rp = d["reperes"]
    pose, vers = _pose_tete()
    U, V, W = pose.U, pose.V, pose.W
    L = pose.longueur
    larg = np.array(LARGEUR_CRANE)
    f.ajouter(volume_profil(d["contour"], pose, larg, p=2.6, haut_etroit=0.7), 0.006)
    P_ = lambda cle, z=0.0: p3(*vers(rp[cle]), z)
    demi = lambda u: float(np.interp(u, larg[:, 0], larg[:, 1]))
    u_de = lambda P: float((np.asarray(P) - pose.A) @ U) / L
    for sz in (1, -1):
        # orbite : creux profond tourné en dehors (un peu en avant), rebord osseux saillant
        o = P_("orbite")
        wo = demi(u_de(o))
        regard = n_(Z * sz * 0.92 - U * 0.3)
        f.ajouter(tore(o + Z * sz * (wo - 0.014), regard, 0.031, 0.0075), 0.018)
        f.creuser(ell(o + Z * sz * (wo + 0.002), (0.03, 0.028, 0.032), axes=(U, V, W)), 0.01)
        # fosse temporale derrière l'orbite, arcade zygomatique par-dessus
        t = P_("temporal")
        f.creuser(ell(t + Z * sz * (demi(u_de(t)) + 0.006), (0.04, 0.03, 0.02), axes=(U, V, W)), 0.01)
        arc = [p3(*vers(q), sz * (demi(u_de(p3(*vers(q)))) + 0.004)) for q in rp["arcade"]]
        f.ajouter(loft(courbe(arc, n=10), [0.011, 0.009, 0.009, 0.011], [0.006, 0.005, 0.005, 0.006], haut=V, arrondi=0.003), 0.008)
        # trou sous-orbitaire
        so = P_("trou_sous_orbite")
        f.creuser(ell(so + Z * sz * demi(u_de(so)), (0.008, 0.006, 0.01), axes=(U, V, W)), 0.002)
        # cheville osseuse de la corne : sur le côté puis vers le haut, logée dans la corne
        cb = P_("corne", sz * 0.075 * KZ)
        corne = courbe([cb, cb + p3(0.006, 0.02, sz * 0.066), cb + p3(0.012, 0.05, sz * 0.13), cb + p3(-0.01, 0.1, sz * 0.18)], n=12)
        f.ajouter(loft(corne, np.linspace(0.03, 0.008, 12), np.linspace(0.026, 0.007, 12), haut=Y, arrondi=0.004), 0.016)
        # molaires du haut : 6 dents (3 prémolaires, 3 molaires) le long de la rangée
        dents = [p3(*vers(q)) for q in rp["dents_haut"]]
        for j in range(6):
            t_ = j / 5
            q = np.asarray(dents[0]) * (1 - t_) + np.asarray(dents[-1]) * t_
            zq = sz * (demi(u_de(q)) - 0.016)
            f.ajouter(boite(q + p3(0, 0.012, 0) + Z * zq, (0.011 + 0.002 * t_, 0.013, 0.0095), arrondi=0.004, axes=(U, V, W)),
                      0.003, "dent")
    # ouverture du nez (entre l'os nasal et l'os incisif), trou occipital
    f.creuser(ell(P_("narine"), (0.05, 0.026, 0.046), axes=(U, V, W)), 0.01)
    oc = P_("occipital")
    f.creuser(cylindre(oc - U * 0.03 + V * 0.005, oc + U * 0.05 + V * 0.005, 0.015), 0.004)
    for sz in (1, -1):    # condyles de l'occipital
        f.ajouter(ell(oc + Z * sz * 0.026 - V * 0.004, (0.015, 0.02, 0.013), axes=(U, V, W)), 0.006)
    # mâchoire inférieure : deux moitiés écartées vers l'arrière (symphyse devant)
    dm = os_planche("mandibule")
    rm = dm["reperes"]
    for sz in (1, -1):
        A = p3(*vers(rm["incisives"]), sz * 0.014 * KZ)
        B = p3(*vers(rm["condyle"]), sz * 0.09 * KZ)
        pm = Placement(rm["incisives"], rm["condyle"], A, B, normale=Z * sz)
        cm = cartes_silhouette(dm["contour"], forme="plat", plat=0.0065 / pm.s,
                               zones=[([(2020, 1540), (2780, 1540), (2780, 1700), (2020, 1700)], 1.9),     # corps épais
                                      ([(2880, 980), (2960, 980), (2960, 1050), (2880, 1050)], 2.2)])     # condyle
        f.ajouter(silhouette(cm, pm), 0.006)
        dents = [p3(*vers(q)) for q in rm["dents_bas"]]
        for j in range(6):
            t_ = j / 5
            q = np.asarray(dents[0]) * (1 - t_) + np.asarray(dents[-1]) * t_
            zq = KZ * sz * (0.014 + (0.09 - 0.014) * float((q - A) @ pm.U) / pm.longueur) - sz * 0.002
            f.ajouter(boite(p3(q[0], q[1], zq) - pm.V * 0.012, (0.011 + 0.002 * t_, 0.012, 0.0085), arrondi=0.004,
                            axes=(pm.U, pm.V, pm.W)), 0.003, "dent")
    # 8 incisives, en bas seulement (en haut : bourrelet sans dents)
    ib = p3(*vers(rm["incisives"]))
    for j, a in enumerate(np.linspace(-1, 1, 8)):
        f.ajouter(ell(ib + p3(0.006 * abs(a), 0.012 + 0.004 * abs(a), 0.022 * a), (0.0075, 0.014, 0.0042), rot=(0, 0, -35)),
                  0.002, "dent")
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
