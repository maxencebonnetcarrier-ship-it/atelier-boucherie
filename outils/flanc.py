# Atelier : le flanchet, les bavettes, l'onglet et la hampe du bœuf (« python outils/detail.py flanc ») : la
# paroi du ventre et le diaphragme, sous l'aloyau.
#
# D'après le classeur (fiches magasin, guide de découpe) et l'OQLF :
#   - flanchet : la paroi du ventre, sur 3 cartilages de côtes (aussi appelé « œillet ») ;
#   - bavette de flanchet (le « flank steak » : OQLF), « affranchie de sa pointe » ;
#   - bavette d'aloyau, sous l'aloyau, « entièrement parée et épluchée » ;
#   - onglet (les piliers du diaphragme : OQLF) : « séparer les 2 muscles », « nerf central retiré » ;
#   - hampe (la base du diaphragme : OQLF).
# Placement de la pointe de la bavette et des deux muscles de l'onglet : approximatif, À FAIRE VALIDER.
# Os : les vertèbres des reins (fendues) et le bas des 4 dernières côtes avec leurs cartilages.
import numpy as np

PAS = 0.004
PIECES_FLANC = ["flanchet", "bavette-de-flanchet", "bavette-d-aloyau", "onglet", "hampe"]
GRAS_FLANC = "gras-flanc"
OS_HD_FLANC = {"lombaires-flanc": 24000, "cotes-flanc": 16000}
# l'onglet dans muscles.py : de sous les premières lombaires (A) vers le bas et l'avant (B)
ONGLET_A = np.array([0.2, 1.212, 0.016])
ONGLET_B = np.array([0.0, 1.03, 0.052])


def _lombaires():
    import squelette as sq
    return sq.lombaires()


def _cotes():
    import squelette as sq
    from aloyau import Y_SCIE
    return sq.cotes(premiere=10, derniere=13, sciees_a=Y_SCIE, garder="bas")


FORMES_OS = {"lombaires-flanc": (_lombaires, False), "cotes-flanc": (_cotes, True)}


def epaisseur_gras_flanc(X, Y, Z):
    """Gras de couverture : 1,2 cm sur le flanc, 1,6 cm sous le ventre (le flanchet est gras)."""
    return 0.012 + 0.004 * np.clip((0.8 - Y) / 0.2, 0, 1)


def decouper_flanc(e):
    """Renvoie (sous, noms, fins) comme detail.decouper, plus le champ du nerf central de l'onglet."""
    import scipy.ndimage as ndi
    lab, ids, cd = e["lab"], e["ids"], e["corps_d"]
    xs, ys, zs = e["axes"]
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    piece = {mid: lab == (ids.index(mid) + 1) for mid in PIECES_FLANC}
    sous = np.zeros(lab.shape, np.int16)
    noms, fins = [], {}

    def poser(nom, pc, masque):
        noms.append((nom, pc))
        sous[masque & (sous == 0)] = len(noms)

    region = np.zeros_like(lab, bool)
    for mid in ("flanchet", "bavette-de-flanchet", "bavette-d-aloyau"):       # sous la peau
        region |= piece[mid]
    poser(GRAS_FLANC, None, region & (cd > -epaisseur_gras_flanc(X, Y, Z)))
    libre = sous == 0

    # --- onglet : ses 2 muscles de part et d'autre d'un plan qui contient sa longueur ; le nerf central dedans
    on = piece["onglet"] & libre
    ax = (ONGLET_B - ONGLET_A) / np.linalg.norm(ONGLET_B - ONGLET_A)
    n = np.cross(ax, [0.0, 0.0, 1.0]); n /= np.linalg.norm(n)
    A = ONGLET_A.astype(np.float32)
    d = ((X - A[0]) * n[0] + (Y - A[1]) * n[1] + (Z - A[2]) * n[2]).astype(np.float32)
    d -= np.median(d[on])                                 # l'onglet est courbe : le plan passe par son milieu
    t = ((X - A[0]) * ax[0] + (Y - A[1]) * ax[1] + (Z - A[2]) * ax[2]) / float(np.linalg.norm(ONGLET_B - ONGLET_A))
    dans = (0.5 - ndi.gaussian_filter(on.astype(np.float32), 1.0)) * (2 * PAS)
    champ = np.maximum.reduce([np.abs(d) - 0.003, dans, (0.08 - t) * 0.1, (t - 0.92) * 0.1]).astype(np.float32)
    fins["on-nerf"] = champ
    poser("on-nerf", "onglet", on & (champ < 0))
    poser("on-avant", "onglet", on & (d < 0))
    poser("on-arriere", "onglet", on)
    poser("hampe", "hampe", piece["hampe"] & libre)

    # --- bavettes et flanchet
    poser("bavette-d-aloyau", "bavette-d-aloyau", piece["bavette-d-aloyau"] & libre)
    bf = piece["bavette-de-flanchet"] & libre
    x_pointe = np.percentile(X[bf], 85)                   # le bout côté cuisse, le plus mince
    poser("bf-pointe", "bavette-de-flanchet", bf & (X > x_pointe))
    poser("bf-bavette", "bavette-de-flanchet", bf)
    poser("flanchet", "flanchet", piece["flanchet"] & libre)

    # nettoyage : un seul bloc par muscle ; les miettes vont au muscle voisin
    for k_, (nom, pc_) in enumerate(noms, start=1):
        m = sous == k_
        if not m.any():
            raise ValueError(f"muscle {nom} vide")
        cc, ncc = ndi.label(m)
        if ncc > 1:
            tt = ndi.sum(m, cc, range(1, ncc + 1))
            sous[m & (cc != 1 + int(np.argmax(tt)))] = -1
    orphelin = sous == -1
    for _ in range(40):
        if not orphelin.any():
            break
        for ax_ in range(3):
            for s in (1, -1):
                vv = np.roll(sous, s, axis=ax_)
                pris = orphelin & (vv > 0)
                sous[pris] = vv[pris]
                orphelin &= ~pris
    sous[sous < 0] = 0
    for k_, (nom, pc_) in enumerate(noms, start=1):
        print(f"   {nom:18s} {float((sous == k_).sum() * PAS ** 3 * 1000):6.2f} L", flush=True)
    return sous, noms, fins


def reperes_flanc():
    """Points nommés des vertèbres des reins et des dernières côtes, posés sur l'os en haute définition, du
    côté gauche (z ≥ 0)."""
    import os
    import squelette as sq
    from sdf import courbe
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    V = {}
    for oid in OS_HD_FLANC:
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
    L2, L4 = sq.VERT["L2"][0], sq.VERT["L4"][0]
    os13, _ = sq._ribs()[12]
    c13 = courbe(os13, n=30)
    _, cart11 = sq._ribs()[10]
    _, cart12 = sq._ribs()[11]
    return {
        "lombaires-flanc": [
            ("fl-corpus", sur("lombaires-flanc", L2 + np.array([0.0, -0.045, 0.01]))),
            ("fl-processus-transversus", le_plus("lombaires-flanc", lambda a: np.abs(a[:, 0] - L4[0]) < 0.03, lambda a: a[:, 2])),
        ],
        "cotes-flanc": [
            ("fl-costa-ultima", sur("cotes-flanc", c13[np.argmin(np.abs(c13[:, 1] - 1.0))] + np.array([0.0, 0.0, 0.02]))),
            ("fl-cartilago-costalis", sur("cotes-flanc", courbe(cart11, n=12)[6])),
            ("fl-arcus-costalis", sur("cotes-flanc", courbe(cart12, n=12)[-1])),
        ],
    }
