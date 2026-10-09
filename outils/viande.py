# Morceaux de viande du bœuf en volume, qui REMPLISSENT la carcasse (côté gauche ; l'appli fait le droit
# par symétrie).
#
# 1. La viande = tout ce qui est sous la peau (6 mm), hors des os (2 mm d'écart) et hors des cavités :
#    la cage thoracique (en dedans des côtes, au-dessus du sternum) et le ventre (en dedans d'une paroi de
#    4 à 5 cm) sont creux, comme sur une carcasse. La tête, le bas des pattes (sous le carpe et le jarret)
#    et la queue n'en font pas partie, sauf les muscles modelés de la tête (joue, langue).
# 2. Les volumes de outils/muscles.py servent de GERMES, à leur place anatomique ; chacun s'étend dans la
#    viande, de proche en proche (sans traverser un os ni une cavité), jusqu'à rencontrer ses voisins.
#    Les morceaux se touchent donc comme sur une carcasse, séparés par une fine ligne (le « raccord »
#    que suit le couteau).
# 3. Chaque morceau devient une surface lissée et allégée, avec son ombrage dans les creux.
import time

import numpy as np

PAS = 0.006
# muscles logés contre une cavité (sous les lombaires, sur le diaphragme) : gardés à leur volume modelé
INTERNES = ("filet", "onglet", "hampe")
RACCORD = 0.56          # seuil de la surface (0.5 = morceaux jointifs ; un peu plus = fine séparation)


def _grille():
    xs = np.arange(-1.62, 1.12, PAS, dtype=np.float32)
    ys = np.arange(0.40, 1.58, PAS, dtype=np.float32)
    zs = np.arange(0.0, 0.47, PAS, dtype=np.float32)
    return xs, ys, zs


def _sous_grille(axes, lo, hi):
    sl = []
    for i in range(3):
        a = int(np.searchsorted(axes[i], lo[i]))
        b = int(np.searchsorted(axes[i], hi[i], side="right"))
        sl.append(slice(max(a, 0), min(b, len(axes[i]))))
    return sl


def _champ_sur(forme, axes, sl):
    """Distance signée d'une forme (sdf.Forme) sur la sous-grille sl."""
    sub = [axes[i][sl[i]] for i in range(3)]
    if any(len(a) < 2 for a in sub):
        return None
    return forme.champ(sub)


_cage_memo = None


def _cage():
    """Demi-largeur intérieure de la cage thoracique z(x, y), d'après les côtes de squelette.py."""
    global _cage_memo
    if _cage_memo is None:
        import squelette as sq
        from scipy.interpolate import LinearNDInterpolator
        pts, zs = [], []
        for os_pts, cart in sq._ribs():
            c = sq.courbe(os_pts, n=30)
            for p in c[3:]:
                pts.append((p[0], p[1])); zs.append(p[2] - 0.012)
            for p in sq.courbe(cart, n=8):
                pts.append((p[0], p[1])); zs.append(max(p[2] - 0.01, 0.02))
        _cage_memo = LinearNDInterpolator(np.array(pts), np.array(zs), fill_value=np.nan)
    return _cage_memo


def cavites(P, corps_d):
    """Masque des cavités (thorax, ventre, bassin) pour les points P (..., 3), corps_d = distance à la peau.
    Thorax : en dedans des côtes. Ventre : en dedans d'une paroi de 4,6 cm, et pas dans la cuisse (la
    cavité se resserre vers l'entrée du bassin). Bassin : canal sous le sacrum, entre les os coxaux."""
    import squelette as sq
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    noms = [f"T{i}" for i in range(1, 14)] + [f"L{i}" for i in range(1, 7)]
    vx = np.array([sq.VERT[n][0][0] for n in noms])
    vy = np.array([sq.VERT[n][0][1] for n in noms])
    toit = np.interp(x, vx, vy) - 0.035                     # sous le corps des vertèbres
    zc = _cage()(x, y)                                       # NaN hors de la cage
    dans_cage = np.isfinite(zc) & (z < np.nan_to_num(zc, nan=-1.0))
    paroi = (corps_d < -0.046) & ~np.isfinite(zc)
    zmax_ventre = np.interp(x, [-0.2, 0.42, 0.72], [0.6, 0.38, 0.09])
    ventre = paroi & (z < zmax_ventre) & (x > -0.3) & (x < 0.72)
    dans = (dans_cage | ventre) & (y < toit) & (x > -0.655)
    dans &= ~(np.isfinite(zc) & (x < -0.2) & (y < sq.Y_STERNUM + 0.025))      # poitrine sous le sternum : viande
    bassin = (x >= 0.6) & (x < 0.98) & (z < 0.085) & (y > 1.0) & (y < 1.21)
    return dans | bassin


def etiqueter(axes, animal="boeuf", iterations=120, t0=None):
    """Étapes 1 à 4 sur une grille (axes) : peau, os, cavités, germes, croissance. Renvoie un dict :
    lab (numéro du morceau par voxel, 0 = rien), ids (morceau k = ids[k-1]), corps_d (distance à la peau),
    os_occ, cav, X, Y, Z (coordonnées des voxels)."""
    from muscles import MUSCLES, corps, formes_os
    t0 = t0 or time.time()
    specs = MUSCLES[animal]
    ids = list(specs)
    nx, ny, nz = (len(a) for a in axes)
    # 1. peau
    corps_d = np.empty((nx, ny, nz), np.float32)
    Yg, Zg = np.meshgrid(axes[1], axes[2], indexing="ij")
    for i, x in enumerate(axes[0]):
        P = np.stack([np.full_like(Yg, x), Yg, Zg], -1)
        corps_d[i] = corps().distance(P)
    print(f"   viande : peau ({time.time() - t0:.0f} s)", flush=True)
    # 2. os (2 mm d'écart) et cavités
    os_occ = np.zeros((nx, ny, nz), bool)
    for oid, f_os in formes_os().items():
        lo, hi = f_os.boite(0.004)
        sl = _sous_grille(axes, lo, hi)
        d = _champ_sur(f_os, axes, sl)
        if d is not None:
            os_occ[tuple(sl)] |= d < 0.002
    print(f"   viande : os ({time.time() - t0:.0f} s)", flush=True)
    X, Y, Z = np.meshgrid(*axes, indexing="ij")
    P = np.stack([X, Y, Z], -1)
    cav = cavites(P, corps_d)
    del P
    base = (corps_d < -0.006) & ~os_occ & (Z > 0.003)
    viande = base & ~cav
    tete = X < -1.14
    bas_avant = (X < -0.4) & (Y < 0.455)
    bas_arriere = (X > 0.55) & (Y < 0.45)
    # queue : tube autour de son axe (comme dans formes.py)
    queue = X > 1.075
    for a_, b_ in (((1.03, 1.38), (1.09, 1.0)), ((1.09, 1.0), (1.09, 0.5))):
        ax_, ay_ = a_; bx_, by_ = b_
        dx_, dy_ = bx_ - ax_, by_ - ay_
        t_ = np.clip(((X - ax_) * dx_ + (Y - ay_) * dy_) / (dx_ * dx_ + dy_ * dy_), 0, 1)
        queue |= (np.hypot(X - ax_ - t_ * dx_, Y - ay_ - t_ * dy_) ** 2 + Z ** 2 < 0.058 ** 2) & (X > 1.0)
    viande &= ~(bas_avant | bas_arriere | queue)
    # 3. germes : intérieur de chaque volume modelé (où ils se recouvrent, le point va à celui dont il est le
    #    plus au cœur, en proportion de sa taille)
    lab = np.zeros((nx, ny, nz), np.int16)
    meilleur = np.full((nx, ny, nz), 1.0, np.float32)
    for k, mid in enumerate(ids, start=1):
        forme = specs[mid]["forme"]()
        lo, hi = forme.boite(0.01)
        sl = _sous_grille(axes, lo, hi)
        d = _champ_sur(forme, axes, sl)
        if d is None:
            continue
        sub_v = viande[tuple(sl)]
        if mid in INTERNES:
            sub_v = sub_v | base[tuple(sl)]
        sub_v = sub_v | (tete[tuple(sl)] & base[tuple(sl)])
        # profondeur relative (-1 = au cœur du germe) : un gros germe n'écrase pas un petit voisin
        dn = d / max(float(-d.min()), 1e-3)
        d = dn
        m = (d < 0) & (d < meilleur[tuple(sl)]) & sub_v
        meilleur[tuple(sl)][m] = d[m]
        lab[tuple(sl)][m] = k
    # la tête n'a que ses muscles modelés (joue, langue) ; pas de croissance dedans ; les muscles
    # internes restent à leur volume (ils ne grandissent pas dans la cavité)
    viande_tete = tete & (lab > 0)
    viande = (viande & ~tete) | viande_tete | (lab > 0)
    lab[~viande] = 0
    print(f"   viande : germes ({time.time() - t0:.0f} s) ; {int(viande.sum())} voxels de viande", flush=True)
    # 4. croissance de proche en proche dans la viande (6 voisins), jusqu'à remplir. Chaque morceau a sa
    #    « vitesse » (période en pas : 1 = à chaque pas, 3 = un pas sur trois) : un gros germe posé dans une
    #    région très large (le rumsteck dans la croupe) avance moins vite, ses voisins prennent leur part.
    internes = np.array([0] + [1 if mid in INTERNES else 0 for mid in ids], bool)
    periode = np.array([1] + [int(specs[mid].get("vitesse", 1)) for mid in ids], np.int16)
    # zones permises : un morceau ne grandit pas hors de sa région anatomique (ex. le tende de tranche reste
    # sous le plancher du bassin)
    interdit = {k: ~specs[mid]["domaine"](X, Y, Z) for k, mid in enumerate(ids, start=1) if "domaine" in specs[mid]}
    pmax = int(periode.max())
    libre = viande & (lab == 0) & ~tete
    sans_gain = 0
    for it in range(iterations * pmax):
        if not libre.any() or sans_gain >= pmax:
            break
        prop = np.zeros_like(lab)
        for ax in range(3):
            for s in (1, -1):
                v = np.roll(lab, s, axis=ax)
                if s == 1:
                    idx = [slice(None)] * 3; idx[ax] = slice(0, 1); v[tuple(idx)] = 0
                else:
                    idx = [slice(None)] * 3; idx[ax] = slice(-1, None); v[tuple(idx)] = 0
                prop = np.where((prop == 0) & (v > 0), v, prop)
        actif = (it % periode) == 0                      # morceaux qui avancent à ce pas
        gagne = libre & (prop > 0) & ~internes[prop] & actif[prop]
        for k, hors in interdit.items():
            gagne &= ~((prop == k) & hors)
        if not gagne.any():
            sans_gain += 1
            continue
        sans_gain = 0
        lab[gagne] = prop[gagne]
        libre &= ~gagne
    print(f"   viande : croissance ({time.time() - t0:.0f} s), {int(libre.sum())} voxels isolés laissés", flush=True)
    return {"lab": lab, "ids": ids, "corps_d": corps_d, "os_occ": os_occ, "cav": cav, "X": X, "Y": Y, "Z": Z}


def construire_viande(animal="boeuf", seulement=None):
    """Renvoie {id muscle: {"v", "f", "code", "ao"}} pour tous les morceaux du bœuf."""
    import scipy.ndimage as ndi
    from skimage.measure import marching_cubes
    import fast_simplification as fs
    from anatomie import lisser, normales
    t0 = time.time()
    axes = _grille()
    e = etiqueter(axes, animal, t0=t0)
    lab, ids, corps_d, os_occ, cav = e["lab"], e["ids"], e["corps_d"], e["os_occ"], e["cav"]
    # 5. surfaces. Chaque morceau est prolongé de quelques mm au-delà de la peau (dans la mince couche qui
    #    lui fait face), pour que sa face extérieure soit recoupée exactement sur la peau lisse.
    coque = (corps_d >= -0.0065) & (corps_d < 0.02) & ~os_occ & ~cav
    _, plus_proche = ndi.distance_transform_edt(lab == 0, return_indices=True)
    lab_coque = np.where(coque, lab[tuple(plus_proche)], 0)
    del plus_proche
    occ = ndi.gaussian_filter((lab > 0).astype(np.float32) + os_occ.astype(np.float32), 4.0)
    origine = np.array([axes[0][0], axes[1][0], axes[2][0]], np.float64)
    sortie = {}
    for k, mid in enumerate(ids, start=1):
        if seulement and mid not in seulement:
            continue
        m = lab == k
        if m.sum() < 20:
            raise ValueError(f"morceau {mid} vide")
        # un seul bloc par morceau : les miettes détachées (germes coupés par un os) sont rendues aux voisins
        cc, ncc = ndi.label(m)
        if ncc > 1:
            tailles = ndi.sum(m, cc, range(1, ncc + 1))
            m = cc == (1 + int(np.argmax(tailles)))
        m = m | ((lab_coque == k) & ndi.binary_dilation(m, iterations=4))
        ii = np.nonzero(m)
        sl = tuple(slice(max(int(a.min()) - 3, 0), int(a.max()) + 4) for a in ii)
        ind = ndi.gaussian_filter(m[sl].astype(np.float32), 1.1)
        # face extérieure : la peau (lisse) plutôt que l'escalier de la grille
        peau = (corps_d[sl] + 0.006) * (0.45 / PAS)
        champ = np.maximum(RACCORD - ind, peau)
        champ = np.pad(champ, 1, constant_values=1.0)
        # négatif dedans (comme les os) : faces tournées vers l'extérieur
        v, f, _, _ = marching_cubes(champ, 0.0, spacing=(PAS, PAS, PAS))
        v = v - PAS + origine + np.array([sl[0].start, sl[1].start, sl[2].start]) * PAS
        v = lisser(v, f, iterations=8)
        cible = int(np.clip(m.sum() / 9.0, 2200, 5000))
        if len(f) > cible:
            v, f = fs.simplify(v.astype(np.float32), f.astype(np.int64), target_reduction=1 - cible / len(f), agg=3)
        v, f = v.astype(np.float64), f.astype(np.int64)
        # ombrage : occupation (viande + os) un peu au-dessus de la surface
        n = normales(v, f)
        o = 0.0
        for h, w in ((0.012, 0.5), (0.024, 0.3), (0.04, 0.2)):
            q = (v + n * h - origine) / PAS
            o = o + w * ndi.map_coordinates(occ, q.T, order=1, mode="nearest")
        ao = np.clip(1.2 - 1.0 * o, 0.0, 1.0)
        sortie[mid] = {"v": v, "f": f, "code": np.zeros(len(v), np.uint8), "ao": ao}
        print(f"   morceau {mid}: {int(m.sum())} voxels, {len(v)} sommets, {len(f)} triangles", flush=True)
    print(f"   viande : fini en {time.time() - t0:.0f} s", flush=True)
    return sortie
