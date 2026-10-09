# Atelier : l'épaule du bœuf, muscle par muscle (appelé par « python outils/detail.py epaule »).
#
# L'épaule « levée » (détachée de la cage thoracique) comprend, d'après le classeur et l'affiche Interbev
# « Découpe de l'avant » : le paleron, le dessus de palette (surprise et merlan d'épaule), le jumeau à
# bifteck, la macreuse à bifteck (boule de macreuse), la macreuse à pot-au-feu (à braiser), le jumeau à
# pot-au-feu et le gîte (jarret avant), autour de la palette, de l'humérus et du radius-cubitus.
#
# Repère de la palette (squelette.repere_palette) : u le long de l'os, de la cavité glénoïde (u = 0) vers le
# bord dorsal (u ≈ 0,45 m) ; v vers l'avant (v > 0 : fosse de devant, au-dessus de l'arête) ; w vers
# l'extérieur (w < 0 : face interne, collée aux côtes).
#   - paleron = fosse de derrière l'arête (muscle infra-épineux), coupé en deux par son NERF CENTRAL (nappe
#     parallèle à l'os, au milieu de l'épaisseur) ; le « derrière de paleron » est la partie qui reste avec
#     le cartilage de la palette ;
#   - jumeau à bifteck = fosse de devant (muscle sus-épineux), avec son nerf central (ruban dans la longueur) ;
#   - dessus de palette = face interne de la palette : merlan d'épaule le long du bord arrière, surprise sur
#     le reste de la face ;
#   - macreuse à bifteck = dessous (la boule), dessus de boule (vers la palette) et petit muscle latéral.
# Placement simplifié, d'après les os : À FAIRE VALIDER par un formateur.
import numpy as np

PAS = 0.004
PIECES_EPAULE = ["paleron", "jumeau-a-bifteck", "macreuse-a-bifteck", "macreuse-a-pot-au-feu", "jumeau-a-pot-au-feu",
                 "gite-avant"]
# morceaux de l'étiquetage qui occupent la face interne de la palette (on y prend le dessus de palette)
VOISINS = ["basses-cotes", "collier", "cotes-entrecotes", "plat-de-cotes"]
OS_HD_EPAULE = {"palette": 30000, "humerus": 20000, "radius": 22000}
GRAS_EPAULE = "gras-epaule"


def epaisseur_gras_epaule(X, Y, Z):
    """Gras de couverture : 8 mm sur le jarret, jusqu'à 1,5 cm sur le haut de l'épaule."""
    return 0.008 + 0.007 * np.clip((Y - 0.75) / 0.45, 0, 1)


def repere():
    """Repère de la palette, pose de la planche, longueur de l'os, contour et bords en (u, v)."""
    import squelette as sq
    from planches_os import os_planche
    from sdf import Placement
    R = sq.repere_palette()
    d = os_planche("palette")
    rp = d["reperes"]
    G_p = np.asarray(rp["glene"], float)
    D_p = (np.asarray(rp["angle_cranial"], float) + np.asarray(rp["angle_caudal"], float)) / 2
    pose = Placement(G_p, D_p, sq.GLENE, sq.DOS_PAL, normale=R.W)

    def uv(q):
        P = pose.vers_modele(*q)
        return np.array([(P - R.O) @ R.U, (P - R.O) @ R.V])
    L = float(np.linalg.norm(sq.DOS_PAL - sq.GLENE))
    return {"R": R, "pose": pose, "L": L, "rp": rp,
            "contour": np.array([uv(q) for q in d["contour"]]),
            "caudal": np.array([uv(q) for q in rp["bord_caudal"]]),
            "cranial": np.array([uv(q) for q in rp["bord_cranial"]]),
            "epine": np.array([uv(q) for q in rp["epine"]])}


def _raster_uv(rep, pas=0.002):
    """Cartes 2D dans le plan de la palette : distance au bord de l'os (dedans) et au bord arrière."""
    import scipy.ndimage as ndi
    from skimage.measure import points_in_poly
    u0, v0 = -0.08, -0.40
    nu, nv = int(0.64 / pas), int(0.75 / pas)
    U, V = np.meshgrid(u0 + np.arange(nu) * pas, v0 + np.arange(nv) * pas, indexing="ij")
    dedans = points_in_poly(np.stack([U.ravel(), V.ravel()], 1), rep["contour"]).reshape(nu, nv)
    d_bord = ndi.distance_transform_edt(dedans) * pas
    trait = np.zeros((nu, nv), bool)
    c = rep["caudal"]
    for a, b in zip(c[:-1], c[1:]):
        for t in np.linspace(0, 1, 60):
            p = a + t * (b - a)
            i, j = int(round((p[0] - u0) / pas)), int(round((p[1] - v0) / pas))
            if 0 <= i < nu and 0 <= j < nv:
                trait[i, j] = True
    d_caudal = ndi.distance_transform_edt(~trait) * pas

    def lire(carte, u, v):
        return ndi.map_coordinates(carte, [(u - u0) / pas, (v - v0) / pas], order=1, mode="nearest")
    return lambda u, v: (lire(d_bord, u, v), lire(d_caudal, u, v))


def _colonnes(m, u, v, w, pas=0.008, lisse=1.5):
    """Pour le muscle m : milieu et épaisseur de chaque colonne perpendiculaire à la palette (le long de w),
    lissés, lus en chaque voxel de la grille (fonctions continues de u et v)."""
    import scipy.ndimage as ndi
    uu, vv, ww = u[m], v[m], w[m]
    u0, v0 = float(uu.min()) - 2 * pas, float(vv.min()) - 2 * pas
    iu = ((uu - u0) / pas).astype(int)
    iv = ((vv - v0) / pas).astype(int)
    nu, nv = int(iu.max()) + 3, int(iv.max()) + 3
    lo = np.full((nu, nv), np.inf)
    hi = np.full((nu, nv), -np.inf)
    np.minimum.at(lo, (iu, iv), ww)
    np.maximum.at(hi, (iu, iv), ww)
    ok = np.isfinite(lo)
    lo, hi = np.where(ok, lo, 0.0), np.where(ok, hi, 0.0)
    k = np.maximum(ndi.gaussian_filter(ok.astype(float), lisse), 1e-6)
    mil = ndi.gaussian_filter(np.where(ok, (lo + hi) / 2, 0.0), lisse) / k
    ep = ndi.gaussian_filter(np.where(ok, hi - lo, 0.0), lisse) / k
    ep[~ok] = 0.0
    coord = [(u - u0) / pas - 0.5, (v - v0) / pas - 0.5]
    return (ndi.map_coordinates(mil, coord, order=1, mode="nearest").astype(np.float32),
            ndi.map_coordinates(ep, coord, order=1, mode="constant", cval=0.0).astype(np.float32))


def _nerf(m, u, v, w, epaisseur, garde):
    """Champ (m, négatif dedans) d'une nappe au milieu de l'épaisseur du muscle m, parallèle à la palette :
    c'est par là qu'on ouvre le muscle en deux pour lever le nerf. « garde » (négatif = permis) la borne."""
    import scipy.ndimage as ndi
    mil, ep = _colonnes(m, u, v, w)
    nappe = np.abs(w - mil) - epaisseur / 2
    epais = 0.03 - ep                                    # pas sur les bords minces du muscle
    dans = (0.5 - ndi.gaussian_filter(m.astype(np.float32), 1.0)) * (2 * PAS)
    return np.maximum.reduce([nappe, epais, dans, garde]).astype(np.float32), mil


def decouper_epaule(e):
    """Renvoie (sous, noms, fins) comme detail.decouper, plus les champs des nerfs (nappes fines)."""
    import scipy.ndimage as ndi
    lab, ids, cd, os_occ = e["lab"], e["ids"], e["corps_d"], e["os_occ"]
    xs, ys, zs = e["axes"]
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    rep = repere()
    R, L = rep["R"], rep["L"]
    O = R.O.astype(np.float32)
    u = (X - O[0]) * R.U[0] + (Y - O[1]) * R.U[1] + (Z - O[2]) * R.U[2]
    v = (X - O[0]) * R.V[0] + (Y - O[1]) * R.V[1] + (Z - O[2]) * R.V[2]
    w = (X - O[0]) * R.W[0] + (Y - O[1]) * R.W[1] + (Z - O[2]) * R.W[2]
    u, v, w = (a.astype(np.float32) for a in (u, v, w))
    piece = {mid: lab == (ids.index(mid) + 1) for mid in PIECES_EPAULE}
    # paleron et jumeau à bifteck : départagés par l'arête (l'épine) de la palette, prolongée jusqu'à
    # l'épaule. La face externe de la palette est « divisée par l'épine en une petite fosse crâniale (muscle
    # sus-épineux) et une grande fosse caudale (muscle infra-épineux) » (IMAIOS). muscles.py applique la même
    # règle (squelette.cote_epine) ; on la redit ici pour que l'atelier la garantisse quel que soit l'étiquetage.
    ep_uv = rep["epine"][np.argsort(rep["epine"][:, 0])]
    v_epine = np.interp(u, ep_uv[:, 0], ep_uv[:, 1]).astype(np.float32)
    pj = piece["paleron"] | piece["jumeau-a-bifteck"]
    piece["paleron"] = pj & (v <= v_epine)
    piece["jumeau-a-bifteck"] = pj & (v > v_epine)
    voisin = np.isin(lab, [ids.index(m) + 1 for m in VOISINS if m in ids])
    sous = np.zeros(lab.shape, np.int16)
    noms = []
    fins = {}

    def poser(nom, pc, masque):
        noms.append((nom, pc))
        sous[masque & (sous == 0)] = len(noms)

    # --- dessus de palette : face interne de la palette (pris aux voisins de l'étiquetage)
    plan = _raster_uv(rep)
    ii = np.nonzero((w < 0.01) & (w > -0.07) & (u > -0.02) & (u < L + 0.02) & (np.abs(v) < 0.35))
    d_bord = np.full(lab.shape, -1.0, np.float32)
    d_caud = np.full(lab.shape, 9.0, np.float32)
    a, b = plan(u[ii], v[ii])
    d_bord[ii], d_caud[ii] = a, b
    # merlan d'épaule : le long du bord arrière, sur la face interne (et un peu au-delà du bord)
    merlan = ((voisin | piece["macreuse-a-bifteck"]) & (w < -0.003) & (w > -0.04) & (d_caud < 0.03)
              & (u > 0.12) & (u < L - 0.04))
    # surprise : le reste de la face interne, plus épaisse au milieu de la fosse
    surprise = (voisin & (d_bord > 0.004) & (w < -0.003) & (w > -(0.012 + 0.8 * np.minimum(d_bord, 0.04)))
                & (u > 0.03) & (u < L - 0.05))
    epaule = surprise | merlan
    for m in piece.values():
        epaule |= m

    # --- gras de couverture, sous la peau de l'épaule
    gras = epaule & (cd > -epaisseur_gras_epaule(X, Y, Z))
    poser(GRAS_EPAULE, None, gras)
    libre = ~gras

    # --- paleron : derrière de paleron (avec le cartilage), nerf central, deux moitiés de part et d'autre
    pal = piece["paleron"] & libre
    derriere = pal & (u > L - 0.075)
    corps_pal = pal & ~derriere
    ep_nerf = 0.004 + 0.007 * np.clip((0.30 - u) / 0.22, 0, 1)        # s'épaissit vers l'épaule (le « talon »)
    garde = np.maximum(0.07 - u, u - (L - 0.09))
    champ, mil = _nerf(corps_pal, u, v, w, ep_nerf, garde)
    fins["pal-nerf"] = champ
    poser("pal-nerf", "paleron", corps_pal & (champ < 0))
    poser("pal-cote-os", "paleron", corps_pal & (w <= mil))
    poser("pal-exterieur", "paleron", corps_pal)
    poser("pal-derriere", "paleron", derriere)
    del champ, mil

    # --- dessus de palette
    poser("dp-merlan", "paleron", merlan & libre)
    poser("dp-surprise", "paleron", surprise & libre)

    # --- jumeau à bifteck : nerf central en ruban dans la longueur, au milieu de la largeur
    jb = piece["jumeau-a-bifteck"] & libre
    iu = np.clip(((u[jb] + 0.05) / 0.02).astype(int), 0, 40)
    vmid = np.array([np.median(v[jb][iu == k]) if (iu == k).sum() > 20 else np.nan for k in range(41)])
    ok = np.isfinite(vmid)
    vmid = np.interp(np.arange(41), np.where(ok)[0], vmid[ok])
    vm = np.interp((u + 0.05) / 0.02, np.arange(41), vmid).astype(np.float32)
    garde = np.maximum.reduce([0.06 - u, u - (L - 0.06), np.abs(v - vm) - 0.022])
    champ, _ = _nerf(jb, u, v, w, np.float32(0.006), garde)
    fins["jb-nerf"] = champ
    poser("jb-nerf", "jumeau-a-bifteck", jb & (champ < 0))
    poser("jumeau-a-bifteck", "jumeau-a-bifteck", jb)
    del champ

    # --- macreuse à bifteck : petit muscle latéral (côté coude, à l'extérieur), dessus de boule (vers la
    #     palette), dessous de macreuse (la boule)
    mb = piece["macreuse-a-bifteck"] & libre
    w_lat = np.percentile(w[mb & (u < 0.10)], 70)
    poser("mb-lateral", "macreuse-a-bifteck", mb & (u < 0.10) & (w > w_lat))
    poser("mb-dessus", "macreuse-a-bifteck", mb & (u > 0.16))
    poser("mb-dessous", "macreuse-a-bifteck", mb)

    for mid in ("macreuse-a-pot-au-feu", "jumeau-a-pot-au-feu", "gite-avant"):
        poser(mid, mid, piece[mid] & libre)

    # nettoyage : un seul bloc par muscle ; les miettes vont au muscle voisin
    for k, (nom, pc) in enumerate(noms, start=1):
        m = sous == k
        if not m.any():
            raise ValueError(f"muscle {nom} vide")
        cc, ncc = ndi.label(m)
        if ncc > 1:
            t = ndi.sum(m, cc, range(1, ncc + 1))
            garde_ = cc == (1 + int(np.argmax(t)))
            sous[m & ~garde_] = -1
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
    for k, (nom, pc) in enumerate(noms, start=1):
        print(f"   {nom:22s} {float((sous == k).sum() * PAS ** 3 * 1000):6.2f} L", flush=True)
    return sous, noms, fins


def reperes_epaule(os_=None):
    """Points nommés des os de l'épaule (côté gauche), posés sur le sommet le plus proche de l'os en haute
    définition (outils/cache/anatomie/hd-<os>.npz)."""
    import os
    import squelette as sq
    from planches_os import os_planche
    from sdf import Placement, courbe
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    V = {oid: np.load(os.path.join(racine, "outils", "cache", "anatomie", f"hd-{oid}.npz"))["v"] for oid in OS_HD_EPAULE}
    rep = repere()
    R, pose, rp, L = rep["R"], rep["pose"], rep["rp"], rep["L"]

    def sur(oid, P):
        v = V[oid]
        i = int(np.argmin(((v - np.asarray(P)) ** 2).sum(1)))
        return [round(float(x), 4) for x in v[i]]

    def milieu(polyA, polyB, uu):
        """v à mi-chemin entre deux bords (polylignes en (u, v)) à la hauteur uu."""
        va = np.interp(uu, *polyA[np.argsort(polyA[:, 0])].T)
        vb = np.interp(uu, *polyB[np.argsort(polyB[:, 0])].T)
        return (va + vb) / 2
    ep = courbe([pose.vers_modele(*q) for q in rp["epine"]], n=18)
    W = R.W
    out = {"palette": [
        ("cavitas-glenoidalis", sur("palette", sq.GLENE - R.U * 0.04)),
        ("tuberculum-supraglenoidale", sur("palette", sq.GLENE + R.U * 0.028 + R.V * 0.045)),
        ("collum-scapulae", sur("palette", sq.GLENE + R.U * 0.07 + W * 0.03)),
        ("acromion", sur("palette", ep[1] + W * 0.04)),
        ("tuber-spinae", sur("palette", ep[7] + W * 0.06)),
        ("spina-scapulae", sur("palette", ep[11] + W * 0.05)),
        ("fossa-supraspinata", sur("palette", R.point(0.25, milieu(rep["epine"], rep["cranial"], 0.25), 0.03))),
        ("fossa-infraspinata", sur("palette", R.point(0.25, milieu(rep["epine"], rep["caudal"], 0.25), 0.03))),
        ("fossa-subscapularis", sur("palette", R.point(0.24, milieu(rep["cranial"], rep["caudal"], 0.24), -0.04))),
        ("margo-caudalis", sur("palette", pose.vers_modele(*rp["bord_caudal"][2]) - R.V * 0.02)),
        ("angulus-cranialis", sur("palette", pose.vers_modele(*rp["angle_cranial"]))),
        ("angulus-caudalis", sur("palette", pose.vers_modele(*rp["angle_caudal"]))),
        ("cartilago-scapulae", sur("palette", sq.DOS_PAL + R.U * 0.03)),
    ]}
    # humérus
    vh = V["humerus"]
    A, B = sq.HUM_TETE, sq.COUDE
    ax = (B - A) / np.linalg.norm(B - A)
    t = (vh - A) @ ax / np.linalg.norm(B - A)
    pres = np.linalg.norm(vh - A, axis=1) < 0.09
    tub = vh[pres][np.argmax(-vh[pres, 0] + 0.5 * vh[pres, 1] + 0.3 * vh[pres, 2])]
    bande = (t > 0.3) & (t < 0.5)
    delt = vh[bande][np.argmax(vh[bande, 2])]
    d = os_planche("humerus")["reperes"]
    ph = Placement(d["tete"], d["coude"], A, B, normale=(0, 0, 1))
    out["humerus"] = [
        ("caput-humeri", sur("humerus", sq.GLENE)),
        ("tuberculum-majus", sur("humerus", tub)),
        ("tuberositas-deltoidea", sur("humerus", delt)),
        ("corpus-humeri", sur("humerus", A + (B - A) * 0.62 + np.array([0.0, 0.0, 0.05]))),
        ("condylus-humeri", sur("humerus", B + np.array([0.0, -0.02, 0.05]))),
        ("fossa-olecrani", sur("humerus", B - ph.U * 0.03 - ph.V * 0.03)),
    ]
    # radius, cubitus et carpe
    vr = V["radius"]
    haut = vr[:, 1] > B[1] - 0.08
    olec = vr[haut][np.argmax(vr[haut, 0] + 0.5 * vr[haut, 1])]
    C = sq.CARPE
    tr = (vr - B) @ ((C - B) / np.linalg.norm(C - B)) / np.linalg.norm(C - B)
    mi = (tr > 0.45) & (tr < 0.55)
    corps_r = vr[mi][np.argmin(vr[mi, 0])]
    ul = (tr > 0.22) & (tr < 0.32)
    corps_u = vr[ul][np.argmax(vr[ul, 0])]
    carpe = (vr[:, 1] < C[1] + 0.01) & (vr[:, 1] > C[1] - 0.05)
    acc = vr[carpe][np.argmax(vr[carpe, 0])]
    out["radius"] = [
        ("tuber-olecrani", sur("radius", olec)),
        ("caput-radii", sur("radius", B + np.array([-0.03, -0.045, 0.0]))),
        ("corpus-radii", sur("radius", corps_r)),
        ("corpus-ulnae", sur("radius", corps_u)),
        ("ossa-carpi", sur("radius", (C + sq.CANON_AV_HAUT) / 2 + np.array([-0.04, 0.0, 0.0]))),
        ("os-carpi-accessorium", sur("radius", acc)),
    ]
    return out
