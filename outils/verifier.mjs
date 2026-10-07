// Vérifie la cohérence du contenu et des modèles 3D cliquables.
// Usage : node outils/verifier.mjs   (code de sortie 0 = tout est bon)
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const APP = process.env.APP_DIR || join(dirname(dirname(fileURLToPath(import.meta.url))), "app");
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["data/modeles3d.js", "data/recettes.js", "data/pieces.js", "data/os.js", "data/classeur.js", "data/anatomie.js"]) {
  vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx, { filename: f });
}
const { ANIMAUX, PIECES, CUISSONS, REGIONS, RECETTES, MODELES3D, OS, CLASSEUR, ANATOMIE } = ctx.window;

const erreurs = [];
const err = (m) => erreurs.push(m);

// Tous les scripts appelés par la page doivent exister (l'appli marche sans réseau).
const page = readFileSync(join(APP, "index.html"), "utf8");
for (const [, src] of page.matchAll(/<script src="([^"]+)"/g)) if (!existsSync(join(APP, src))) err(`index.html : script manquant ${src}`);
for (const [, href] of page.matchAll(/<link[^>]+href="([^"]+)"/g)) if (!/^https?:/.test(href) && !existsSync(join(APP, href))) err(`index.html : fichier manquant ${href}`);

// --- décodage des données compressées des modèles (même format que app/vue3d.js)
const octets = (b64) => new Uint8Array(Buffer.from(b64, "base64"));
function plages(b64, n) {
  const b = octets(b64), out = new Uint8Array(n);
  let o = 0;
  for (let i = 0; i < b.length; i += 3) { const l = b[i + 1] | (b[i + 2] << 8); out.fill(b[i], o, o + l); o += l; }
  return { out, total: o };
}
function etiquetteEn(m, carte, x, y) {
  const c = m.carte;
  const col = Math.floor(((x - c.x0) / (c.x1 - c.x0)) * c.largeur), lig = Math.floor(((c.y1 - y) / (c.y1 - c.y0)) * c.hauteur);
  return carte[lig * c.largeur + col] - 1;
}

const utilisees = new Set();
for (const a of ANIMAUX) {
  const pieces = PIECES[a.id];
  const m = MODELES3D[a.id];
  if (!pieces) { err(`${a.id}: aucune fiche de pièce`); continue; }
  if (!m) { err(`${a.id}: aucun modèle 3D`); continue; }

  // maillage : tailles cohérentes, aucun triangle ne pointe hors des sommets
  const nbSommets = octets(m.sommets).length / 6;
  const tri = octets(m.triangles);
  const idx = m.indices32 ? new Uint32Array(tri.buffer) : new Uint16Array(tri.buffer);
  if (!Number.isInteger(nbSommets) || nbSommets < 1000) err(`${a.id}: maillage invalide (${nbSommets} sommets)`);
  if (idx.length % 3 || idx.some((i) => i >= nbSommets)) err(`${a.id}: triangles invalides`);
  if (octets(m.parties).length !== nbSommets) err(`${a.id}: une « partie » par sommet attendue`);
  const { out: carte, total } = plages(m.carte.rle, m.carte.largeur * m.carte.hauteur);
  if (total !== m.carte.largeur * m.carte.hauteur) err(`${a.id}: carte des pièces de taille incorrecte`);

  const idsPieces = new Set(pieces.map((p) => p.id));
  const idsModele = new Set(m.pieces);
  if (idsPieces.size !== pieces.length) err(`${a.id}: identifiant de pièce en double`);
  for (const id of idsModele) if (!idsPieces.has(id)) err(`${a.id}/${id}: pièce du modèle sans fiche`);
  for (const id of idsPieces) if (!idsModele.has(id)) err(`${a.id}/${id}: fiche absente du modèle 3D`);

  for (const p of pieces) {
    const ou = `${a.id}/${p.id}`;
    if (!p.nom) err(`${ou}: nom vide`);
    if (!p.savoir || p.savoir.length < 30) err(`${ou}: « à savoir » absent ou trop court`);
    if (!p.client) err(`${ou}: conseil client absent`);
    if (!p.cuissons?.length) err(`${ou}: aucun mode de cuisson`);
    for (const c of p.cuissons || []) if (!CUISSONS[c]) err(`${ou}: cuisson inconnue « ${c} »`);
    if (!p.transformations?.length) err(`${ou}: aucune transformation`);
    for (const t of p.transformations || []) if (!Array.isArray(t) || t.length !== 2 || !t[0] || !t[1]) err(`${ou}: transformation mal formée`);
    if (!p.recettes?.length) err(`${ou}: aucune recette`);
    for (const r of p.recettes || []) { if (!RECETTES[r]) err(`${ou}: recette inconnue « ${r} »`); utilisees.add(r); }
    if (p.region !== null && !REGIONS[p.region]) err(`${ou}: région inconnue « ${p.region} »`);

    // La pièce doit être assez grande pour être touchée, et son centre doit bien porter son nom.
    if (idsModele.has(p.id)) {
      if ((m.aires[p.id] || 0) < 150) err(`${ou}: pièce trop petite sur le modèle (${m.aires[p.id] || 0} px)`);
      const c = m.centres[p.id];
      if (!c) err(`${ou}: pas de centre`);
      else if (m.pieces[etiquetteEn(m, carte, c[0], c[1])] !== p.id) err(`${ou}: le centre ne tombe pas sur la pièce`);
    }
  }
  for (const r of Object.keys(REGIONS)) {
    if (!REGIONS[r].par[a.id]) err(`région ${r}: pas de colonne ${a.id}`);
    if (!pieces.some((p) => p.region === r)) err(`région ${r}: aucune pièce de ${a.id} rattachée`);
  }
}
for (const [id, r] of Object.entries(RECETTES)) {
  if (!utilisees.has(id)) err(`recette « ${id} » jamais proposée`);
  for (const k of ["nom", "pour", "temps", "client"]) if (!r[k]) err(`recette ${id}: champ ${k} vide`);
  if (!r.ingredients?.length || !r.etapes?.length) err(`recette ${id}: ingrédients ou étapes manquants`);
}

// --- squelettes (data/anatomie.js, chargé à la demande par l'appli) : chaque os a sa fiche complète et
// son maillage ; chaque pièce posée sur un os a son muscle en volume (sinon la plongée n'en montrerait rien)
let nbOs = 0, nbMuscles = 0;
function maillageValide(e, ou) {
  const n = octets(e.sommets).length / 6;
  const idx = new Uint16Array(octets(e.triangles).buffer);
  if (!Number.isInteger(n) || n < 20 || idx.length % 3 || idx.some((i) => i >= n)) err(`${ou}: maillage invalide`);
  if (e.ombre && octets(e.ombre).length !== n) err(`${ou}: une valeur d'ombre par sommet attendue`);
  if (e.parties && octets(e.parties).length !== n) err(`${ou}: une « partie » par sommet attendue`);
  const [lo, hi] = e.boite;
  if (lo.some((v, i) => !(v < hi[i]))) err(`${ou}: boîte englobante vide`);
  if (e.pair && lo[2] < -0.01) err(`${ou}: un os ou muscle pair doit être modélisé côté gauche (z > 0)`);
}
for (const [animal, liste] of Object.entries(OS || {})) {
  const A = ANATOMIE && ANATOMIE[animal];
  if (!A || !A.os) { err(`${animal}: fiches d'os sans squelette 3D (data/anatomie.js)`); continue; }
  const ids = new Set(liste.map((o) => o.id));
  if (ids.size !== liste.length) err(`${animal}: identifiant d'os en double`);
  const maillages = new Set(A.os.map((e) => e.id));
  for (const id of maillages) if (!ids.has(id)) err(`${animal}/os ${id}: maillage sans fiche`);
  const muscles = A.muscles || [];
  const piecesMusclees = new Set(muscles.flatMap((m) => m.pieces));
  for (const o of liste) {
    const ou = `${animal}/os ${o.id}`;
    nbOs++;
    if (!maillages.has(o.id)) err(`${ou}: fiche sans maillage 3D`);
    for (const k of ["nom", "savant", "savoir", "desossage", "groupe"]) if (!o[k]) err(`${ou}: champ ${k} vide`);
    for (const p of o.pieces) {
      if (!PIECES[animal].some((x) => x.id === p)) err(`${ou}: pièce inconnue « ${p} »`);
      else if (!piecesMusclees.has(p)) err(`${ou}: la pièce « ${p} » posée sur l'os n'a pas de muscle en volume`);
    }
  }
  for (const e of A.os) maillageValide(e, `${animal}/os ${e.id}`);
  for (const m of muscles) {
    nbMuscles++;
    maillageValide(m, `${animal}/muscle ${m.id}`);
    for (const p of m.pieces || []) if (!PIECES[animal].some((x) => x.id === p)) err(`${animal}/muscle ${m.id}: pièce inconnue « ${p} »`);
  }
}

// --- classeur de découpe : chaque fiche est rattachée à une vraie pièce et chaque dénomination est complète
let nbDenominations = 0;
if (!CLASSEUR) err("data/classeur.js : CLASSEUR absent");
else {
  for (const k of ["guide", "magasin", "tableaux"]) if (!CLASSEUR.sources?.[k]) err(`classeur : source ${k} non citée`);
  if (!CLASSEUR.etoiles || !CLASSEUR.lexique?.length) err("classeur : explication des étoiles ou lexique manquant");
  for (const animal of Object.keys(CLASSEUR).filter((k) => PIECES[k])) {
    for (const [id, c] of Object.entries(CLASSEUR[animal])) {
      const ou = `classeur ${animal}/${id}`;
      if (!PIECES[animal].some((p) => p.id === id)) err(`${ou}: pièce inconnue`);
      if (!c.guide?.length && !c.magasin?.length) err(`${ou}: ni dénomination ni fiche magasin`);
      for (const g of c.guide || []) {
        nbDenominations++;
        if (!g.nom || !g.morceau || !g.preparation) err(`${ou}: dénomination incomplète ${JSON.stringify(g).slice(0, 80)}`);
        if (![1, 2, 3].includes(g.etoiles)) err(`${ou}: étoiles ${g.etoiles} (1 à 3 attendu)`);
        if (!(g.p >= 1 && g.p <= 51)) err(`${ou}: page du guide ${g.p} hors du guide (1 à 51)`);
      }
      for (const f of c.magasin || []) if (!f.titre || !(f.controle || f.parage || f.decoupe || f.barquettes)) err(`${ou}: fiche magasin vide`);
    }
  }
}

const nbPieces = ANIMAUX.reduce((n, a) => n + (PIECES[a.id]?.length || 0), 0);
if (erreurs.length) {
  console.error(`ÉCHEC — ${erreurs.length} problème(s) :\n - ` + erreurs.join("\n - "));
  process.exit(1);
}
console.log(`OK — ${ANIMAUX.length} animaux, ${nbPieces} pièces, ${Object.keys(RECETTES).length} recettes, ${nbOs} os, ${nbMuscles} muscles en volume, ${nbDenominations} dénominations du classeur, modèles 3D et fiches cohérents.`);
