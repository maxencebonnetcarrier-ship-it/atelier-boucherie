# Délimite chaque os du bœuf sur les planches anatomiques de référence (sources/anatomie/, domaine
# public), pour construire ensuite les os 3D d'après leur vrai contour (outils/squelette.py).
#
# Principe (comme outils/zones.py pour les planches de découpe) : les traits du dessin sont repérés
# comme des lignes fines plus sombres que leur voisinage (filtre « chapeau noir ») ; les zones claires
# entre les traits sont numérotées ; un os = les zones qui contiennent ses points « graines ».
# Là où le trait d'un os s'ouvre sur le fond (pointillés, os qui se touchent), une « barrière »
# tracée à la main referme le contour. On bouche ensuite les trous (texte, hachures), on rend au
# contour l'épaisseur du trait, puis on vectorise.
#
#   python outils/planches_os.py            -> outils/cache/os_planches.json + outils/controle/os-<planche>.png
#   python outils/planches_os.py palette    -> seulement ces os
import json
import os
import sys

import cv2
import numpy as np

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOURCES = os.path.join(RACINE, "sources", "anatomie")
CONTROLE = os.path.join(RACINE, "outils", "controle")
SORTIE = os.path.join(RACINE, "outils", "cache", "os_planches.json")

PLANCHES_IMG = {
    "profil": os.path.join(SOURCES, "das-rind-tafel-3.jpg"),     # squelette entier, côté gauche
    "dessus": os.path.join(SOURCES, "das-rind-tafel-13.jpg"),    # squelette vu de dessus (fig. 57)
    "tete": os.path.join(SOURCES, "das-rind-tafel-9.jpg"),       # crâne de profil (fig. 31)
    "face": os.path.join(SOURCES, "das-rind-tafel-4.jpg"),       # squelette de face (fig. VI)
}
# réglage du repérage des traits : (taille du filtre, seuil)
TRAITS = {"profil": (9, 22), "dessus": (7, 22), "tete": (9, 22), "face": (9, 22)}

# Os : planche, graines (pixels de la planche), barrières (polylignes qui referment un contour),
# repères (points nommés de la planche : articulations, angles) qui servent à poser l'os dans le modèle.
OS = {
    "palette": {
        "planche": "profil", "graines": [(1450, 700), (1340, 950)],
        "barrieres": [
            [(1366, 556), (1395, 543), (1440, 556), (1500, 592), (1560, 632), (1605, 672), (1618, 698)],   # bord dorsal
            [(1366, 556), (1352, 600), (1335, 680), (1318, 760), (1300, 850), (1288, 940), (1282, 1010), (1284, 1062)],  # bord crânial
        ],
        "reperes": {"glene": (1333, 1078), "angle_cranial": (1370, 549), "angle_caudal": (1612, 694),
                    "epine": [(1306, 1030), (1318, 930), (1338, 830), (1368, 730), (1405, 650), (1440, 592)],
                    "bord_caudal": [(1600, 700), (1530, 770), (1445, 838), (1380, 905), (1345, 975), (1338, 1045)],
                    "bord_cranial": [(1370, 556), (1350, 640), (1325, 760), (1300, 880), (1290, 980), (1295, 1050)]},
    },
    "humerus": {
        "planche": "profil", "graines": [(1300, 1150), (1460, 1330), (1220, 1110)],
        "retirer": [[(1225, 1020), (1262, 1020), (1262, 1068), (1225, 1068)]],
        "reperes": {"tete": (1322, 1100), "coude": (1440, 1330)},
    },
    "radius": {
        "planche": "profil", "graines": [(1400, 1500), (1452, 1460), (1560, 1290), (1430, 1390), (1395, 1650)],
        "reperes": {"coude": (1440, 1330), "carpe": (1385, 1682)},
    },
    "carpe_avant": {   # deux rangées d'os du carpe + os accessoire (11), tracés à la main
        "planche": "profil", "graines": [],
        "ajouter": [[(1352, 1678), (1395, 1675), (1425, 1680), (1440, 1688), (1468, 1693), (1472, 1706), (1455, 1714),
                     (1428, 1712), (1424, 1738), (1388, 1742), (1356, 1738), (1350, 1715)]],
        "reperes": {"haut": (1385, 1682), "bas": (1385, 1738)},
    },
    "canon_avant": {   # métacarpe (12), tracé à la main : son bord arrière n'est qu'une ombre
        "planche": "profil", "graines": [],
        "ajouter": [[(1360, 1738), (1388, 1735), (1418, 1740), (1416, 1760), (1412, 1800), (1408, 1850), (1403, 1900),
                     (1398, 1950), (1395, 1975), (1398, 1990), (1392, 2004), (1378, 2010), (1360, 2008), (1340, 2004),
                     (1328, 1995), (1330, 1975), (1337, 1940), (1345, 1870), (1352, 1800), (1358, 1750)]],
        "reperes": {"haut": (1388, 1738), "boulet": (1362, 2000)},
    },
    "doigt_avant": {   # 1re, 2e et 3e phalanges (13), tracées à la main
        "planche": "profil", "graines": [],
        "ajouter": [[(1318, 2008), (1345, 2012), (1350, 2030), (1330, 2045), (1300, 2058), (1285, 2075), (1280, 2095),
                     (1268, 2112), (1262, 2130), (1240, 2138), (1200, 2140), (1172, 2135), (1165, 2125), (1185, 2105),
                     (1215, 2085), (1232, 2062), (1258, 2045), (1290, 2022)]],
        "reperes": {"boulet": (1330, 2015), "pince": (1168, 2130)},
    },
    "coxal_dessus": {  # os coxal gauche vu de dessus (planche 13, fig. 62), tracé à la main : tête en haut, gauche à gauche
        "planche": "dessus", "graines": [],
        "ajouter": [[(668, 1095), (680, 1083), (700, 1080), (720, 1085), (740, 1095), (760, 1105), (775, 1122), (782, 1140),
                     (778, 1150), (768, 1155), (758, 1152), (755, 1165), (758, 1182), (766, 1196), (780, 1205), (796, 1210),
                     (796, 1302), (790, 1306), (785, 1320), (770, 1335), (752, 1340), (740, 1335), (730, 1320), (722, 1303),
                     (738, 1288), (744, 1268), (740, 1250), (731, 1232), (729, 1212), (736, 1196), (737, 1180), (733, 1162),
                     (723, 1143), (707, 1125), (689, 1110), (674, 1103)]],
        "trous_poly": [[(780, 1215), (788, 1222), (791, 1240), (789, 1258), (781, 1266), (772, 1259), (768, 1240), (771, 1222)]],
        "reperes": {"hanche": (680, 1093), "acetabule": (733, 1218), "fesse": (745, 1325), "symphyse": (796, 1250),
                    "sacree": (768, 1128)},
    },
    "femur": {   # fémur gauche (18) et grand trochanter (19), tracé à la main (patte dessinée sans contour net)
        "planche": "profil", "graines": [],
        "ajouter": [[(2880, 748), (2905, 738), (2935, 712), (2965, 700), (2995, 712), (3005, 740), (2990, 775), (2968, 815),
                     (2948, 860), (2922, 915), (2898, 965), (2882, 1010), (2872, 1055), (2870, 1095), (2880, 1125),
                     (2897, 1148), (2905, 1172), (2898, 1196), (2872, 1207), (2840, 1207), (2810, 1195), (2790, 1175),
                     (2778, 1150), (2770, 1120), (2768, 1085), (2778, 1055), (2792, 1010), (2808, 955), (2825, 905),
                     (2842, 860), (2858, 822), (2866, 790), (2870, 765)]],
        "reperes": {"tete": (2905, 785), "grasset": (2852, 1168)},
    },
    "rotule": {
        "planche": "profil", "graines": [],
        "ajouter": [[(2752, 1058), (2775, 1060), (2790, 1080), (2795, 1110), (2788, 1140), (2770, 1158), (2750, 1155),
                     (2738, 1130), (2735, 1095), (2740, 1070)]],
        "reperes": {},
    },
    "tibia": {   # tibia gauche (21) et sa tubérosité (21')
        "planche": "profil", "graines": [],
        "ajouter": [[(2852, 1205), (2880, 1196), (2915, 1195), (2945, 1205), (2955, 1235), (2965, 1270), (2990, 1320),
                     (3030, 1390), (3068, 1455), (3098, 1515), (3110, 1565), (3108, 1600), (3090, 1612), (3068, 1606),
                     (3055, 1580), (3030, 1535), (2990, 1470), (2950, 1400), (2908, 1330), (2870, 1272), (2850, 1240)]],
        "reperes": {"plateau": (2885, 1205), "jarret": (3095, 1605)},
    },
    "tarse": {   # astragale (23), calcanéum (pointe du jarret) et os du tarse
        "planche": "profil", "graines": [],
        "ajouter": [[(3140, 1505), (3175, 1495), (3205, 1505), (3210, 1540), (3200, 1580), (3195, 1620), (3200, 1660),
                     (3195, 1700), (3160, 1712), (3120, 1708), (3100, 1690), (3095, 1655), (3080, 1625), (3095, 1600),
                     (3112, 1578), (3125, 1560), (3138, 1540)]],
        "reperes": {"haut": (3095, 1605), "bas": (3150, 1708)},
    },
    "canon_arriere": {   # métatarse (25)
        "planche": "profil", "graines": [],
        "ajouter": [[(3118, 1702), (3150, 1698), (3180, 1702), (3178, 1750), (3176, 1800), (3176, 1850), (3178, 1900),
                     (3180, 1950), (3195, 1975), (3195, 1995), (3180, 2008), (3155, 2010), (3132, 2005), (3122, 1990),
                     (3125, 1960), (3128, 1900), (3127, 1850), (3125, 1800), (3122, 1750)]],
        "reperes": {"haut": (3150, 1702), "boulet": (3155, 2000)},
    },
    "doigt_arriere": {   # phalanges (26)
        "planche": "profil", "graines": [],
        "ajouter": [[(3140, 2008), (3175, 2015), (3172, 2040), (3160, 2070), (3155, 2100), (3150, 2130), (3148, 2155),
                     (3120, 2165), (3080, 2165), (3040, 2160), (3025, 2150), (3045, 2140), (3075, 2120), (3090, 2095),
                     (3105, 2065), (3118, 2035)]],
        "reperes": {"boulet": (3155, 2012), "pince": (3028, 2155)},
    },
    "crane": {   # crâne et face sans la mâchoire (planche 9, fig. 31), tracé à la main
        "planche": "tete", "graines": [],
        "ajouter": [[(2052, 1652), (2090, 1600), (2140, 1480), (2170, 1390), (2195, 1335), (2155, 1336), (2210, 1290),
                     (2300, 1210), (2380, 1140), (2450, 1080), (2510, 1020), (2560, 960), (2600, 900), (2660, 840),
                     (2720, 790), (2790, 745), (2860, 712), (2930, 700), (2975, 720), (2995, 760), (3000, 820),
                     (2998, 880), (3010, 940), (3025, 990), (3015, 1035), (2995, 1050), (2985, 1090), (2965, 1085),
                     (2950, 1030), (2920, 1000), (2860, 1000), (2800, 1010), (2760, 1060), (2770, 1150), (2775, 1250),
                     (2772, 1345), (2700, 1390), (2600, 1445), (2500, 1495), (2440, 1525), (2420, 1485), (2350, 1490),
                     (2250, 1530), (2160, 1580), (2110, 1612), (2075, 1640)]],
        "reperes": {"incisif": (2052, 1652), "orbite": (2570, 990), "nuque": (2930, 700), "condyle_mandibule": (2925, 1002),
                    "incisives_bas": (2035, 1685), "corne": (2880, 690), "trou_sous_orbite": (2340, 1395),
                    "temporal": (2715, 900), "arcade": [(2615, 1055), (2690, 1035), (2770, 1000), (2840, 985)],
                    "dents_haut": [(2445, 1512), (2520, 1478), (2600, 1440), (2680, 1396), (2765, 1350)],
                    "narine": (2215, 1420), "occipital": (2990, 1000)},
    },
    "mandibule": {   # mâchoire inférieure gauche (fig. 31)
        "planche": "tete", "graines": [],
        "ajouter": [[(2030, 1682), (2060, 1655), (2120, 1622), (2200, 1602), (2300, 1586), (2400, 1562), (2440, 1546),
                     (2500, 1520), (2600, 1470), (2700, 1410), (2760, 1370), (2790, 1300), (2800, 1200), (2805, 1100),
                     (2825, 1030), (2838, 958), (2858, 962), (2870, 1000), (2895, 1010), (2930, 995), (2945, 1030),
                     (2955, 1090), (2975, 1180), (2995, 1280), (3000, 1335), (2985, 1420), (2960, 1480), (2920, 1530),
                     (2850, 1562), (2750, 1592), (2650, 1622), (2550, 1650), (2450, 1670), (2350, 1682), (2250, 1690),
                     (2150, 1692), (2080, 1692), (2040, 1695)]],
        "reperes": {"incisives": (2035, 1685), "condyle": (2925, 1002),
                    "dents_bas": [(2448, 1560), (2520, 1530), (2600, 1490), (2680, 1440), (2755, 1395)]},
    },
}


# ================================================================ colonne vertébrale (relevés à la main)
# Planche 3 (profil gauche, pixels) : épines des dorsales. Le haut de chaque épine est bien dessiné ; le bas
# est caché par la palette (T1 à T7) ou par les côtes. On relève donc le BOUT (milieu du bord supérieur),
# la PENTE du haut de l'épine (dx/dy, négatif = penchée vers la queue) et la LARGEUR au bout et à la base ;
# la BASE (sur l'arc vertébral) est le pied de l'épine, au-dessus de l'apophyse transverse de sa vertèbre
# (chaîne d'apophyses visible sous les épines de T8 à T13) ; de T2 à T7, bases régulièrement réparties.
EPINES_T = {   # nom : (bout, pente au bout, largeur au bout, largeur à la base)
    "T1": ((1301, 553), -0.20, 44, 50), "T2": ((1424, 519), -0.40, 46, 52), "T3": ((1524, 508), -0.52, 42, 54),
    "T4": ((1604, 511), -0.40, 42, 52), "T5": ((1675, 527), -0.60, 38, 50), "T6": ((1747, 530), -0.77, 33, 48),
    "T7": ((1812, 530), -0.85, 30, 46), "T8": ((1888, 538), -0.95, 28, 44), "T9": ((1960, 536), -0.97, 27, 42),
    "T10": ((2020, 542), -0.80, 25, 38), "T11": ((2047, 542), -0.45, 22, 34),
}
BASES_T = {"T1": (1257, 770), "T8": (1761, 672), "T9": (1839, 663), "T10": (1933, 651), "T11": (2003, 640),
           "T12": (2076, 618), "T13": (2121, 605)}
for _i in range(2, 8):     # T2 à T7 : bases réparties entre celles de T1 et de T8 (arc qui remonte vers le dos)
    _t = (_i - 1) / 7
    BASES_T[f"T{_i}"] = (round(1257 + (1761 - 1257) * _t), round(770 + (672 - 770) * _t))
# centres des corps des lombaires (entre les disques, planche 3) ; repères des épines des reins
CORPS_L = {"L1": (2169, 668), "L2": (2244, 668), "L3": (2318, 666), "L4": (2394, 664), "L5": (2472, 662), "L6": (2551, 660)}
# Planche 13, fig. 57 (squelette vu de dessus) : milieu de la colonne et niveau (y) de chaque lombaire
MILIEU_57 = 381
NIVEAU_57 = {"L1": 900, "L2": 931, "L3": 975, "L4": 1015, "L5": 1050, "L6": 1080}


def _epine_T(nom):
    """Contour (pixels de planche) d'une épine de dorsale : bande de la base au bout, droite en bas et
    orientée au bout comme sur la planche (courbe de Bézier), bout arrondi (tubérosité)."""
    (tx, ty), pente, lt, lb = EPINES_T[nom]
    bx, by = BASES_T[nom]
    d = np.array([pente, 1.0]); d /= np.linalg.norm(d)          # vers le bas, le long de l'épine
    haut = -d
    r = lt / 2
    Cb = np.array([tx, ty], float) - haut * r * 0.6              # centre de l'arrondi du bout
    B0 = np.array([bx, by + 14.0])
    L = np.linalg.norm(Cb - B0)
    B1 = Cb + d * L * 0.45
    ts = np.linspace(0, 1, 14)
    gauche, droite = [], []
    for t in ts:
        c = (1 - t) ** 2 * B0 + 2 * (1 - t) * t * B1 + t * t * Cb
        tg = 2 * (1 - t) * (B1 - B0) + 2 * t * (Cb - B1)
        tg = tg / np.linalg.norm(tg)
        n = np.array([-tg[1], tg[0]])
        w = (lb + (lt - lb) * t) / 2
        gauche.append(c + n * w); droite.append(c - n * w)
    n = np.array([-haut[1], haut[0]])
    cap = [Cb + haut * np.sin(a) * r * 0.6 + n * np.cos(a) * r for a in np.linspace(0, np.pi, 9)][1:-1]
    pts = gauche + cap + droite[::-1]
    return [(int(round(p[0])), int(round(p[1]))) for p in pts]


def _epine_L(haut, gauche_haut, droite_haut, taille, g_taille, d_taille, bas, g_bas, d_bas, prolonge=16):
    """Contour d'une épine de lombaire (rectangle à taille creuse, bord supérieur épaissi, coins arrondis)."""
    return [(g_bas, bas + prolonge), (g_bas, bas), (g_bas + (g_taille - g_bas) * 0.6, (bas + taille) / 2), (g_taille, taille),
            (gauche_haut + (g_taille - gauche_haut) * 0.35, (taille + haut) / 2 + 4), (gauche_haut, haut + 7),
            (gauche_haut + 4, haut + 1), (gauche_haut + 10, haut), (droite_haut - 10, haut), (droite_haut - 4, haut + 1),
            (droite_haut, haut + 7), (droite_haut + (d_taille - droite_haut) * 0.35, (taille + haut) / 2 + 4),
            (d_taille, taille), (d_bas + (d_taille - d_bas) * 0.6, (bas + taille) / 2), (d_bas, bas), (d_bas, bas + prolonge)]


for _n in EPINES_T:
    OS[f"epine_{_n}"] = {"planche": "profil", "graines": [], "ajouter": [_epine_T(_n)],
                         "reperes": {"base": BASES_T[_n], "bout": EPINES_T[_n][0]}}
for _n, _p in {   # épines rectangulaires : T12, T13 et les lombaires (relevées sur la planche 3)
    "T12": _epine_L(548, 2067, 2097, 585, 2063, 2098, 618, 2058, 2095),
    "T13": _epine_L(547, 2103, 2144, 576, 2102, 2142, 605, 2101, 2141),
    "L1": _epine_L(547, 2159, 2214, 577, 2165, 2207, 602, 2160, 2212),
    "L2": _epine_L(546, 2229, 2282, 577, 2233, 2276, 600, 2230, 2280),
    "L3": _epine_L(539, 2297, 2356, 570, 2303, 2346, 596, 2299, 2352),
    "L4": _epine_L(535, 2370, 2433, 566, 2378, 2426, 592, 2375, 2431),
    "L5": _epine_L(524, 2449, 2509, 556, 2455, 2503, 588, 2452, 2508),
    "L6": _epine_L(518, 2524, 2579, 550, 2528, 2576, 584, 2522, 2580),
}.items():
    OS[f"epine_{_n}"] = {"planche": "profil", "graines": [], "ajouter": [[(round(x), round(y)) for x, y in _p]],
                         "reperes": {"base": BASES_T.get(_n, ((_p[1][0] + _p[-2][0]) / 2, _p[1][1])),
                                     "corps": CORPS_L.get(_n)}}
# apophyses articulaires craniales (et mamillaires) des lombaires : bosses au pied de chaque épine, devant
ARTICULAIRES_L = {"L1": (2142, 617), "L2": (2208, 609), "L3": (2279, 602), "L4": (2359, 597), "L5": (2436, 590),
                  "L6": (2510, 584)}
# apophyses transverses des lombaires, côté gauche, vue de dessus (planche 13, fig. 57)
for _n, _p in {
    "L1": [(368, 891), (350, 890), (334, 891), (328, 895), (327, 903), (331, 908), (345, 909), (368, 910)],
    "L2": [(368, 923), (345, 920), (325, 917), (314, 918), (311, 924), (313, 931), (325, 935), (340, 942), (368, 946)],
    "L3": [(368, 969), (342, 968), (318, 965), (303, 962), (299, 967), (300, 975), (303, 980), (322, 984), (342, 986), (368, 985)],
    "L4": [(368, 1009), (330, 1006), (305, 1004), (296, 1003), (293, 1010), (294, 1020), (301, 1025), (322, 1027), (342, 1028),
           (368, 1025)],
    "L5": [(368, 1040), (330, 1039), (300, 1041), (289, 1042), (286, 1047), (289, 1052), (300, 1056), (323, 1061), (368, 1059)],
    "L6": [(368, 1076), (330, 1072), (310, 1070), (301, 1073), (299, 1078), (305, 1082), (330, 1086), (368, 1090)],
}.items():
    OS[f"transverse_{_n}"] = {"planche": "dessus", "graines": [], "ajouter": [_p], "reperes": {"niveau": NIVEAU_57[_n]}}
# sacrum : crête (épines soudées) vue de profil, planche 3 ; ligne de sa face dorsale (bord des parties
# latérales, avec les trous sacrés) ; contour vu de dessus, moitié gauche (planche 13, fig. 57)
OS["sacrum_crete"] = {
    "planche": "profil", "graines": [],
    "ajouter": [[(2637, 496), (2657, 484), (2695, 477), (2732, 473), (2770, 470), (2800, 469), (2824, 468), (2830, 474),
                 (2836, 492), (2842, 472), (2847, 463), (2870, 461), (2890, 463), (2894, 475), (2897, 490), (2899, 506),
                 (2899, 530), (2860, 541), (2820, 547), (2780, 553), (2740, 560), (2700, 567), (2660, 571), (2636, 569),
                 (2630, 540)]],      # le bas plonge dans le corps du sacrum (sous sa face dorsale)
    "reperes": {"axe_avant": (2600, 635), "axe_arriere": (2900, 555),
                "face_dorsale": [(2610, 560), (2650, 556), (2691, 552), (2732, 543), (2770, 536), (2807, 532), (2845, 528),
                                 (2882, 521), (2901, 513)],
                "trous": [(2690, 551), (2762, 540), (2834, 527), (2884, 519)]},
}
OS["sacrum_dessus"] = {
    "planche": "dessus", "graines": [],
    "ajouter": [[(381, 1110), (365, 1112), (348, 1116), (332, 1121), (327, 1130), (331, 1141), (338, 1150), (339, 1175),
                 (340, 1200), (345, 1210), (347, 1225), (348, 1240), (352, 1250), (350, 1262), (360, 1272), (381, 1276)]],
    "reperes": {"avant": 1110, "arriere": 1276},
}


def carte_traits(gris, planche):
    k, s = TRAITS[planche]
    g = cv2.GaussianBlur(gris, (3, 3), 0)
    bh = cv2.morphologyEx(g, cv2.MORPH_BLACKHAT, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    t = (bh > s).astype(np.uint8)
    return cv2.morphologyEx(t, cv2.MORPH_CLOSE, np.ones((3, 3), np.uint8))


def masque_os(gris, traits, spec):
    t = traits.copy()
    for b in spec.get("barrieres", []):
        cv2.polylines(t, [np.asarray(b, np.int32)], False, 1, 3)
    for b in spec.get("ouvertures", []):          # trait parasite (texte, hachure) qui coupe l'os en deux
        cv2.polylines(t, [np.asarray(b, np.int32)], False, 0, 3)
    if not spec.get("graines"):                 # os tracé entièrement à la main (contour peu marqué sur la planche)
        m = np.zeros_like(t)
        for poly in spec.get("ajouter", []):
            cv2.fillPoly(m, [np.asarray(poly, np.int32)], 1)
        for poly in spec.get("trous_poly", []):
            cv2.fillPoly(m, [np.asarray(poly, np.int32)], 0)
        return m
    n, lab = cv2.connectedComponents(1 - t, connectivity=4)
    ids = {int(lab[y, x]) for x, y in spec["graines"] if t[y, x] == 0}
    m = np.isin(lab, list(ids)).astype(np.uint8)
    # trous (texte, points, hachures) : tout ce qui n'est pas relié au dehors de l'os
    ys, xs = np.where(m)
    x0, x1, y0, y1 = max(xs.min() - 6, 0), xs.max() + 7, max(ys.min() - 6, 0), ys.max() + 7
    if m.sum() > 400000:
        raise ValueError("zone énorme : une graine est tombée dans le fond (aire %d px)" % m.sum())
    sub = m[y0:y1, x0:x1].copy()
    sub = cv2.morphologyEx(sub, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7)))
    dehors = sub.copy()
    cv2.floodFill(dehors, np.zeros((sub.shape[0] + 2, sub.shape[1] + 2), np.uint8), (0, 0), 2)
    sub = (dehors != 2).astype(np.uint8)
    # le contour passe au milieu du trait : on regagne l'épaisseur du trait (≈ 2 px)
    sub = cv2.dilate(sub, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
    m = np.zeros_like(m)
    m[y0:y1, x0:x1] = sub
    for x, y in spec.get("trous", []):           # vrais trous de l'os (trou obturé...) : on les rouvre
        if t[y, x] == 0:
            m[lab == lab[y, x]] = 0
    for p in spec.get("couper", []):             # demi-plan à garder : [(x0, y0), (x1, y1)] -> on garde la gauche du segment
        (ax, ay), (bx, by) = p
        yy, xx = np.mgrid[0:m.shape[0], 0:m.shape[1]]
        m[((bx - ax) * (yy - ay) - (by - ay) * (xx - ax)) < 0] = 0
    for p in spec.get("retirer", []):            # zone à exclure (morceau d'un autre os happé)
        cv2.fillPoly(m, [np.asarray(p, np.int32)], 0)
    for p in spec.get("ajouter", []):            # zone cachée par un autre os, complétée à la main
        cv2.fillPoly(m, [np.asarray(p, np.int32)], 1)
    return m


def contour(m):
    cs, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    c = max(cs, key=cv2.contourArea)
    c = cv2.approxPolyDP(c, 1.2, True)[:, 0, :]
    return c.tolist()


def trous(m):
    """Contours des trous intérieurs (assez grands) de la zone."""
    cs, h = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    for c, hh in zip(cs, h[0]):
        if hh[3] >= 0 and cv2.contourArea(c) > 60:
            out.append(cv2.approxPolyDP(c, 1.2, True)[:, 0, :].tolist())
    return out


def main(noms):
    sortie = json.load(open(SORTIE, encoding="utf-8")) if os.path.exists(SORTIE) else {}
    par_planche = {}
    for nom, spec in OS.items():
        if noms and nom not in noms:
            continue
        par_planche.setdefault(spec["planche"], []).append(nom)
    for planche, liste in par_planche.items():
        im = cv2.imread(PLANCHES_IMG[planche])
        gris = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
        traits = carte_traits(gris, planche)
        vue = im.copy()
        rng = np.random.default_rng(7)
        for nom in liste:
            spec = OS[nom]
            m = masque_os(gris, traits, spec)
            c = contour(m)
            sortie[nom] = {"planche": planche, "contour": c, "trous": trous(m), "aire": int(m.sum()),
                           "reperes": spec.get("reperes", {}), "empreinte": empreinte(spec)}
            couleur = tuple(int(v) for v in rng.integers(40, 230, 3))
            calque = vue.copy()
            calque[m > 0] = couleur
            vue = cv2.addWeighted(vue, 0.5, calque, 0.5, 0)
            cv2.polylines(vue, [np.asarray(c, np.int32)], True, couleur, 2)
            for x, y in spec["graines"]:
                cv2.circle(vue, (x, y), 6, (0, 0, 255), -1)
            for b in spec.get("barrieres", []):
                cv2.polylines(vue, [np.asarray(b, np.int32)], False, (255, 0, 255), 3)
            print(f"{nom:16s} {planche:7s} aire {int(m.sum()):7d} px, {len(c)} points")
        os.makedirs(CONTROLE, exist_ok=True)
        cv2.imwrite(os.path.join(CONTROLE, f"os-{planche}.jpg"), vue)
    with open(SORTIE, "w", encoding="utf-8", newline="") as fh:
        json.dump(sortie, fh)



def empreinte(spec):
    """Empreinte de la description d'un os (graines, tracés, repères) : le cache est refait si elle change."""
    import hashlib
    return hashlib.sha1(json.dumps(spec, sort_keys=True, default=list).encode()).hexdigest()[:16]


def os_planche(nom):
    """Contour et repères d'un os, depuis le cache (le recalcule s'il manque ou si sa description a changé)."""
    d = json.load(open(SORTIE, encoding="utf-8")) if os.path.exists(SORTIE) else {}
    if nom not in d or d[nom].get("empreinte") != empreinte(OS[nom]):
        main([nom])
        d = json.load(open(SORTIE, encoding="utf-8"))
    return d[nom]


if __name__ == "__main__":
    main(sys.argv[1:])
