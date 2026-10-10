// Vérifie la cohérence du contenu et des modèles 3D cliquables.
// Usage : node outils/verifier.mjs   (code de sortie 0 = tout est bon)
import { readFileSync, existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import vm from "node:vm";

const APP = process.env.APP_DIR || join(dirname(dirname(fileURLToPath(import.meta.url))), "app");
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["data/modeles3d.js", "data/recettes.js", "data/pieces.js", "data/os.js", "data/classeur.js", "data/anatomie.js",
  "data/atelier.js", "data/atelier-cuisse.js", "data/atelier-epaule.js", "data/atelier-aloyau.js",
  "data/atelier-avant.js", "data/atelier-flanc.js"]) {
  vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx, { filename: f });
}
const { ANIMAUX, PIECES, CUISSONS, REGIONS, RECETTES, MODELES3D, OS, CLASSEUR, ANATOMIE, ATELIER, ATELIER_MAILLAGES } = ctx.window;

const erreurs = [];
const err = (m) => erreurs.push(m);

// Tous les scripts appelés par la page doivent exister (l'appli marche sans réseau).
const page = readFileSync(join(APP, "index.html"), "utf8");
for (const [, src] of page.matchAll(/<script src="([^"]+)"/g)) if (!existsSync(join(APP, src))) err(`index.html : script manquant ${src}`);
for (const [, href] of page.matchAll(/<link[^>]+href="([^"]+)"/g)) if (!/^https?:/.test(href) && !existsSync(join(APP, href))) err(`index.html : fichier manquant ${href}`);
const pageAtelier = readFileSync(join(APP, "atelier.html"), "utf8");
for (const [, src] of pageAtelier.matchAll(/<script src="([^"]+)"/g)) if (!existsSync(join(APP, src))) err(`atelier.html : script manquant ${src}`);
for (const [, href] of pageAtelier.matchAll(/<link[^>]+href="([^"]+)"/g)) if (!/^https?:/.test(href) && !existsSync(join(APP, href))) err(`atelier.html : fichier manquant ${href}`);

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

// --- page atelier : chaque muscle, os, repère et source cités existent, dans les deux sens (toutes les régions)
let nbMusclesAtelier = 0, nbReperes = 0;
const regionsAtelier = ATELIER ? Object.keys(ATELIER.regions) : [];
if (!ATELIER || !ATELIER_MAILLAGES) err("atelier : data/atelier.js ou les formes 3D (data/atelier-<région>.js) absents");
else {
  // la page charge data/atelier-<région>.js à la demande : chaque région doit avoir son fichier
  for (const r of regionsAtelier) if (!ATELIER_MAILLAGES[r]) err(`atelier : formes 3D de la région ${r} absentes (data/atelier-${r}.js)`);
  for (const r of Object.keys(ATELIER_MAILLAGES)) if (!ATELIER.regions[r]) err(`atelier : formes 3D ${r} sans région dans data/atelier.js`);
  const mesh = new Map(), osMesh = new Map(), reperesMesh = {};
  for (const r of regionsAtelier) {
    const M = ATELIER_MAILLAGES[r];
    if (!M) continue;
    for (const m of M.muscles) { if (mesh.has(m.id)) err(`atelier : muscle ${m.id} dans deux régions`); mesh.set(m.id, { ...m, region: r }); }
    for (const o of M.os) osMesh.set(o.id, { ...o, region: r });
    for (const [osId, l] of Object.entries(M.reperes)) reperesMesh[osId] = l;
  }
  const piecesBoeuf = new Set(PIECES.boeuf.map((p) => p.id));
  const src = (liste, ou) => { if (!liste?.length) err(`${ou} : aucune source`); for (const s of liste || []) if (!ATELIER.sources[s]) err(`${ou} : source inconnue ${s}`); };
  for (const [id, m] of Object.entries(ATELIER.muscles)) {
    nbMusclesAtelier++;
    if (!mesh.has(id)) err(`atelier : muscle ${id} sans forme 3D`);
    if (m.piece && !piecesBoeuf.has(m.piece)) err(`atelier : muscle ${id} -> pièce inconnue ${m.piece}`);
    if (!m.nom || !m.info || !m.separer) err(`atelier : muscle ${id} sans nom, description ou « comment le séparer »`);
    if (!/^#[0-9a-f]{6}$/i.test(m.teinte || "")) err(`atelier : muscle ${id} teinte invalide`);
    if (m.anat && !ATELIER.sources[m.anatSource]) err(`atelier : muscle ${id} nom anatomique sans source`);
    src(m.sources, `atelier : muscle ${id}`);
    if (mesh.has(id) && m.piece && mesh.get(id).piece !== m.piece) err(`atelier : muscle ${id} rattaché à ${mesh.get(id).piece} dans la 3D, à ${m.piece} dans le texte`);
  }
  for (const id of mesh.keys()) if (!ATELIER.muscles[id]) err(`atelier : forme 3D ${id} sans texte`);
  for (const [r, R] of Object.entries(ATELIER.regions)) {
    if (!R.nom || !R.court || !R.gras || !R.vues?.length) err(`atelier : région ${r} incomplète (nom, nom court, gras, vues)`);
    if (mesh.get(R.gras)?.region !== r) err(`atelier : région ${r} -> gras ${R.gras} absent de ses formes 3D`);
    for (const [p, ids] of Object.entries(R.pieces)) {
      if (!piecesBoeuf.has(p)) err(`atelier : pièce inconnue ${p}`);
      for (const id of ids) {
        if (ATELIER.muscles[id]?.piece !== p) err(`atelier : ${id} listé sous ${p}`);
        if (mesh.has(id) && mesh.get(id).region !== r) err(`atelier : ${id} listé dans la région ${r}, forme 3D dans ${mesh.get(id).region}`);
      }
    }
    for (const o of R.os) if (osMesh.get(o)?.region !== r) err(`atelier : os ${o} de la région ${r} sans forme 3D détaillée`);
    for (const o of R.fendus || []) if (!R.os.includes(o)) err(`atelier : os fendu ${o} hors de la région ${r}`);
    // onglets de la région : chaque adresse mène à une vue qui existe
    for (const [, h] of R.vues) {
      const q = new URLSearchParams(h.replace(/^\?/, ""));
      if (q.get("region") && !ATELIER.regions[q.get("region")]) err(`atelier : vue ${h} -> région inconnue`);
      if (q.get("piece") && !ATELIER.regions[q.get("region")]?.pieces[q.get("piece")]) err(`atelier : vue ${h} -> pièce hors de la région`);
      if (q.get("os") && !ATELIER.os[q.get("os")]) err(`atelier : vue ${h} -> os sans page`);
      if (!q.get("region") && !q.get("os")) err(`atelier : vue ${h} sans région ni os`);
    }
    // étapes : muscles de la région, sourcés ; toute la région est levée dans l'ordre de découpe
    const etapes = [...R.etapes, ...Object.values(R.etapesPieces).flat()];
    for (const e of etapes) {
      if (!e.titre || !e.texte) err(`atelier : étape incomplète ${e.titre}`);
      for (const m of e.muscles) if (mesh.get(m)?.region !== r) err(`atelier : étape « ${e.titre} » -> muscle ${m} hors de la région ${r}`);
      src(e.sources, `atelier : étape « ${e.titre} »`);
    }
    for (const p of Object.keys(R.etapesPieces)) if (!R.pieces[p]) err(`atelier : étapes pour une pièce hors de la région ${r} : ${p}`);
    const leves = new Set(R.etapes.flatMap((e) => e.muscles));
    for (const id of [R.gras, ...Object.values(R.pieces).flat()]) if (!leves.has(id)) err(`atelier : ${id} n'est levé à aucune étape (${r})`);
  }
  for (const [id, o] of Object.entries(ATELIER.os)) {
    if (!osMesh.has(id)) err(`atelier : os ${id} sans forme 3D détaillée`);
    // un os pris en partie dans une région (vertèbres du garrot, panneau de côtes) renvoie à la fiche de l'appli
    if (!OS.boeuf.some((b) => b.id === (o.appli || id))) err(`atelier : os ${id} inconnu de l'appli`);
    for (const m of o.muscles) {
      if (!ATELIER.muscles[m]) err(`atelier : os ${id} -> muscle inconnu ${m}`);
      else if (osMesh.has(id) && mesh.get(m)?.region !== osMesh.get(id).region) err(`atelier : os ${id} -> muscle ${m} d'une autre région`);
    }
    if (o.sourceReperes && !ATELIER.sources[o.sourceReperes]) err(`atelier : os ${id} -> source des repères inconnue`);
  }
  // repères : un texte pour chaque point, chaque point près de son os (moins de 4 cm de sa boîte)
  for (const [osId, liste] of Object.entries(reperesMesh)) {
    const e = osMesh.get(osId);
    for (const r of liste) {
      nbReperes++;
      if (!ATELIER.reperes[r.id]) err(`atelier : repère ${r.id} sans texte`);
      if (!e) { err(`atelier : repère ${r.id} pour un os sans forme 3D ${osId}`); continue; }
      const [lo, hi] = e.boite;
      if (r.point.some((v, i) => v < lo[i] - 0.04 || v > hi[i] + 0.04)) err(`atelier : repère ${r.id} loin de l'os ${osId}`);
    }
  }
  for (const id of Object.keys(ATELIER.reperes)) if (!Object.values(reperesMesh).some((l) => l.some((r) => r.id === id))) err(`atelier : texte du repère ${id} sans point 3D`);
  for (const i of ATELIER.presentation.general) src(i.sources, `atelier : idée « ${i.titre} »`);
  for (const [p, l] of Object.entries(ATELIER.presentation.pieces)) {
    if (!piecesBoeuf.has(p)) err(`atelier : idées d'étal pour une pièce inconnue ${p}`);
    if (!regionsAtelier.some((r) => ATELIER.regions[r].pieces[p])) err(`atelier : idées d'étal pour ${p}, qui n'est dans aucune région`);
    for (const i of l) src(i.sources, `atelier : idée « ${i.titre} »`);
  }
  for (const [k, s] of Object.entries(ATELIER.sources)) if (!s.titre) err(`atelier : source ${k} sans titre`);
  // décor façon MOF : règles sourcées, liens photos / vidéos, fiches « comment faire »
  const mof = ATELIER.presentation.mof;
  if (!mof?.regles?.length || !mof.voir?.length || !mof.commentFaire?.length) err("atelier : partie MOF incomplète (règles, photos et vidéos, comment faire)");
  else {
    for (const i of mof.regles) src(i.sources, `atelier : MOF « ${i.titre} »`);
    for (const v of mof.voir) if (!/^https:\/\//.test(ATELIER.sources[v.source]?.url || "")) err(`atelier : MOF « ${v.titre} » sans lien vers la photo ou la vidéo`);
    for (const c of mof.commentFaire) {
      src(c.sources, `atelier : comment faire « ${c.titre} »`);
      if ((c.etapes || []).length < 3) err(`atelier : comment faire « ${c.titre} » : moins de 3 étapes`);
    }
  }
}

const nbPieces = ANIMAUX.reduce((n, a) => n + (PIECES[a.id]?.length || 0), 0);
if (erreurs.length) {
  console.error(`ÉCHEC — ${erreurs.length} problème(s) :\n - ` + erreurs.join("\n - "));
  process.exit(1);
}
console.log(`OK — ${ANIMAUX.length} animaux, ${nbPieces} pièces, ${Object.keys(RECETTES).length} recettes, ${nbOs} os, ${nbMuscles} muscles en volume, ${nbDenominations} dénominations du classeur, atelier : ${nbMusclesAtelier} muscles (${regionsAtelier.join(", ")}) et ${nbReperes} repères d'os, modèles 3D et fiches cohérents.`);
