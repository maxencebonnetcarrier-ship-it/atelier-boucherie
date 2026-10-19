# Page atelier du squelette du PORC : app/data/atelier-porc.js (chargé seulement par atelier.html?region=porc et
# atelier.html?os=porc-…).
#
#   python outils/atelier_porc.py            -> os en haute définition (cache outils/cache/anatomie/hd-porc-*.npz)
#                                              et repères nommés de chaque os
#   python outils/atelier_porc.py femur      -> refait cet os en haute définition
#
# Les os sont ceux de outils/squelette_porc.py, refaits sur une grille plus fine. Chaque repère est un point
# annoté sur la figure de Sisson (ou un point du squelette : bout d'une épine…), posé dans le modèle par le même
# calage que son os, puis « collé » à la surface de l'os (côté dehors, dessus, devant… selon le repère).
# Les textes des repères (nom, nom latin, ce qu'en fait le boucher) sont dans app/data/atelier.js.
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import anatomie  # noqa: E402
import squelette_porc as SP  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(RACINE, "outils", "cache", "anatomie")
SORTIE = os.path.join(RACINE, "app", "data", "atelier-porc.js")
LENTS = {"cotes", "sacrum"}          # déjà fins et longs à calculer : même grille que dans l'appli


def os_hd(refaire=()):
    out = {}
    for oid, fn, pair, cible, pas in SP.OS_PORC:
        cle = os.path.join(CACHE, f"hd-porc-{oid}.npz")
        if os.path.exists(cle) and oid not in refaire and "tout" not in refaire:
            z = np.load(cle)
            d = {k: z[k] for k in z.files}
        else:
            d = anatomie.construire_os(oid, fn, int(cible * 2.4), pas=pas if oid in LENTS else max(0.0013, pas * 0.78))
            os.makedirs(CACHE, exist_ok=True)
            np.savez_compressed(cle, **d)
        out[oid] = (d, pair)
    return out


def parties_coxal(v, code):
    """Parties de l'os coxal (soudées chez l'adulte) : 3 ilium (devant le cotyle), 4 pubis (plancher, devant le trou
    obturé), 5 ischium (le reste, derrière) ; limites approximatives."""
    A = SP.ACETABULE
    x, y = v[:, 0], v[:, 1]
    ilium = x < A[0] - 0.028
    plancher = y < A[1] - 0.045
    pubis = ~ilium & plancher & (x < A[0] + 0.06)
    part = np.where(ilium, 3, np.where(pubis, 4, 5))
    return np.where(code > 0, code, part)


def coller(v, P, mode, rayon=0.012):
    """Le sommet de l'os qui représente le repère P : parmi les sommets proches de P (dans le plan qui ne compte pas
    la direction du mode), celui qui est le plus loin dans cette direction (dehors = +z, haut = +y…) ; « pres » :
    le sommet le plus proche."""
    P = np.asarray(P, np.float64)
    if mode == "pres":
        return v[np.argmin(((v - P) ** 2).sum(1))]
    axe, signe = {"dehors": (2, 1), "dedans": (2, -1), "haut": (1, 1), "bas": (1, -1), "devant": (0, -1), "derriere": (0, 1)}[mode]
    autres = [i for i in range(3) if i != axe]
    for r in (rayon, rayon * 2, rayon * 4, rayon * 8):
        m = ((v[:, autres] - P[autres]) ** 2).sum(1) < r * r
        if mode == "dehors":
            m &= v[:, 2] > 0
        if m.any():
            idx = np.nonzero(m)[0]
            return v[idx[np.argmax(signe * v[idx, axe])]]
    return v[np.argmin(((v - P) ** 2).sum(1))]


def _vert(nom):
    P, T, L = SP.VERT[nom]
    u, v, w = SP.repere_vertebre(P, T)
    return P, u, v, w, L


def points_reperes():
    """Repères de chaque os : (id, point approché, mode de collage)."""
    pp = SP.pose_crane_profil()
    c = lambda px, py: pp.vers_modele(px, py)
    R = {}
    R["crane"] = [("os-rostrale", c(60, 1650), "devant"), ("os-nasale", c(480, 1270), "haut"),
                  ("foramen-infraorbitale", c(621, 1422), "dehors"), ("orbita", c(965, 1092), "dehors"),
                  ("fossa-temporalis", c(1165, 900), "dehors"), ("arcus-zygomaticus", c(1210, 1290), "dehors"),
                  ("crista-nuchae", c(1110, 650), "haut"), ("condylus-occipitalis", c(1470, 1110), "derriere"),
                  ("meatus-acusticus", c(1385, 905), "dehors"), ("dens-caninus", c(395, 1650), "dehors"),
                  ("dentes-molares", c(900, 1520), "dehors"), ("dentes-incisivi", c(150, 1705), "devant"),
                  ("corpus-mandibulae", c(800, 1720), "dehors"), ("foramina-mentalia", c(600, 1700), "dehors"),
                  ("angulus-mandibulae", c(1385, 1740), "dehors")]
    P1, u1, v1, w1, _ = _vert("C1")
    P2, u2, v2, w2, _ = _vert("C2")
    P5, u5, v5, w5, _ = _vert("C5")
    P7, u7, v7, w7, _ = _vert("C7")
    R["cervicales"] = [("atlas-ala", P1 + w1 * 0.06, "dehors"), ("axis-processus-spinosus", P2 + v2 * 0.08, "haut"),
                       ("axis-dens", P2 - u2 * 0.03, "devant"), ("c-processus-transversus", P5 + w5 * 0.035 - v5 * 0.015, "pres"),
                       ("c-corpus", P5 - v5 * 0.02, "bas"), ("c7-processus-spinosus", P7 + v7 * 0.12, "haut")]
    T2, *_ = _vert("T2")
    T7, u, v, w, L = _vert("T7")
    T14, *_ = _vert("T14")
    R["dorsales"] = [("t-processus-spinosus", T2 + _vert("T2")[2] * 0.135 + _vert("T2")[1] * 0.028, "haut"),
                     ("t-processus-spinosus-dernier", T14 + _vert("T14")[2] * 0.075, "haut"),
                     ("t-corpus", T7 - v * 0.015, "bas"), ("t-processus-transversus", T7 + v * 0.012 + w * 0.042, "dehors"),
                     ("t-fovea-costalis", T7 - u * L * 0.5 + w * 0.016 + v * 0.004, "pres")]
    L3, u, v, w, L = _vert("L3")
    L5, u5_, v5_, w5_, _ = _vert("L5")
    R["lombaires"] = [("l-processus-transversus", L3 + w * 0.08, "dehors"), ("l-processus-spinosus", L3 + v * 0.09, "haut"),
                      ("l-corpus", L3 - v * 0.02, "bas"), ("l-processus-mamillaris", L5 + v5_ * 0.042 + w5_ * 0.016, "pres")]
    s0 = SP.VERT["S_debut"]
    a, Ta = SP.le_long(s0)
    b, _ = SP.le_long(s0 + SP.L_SACRUM)
    us = SP.n_(b - a)
    R["sacrum"] = [("ala-sacralis", a + us * 0.025 + SP.Z * 0.062, "dehors"), ("foramina-sacralia", a + us * 0.045 + SP.Z * 0.022, "haut"),
                   ("crista-sacralis", a + us * 0.07 + SP.Y * 0.02, "haut"), ("apex-ossis-sacri", b, "derriere")]
    R["coccygiennes"] = [("vertebrae-caudales", SP.VERT["Co2"][0], "pres"), ("cauda-apex", SP.VERT[f"Co{SP.N_COCC}"][0], "pres")]
    cotes = SP._cotes()
    R["cotes"] = [("costa-prima", cotes[0][0][6], "dehors"), ("caput-costae", cotes[6][0][0], "pres"),
                  ("tuberculum-costae", cotes[6][0][0] + SP.p3(0.003, 0.009, 0.016), "pres"),
                  ("corpus-costae", cotes[6][0][5], "dehors"), ("cartilago-costalis", cotes[5][1][1], "pres"),
                  ("arcus-costalis", cotes[11][1][1], "pres"), ("costa-ultima", cotes[13][0][6], "dehors")]
    R["sternum"] = [("manubrium-sterni", SP.STERNUM_A + SP.p3(-0.02, 0.012), "devant"),
                    ("sternebrae", (SP.STERNUM_A + SP.STERNUM_B) / 2, "bas"), ("processus-xiphoideus", SP.XIPHOIDE, "pres")]
    p = SP.pose_palette()
    q = lambda px, py: p.vers_modele(px, py)
    R["palette"] = [("cavitas-glenoidalis", q(880, 1885), "bas"), ("tuberculum-supraglenoidale", q(790, 1845), "pres"),
                    ("collum-scapulae", q(880, 1700), "dehors"), ("acromion", q(808, 1606), "dehors"),
                    ("spina-scapulae", q(800, 1330), "dehors"), ("tuber-spinae", q(905, 1150), "dehors"),
                    ("fossa-supraspinata", q(650, 1250), "dehors"), ("fossa-infraspinata", q(1060, 1350), "dehors"),
                    ("margo-caudalis", q(1110, 1500), "pres"), ("angulus-cranialis", q(560, 985), "pres"),
                    ("angulus-caudalis", q(1205, 1045), "pres"), ("cartilago-scapulae", q(888, 780), "dehors")]
    p = SP.pose_humerus()
    q = lambda px, py: p.vers_modele(px, py)
    R["humerus"] = [("caput-humeri", q(655, 455), "pres"), ("tuberculum-majus", q(455, 330), "haut"),
                    ("tuberositas-deltoidea", q(370, 690), "dehors"), ("corpus-humeri", q(520, 860), "dehors"),
                    ("condylus-humeri", q(500, 1215), "bas"), ("fossa-olecrani", q(610, 1140), "derriere")]
    p = SP.pose_radius()
    q = lambda px, py: p.vers_modele(px, py)
    R["radius"] = [("tuber-olecrani", q(620, 1450), "haut"), ("incisura-trochlearis", q(440, 1735), "pres"),
                   ("caput-radii", q(400, 1815), "pres"), ("corpus-radii", q(430, 2150), "devant"),
                   ("corpus-ulnae", q(565, 2100), "derriere"), ("trochlea-radii", q(515, 2455), "bas")]
    g = SP.geom_pied_avant()
    R["pied-avant"] = [("ossa-carpi", g.pt(330, 935), "devant"), ("os-carpi-accessorium", g.pt(440, 935, 0.021), "derriere"),
                       ("os-metacarpale-iii", g.pt(240, 1240), "devant"), ("os-metacarpale-v", g.pt(502, 1300, 0.008), "dehors"),
                       ("phalanx-proximalis", g.pt(372, 1470), "devant"), ("phalanx-distalis", g.pt(374, 1720), "devant"),
                       ("ossa-sesamoidea", g.pt(372, 1395, 0.02), "derriere"), ("digitus-accessorius", g.pt(506, 1470, 0.02), "pres")]
    p = SP.pose_coxal()
    q = lambda px, py: p.vers_modele(px, py)
    R["coxal"] = [("tuber-coxae", q(360, 1480), "devant"), ("tuber-sacrale", q(645, 1180), "haut"),
                  ("crista-iliaca", q(430, 1205), "haut"), ("ala-ilii", q(500, 1330), "dehors"),
                  ("corpus-ilii", q(720, 1420), "dehors"), ("acetabulum", q(944, 1533), "dehors"),
                  ("spina-ischiadica", q(1000, 1292), "haut"), ("incisura-ischiadica-minor", q(1225, 1418), "haut"),
                  ("tuber-ischiadicum", q(1462, 1400), "derriere"), ("foramen-obturatum", SP.ACETABULE + SP.p3(0.06, -0.07, -0.05), "pres"),
                  ("pubis", SP.ACETABULE + SP.p3(0.0, -0.07, -0.05), "pres"), ("symphysis-pelvina", SP.ACETABULE + SP.p3(0.06, -0.085, -0.1), "pres")]
    p = SP.pose_femur()
    q = lambda px, py: p.vers_modele(px, py)
    R["femur"] = [("caput-femoris", q(475, 860), "dedans"), ("trochanter-major", q(250, 850), "haut"),
                  ("trochanter-minor", q(460, 1080), "dedans"), ("corpus-femoris", q(380, 1350), "devant"),
                  ("trochlea-femoris", q(380, 1840), "devant"), ("condyli-femoris", q(400, 1930), "derriere")]
    U = SP.n_(SP.GRASSET - SP.ACETABULE)
    devant = SP.n_(np.cross(U, SP.Z))
    if devant[0] > 0:
        devant = -devant
    cr = SP.GRASSET - U * 0.012 + devant * 0.034
    R["rotule"] = [("basis-patellae", cr - U * 0.024, "haut"), ("apex-patellae", cr + U * 0.026, "bas")]
    p = SP.pose_tibia()
    q = lambda px, py: p.vers_modele(px, py)
    R["tibia"] = [("condyli-tibiae", q(542, 830), "haut"), ("tuberositas-tibiae", q(600, 900), "devant"),
                  ("crista-tibiae", q(600, 1100), "devant"), ("corpus-tibiae", q(590, 1450), "devant"),
                  ("caput-fibulae", q(372, 880), "dehors"), ("corpus-fibulae", q(378, 1300), "dehors"),
                  ("malleolus-medialis", q(650, 1790), "dedans"), ("malleolus-lateralis", q(385, 1790), "dehors")]
    g = SP.geom_pied_arriere()
    R["pied-arriere"] = [("tuber-calcanei", SP.CALCANEUM, "haut"), ("trochlea-tali", g.pt(355, 915), "devant"),
                         ("os-tarsi-centrale", g.pt(380, 1028), "devant"), ("os-metatarsale-iii", g.pt(392, 1300), "devant"),
                         ("phalanx-proximalis", g.pt(300, 1550), "devant"), ("phalanx-distalis", g.pt(296, 1800), "devant"),
                         ("digitus-accessorius", g.pt(205, 1470, 0.02), "pres")]
    return R


def main(args):
    maillages = os_hd(args)
    reps = points_reperes()
    os_out, rep_out = [], {}
    for oid, (d, pair) in maillages.items():
        v = d["v"]
        code = d["code"].astype(np.int16)
        if oid == "coxal":
            code = parties_coxal(v, code)
        e = anatomie.emballer({**d, "code": code.astype(np.uint8)})
        e.update({"id": f"porc-{oid}", "pair": pair})
        os_out.append(e)
        rep_out[f"porc-{oid}"] = [{"id": f"porc-{rid}", "point": [round(float(x), 4) for x in coller(v, P, mode)]}
                                  for rid, P, mode in reps.get(oid, [])]
        print(f"   os {oid}: {len(v)} sommets, {len(d['f'])} triangles, {len(rep_out[f'porc-{oid}'])} repères", flush=True)
    donnees = {"muscles": [], "os": os_out, "reperes": rep_out}
    entete = ("// Fichier généré par outils/atelier_porc.py — ne pas modifier à la main.\n"
              "// Le squelette du porc en haute définition (os gauches et colonne) et les repères nommés de chaque os.\n"
              "// Chargé seulement par la page atelier.html (région « porc »).\n")
    with open(SORTIE, "w", encoding="utf-8", newline="") as fh:
        fh.write(entete + "(window.ATELIER_MAILLAGES = window.ATELIER_MAILLAGES || {}).porc = "
                 + json.dumps(donnees, separators=(",", ":")) + ";\n")
    print("écrit", os.path.relpath(SORTIE, RACINE), f"({os.path.getsize(SORTIE) // 1024} Ko)")


if __name__ == "__main__":
    main(sys.argv[1:])
