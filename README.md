# Atelier Boucherie

Appli pour apprendre la boucherie ou se perfectionner. Les quatre animaux sont en **3D, tous dans le même style** : tu les fais tourner, tu touches une pièce et l'appli t'affiche :

- son **mode de cuisson** : griller, poêler, rôtir, sauter, braiser / mijoter, bouillir / pocher, cru ;
- ce qu'il faut **savoir** sur la pièce (où elle se trouve, ses caractéristiques) ;
- les **transformations bouchères** possibles (pavé, rôti, bourguignon, osso-buco…) ;
- des **recettes simples** à proposer au client, avec une phrase toute prête pour le comptoir ;
- la **même région chez les autres animaux**, d'après le comparatif des dénominations.

Contenu : 4 animaux (bœuf, veau, porc, agneau), 69 pièces et 54 recettes.

## Ouvrir l'appli

Double-clique sur `app/index.html`. Elle fonctionne sans internet et sans installation, dans n'importe quel navigateur.

- **Tourner l'animal** : glisse à la souris ou au doigt (de gauche à droite). Les boutons Avant, Profil, Arrière et Dessus donnent les vues classiques ; + et − zooment.
- **Couleurs** : rouge vif = cuisson rapide, bordeaux = cuisson lente, orangé = les deux, rosé = abat. Ce qui n'est pas une pièce garde la robe de l'animal (bœuf fauve, veau crème : tête et bas des pattes). Les traits clairs sont les lignes de découpe.
- **Noms** : le nom de chaque pièce est écrit dessus, comme sur une planche. Le bouton « Noms » les masque. Quand deux noms se chevauchent, le plus petit est caché : tourne l'animal ou zoome pour le voir.
- **Filtre par cuisson** : « Voir les pièces à : Braiser » colore toutes les pièces à braiser et grise les autres.
- **Liste sous l'animal** : choisir une pièce dans la liste fait **tourner l'animal** pour te la montrer (pratique pour les petites pièces : onglet, hampe, araignée…).
- **Comparatif** : c'est la fiche « Comparatif dénomination musculaire ». Clique sur une case pour surligner la région sur l'animal.
- **Adresse directe** : `index.html#boeuf/paleron` ouvre directement la fiche du paleron.

### Squelette (bœuf)

- Le bouton **Squelette** rend le corps transparent et montre les **17 os ou groupes d'os** à leur place : tête, vertèbres du cou, du dos et des reins, sacrum, queue, côtes, sternum, palette, boîte à moelle (humérus), os des jarrets, canons, os du bassin, fémur, rotule.
- **Style dessin animé, vraies formes** : chaque os garde sa forme réelle, simplifiée. On reconnaît la tête et le col du fémur, l'arête de la palette, le trou du bassin, la pointe du coude et du jarret, les deux doigts du pied, les « étagères » des vertèbres des reins, le crâne avec ses orbites, les chevilles des cornes et les dents. Les cartilages (bout des côtes, bord de la palette) sont bleutés. L'animal et les os ont des ombres en aplats et un contour foncé.
- **Gros plan** : choisir un os dans la liste fait tourner l'animal, rapproche la caméra et centre l'os à l'écran.
- **Touche un os** : sa fiche donne son nom de boucher et son nom savant, les **pièces posées dessus** et un conseil « Au désossage ». Ces pièces restent colorées sur le corps transparent.
- **Éclater / Rassembler** : les os s'écartent les uns des autres, puis se remettent en place, comme pour remonter le squelette.
- Dans la fiche de chaque pièce, la rubrique **« Sur quel os ? »** mène à l'os correspondant.
- Adresse directe : `index.html#boeuf/squelette/palette`.
- Sources : la fiche « Le squelette du bovin » (École des Métiers Bigard) pour la place des os ; le [tableau des pièces de bœuf](http://www.ecomet.fr/tableau_des_pieces_de_beef.pdf) (colonne OS) et l'article [Désossage](https://fr.wikipedia.org/wiki/D%C3%A9sossage) de Wikipédia pour le lien os ↔ pièces. Les fiches sont dans `app/data/os.js`, et la forme des os dans `outils/squelette.py`.

## Sur le téléphone

L'appli est en ligne à l'adresse **https://maxencebonnetcarrier-ship-it.github.io/atelier-boucherie/** (GitHub Pages, dépôt `maxencebonnetcarrier-ship-it/atelier-boucherie`).

1. Ouvre le lien dans le navigateur du téléphone : Safari sur iPhone, Chrome sur Android.
2. Ajoute l'appli à l'écran d'accueil. Sur iPhone : bouton Partager, puis « Sur l'écran d'accueil ». Sur Android : menu ⋮, puis « Ajouter à l'écran d'accueil ».
3. L'icône « Boucherie » s'ouvre alors en plein écran, comme une appli.

Pour **mettre à jour** le site après une modification : commite, puis lance `bash outils/publier.sh`. Le site est servi depuis la branche `gh-pages`, qui ne contient que le dossier `app/`. Les deux photos des fiches de cours (squelette, comparatif) restent hors du dépôt (voir `.gitignore`).

## Organisation du dossier

| Chemin | Rôle |
|---|---|
| `app/` | L'appli : `index.html`, `styles.css`, `app.js` (interface) et `vue3d.js` (affichage 3D) |
| `app/data/pieces.js` | Fiches des pièces, modes de cuisson, régions du comparatif. **C'est ici qu'on corrige ou complète le contenu.** |
| `app/data/recettes.js` | Les recettes. Les pièces y renvoient par leur identifiant. |
| `app/data/modeles3d.js` | Les modèles 3D et la carte des pièces de chaque animal. Ce fichier est **généré**, ne pas le modifier à la main. |
| `app/vendor/three.min.js` | Three.js r160, le moteur 3D (licence MIT, copiée à côté), embarqué pour marcher sans internet. |
| `sources/` | Tes images d'origine (planches, squelette, comparatif). Les planches servent de guide pour placer les découpes. |
| `outils/` | Les scripts de fabrication des modèles et de vérification. |

## Modifier le contenu

1. Modifie `app/data/pieces.js` ou `app/data/recettes.js`.
2. Lance `node outils/verifier.mjs`. Ce contrôle vérifie que chaque pièce du modèle 3D a sa fiche et inversement, que chaque fiche est complète (cuisson, transformations, recettes existantes) et que chaque pièce est assez grande pour être touchée.
3. Lance `node outils/test-clic.mjs`. Ce test ouvre l'appli dans Edge ou Chrome, sans fenêtre : pour chacune des 69 pièces, il tourne l'animal vers elle et clique réellement dessus. Il teste aussi le survol, la rotation, la liste, le filtre, le comparatif et le toucher sur téléphone, puis enregistre des captures dans `outils/captures/`.

## Comment les modèles 3D sont fabriqués

1. **Les formes** (`outils/formes.py`) : chaque animal est sculpté en assemblant des volumes arrondis (tronc, cuisses, épaules, cou, tête, pattes). Les quatre utilisent le même vocabulaire de formes, d'où le style commun. Chaque animal porte aussi ses **repères anatomiques** (museau, garrot, hanche, jarret…).
2. **Les découpes** (`outils/zones.py`) : le découpage de chaque planche de `sources/` est lu automatiquement, à partir d'un point posé dans chaque pièce (une « graine »).
3. **Le report** (`outils/modeles3d.py`) : la planche est déformée pour que ses repères tombent sur ceux du modèle. Chaque pièce se retrouve ainsi à sa place sur le corps 3D, vu de profil. Le script fabrique ensuite la surface, l'allège à 16 000 triangles par animal et écrit `app/data/modeles3d.js`.

```
pip install opencv-python-headless numpy scikit-image fast-simplification
python outils/zones.py          # découpage des planches
python outils/modeles3d.py      # modèles 3D (ou : python outils/modeles3d.py porc)
node outils/apercu.mjs boeuf depart profil avant arriere dessus   # captures 3D
```

- `outils/controle/carte_<animal>.png` montre les pièces reportées sur le profil du modèle, avec les repères en rouge. Regarde-le après chaque génération.
- `python outils/modeles3d.py apercu <animal>` dessine la silhouette quadrillée d'un modèle. C'est utile pour placer un repère.
- Si une pièce tombe mal, déplace le repère concerné : dans `formes.py` côté modèle, dans `REPERES_PLANCHE` (`modeles3d.py`) côté planche. Pour le bas des pattes, une règle directe se met dans `CORRECTIONS`.

## Points à vérifier avec ton formateur

- Le contenu (cuissons, transformations, recettes) a été rédigé pour l'appli : **fais-le relire**.
- **Porc** : une petite zone sans nom, sous le travers, a été rattachée à la **poitrine** (hypothèse).
- **Agneau** : la gravure est ancienne et ses pointillés sont ouverts. Le haut de côtelettes et les pieds sont donc tracés à la main, avec des contours approximatifs. Sur la gravure, l'agneau broute : sa tête et son collet sont reportés sur un agneau debout.
- **Squelette** : les os sont **stylisés** et placés d'après la fiche Bigard, pas mesurés sur un vrai squelette. Les conseils « Au désossage » ont été rédigés pour l'appli, à partir du tableau des pièces et de Wikipédia : **fais-les valider**. Pour la macreuse à bifteck, les sources ne s'accordent pas sur le muscle exact ; elles s'accordent sur l'os (la palette), qui est le seul point affiché.
- **Modèles 3D** : ce sont des animaux **stylisés**, pas des modèles anatomiques. Les découpes sont reportées des planches, vues de profil : les frontières entre pièces sont donc approximatives, surtout sur le dessus du dos et sous le ventre.
- **Comparatif** : la fiche place le **merlan** dans l'épaule du bœuf, alors que la planche du bœuf le met dans la cuisse (avec la tende de tranche). L'appli recopie la fiche telle quelle.
- **Droits** : l'image du porc est une image Adobe Stock avec filigrane (n° 396567493). Elle **n'est plus affichée** dans l'appli : seul son découpage sert de guide. Mais elle est encore présente dans `sources/`, donc dans le dépôt public.
