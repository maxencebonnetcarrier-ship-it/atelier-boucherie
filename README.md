# Atelier Boucherie

Appli pour apprendre la boucherie ou se perfectionner. Tu cliques sur une pièce d'un animal et elle t'affiche :

- son **mode de cuisson** : griller, poêler, rôtir, sauter, braiser / mijoter, bouillir / pocher, cru ;
- ce qu'il faut **savoir** sur la pièce (où elle se trouve, ses caractéristiques) ;
- les **transformations bouchères** possibles (pavé, rôti, bourguignon, osso-buco…) ;
- des **recettes simples** à proposer au client, avec une phrase toute prête pour le comptoir ;
- la **même région chez les autres animaux**, d'après le comparatif des dénominations.

Contenu : 4 animaux (bœuf, veau, porc, agneau), 69 pièces et 54 recettes.

## Ouvrir l'appli

Double-clique sur `app/index.html`. Elle fonctionne sans internet et sans installation, dans n'importe quel navigateur.

- **Filtre par cuisson** : « Voir les pièces à : Braiser » colore sur la planche toutes les pièces à braiser.
- **Liste sous la planche** : sert pour les petites zones (onglet, hampe, araignée…), plus faciles à choisir là.
- **Comparatif** : c'est la fiche « Comparatif dénomination musculaire ». Clique sur une case pour surligner la région sur la planche.
- **Adresse directe** : `index.html#boeuf/paleron` ouvre directement la fiche du paleron.

## Organisation du dossier

| Chemin | Rôle |
|---|---|
| `app/` | L'appli : `index.html`, `styles.css`, `app.js` |
| `app/data/pieces.js` | Fiches des pièces, modes de cuisson, régions du comparatif. **C'est ici qu'on corrige ou complète le contenu.** |
| `app/data/recettes.js` | Les recettes. Les pièces y renvoient par leur identifiant. |
| `app/data/zones.js` | Les zones cliquables. Ce fichier est **généré**, ne pas le modifier à la main. |
| `app/img/` | Les planches telles qu'elles apparaissent dans l'appli. |
| `sources/` | Tes images d'origine (planches, squelette, comparatif). |
| `outils/` | Les scripts de génération et de vérification. |

## Modifier le contenu

1. Modifie `app/data/pieces.js` ou `app/data/recettes.js`.
2. Lance `node outils/verifier.mjs`. Ce contrôle vérifie que chaque zone a sa fiche et que chaque fiche est complète (cuisson, transformations, recettes existantes). Il vérifie aussi qu'un clic au centre d'une zone tombe bien sur la bonne pièce.
3. Lance `node outils/test-clic.mjs`. Ce test ouvre l'appli dans Edge ou Chrome, sans fenêtre, et clique réellement sur les 69 pièces. Il teste aussi le filtre, le comparatif et l'affichage téléphone, puis enregistre des captures dans `outils/captures/`.

## Changer une planche ou en ajouter une

Les zones sont découpées **automatiquement** à partir des images de `sources/`. Le script `outils/zones.py` repère chaque zone colorée grâce à un point posé à l'intérieur (une « graine »), puis la transforme en forme cliquable.

```
pip install opencv-python-headless numpy
python outils/zones.py
```

- `outils/controle/<animal>.png` montre le découpage obtenu : chaque pièce y est colorée et nommée. Regarde-le après chaque génération.
- Pour trouver les coordonnées d'une nouvelle graine, utilise `python outils/composantes.py <image> <mode> <sortie.png> 3`. Ce script numérote les zones détectées.
- Une zone que la planche ne ferme pas (pointillés trop espacés, partie trop fine) se trace à la main dans la rubrique `manuel` de `zones.py`.

## Points à vérifier avec ton formateur

- Le contenu (cuissons, transformations, recettes) a été rédigé pour l'appli : **fais-le relire**.
- **Porc** : une petite zone sans nom, sous le travers, a été rattachée à la **poitrine** (hypothèse).
- **Agneau** : la gravure est ancienne et ses pointillés sont ouverts. Le haut de côtelettes et les pieds sont donc tracés à la main, avec des contours approximatifs.
- **Comparatif** : la fiche place le **merlan** dans l'épaule du bœuf, alors que la planche du bœuf le met dans la cuisse (avec la tende de tranche). L'appli recopie la fiche telle quelle.
- **Droits** : l'image du porc est une image Adobe Stock avec filigrane (n° 396567493). Elle convient pour un usage personnel, mais il faudra la remplacer si l'appli est publiée.
