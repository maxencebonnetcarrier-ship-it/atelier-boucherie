// Classeur de découpe du bœuf (photos fournies par l'utilisateur, gardées hors du dépôt public).
// Texte retranscrit page par page :
//  - guide : « Guide de découpe de la viande bovine » (51 pages) : dénomination de vente, étoiles,
//    mention de cuisson, morceau et niveau de préparation ; « p » = numéro de page du guide.
//  - magasin : fiches de découpe du rayon boucherie (contrôle avant découpe, parage, découpe,
//    mise en barquette, poids des portions).
//  - noms : petits noms et sous-muscles cités par les tableaux « Le bœuf » n° 1 à 3 (L.T. Éditions
//    Jacques Lanore) et par le dépliant Interbev « Chez le boucher, mieux connaître les morceaux ».
// Chaque clé doit être une pièce du bœuf (data/pieces.js) ; outils/verifier.mjs le contrôle.

window.CLASSEUR = {
  sources: {
    guide: "« Guide de découpe de la viande bovine » (classeur, 51 pages)",
    magasin: "Fiches de découpe du rayon boucherie (classeur magasin)",
    tableaux: "Tableaux « Le bœuf » n° 1 à 3 (L.T. Éditions Jacques Lanore)",
    interbev: "Dépliant Interbev « Chez le boucher, mieux connaître les morceaux » (la-viande.fr)",
  },
  // Dépliant Interbev, retranscrit.
  etoiles: "Au rayon, la viande de bœuf porte trois informations : le nom ou le type de morceau, son mode de cuisson, "
    + "et un repère de tendreté (morceaux à griller ou à rôtir) ou de moelleux (morceaux à mijoter) donné par 1 à 3 étoiles. "
    + "★★★ = le plus tendre ou le plus moelleux.",
  lexique: [
    ["Parer", "retirer le gras, les nerfs et les parties abîmées pour présenter la viande."],
    ["Éplucher", "retirer les peaux nacrées (aponévroses) et les membranes qui couvrent le muscle."],
    ["Affranchir", "couper une extrémité ou un bord moins tendre pour ne garder que le cœur ; les « affranchis » partent en bourguignon ou en haché."],
    ["Dénerver", "retirer les nerfs (tendons, aponévroses épaisses)."],
    ["Barder, ficeler", "entourer d’une fine tranche de gras (la barde) puis ficeler ; les fiches magasin limitent la barde à 10 % du poids (13 % pour les tournedos)."],
    ["PAD", "prêt à découper."],
  ],
  // Guide, pages 48 à 50 : assemblages de plusieurs muscles.
  assemblages: [
    { nom: "Bourguignon ★★★ ou Pot-au-feu ★★★", mention: "À mijoter", texte: "Basse côte, collier, paleron (sans tête de nerf, épluché), jumeau, macreuse à braiser, nerveux de gîte noix, jarret, queue, joue, et tous les muscles des gammes Steak ★★★ et Rôti ★★★ avec leurs affranchis ; un seul muscle ou un mélange.", p: 48 },
    { nom: "Bourguignon ★★ ou Pot-au-feu ★★", mention: "À mijoter", texte: "Plat de côtes découvert, dessus de côte, plat de côtes, rond de gîte noix, gîte noix, poitrine (gros bout, milieu, tendron) en mélange, et tous les muscles avec leurs affranchis.", p: 48 },
    { nom: "Pièces à fondue", mention: "", texte: "Tous les muscles des gammes Steak ★★★ et Rôti ★★★, en morceaux ou en petits cubes.", p: 50 },
    { nom: "Pièces à brochettes", mention: "", texte: "Tous les muscles des gammes Steak ★★★, Rôti ★★★, Steak ★★ et Rôti ★★.", p: 50 },
    { nom: "Cuisson sur pierre", mention: "", texte: "Muscles des gammes Steak ★★★, Rôti ★★★, Steak ★★ et Rôti ★★, en tranches fines de 5 mm au plus.", p: 49 },
    { nom: "Carpaccio", mention: "", texte: "Muscles des gammes Rôti ★★★, Rôti ★★ et Rôti ★, en tranches très fines de 2 mm au plus.", p: 49 },
    { nom: "Émincés", mention: "", texte: "Muscles des gammes Steak ★★★, Rôti ★★★, Steak ★★, Rôti ★★, Steak ★ et Rôti ★, en fines lanières.", p: 49 },
  ],
  boeuf: {
    "plat-de-joue": {
      guide: [
        { nom: "Joue", etoiles: 3, mention: "À mijoter", morceau: "Joue", preparation: "Viande préparée exclusivement à partir de joues (noix et contre-joue).", p: 45 },
      ],
      noms: ["Noix de joue", "Contre-joue"],
    },
    "collier": {
      guide: [
        { nom: "Bourguignon ou Pot-au-feu", etoiles: 3, mention: "À mijoter", morceau: "Collier", preparation: "Le collier fait partie des muscles admis en Bourguignon ★★★ et Pot-au-feu ★★★.", p: 48 },
      ],
      magasin: [
        { titre: "Collier", decoupe: "Affranchir la saignée (en bourguignon ★★★). Le reste, sans os, part en pot-au-feu ★★★ ou en bourguignon ★★★.", barquettes: ["Pot-au-feu ★★★", "Bourguignon ★★★"] },
      ],
      noms: ["Salière (contre les 2 premières vertèbres du cou)", "Saignée", "Griffe (partie externe)", "Veine maigre", "Veine grasse"],
    },
    "gros-bout-de-poitrine": {
      guide: [
        { nom: "Poitrine", etoiles: 1, mention: "À mijoter", morceau: "Gros bout, milieu, tendron et flanchet", preparation: "Viande désossée, d’une seule pièce ou en mélange.", p: 47 },
      ],
      magasin: [
        { titre: "Poitrine : flanchet et gros bout", barquettes: ["Poitrine ★ à griller", "Poitrine ★ à mijoter", "Poitrine ★ à mijoter en caissette"], poids: ["Poitrine ★ à mijoter : 500 g", "Poitrine ★ à griller : 300 g"] },
      ],
      noms: ["Sur les 2 premières sternèbres et 2 cartilages (tableau n° 1)"],
    },
    "basses-cotes": {
      guide: [
        { nom: "Basse côte", etoiles: 2, mention: "À griller", morceau: "Basse côte affranchie", preparation: "Désossée, parée, sans « nerf » cervical, affranchie côté nuque et côté bretelles, avec ou sans pièce parée ; tranchée dans la largeur.", p: 40 },
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Pièce parée affranchie", preparation: "Parée et épluchée, affranchie de la pointe côté nuque et collier ; tranchée dans la largeur.", p: 41 },
        { nom: "Bourguignon ou Pot-au-feu", etoiles: 3, mention: "À mijoter", morceau: "Basse côte", preparation: "La basse côte fait partie des muscles admis en Bourguignon ★★★.", p: 48 },
      ],
      magasin: [
        { titre: "Basse côte", controle: "Livrée désossée ; on peut aussi la couper avec l’os l’été.", parage: "Basse côte désossée, parée sur ses 4 faces ; les affranchis partent en bourguignon ★★.", decoupe: "Tranches de 1 cm : basse côte ★★ ou ★★★, à griller ou à braiser." },
      ],
      noms: ["Surlonge (sur les 2 premières côtes)", "Entrecôtes découvertes (sur les 3 côtes suivantes)", "Pièce parée : derrière de paleron, 1er talon, persillé"],
    },
    "cotes-entrecotes": {
      guide: [
        { nom: "Entrecôte", etoiles: 3, mention: "À griller", morceau: "Entrecôte parée sans dessus de côte et sans nerf dorsal", preparation: "Milieu de train de côtes (5 côtes) désossé, sans dessus de côte, sans « nerf » dorsal, bretelles coupées de 3 à 5 cm de la noix ; tranché dans la largeur.", p: 16 },
        { nom: "Côte", etoiles: 3, mention: "À griller", morceau: "Côte", preparation: "Milieu de train de côtes : les 5 côtes du milieu, la dernière côte de la basse côte et les 2 premières côtes du faux-filet ; dévertébré, sans dessus de côtes ni « nerf » dorsal, bretelle de moins de 5 cm ; tranché dans la largeur.", p: 16 },
      ],
      magasin: [
        { titre: "Entrecôte", parage: "Désosser les côtes. Retirer l’excédent des baguettes et les intercostaux.", decoupe: "Trancher des entrecôtes d’au moins 1 cm.", barquettes: ["1 entrecôte ★★★", "2 entrecôtes ★★★"] },
        { titre: "Train de côtes", decoupe: "Retirer l’excès de gras au niveau des côtes. Couper des côtes d’environ 4 cm.", barquettes: ["1 côte ★★★"] },
      ],
      noms: ["Entrecôtes couvertes (milieu de train, 5 côtes)", "Dessus de côtes", "Noix d’entrecôte"],
    },
    "faux-filet": {
      guide: [
        { nom: "Faux-filet", etoiles: 3, mention: "À griller", morceau: "Faux-filet", preparation: "« Nerf » dorsal enlevé sur toute la longueur, paré ; tranché dans la largeur (tranches côté entrecôte, milieu, côté rumsteck).", p: 13 },
        { nom: "Faux-filet", etoiles: 3, mention: "À rôtir", morceau: "Faux-filet", preparation: "« Nerf » dorsal enlevé, sans chaînette ni bretelle, paré et démonté pour ne garder que le cœur du muscle, avec ou sans « chapeau de gendarme » ; rôtis ficelés ou non, bardés ou non.", p: 14 },
        { nom: "T-bone", etoiles: 3, mention: "À griller", morceau: "Aloyau à l’os", preparation: "Tranche de filet et de faux-filet avec l’os, issue des 5 dernières vertèbres lombaires, côté rumsteck. À présenter selon la règle en vigueur sur les MRS (corps vertébral).", p: 15 },
      ],
      magasin: [
        { titre: "Faux-filet", parage: "1 : retirer l’excès de gras sur la chaînette. 2 : retirer les aponévroses et les intercostaux.", decoupe: "Tranches d’1 cm ; retirer l’excès de gras s’il y en a trop." },
        { titre: "Faux-filet en pièces", parage: "Couper le faux-filet à partir du chapeau ; éplucher les pièces.", decoupe: "Pièce à fondue ; chapeau du faux-filet en steak ou en fondue ; pièce à griller." },
      ],
      noms: ["Contre-filet", "Chapeau de gendarme", "Chaînette", "Bretelle"],
    },
    "filet": {
      guide: [
        { nom: "Filet", etoiles: 3, mention: "À griller", morceau: "Filet", preparation: "Entièrement paré et épluché, tranché dans la largeur. En tranches épaisses, il peut s’appeler Châteaubriand ★★★ ; ficelé, bardé ou non, puis tranché : Tournedos ★★★.", p: 11 },
        { nom: "Filet", etoiles: 3, mention: "À rôtir", morceau: "Filet", preparation: "Entièrement paré et épluché ; rôtis ficelés ou non, bardés ou non, avec ou sans chaînette.", p: 12 },
        { nom: "T-bone", etoiles: 3, mention: "À griller", morceau: "Aloyau à l’os", preparation: "Tranche de filet et de faux-filet avec l’os, issue des 5 dernières vertèbres lombaires, côté rumsteck (règle MRS).", p: 15 },
      ],
      magasin: [
        { titre: "Filet", parage: "Séparer la chaînette, enlever le nerf du dessus. Dégraisser complètement.", decoupe: "Pour un rôti : entailler et replier la queue sous le filet, ficeler et barder (10 % du poids au plus), rôti de 500 à 600 g.", barquettes: ["1 filet ★★★ à rôtir"] },
        { titre: "Pavés (châteaubriand)", decoupe: "Retirer la queue (en steak, brochette ou fondue). Couper des pavés de 3 à 4 cm.", barquettes: ["1 filet ★★★ en pavés", "2 filets ★★★ en pavés"] },
        { titre: "Tournedos", decoupe: "Retirer la queue. Barder et ficeler (13 % du poids au plus), puis couper des tournedos de 3 à 4 cm.", barquettes: ["1 tournedos ★★★", "2 tournedos ★★★"] },
      ],
      noms: ["Tête", "Cœur (châteaubriand)", "Queue (pointe)", "Aile du filet", "Chaînette"],
    },
    "rumsteck": {
      guide: [
        { nom: "Rumsteck", etoiles: 3, mention: "À griller", morceau: "Milieu de rumsteck affranchi", preparation: "Paré et épluché, sans aiguillette, faux morceau ni chaînette, démonté en 3 pièces (cœur, filet et limande), « nerfs » retirés ; cœur et filet affranchis côté fémur ; filet tranché dans la longueur, cœur dans la largeur.", p: 4 },
        { nom: "Rumsteck", etoiles: 3, mention: "À griller, pavé ou tournedos à griller", morceau: "Milieu de rumsteck affranchi", preparation: "Démonté en 2 pièces (cœur et filet), sans limande ; tranches épaisses = « pavé à griller » ; ficelées, bardées ou non = « en tournedos à griller ».", p: 5 },
        { nom: "Rumsteck", etoiles: 3, mention: "À griller ou tranche à griller", morceau: "Milieu de rumsteck affranchi", preparation: "Semi-paré côté externe, paré et épluché côté interne, sans aiguillette, faux morceau ni chaînette ; affranchi côté fémur ; tranché à partir du fémur.", p: 6 },
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Aiguillette de rumsteck affranchie", preparation: "Parée et épluchée, séparée de la partie attenante au gîte noix ; tranchée dans la largeur.", p: 6 },
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Partie de l’aiguillette attenante au gîte noix", preparation: "Partie ferme de l’aiguillette de rumsteck, côté gîte noix, parée et épluchée ; tranchée dans la longueur de l’aiguillette.", p: 7 },
        { nom: "Rumsteck", etoiles: 3, mention: "À rôtir", morceau: "Milieu de rumsteck affranchi", preparation: "Démonté en 2 pièces (cœur et filet), « nerfs » retirés, affranchis côté fémur ; rôtis ficelés ou non, bardés ou non.", p: 8 },
        { nom: "Rôti", etoiles: 2, mention: "", morceau: "Aiguillette de rumsteck affranchie", preparation: "Parée et épluchée, séparée de la partie attenante au gîte noix ; rôtis ficelés ou non, bardés ou non.", p: 9 },
      ],
      magasin: [
        { titre: "Rumsteck : parage", parage: "Séparer l’aiguillette de rumsteck. Éplucher, séparer le cœur.", decoupe: "Trois muscles : langue de chat, filet, cœur. Cœur en tranches d’environ 1 cm." },
        { titre: "Rumsteck à griller", decoupe: "Affranchir la pointe dure. Cœur en tranches d’environ 1 cm.", barquettes: ["1 rumsteck ★★★ à griller", "2 rumstecks ★★★ à griller"] },
        { titre: "Filet de rumsteck", controle: "Affranchir la pointe dure.", decoupe: "Pavés épais de 3 à 4 cm.", barquettes: ["1 rumsteck ★★★ pavé à griller", "2 rumstecks ★★★ pavés à griller"] },
        { titre: "Rumsteck à rôtir ou à fondue", decoupe: "Affranchir la pointe dure. Couper le cœur en deux. Barder et ficeler (10 % du poids au plus).", barquettes: ["Rumsteck ★★★ pour fondue", "Rumsteck ★★★ à rôtir"] },
      ],
      noms: ["Cœur", "Filet de rumsteck", "Limande", "Aiguillette de rumsteck", "Langue de chat", "Panoufle"],
    },
    "aiguillette-baronne": {
      guide: [
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Aiguillette baronne affranchie", preparation: "Parée et épluchée, affranchie côté rumsteck ; tranchée dans la largeur.", p: 7 },
        { nom: "Rôti", etoiles: 1, mention: "", morceau: "Aiguillette baronne affranchie", preparation: "Entièrement parée et épluchée, affranchie côté rumsteck ; rôtis ficelés ou non, bardés ou non.", p: 10 },
      ],
      magasin: [
        { titre: "Aiguillette baronne", decoupe: "Couper en steaks en partant de la pointe. Pour un rôti : barder et ficeler (10 % du poids au plus).", barquettes: ["1 rôti ★", "2 rôtis ★"], poids: ["Rôti ★ : 500 g"] },
      ],
    },
    "onglet": {
      guide: [
        { nom: "Onglet", etoiles: 3, mention: "À griller", morceau: "Onglet", preparation: "Paré et épluché, « nerf » central retiré, tranché ou non.", p: 43 },
      ],
      magasin: [
        { titre: "Onglet", parage: "Dégraisser et éplucher entièrement. Séparer les 2 muscles.", decoupe: "Le laisser entier à rôtir, ou le trancher à l’horizontale en portions de 150 à 170 g." },
      ],
    },
    "hampe": {
      guide: [
        { nom: "Hampe", etoiles: 2, mention: "À griller", morceau: "Hampe", preparation: "Parée et épluchée, tranchée ou non.", p: 42 },
      ],
      magasin: [
        { titre: "Hampe", decoupe: "Bien dégraisser et faire des portions de 120 g.", barquettes: ["1 hampe ★★ à griller", "2 hampes ★★ à griller"], poids: ["Hampe ★★ : 150 g"] },
      ],
    },
    "bavette-d-aloyau": {
      guide: [
        { nom: "Bavette d’aloyau", etoiles: 3, mention: "À griller", morceau: "Bavette d’aloyau", preparation: "Entièrement parée et épluchée ; tranchée dans la largeur.", p: 17 },
      ],
      magasin: [
        { titre: "Bavette", decoupe: "Trancher en steaks épais d’au moins 1 cm, dans le sens de la fibre.", barquettes: ["1 bavette ★★★", "2 bavettes ★★★"] },
      ],
    },
    "bavette-de-flanchet": {
      guide: [
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Bavette de flanchet affranchie", preparation: "Affranchie de sa pointe ; tranchée dans la largeur.", p: 18 },
      ],
    },
    "flanchet": {
      guide: [
        { nom: "Poitrine", etoiles: 1, mention: "À mijoter", morceau: "Gros bout, milieu, tendron et flanchet", preparation: "Viande désossée, d’une seule pièce ou en mélange.", p: 47 },
      ],
      magasin: [
        { titre: "Poitrine : flanchet et gros bout", barquettes: ["Poitrine ★ à griller", "Poitrine ★ à mijoter"], poids: ["Poitrine ★ à mijoter : 500 g", "Poitrine ★ à griller : 300 g"] },
      ],
      noms: ["Sur 3 cartilages de côtes (tableau n° 1)", "Bavettes à pot-au-feu (3 dernières côtes)", "Œillet"],
    },
    "plat-de-cotes": {
      guide: [
        { nom: "Bourguignon ou Pot-au-feu", etoiles: 2, mention: "À mijoter", morceau: "Plat de côtes, plat de côtes découvert, dessus de côte", preparation: "Admis en Bourguignon ★★ et Pot-au-feu ★★, seul ou en mélange.", p: 48 },
      ],
      magasin: [
        { titre: "Plat de côtes", decoupe: "Couper entre chaque côte, bien au milieu.", barquettes: ["Pot-au-feu ★★"] },
      ],
      noms: ["Plat de côtes découvert (5 côtes)", "Plat de côtes couvert (5 côtes)", "Bavettes à pot-au-feu (3 côtes)", "Le « panneau » = les 13 côtes"],
    },
    "tendron": {
      guide: [
        { nom: "Poitrine", etoiles: 1, mention: "À mijoter", morceau: "Gros bout, milieu, tendron et flanchet", preparation: "Viande désossée, d’une seule pièce ou en mélange.", p: 47 },
        { nom: "Bourguignon ou Pot-au-feu", etoiles: 2, mention: "À mijoter", morceau: "Poitrine (gros bout, milieu, tendron)", preparation: "En mélange avec d’autres morceaux.", p: 48 },
      ],
      noms: ["Milieu de poitrine : 5 sternèbres, 4 cartilages (tableau n° 1)", "Tendron ou petite poitrine : 4 cartilages"],
    },
    "jumeau-a-bifteck": {
      guide: [
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Jumeau affranchi", preparation: "Paré et épluché, « nerf » central retiré, affranchi de ses 2 extrémités ; tranché dans la largeur.", p: 37 },
        { nom: "Rôti", etoiles: 1, mention: "", morceau: "Jumeau affranchi", preparation: "Paré et épluché, « nerf » central retiré, affranchi de ses 2 extrémités ; rôtis ficelés ou non, bardés ou non.", p: 37 },
      ],
    },
    "paleron": {
      guide: [
        { nom: "Paleron", etoiles: 3, mention: "À mijoter", morceau: "Paleron", preparation: "Viande préparée exclusivement à partir du paleron.", p: 39 },
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Paleron sans nerf central, affranchi", preparation: "Affranchi de son extrémité côté « nerf », entièrement démonté, paré et épluché ; tranché dans la largeur.", p: 38 },
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Paleron avec nerf central", preparation: "Affranchi de ses 2 extrémités, paré ; tranché dans la largeur.", p: 38 },
        { nom: "Steak", etoiles: 3, mention: "À griller", morceau: "Dessus de palette", preparation: "Entièrement démonté (surprise et merlan d’épaule). La surprise, parée, épluchée et dénervée, est tranchée dans la largeur ; le merlan d’épaule, paré et épluché, est tranché ou non.", p: 35 },
      ],
      magasin: [
        { titre: "Paleron", decoupe: "Lever l’affranchi. Selon la saison, couper des steaks ★ de la pointe jusqu’à l’épaississement du nerf, ou couper en morceaux : paleron ★★★ à mijoter." },
        { titre: "Dessus de la palette", decoupe: "Merlan d’épaule en steak ★★. Dessus de palette : bien éplucher et lever le nerf, pour la fondue ou le steak ★★★.", barquettes: ["1 steak ★★★", "2 steaks ★★★", "Pièce à fondue ou brochette"], poids: ["Steak ★★ ou ★★★ : 150 g"] },
      ],
      noms: ["Dessus de palette", "Surprise", "Merlan d’épaule", "Raquette", "Derrière de paleron (muscle avec le cartilage de la palette)"],
    },
    "macreuse-a-bifteck": {
      guide: [
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Dessous de macreuse affranchi", preparation: "Paré et épluché, affranchi de l’extrémité de la pointe de l’olécrane, séparé du petit muscle latéral ; tranché dans la largeur.", p: 36 },
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Dessus de boule de macreuse", preparation: "Paré et épluché ; tranché dans la largeur.", p: 36 },
        { nom: "Rôti", etoiles: 2, mention: "", morceau: "Dessous de macreuse affranchi", preparation: "Paré et épluché, affranchi de la pointe de l’olécrane, séparé du petit muscle latéral ; rôtis ficelés ou non, bardés ou non.", p: 36 },
      ],
      magasin: [
        { titre: "Macreuse", parage: "Séparer le dessus de macreuse et enlever le nerf.", decoupe: "Dessus de macreuse : steak ★ ou bourguignon ★★. Macreuse : steak ★★, rôti ★★ ou bourguignon ★★.", barquettes: ["1 steak ★ ou ★★"], poids: ["Steak ★ ou ★★ : 150 g"] },
      ],
      noms: ["Boule de macreuse", "Dessus et dessous de macreuse"],
    },
    "jumeau-a-pot-au-feu": {
      guide: [
        { nom: "Bourguignon ou Pot-au-feu", etoiles: 3, mention: "À mijoter", morceau: "Jumeau", preparation: "Le jumeau fait partie des muscles admis en Bourguignon ★★★ et Pot-au-feu ★★★.", p: 48 },
      ],
      magasin: [
        { titre: "Jumeau", decoupe: "Lever le nerf. Couper en morceaux pour du pot-au-feu ★★★ ou du bourguignon ★★★.", barquettes: ["Pot-au-feu ★★★", "Pot-au-feu ★★★ en caissette"], poids: ["Pot-au-feu ★★★ : 400 g"] },
      ],
    },
    "macreuse-a-pot-au-feu": {
      guide: [
        { nom: "Bourguignon ou Pot-au-feu", etoiles: 3, mention: "À mijoter", morceau: "Macreuse à braiser", preparation: "La macreuse à braiser fait partie des muscles admis en Bourguignon ★★★ et Pot-au-feu ★★★.", p: 48 },
      ],
      noms: ["Macreuse à braiser (gélatineuse)"],
    },
    "gite-avant": {
      guide: [
        { nom: "Jarret", etoiles: 3, mention: "À mijoter", morceau: "Jarret sans os", preparation: "Viande préparée exclusivement à partir de jarret sans os.", p: 44 },
        { nom: "Jarret à l’os", etoiles: 3, mention: "À mijoter", morceau: "Jarret avec os", preparation: "Viande préparée exclusivement à partir de jarret avec os.", p: 44 },
      ],
      magasin: [
        { titre: "Jarret avant à l’os", decoupe: "Dégraisser et désosser le jarret. Couper en deux rouelles de 600 à 800 g.", barquettes: ["1 jarret ★★★ sans os", "Bourguignon ★★★"], poids: ["Jarret sans os : 700 g"] },
      ],
      noms: ["Charolaise", "Joint de gîte"],
    },
    "tende-de-tranche": {
      guide: [
        { nom: "Steak", etoiles: 3, mention: "À griller", morceau: "Entame du tende de tranche", preparation: "Premier tiers, côté poire, du cœur de tende de tranche, paré et épluché (artère fémorale retirée) ; tranché dans la largeur.", p: 25 },
        { nom: "Pavé", etoiles: 3, mention: "À griller, ou en tournedos à griller", morceau: "Entame du tende de tranche", preparation: "Même muscle tranché en tranches épaisses ; ficelées, bardées ou non : « Pavé ★★★ en tournedos à griller ».", p: 25 },
        { nom: "Rôti", etoiles: 3, mention: "", morceau: "Entame du tende de tranche", preparation: "Premier tiers côté poire, paré et épluché (artère fémorale retirée) ; rôtis ficelés ou non, bardés ou non.", p: 26 },
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Partie centrale du tende de tranche", preparation: "Tiers central du cœur, paré et épluché ; tranché dans la largeur.", p: 25 },
        { nom: "Rôti", etoiles: 2, mention: "", morceau: "Partie centrale du tende de tranche", preparation: "Tiers central du cœur, paré et épluché ; rôtis ficelés ou non, bardés ou non.", p: 27 },
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Talon du tende de tranche", preparation: "Dernier tiers, côté talon, du cœur de tende de tranche PAD ; tranché dans la largeur.", p: 26 },
        { nom: "Rôti", etoiles: 1, mention: "", morceau: "Talon du tende de tranche", preparation: "Dernier tiers, côté talon, paré et épluché ; rôtis ficelés ou non, bardés ou non.", p: 27 },
        { nom: "Steak", etoiles: 3, mention: "À griller", morceau: "Poire", preparation: "Entièrement parée, épluchée et dénervée, tranchée dans la largeur ou non tranchée.", p: 28 },
        { nom: "Rôti", etoiles: 3, mention: "", morceau: "Poire", preparation: "Parée, épluchée et dénervée ; rôtis ficelés ou non, bardés ou non.", p: 28 },
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Merlan", preparation: "Merlan de cuisse, paré et épluché, tranché ou non.", p: 29 },
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Dessus de tranche affranchi", preparation: "Affranchi de sa partie mince, entièrement paré et épluché ; tranché dans la longueur du muscle.", p: 30 },
      ],
      magasin: [
        { titre: "Tende de tranche", controle: "Dessus de tende de tranche levé avec la poire et le merlan.", decoupe: "Du haut vers le bas : affranchi ★, rôti ou steak ★, rôti ou steak ★★, rôti ou steak ★★★, affranchi ★. Barder et ficeler (10 % du poids au plus)." },
        { titre: "Dessus de tende de tranche", decoupe: "Steak haché, merlan ★★, poire ★★★, steak ★. Merlan en steak ★★. Poire : bien éplucher et lever le nerf, pour la fondue ou le steak ★★★.", barquettes: ["1 steak ★, ★★ ou ★★★", "2 steaks ★, ★★ ou ★★★"], poids: ["Steak : 150 g", "Pièce à fondue : 500 g"] },
      ],
      noms: ["Poire", "Merlan", "Dessus de tranche", "Talon de tranche", "Entame"],
    },
    "tranche-grasse": {
      guide: [
        { nom: "Steak", etoiles: 3, mention: "À griller", morceau: "Rond de tranche affranchi", preparation: "Paré et épluché, « nerf » central retiré, affranchi côté rotule ; tranché dans sa largeur.", p: 21 },
        { nom: "Pavé", etoiles: 3, mention: "À griller, ou en tournedos à griller", morceau: "Rond de tranche affranchi", preparation: "Même muscle tranché en tranches épaisses ; ficelées, bardées ou non : « Pavé ★★★ en tournedos à griller ».", p: 21 },
        { nom: "Rôti", etoiles: 3, mention: "", morceau: "Rond de tranche affranchi", preparation: "Paré et épluché, « nerf » central retiré, affranchi côté rotule ; rôtis ficelés ou non, bardés ou non.", p: 22 },
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Plat de tranche affranchi sans la pointe", preparation: "Paré et épluché, affranchi côté rond de tranche dans la longueur et séparé de sa pointe, côté rotule ; tranché dans la largeur.", p: 23 },
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Pointe de plat de tranche", preparation: "Partie ferme, côté rotule, du plat de tranche, parée et épluchée ; tranchée dans la largeur.", p: 23 },
        { nom: "Rôti", etoiles: 2, mention: "", morceau: "Plat de tranche affranchi sans la pointe", preparation: "Même préparation ; rôtis ficelés ou non, bardés ou non.", p: 24 },
        { nom: "Steak", etoiles: 3, mention: "À griller", morceau: "Plat de mouvant de tranche affranchi", preparation: "Partie importante du mouvant, parée et épluchée, affranchie côté rotule ; tranchée dans sa largeur.", p: 19 },
        { nom: "Steak", etoiles: 2, mention: "À griller", morceau: "Partie centrale du mouvant", preparation: "Pièce centrale du mouvant, parée et épluchée, affranchie des 2 extrémités ; tranchée dans la longueur.", p: 19 },
        { nom: "Rôti", etoiles: 2, mention: "", morceau: "Partie centrale du mouvant", preparation: "Pièce centrale du mouvant, parée et épluchée, affranchie des 2 extrémités ; rôtis ficelés ou non, bardés ou non.", p: 20 },
      ],
      magasin: [
        { titre: "Tranche grasse", controle: "Trois muscles : plat de tranche grasse, rond de tranche grasse, mouvant de tranche grasse." },
        { titre: "Rond de tranche grasse", parage: "Séparer le muscle au niveau du nerf, enlever le nerf. Affranchir la pointe dure.", decoupe: "Pavés ★★★ de 3 à 4 cm ; tournedos ★★★ : barder (13 % au plus), ficeler, couper des pavés de 3 à 4 cm ; morceaux à brochette ou steak ★★.", poids: ["Pavé ★★★ : 160 g", "Tournedos ★★★ : 160 g", "Steak ★★ : 150 g"] },
        { titre: "Mouvant", decoupe: "3 morceaux : steak ★★★, et deux morceaux pour haché ou bourguignon ★★.", poids: ["Steak ★★★ : 150 g"] },
        { titre: "Plat de tranche", decoupe: "Éliminer les affranchis et couper en steaks.", barquettes: ["1 steak ★★"], poids: ["Steak ★★ : 150 g"] },
      ],
      noms: ["Rond de tranche", "Plat de tranche", "Mouvant"],
    },
    "araignee": {
      guide: [
        { nom: "Steak", etoiles: 3, mention: "À griller", morceau: "Araignée", preparation: "Entièrement parée et dénervée.", p: 31 },
      ],
      noms: ["Fausse araignée (tableau n° 2)"],
    },
    "gite-a-la-noix": {
      guide: [
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Gîte noix affranchi", preparation: "Paré et épluché, séparé de l’oreille, affranchi dans sa longueur côté tranche (côté « nerf ») ; tranché dans sa largeur.", p: 32 },
        { nom: "Rôti", etoiles: 1, mention: "", morceau: "Gîte noix affranchi", preparation: "Entièrement paré, épluché et dénervé, séparé de l’oreille, affranchi côté tranche ; rôtis ficelés ou non, bardés ou non.", p: 32 },
        { nom: "Steak", etoiles: 3, mention: "À griller", morceau: "Plat de nerveux de gîte noix affranchi", preparation: "Paré et épluché, affranchi côté tendon d’Achille ; tranché dans la largeur.", p: 34 },
      ],
      magasin: [
        { titre: "Gîte noix", controle: "Carré de gîte et oreille de gîte.", decoupe: "Couper les affranchis, puis en steaks ★ ou en rôtis ★ (barde : 10 % du poids au plus). Oreille de gîte en steak haché ou en bourguignon ★★.", barquettes: ["1 rôti ★", "2 rôtis ★"], poids: ["Rôti ★ : 500 g"] },
        { titre: "Gîte nerveux", parage: "La partie ferme contre la carotte part en bourguignon ★★★ ou pot-au-feu ★★★.", decoupe: "Éplucher le reste pour des pièces à griller ★★★." },
      ],
      noms: ["Semelle (avec le rond de gîte)", "Oreille de gîte", "Carré de gîte", "Nerveux de gîte noix", "Aiguillette de gîte noix"],
    },
    "rond-de-gite": {
      guide: [
        { nom: "Steak", etoiles: 1, mention: "À griller", morceau: "Rond de gîte noix affranchi", preparation: "Paré et épluché, affranchi côté bassin ; tranché dans la largeur.", p: 33 },
        { nom: "Rôti", etoiles: 1, mention: "", morceau: "Rond de gîte noix affranchi", preparation: "Entièrement paré et épluché, affranchi côté bassin ; rôtis ficelés ou non, bardés ou non.", p: 33 },
      ],
      magasin: [
        { titre: "Rond de gîte", decoupe: "Couper les affranchis, trancher en steaks ★ assez fins (1 cm) ; affranchis en bourguignon ★★. Rôti ★★★ : barder et ficeler (10 % du poids au plus).", barquettes: ["Bourguignon ★★"], poids: ["Bourguignon ★★ : 400 g"] },
      ],
    },
    "gite-arriere": {
      guide: [
        { nom: "Jarret", etoiles: 3, mention: "À mijoter", morceau: "Jarret sans os", preparation: "Viande préparée exclusivement à partir de jarret sans os.", p: 44 },
        { nom: "Jarret à l’os", etoiles: 3, mention: "À mijoter", morceau: "Jarret avec os", preparation: "Viande préparée exclusivement à partir de jarret avec os.", p: 44 },
      ],
      magasin: [
        { titre: "Jarret arrière", controle: "Dégraisser le jarret, le prédécouper au couteau, puis scier l’os à moelle en rouelles de 4 à 5 cm. Gratter la sciure sur les rouelles.", barquettes: ["1 jarret ★★★"] },
      ],
      noms: ["Joint de gîte"],
    },
  },
};
