// Captures de la page atelier : node outils/apercu-atelier.mjs [mobile] "adresse!action" ...
// Images dans outils/controle/atelier-<n>.png ; affiche les erreurs JavaScript de la page.
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { lancer, attendre } from "./navigateur.mjs";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
let adresses = process.argv.slice(2);
const mobile = adresses[0] === "mobile";
if (mobile) adresses = adresses.slice(1);
if (!adresses.length) adresses = ["?region=cuisse", "?os=coxal", "?region=cuisse&piece=tranche-grasse"];
const nav = await lancer({ largeur: 1500, hauteur: 960, port: 9351 });
try {
  if (mobile) await nav.taille(390, 844, true, 2);
  let n = 0;
  for (const a of adresses) {
    const [requete, action] = a.split("!");
    const url = pathToFileURL(join(RACINE, "app", "atelier.html")).href + requete;
    await nav.aller(url, "document.readyState === 'complete' && !!window.ATELIER3D");
    await attendre(500);
    if (action) { await nav.evaluer(action); await attendre(900); }
    const f = join(RACINE, "outils", "controle", `atelier-${++n}.png`);
    await nav.capture(f);
    console.log(a, "->", f, JSON.stringify(await nav.evaluer("({pret: window.ATELIER3D.pret, objets: window.ATELIER3D.objets().length, etiquettes: window.ATELIER3D.etiquettesVisibles().length})")));
  }
  if (nav.journal.length) console.log("journal :\n" + nav.journal.join("\n"));
} finally {
  await nav.fermer();
}
