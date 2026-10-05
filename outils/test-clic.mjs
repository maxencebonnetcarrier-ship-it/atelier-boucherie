// Test de bout en bout : ouvre l'appli dans un navigateur sans fenêtre (Edge ou Chrome),
// fait tourner chaque animal 3D vers chaque pièce et CLIQUE réellement dessus, puis vérifie
// que la bonne fiche s'ouvre. Teste aussi le survol, la rotation à la souris, le filtre par
// cuisson, le comparatif, la liste et l'affichage téléphone, et enregistre des captures.
// Usage : node outils/test-clic.mjs [url]   (code de sortie 0 = tout est bon)
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";
import { lancer, attendre } from "./navigateur.mjs";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
const APP = join(RACINE, "app");
const CAPTURES = join(RACINE, "outils", "captures");
const URL_APP = process.argv[2] || pathToFileURL(join(APP, "index.html")).href;

// Données de référence (lues comme le fait la page).
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["data/recettes.js", "data/pieces.js", "data/os.js"]) vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx);
const { ANIMAUX, PIECES, OS } = ctx.window;

const erreurs = [];
let clics = 0;
const nav = await lancer({ largeur: 1400, hauteur: 1000, port: 9337 });
const pret = "document.readyState === 'complete' && !!window.ATELIER3D";
const aller = (hash) => nav.aller(URL_APP + hash, pret);
const lire = (expr) => nav.evaluer(expr);

try {
  // 1. Pour chaque pièce : la caméra la montre, on clique dessus, la bonne fiche s'ouvre.
  for (const a of ANIMAUX) {
    await aller("#" + a.id);
    await attendre(300);
    // l'animal est bien dessiné (pas un cadre vide) : beaucoup de pixels rouges sur la toile
    const rouge = await lire(`(() => { const c = document.querySelector('#planche canvas'); const t = document.createElement('canvas');
      t.width = 200; t.height = 125; const x = t.getContext('2d'); x.drawImage(c, 0, 0, 200, 125);
      const d = x.getImageData(0, 0, 200, 125).data; let n = 0;
      for (let i = 0; i < d.length; i += 4) if (d[i] > d[i + 1] + 50 && d[i + 3] > 0) n++; return n / (200 * 125); })()`);
    if (!(rouge > 0.12)) erreurs.push(`${a.id} : l'animal 3D ne s'affiche pas (${(rouge * 100).toFixed(1)} % de pixels de viande)`);
    for (const p of PIECES[a.id]) {
      const pt = await lire(`window.ATELIER3D.pointEcran(${JSON.stringify(p.id)})`);
      if (!pt) { erreurs.push(`${a.id}/${p.id} : aucun point visible`); continue; }
      await attendre(30);
      await nav.cliquer(pt[0], pt[1]);
      clics++;
      const [hash, titre] = await lire("[location.hash, (document.querySelector('#panneau h2')||{}).textContent]");
      if (hash !== `#${a.id}/${p.id}` || titre !== p.nom) erreurs.push(`${a.id}/${p.id} : clic en (${pt.map(Math.round)}) → ${hash} « ${titre} »`);
    }
  }

  // 2. Survol à la souris : la bulle donne le nom de la pièce.
  await aller("#boeuf");
  await attendre(200);
  const ptPal = await lire(`window.ATELIER3D.pointEcran("paleron")`);
  await nav.cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: ptPal[0], y: ptPal[1] });
  await attendre(120);
  const bulle = await lire("[document.getElementById('bulle').hidden, document.getElementById('bulle').textContent]");
  if (bulle[0] || bulle[1] !== "Paleron") erreurs.push(`survol du paleron : bulle ${JSON.stringify(bulle)}`);

  // 2 bis. Noms écrits sur les pièces : affichés, sans chevauchement, et masquables par le bouton « Noms ».
  const noms = await lire("window.ATELIER3D.nomsAffiches()");
  if (noms.length < 10) erreurs.push(`bœuf vue de départ : seulement ${noms.length} noms écrits sur les pièces`);
  const chevauche = await lire(`(() => { const r = [...document.querySelectorAll('.etiquettes3d span')]
    .filter((s) => s.style.visibility === 'visible').map((s) => s.getBoundingClientRect());
    for (let i = 0; i < r.length; i++) for (let j = i + 1; j < r.length; j++)
      if (r[i].left < r[j].right - 1 && r[i].right > r[j].left + 1 && r[i].top < r[j].bottom - 1 && r[i].bottom > r[j].top + 1) return true;
    return false; })()`);
  if (chevauche) erreurs.push("des noms se chevauchent sur le bœuf");
  await lire(`document.querySelector('#outils3d [data-noms]').click()`);
  await attendre(150);
  const sansNoms = await lire("[window.ATELIER3D.nomsAffiches().length, document.querySelector('#outils3d [data-noms]').getAttribute('aria-pressed')]");
  if (sansNoms[0] !== 0 || sansNoms[1] !== "false") erreurs.push(`bouton Noms : ${JSON.stringify(sansNoms)}`);
  await lire(`document.querySelector('#outils3d [data-noms]').click()`);
  await attendre(150);

  // 3. Glisser à la souris fait tourner l'animal, sans sélectionner de pièce.
  const avant = await lire("window.ATELIER3D.orientation().az");
  await nav.glisser(ptPal[0], ptPal[1], ptPal[0] + 220, ptPal[1]);
  const apres = await lire("[window.ATELIER3D.orientation().az, location.hash]");
  if (Math.abs(apres[0] - avant) < 1) erreurs.push(`glisser ne fait pas tourner l'animal (az ${avant} → ${apres[0]})`);
  if (apres[1] !== "#boeuf") erreurs.push(`glisser a sélectionné une pièce (${apres[1]})`);

  // 4. Fiche complète : cuissons, transformations, recettes, équivalences.
  await aller("#boeuf/paleron");
  await attendre(700);
  const contenu = await lire(`({ cuissons: document.querySelectorAll('#panneau .cuissons .puce').length,
    transfo: document.querySelectorAll('#panneau .transfo li').length,
    recettes: document.querySelectorAll('#panneau details.recette').length,
    ouverte: !!document.querySelector('#panneau details.recette[open]'),
    equiv: document.querySelectorAll('#panneau .equivalences a').length,
    selection: window.ATELIER3D.etatCourant().selection })`);
  const nomSel = await lire(`(() => { const s = document.querySelector('.etiquettes3d span.actif'); return s && s.style.visibility === 'visible' ? s.dataset.piece : null; })()`);
  if (nomSel !== "paleron") erreurs.push(`le nom de la pièce choisie n'est pas affiché (${nomSel})`);
  const pal = PIECES.boeuf.find((p) => p.id === "paleron");
  if (contenu.cuissons !== pal.cuissons.length || contenu.transfo !== pal.transformations.length
    || contenu.recettes !== pal.recettes.length || !contenu.ouverte || contenu.equiv < 3 || contenu.selection !== "paleron") {
    erreurs.push("fiche paleron incomplète : " + JSON.stringify(contenu));
  }
  await lire("window.scrollTo(0,0)");
  await nav.capture(join(CAPTURES, "1-boeuf-paleron.png"));

  // 5. Choisir dans la liste fait tourner l'animal vers la pièce.
  await aller("#boeuf");
  await attendre(200);
  const az0 = await lire("window.ATELIER3D.orientation().az");
  await lire(`document.querySelector('#liste-pieces [data-piece="rond-de-gite"]').click()`);
  await attendre(900);
  const [az1, selListe] = await lire("[window.ATELIER3D.orientation().az, window.ATELIER3D.etatCourant().selection]");
  if (selListe !== "rond-de-gite" || Math.abs(az1 - az0) < 0.3) erreurs.push(`liste → rond de gîte : sélection ${selListe}, rotation ${az0.toFixed(2)} → ${az1.toFixed(2)}`);
  await nav.capture(join(CAPTURES, "2-boeuf-rond-de-gite.png"));

  // 6. Filtre « Braiser » sur le porc : pièces à braiser colorées, les autres atténuées.
  await aller("#porc");
  await attendre(200);
  await lire(`document.querySelector('#legende [data-filtre="braiser"]').click()`);
  await attendre(300);
  const coul = await lire("window.ATELIER3D.etatCourant().couleurs");
  const aBraiser = PIECES.porc.filter((p) => p.cuissons.includes("braiser")).map((p) => p.id);
  const faux = PIECES.porc.filter((p) => (coul[p.id] === "#e6ddd2") === aBraiser.includes(p.id)).map((p) => p.id);
  if (faux.length) erreurs.push(`filtre braiser porc : couleurs incohérentes pour ${faux.join(", ")}`);
  const nomsFiltre = await lire("window.ATELIER3D.nomsAffiches()");
  const intrus = nomsFiltre.filter((id) => !aBraiser.includes(id));
  if (intrus.length || !nomsFiltre.length) erreurs.push(`filtre braiser porc : noms écrits ${nomsFiltre} (intrus : ${intrus})`);
  await nav.capture(join(CAPTURES, "3-porc-filtre-braiser.png"));

  // 7. Comparatif : la case « Veau / épaule » ouvre le veau avec la région surlignée.
  await aller("#comparatif");
  await nav.capture(join(CAPTURES, "4-comparatif.png"));
  const [bx, by] = await lire(`(() => { const b = document.querySelector('[data-region="epaule"][data-animal="veau"]');
    b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect(); return [r.left + 20, r.top + 10]; })()`);
  await nav.cliquer(bx, by);
  await attendre(300);
  const [hashC, coulC] = await lire("[location.hash, window.ATELIER3D.etatCourant().couleurs]");
  const regionVeau = PIECES.veau.filter((p) => p.region === "epaule").map((p) => p.id);
  const surlignees = Object.entries(coulC).filter(([, c]) => c === "#d99a1e").map(([id]) => id).sort();
  if (hashC !== "#veau" || surlignees.join() !== [...regionVeau].sort().join()) {
    erreurs.push(`comparatif → ${hashC}, surlignées ${surlignees} au lieu de ${regionVeau}`);
  }
  await lire("window.scrollTo(0,0)");
  await nav.capture(join(CAPTURES, "5-veau-region-epaule.png"));

  // 7 bis. Squelette du bœuf : chaque os est visible, se clique et ouvre sa fiche ; vue éclatée.
  let clicsOs = 0;
  await aller("#boeuf/squelette");
  await attendre(400);
  const m0 = await lire("[window.ATELIER3D.modeCourant().squelette, window.ATELIER3D.osAffiches().length]");
  if (!m0[0] || m0[1] < 8) erreurs.push(`squelette du bœuf : mode ${m0[0]}, ${m0[1]} noms d'os affichés`);
  // ce qui est réellement AFFICHÉ (pas seulement l'attribut hidden) : pas de filtres de cuisson en mode squelette
  const legendeVue = await lire("getComputedStyle(document.getElementById('legende')).display");
  if (legendeVue !== "none") erreurs.push(`mode squelette : la ligne des filtres de cuisson reste affichée (display ${legendeVue})`);
  for (const o of OS.boeuf) {
    const pt = await lire(`window.ATELIER3D.pointEcranOs(${JSON.stringify(o.id)})`);
    if (!pt) { erreurs.push(`os ${o.id} : aucun point visible`); continue; }
    await nav.cliquer(pt[0], pt[1]);
    clicsOs++;
    const [h, titre, forts, choisi] = await lire("[location.hash, (document.querySelector('#panneau h2')||{}).textContent, window.ATELIER3D.etatCourant().forts, window.ATELIER3D.modeCourant().os]");
    if (h !== `#boeuf/squelette/${o.id}` || titre !== o.nom || choisi !== o.id) erreurs.push(`os ${o.id} : clic → ${h} « ${titre} » (choisi : ${choisi})`);
    if ([...forts].sort().join() !== [...o.pieces].sort().join()) erreurs.push(`os ${o.id} : pièces surlignées ${forts} au lieu de ${o.pieces}`);
  }
  await allerOsCapture("#boeuf/squelette/palette", "9-boeuf-squelette-palette.png");
  await lire(`document.querySelector('#outils3d [data-eclater]').click()`);
  await attendre(1300);
  const ecl = await lire("window.ATELIER3D.modeCourant()");
  if (!ecl.eclate || ecl.eclat !== 1) erreurs.push(`vue éclatée : ${JSON.stringify(ecl)}`);
  const ptEcl = await lire(`window.ATELIER3D.pointEcranOs("femur")`);
  if (ptEcl) {
    await nav.cliquer(ptEcl[0], ptEcl[1]);
    const hEcl = await lire("location.hash");
    if (hEcl !== "#boeuf/squelette/femur") erreurs.push(`clic sur le fémur en vue éclatée → ${hEcl}`);
  } else erreurs.push("vue éclatée : fémur introuvable à l'écran");
  await lire("window.scrollTo(0,0)");
  await nav.capture(join(CAPTURES, "10-boeuf-squelette-eclate.png"));
  await lire(`document.querySelector('#outils3d [data-eclater]').click()`);
  await attendre(1300);
  const ras = await lire("window.ATELIER3D.modeCourant()");
  if (ras.eclate || ras.eclat !== 0) erreurs.push(`Rassembler : ${JSON.stringify(ras)}`);
  // lien pièce → os, et pas de bouton Squelette pour un animal sans squelette
  await aller("#boeuf/paleron");
  await attendre(300);
  const lien = await lire(`!!document.querySelector('#panneau a[href="#boeuf/squelette/palette"]')`);
  if (!lien) erreurs.push("fiche du paleron : pas de lien vers la palette");
  await aller("#veau");
  await attendre(200);
  const cache = await lire(`getComputedStyle(document.querySelector('#outils3d [data-squelette]')).display`);
  if (cache !== "none") erreurs.push(`bouton Squelette affiché sur le veau (pas encore de squelette) : display ${cache}`);

  // 8. Agneau, et affichage téléphone.
  await aller("#agneau/gigot");
  await attendre(800);
  await lire("window.scrollTo(0,0)");
  await nav.capture(join(CAPTURES, "6-agneau-gigot.png"));
  await nav.taille(390, 844, true, 2);
  await aller("#porc/jambon");
  await attendre(800);
  await lire("window.scrollTo(0,0)");
  await nav.capture(join(CAPTURES, "7-mobile-porc.png"));
  const ptMobile = await lire(`window.ATELIER3D.pointEcran("echine")`);
  await nav.cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: ptMobile[0], y: ptMobile[1] }] });
  await nav.cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
  await attendre(400);
  const hashMobile = await lire("location.hash");
  if (hashMobile !== "#porc/echine") erreurs.push(`toucher du doigt sur l'échine (téléphone) → ${hashMobile}`);
  await lire("document.querySelector('#panneau').scrollIntoView()");
  await nav.capture(join(CAPTURES, "8-mobile-porc-fiche.png"));

  if (nav.journal.length) erreurs.push("erreurs JavaScript dans la page :\n   " + nav.journal.join("\n   "));
} catch (e) {
  erreurs.push("exception : " + e.message);
} finally {
  await nav.fermer();
}

async function allerOsCapture(hash, fichier) {
  await aller(hash);
  await attendre(900);
  await lire("window.scrollTo(0,0)");
  await nav.capture(join(CAPTURES, fichier));
}

if (erreurs.length) {
  console.error(`ÉCHEC — ${erreurs.length} problème(s) sur ${clics} clics :\n - ` + erreurs.join("\n - "));
  process.exit(1);
}
console.log(`OK — ${clics} pièces et ${OS.boeuf.length} os cliqués en 3D, chacun ouvre la bonne fiche ; survol, rotation, liste, filtre, comparatif, squelette, vue éclatée et téléphone vérifiés. Captures : outils/captures/`);
process.exit(0);
