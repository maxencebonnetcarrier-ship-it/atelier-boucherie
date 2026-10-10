# Atelier : l'aloyau et le train de côtes du bœuf, muscle par muscle (« python outils/detail.py aloyau »).
#
# D'après le classeur (tableau n° 1, fiches magasin, guide de découpe) : les 5 dorsales du milieu (6e à 10e)
# portent le milieu de train de côtes, les 3 dernières dorsales et les 6 lombaires l'aloyau (faux-filet
# dessus, filet dessous). Chaque pièce est démontée en ses parties :
#   - train de côtes : noix d'entrecôte, nerf dorsal (sur la noix), dessus de côtes, bretelles (le long
#     des côtes) ;
#   - faux-filet : cœur, nerf dorsal (sur toute la longueur), chapeau de gendarme (bout côté entrecôte),
#     bretelle (le long des 3 dernières côtes), chaînette (bord côté flanc ; coupé du flanc à 6 cm de la noix) ;
#   - filet : chaînette (petit psoas, le long du filet), aile (muscle iliaque, contre la tête), tête,
#     cœur (châteaubriand), queue.
# La noix est le muscle long du dos (longissimus) : un tube elliptique le long de la colonne, posé sur les
# apophyses transverses, à la place des germes de outils/muscles.py. Placement simplifié : À FAIRE VALIDER.
# Os : dorsales de la 6e à la 13e, les 6 lombaires (fendues au milieu, comme sur une demi-carcasse) et les
# côtes 6 à 13 sciées en haut, comme sur un train de côtes.
import numpy as np

PAS = 0.004
PIECES_ALOYAU = ["cotes-entrecotes", "faux-filet", "filet"]
GRAS_ALOYAU = "gras-aloyau"
Y_SCIE = 1.13                       # trait de scie sur les côtes (m), juste sous les bretelles
OS_HD_ALOYAU = {"dorsales": 26000, "lombaires": 24000, "cotes": 24000}


def _dorsales():
    import squelette as sq
    return sq.dorsales(premiere=6)


def _cotes():
    import squelette as sq
    return sq.cotes(premiere=6, sciees_a=Y_SCIE)


FORMES_OS = {"dorsales": (_dorsales, False), "cotes": (_cotes, True)}


def epaisseur_gras_aloyau(X, Y, Z):
    """Gras de couverture : 1 cm sur les côtés, jusqu'à 1,8 cm sur le dos."""
    return 0.010 + 0.008 * np.clip((Y - 1.25) / 0.15, 0, 1)


def noix():
    """Le muscle long du dos (la noix) le long de la colonne : x des vertèbres, centre (y, z) et demi-axes
    (ay, az) de sa section. Dorsales : comme le germe des entrecôtes ; lombaires : comme celui du faux-filet."""
    import squelette as sq
    xs, yc, zc, ay, az = [], [], [], [], []
    for i in range(5, 13):                                  # T6 à T13
        P = sq.VERT[f"T{i + 1}"][0]
        tip = sq.EPINES_DORS[i]
        xs.append((P[0] + tip[0]) / 2); yc.append(P[1] + 0.076); zc.append(0.074); ay.append(0.056); az.append(0.064)
    for i in range(1, 7):                                   # L1 à L6
        P = sq.VERT[f"L{i}"][0]
        xs.append(P[0] + 0.01); yc.append(P[1] + 0.064); zc.append(0.074); ay.append(0.056); az.append(0.066)
    o = np.argsort(xs)
    return tuple(np.asarray(a, np.float32)[o] for a in (xs, yc, zc, ay, az))


def _au_plus_proche(sous, masque, permis):
    """Les voxels de « masque » encore libres prennent le muscle (parmi « permis ») le plus proche."""
    import scipy.ndimage as ndi
    cible = np.isin(sous, permis)
    if not cible.any():
        return
    _, idx = ndi.distance_transform_edt(~cible, return_indices=True)
    reste = masque & (sous == 0)
    sous[reste] = sous[tuple(i[reste] for i in idx)]


def decouper_aloyau(e):
    """Renvoie (sous, noms, fins) comme detail.decouper, plus les champs des nerfs dorsaux (nappes fines)."""
    import scipy.ndimage as ndi
    import squelette as sq
    lab, ids, cd = e["lab"], e["ids"], e["corps_d"]
    xs, ys, zs = e["axes"]
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    piece = {mid: lab == (ids.index(mid) + 1) for mid in PIECES_ALOYAU}
    sous = np.zeros(lab.shape, np.int16)
    noms, fins = [], {}

    def poser(nom, pc, masque):
        noms.append((nom, pc))
        sous[masque & (sous == 0)] = len(noms)
        return len(noms)

    nx, nyc, nzc, nay, naz = noix()
    yc = np.interp(xs, nx, nyc).astype(np.float32)[:, None, None]
    zc = np.interp(xs, nx, nzc).astype(np.float32)[:, None, None]
    ay = np.interp(xs, nx, nay).astype(np.float32)[:, None, None]
    az = np.interp(xs, nx, naz).astype(np.float32)[:, None, None]
    ell = np.sqrt(((Y - yc) / ay) ** 2 + ((Z - zc) / az) ** 2)
    dans_noix = ell < 1

    def nerf_dorsal(m, epaisseur=0.005):
        """Nappe nacrée sur le dessus de la noix (champ en m, négatif dedans)."""
        nappe = np.abs(ell - 1) * np.minimum(ay, az) - epaisseur / 2
        dessus = (yc + 0.1 * ay) - Y
        cote = Z - (zc + 0.85 * az)
        dans = (0.5 - ndi.gaussian_filter(m.astype(np.float32), 1.0)) * (2 * PAS)
        return np.maximum.reduce([nappe, dessus, cote, dans]).astype(np.float32)

    # l'aloyau est séparé du flanc par une coupe parallèle à la colonne, à 6 cm du bord de la noix (au-delà :
    # bavettes et flanchet, qui ne font pas partie de la pièce)
    x_t13 = float(sq.VERT["T13"][0][0])
    flanc = piece["faux-filet"] & (X > x_t13 + 0.02) & (Z > zc + az + 0.06)
    piece["faux-filet"] &= ~flanc
    region = np.zeros_like(lab, bool)
    for m in piece.values():
        region |= m
    poser(GRAS_ALOYAU, None, region & (cd > -epaisseur_gras_aloyau(X, Y, Z)))
    libre = sous == 0

    # --- train de côtes
    tc = piece["cotes-entrecotes"] & libre
    fins["tc-nerf"] = nerf_dorsal(tc)
    k0 = len(noms) + 1
    poser("tc-nerf", "cotes-entrecotes", tc & (fins["tc-nerf"] < 0))
    poser("tc-noix", "cotes-entrecotes", tc & dans_noix)
    # bretelles : le prolongement le long des côtes, en dehors et plus bas que la noix
    poser("tc-bretelle", "cotes-entrecotes", tc & (Z > zc + 0.9 * az) & (Y < yc + 0.2 * ay))
    poser("tc-dessus", "cotes-entrecotes", tc & ~dans_noix & ((Y > yc + 0.5 * ay) | (cd > -0.035)))
    _au_plus_proche(sous, tc, list(range(k0 + 1, len(noms) + 1)))

    # --- faux-filet
    ff = piece["faux-filet"] & libre
    fins["ff-nerf"] = nerf_dorsal(ff)
    k0 = len(noms) + 1
    poser("ff-nerf", "faux-filet", ff & (fins["ff-nerf"] < 0))
    poser("ff-coeur", "faux-filet", ff & dans_noix)
    poser("ff-chapeau", "faux-filet", ff & (X < x_t13 + 0.03) & (Y > yc))
    # bretelle : sur les 3 dernières côtes, le prolongement le long des côtes ; chaînette : le bord côté flanc
    poser("ff-bretelle", "faux-filet", ff & (X <= x_t13 + 0.02) & (Z > zc + 0.9 * az) & (Y < yc + 0.2 * ay))
    poser("ff-chainette", "faux-filet", ff & (Z > zc + 0.6 * az))
    _au_plus_proche(sous, ff, list(range(k0 + 1, len(noms) + 1)))

    # --- filet : par tranches le long de la colonne
    fi = piece["filet"] & libre
    ii = np.nonzero(fi)
    zmin = np.full(len(xs), np.nan, np.float32); zmed = zmin.copy(); ymed = zmin.copy()
    for i in np.unique(ii[0]):
        sel = ii[0] == i
        if sel.sum() < 8:
            continue
        zz, yy = zs[ii[2][sel]], ys[ii[1][sel]]
        zmin[i], zmed[i], ymed[i] = zz.min(), np.median(zz), np.median(yy)
    ok = np.isfinite(zmin)
    k = np.arange(len(xs))
    zmin, zmed, ymed = (np.interp(k, k[ok], a[ok]).astype(np.float32)[:, None, None] for a in (zmin, zmed, ymed))
    poser("fi-chainette", "filet", fi & (Z < zmin + 0.013) & (Y > ymed))
    poser("fi-aile", "filet", fi & (X > 0.6) & (Z > zmed + 0.006))
    poser("fi-tete", "filet", fi & (X > 0.52))
    poser("fi-coeur", "filet", fi & (X > 0.24))
    poser("fi-queue", "filet", fi)

    # nettoyage : un seul bloc par muscle ; les miettes vont au muscle voisin
    for k_, (nom, pc) in enumerate(noms, start=1):
        m = sous == k_
        if not m.any():
            raise ValueError(f"muscle {nom} vide")
        cc, ncc = ndi.label(m)
        if ncc > 1:
            t = ndi.sum(m, cc, range(1, ncc + 1))
            sous[m & (cc != 1 + int(np.argmax(t)))] = -1
    orphelin = sous == -1
    for _ in range(40):
        if not orphelin.any():
            break
        for ax in range(3):
            for s in (1, -1):
                vv = np.roll(sous, s, axis=ax)
                pris = orphelin & (vv > 0)
                sous[pris] = vv[pris]
                orphelin &= ~pris
    sous[sous < 0] = 0
    for k_, (nom, pc) in enumerate(noms, start=1):
        print(f"   {nom:16s} {float((sous == k_).sum() * PAS ** 3 * 1000):6.2f} L", flush=True)
    return sous, noms, fins


def reperes_aloyau():
    """Points nommés des vertèbres et des côtes, posés sur le sommet le plus proche de l'os en haute
    définition, du côté gauche (z ≥ 0 : la moitié droite des vertèbres est sciée)."""
    import os
    import squelette as sq
    from sdf import courbe
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    V = {}
    for oid in OS_HD_ALOYAU:
        v = np.load(os.path.join(racine, "outils", "cache", "anatomie", f"hd-{oid}.npz"))["v"]
        V[oid] = v[v[:, 2] > 0.004]

    def sur(oid, P):
        v = V[oid]
        i = int(np.argmin(((v - np.asarray(P, float)) ** 2).sum(1)))
        return [round(float(x), 4) for x in v[i]]

    def le_plus(oid, pres, critere):
        v = V[oid]
        sel = v[pres(v)]
        return sel[np.argmax(critere(sel))]
    P8 = sq.VERT["T8"][0]
    P9, T9, L9 = sq.VERT["T9"]
    u, v_, w = sq.repere_vertebre(P9, T9)
    L3 = sq.VERT["L3"][0]
    L4 = sq.VERT["L4"][0]
    os_pts, _ = sq._ribs()[7]                                  # 8e côte
    c = courbe(os_pts, n=30)
    milieu = c[np.argmin(np.abs(c[:, 1] - (c[0, 1] + Y_SCIE) / 2))]
    return {
        "dorsales": [
            ("t-processus-spinosus", sur("dorsales", np.array([*sq.EPINES_DORS[7], 0.01]))),     # pointe (x, y) de T8
            ("t-corpus", sur("dorsales", P9 + np.array([0.0, -0.02, 0.03]))),
            ("t-processus-transversus", sur("dorsales", P9 + np.array([0.0, 0.03, 0.07]))),
            ("t-fovea-costalis", sur("dorsales", P9 - u * L9 * 0.5 + v_ * 0.008 + w * 0.02)),
            ("canalis-vertebralis", sur("dorsales", P8 + np.array([0.0, 0.03, 0.006]))),
        ],
        "lombaires": [
            ("l-processus-transversus", [round(float(x), 4) for x in le_plus(
                "lombaires", lambda a: np.abs(a[:, 0] - L3[0]) < 0.03, lambda a: a[:, 2])]),
            ("l-processus-spinosus", [round(float(x), 4) for x in le_plus(
                "lombaires", lambda a: np.abs(a[:, 0] - L3[0]) < 0.03, lambda a: a[:, 1])]),
            ("l-corpus", sur("lombaires", L3 + np.array([0.0, -0.03, 0.03]))),
            ("l-processus-mamillaris", sur("lombaires", L4 + np.array([0.01, 0.055, 0.035]))),
        ],
        "cotes": [
            ("caput-costae", sur("cotes", os_pts[0])),
            ("tuberculum-costae", sur("cotes", os_pts[0] + sq.p3(0.004, 0.012, 0.03))),
            ("corpus-costae", sur("cotes", milieu + np.array([0.0, 0.0, 0.02]))),
        ],
    }
