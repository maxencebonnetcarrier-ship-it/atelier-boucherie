// Pilotage d'un navigateur sans fenêtre (Edge ou Chrome) par le protocole DevTools.
// Utilisé par les tests (test-clic.mjs) et les aperçus (apercu.mjs). WebGL est rendu
// en logiciel (SwiftShader) pour que la 3D fonctionne même sans carte graphique.
import { spawn } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";

const NAVIGATEURS = [
  "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
  "C:/Program Files/Google/Chrome/Application/chrome.exe",
];

export const attendre = (ms) => new Promise((r) => setTimeout(r, ms));

export async function lancer({ largeur = 1400, hauteur = 1000, port = 9337 } = {}) {
  const exe = NAVIGATEURS.find(existsSync);
  if (!exe) throw new Error("Aucun navigateur Edge/Chrome trouvé.");
  const profil = mkdtempSync(join(tmpdir(), "atelier-boucherie-"));
  const proc = spawn(exe, ["--headless=new", `--remote-debugging-port=${port}`, `--user-data-dir=${profil}`,
    "--no-first-run", "--disable-extensions", "--allow-file-access-from-files",
    "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--ignore-gpu-blocklist",
    `--window-size=${largeur},${hauteur}`, "about:blank"], { stdio: "ignore" });

  let url = null;
  for (let i = 0; i < 50 && !url; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      url = (l.find((t) => t.type === "page") || {}).webSocketDebuggerUrl || null;
    } catch { /* pas encore prêt */ }
    if (!url) await attendre(200);
  }
  if (!url) { proc.kill(); throw new Error("le navigateur ne répond pas sur le port de débogage"); }

  const ws = new WebSocket(url);
  await new Promise((ok, ko) => { ws.onopen = ok; ws.onerror = ko; });
  let seq = 0;
  const enAttente = new Map();
  const journal = [];
  ws.onmessage = (m) => {
    const d = JSON.parse(m.data);
    if (d.id && enAttente.has(d.id)) {
      const p = enAttente.get(d.id); enAttente.delete(d.id);
      d.error ? p.ko(new Error(d.error.message)) : p.ok(d.result);
    } else if (d.method === "Runtime.exceptionThrown") {
      journal.push("exception : " + (d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text));
    } else if (d.method === "Runtime.consoleAPICalled" && d.params.type === "error") {
      journal.push("console.error : " + d.params.args.map((a) => a.value ?? a.description).join(" "));
    }
  };
  const cdp = (method, params = {}) => {
    const id = ++seq;
    ws.send(JSON.stringify({ id, method, params }));
    return new Promise((ok, ko) => enAttente.set(id, { ok, ko }));
  };
  await cdp("Page.enable");
  await cdp("Runtime.enable");

  const nav = {
    cdp,
    journal,
    async taille(l, h, mobile = false, echelle = 1) {
      await cdp("Emulation.setDeviceMetricsOverride", { width: l, height: h, deviceScaleFactor: echelle, mobile });
    },
    async evaluer(expr) {
      const r = await cdp("Runtime.evaluate", { expression: expr, returnByValue: true, awaitPromise: true });
      if (r.exceptionDetails) throw new Error("erreur JS : " + (r.exceptionDetails.exception?.description || r.exceptionDetails.text));
      return r.result.value;
    },
    async aller(url, pret = "document.readyState === 'complete'") {
      await cdp("Page.navigate", { url });
      for (let i = 0; i < 100; i++) {
        if (await nav.evaluer(pret).catch(() => false)) return;
        await attendre(100);
      }
      throw new Error("la page ne se charge pas : " + url);
    },
    async cliquer(x, y) {
      for (const type of ["mouseMoved", "mousePressed", "mouseReleased"]) {
        await cdp("Input.dispatchMouseEvent", { type, x, y, button: "left", clickCount: type === "mouseMoved" ? 0 : 1 });
      }
      await attendre(80);
    },
    async glisser(x1, y1, x2, y2, etapes = 8) {
      await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x: x1, y: y1 });
      await cdp("Input.dispatchMouseEvent", { type: "mousePressed", x: x1, y: y1, button: "left", clickCount: 1 });
      for (let i = 1; i <= etapes; i++) {
        const x = x1 + ((x2 - x1) * i) / etapes, y = y1 + ((y2 - y1) * i) / etapes;
        await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", x, y, button: "left", buttons: 1 });
        await attendre(16);
      }
      await cdp("Input.dispatchMouseEvent", { type: "mouseReleased", x: x2, y: y2, button: "left", clickCount: 1 });
      await attendre(80);
    },
    async capture(chemin) {
      const r = await cdp("Page.captureScreenshot", { format: "png" });
      mkdirSync(dirname(chemin), { recursive: true });
      writeFileSync(chemin, Buffer.from(r.data, "base64"));
    },
    async fermer() {
      try { await cdp("Browser.close"); } catch { /* déjà fermé */ }
      await attendre(300);
      try { proc.kill(); } catch { /* déjà fermé */ }
      try { rmSync(profil, { recursive: true, force: true }); } catch { /* fichiers encore verrouillés */ }
    },
  };
  await nav.taille(largeur, hauteur);
  return nav;
}
