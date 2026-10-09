// Test de bout en bout de la page atelier (atelier.html) : vrais clics dans la 3D sur chaque muscle de la
// cuisse et de l'épaule, séparation, étapes, zoom, repères de l'os du bassin et de la palette, vue d'une pièce
// (tranche grasse, paleron), téléphone, et liens depuis l'appli.
// Usage : node outils/test-atelier.mjs [url de base]   (code de sortie 0 = tout est bon)
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";
import { lancer, attendre } from "./navigateur.mjs";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
const APP = join(RACINE, "app");
const CAPTURES = join(RACINE, "outils", "captures");
const BASE = (process.argv[2] || pathToFileURL(APP).href).replace(/\/?$/, "/");
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["data/atelier.js", "data/atelier-cuisse.js", "data/atelier-epaule.js"]) vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx);
const { ATELIER, ATELIER_MAILLAGES } = ctx.window;
const R = ATELIER.regions.cuisse;

const erreurs = [];
const nav = await lancer({ largeur: 1500, hauteur: 950, port: 9361 });
const lire = (e) => nav.evaluer(e);
const ouvrir = async (requete) => {
  await nav.aller(BASE + "atelier.html" + requete, "document.readyState === 'complete' && !!window.ATELIER3D");
  await attendre(400);
};
// pixels de la scène qui ne sont pas le fond (la 3D est bien dessinée)
const pixels = () => lire(`(() => { const c = document.querySelector('#scene canvas'); const t = document.createElement('canvas');
  t.width = 160; t.height = 120; const x = t.getContext('2d'); x.drawImage(c, 0, 0, 160, 120);
  const d = x.getImageData(0, 0, 160, 120).data; let rouge = 0, plein = 0;
  for (let i = 0; i < d.length; i += 4) { if (d[i + 3] > 10) plein++; if (d[i + 3] > 10 && d[i] > d[i + 1] * 1.6 && d[i] > 80) rouge++; }
  return { rouge, plein }; })()`);
let clics = 0;
// attendre que la vue et les muscles aient fini de bouger (animations). Le navigateur de test dessine sans carte
// graphique : une image peut prendre plusieurs centaines de ms. Au-delà de 30 s, c'est une erreur (jamais ignorée :
// viser un muscle encore en mouvement fausse le clic).
async function immobile() {
  for (let i = 0; i < 600; i++) { if (await lire("window.ATELIER3D.immobile()")) return; await attendre(50); }
  erreurs.push("la scène bouge encore après 30 s");
}

const separerA = (v) => lire(`(() => { const s = document.getElementById('separer'); s.value = ${v}; s.dispatchEvent(new Event('input')); })()`);
const oeil = (id) => lire(`document.querySelector('[data-oeil="${id}"]').click()`);

// Un vrai clic sur chaque muscle. Un muscle enfermé dans les autres (l'araignée, le nerf du paleron) : on écarte
// les muscles ; s'il reste caché, on cache ses voisins de la même pièce avec leur bouton « œil », comme un utilisateur.
async function cliquerChaque(ids, ou) {
  for (const id of ids) {
    await immobile();
    const viser = () => lire(`window.ATELIER3D.pointEcran(${JSON.stringify(id)})`);
    let pt = await viser();
    let ecarte = false, caches = [];
    if (!pt) { await separerA(100); await immobile(); ecarte = true; pt = await viser(); }
    if (!pt) {
      caches = ids.filter((x) => x !== id && ATELIER.muscles[x].piece === ATELIER.muscles[id].piece);
      for (const x of caches) await oeil(x);
      await immobile();
      pt = await viser();
    }
    if (!pt) erreurs.push(`${ou} : muscle ${id} : aucun point visible à l'écran, même muscles écartés et voisins cachés`);
    else {
      const vise = await lire(`window.ATELIER3D.toucher(${pt[0]}, ${pt[1]})`);
      const t0 = Date.now();
      await nav.cliquer(pt[0], pt[1]);
      const tClic = Date.now() - t0;
      await attendre(350);
      clics++;
      const [sel, carte] = await lire("[window.ATELIER3D.selection(), window.ATELIER3D.carte()]");
      const nom = ATELIER.muscles[id].nom;
      if (!sel || sel.id !== id) {
        const apres = await lire(`window.ATELIER3D.toucher(${pt[0]}, ${pt[1]})`);
        erreurs.push(`${ou} : clic sur ${id} : choisi ${sel && sel.id} (visé avant : ${JSON.stringify(vise)}, après : ${JSON.stringify(apres)}, clic en ${tClic} ms)`);
      }
      if (!carte || !carte.includes(nom) || !carte.includes("Comment le séparer")) erreurs.push(`${ou} : clic sur ${id} : carte « ${(carte || "").slice(0, 60)} »`);
    }
    for (const x of caches) await oeil(x);
    if (ecarte) { await separerA(0); await immobile(); }
  }
}

// Une région entière : tout est dessiné, chaque muscle se clique, la séparation écarte tout, les étapes se
// déroulent, et les idées d'étal sont celles de ses pièces.
async function regionEntiere(rid, n) {
  const RR = ATELIER.regions[rid], muscles = Object.values(RR.pieces).flat();
  await ouvrir(`?region=${rid}`);
  const o = await lire("window.ATELIER3D.objets()");
  const nbAttendu = muscles.length + 1 + RR.os.length;
  if (!(await lire("window.ATELIER3D.pret")) || o.length !== nbAttendu) erreurs.push(`${rid} : ${o.length} éléments 3D au lieu de ${nbAttendu}`);
  const px = await pixels();
  if (px.plein < 3000) erreurs.push(`${rid} : la scène est presque vide (${px.plein} pixels dessinés)`);
  if (!(await lire("document.getElementById('chargement').hidden"))) erreurs.push(`${rid} : le message de chargement reste affiché`);
  // gras de couverture caché pour atteindre les muscles, puis un vrai clic sur chacun
  await lire(`document.querySelector('[data-voir="gras"]').click()`);
  await attendre(200);
  if ((await lire("window.ATELIER3D.objets()")).find((x) => x.id === RR.gras).visible) erreurs.push(`${rid} : bouton Gras : le gras reste visible`);
  await cliquerChaque(muscles, rid);
  await nav.capture(join(CAPTURES, `atelier-${n}-${rid}-muscle.png`));
  // séparation : chaque muscle s'écarte
  await separerA(100);
  await attendre(1500);
  const ecart = await lire("window.ATELIER3D.objets().filter((x) => x.type === 'muscle')");
  const fixes = ecart.filter((x) => x.decale < 0.03).map((x) => x.id);
  if (fixes.length) erreurs.push(`${rid} : séparer à 100 % : muscles restés en place ${fixes}`);
  await nav.capture(join(CAPTURES, `atelier-${n + 1}-${rid}-separee.png`));
  await separerA(0);
  // étapes : on les déroule toutes avec « Suivante »
  for (let i = 0; i < RR.etapes.length; i++) {
    await lire("document.getElementById('e-suiv').click()");
    await attendre(250);
    const [et, objs, carte] = await lire("[window.ATELIER3D.etape(), window.ATELIER3D.objets(), window.ATELIER3D.carte()]");
    if (et !== i) erreurs.push(`${rid} : étape ${i + 1} : étape courante ${et}`);
    for (const m of RR.etapes[i].muscles) if (!objs.find((x) => x.id === m)?.courant) erreurs.push(`${rid} : étape ${i + 1} : ${m} n'est pas mis en avant`);
    for (const m of RR.etapes.slice(0, i).flatMap((e) => e.muscles)) if (!objs.find((x) => x.id === m)?.leve) erreurs.push(`${rid} : étape ${i + 1} : ${m} (étape précédente) n'est pas posé à côté`);
    if (!carte || !carte.includes(RR.etapes[i].titre)) erreurs.push(`${rid} : étape ${i + 1} : la carte n'explique pas l'étape`);
  }
  await attendre(900);
  await nav.capture(join(CAPTURES, `atelier-${n + 2}-${rid}-derniere-etape.png`));
  await lire("document.getElementById('e-zero').click()");
  await attendre(300);
  if ((await lire("window.ATELIER3D.objets()")).some((x) => x.leve)) erreurs.push(`${rid} : « Tout remettre » : des muscles restent posés à côté`);
  // étal : les idées des pièces de la région, celles de toute la vitrine et la partie MOF
  const idees = await lire("document.querySelectorAll('#etal .idee').length");
  const ideesAttendues = ATELIER.presentation.general.length + Object.keys(RR.pieces).flatMap((p) => ATELIER.presentation.pieces[p] || []).length
    + ATELIER.presentation.mof.regles.length;
  if (idees !== ideesAttendues) erreurs.push(`${rid} : ${idees} idées d'étal au lieu de ${ideesAttendues}`);
  const nbVoir = await lire("document.querySelectorAll('#etal .voir-mof a[target=_blank]').length");
  if (nbVoir !== ATELIER.presentation.mof.voir.length) erreurs.push(`${rid} : ${nbVoir} liens photos / vidéos MOF au lieu de ${ATELIER.presentation.mof.voir.length}`);
  const fiches = await lire("[...document.querySelectorAll('#etal .comment-faire')].map((d) => { d.open = true; return d.querySelectorAll('ol li').length; })");
  if (fiches.length !== ATELIER.presentation.mof.commentFaire.length || fiches.some((k) => k < 3)) erreurs.push(`${rid} : fiches « comment faire » ${JSON.stringify(fiches)}`);
  // les onglets mènent aux vues de la région et à l'autre région
  const onglets = await lire("[...document.querySelectorAll('#vues a')].map((a) => a.getAttribute('href'))");
  for (const [, h] of RR.vues) if (!onglets.includes("atelier.html" + h)) erreurs.push(`${rid} : onglet ${h} absent`);
  for (const r of Object.keys(ATELIER.regions)) if (r !== rid && !onglets.includes(`atelier.html?region=${r}`)) erreurs.push(`${rid} : pas d'onglet vers ${r}`);
}

try {
  // 1. la cuisse entière
  await regionEntiere("cuisse", 1);
  // zoom à la molette et rotation au glisser
  const avant = await lire("window.ATELIER3D.orientation()");
  for (let i = 0; i < 10; i++) await nav.cdp("Input.dispatchMouseEvent", { type: "mouseWheel", x: 500, y: 500, deltaX: 0, deltaY: -240 });
  await attendre(200);
  const zoom = await lire("window.ATELIER3D.orientation()");
  if (!(zoom.dist < avant.dist * 0.2)) erreurs.push(`molette : on ne s'approche pas assez (${avant.dist.toFixed(2)} → ${zoom.dist.toFixed(2)} m)`);
  await nav.glisser(400, 500, 650, 520);
  const tour = await lire("window.ATELIER3D.orientation()");
  if (Math.abs(tour.az - zoom.az) < 0.5) erreurs.push("glisser : la vue ne tourne pas");
  // aucune référence à une ressource en ligne cassée : toutes les sources citées ont un titre
  const sources = await lire("document.querySelectorAll('#sources li').length");
  if (sources < 8) erreurs.push(`cuisse : seulement ${sources} sources citées`);

  // 2. l'os du bassin : repères nommés, parties de l'os, muscles autour
  await ouvrir("?os=coxal");
  const reps = await lire("window.ATELIER3D.reperes()");
  const attendus = ATELIER_MAILLAGES.cuisse.reperes.coxal.map((r) => r.id);
  if (reps.join() !== attendus.join()) erreurs.push(`os du bassin : repères ${reps} au lieu de ${attendus}`);
  if ((await lire("window.ATELIER3D.etiquettesVisibles().length")) < 6) erreurs.push("os du bassin : moins de 6 noms de repères visibles");
  const objsOs = await lire("window.ATELIER3D.objets()");
  if (objsOs.some((x) => x.type === "muscle" && x.visible)) erreurs.push("os du bassin : les muscles cachent l'os au départ");
  await lire(`document.querySelector('[data-repere="${attendus.indexOf("foramen-obturatum")}"]').click()`);
  await attendre(800);
  const [selR, carteR] = await lire("[window.ATELIER3D.selection(), window.ATELIER3D.carte()]");
  if (!selR || selR.repere !== "foramen-obturatum" || !carteR.includes("Foramen obturatum")) erreurs.push(`repère trou obturé : ${JSON.stringify(selR)} « ${(carteR || "").slice(0, 50)} »`);
  await lire(`document.querySelector('[data-voir="parties"]').click()`);
  await attendre(300);
  await nav.capture(join(CAPTURES, "atelier-4-os-bassin-parties.png"));
  await lire(`document.querySelector('[data-voir="autour"]').click()`);
  await attendre(1400);
  const autour = await lire("window.ATELIER3D.objets().filter((x) => x.type === 'muscle')");
  if (!autour.length || autour.some((x) => !x.visible || x.decale < 0.03)) erreurs.push("os du bassin : « Muscles autour » ne montre pas les muscles écartés");
  await nav.capture(join(CAPTURES, "atelier-5-os-bassin-muscles.png"));

  // 3. une pièce : la tranche grasse et ses trois muscles
  await ouvrir("?region=cuisse&piece=tranche-grasse");
  const tg = (await lire("window.ATELIER3D.objets()")).filter((x) => x.type === "muscle").map((x) => x.id).sort();
  if (tg.join() !== [...R.pieces["tranche-grasse"]].sort().join()) erreurs.push(`tranche grasse : muscles ${tg}`);
  if ((await lire("document.querySelectorAll('#etapes li').length")) !== R.etapesPieces["tranche-grasse"].length) erreurs.push("tranche grasse : étapes de séparation incomplètes");
  await lire(`(() => { const s = document.getElementById('separer'); s.value = 70; s.dispatchEvent(new Event('input')); })()`);
  await attendre(1300);
  await nav.capture(join(CAPTURES, "atelier-6-tranche-grasse.png"));

  // 3 bis. l'épaule entière, la palette et ses repères, le paleron ouvert en deux
  await regionEntiere("epaule", 8);
  await ouvrir("?os=palette");
  const repsP = await lire("window.ATELIER3D.reperes()");
  const attendusP = ATELIER_MAILLAGES.epaule.reperes.palette.map((r) => r.id);
  if (repsP.join() !== attendusP.join()) erreurs.push(`palette : repères ${repsP} au lieu de ${attendusP}`);
  if ((await lire("window.ATELIER3D.etiquettesVisibles().length")) < 6) erreurs.push("palette : moins de 6 noms de repères visibles");
  await lire(`document.querySelector('[data-repere="${attendusP.indexOf("fossa-infraspinata")}"]').click()`);
  await attendre(800);
  const [selP, carteP] = await lire("[window.ATELIER3D.selection(), window.ATELIER3D.carte()]");
  if (!selP || selP.repere !== "fossa-infraspinata" || !carteP.includes("Fossa infraspinata") || !carteP.includes("IMAIOS")) erreurs.push(`palette : repère fosse infra-épineuse ${JSON.stringify(selP)} « ${(carteP || "").slice(0, 60)} »`);
  await lire(`document.querySelector('[data-voir="autour"]').click()`);
  await attendre(1400);
  const autourP = await lire("window.ATELIER3D.objets().filter((x) => x.type === 'muscle')");
  if (autourP.length !== ATELIER.os.palette.muscles.length || autourP.some((x) => !x.visible || x.decale < 0.03)) erreurs.push("palette : « Muscles autour » ne montre pas les muscles écartés");
  await nav.capture(join(CAPTURES, "atelier-11-palette.png"));
  await ouvrir("?region=epaule&piece=paleron");
  const RE = ATELIER.regions.epaule;
  const pal = (await lire("window.ATELIER3D.objets()")).filter((x) => x.type === "muscle").map((x) => x.id).sort();
  if (pal.join() !== [...RE.pieces.paleron].sort().join()) erreurs.push(`paleron : muscles ${pal}`);
  if ((await lire("document.querySelectorAll('#etapes li').length")) !== RE.etapesPieces.paleron.length) erreurs.push("paleron : étapes de séparation incomplètes");
  // « Ouvrir le paleron en deux » puis « Lever le nerf » : la moitié du dessus est posée à côté, le nerf est mis en avant
  const iNerf = RE.etapesPieces.paleron.findIndex((e) => e.muscles.includes("pal-nerf"));
  await lire(`document.querySelector('[data-etape="${iNerf}"]').click()`);
  await attendre(1200);
  const objsN = await lire("window.ATELIER3D.objets()");
  if (!objsN.find((x) => x.id === "pal-exterieur")?.leve) erreurs.push("paleron : la moitié extérieure n'est pas levée avant le nerf");
  const nerf = objsN.find((x) => x.id === "pal-nerf");
  if (!nerf?.courant || !nerf.visible) erreurs.push("paleron : le nerf central n'est pas mis en avant");
  await nav.capture(join(CAPTURES, "atelier-12-paleron-nerf.png"));

  // 4. téléphone : la page tient en largeur, toucher un muscle le choisit
  await nav.taille(390, 844, true, 2);
  await ouvrir("?region=cuisse&piece=rumsteck");
  const deborde = await lire("document.documentElement.scrollWidth - window.innerWidth");
  if (deborde > 2) erreurs.push(`téléphone : la page déborde de ${deborde} px en largeur`);
  const ptT = await lire(`window.ATELIER3D.pointEcran("rs-coeur")`);
  if (!ptT) erreurs.push("téléphone : cœur de rumsteck introuvable à l'écran");
  else {
    await nav.cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: ptT[0], y: ptT[1] }] });
    await nav.cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await attendre(400);
    const s = await lire("window.ATELIER3D.selection()");
    if (!s || s.id !== "rs-coeur") erreurs.push(`téléphone : toucher le cœur de rumsteck → ${JSON.stringify(s)}`);
  }
  // pincer à deux doigts : zoom
  const z0 = await lire("window.ATELIER3D.orientation().dist");
  const doigts = (k) => [{ x: 160 - 4 * k, y: 300, id: 1 }, { x: 230 + 4 * k, y: 300, id: 2 }];
  await nav.cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: doigts(0) });
  for (let k = 1; k <= 12; k++) { await nav.cdp("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: doigts(k) }); await attendre(16); }
  await nav.cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await attendre(200);
  const z1 = await lire("window.ATELIER3D.orientation().dist");
  if (!(z1 < z0 * 0.7)) erreurs.push(`téléphone : pincer ne zoome pas (${z0.toFixed(2)} → ${z1.toFixed(2)})`);
  await nav.capture(join(CAPTURES, "atelier-7-mobile-rumsteck.png"));
  await nav.taille(1500, 950, false, 1);

  // 5. liens depuis l'appli et classeur marqué « libre-service »
  await nav.aller(BASE + "index.html#boeuf/squelette", "document.readyState === 'complete' && !!window.ATELIER3D");
  await attendre(600);
  const liens = await lire("[...document.querySelectorAll('#liste-pieces a')].map((a) => a.getAttribute('href'))");
  for (const h of ["atelier.html?region=cuisse", "atelier.html?os=coxal", "atelier.html?region=epaule", "atelier.html?os=palette"]) {
    if (!liens.includes(h)) erreurs.push(`appli : lien ${h} absent de la liste des os (${liens})`);
  }
  await lire("location.hash = '#boeuf/squelette/coxal'");
  await attendre(900);
  if (!(await lire("!!document.querySelector('#panneau a[href=\"atelier.html?os=coxal\"]')"))) erreurs.push("appli : la fiche de l'os du bassin n'ouvre pas l'atelier");
  await lire("location.hash = '#boeuf/tranche-grasse'");
  await attendre(700);
  const [lienP, titreC] = await lire(`[!!document.querySelector('#panneau a[href="atelier.html?region=cuisse&piece=tranche-grasse"]'),
    [...document.querySelectorAll('#panneau h3')].map((h) => h.textContent).join(' | ')]`);
  if (!lienP) erreurs.push("appli : la fiche tranche grasse n'ouvre pas ses muscles en 3D");
  if (!titreC.includes("En libre-service")) erreurs.push(`appli : le classeur n'est pas marqué libre-service (${titreC})`);
  await lire("location.hash = '#boeuf/paleron'");
  await attendre(700);
  if (!(await lire(`!!document.querySelector('#panneau a[href="atelier.html?region=epaule&piece=paleron"]')`))) erreurs.push("appli : la fiche paleron n'ouvre pas ses muscles en 3D");
  await lire("location.hash = '#boeuf/squelette/palette'");
  await attendre(900);
  if (!(await lire("!!document.querySelector('#panneau a[href=\"atelier.html?os=palette\"]')"))) erreurs.push("appli : la fiche de la palette n'ouvre pas l'atelier");
  await lire("location.hash = '#boeuf/tranche-grasse'");
  await attendre(700);
  // le lien s'ouvre vraiment
  await lire(`document.querySelector('#panneau a[href="atelier.html?region=cuisse&piece=tranche-grasse"]').click()`);
  await attendre(1500);
  const arrivee = await lire("[location.pathname.split('/').pop(), location.search, !!window.ATELIER3D && window.ATELIER3D.pret]");
  if (arrivee[0] !== "atelier.html" || arrivee[1] !== "?region=cuisse&piece=tranche-grasse" || !arrivee[2]) erreurs.push(`appli : le lien mène à ${arrivee}`);

  if (nav.journal.length) erreurs.push("erreurs JavaScript dans la page :\n   " + nav.journal.join("\n   "));
} catch (e) {
  erreurs.push("exception : " + e.message);
} finally {
  await nav.fermer();
}
if (erreurs.length) {
  console.error(`ÉCHEC — ${erreurs.length} problème(s) :\n - ` + erreurs.join("\n - "));
  process.exit(1);
}
console.log(`OK — atelier : ${clics} muscles de la cuisse et de l'épaule cliqués en 3D (carte « comment le séparer »), séparation, ${R.etapes.length} + ${ATELIER.regions.epaule.etapes.length} étapes, zoom, rotation, os du bassin et palette (repères, muscles autour), tranche grasse, paleron ouvert sur son nerf, téléphone (toucher, pincer) et liens depuis l'appli vérifiés. Captures : outils/captures/atelier-*.png`);
