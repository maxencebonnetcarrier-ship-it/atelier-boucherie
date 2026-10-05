// Vérifie la cohérence du contenu et des modèles 3D cliquables.
// Usage : node outils/verifier.mjs   (code de sortie 0 = tout est bon)
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const APP = process.env.APP_DIR || join(dirname(dirname(fileURLToPath(import.meta.url))), "app");
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["data/modeles3d.js", "data/recettes.js", "data/pieces.js"]) {
  vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx, { filename: f });
}
const { ANIMAUX, PIECES, CUISSONS, REGIONS, RECETTES, MODELES3D } = ctx.window;

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

const nbPieces = ANIMAUX.reduce((n, a) => n + (PIECES[a.id]?.length || 0), 0);
if (erreurs.length) {
  console.error(`ÉCHEC — ${erreurs.length} problème(s) :\n - ` + erreurs.join("\n - "));
  process.exit(1);
}
console.log(`OK — ${ANIMAUX.length} animaux, ${nbPieces} pièces, ${Object.keys(RECETTES).length} recettes, modèles 3D et fiches cohérents.`);
