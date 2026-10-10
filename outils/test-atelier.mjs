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
for (const f of ["data/atelier.js", "data/atelier-cuisse.js", "data/atelier-epaule.js", "data/atelier-aloyau.js", "data/atelier-avant.js", "data/atelier-flanc.js"]) vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx);
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
      // la carte de ce qu'on a choisi est SOUS la scène : elle ne cache rien de la 3D
    const sousScene = await lire("(() => { const c = document.getElementById('carte'), s = document.getElementById('scene'); return !c.hidden && !s.contains(c) && c.getBoundingClientRect().top >= s.getBoundingClientRect().bottom - 1; })()");
    if (!sousScene) erreurs.push(`${ou} : la carte de ${id} recouvre la 3D`);
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
  // le texte n'est pas alourdi : plus d'idées d'étal ni de références de sources dans les étapes et la carte
  const lourd = await lire("[document.querySelectorAll('#etal, #etapes .src, #carte .src a').length, document.querySelectorAll('#sources li').length]");
  if (lourd[0] !== 0 || lourd[1] < 3) erreurs.push(`${rid} : texte alourdi (${lourd[0]} éléments d'étal ou de sources en ligne) ou sources absentes (${lourd[1]})`);
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
  // la molette zoome aussi quand la souris est sur le nom d'un muscle
  await lire("document.getElementById('b-recadrer').click()");
  await immobile();
  const surNom = await lire("(() => { const e = [...document.querySelectorAll('.etiquettes-atelier .et')].find((el) => el.style.visibility === 'visible'); if (!e) return null; const r = e.getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()");
  if (!surNom) erreurs.push("molette : aucun nom visible pour l'essai");
  else {
    const d0 = await lire("window.ATELIER3D.orientation().dist");
    for (let i = 0; i < 5; i++) await nav.cdp("Input.dispatchMouseEvent", { type: "mouseWheel", x: surNom[0], y: surNom[1], deltaX: 0, deltaY: -240 });
    await attendre(200);
    const d1 = await lire("window.ATELIER3D.orientation().dist");
    if (!(d1 < d0 * 0.4)) erreurs.push(`molette sur un nom de muscle : pas de zoom (${d0.toFixed(2)} → ${d1.toFixed(2)} m)`);
  }
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
  if (!selP || selP.repere !== "fossa-infraspinata" || !carteP.includes("Fossa infraspinata") || !(await lire("document.getElementById('sources').textContent.includes('IMAIOS')"))) erreurs.push(`palette : repère fosse infra-épineuse ${JSON.stringify(selP)} « ${(carteP || "").slice(0, 60)} »`);
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

  // 3 ter. l'aloyau et le train de côtes : région entière, vertèbres des reins et leurs repères, filet démonté
  await regionEntiere("aloyau", 13);
  await ouvrir("?os=lombaires");
  const repsL = await lire("window.ATELIER3D.reperes()");
  const attendusL = ATELIER_MAILLAGES.aloyau.reperes.lombaires.map((r) => r.id);
  if (repsL.join() !== attendusL.join()) erreurs.push(`lombaires : repères ${repsL} au lieu de ${attendusL}`);
  await lire(`document.querySelector('[data-repere="${attendusL.indexOf("l-processus-transversus")}"]').click()`);
  await attendre(800);
  const [selL, carteL] = await lire("[window.ATELIER3D.selection(), window.ATELIER3D.carte()]");
  if (!selL || selL.repere !== "l-processus-transversus" || !carteL.includes("étagère") || !(await lire("document.getElementById('sources').textContent.includes('IMAIOS')"))) erreurs.push(`lombaires : repère apophyse transverse ${JSON.stringify(selL)} « ${(carteL || "").slice(0, 60)} »`);
  await nav.capture(join(CAPTURES, "atelier-16-lombaires.png"));
  await ouvrir("?region=aloyau&piece=filet");
  const RA = ATELIER.regions.aloyau;
  const fil = (await lire("window.ATELIER3D.objets()")).filter((x) => x.type === "muscle").map((x) => x.id).sort();
  if (fil.join() !== [...RA.pieces.filet].sort().join()) erreurs.push(`filet : muscles ${fil}`);
  await lire(`document.querySelector('[data-etape="${RA.etapesPieces.filet.length - 1}"]').click()`);
  await attendre(1200);
  const objsF = await lire("window.ATELIER3D.objets()");
  for (const m of ["fi-chainette", "fi-aile", "fi-queue", "fi-tete"]) if (!objsF.find((x) => x.id === m)?.leve) erreurs.push(`filet : ${m} n'est pas posé à côté avant de couper le cœur`);
  await nav.capture(join(CAPTURES, "atelier-17-filet.png"));

  // 3 quater. l'avant : région entière, sternum et ses repères
  await regionEntiere("avant", 18);
  await ouvrir("?os=sternum");
  const repsS = await lire("window.ATELIER3D.reperes()");
  const attendusS = ATELIER_MAILLAGES.avant.reperes.sternum.map((r) => r.id);
  if (repsS.join() !== attendusS.join()) erreurs.push(`sternum : repères ${repsS} au lieu de ${attendusS}`);
  await lire(`document.querySelector('[data-repere="${attendusS.indexOf("processus-xiphoideus")}"]').click()`);
  await attendre(800);
  const [selS, carteS] = await lire("[window.ATELIER3D.selection(), window.ATELIER3D.carte()]");
  if (!selS || selS.repere !== "processus-xiphoideus" || !carteS.includes("Processus xiphoideus")) erreurs.push(`sternum : repère appendice xiphoïde ${JSON.stringify(selS)} « ${(carteS || "").slice(0, 60)} »`);
  await nav.capture(join(CAPTURES, "atelier-21-sternum.png"));

  // 3 quinquies. le flanc : région entière, onglet ouvert sur son nerf central
  await regionEntiere("flanc", 22);
  await ouvrir("?region=flanc&piece=onglet");
  const RF = ATELIER.regions.flanc;
  await lire(`document.querySelector('[data-etape="1"]').click()`);
  await attendre(1200);
  const objsO = await lire("window.ATELIER3D.objets()");
  if (!objsO.find((x) => x.id === "on-avant")?.leve || !objsO.find((x) => x.id === "on-nerf")?.courant) erreurs.push("onglet : le nerf central n'est pas mis en avant une fois le premier muscle séparé");
  if ((await lire("document.querySelectorAll('#etapes li').length")) !== RF.etapesPieces.onglet.length) erreurs.push("onglet : étapes de séparation incomplètes");
  await nav.capture(join(CAPTURES, "atelier-25-onglet.png"));

  // 3 sexies. parcours guidé : une seule étape à l'écran, du début à la fin
  await ouvrir("?region=cuisse&pas=1");
  const RC = ATELIER.regions.cuisse;
  const panneauCache = await lire("getComputedStyle(document.getElementById('panneau')).display === 'none'");
  if (!panneauCache) erreurs.push("pas à pas : le panneau (listes, réglages) reste affiché");
  let pas0 = await lire("window.ATELIER3D.pas()");
  if (!pas0 || pas0.etape !== -1 || !pas0.texte.includes("Commencer")) erreurs.push(`pas à pas : écran de départ ${JSON.stringify(pas0)}`);
  for (let i = 0; i <= RC.etapes.length; i++) {
    await lire(`document.querySelector('#carte-pas [data-pas="suiv"]').click()`);
    await attendre(250);
    await immobile();
    const [p, objs, titres, noms] = await lire(`[window.ATELIER3D.pas(), window.ATELIER3D.objets(), document.querySelectorAll('#carte-pas h3').length, window.ATELIER3D.etiquettesVisibles()]`);
    if (titres !== 1) erreurs.push(`pas à pas, étape ${i + 1} : ${titres} titres d'étape à l'écran au lieu d'un seul`);
    if (i < RC.etapes.length) {
      const e = RC.etapes[i];
      if (p.etape !== i || !p.texte.includes(e.titre) || !p.texte.toLowerCase().includes(`étape ${i + 1} sur ${RC.etapes.length}`)) erreurs.push(`pas à pas, étape ${i + 1} : « ${p.texte.slice(0, 60)} »`);
      for (const m of e.muscles) if (!objs.find((x) => x.id === m)?.courant) erreurs.push(`pas à pas, étape ${i + 1} : ${m} n'est pas surligné`);
      for (const m of RC.etapes.slice(0, i).flatMap((x) => x.muscles)) if (!objs.find((x) => x.id === m)?.leve) erreurs.push(`pas à pas, étape ${i + 1} : ${m} n'est pas posé à côté`);
      const typeDe = (id) => objs.find((x) => x.id === id)?.type;
      const enTrop = noms.filter((id) => typeDe(id) !== "os" && !e.muscles.includes(id));
      if (enTrop.length) erreurs.push(`pas à pas, étape ${i + 1} : noms affichés en trop ${enTrop}`);
      if (i === 2) await nav.capture(join(CAPTURES, "atelier-31-pas-a-pas-etape.png"));
    } else if (p.etape !== RC.etapes.length || !p.texte.includes("C’est fini") || objs.some((x) => x.type === "muscle" && !x.leve)) {
      erreurs.push(`pas à pas : écran de fin ${JSON.stringify(p).slice(0, 120)}`);
    }
  }
  await nav.capture(join(CAPTURES, "atelier-32-pas-a-pas-fin.png"));
  await lire(`document.querySelector('#carte-pas [data-pas="prec"]').click()`);
  await attendre(200);
  if ((await lire("window.ATELIER3D.pas().etape")) !== RC.etapes.length - 1) erreurs.push("pas à pas : « Précédente » ne revient pas à la dernière étape");

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
  await ouvrir("?region=epaule");
  await lire(`document.querySelector('#muscles [data-objet="jumeau-a-bifteck"]').scrollIntoView({ block: 'center' })`);
  await attendre(300);
  const ptL = await lire(`(() => { const r = document.querySelector('#muscles [data-objet="jumeau-a-bifteck"] span:nth-of-type(2)').getBoundingClientRect(); return [r.left + 10, r.top + r.height / 2]; })()`);
  await nav.cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: ptL[0], y: ptL[1] }] });
  await nav.cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await attendre(1500);
  const [selJ, hautJ, basJ] = await lire("(() => { const r = document.getElementById('scene').getBoundingClientRect(); return [window.ATELIER3D.selection(), Math.round(r.top), Math.round(r.bottom - innerHeight)]; })()");
  if (!selJ || selJ.id !== "jumeau-a-bifteck") erreurs.push(`téléphone : toucher le jumeau dans la liste → ${JSON.stringify(selJ)}`);
  if (hautJ < 0 || basJ > 0) erreurs.push(`téléphone : après le jumeau choisi dans la liste, la 3D n'est pas à l'écran (haut ${hautJ} px, dépasse en bas de ${basJ} px)`);
  // et il est vraiment visible : le gras de couverture qui le recouvrait est retiré
  const grasJ = await lire("window.ATELIER3D.objets().find((x) => x.type === 'gras').visible");
  if (grasJ) erreurs.push("téléphone : le jumeau choisi dans la liste reste caché sous le gras de couverture");
  await nav.capture(join(CAPTURES, "atelier-8b-mobile-liste-jumeau.png"));
  // téléphone, parcours guidé du paleron : la 3D et l'étape tiennent dans l'écran ; toucher « à lever » explique
  await ouvrir("?region=epaule&piece=paleron&pas=1");
  await lire(`document.querySelector('#carte-pas [data-pas="suiv"]').click()`);
  await attendre(900);
  const ecranPas = await lire(`(() => { const s = document.getElementById('scene').getBoundingClientRect(), c = document.getElementById('carte-pas').getBoundingClientRect();
    return { haut: Math.round(s.top), bas: Math.round(c.bottom - innerHeight), largeur: document.documentElement.scrollWidth - innerWidth }; })()`);
  if (ecranPas.haut < 0 || ecranPas.bas > 0 || ecranPas.largeur > 2) erreurs.push(`téléphone, pas à pas : la 3D et l'étape ne tiennent pas dans l'écran ${JSON.stringify(ecranPas)}`);
  const premier = ATELIER.regions.epaule.etapesPieces.paleron[0].muscles[0];
  await lire(`document.querySelector('#carte-pas [data-m="${premier}"]').click()`);
  await attendre(300);
  const [txtPas, carteVisible] = await lire("[window.ATELIER3D.pas().texte, window.ATELIER3D.carte()]");
  if (!txtPas.includes(ATELIER.muscles[premier].separer.slice(0, 30)) || carteVisible) erreurs.push(`téléphone, pas à pas : toucher « ${premier} » n'explique pas dans la carte de l'étape`);
  await nav.capture(join(CAPTURES, "atelier-33-mobile-pas-a-pas-paleron.png"));
  await nav.taille(1500, 950, false, 1);

  // 5. liens depuis l'appli et classeur marqué « libre-service »
  await nav.aller(BASE + "index.html#boeuf/squelette", "document.readyState === 'complete' && !!window.ATELIER3D");
  await attendre(600);
  const liens = await lire("[...document.querySelectorAll('#liste-pieces a')].map((a) => a.getAttribute('href'))");
  for (const h of ["atelier.html?region=cuisse", "atelier.html?os=coxal", "atelier.html?region=epaule", "atelier.html?os=palette", "atelier.html?region=aloyau", "atelier.html?region=avant", "atelier.html?region=flanc",
    ...Object.keys(ATELIER.regions).map((r) => `atelier.html?region=${r}&pas=1`)]) {
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
  if (!(await lire(`!!document.querySelector('#carte3d a[href="atelier.html?region=cuisse&piece=tranche-grasse&pas=1"]')`))) erreurs.push("appli : la carte de la tranche grasse n'ouvre pas le pas à pas");
  if (!titreC.includes("En libre-service")) erreurs.push(`appli : le classeur n'est pas marqué libre-service (${titreC})`);
  await lire("location.hash = '#boeuf/paleron'");
  await attendre(700);
  if (!(await lire(`!!document.querySelector('#panneau a[href="atelier.html?region=epaule&piece=paleron"]')`))) erreurs.push("appli : la fiche paleron n'ouvre pas ses muscles en 3D");
  await lire("location.hash = '#boeuf/filet'");
  await attendre(700);
  if (!(await lire(`!!document.querySelector('#panneau a[href="atelier.html?region=aloyau&piece=filet"]')`))) erreurs.push("appli : la fiche filet n'ouvre pas ses muscles en 3D");
  await lire("location.hash = '#boeuf/squelette/palette'");
  await attendre(900);
  if (!(await lire("!!document.querySelector('#panneau a[href=\"atelier.html?os=palette\"]')"))) erreurs.push("appli : la fiche de la palette n'ouvre pas l'atelier");
  await lire("location.hash = '#boeuf/tranche-grasse'");
  await attendre(700);
  // onglet « Mise en avant » : les idées de vitrine, la partie MOF (photos, vidéos, comment faire)
  await lire("location.hash = '#etal'");
  await attendre(600);
  const etal = await lire(`({ idees: document.querySelectorAll('#vue-etal .idee').length, voir: document.querySelectorAll('#vue-etal .voir-mof a[target=_blank]').length,
    fiches: [...document.querySelectorAll('#vue-etal .comment-faire')].length, planche: !document.getElementById('vue-planche').hidden })`);
  const P = ATELIER.presentation;
  const ideesAttendues = P.general.length + P.mof.regles.length + Object.values(P.pieces).flat().length;
  if (etal.idees !== ideesAttendues || etal.voir !== P.mof.voir.length || etal.fiches !== P.mof.commentFaire.length + Object.keys(P.pieces).length || etal.planche) {
    erreurs.push(`onglet Mise en avant : ${JSON.stringify(etal)} (attendu ${ideesAttendues} idées, ${P.mof.voir.length} liens)`);
  }
  await nav.capture(join(CAPTURES, "atelier-30-onglet-mise-en-avant.png"));
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
console.log(`OK — atelier : ${clics} muscles des 5 régions (cuisse, épaule, aloyau, avant, flanc) cliqués en 3D (carte « comment le séparer »), séparation, ${Object.values(ATELIER.regions).map((r) => r.etapes.length).join(" + ")} étapes, zoom, rotation, os du bassin, palette, vertèbres des reins et sternum (repères, muscles autour), tranche grasse, paleron ouvert sur son nerf, filet démonté, onglet ouvert sur son nerf, téléphone (toucher, pincer) et liens depuis l'appli vérifiés. Captures : outils/captures/atelier-*.png`);
