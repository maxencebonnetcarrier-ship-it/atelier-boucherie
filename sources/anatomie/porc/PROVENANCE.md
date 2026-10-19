# Gravures de référence (squelette du porc)

Deux ouvrages anciens, **domaine public** :

| Fichier | Contenu | Source |
|---|---|---|
| sisson-1914-p170.jpg à p191.jpg | chaque os du porc dessiné seul : vertèbres (fig. 164 à 174), côtes (175, 176), crâne de profil, de dessous et de dessus (177 à 179), mâchoire (181), palette (183), humérus (185, 186), radius et cubitus (187, 188), pied avant (189, 190), os coxal (191, 192), fémur (193, 194), tibia et péroné (195, 196), pied arrière (197, 198) | S. Sisson, *The Anatomy of the Domestic Animals*, 2e éd., Philadelphie, 1914, chapitre « Skeleton of the pig » — https://archive.org/details/anatomyofdomesti00sissuoft |
| sisson-1914-p182.jpg | crâne et mâchoire vus de derrière (fig. 182) | même ouvrage |
| cuyer-1905-fig38.jpg | squelette entier de profil (côté gauche) dans le contour du corps | É. Cuyer, *The Artistic Anatomy of Animals*, Londres, 1905, fig. 38 — https://commons.wikimedia.org/wiki/File:Artistic_anatomy_of_animals_(Page_58)_BHL22847451.jpg |

Les pages de Sisson ne sont gardées que recadrées sur leurs figures (coordonnées dans `outils/planches_porc.py`,
`RECADRAGES`).

Utilisation : `outils/planches_porc.py` détoure chaque figure ; `outils/squelette_porc.py` construit les os 3D
d'après ces contours (formes), posés aux articulations relevées sur Cuyer (places) ; `outils/atelier_porc.py`
fabrique la page atelier (os en haute définition et repères nommés).

Os de chaque grande coupe de boucherie : Agence canadienne d'inspection des aliments, « Manuel des coupes de
viande — Porc » — https://inspection.canada.ca/fr/etiquetage-aliments/etiquetage/industrie/produits-viande-volaille/coupes-viande/porc
