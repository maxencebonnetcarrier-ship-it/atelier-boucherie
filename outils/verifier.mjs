// Vérifie la cohérence du contenu et des zones cliquables.
// Usage : node outils/verifier.mjs   (code de sortie 0 = tout est bon)
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const APP = process.env.APP_DIR || join(dirname(dirname(fileURLToPath(import.meta.url))), "app");
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["data/zones.js", "data/recettes.js", "data/pieces.js"]) {
  vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx, { filename: f });
}
const { ANIMAUX, PIECES, CUISSONS, REGIONS, RECETTES, ZONES } = ctx.window;

const erreurs = [];
const err = (m) => erreurs.push(m);

// --- géométrie : point dans un chemin SVG "M..L..Z" (règle pair-impair, comme fill-rule evenodd)
function polygones(d) {
  return d.split("M").filter(Boolean).map((s) => s.replace("Z", "").split("L").map((p) => p.split(",").map(Number)));
}
function dedans(d, x, y) {
  let c = false;
  for (const poly of polygones(d)) {
    for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      const [xi, yi] = poly[i], [xj, yj] = poly[j];
      if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) c = !c;
    }
  }
  return c;
}

const utilisees = new Set();
for (const a of ANIMAUX) {
  const pieces = PIECES[a.id];
  const zones = ZONES[a.id];
  if (!pieces) { err(`${a.id}: aucune fiche de pièce`); continue; }
  if (!zones) { err(`${a.id}: aucune zone cliquable`); continue; }
  if (!existsSync(join(APP, zones.image))) err(`${a.id}: image manquante ${zones.image}`);

  const idsPieces = new Set(pieces.map((p) => p.id));
  const idsZones = new Set(Object.keys(zones.zones));
  if (idsPieces.size !== pieces.length) err(`${a.id}: identifiant de pièce en double`);
  for (const id of idsZones) if (!idsPieces.has(id)) err(`${a.id}/${id}: zone sans fiche`);
  for (const id of idsPieces) if (!idsZones.has(id)) err(`${a.id}/${id}: fiche sans zone cliquable`);

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

    // Le centre de la zone doit tomber dans SA zone et dans aucune autre : c'est là qu'un clic la sélectionne.
    const z = zones.zones[p.id];
    if (z) {
      const [x, y] = z.centre;
      if (!dedans(z.d, x + 0.5, y + 0.5)) err(`${ou}: le centre (${x},${y}) n'est pas dans la zone`);
      for (const [autre, za] of Object.entries(zones.zones)) {
        if (autre !== p.id && dedans(za.d, x + 0.5, y + 0.5)) err(`${ou}: le centre tombe aussi dans « ${autre} »`);
      }
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
console.log(`OK — ${ANIMAUX.length} animaux, ${nbPieces} pièces, ${Object.keys(RECETTES).length} recettes, zones et fiches cohérentes.`);
