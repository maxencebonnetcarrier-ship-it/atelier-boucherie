# Atelier : le collier, les basses côtes et la poitrine du bœuf (« python outils/detail.py avant »), avec le
# plat de côtes qui couvre les côtes entre les deux. C'est l'avant une fois l'épaule levée.
#
# D'après le classeur (tableau n° 1, fiches magasin, guide de découpe) :
#   - collier, autour des 7 vertèbres du cou : salière (contre les 2 premières), saignée, griffe (partie
#     externe), veine maigre, veine grasse ;
#   - basses côtes, sur les 5 premières dorsales : surlonge (sur les 2 premières côtes), entrecôtes
#     découvertes (sur les 3 côtes suivantes), pièce parée ; « sans nerf cervical » (le ligament de la nuque) ;
#   - plat de côtes : découvert (5 côtes), couvert (5 côtes), bavettes à pot-au-feu (3 côtes) ;
#   - poitrine : gros bout (2 premières sternèbres, 2 cartilages), milieu de poitrine (5 sternèbres,
#     4 cartilages), tendron (4 cartilages).
# Le numéro de côte d'un point se lit à sa hauteur : les côtes sont penchées. Placement des parties que les
# sources ne situent pas (saignée, griffe, veines, pièce parée) : approximatif, À FAIRE VALIDER.
# Os : les 7 cervicales, les dorsales 1 à 5 (le garrot), fendues au milieu ; les côtes 1 à 5 entières et le
# bas des côtes 6 à 13 (sous le trait de scie de l'aloyau) ; le sternum, fendu.
import numpy as np

PAS = 0.004
PIECES_AVANT = ["collier", "basses-cotes", "plat-de-cotes", "gros-bout-de-poitrine", "tendron"]
GRAS_AVANT = "gras-avant"
OS_HD_AVANT = {"cervicales": 26000, "dorsales-garrot": 22000, "cotes-panneau": 30000, "sternum": 12000}


def _garrot():
    import squelette as sq
    return sq.dorsales(premiere=1, derniere=5)


def _panneau():
    """Côtes 1 à 5 entières, et le bas des côtes 6 à 13 (le haut part avec l'aloyau et le train de côtes)."""
    import squelette as sq
    from aloyau import Y_SCIE
    f = sq.cotes(premiere=6, derniere=13, sciees_a=Y_SCIE, garder="bas")
    f.ops.extend(sq.cotes(premiere=1, derniere=5).ops)
    return f


FORMES_OS = {"dorsales-garrot": (_garrot, False), "cotes-panneau": (_panneau, True)}


def epaisseur_gras_avant(X, Y, Z):
    """Gras de couverture : 1,2 cm sur le cou et la poitrine, jusqu'à 1,8 cm sur le garrot (la viande commence à
    6 mm sous la peau : en dessous de 1 cm, la couche ne tient pas dans la grille de 4 mm)."""
    return 0.012 + 0.006 * np.clip((Y - 1.2) / 0.2, 0, 1)


def numero_cote(X, Y):
    """Numéro de côte (réel, 1 à 13) à la hauteur de chaque point : 1,5 = entre la 1re et la 2e côte. Les
    côtes sont penchées ; au-dessus de leur tête on garde la position de la tête, sous leur bas celle du bas."""
    import squelette as sq
    from sdf import courbe
    ys = np.linspace(0.5, 1.6, 111)
    xs = []
    for os_pts, _ in sq._ribs():
        c = courbe(os_pts, n=40)
        o = np.argsort(c[:, 1])
        xs.append(np.interp(ys, c[o, 1], c[o, 0]))
    xs = np.array(xs, np.float32)                             # (13, len(ys)) : x de chaque côte à chaque hauteur
    Xf, Yf = X.ravel(), Y.ravel()
    n = np.empty(Xf.size, np.float32)
    for s0 in range(0, Xf.size, 1_000_000):                   # par paquets, pour la mémoire
        s = slice(s0, s0 + 1_000_000)
        j = np.clip(np.round((Yf[s] - ys[0]) / (ys[1] - ys[0])).astype(int), 0, len(ys) - 1)
        n[s] = _interp_lignes(Xf[s], xs[:, j])
    return n.reshape(X.shape)


def _interp_lignes(x, c):
    """Interpolation, colonne par colonne, de x dans les abscisses croissantes c[:, i] -> 1..13."""
    k = (c < x[None, :]).sum(0)                               # nombre de côtes devant le point
    k = np.clip(k, 1, 12)
    a, b = c[k - 1, np.arange(len(x))], c[k, np.arange(len(x))]
    t = np.clip((x - a) / np.maximum(b - a, 1e-6), -0.5, 1.5)
    return (k + t).astype(np.float32)


def _au_plus_proche(sous, masque, permis):
    import scipy.ndimage as ndi
    cible = np.isin(sous, permis)
    if not cible.any():
        return
    _, idx = ndi.distance_transform_edt(~cible, return_indices=True)
    reste = masque & (sous == 0)
    sous[reste] = sous[tuple(i[reste] for i in idx)]


def _ligne(points, X, Y, Z, rayon):
    """Masque des points à moins de « rayon » d'une ligne brisée (le ligament de la nuque)."""
    d = np.full(X.shape, np.inf, np.float32)
    for a, b in zip(points[:-1], points[1:]):
        a, b = np.asarray(a, np.float32), np.asarray(b, np.float32)
        ab = b - a
        t = np.clip(((X - a[0]) * ab[0] + (Y - a[1]) * ab[1] + (Z - a[2]) * ab[2]) / float(ab @ ab), 0, 1)
        dd = np.sqrt((X - a[0] - t * ab[0]) ** 2 + (Y - a[1] - t * ab[1]) ** 2 + (Z - a[2] - t * ab[2]) ** 2)
        d = np.minimum(d, dd)
    return d < rayon


def decouper_avant(e):
    """Renvoie (sous, noms, fins) comme detail.decouper."""
    import scipy.ndimage as ndi
    import squelette as sq
    lab, ids, cd = e["lab"], e["ids"], e["corps_d"]
    xs, ys, zs = e["axes"]
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    piece = {mid: lab == (ids.index(mid) + 1) for mid in PIECES_AVANT}
    sous = np.zeros(lab.shape, np.int16)
    noms = []

    def poser(nom, pc, masque):
        noms.append((nom, pc))
        sous[masque & (sous == 0)] = len(noms)
        return len(noms)

    region = np.zeros_like(lab, bool)
    for m in piece.values():
        region |= m
    poser(GRAS_AVANT, None, region & (cd > -epaisseur_gras_avant(X, Y, Z)))
    libre = sous == 0
    cote = numero_cote(X, Y)
    V = sq.VERT

    # --- nerf cervical : le ligament de la nuque, sur la pointe des épines du garrot et le haut du cou
    tips = [np.array([*sq.EPINES_DORS[i], 0.008]) + np.array([0.0, 0.012, 0.0]) for i in range(4, -1, -1)]
    cou = [V[f"C{i}"][0] + np.array([0.0, 0.13 - 0.008 * (7 - i), 0.008]) for i in (7, 5, 3)]
    nerf = _ligne(tips + cou, X, Y, Z, 0.016) & (piece["basses-cotes"] | piece["collier"]) & libre
    poser("bc-nerf", "basses-cotes", nerf)

    # --- basses côtes : surlonge (côtes 1-2), entrecôtes découvertes (3-5) ; pièce parée sur le côté, sous
    #     la place de la palette (« derrière de paleron »)
    bc = piece["basses-cotes"] & libre
    k0 = len(noms) + 1
    poser("bc-piece-paree", "basses-cotes", bc & (Z > 0.13) & (Y < 1.3))
    poser("bc-surlonge", "basses-cotes", bc & (cote < 2.5))
    poser("bc-entrecotes", "basses-cotes", bc)

    # --- collier : salière contre l'atlas et l'axis, saignée en dessous du cou côté tête, griffe en surface
    #     sur le côté, veine grasse au-dessus des vertèbres, veine maigre autour
    co = piece["collier"] & libre
    x_c2 = float(V["C2"][0][0]) + 0.04
    yv = np.interp(xs, [float(V[f"C{i}"][0][0]) for i in range(1, 8)], [float(V[f"C{i}"][0][1]) for i in range(1, 8)])
    yv = yv.astype(np.float32)[:, None, None]
    poser("col-saliere", "collier", co & (X < x_c2) & (Y > yv - 0.03))
    poser("col-saignee", "collier", co & (Y < yv - 0.09) & (X < -0.85))
    poser("col-griffe", "collier", co & (cd > -0.035) & (Z > 0.1) & (Y >= yv - 0.09))
    poser("col-veine-grasse", "collier", co & (Y > yv + 0.07))
    poser("col-veine-maigre", "collier", co)

    # --- plat de côtes : découvert (côtes 1 à 5), couvert (6 à 10), bavettes à pot-au-feu (11 à 13)
    pc = piece["plat-de-cotes"] & libre
    poser("pc-decouvert", "plat-de-cotes", pc & (cote < 5.5))
    poser("pc-couvert", "plat-de-cotes", pc & (cote < 10.5))
    poser("pc-bavettes", "plat-de-cotes", pc)

    # --- poitrine : gros bout ; milieu de poitrine sur le sternum ; tendron derrière, sur les cartilages
    poser("gros-bout-de-poitrine", "gros-bout-de-poitrine", piece["gros-bout-de-poitrine"] & libre)
    td = piece["tendron"] & libre
    x_fin_sternum = float(sq.X_STERNEBRES[-1]) + 0.04
    poser("po-milieu", "tendron", td & (X < x_fin_sternum))
    poser("po-tendron", "tendron", td)

    # nettoyage : un seul bloc par muscle ; les miettes vont au muscle voisin
    for k_, (nom, pc_) in enumerate(noms, start=1):
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
    for k_, (nom, pc_) in enumerate(noms, start=1):
        print(f"   {nom:22s} {float((sous == k_).sum() * PAS ** 3 * 1000):6.2f} L", flush=True)
    return sous, noms, {}


def reperes_avant():
    """Points nommés des vertèbres du cou et du garrot, des côtes et du sternum, posés sur le sommet le plus
    proche de l'os en haute définition, du côté gauche (z ≥ 0)."""
    import os
    import squelette as sq
    from sdf import courbe
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    V = {}
    for oid in OS_HD_AVANT:
        v = np.load(os.path.join(racine, "outils", "cache", "anatomie", f"hd-{oid}.npz"))["v"]
        V[oid] = v[v[:, 2] > 0.004]
    r4 = lambda P: [round(float(x), 4) for x in P]

    def sur(oid, P):
        v = V[oid]
        return r4(v[int(np.argmin(((v - np.asarray(P, float)) ** 2).sum(1)))])

    def le_plus(oid, pres, critere):
        v = V[oid]
        sel = v[pres(v)]
        return r4(sel[np.argmax(critere(sel))])
    VT = sq.VERT
    c1, c2, c4, c5 = (VT[f"C{i}"][0] for i in (1, 2, 4, 5))
    t3 = VT["T3"][0]
    cote1, _ = sq._ribs()[0]
    c = courbe(cote1, n=30)
    _, cart9 = sq._ribs()[8]
    _, cart11 = sq._ribs()[10]
    return {
        "cervicales": [
            ("atlas", le_plus("cervicales", lambda a: np.abs(a[:, 0] - c1[0]) < 0.03, lambda a: a[:, 2])),
            ("axis", le_plus("cervicales", lambda a: np.abs(a[:, 0] - c2[0]) < 0.03, lambda a: a[:, 1])),
            ("c-processus-transversus", le_plus("cervicales", lambda a: np.abs(a[:, 0] - c4[0]) < 0.03, lambda a: a[:, 2])),
            ("c-corpus", sur("cervicales", c5 + np.array([0.0, -0.03, 0.02]))),
        ],
        "dorsales-garrot": [
            ("garrot", sur("dorsales-garrot", np.array([*sq.EPINES_DORS[2], 0.01]))),
            ("g-corpus", sur("dorsales-garrot", t3 + np.array([0.0, -0.02, 0.03]))),
        ],
        "cotes-panneau": [
            ("costa-prima", sur("cotes-panneau", c[len(c) // 2] + np.array([0.0, 0.0, 0.02]))),
            ("cartilago-costalis", sur("cotes-panneau", courbe(cart9, n=12)[6])),
            ("arcus-costalis", sur("cotes-panneau", courbe(cart11, n=12)[-1])),
        ],
        "sternum": [
            ("manubrium-sterni", le_plus("sternum", lambda a: np.ones(len(a), bool), lambda a: -a[:, 0])),
            ("sternebrae", sur("sternum", np.array([float(sq.X_STERNEBRES[3]), sq.Y_STERNUM - 0.03, 0.02]))),
            ("processus-xiphoideus", le_plus("sternum", lambda a: np.ones(len(a), bool), lambda a: a[:, 0])),
        ],
    }
