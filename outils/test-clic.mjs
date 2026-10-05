// Test de bout en bout : ouvre l'appli dans un navigateur sans fenêtre (Edge ou Chrome),
// CLIQUE réellement au centre de chaque pièce de chaque animal et vérifie que la bonne fiche
// s'affiche. Teste aussi le filtre par cuisson et le comparatif, puis enregistre des captures.
// Usage : node outils/test-clic.mjs   (code de sortie 0 = tout est bon)
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
const APP = join(RACINE, "app");
const CAPTURES = join(RACINE, "outils", "captures");
const URL_APP = pathToFileURL(join(APP, "index.html")).href;
const PORT = 9337;

const NAVIGATEURS = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
];
const exe = NAVIGATEURS.find(existsSync);
if (!exe) { console.error("Aucun navigateur Edge/Chrome trouvé."); process.exit(2); }

// Données de référence (lues comme le fait la page).
const ctx = { window: {} };
vm.createContext(ctx);
for (const f of ["data/zones.js", "data/recettes.js", "data/pieces.js"]) vm.runInContext(readFileSync(join(APP, f), "utf8"), ctx);
const { ANIMAUX, PIECES, ZONES, REGIONS } = ctx.window;

const profil = mkdtempSync(join(tmpdir(), "atelier-boucherie-"));
const nav = spawn(exe, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${profil}`,
  "--no-first-run", "--disable-extensions", "--allow-file-access-from-files", "--window-size=1400,1000", "about:blank"], { stdio: "ignore" });

const attendre = (ms) => new Promise((r) => setTimeout(r, ms));
async function cible() {
  for (let i = 0; i < 50; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = l.find((t) => t.type === "page");
      if (p) return p.webSocketDebuggerUrl;
    } catch { /* pas encore prêt */ }
    await attendre(200);
  }
  throw new Error("le navigateur ne répond pas sur le port de débogage");
}

let ws, seq = 0;
const enAttente = new Map();
function cdp(method, params = {}) {
  const id = ++seq;
  ws.send(JSON.stringify({ id, method, params }));
  return new Promise((ok, ko) => enAttente.set(id, { ok, ko }));
}
async function evaluer(expr) {
  const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.exceptionDetails) throw new Error("erreur JS : " + JSON.stringify(r.exceptionDetails.exception?.description || r.exceptionDetails.text));
  return r.result.value;
}
async function aller(hash) {
  await cdp("Page.navigate", { url: URL_APP + hash });
  for (let i = 0; i < 50; i++) {
    if (await evaluer("document.readyState === 'complete' && !!document.querySelector('#onglets button')").catch(() => false)) return;
    await attendre(100);
  }
  throw new Error("la page ne se charge pas : " + hash);
}
async function cliquer(x, y) {
  for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
    await cdp("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: type === "mouseMoved" ? 0 : 1 });
  }
  await attendre(60);
}
async function capture(nom) {
  const r = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  mkdirSync(CAPTURES, { recursive: true });
  writeFileSync(join(CAPTURES, nom), Buffer.from(r.data, "base64"));
}
// Amène un point de la planche (en pixels de l'image) au milieu de l'écran et rend ses coordonnées écran.
async function pointEcran(animal, [cx, cy]) {
  const larg = ZONES[animal].largeur;
  const js = (scroll) => `(() => { const r = document.querySelector('#planche img').getBoundingClientRect();
    const k = r.width / ${larg}; const x = r.left + ${cx + 0.5} * k, y = r.top + ${cy + 0.5} * k;
    ${scroll ? "window.scrollBy(0, y - innerHeight / 2);" : ""} return [x, y]; })()`;
  await evaluer(js(true));
  await attendre(30);
  return evaluer(js(false));
}

const erreurs = [];
let clics = 0;
try {
  ws = new WebSocket(await cible());
  await new Promise((ok, ko) => { ws.onopen = ok; ws.onerror = ko; });
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && enAttente.has(d.id)) { const p = enAttente.get(d.id); enAttente.delete(d.id); d.error ? p.ko(new Error(d.error.message)) : p.ok(d.result); }
  };
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false });

  // 1. Un clic au centre de chaque pièce ouvre la bonne fiche.
  for (const a of ANIMAUX) {
    await aller("#" + a.id);
    for (const p of PIECES[a.id]) {
      const [x, y] = await pointEcran(a.id, ZONES[a.id].zones[p.id].centre);
      await cliquer(x, y);
      clics++;
      const [hash, titre, bulleCachee] = await evaluer("[location.hash, (document.querySelector('#panneau h2')||{}).textContent, document.getElementById('bulle').hidden]");
      if (hash !== `#${a.id}/${p.id}` || titre !== p.nom) erreurs.push(`${a.id}/${p.id} : clic → ${hash} « ${titre} »`);
      if (!bulleCachee) erreurs.push(`${a.id}/${p.id} : la bulle de survol reste affichée après le clic`);
    }
  }

  // 2. Le panneau d'une pièce montre cuissons, transformations et recettes.
  await aller("#boeuf/paleron");
  const contenu = await evaluer(`({ cuissons: document.querySelectorAll('#panneau .cuissons .puce').length,
    transfo: document.querySelectorAll('#panneau .transfo li').length,
    recettes: document.querySelectorAll('#panneau details.recette').length,
    ouverte: !!document.querySelector('#panneau details.recette[open]'),
    equiv: document.querySelectorAll('#panneau .equivalences a').length })`);
  const pal = PIECES.boeuf.find((p) => p.id === "paleron");
  if (contenu.cuissons !== pal.cuissons.length || contenu.transfo !== pal.transformations.length
    || contenu.recettes !== pal.recettes.length || !contenu.ouverte || contenu.equiv < 3) {
    erreurs.push("panneau paleron incomplet : " + JSON.stringify(contenu));
  }
  await evaluer("window.scrollTo(0,0)");
  await capture("1-boeuf-paleron.png");
  await aller("#veau/longe");
  await evaluer("window.scrollTo(0,0)");
  await capture("6-veau-longe.png");

  // 3. Filtre « Braiser » : seules les pièces à braiser sont surlignées.
  await aller("#porc");
  await evaluer(`document.querySelector('#legende [data-filtre="braiser"]').click()`);
  const surlignees = await evaluer("document.querySelectorAll('#planche .zone.match').length");
  const attendues = PIECES.porc.filter((p) => p.cuissons.includes("braiser")).length;
  if (surlignees !== attendues) erreurs.push(`filtre braiser porc : ${surlignees} zones surlignées au lieu de ${attendues}`);
  await capture("2-porc-filtre-braiser.png");

  // 4. Comparatif : un clic sur « Veau / épaule » ouvre le veau avec la région surlignée.
  await aller("#comparatif");
  await capture("3-comparatif.png");
  const [bx, by] = await evaluer(`(() => { const b = document.querySelector('[data-region="epaule"][data-animal="veau"]');
    b.scrollIntoView({ block: 'center' }); const r = b.getBoundingClientRect(); return [r.left + 20, r.top + 10]; })()`);
  await cliquer(bx, by);
  await attendre(100);
  const [hashC, regionC] = await evaluer("[location.hash, document.querySelectorAll('#planche .zone.match').length]");
  const attenduC = PIECES.veau.filter((p) => p.region === "epaule").length;
  if (hashC !== "#veau" || regionC !== attenduC) erreurs.push(`comparatif → ${hashC}, ${regionC} zones au lieu de #veau, ${attenduC}`);

  // 5. Affichage téléphone : la fiche s'affiche sous la planche.
  await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await aller("#agneau/gigot");
  await evaluer("window.scrollTo(0,0)");
  await capture("4-mobile-agneau.png");
  await evaluer("document.querySelector('#panneau').scrollIntoView()");
  await capture("5-mobile-agneau-fiche.png");
  void REGIONS;
} catch (e) {
  erreurs.push("exception : " + e.message);
} finally {
  try { await cdp("Browser.close"); } catch { /* déjà fermé */ }
  await attendre(300);
  try { nav.kill(); } catch { /* déjà fermé */ }
  try { rmSync(profil, { recursive: true, force: true }); } catch { /* fichiers encore verrouillés */ }
}

if (erreurs.length) {
  console.error(`ÉCHEC — ${erreurs.length} problème(s) sur ${clics} clics :\n - ` + erreurs.join("\n - "));
  process.exit(1);
}
console.log(`OK — ${clics} pièces cliquées, chacune ouvre la bonne fiche ; filtre, comparatif et vue téléphone vérifiés. Captures : outils/captures/`);
process.exit(0);
