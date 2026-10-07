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
for (const f of ["data/recettes.js", "data/pieces.js", "data/os.js", "data/classeur.js", "data/anatomie.js"]) vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx);
const { ANIMAUX, PIECES, OS, CLASSEUR, ANATOMIE } = ctx.window;
// muscles (en volume) de chaque pièce du bœuf
const musclesDe = (pieces) => ANATOMIE.boeuf.muscles.filter((m) => m.pieces.some((p) => pieces.includes(p))).map((m) => m.id).sort();

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
  // classeur de découpe : les dénominations du guide (étoiles) et les fiches magasin du paleron
  const classeur = await lire(`({ denoms: document.querySelectorAll('#panneau .classeur li').length,
    etoiles: document.querySelectorAll('#panneau .classeur .etoiles').length,
    fiches: document.querySelectorAll('#panneau details.fiche-magasin:not(.lexique)').length })`);
  const cPal = CLASSEUR.boeuf.paleron;
  if (classeur.denoms !== cPal.guide.length || classeur.etoiles !== cPal.guide.length || classeur.fiches !== cPal.magasin.length) {
    erreurs.push(`fiche paleron : classeur affiché ${JSON.stringify(classeur)} au lieu de ${cPal.guide.length} dénominations et ${cPal.magasin.length} fiches magasin`);
  }
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

  // 7 bis. Squelette du bœuf : chargé à la demande ; chaque os est visible, se clique, ouvre sa fiche
  // et « plonge » dessus (caméra centrée sur l'os, ses muscles affichés) ; vue éclatée.
  let clicsOs = 0;
  const attendreSquelette = async () => {
    for (let i = 0; i < 80; i++) { if (await lire("window.ATELIER3D.modeCourant().squelette")) return true; await attendre(100); }
    return false;
  };
  await aller("#boeuf/squelette");
  if (!(await attendreSquelette())) erreurs.push("squelette du bœuf : data/anatomie.js ne se charge pas");
  await attendre(400);
  const m0 = await lire("[window.ATELIER3D.modeCourant().squelette, window.ATELIER3D.osAffiches().length, window.ATELIER3D.modeCourant().muscles.length]");
  if (!m0[0] || m0[1] < 8) erreurs.push(`squelette du bœuf : mode ${m0[0]}, ${m0[1]} noms d'os affichés`);
  if (m0[2] !== 0) erreurs.push(`squelette sans os choisi : ${m0[2]} muscles affichés au lieu de 0`);
  // ce qui est réellement AFFICHÉ (pas seulement l'attribut hidden) : pas de filtres de cuisson en mode squelette
  const legendeVue = await lire("getComputedStyle(document.getElementById('legende')).display");
  if (legendeVue !== "none") erreurs.push(`mode squelette : la ligne des filtres de cuisson reste affichée (display ${legendeVue})`);
  for (const o of OS.boeuf) {
    await lire("location.hash = '#boeuf/squelette'");
    await attendre(120);
    const pt = await lire(`window.ATELIER3D.pointEcranOs(${JSON.stringify(o.id)})`);
    if (!pt) { erreurs.push(`os ${o.id} : aucun point visible`); continue; }
    await nav.cliquer(pt[0], pt[1]);
    clicsOs++;
    await attendre(750);
    const [h, titre, forts, mode, ori] = await lire(`[location.hash, (document.querySelector('#panneau h2')||{}).textContent,
      window.ATELIER3D.etatCourant().forts, window.ATELIER3D.modeCourant(), window.ATELIER3D.orientation()]`);
    if (h !== `#boeuf/squelette/${o.id}` || titre !== o.nom || mode.os !== o.id) erreurs.push(`os ${o.id} : clic → ${h} « ${titre} » (choisi : ${mode.os})`);
    if ([...forts].sort().join() !== [...o.pieces].sort().join()) erreurs.push(`os ${o.id} : pièces surlignées ${forts} au lieu de ${o.pieces}`);
    // plongée : les muscles de ses pièces sont affichés, les autres os estompés, la caméra s'est approchée
    if ([...mode.muscles].sort().join() !== musclesDe(o.pieces).join()) erreurs.push(`os ${o.id} : muscles affichés ${mode.muscles} au lieu de ${musclesDe(o.pieces)}`);
    if (mode.autresOsNets) erreurs.push(`os ${o.id} : les autres os restent nets pendant la plongée`);
    if (mode.osChoisisNets !== 1) erreurs.push(`os ${o.id} : ${mode.osChoisisNets} os allumés pendant la plongée au lieu d'un seul (côté gauche et droit allumés ensemble ?)`);
    if (!(ori.zoom > 1.2)) erreurs.push(`os ${o.id} : la vue ne plonge pas sur l'os (zoom ${ori.zoom.toFixed(2)})`);
    const carte = await lire("(() => { const c = document.getElementById('carte3d'); return c && !c.hidden ? (c.querySelector('b')||{}).textContent : null; })()");
    if (carte !== o.nom) erreurs.push(`os ${o.id} : carte de la plongée « ${carte} »`);
  }
  await allerOsCapture("#boeuf/squelette/palette", "9-boeuf-squelette-palette.png");
  // un muscle touché pendant la plongée ouvre la fiche de sa pièce
  const ptMuscle = await lire(`window.ATELIER3D.pointEcranMuscle("paleron")`);
  if (!ptMuscle) erreurs.push("plongée sur la palette : le muscle du paleron n'est pas touchable");
  else {
    await nav.cliquer(ptMuscle[0], ptMuscle[1]);
    await attendre(300);
    const hm = await lire("location.hash");
    if (hm !== "#boeuf/paleron") erreurs.push(`clic sur le muscle du paleron → ${hm}`);
  }
  // zoom sur l'os choisi : on s'approche jusque contre l'os (même un petit os), et l'os reste à sa place
  // à l'écran quand on zoome ou qu'on en fait le tour (la vue tourne autour de l'os, pas à côté)
  const ecart = (a, b) => Math.hypot(a.x - b.x, a.y - b.y) / Math.min(a.vue[2], a.vue[3]);
  for (const id of ["rotule", "sacrum"]) {
    await aller(`#boeuf/squelette/${id}`);
    await attendre(900);
    const e0 = await lire("window.ATELIER3D.ecranOsChoisi()");
    if (!e0) { erreurs.push(`zoom sur l'os ${id} : os choisi introuvable`); continue; }
    for (let i = 0; i < 40; i++) await nav.cdp("Input.dispatchMouseEvent", { type: "mouseWheel", x: e0.x, y: e0.y, deltaX: 0, deltaY: -240 });
    await attendre(200);
    const e1 = await lire("window.ATELIER3D.ecranOsChoisi()");
    if (e1.distance / e1.rayon > 1.25) erreurs.push(`zoom sur l'os ${id} : bloqué à ${(e1.distance / e1.rayon).toFixed(2)} fois son rayon (on doit pouvoir s'en approcher)`);
    if (ecart(e1, e0) > 0.06) erreurs.push(`zoom sur l'os ${id} : l'os part de ${(ecart(e1, e0) * 100).toFixed(0)} % en zoomant`);
    const [l, t, w, h] = e1.vue;
    for (let k = 0; k < 3; k++) await nav.glisser(l + w / 2 - 80, t + h * 0.25, l + w / 2 + 80, t + h * 0.25);
    await nav.glisser(l + w / 2, t + h * 0.25 + 60, l + w / 2, t + h * 0.25 - 60);
    const e2 = await lire("window.ATELIER3D.ecranOsChoisi()");
    if (ecart(e2, e0) > 0.06) erreurs.push(`tour de l'os ${id} : l'os part de ${(ecart(e2, e0) * 100).toFixed(0)} % quand on tourne autour`);
  }
  // geste pendant le plongeon (toucher un os puis tourner / « Arrière » tout de suite) : une fois posée,
  // la vue doit tourner autour de l'os choisi, et pas autour d'un point figé à mi-chemin
  for (const geste of ["tourner", "Arrière"]) {
    await aller("#boeuf/squelette");
    await attendre(700);
    await lire("window.scrollTo(0, 0)");
    const ptS = await lire(`window.ATELIER3D.pointEcranOs("sacrum")`);
    await nav.cliquer(ptS[0], ptS[1]);
    await attendre(120);
    const e = await lire("window.ATELIER3D.ecranOsChoisi()");
    const [l, t, w, h] = e.vue;
    if (geste === "tourner") await nav.glisser(l + w / 2 - 60, t + h * 0.2, l + w / 2 + 60, t + h * 0.2, 4);
    else await lire(`[...document.querySelectorAll('#outils3d button')].find((b) => b.textContent.trim() === 'Arrière').click()`);
    await attendre(1000);
    await nav.glisser(l + w / 2 - 80, t + h * 0.2, l + w / 2 + 80, t + h * 0.2);
    const f = await lire("window.ATELIER3D.ecranOsChoisi()");
    const loin = Math.hypot(f.x - (l + w / 2), f.y - (t + h * 0.4)) / Math.min(w, h);
    if (loin > 0.03) erreurs.push(`geste « ${geste} » pendant le plongeon sur le sacrum : la vue ne tourne plus autour de l'os (écart ${(loin * 100).toFixed(0)} %)`);
  }
  // navigation libre : zoom bien plus fort qu'avant, déplacement (clic droit), vue par-dessous
  await aller("#boeuf/squelette/femur");
  await attendre(900);
  const avantNav = await lire("window.ATELIER3D.orientation()");
  const r3 = await lire("(() => { const r = document.querySelector('#planche canvas').getBoundingClientRect(); return [r.left + r.width / 2, r.top + r.height / 2]; })()");
  for (let i = 0; i < 12; i++) await nav.cdp("Input.dispatchMouseEvent", { type: "mouseWheel", x: r3[0], y: r3[1], deltaX: 0, deltaY: -240 });
  await attendre(200);
  const zoomMax = await lire("window.ATELIER3D.orientation().zoom");
  if (!(zoomMax > 3.3 && zoomMax > avantNav.zoom)) erreurs.push(`squelette : la molette ne zoome pas au-delà de l'ancien maximum (${avantNav.zoom.toFixed(2)} → ${zoomMax.toFixed(2)})`);
  await nav.cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: r3[0], y: r3[1] });
  await nav.cdp("Input.dispatchMouseEvent", { type: "mousePressed", x: r3[0], y: r3[1], button: "right", buttons: 2, clickCount: 1 });
  for (let i = 1; i <= 8; i++) await nav.cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: r3[0] + 15 * i, y: r3[1], button: "right", buttons: 2 });
  await nav.cdp("Input.dispatchMouseEvent", { type: "mouseReleased", x: r3[0] + 120, y: r3[1], button: "right", clickCount: 1 });
  await attendre(150);
  const apresPan = await lire("[window.ATELIER3D.orientation(), location.hash]");
  const bouge = Math.hypot(...apresPan[0].centre.map((v, i) => v - avantNav.centre[i]));
  if (!(bouge > 0.005)) erreurs.push(`clic droit glissé : la vue ne se déplace pas (${bouge.toFixed(4)})`);
  if (apresPan[1] !== "#boeuf/squelette/femur") erreurs.push(`clic droit glissé : a changé la sélection (${apresPan[1]})`);
  // glisser vers le haut (à droite de la carte de la plongée) : la caméra passe dessous
  await nav.glisser(r3[0] + 260, r3[1] + 150, r3[0] + 260, r3[1] - 170);
  const elDessous = await lire("window.ATELIER3D.orientation().el");
  if (!(elDessous < -0.3)) erreurs.push(`squelette : on ne peut pas regarder par-dessous (élévation ${elDessous.toFixed(2)})`);
  // « Muscles » : toute la viande sur le squelette
  await aller("#boeuf/squelette");
  await attendre(300);
  await lire(`document.querySelector('#outils3d [data-muscles]').click()`);
  await attendre(400);
  const viande = await lire("[window.ATELIER3D.modeCourant().muscles.length, window.ATELIER3D.musclesAffiches().length]");
  if (viande[0] !== ANATOMIE.boeuf.muscles.length || viande[1] < 8) erreurs.push(`bouton Muscles : ${viande[0]} muscles affichés (${viande[1]} noms) sur ${ANATOMIE.boeuf.muscles.length}`);
  await lire("window.scrollTo(0,0)");
  await nav.capture(join(CAPTURES, "11-boeuf-muscles.png"));
  await lire(`document.querySelector('#outils3d [data-muscles]').click()`);
  await attendre(200);
  // plein écran : la 3D prend tout l'écran ; Échap pour sortir
  await lire(`document.querySelector('#outils3d [data-plein]').click()`);
  await attendre(300);
  const plein = await lire("(() => { const r = document.getElementById('planche').getBoundingClientRect(); return [document.body.classList.contains('plein-ecran-3d'), Math.round(r.width), Math.round(r.height), innerWidth, innerHeight]; })()");
  if (!plein[0] || plein[1] < plein[3] - 2 || plein[2] < plein[4] * 0.8) erreurs.push(`plein écran : ${JSON.stringify(plein)}`);
  await nav.cdp("Input.dispatchKeyEvent", { type: "keyDown", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await nav.cdp("Input.dispatchKeyEvent", { type: "keyUp", key: "Escape", code: "Escape", windowsVirtualKeyCode: 27 });
  await attendre(200);
  if (await lire("document.body.classList.contains('plein-ecran-3d')")) erreurs.push("plein écran : Échap ne le quitte pas");
  // vue éclatée
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
  await aller("#boeuf/squelette");
  await attendreSquelette();
  await attendre(400);
  await lire("window.scrollTo(0,0)");
  const ptOsMobile = await lire(`window.ATELIER3D.pointEcranOs("femur")`);
  if (!ptOsMobile) erreurs.push("téléphone : fémur introuvable à l'écran");
  else {
    await nav.cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: [{ x: ptOsMobile[0], y: ptOsMobile[1] }] });
    await nav.cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await attendre(900);
    const [hOs, defile] = await lire("[location.hash, Math.round(window.scrollY)]");
    if (hOs !== "#boeuf/squelette/femur") erreurs.push(`téléphone : toucher le fémur → ${hOs}`);
    if (defile > 40) erreurs.push(`téléphone : toucher un os fait descendre la page (${defile} px) au lieu de rester dans la 3D`);
    await lire(`document.querySelector('#outils3d [data-plein]').click()`);
    await attendre(500);
    const nomsMuscles = await lire("window.ATELIER3D.musclesAffiches()");
    if (nomsMuscles.length < 2) erreurs.push(`téléphone, plongée sur le fémur en plein écran : ${nomsMuscles.length} nom(s) de muscle visibles (${nomsMuscles})`);
    await nav.capture(join(CAPTURES, "12-mobile-plongee-femur.png"));
    // pincer à deux doigts (qui glissent un peu, comme de vrais doigts) : zoome sans quitter l'os
    const p0 = await lire("window.ATELIER3D.ecranOsChoisi()");
    const [pl, pt, pw, ph] = p0.vue;
    const doigts = (k) => [{ x: pl + pw / 2 - 20 - 3 * k, y: pt + ph * 0.3, id: 1 }, { x: pl + pw / 2 + 20 + 9 * k, y: pt + ph * 0.3, id: 2 }];
    await nav.cdp("Input.dispatchTouchEvent", { type: "touchStart", touchPoints: doigts(0) });
    for (let k = 1; k <= 12; k++) { await nav.cdp("Input.dispatchTouchEvent", { type: "touchMove", touchPoints: doigts(k) }); await attendre(16); }
    await nav.cdp("Input.dispatchTouchEvent", { type: "touchEnd", touchPoints: [] });
    await attendre(200);
    const p1 = await lire("window.ATELIER3D.ecranOsChoisi()");
    if (!(p1.zoom > p0.zoom * 1.5)) erreurs.push(`téléphone : pincer ne zoome pas sur le fémur (${p0.zoom.toFixed(1)} → ${p1.zoom.toFixed(1)})`);
    if (ecart(p1, p0) > 0.03) erreurs.push(`téléphone : pincer fait quitter le fémur (${(ecart(p1, p0) * 100).toFixed(0)} %)`);
  }

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
console.log(`OK — ${clics} pièces et ${OS.boeuf.length} os cliqués en 3D, chacun ouvre la bonne fiche ; plongée sur chaque os avec ses muscles, clic sur un muscle, zoom et tour autour de l'os choisi, pincement, déplacement, vue par-dessous, toute la viande, plein écran, classeur, survol, rotation, liste, filtre, comparatif, vue éclatée et téléphone vérifiés. Captures : outils/captures/`);
process.exit(0);
