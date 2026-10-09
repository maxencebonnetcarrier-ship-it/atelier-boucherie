# Atelier : la cuisse et l'épaule du bœuf en détail, muscle par muscle, pour la page app/atelier.html.
#
#   python outils/detail.py [cuisse]          -> app/data/atelier-cuisse.js (maillages fins des muscles, du gras
#                                                de couverture et des os de la cuisse, repères nommés des os)
#   python outils/detail.py epaule            -> app/data/atelier-epaule.js (même chose pour l'épaule)
#   ... --vite                                -> réutilise l'étiquetage en cache (outils/cache/<région>_lab.npz)
#
# 1. La cuisse et la croupe sont étiquetées comme dans outils/viande.py, mais sur une grille plus fine
#    (4 mm au lieu de 6) et seulement dans la région de la cuisse.
# 2. Une couche de GRAS DE COUVERTURE est mise à part sous la peau (plus épaisse sur la croupe) : c'est ce
#    qui recouvre une cuisse reçue en atelier, et ce que le boucher retire au parage.
# 3. Chaque pièce est divisée en ses muscles, avec les noms du classeur (tableaux « Le bœuf » n° 1 et 2,
#    fiches magasin, guide de découpe) : tranche grasse = mouvant, rond, plat ; tende de tranche = cœur,
#    dessus, merlan, poire ; semelle = gîte noix (carré et oreille), nerveux de gîte, rond de gîte ;
#    rumsteck = cœur, filet, langue de chat, aiguillette. Les limites suivent des repères anatomiques
#    (axe du fémur, peau, os) : placement simplifié, À FAIRE VALIDER par un formateur.
# 4. Chaque muscle devient une surface lissée avec, par sommet : ombrage des creux, gras (face sous la
#    couverture) et nacre (face collée à un autre muscle ou à un os : l'aponévrose que l'on suit au couteau
#    pour séparer, puis que l'on retire en épluchant). La direction des fibres est l'axe long du muscle.
import base64
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RACINE, "outils", "cache")
PAS = 0.004
# Boîte de calcul de chaque région (m) : assez large pour que les morceaux voisins (collier, basses côtes,
# poitrine…) grandissent aussi et bornent la région.
BOITES = {"cuisse": ((0.0, 0.40, 0.0), (1.13, 1.50, 0.45)),
          "epaule": ((-1.04, 0.42, 0.0), (-0.27, 1.52, 0.45))}
BOITE = BOITES["cuisse"]

# Pièces de la cuisse (et de la croupe) ; os de la région ; résolution des os (triangles).
PIECES = ["rumsteck", "aiguillette-baronne", "tende-de-tranche", "tranche-grasse", "gite-a-la-noix", "rond-de-gite",
          "araignee", "gite-arriere"]
OS_HD = {"coxal": 32000, "femur": 18000, "rotule": 3000, "tibia": 18000, "sacrum": 9000}
GRAS = "gras-de-couverture"


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def emballer(v, f, extra):
    lo, hi = v.min(0), v.max(0)
    q = np.round((v - lo) / np.maximum(hi - lo, 1e-6) * 65535).astype("<u2")
    if len(v) >= 65536:
        raise ValueError("trop de sommets pour des indices 16 bits")
    d = {"boite": [lo.round(5).tolist(), hi.round(5).tolist()], "centre": v.mean(0).round(4).tolist(),
         "sommets": b64(q), "triangles": b64(f.astype("<u2"))}
    for k, a in extra.items():
        d[k] = b64(np.round(np.clip(a, 0, 1) * 255).astype(np.uint8))
    return d


# ---------------------------------------------------------------- 1. étiquetage
def etiquetage(vite=False, region="cuisse"):
    import viande
    p = os.path.join(CACHE, f"{region}_lab.npz")
    if vite and os.path.exists(p):
        z = np.load(p)
        axes = (z["x"], z["y"], z["z"])
        return {"lab": z["lab"], "ids": [str(i) for i in z["ids"]], "corps_d": z["corps_d"], "os_occ": z["os_occ"],
                "cav": z["cav"], "axes": axes}
    axes = tuple(np.arange(lo, hi, PAS, dtype=np.float32) for lo, hi in zip(*BOITES[region]))
    e = viande.etiqueter(axes, iterations=200)
    np.savez_compressed(p, lab=e["lab"], corps_d=e["corps_d"], os_occ=e["os_occ"], cav=e["cav"], ids=np.array(e["ids"]),
                        x=axes[0], y=axes[1], z=axes[2])
    e["axes"] = axes
    return e


# ---------------------------------------------------------------- 2-3. gras et muscles
def epaisseur_gras(X, Y, Z):
    """Épaisseur du gras de couverture (m) : 1,6 cm sur la croupe, 1 cm sur les côtés de la cuisse, 5 mm à
    l'intérieur de la cuisse et vers le jarret."""
    e = 0.006 + 0.01 * np.clip((Y - 0.8) / 0.4, 0, 1) * np.clip((Z - 0.08) / 0.12, 0.3, 1)
    return e


def decouper(e):
    """Renvoie (sous, noms) : sous = numéro du muscle par voxel (0 = rien), noms[k-1] = (id, pièce)."""
    import scipy.ndimage as ndi
    import squelette as sq
    lab, ids, cd = e["lab"], e["ids"], e["corps_d"]
    xs, ys, zs = e["axes"]
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    piece = {mid: lab == (ids.index(mid) + 1) for mid in PIECES}
    cuisse = np.zeros_like(lab, bool)
    for m in piece.values():
        cuisse |= m
    sous = np.zeros(lab.shape, np.int16)
    noms = []

    def poser(nom, pc, masque):
        noms.append((nom, pc))
        sous[masque & (sous == 0)] = len(noms)

    # gras de couverture : la couche sous la peau des pièces de la cuisse
    gras = cuisse & (cd > -epaisseur_gras(X, Y, Z))
    poser(GRAS, None, gras)
    libre = ~gras
    # gradient de la distance à la peau : vers où regarde la peau la plus proche
    gz = np.gradient(cd, axis=2) / PAS                 # pente par mètre : -1 = la peau est vers le dedans

    # --- tranche grasse : secteurs autour du fémur réel, tranche par tranche horizontale ---
    # (0° = devant, vers la tête ; + = dehors ; - = dedans). Rond = droit de la cuisse, devant ; plat = vaste
    # latéral, dehors ; mouvant = vaste médial, dedans (AHDB « thick flank » ; mouvant = vaste médial).
    A, B = sq.TETE_FEMUR, sq.GRASSET
    xc = np.full(len(ys), np.nan); zc = np.full(len(ys), np.nan)
    for j, y in enumerate(ys):
        t = np.clip((y - A[1]) / (B[1] - A[1]), 0, 1)
        ax_, az_ = A[0] + t * (B[0] - A[0]), A[2] + t * (B[2] - A[2])
        o = e["os_occ"][:, j, :]
        if not o.any():
            continue
        ii_, kk_ = np.nonzero(o)
        près = (xs[ii_] - ax_) ** 2 + (zs[kk_] - az_) ** 2 < 0.05 ** 2
        if près.sum() > 5:
            xc[j], zc[j] = xs[ii_[près]].mean(), zs[kk_[près]].mean()
    ok = np.isfinite(xc)
    xc = np.interp(np.arange(len(ys)), np.where(ok)[0], xc[ok]); zc = np.interp(np.arange(len(ys)), np.where(ok)[0], zc[ok])
    ang = np.degrees(np.arctan2(Z - zc[None, :, None], -(X - xc[None, :, None])))
    tg = piece["tranche-grasse"] & libre
    poser("tg-rond", "tranche-grasse", tg & (np.abs(ang) < 30))
    poser("tg-plat", "tranche-grasse", tg & (ang >= 30))
    poser("tg-mouvant", "tranche-grasse", tg & (ang <= -30))

    # --- tende de tranche ---
    tt = piece["tende-de-tranche"] & libre
    # poire : petite masse (≈ 0,55 kg) dans l'angle du pubis, au-dessus de l'araignée
    ii = np.argwhere(tt)
    pts = np.stack([xs[ii[:, 0]], ys[ii[:, 1]], zs[ii[:, 2]]], 1)
    ancre = np.array([0.86, 0.95, 0.06])
    d = np.linalg.norm(pts - ancre, axis=1)
    n_poire = int(0.55e-3 / PAS ** 3)
    choix = ii[np.argsort(d)[:n_poire]]
    m = np.zeros_like(tt); m[tuple(choix.T)] = True
    poser("tt-poire", "tende-de-tranche", m)
    # Face interne de la cuisse : sur une demi-carcasse, c'est le plan de fente (z = 0) sous le bassin.
    # merlan : bande le long du bord avant (crânial) de cette face
    xmin = np.full(len(ys), np.inf)
    for j in range(len(ys)):
        c = tt[:, j, :8]
        if c.any():
            xmin[j] = xs[np.where(c.any(1))[0].min()]
    poser("tt-merlan", "tende-de-tranche", tt & (X < xmin[None, :, None] + 0.05) & (Z < 0.075) & (Y < 1.02))
    # dessus de tranche : la nappe de surface de la face interne (OQLF : « face libre superficielle »)
    poser("tt-dessus", "tende-de-tranche", tt & (Z < 0.032) & (Y < 1.0))
    poser("tt-coeur", "tende-de-tranche", tt)

    # --- semelle : gîte à la noix (carré, oreille), nerveux de gîte ; rond de gîte ---
    gn = piece["gite-a-la-noix"] & libre
    poser("gn-nerveux", "gite-a-la-noix", gn & (Y < 0.8))
    poser("gn-oreille", "gite-a-la-noix", gn & (Y > 1.24) & (X < 0.92))
    poser("gn-carre", "gite-a-la-noix", gn)
    poser("rond-de-gite", "rond-de-gite", piece["rond-de-gite"] & libre)

    # --- rumsteck : aiguillette, filet, langue de chat, cœur ---
    rs = piece["rumsteck"] & libre
    limite = 0.84 - 0.25 * (Y - 1.0) + 0.6 * (Z - 0.18) ** 2   # bord arrière du rumsteck (voir muscles.py)
    # aiguillette de rumsteck : la calotte de surface, côté gîte noix (« partie attenante au gîte noix »)
    poser("rs-aiguillette", "rumsteck", rs & (X > limite - 0.13) & (cd > -0.055))
    poser("rs-filet", "rumsteck", rs & (Z < 0.085) & (Y > 1.18))
    # langue de chat : petit muscle « au cœur du rumsteck » (Wikipédia, « Rumsteck ») : les voxels les plus
    # profonds du rumsteck, hors du filet
    rs_reste = rs & (sous == 0)
    ii = np.argwhere(rs_reste)
    prof = -cd[rs_reste]
    choix = ii[np.argsort(-prof)[:int(0.7e-3 / PAS ** 3)]]
    m = np.zeros_like(rs); m[tuple(choix.T)] = True
    poser("rs-langue-de-chat", "rumsteck", m)
    poser("rs-coeur", "rumsteck", rs)

    for mid in ("aiguillette-baronne", "araignee", "gite-arriere"):
        poser(mid, mid, piece[mid] & libre)

    # nettoyage : un seul bloc par muscle ; les miettes vont au muscle voisin de la même pièce
    for k, (nom, pc) in enumerate(noms, start=1):
        m = sous == k
        if not m.any():
            raise ValueError(f"muscle {nom} vide")
        cc, ncc = ndi.label(m)
        if ncc > 1:
            t = ndi.sum(m, cc, range(1, ncc + 1))
            garde = cc == (1 + int(np.argmax(t)))
            sous[m & ~garde] = -1
    orphelin = sous == -1
    for _ in range(40):
        if not orphelin.any():
            break
        for ax in range(3):
            for s in (1, -1):
                v = np.roll(sous, s, axis=ax)
                pris = orphelin & (v > 0)
                sous[pris] = v[pris]
                orphelin &= ~pris
    sous[sous < 0] = 0
    return sous, noms


# ---------------------------------------------------------------- 4. surfaces
def surfaces(e, sous, noms, gras_id=GRAS, ep_fn=None, fins=None):
    """Une surface lissée par muscle. fins = {nom: champ (m, négatif dedans)} : nappes trop fines pour la
    grille (le nerf central du paleron), extraites d'un champ continu sur une grille deux fois plus fine."""
    import scipy.ndimage as ndi
    ep_fn = ep_fn or epaisseur_gras
    fins = fins or {}
    from skimage.measure import marching_cubes
    import fast_simplification as fs
    from anatomie import lisser, normales
    xs, ys, zs = e["axes"]
    cd, os_occ = e["corps_d"], e["os_occ"]
    origine = np.array([xs[0], ys[0], zs[0]], np.float64)
    occ = ndi.gaussian_filter((sous > 0).astype(np.float32) + os_occ.astype(np.float32), 3.0)
    k_gras = 1 + [n for n, _ in noms].index(gras_id)
    out = []
    gras_vox = sous == k_gras
    for k, (nom, pc) in enumerate(noms, start=1):
        m = sous == k
        ii = np.nonzero(m)
        sl = tuple(slice(max(int(a.min()) - 4, 0), int(a.max()) + 5) for a in ii)
        Xs, Ys, Zs = np.meshgrid(xs[sl[0]], ys[sl[1]], zs[sl[2]], indexing="ij")
        ep = ep_fn(Xs, Ys, Zs)
        pas_mc = PAS
        if nom in fins:
            # nappe fine : champ continu ré-échantillonné tous les 2 mm
            c = fins[nom][sl].astype(np.float32)
            g = [np.arange(2 * n - 1, dtype=np.float32) / 2 for n in c.shape]
            G = np.meshgrid(*g, indexing="ij")
            champ = ndi.map_coordinates(c, [G[0], G[1], G[2]], order=1, mode="nearest") / (PAS / 2)
            pas_mc = PAS / 2
        elif nom == gras_id:
            # coquille lisse entre la peau (cd = 0) et la surface parallèle cd = -épaisseur, limitée à la cuisse
            reg = ndi.gaussian_filter(ndi.binary_dilation(m, iterations=2)[sl].astype(np.float32), 1.0)
            coque = np.maximum(cd[sl], -(cd[sl] + ep))
            champ = np.maximum(coque * (0.5 / PAS), 0.5 - reg)
        else:
            # face extérieure recoupée sur la face interne du gras (lisse) : le muscle est prolongé de
            # quelques voxels dans le gras qui le couvre, puis coupé à cd = -épaisseur
            mx = m | (gras_vox & ndi.binary_dilation(m, iterations=3))
            ind = ndi.gaussian_filter(mx[sl].astype(np.float32), 0.9)
            champ = np.maximum(0.55 - ind, (cd[sl] + ep) * (0.5 / PAS))
        champ = np.pad(champ, 1, constant_values=1.0)
        v, f, _, _ = marching_cubes(champ, 0.0, spacing=(pas_mc, pas_mc, pas_mc))
        v = v - pas_mc + origine + np.array([sl[0].start, sl[1].start, sl[2].start]) * PAS
        if len(f) == 0:
            raise ValueError(f"surface vide pour {nom}")
        v = lisser(v, f, iterations=10)
        cible = int(np.clip(m.sum() / 14.0, 2500, 9000)) if nom not in fins else 6000
        if len(f) > cible:
            v, f = fs.simplify(v.astype(np.float32), f.astype(np.int64), target_reduction=1 - cible / len(f), agg=3)
        v, f = v.astype(np.float64), f.astype(np.int64)
        n = normales(v, f)
        o = 0.0
        for h, w in ((0.01, 0.5), (0.02, 0.3), (0.035, 0.2)):
            q = (v + n * h - origine) / PAS
            o = o + w * ndi.map_coordinates(occ, q.T, order=1, mode="nearest")
        ao = np.clip(1.25 - 1.0 * o, 0.0, 1.0)
        # ce que touche chaque face, juste devant elle (6 mm le long de la normale)
        q = np.round((v + n * 0.006 - origine) / PAS).astype(int)
        for i in range(3):
            q[:, i] = np.clip(q[:, i], 0, sous.shape[i] - 1)
        voisin = sous[q[:, 0], q[:, 1], q[:, 2]]
        sur_os = os_occ[q[:, 0], q[:, 1], q[:, 2]]
        dehors_peau = cd[q[:, 0], q[:, 1], q[:, 2]] > -0.002
        gras = ((voisin == k_gras) | dehors_peau).astype(np.float64)
        nacre = (((voisin > 0) & (voisin != k) & (voisin != k_gras)) | sur_os).astype(np.float64)
        gras = np.clip(ndi.uniform_filter1d(gras, 1), 0, 1)
        # direction des fibres : axe long du muscle (analyse en composantes principales)
        pts = np.stack([xs[ii[0]], ys[ii[1]], zs[ii[2]]], 1)
        c = pts - pts.mean(0)
        w_, V = np.linalg.eigh(c.T @ c)
        fibre = V[:, -1]
        if fibre[1] < 0:
            fibre = -fibre
        litres = float(m.sum() * PAS ** 3 * 1000)
        print(f"   {nom:20s} {litres:6.2f} L  {len(v):5d} sommets {len(f):5d} triangles", flush=True)
        d = emballer(v, f, {"ombre": ao, "gras": gras, "nacre": nacre})
        d.update({"id": nom, "piece": pc, "fibre": fibre.round(3).tolist(), "litres": round(litres, 2)})
        out.append(d)
    return out


# ---------------------------------------------------------------- os en haute définition et repères
def os_hd(liste=None):
    import anatomie
    import squelette as sq
    out = []
    formes = {oid: (fn, pair) for oid, fn, pair, _, _ in sq.OS_BOEUF}
    for oid, cible in (liste or OS_HD).items():
        fn, pair = formes[oid]
        cle = os.path.join(CACHE, "anatomie", f"hd-{oid}.npz")
        if os.path.exists(cle):
            z = np.load(cle)
            d = {k: z[k] for k in z.files}
        else:
            d = anatomie.construire_os(oid, fn, cible, pas=0.0024)
            np.savez_compressed(cle, **d)
        v = d["v"]
        code = d["code"].astype(np.int16)
        if oid == "coxal":            # parties de l'os (soudées chez l'adulte) : 3 ilium, 4 pubis, 5 ischium
            x, y, z_ = v[:, 0], v[:, 1], v[:, 2]
            ilium = (x < 0.785) | ((x < 0.83) & (y > 1.03))
            pubis = ~ilium & (x < 0.905) & (y < 1.0) & (z_ < 0.165)
            part = np.where(ilium, 3, np.where(pubis, 4, 5))
            code = np.where(code > 0, code, part)
        e = emballer(v, d["f"], {"ombre": d["ao"]})
        e["parties"] = b64(code.astype(np.uint8))
        e.update({"id": oid, "pair": pair})
        out.append(e)
        print(f"   os {oid}: {len(v)} sommets, {len(d['f'])} triangles", flush=True)
    return out


def reperes():
    """Points nommés des os de la cuisse, posés sur le maillage le plus proche (côté gauche)."""
    import squelette as sq
    p = lambda *a: [round(float(x), 4) for x in a]
    tf = sq.TETE_FEMUR
    return {
        "coxal": [
            ("tuber-coxae", p(*(sq.POINTE_HANCHE + np.array([0, 0.012, -0.012])))),
            ("tuber-sacrale", p(*sq.SACREE)),
            ("crista-iliaca", p(*((sq.POINTE_HANCHE + sq.SACREE) / 2 + np.array([0.03, 0.02, 0.0])))),
            ("ala-ilii", p(0.56, 1.27, 0.17)),
            ("corpus-ilii", p(0.705, 1.11, 0.178)),
            ("acetabulum", p(*(tf + np.array([0.0, -0.03, 0.04])))),
            ("foramen-obturatum", p(0.885, 0.965, 0.085)),
            ("pubis", p(0.85, 0.955, 0.04)),
            ("ischium", p(0.975, 1.02, 0.09)),
            ("symphysis-pelvina", p(0.93, 0.95, 0.008)),
            ("spina-ischiadica", p(0.885, 1.085, 0.135)),
            ("tuber-ischiadicum", p(*sq.POINTE_FESSE)),
            ("arcus-ischiadicus", p(1.03, 1.03, 0.03)),
        ],
        "femur": [
            ("caput-femoris", p(*(tf + np.array([0.0, 0.0, -0.02])))),
            ("trochanter-major", p(0.845, 1.03, 0.262)),
            ("corpus-femoris", p(0.765, 0.86, 0.228)),
            ("trochlea-femoris", p(0.665, 0.73, 0.215)),
            ("condyli-femoris", p(0.71, 0.69, 0.24)),
        ],
        "rotule": [("patella", p(0.632, 0.735, 0.215))],
        "tibia": [
            ("condyli-tibiae", p(*(sq.PLATEAU_TIBIA + np.array([0.0, 0.0, 0.03])))),
            ("tuberositas-tibiae", p(0.662, 0.645, 0.21)),
            ("corpus-tibiae", p(0.79, 0.53, 0.21)),
            ("tuber-calcanei", p(0.962, 0.492, 0.229)),
        ],
    }


def main(args):
    t = time.time()
    region = "epaule" if "epaule" in args else "cuisse"
    e = etiquetage(vite="--vite" in args, region=region)
    print(f"   étiquetage : {time.time() - t:.0f} s", flush=True)
    if region == "cuisse":
        sous, noms = decouper(e)
        print(f"   découpage : {time.time() - t:.0f} s", flush=True)
        muscles = surfaces(e, sous, noms)
        os_ = os_hd()
        rep_ = reperes()
        texte = "La cuisse du bœuf en détail (côté gauche)"
    else:
        from epaule import decouper_epaule, reperes_epaule, epaisseur_gras_epaule, GRAS_EPAULE, OS_HD_EPAULE
        sous, noms, fins = decouper_epaule(e)
        print(f"   découpage : {time.time() - t:.0f} s", flush=True)
        muscles = surfaces(e, sous, noms, gras_id=GRAS_EPAULE, ep_fn=epaisseur_gras_epaule, fins=fins)
        os_ = os_hd(OS_HD_EPAULE)
        rep_ = reperes_epaule(os_)
        texte = "L'épaule du bœuf en détail (côté gauche)"
    donnees = {"muscles": muscles, "os": os_, "reperes": {k: [{"id": i, "point": pt} for i, pt in v] for k, v in rep_.items()}}
    sortie = os.path.join(RACINE, "app", "data", f"atelier-{region}.js")
    entete = ("// Fichier généré par outils/detail.py — ne pas modifier à la main.\n"
              f"// {texte} : muscles séparés, gras de couverture, os en haute\n"
              "// définition et leurs repères. Chargé seulement par la page atelier.html.\n")
    with open(sortie, "w", encoding="utf-8", newline="") as fh:
        fh.write(entete + f"(window.ATELIER_MAILLAGES = window.ATELIER_MAILLAGES || {{}}).{region} = "
                 + json.dumps(donnees, separators=(",", ":")) + ";\n")
    print("écrit", os.path.relpath(sortie, RACINE), f"({os.path.getsize(sortie) // 1024} Ko) en {time.time() - t:.0f} s")

if __name__ == "__main__":
    main(sys.argv[1:])
