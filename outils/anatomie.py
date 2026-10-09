# Fabrique app/data/anatomie.js : squelette réaliste du bœuf (et muscles posés sur les os),
# chargé par l'appli seulement quand on ouvre le squelette.
#
#   python outils/anatomie.py            reconstruit ce qui manque dans le cache, puis écrit le fichier
#   python outils/anatomie.py femur cotes   force la reconstruction de ces éléments
#   python outils/anatomie.py tout       reconstruit tout
#
# Morceaux de viande : outils/viande.py (ils remplissent la carcasse, à partir des germes de muscles.py).
# Étapes pour chaque os : distance signée sur une grille fine -> surface (marching cubes) ->
# allègement -> ombrage des creux précalculé -> quantification sur 16 bits -> base64.
# Les os pairs ne sont calculés qu'à gauche : l'appli fabrique le côté droit par symétrie.
import base64
import json
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from squelette import SQUELETTES  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RACINE, "outils", "cache", "anatomie")
SORTIE = os.path.join(RACINE, "app", "data", "anatomie.js")
PAS_OS = 0.0032


def b64(a):
    return base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()


def maillage(forme, pas, cible):
    from skimage.measure import marching_cubes
    import fast_simplification as fs
    axes = forme.grille(pas)
    vol = forme.champ(axes)
    if vol.min() >= 0:
        raise ValueError("forme vide")
    v, f, _, _ = marching_cubes(vol, 0.0, spacing=(pas, pas, pas))
    v = v + np.array([axes[0][0], axes[1][0], axes[2][0]])
    v = lisser(v, f)          # efface l'effet d'escalier de la grille (sinon : plis sur les os plats)
    if len(f) > cible:
        v, f = fs.simplify(v.astype(np.float32), f.astype(np.int64), target_reduction=1 - cible / len(f), agg=3)
    return v.astype(np.float64), f.astype(np.int64)


def lisser(v, f, iterations=8, lam=0.5, mu=-0.53):
    """Lissage de Taubin : adoucit sans faire fondre le volume."""
    import scipy.sparse as sp
    n = len(v)
    i = np.concatenate([f[:, 0], f[:, 1], f[:, 2], f[:, 1], f[:, 2], f[:, 0]])
    j = np.concatenate([f[:, 1], f[:, 2], f[:, 0], f[:, 0], f[:, 1], f[:, 2]])
    A = sp.coo_matrix((np.ones(len(i)), (i, j)), shape=(n, n)).tocsr()
    A.data[:] = 1.0
    deg = np.asarray(A.sum(1)).ravel()
    W = sp.diags(1.0 / np.maximum(deg, 1)) @ A
    for _ in range(iterations):
        v = v + lam * (W @ v - v)
        v = v + mu * (W @ v - v)
    return v


def normales(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    fn = np.cross(b - a, c - a)
    nor = np.zeros_like(v)
    for k in range(3):
        np.add.at(nor, f[:, k], fn)
    return nor / (np.linalg.norm(nor, axis=1, keepdims=True) + 1e-12)


def occlusion(forme, v, f, pas=0.006, n=5):
    """1 = à découvert, 0 = au fond d'un creux : on sonde le volume le long de la normale."""
    nor = normales(v, f)
    occ = np.zeros(len(v))
    poids = 1.0
    for i in range(1, n + 1):
        h = pas * i
        d = forme.distance((v + nor * h).astype(np.float32))
        occ += poids * np.clip(h - d, 0, None) / h
        poids *= 0.55
    return np.clip(1.0 - 0.75 * occ, 0.0, 1.0)


def construire_os(oid, fn, cible, pas=PAS_OS):
    forme = fn()
    t = time.time()
    v, f = maillage(forme, pas, cible)
    noms, lab = forme.parties(v.astype(np.float32))
    code = np.array([{"cartilage": 1, "dent": 2}.get(noms[i], 0) for i in lab], np.uint8)
    ao = occlusion(forme, v, f)
    print(f"   os {oid}: {len(v)} sommets, {len(f)} triangles ({time.time() - t:.0f} s)", flush=True)
    return {"v": v, "f": f, "code": code, "ao": ao}


def emballer(d):
    v, f = d["v"], d["f"]
    lo, hi = v.min(0), v.max(0)
    q = np.round((v - lo) / np.maximum(hi - lo, 1e-6) * 65535).astype("<u2")
    if len(v) >= 65536:
        raise ValueError("trop de sommets pour des indices 16 bits")
    return {"boite": [lo.round(5).tolist(), hi.round(5).tolist()], "centre": v.mean(0).round(4).tolist(),
            "sommets": b64(q), "triangles": b64(f.astype("<u2")), "parties": b64(d["code"]),
            "ombre": b64(np.round(d["ao"] * 255).astype(np.uint8))}


def charger(nom):
    p = os.path.join(CACHE, nom + ".npz")
    if not os.path.exists(p):
        return None
    z = np.load(p)
    return {k: z[k] for k in z.files}


def ranger(nom, d):
    os.makedirs(CACHE, exist_ok=True)
    np.savez_compressed(os.path.join(CACHE, nom + ".npz"), **d)


def main(args):
    tout = "tout" in args
    sortie = {}
    for animal, liste in SQUELETTES.items():
        os_out = []
        for oid, fn, pair, cible, pas in liste:
            cle = f"{animal}-os-{oid}"
            d = None if (tout or oid in args) else charger(cle)
            if d is None:
                d = construire_os(oid, fn, cible, pas)
                ranger(cle, d)
            os_out.append({"id": oid, "pair": pair, **emballer(d)})
        sortie[animal] = {"os": os_out}
        try:
            from muscles import MUSCLES, construire_muscle
        except ImportError:
            MUSCLES = {}
        mus = []
        specs = MUSCLES.get(animal, {})
        # morceaux qui remplissent la carcasse (outils/viande.py), calculés tous ensemble
        a_refaire = [mid for mid in specs
                     if tout or mid in args or "muscles" in args or charger(f"{animal}-muscle-{mid}") is None]
        if a_refaire:
            from viande import construire_viande
            for mid, d in construire_viande(animal).items():
                ranger(f"{animal}-muscle-{mid}", d)
        for mid, spec in specs.items():
            d = charger(f"{animal}-muscle-{mid}")
            mus.append({"id": mid, "pieces": spec["pieces"], "pair": spec.get("pair", True), **emballer(d)})
        if mus:
            sortie[animal]["muscles"] = mus
    entete = ("// Fichier généré par outils/anatomie.py — ne pas modifier à la main.\n"
              "// Squelette réaliste du bœuf et muscles posés sur les os ; os et muscles pairs : côté gauche seulement\n"
              "// (l'appli fabrique le côté droit par symétrie). Chargé seulement à l'ouverture du squelette.\n")
    with open(SORTIE, "w", encoding="utf-8", newline="") as fh:
        fh.write(entete + "window.ANATOMIE = " + json.dumps(sortie, separators=(",", ":")) + ";\n")
    print("écrit", os.path.relpath(SORTIE, RACINE), f"({os.path.getsize(SORTIE) // 1024} Ko)")


if __name__ == "__main__":
    main(sys.argv[1:])
