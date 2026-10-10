/* Atelier Boucherie — logique de l'interface (fonctionne en ouvrant index.html, sans réseau). */
(function () {
  "use strict";

  const { ANIMAUX, PIECES, CUISSONS, REGIONS, RECETTES } = window;
  const OS = window.OS || {};
  const CLASSEUR = window.CLASSEUR || null;
  // Page atelier 3D (atelier.html) : os et pièces qui y ont une vue détaillée (bœuf seulement).
  const ATELIER = window.ATELIER || null;
  const lienAtelierOs = (animal, id) => animal === "boeuf" && ATELIER && ATELIER.os[id] ? `atelier.html?os=${encodeURIComponent(id)}` : null;
  const regionAtelier = (id) => ATELIER && Object.keys(ATELIER.regions).find((r) => ATELIER.regions[r].pieces[id]);
  const lienAtelierPiece = (animal, id) => animal === "boeuf" && regionAtelier(id) ? `atelier.html?region=${regionAtelier(id)}&piece=${encodeURIComponent(id)}` : null;
  const RAPIDES = ["griller", "poeler", "rotir", "sauter", "cru"];
  const LENTES = ["braiser", "bouillir"];

  const $ = (id) => document.getElementById(id);
  const etat = { animal: ANIMAUX[0].id, piece: null, filtre: null, vue: "planche", montrer: true, squelette: false, os: null, eclate: false,
    muscles: true, viande: false, autresOs: false, chargement: false, erreurAnatomie: null, recadrer: false,
    recettes: { animal: ANIMAUX[0].id, piece: null } };

  // Couleur d'une pièce sur le modèle 3D = sa famille de cuisson (même code pour les 4 animaux).
  // Plusieurs nuances par famille, pour que deux pièces voisines ne se confondent pas.
  const FAMILLES = {
    rapide: ["#d9383c", "#ea5b50", "#c22b39", "#f07563", "#cf4a40", "#b3323d"],
    lente: ["#8a2338", "#a3374a", "#741f36", "#b0464f", "#68203a", "#963244"],
    mixte: ["#c9502e", "#dd6a3b", "#b4432a", "#e5814d"],
    abat: ["#b8857f", "#a3716c", "#caa099"],
  };
  const TEINTE_FAMILLE = { rapide: "#d9383c", lente: "#8a2338", mixte: "#c9502e", abat: "#b8857f" };
  const ATTENUE = "#e6ddd2";

  // ---------- utilitaires ----------
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pieceDe = (animal, id) => (PIECES[animal] || []).find((p) => p.id === id) || null;
  const osDe = (animal, id) => (OS[animal] || []).find((o) => o.id === id) || null;
  const osDePiece = (animal, piece) => (OS[animal] || []).filter((o) => o.pieces.includes(piece));
  const nomAnimal = (id) => (ANIMAUX.find((a) => a.id === id) || {}).nom || id;

  function typeCuisson(piece) {
    const rapide = piece.cuissons.some((c) => RAPIDES.includes(c));
    const lente = piece.cuissons.some((c) => LENTES.includes(c));
    if (rapide && lente) return { cls: "mixte", txt: "Polyvalente : rapide ou lente" };
    if (lente) return { cls: "lente", txt: "Cuisson lente" };
    return { cls: "rapide", txt: "Cuisson rapide" };
  }

  function correspond(piece) {
    if (!etat.filtre) return true;
    if (etat.filtre.type === "cuisson") return piece.cuissons.includes(etat.filtre.id);
    return piece.region === etat.filtre.id;
  }

  // ---------- navigation (adresse #animal/piece) ----------
  function lireAdresse() {
    const [a, p, q] = decodeURIComponent(location.hash.replace(/^#/, "")).split("/");
    if (a === "comparatif") { etat.vue = "comparatif"; return; }
    if (a === "etal") { etat.vue = "etal"; return; }
    if (a === "recettes") {
      etat.vue = "recettes";
      const animal = ANIMAUX.some((x) => x.id === p) ? p : etat.animal;
      etat.recettes = { animal, piece: q && pieceDe(animal, q) ? q : null };
      return;
    }
    etat.vue = "planche";
    if (ANIMAUX.some((x) => x.id === a)) {
      if (a !== etat.animal) { etat.filtre = null; etat.eclate = false; }
      etat.animal = a;
      const avant = etat.os;
      etat.squelette = p === "squelette" && !!OS[a];
      if (!etat.squelette) etat.eclate = false;
      etat.os = etat.squelette && q && osDe(a, q) ? q : null;
      if (etat.squelette && avant && !etat.os) etat.recadrer = true;
      etat.piece = !etat.squelette && p && pieceDe(a, p) ? p : null;
    }
  }

  function aller(animal, piece) {
    allerA("#" + animal + (piece ? "/" + piece : ""));
  }
  function allerOs(animal, os) {
    allerA("#" + animal + "/squelette" + (os ? "/" + os : ""));
  }
  function allerA(cible) {
    if (location.hash === cible) { lireAdresse(); rendre(); montrer3D(); } else { location.hash = cible; }
  }

  // Sur téléphone, la vue 3D est en haut et les listes et la fiche en dessous : quand on choisit une pièce ou un
  // os (liste, lien de la fiche, carte), on remonte jusqu'à la 3D pour le VOIR, si elle n'est pas déjà à l'écran.
  function montrer3D() {
    if (etat.vue !== "planche" || !(etat.piece || etat.os)) return;
    if (!window.matchMedia("(max-width: 900px)").matches || document.body.classList.contains("plein-ecran-3d")) return;
    const r = $("planche").getBoundingClientRect();
    if (r.top >= 0 && r.bottom <= window.innerHeight) return;
    window.scrollTo({ top: Math.max(0, r.top + window.scrollY - 8), behavior: "smooth" });
  }

  // ---------- rendu ----------
  function rendreOnglets() {
    const nav = $("onglets");
    nav.innerHTML = "";
    ANIMAUX.forEach((a) => {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = a.nom;
      if (etat.vue === "planche" && etat.animal === a.id) b.setAttribute("aria-current", "page");
      b.addEventListener("click", () => aller(a.id, null));
      nav.appendChild(b);
    });
    const c = document.createElement("button");
    c.type = "button";
    c.textContent = "Comparatif";
    if (etat.vue === "comparatif") c.setAttribute("aria-current", "page");
    c.addEventListener("click", () => { location.hash = "#comparatif"; });
    nav.appendChild(c);
    // Recettes et mise en avant : à part, pour que la fiche d'une pièce reste courte
    for (const [vue, nom, cible] of [["recettes", "Recettes", () => "#recettes/" + etat.animal], ["etal", "Mise en avant", () => "#etal"]]) {
      const b = document.createElement("button");
      b.type = "button";
      b.textContent = nom;
      if (etat.vue === vue) b.setAttribute("aria-current", "page");
      b.addEventListener("click", () => { location.hash = cible(); });
      nav.appendChild(b);
    }
  }

  let vue3d = null;
  const nuances = {};

  function famille(piece) {
    if (piece.abat) return "abat";
    return typeCuisson(piece).cls;
  }

  // Attribue les nuances une fois par animal : les pièces voisines d'une même famille diffèrent.
  function nuancesDe(animal) {
    if (nuances[animal]) return nuances[animal];
    const voisins = vue3d.voisins();
    const ids = window.MODELES3D[animal].pieces;
    const ordre = ids.map((id, i) => i).sort((a, b) => voisins[b].length - voisins[a].length);
    const res = {};
    for (const i of ordre) {
      const p = pieceDe(animal, ids[i]);
      const f = famille(p);
      const pris = new Set(voisins[i].filter((v) => res[v] && res[v].f === f).map((v) => res[v].k));
      let k = 0;
      while (pris.has(k)) k++;
      res[ids[i]] = { f, k, couleur: FAMILLES[f][k % FAMILLES[f].length] };
    }
    return (nuances[animal] = res);
  }

  function couleursPieces() {
    const n = nuancesDe(etat.animal);
    const out = {};
    for (const p of PIECES[etat.animal]) {
      if (!etat.filtre) out[p.id] = n[p.id].couleur;
      else if (!correspond(p)) out[p.id] = ATTENUE;
      else out[p.id] = etat.filtre.type === "cuisson" ? CUISSONS[etat.filtre.id].couleur : "#d99a1e";
    }
    return out;
  }

  // Nom écrit sur la pièce en 3D : court, comme sur une planche (« Tende de tranche (poire, merlan) » → « Tende de tranche »).
  function nomCourt(p) {
    let n = p.nom.split(/[(,]/)[0].trim();
    if (n.length > 16 && n.includes(" / ")) n = n.split(" / ")[0];
    return n;
  }

  function rendre3D() {
    if (!vue3d) {
      vue3d = window.Vue3D($("planche"), { surClic: choisirSurModele, surClicOs: choisirOsSurModele, surSurvol: montrerBulle });
      window.ATELIER3D = vue3d; // accès pour les tests automatiques
    }
    vue3d.afficher(etat.animal, Object.fromEntries(PIECES[etat.animal].map((p) => [p.id, nomCourt(p)])));
    // Le squelette réaliste et les muscles (data/anatomie.js, ~2,5 Mo) ne sont chargés qu'à la première ouverture.
    if (etat.squelette && OS[etat.animal] && !vue3d.anatomiePrete(etat.animal) && !etat.chargement && !etat.erreurAnatomie) {
      etat.chargement = true;
      vue3d.chargerAnatomie()
        .then(() => { etat.chargement = false; rendre(); })
        .catch((e) => { etat.chargement = false; etat.erreurAnatomie = e.message; rendre(); });
    }
    const os = etat.os && osDe(etat.animal, etat.os);
    vue3d.squelette(etat.squelette, Object.fromEntries((OS[etat.animal] || []).map((o) => [o.id, o.nom])),
      Object.fromEntries(PIECES[etat.animal].map((p) => [p.id, nomCourt(p)])));
    vue3d.eclater(etat.squelette && etat.eclate);
    vue3d.voir({ muscles: etat.muscles, tous: etat.viande, autres: etat.autresOs });
    vue3d.etat({
      couleurs: couleursPieces(), selection: etat.piece, forts: os ? os.pieces : [],
      etiquettes: etat.filtre ? PIECES[etat.animal].filter(correspond).map((p) => p.id) : null,
    });
    vue3d.etatOs({ selection: etat.os, lies: os ? os.pieces : [] });
    if (etat.piece && etat.montrer) vue3d.focaliser(etat.piece);
    if (etat.os && etat.montrer && !etat.eclate) vue3d.focaliserOs(etat.os);
    if (etat.squelette && !etat.os && etat.recadrer) vue3d.recadrer();
    etat.recadrer = false;
    etat.montrer = true;
    rendreOutils();
    rendreCarte3d(os);
    $("planche").setAttribute("aria-label", `${nomAnimal(etat.animal)} en 3D : glisse pour le faire tourner, clique sur une pièce`);
  }

  // Petite carte JUSTE SOUS la vue 3D quand une pièce ou un os est choisi : elle ne cache rien de la 3D ; elle
  // mène aux muscles ou aux os voisins, à la vue en grand et à la fiche complète.
  function rendreCarte3d(os) {
    let carte = $("carte3d");
    if (!carte) {
      carte = document.createElement("div");
      carte.id = "carte3d";
      carte.className = "carte3d";
      $("planche").after(carte);
    }
    $("planche").classList.toggle("choix", !!(os || etat.piece));
    const piece = !etat.squelette && etat.piece && pieceDe(etat.animal, etat.piece);
    if (piece) {
      const sous = osDePiece(etat.animal, piece.id);
      const enGrand = lienAtelierPiece(etat.animal, piece.id);
      const r = regionAtelier(piece.id);
      const pasAPas = etat.animal === "boeuf" && r && ATELIER.regions[r].etapesPieces[piece.id]
        ? `atelier.html?region=${r}&piece=${encodeURIComponent(piece.id)}&pas=1` : null;
      carte.hidden = false;
      carte.innerHTML = `
        <div class="titre"><b>${esc(piece.nom)}</b> <small>${esc(typeCuisson(piece).txt)}</small></div>
        ${sous.length ? `<div class="muscles-lies">Os dessous : ${sous.map((o) => `<a href="#${etat.animal}/squelette/${o.id}">${esc(o.nom)}</a>`).join(" · ")}</div>` : ""}
        <div class="actions">
          <button type="button" data-fiche>Fiche ↓</button>
          ${pasAPas ? `<a class="bouton-lien" href="${pasAPas}">Séparer pas à pas ▶</a>` : ""}
          ${enGrand ? `<a class="bouton-lien" href="${enGrand}">Ses muscles en grand ↗</a>` : ""}
          <button type="button" data-sortir aria-label="Revenir à l’animal entier">✕</button>
        </div>`;
      return;
    }
    const msg = !etat.squelette ? null : etat.chargement ? "Chargement du squelette et des muscles…"
      : etat.erreurAnatomie ? "Le squelette 3D n’a pas pu se charger : " + etat.erreurAnatomie : null;
    if (msg) {
      carte.hidden = false;
      carte.innerHTML = `<p class="info">${esc(msg)}</p>`;
      return;
    }
    if (!etat.squelette || !os || etat.eclate) { carte.hidden = true; carte.innerHTML = ""; return; }
    const pieces = os.pieces.map((id) => pieceDe(etat.animal, id)).filter(Boolean);
    carte.hidden = false;
    carte.innerHTML = `
      <div class="titre"><b>${esc(os.nom)}</b> <small>${esc(os.savant)}</small></div>
      ${pieces.length ? `<div class="muscles-lies">Muscles posés dessus : ${pieces.map((p) => `<a href="#${etat.animal}/${p.id}">${esc(nomCourt(p))}</a>`).join(" · ")}</div>`
        : `<div class="muscles-lies">Aucune pièce de la planche n’est posée sur cet os.</div>`}
      <div class="actions">
        <button type="button" data-voir="muscles" aria-pressed="${etat.muscles}">Muscles</button>
        <button type="button" data-voir="autres" aria-pressed="${etat.autresOs}">Autres os</button>
        <button type="button" data-fiche>Fiche ↓</button>
        ${lienAtelierOs(etat.animal, os.id) ? `<a class="bouton-lien" href="${lienAtelierOs(etat.animal, os.id)}">En grand ↗</a>` : ""}
        <button type="button" data-sortir aria-label="Revenir au squelette entier">✕</button>
      </div>`;
  }

  // Boutons Squelette / Éclater : seulement pour un animal dont le squelette existe.
  function rendreOutils() {
    const bs = document.querySelector("#outils3d [data-squelette]");
    const be = document.querySelector("#outils3d [data-eclater]");
    const bm = document.querySelector("#outils3d [data-muscles]");
    bs.hidden = !OS[etat.animal];
    bs.setAttribute("aria-pressed", String(etat.squelette));
    be.hidden = !etat.squelette;
    be.setAttribute("aria-pressed", String(etat.eclate));
    be.textContent = etat.eclate ? "Rassembler" : "Éclater";
    bm.hidden = !etat.squelette;
    bm.setAttribute("aria-pressed", String(etat.viande));
    const bp = document.querySelector("#outils3d [data-plein]");
    const plein = document.body.classList.contains("plein-ecran-3d");
    bp.setAttribute("aria-pressed", String(plein));
    bp.textContent = plein ? "Quitter le plein écran" : "Plein écran";
    const tactile = window.matchMedia("(pointer: coarse)").matches;
    document.querySelector(".aide3d").textContent = !etat.squelette ? "Glisse pour tourner · touche une pièce"
      : tactile ? "Glisse : tourner · pince : zoom · 2 doigts : déplacer"
        : "Glisse pour tourner · molette pour zoomer · clic droit pour déplacer · clique un os";
  }

  function rendreCouleurs() {
    if (etat.squelette) {
      $("couleurs3d").innerHTML = `<span class="titre">Couleurs :</span>`
        + `<span class="pastille" style="--c:#ecdfc4">os</span>`
        + `<span class="pastille" style="--c:#bcd6dc">cartilage</span>`
        + `<span class="pastille" style="--c:#f3c45a">os choisi</span>`
        + `<span class="pastille" style="--c:${TEINTE_FAMILLE.rapide}">muscle à cuisson rapide</span>`
        + `<span class="pastille" style="--c:${TEINTE_FAMILLE.lente}">muscle à cuisson lente</span>`
        + `<span class="pastille" style="--c:${TEINTE_FAMILLE.mixte}">rapide ou lente</span>`;
      return;
    }
    const presentes = [...new Set(PIECES[etat.animal].map(famille))];
    const noms = { rapide: "cuisson rapide", lente: "cuisson lente", mixte: "rapide ou lente", abat: "abat" };
    $("couleurs3d").innerHTML = `<span class="titre">Couleurs :</span>` + ["rapide", "mixte", "lente", "abat"]
      .filter((f) => presentes.includes(f))
      .map((f) => `<span class="pastille" style="--c:${TEINTE_FAMILLE[f]}">${noms[f]}</span>`).join("")
      + `<span class="pastille" style="--c:${window.Vue3D.ROBES[etat.animal]}">robe de l’animal (pas une pièce)</span>`;
  }

  function rendreLegende() {
    const leg = $("legende");
    leg.hidden = etat.squelette;
    if (etat.squelette) return;
    const presents = Object.keys(CUISSONS).filter((c) => PIECES[etat.animal].some((p) => p.cuissons.includes(c)));
    let html = `<span class="titre">Voir les pièces à :</span>`;
    html += presents.map((c) => {
      const on = etat.filtre && etat.filtre.type === "cuisson" && etat.filtre.id === c;
      return `<button type="button" class="puce" style="--c:${CUISSONS[c].couleur}" data-filtre="${c}" aria-pressed="${on}">${esc(CUISSONS[c].nom)}</button>`;
    }).join("");
    if (etat.filtre) {
      const txt = etat.filtre.type === "region" ? `Région « ${esc(REGIONS[etat.filtre.id].par[etat.animal].nom)} » — effacer` : "Tout afficher";
      html += `<button type="button" class="puce effacer" data-filtre="">${txt}</button>`;
    }
    leg.innerHTML = html;
  }

  function rendreListe() {
    const liste = $("liste-pieces");
    if (etat.squelette) {
      const tous = OS[etat.animal];
      const groupes = [...new Set(tous.map((o) => o.groupe))];
      const regions = etat.animal === "boeuf" && ATELIER
        ? `<h2>Atelier 3D</h2><div class="grille"><a class="bouton-lien" href="atelier.html?region=cuisse">Cuisse entière : tous les muscles, séparés ↗</a><a class="bouton-lien" href="atelier.html?os=coxal">Os du bassin et ses repères ↗</a><a class="bouton-lien" href="atelier.html?region=epaule">Épaule entière : tous les muscles, séparés ↗</a><a class="bouton-lien" href="atelier.html?os=palette">Palette (omoplate) et ses repères ↗</a><a class="bouton-lien" href="atelier.html?region=aloyau">Aloyau et train de côtes : tous les muscles, séparés ↗</a><a class="bouton-lien" href="atelier.html?os=lombaires">Vertèbres des reins et leurs repères ↗</a><a class="bouton-lien" href="atelier.html?region=avant">Collier, basses côtes et poitrine : tous les muscles, séparés ↗</a><a class="bouton-lien" href="atelier.html?os=sternum">Sternum et ses repères ↗</a><a class="bouton-lien" href="atelier.html?region=flanc">Flanchet, bavettes, onglet et hampe ↗</a></div>` : "";
      // le parcours guidé en premier : désosser une région une étape à la fois
      const pas = etat.animal === "boeuf" && ATELIER
        ? `<h2>Désosser pas à pas</h2><div class="grille">${Object.entries(ATELIER.regions).map(([r, R]) =>
          `<a class="bouton-lien" href="atelier.html?region=${r}&pas=1">${esc(R.court)} ▶</a>`).join("")}</div>` : "";
      liste.innerHTML = pas + regions + `<h2>Tous les os (${tous.length})</h2>` + groupes.map((g) => `<h2 class="sous">${esc(g)}</h2><div class="grille">`
        + tous.filter((o) => o.groupe === g).map((o) =>
          `<button type="button" class="${o.id === etat.os ? "active" : ""}" data-os="${o.id}">${esc(o.nom)}</button>`).join("")
        + `</div>`).join("");
      return;
    }
    const pieces = [...PIECES[etat.animal]].sort((a, b) => a.nom.localeCompare(b.nom, "fr"));
    liste.innerHTML = `<h2>Toutes les pièces (${pieces.length})</h2><div class="grille">` +
      pieces.map((p) => {
        const cls = [p.id === etat.piece ? "active" : "", etat.filtre && !correspond(p) ? "attenue" : ""].join(" ").trim();
        return `<button type="button" class="${cls}" data-piece="${p.id}">${esc(p.nom)}</button>`;
      }).join("") + `</div>`;
  }

  function puceCuisson(c) {
    const d = CUISSONS[c];
    return `<span class="puce statique" style="--c:${d.couleur}" title="${esc(d.definition)}">${esc(d.nom)}</span>`;
  }

  function rendreAccueil() {
    const animal = ANIMAUX.find((a) => a.id === etat.animal);
    return `<div class="accueil">
      <div class="kicker">${esc(animal.nom)}</div>
      <h2>Clique sur une pièce</h2>
      <p>${esc(animal.intro)}</p>
      <div class="pas">
        <div><b>1</b><span>Fais tourner l’animal en glissant, puis touche une pièce (ou choisis-la dans la liste).</span></div>
        <div><b>2</b><span>Lis son mode de cuisson, ce qu’on en fait au billot et le conseil à donner.</span></div>
        <div><b>3</b><span>Les recettes et les idées pour la vitrine sont dans les onglets « Recettes » et « Mise en avant ».</span></div>
      </div>
      <h3>Les modes de cuisson</h3>
      <div class="definitions">${Object.keys(CUISSONS).map((c) =>
        `<div>${puceCuisson(c)}<span>${esc(CUISSONS[c].definition)}</span></div>`).join("")}</div>
    </div>`;
  }

  function rendreRecette(id, ouverte, pieces = []) {
    const r = RECETTES[id];
    const avec = pieces.length ? `<div class="avec">Avec : ${pieces.map((p) => `<a href="#${etat.recettes.animal}/${p.id}">${esc(p.nom)}</a>`).join(" · ")}</div>` : "";
    return `<details class="recette"${ouverte ? " open" : ""}>
      <summary><span class="nom">${esc(r.nom)}</span><small>${esc(r.pour)} · ${esc(r.temps)}</small></summary>
      <div class="corps">
        <b>Ingrédients</b><ul>${r.ingredients.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>
        <b>Étapes</b><ol>${r.etapes.map((e) => `<li>${esc(e)}</li>`).join("")}</ol>
        <div class="client">💬 <b>Au comptoir :</b> ${esc(r.client)}</div>
        ${avec}
      </div>
    </details>`;
  }

  function rendreEquivalences(piece) {
    if (!piece.region) return "";
    const reg = REGIONS[piece.region];
    const lignes = ANIMAUX.map((a) => {
      const info = reg.par[a.id];
      const liens = PIECES[a.id].filter((p) => p.region === piece.region)
        .map((p) => p.id === piece.id && a.id === etat.animal
          ? `<b>${esc(p.nom)}</b>`
          : `<a href="#${a.id}/${p.id}">${esc(p.nom)}</a>`).join(" · ");
      return `<div class="ligne"><span class="animal">${esc(a.nom)}</span><div>
        <div>${esc(info.nom)} : ${liens}</div>
        <div class="muscles">Fiche comparatif : ${info.muscles.map(esc).join(", ")}</div></div></div>`;
    }).join("");
    return `<h3>Même région chez les autres animaux</h3>
      <div class="equivalences">${lignes}</div>`;
  }

  function rendreAccueilSquelette() {
    return `<div class="accueil">
      <div class="kicker">${esc(nomAnimal(etat.animal))} · squelette</div>
      <h2>Touche un os</h2>
      <p>Le corps devient transparent : les os apparaissent à leur place. Chaque pièce de viande repose sur un os ; désosser, c’est suivre l’os.</p>
      <div class="pas">
        <div><b>1</b><span>Touche un os : la vue plonge dessus. Tourne autour, zoome, déplace-toi pour voir sa forme sous tous les angles.</span></div>
        <div><b>2</b><span>Les muscles posés sur l’os apparaissent autour de lui, avec leur nom ; touche un muscle pour ouvrir sa fiche.</span></div>
        <div><b>3</b><span>« Muscles » montre toute la viande sur le squelette ; « Éclater » écarte les os les uns des autres.</span></div>
      </div>
      ${window.COMPTE_OS ? `<div class="classeur-os"><strong>Au classeur :</strong> ${esc(window.COMPTE_OS)}</div>` : ""}
      <p class="source">Os et muscles modélisés pour comprendre la structure : formes simplifiées, à valider avec ton formateur.</p>
    </div>`;
  }

  function rendreFicheOs(o) {
    const pieces = o.pieces.map((id) => pieceDe(etat.animal, id)).filter(Boolean);
    return `
      <div class="kicker">${esc(nomAnimal(etat.animal))} · squelette</div>
      <h2>${esc(o.nom)}</h2>
      <p class="alias">${esc(o.savant)}</p>
      <p>${esc(o.savoir)}</p>
      <div class="conseil"><strong>Au désossage :</strong> ${esc(o.desossage)}</div>
      ${lienAtelierOs(etat.animal, o.id) ? `<p class="lien-atelier"><a href="${lienAtelierOs(etat.animal, o.id)}">Voir cet os en grand : ses repères et les muscles posés dessus ↗</a></p>` : ""}
      ${o.classeur ? `<div class="classeur-os"><strong>Au classeur :</strong> ${esc(o.classeur)}</div>` : ""}
      ${o.mrs ? `<p class="note-mrs">⚠️ ${esc(window.REGLE_MRS)}</p>` : ""}
      <h3>Pièces posées sur cet os</h3>
      ${pieces.length ? `<ul class="transfo">${pieces.map((p) => `<li><a href="#${etat.animal}/${p.id}"><b>${esc(p.nom)}</b></a><span>${esc(typeCuisson(p).txt)}</span></li>`).join("")}</ul>`
        : `<p>Aucune pièce de ta planche ne repose sur cet os.</p>`}
      <p class="source">Sources : fiche « Le squelette du bovin » (École des Métiers Bigard) ; tableau des pièces de bœuf (colonne OS) ; Wikipédia, « Désossage » ; classeur de découpe (tableaux « Le bœuf » n° 1 à 3, guide de découpe). Conseils à faire valider par ton formateur.</p>`;
  }

  // Étoiles du guide de découpe : ★ pleines + ☆ restantes (sur 3).
  const etoiles = (n) => `<span class="etoiles" aria-label="${n} étoile${n > 1 ? "s" : ""} sur 3">${"★".repeat(n)}<i>${"★".repeat(3 - n)}</i></span>`;

  // Classeur de découpe : dénominations du guide (★), fiches magasin, petits noms des tableaux.
  function rendreClasseur(piece) {
    const c = CLASSEUR && CLASSEUR[etat.animal] && CLASSEUR[etat.animal][piece.id];
    if (!c) return "";
    const guide = [...(c.guide || [])].sort((a, b) => b.etoiles - a.etoiles);
    const lignes = guide.map((g) => `<li>
        <div class="denom"><b>${esc(g.nom)}</b> ${etoiles(g.etoiles)}${g.mention ? ` <span class="mention">${esc(g.mention)}</span>` : ""}</div>
        <div class="morceau">${esc(g.morceau)}${g.p ? ` <small>· guide p. ${g.p}</small>` : ""}</div>
        <span>${esc(g.preparation)}</span></li>`).join("");
    const champ = (titre, v) => v ? `<dt>${titre}</dt><dd>${Array.isArray(v) ? v.map(esc).join(" · ") : esc(v)}</dd>` : "";
    const fiches = (c.magasin || []).map((f) => `<details class="fiche-magasin"><summary>Fiche magasin : ${esc(f.titre)}</summary>
        <dl>${champ("Contrôle", f.controle)}${champ("Parage", f.parage)}${champ("Découpe", f.decoupe)}${champ("Barquettes", f.barquettes)}${champ("Poids", f.poids)}</dl></details>`).join("");
    return `<h3>En libre-service : le classeur de découpe</h3>
      <p class="note-etoiles"><b>Libre-service seulement.</b> Ces dénominations et leurs étoiles sont obligatoires en libre-service
        (barquettes) depuis le 13 décembre 2014, mais facultatives au rayon traditionnel, où le boucher conseille de vive voix
        (<a href="https://www.reussir.fr/lesmarches/vers-de-nouvelles-denominations-des-viandes-bovines" target="_blank" rel="noopener">Réussir</a>).
        ${esc(CLASSEUR.etoiles)}</p>
      ${lignes ? `<ul class="classeur">${lignes}</ul>` : ""}
      ${c.noms && c.noms.length ? `<p class="petits-noms"><b>Petits noms :</b> ${c.noms.map(esc).join(" · ")}</p>` : ""}
      ${fiches}
      <details class="fiche-magasin lexique"><summary>Les mots du classeur</summary>
        <dl>${CLASSEUR.lexique.map(([m, d]) => `<dt>${esc(m)}</dt><dd>${esc(d)}</dd>`).join("")}</dl></details>
      <p class="source">Sources : ${esc(CLASSEUR.sources.guide)} ; ${esc(CLASSEUR.sources.magasin)} ; ${esc(CLASSEUR.sources.tableaux)}.</p>`;
  }

  function rendreOsDePiece(piece) {
    const liste = osDePiece(etat.animal, piece.id);
    if (!liste.length) return "";
    return `<h3>Sur quel os ?</h3>
      <p class="os-lien">${liste.map((o) => `<a href="#${etat.animal}/squelette/${o.id}">${esc(o.nom)}</a> <small>(${esc(o.savant)})</small>`).join(" · ")}</p>`;
  }

  function rendrePanneau() {
    const panneau = $("panneau");
    if (etat.squelette) {
      const o = etat.os && osDe(etat.animal, etat.os);
      panneau.innerHTML = o ? rendreFicheOs(o) : rendreAccueilSquelette();
      panneau.scrollTop = 0;
      return;
    }
    const piece = etat.piece && pieceDe(etat.animal, etat.piece);
    if (!piece) { panneau.innerHTML = rendreAccueil(); return; }
    const t = typeCuisson(piece);
    panneau.innerHTML = `
      <div class="kicker">${esc(nomAnimal(etat.animal))}</div>
      <h2>${esc(piece.nom)}</h2>
      ${piece.alias && piece.alias.length ? `<p class="alias">Aussi : ${piece.alias.map(esc).join(", ")}</p>` : ""}
      <div>${piece.abat ? `<span class="type abat">Abat</span>` : ""}<span class="type ${t.cls}">${t.txt}</span></div>
      <div class="cuissons">${piece.cuissons.map(puceCuisson).join("")}</div>
      <p>${esc(piece.savoir)}</p>
      <div class="conseil"><strong>Le mot au client :</strong> ${esc(piece.client)}</div>

      <h3>Transformations bouchères</h3>
      <ul class="transfo">${piece.transformations.map(([n, d]) => `<li><b>${esc(n)}</b><span>${esc(d)}</span></li>`).join("")}</ul>

      ${lienAtelierPiece(etat.animal, piece.id) ? `<p class="lien-atelier"><a href="${lienAtelierPiece(etat.animal, piece.id)}">Voir ses muscles en 3D et comment les séparer ↗</a></p>` : ""}

      ${rendreClasseur(piece)}

      ${rendreOsDePiece(piece)}

      ${piece.recettes.length ? `<p class="vers-recettes"><a class="bouton-lien" href="#recettes/${etat.animal}/${piece.id}">Ses recettes (${piece.recettes.length}) →</a></p>` : ""}

      ${rendreEquivalences(piece)}`;
    panneau.scrollTop = 0;
  }

  function rendreComparatif() {
    const sec = $("vue-comparatif");
    const tete = ANIMAUX.map((a) => `<th>${esc(a.nom)}</th>`).join("");
    const lignes = Object.entries(REGIONS).map(([id, reg]) => {
      const cellules = ANIMAUX.map((a) => {
        const info = reg.par[a.id];
        return `<td class="c-${a.id}" data-animal="${esc(a.nom)}"><button type="button" data-region="${id}" data-animal="${a.id}">
          <span class="region-nom">${esc(info.nom)}</span>
          <ul>${info.muscles.map((m) => `<li>${esc(m)}</li>`).join("")}</ul></button></td>`;
      }).join("");
      return `<tr><th>${esc(reg.titre)}${reg.note ? `<div class="note">${esc(reg.note)}</div>` : ""}</th>${cellules}</tr>`;
    }).join("");
    sec.innerHTML = `<h2>Comparatif des dénominations musculaires</h2>
      <p>Une même région porte un nom différent selon l’animal. Clique sur une case pour voir la région surlignée sur l’animal en 3D.</p>
      <table class="tableau"><thead><tr><th>Région</th>${tete}</tr></thead><tbody>${lignes}</tbody></table>`;
  }

  // ---------- onglet Recettes : toutes les recettes d'un animal, ou celles d'une pièce ----------
  function rendreRecettes() {
    const { animal, piece } = etat.recettes;
    const parRecette = new Map();
    for (const p of PIECES[animal]) for (const id of p.recettes || []) {
      if (!RECETTES[id]) continue;
      if (!parRecette.has(id)) parRecette.set(id, []);
      parRecette.get(id).push(p);
    }
    const choix = piece && pieceDe(animal, piece);
    const ids = choix ? choix.recettes.filter((id) => RECETTES[id])
      : [...parRecette.keys()].sort((a, b) => RECETTES[a].nom.localeCompare(RECETTES[b].nom, "fr"));
    $("vue-recettes").innerHTML = `
      <h2>Recettes à proposer au client</h2>
      <div class="choix-animal">${ANIMAUX.map((a) => `<a href="#recettes/${a.id}"${a.id === animal && !choix ? ` aria-current="page"` : ""}>${esc(a.nom)}</a>`).join("")}</div>
      ${choix ? `<p class="note">Pour <b>${esc(choix.nom)}</b> (${esc(nomAnimal(animal))}) · <a href="#recettes/${animal}">toutes les recettes</a> · <a href="#${animal}/${choix.id}">revoir la pièce en 3D</a></p>`
        : `<p class="note">${ids.length} recettes. Touche une recette pour l’ouvrir.</p>`}
      ${ids.map((id, i) => rendreRecette(id, !!choix && i === 0, parRecette.get(id) || [])).join("")}`;
  }

  // ---------- onglet Mise en avant : le rayon traditionnel (photos et tutos à venir) ----------
  function rendreEtal() {
    const P = ATELIER && ATELIER.presentation;
    if (!P) { $("vue-etal").innerHTML = `<h2>Mise en avant au rayon traditionnel</h2><p class="note">Contenu à venir.</p>`; return; }
    const idee = (i) => `<div class="idee"><b>${esc(i.titre)}</b><p>${esc(i.texte)}</p></div>`;
    const cles = new Set();
    const noter = (l) => (l || []).forEach((s) => cles.add(s));
    P.general.forEach((i) => noter(i.sources));
    Object.values(P.pieces).flat().forEach((i) => noter(i.sources));
    const mof = P.mof;
    if (mof) { mof.regles.forEach((i) => noter(i.sources)); mof.voir.forEach((v) => cles.add(v.source)); mof.commentFaire.forEach((c) => noter(c.sources)); }
    const source = (k) => { const s = ATELIER.sources[k]; return !s ? "" : s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.titre)}</a>` : esc(s.titre); };
    $("vue-etal").innerHTML = `
      <h2>Mise en avant au rayon traditionnel</h2>
      <p class="note">À venir : des photos et des tutos pas à pas. En attendant, les idées et les vidéos ci-dessous.</p>
      <h3>Pour toute la vitrine</h3>${P.general.map(idee).join("")}
      ${mof ? `<h3>Chez les Meilleurs Ouvriers de France et aux examens</h3>${mof.regles.map(idee).join("")}
        <h3>Comment faire</h3>${mof.commentFaire.map((c) => `<details class="comment-faire"><summary>${esc(c.titre)}</summary><ol>${c.etapes.map((e) => `<li>${esc(e)}</li>`).join("")}</ol></details>`).join("")}
        <h3>Le voir en photo et en vidéo</h3><ul class="voir-mof">${mof.voir.map((v) => `<li><a href="${esc(ATELIER.sources[v.source].url)}" target="_blank" rel="noopener">${esc(v.titre)} ↗</a><br><small>${esc(v.texte)}</small></li>`).join("")}</ul>` : ""}
      <h3>Idées par morceau (bœuf)</h3>
      ${Object.entries(P.pieces).map(([p, l]) => `<details class="comment-faire"><summary>${esc((pieceDe("boeuf", p) || { nom: p }).nom)}</summary>${l.map(idee).join("")}</details>`).join("")}
      <details class="sources-repli"><summary>Sources</summary><ul>${[...cles].filter((k) => ATELIER.sources[k]).map((k) => `<li>${source(k)}</li>`).join("")}</ul></details>`;
  }

  function rendre() {
    // La vue est redessinée : la bulle de survol de l'ancienne pièce ne doit pas rester affichée.
    $("bulle").hidden = true;
    rendreOnglets();
    const vue = etat.vue;
    $("page").classList.toggle("mode-comparatif", vue !== "planche");
    $("vue-planche").hidden = vue !== "planche";
    $("panneau").hidden = vue !== "planche";
    $("vue-comparatif").hidden = vue !== "comparatif";
    $("vue-recettes").hidden = vue !== "recettes";
    $("vue-etal").hidden = vue !== "etal";
    if (vue === "comparatif") { rendreComparatif(); return; }
    if (vue === "recettes") { rendreRecettes(); window.scrollTo(0, 0); return; }
    if (vue === "etal") { rendreEtal(); window.scrollTo(0, 0); return; }
    rendre3D();
    rendreCouleurs();
    rendreLegende();
    rendreListe();
    rendrePanneau();
  }

  // ---------- interactions ----------
  // Choisir une pièce : elle s'affiche en 3D (sur téléphone, la page remonte jusqu'à la 3D si besoin) ; sa fiche
  // est sous la vue, à un bouton « Fiche ».
  function choisir(id) {
    aller(etat.animal, id);
  }

  // Clic sur le modèle : la pièce est déjà sous les yeux, on ne fait pas tourner la caméra.
  function choisirSurModele(id) {
    etat.montrer = false;
    choisir(id);
  }

  // Choisir un os : la vue plonge dessus, et sur téléphone la page remonte jusqu'à la 3D si besoin (la carte
  // sous la vue a un bouton « Fiche »).
  function choisirOs(id) {
    allerOs(etat.animal, id);
  }
  function choisirOsSurModele(id) {
    choisirOs(id);
  }

  const bulle = $("bulle");
  // cible : { type: "piece" | "os", id } ou null
  function montrerBulle(cible, x, y) {
    const nom = !cible ? null : cible.type === "os" ? (osDe(etat.animal, cible.id) || {}).nom : (pieceDe(etat.animal, cible.id) || {}).nom;
    if (!nom || x === undefined) { bulle.hidden = true; return; }
    bulle.textContent = nom;
    bulle.style.left = x + "px";
    bulle.style.top = y + "px";
    bulle.hidden = false;
  }

  $("outils3d").addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b || !vue3d) return;
    if (b.dataset.vue) vue3d.vue(b.dataset.vue);
    if (b.dataset.zoom) vue3d.zoomer(parseFloat(b.dataset.zoom));
    if (b.hasAttribute("data-noms")) b.setAttribute("aria-pressed", String(vue3d.noms(b.getAttribute("aria-pressed") !== "true")));
    if (b.hasAttribute("data-squelette")) {
      if (etat.squelette) aller(etat.animal, null); else allerOs(etat.animal, null);
    }
    if (b.hasAttribute("data-eclater")) { etat.eclate = !etat.eclate; rendre(); }
    if (b.hasAttribute("data-plein")) basculerPleinEcran();
    // « Muscles » : toute la viande posée sur le squelette (on quitte la plongée pour la voir en entier)
    if (b.hasAttribute("data-muscles")) {
      etat.viande = !etat.viande;
      if (etat.viande && etat.os) { etat.recadrer = true; allerOs(etat.animal, null); } else { etat.montrer = false; rendre(); }
    }
  });

  // Carte de la pièce ou de l'os choisi (sous la vue 3D).
  $("vue-planche").addEventListener("click", (e) => {
    const b = e.target.closest("#carte3d button");
    if (!b) return;
    if (b.dataset.voir === "muscles") etat.muscles = !etat.muscles;
    if (b.dataset.voir === "autres") etat.autresOs = !etat.autresOs;
    if (b.dataset.voir) { etat.montrer = false; rendre(); }
    if (b.hasAttribute("data-fiche")) {
      basculerPleinEcran(false);
      $("panneau").scrollIntoView({ behavior: "smooth", block: "start" });
    }
    if (b.hasAttribute("data-sortir")) {
      if (etat.squelette) { etat.recadrer = true; allerOs(etat.animal, null); } else aller(etat.animal, null);
    }
  });

  $("legende").addEventListener("click", (e) => {
    const b = e.target.closest("[data-filtre]");
    if (!b) return;
    const id = b.dataset.filtre;
    const actif = etat.filtre && etat.filtre.type === "cuisson" && etat.filtre.id === id;
    etat.filtre = id && !actif ? { type: "cuisson", id } : null;
    rendre();
  });
  $("liste-pieces").addEventListener("click", (e) => {
    const b = e.target.closest("[data-piece]");
    if (b) choisir(b.dataset.piece);
    const o = e.target.closest("[data-os]");
    if (o) choisirOs(o.dataset.os);
  });
  $("vue-comparatif").addEventListener("click", (e) => {
    const b = e.target.closest("[data-region]");
    if (!b) return;
    // L'animal est posé AVANT la navigation : lireAdresse() ne voit pas de changement
    // d'animal et conserve donc le filtre de région.
    etat.filtre = { type: "region", id: b.dataset.region };
    etat.animal = b.dataset.animal;
    etat.piece = null;
    location.hash = "#" + b.dataset.animal;
  });

  // Plein écran : la vue 3D et ses boutons prennent tout l'écran, pour se « plonger » dans le squelette.
  function basculerPleinEcran(oui) {
    const plein = oui ?? !document.body.classList.contains("plein-ecran-3d");
    document.body.classList.toggle("plein-ecran-3d", plein);
    if (plein) window.scrollTo(0, 0);
    rendreOutils();
  }
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && document.body.classList.contains("plein-ecran-3d")) basculerPleinEcran(false);
  });

  window.addEventListener("hashchange", () => { lireAdresse(); rendre(); montrer3D(); });
  lireAdresse();
  rendre();
})();
