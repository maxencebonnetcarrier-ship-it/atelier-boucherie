/* Atelier Boucherie — logique de l'interface (fonctionne en ouvrant index.html, sans réseau). */
(function () {
  "use strict";

  const { ANIMAUX, PIECES, CUISSONS, REGIONS, RECETTES } = window;
  const RAPIDES = ["griller", "poeler", "rotir", "sauter", "cru"];
  const LENTES = ["braiser", "bouillir"];

  const $ = (id) => document.getElementById(id);
  const etat = { animal: ANIMAUX[0].id, piece: null, filtre: null, vue: "planche", montrer: true };

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
    const [a, p] = decodeURIComponent(location.hash.replace(/^#/, "")).split("/");
    if (a === "comparatif") { etat.vue = "comparatif"; return; }
    etat.vue = "planche";
    if (ANIMAUX.some((x) => x.id === a)) {
      if (a !== etat.animal) etat.filtre = null;
      etat.animal = a;
      etat.piece = p && pieceDe(a, p) ? p : null;
    }
  }

  function aller(animal, piece) {
    const cible = "#" + animal + (piece ? "/" + piece : "");
    if (location.hash === cible) { lireAdresse(); rendre(); } else { location.hash = cible; }
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
      vue3d = window.Vue3D($("planche"), { surClic: choisirSurModele, surSurvol: montrerBulle });
      window.ATELIER3D = vue3d; // accès pour les tests automatiques
    }
    vue3d.afficher(etat.animal, Object.fromEntries(PIECES[etat.animal].map((p) => [p.id, nomCourt(p)])));
    vue3d.etat({
      couleurs: couleursPieces(), selection: etat.piece,
      etiquettes: etat.filtre ? PIECES[etat.animal].filter(correspond).map((p) => p.id) : null,
    });
    if (etat.piece && etat.montrer) vue3d.focaliser(etat.piece);
    etat.montrer = true;
    $("planche").setAttribute("aria-label", `${nomAnimal(etat.animal)} en 3D : glisse pour le faire tourner, clique sur une pièce`);
  }

  function rendreCouleurs() {
    const presentes = [...new Set(PIECES[etat.animal].map(famille))];
    const noms = { rapide: "cuisson rapide", lente: "cuisson lente", mixte: "rapide ou lente", abat: "abat" };
    $("couleurs3d").innerHTML = `<span class="titre">Couleurs :</span>` + ["rapide", "mixte", "lente", "abat"]
      .filter((f) => presentes.includes(f))
      .map((f) => `<span class="pastille" style="--c:${TEINTE_FAMILLE[f]}">${noms[f]}</span>`).join("")
      + `<span class="pastille" style="--c:${window.Vue3D.ROBES[etat.animal]}">robe de l’animal (pas une pièce)</span>`;
  }

  function rendreLegende() {
    const leg = $("legende");
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
        <div><b>3</b><span>Ouvre une recette simple à proposer au client.</span></div>
      </div>
      <h3>Les modes de cuisson</h3>
      <div class="definitions">${Object.keys(CUISSONS).map((c) =>
        `<div>${puceCuisson(c)}<span>${esc(CUISSONS[c].definition)}</span></div>`).join("")}</div>
    </div>`;
  }

  function rendreRecette(id, ouverte) {
    const r = RECETTES[id];
    return `<details class="recette"${ouverte ? " open" : ""}>
      <summary><span class="nom">${esc(r.nom)}</span><small>${esc(r.pour)} · ${esc(r.temps)}</small></summary>
      <div class="corps">
        <b>Ingrédients</b><ul>${r.ingredients.map((i) => `<li>${esc(i)}</li>`).join("")}</ul>
        <b>Étapes</b><ol>${r.etapes.map((e) => `<li>${esc(e)}</li>`).join("")}</ol>
        <div class="client">💬 <b>Au comptoir :</b> ${esc(r.client)}</div>
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

  function rendrePanneau() {
    const panneau = $("panneau");
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

      <h3>Recettes simples à proposer</h3>
      ${piece.recettes.map((r, i) => rendreRecette(r, i === 0)).join("")}

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

  function rendre() {
    // La vue est redessinée : la bulle de survol de l'ancienne pièce ne doit pas rester affichée.
    $("bulle").hidden = true;
    rendreOnglets();
    const comparatif = etat.vue === "comparatif";
    $("page").classList.toggle("mode-comparatif", comparatif);
    $("vue-planche").hidden = comparatif;
    $("panneau").hidden = comparatif;
    $("vue-comparatif").hidden = !comparatif;
    if (comparatif) { rendreComparatif(); return; }
    rendre3D();
    rendreCouleurs();
    rendreLegende();
    rendreListe();
    rendrePanneau();
  }

  // ---------- interactions ----------
  function choisir(id) {
    aller(etat.animal, id);
    if (window.matchMedia("(max-width: 900px)").matches) {
      $("panneau").scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }

  // Clic sur le modèle : la pièce est déjà sous les yeux, on ne fait pas tourner la caméra.
  function choisirSurModele(id) {
    etat.montrer = false;
    choisir(id);
  }

  const bulle = $("bulle");
  function montrerBulle(id, x, y) {
    const p = id && pieceDe(etat.animal, id);
    if (!p || x === undefined) { bulle.hidden = true; return; }
    bulle.textContent = p.nom;
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

  window.addEventListener("hashchange", () => { lireAdresse(); rendre(); });
  lireAdresse();
  rendre();
})();
