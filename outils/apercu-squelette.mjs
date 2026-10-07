// Captures du squelette et des muscles dans l'appli : node outils/apercu-squelette.mjs [adresse ...]
// Par défaut : #boeuf, #boeuf/squelette, #boeuf/squelette/palette, #boeuf/squelette/lombaires.
// Images dans outils/controle/squelette-<n>.png ; « mobile » en tête de liste : écran de téléphone.
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { lancer, attendre } from "./navigateur.mjs";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
let adresses = process.argv.slice(2);
const mobile = adresses[0] === "mobile";
if (mobile) adresses = adresses.slice(1);
if (!adresses.length) adresses = ["#boeuf", "#boeuf/squelette", "#boeuf/squelette/palette", "#boeuf/squelette/lombaires"];
const nav = await lancer({ largeur: 1400, hauteur: 1000, port: 9342 });
try {
  if (mobile) await nav.taille(390, 844, true, 2);
  const url = pathToFileURL(join(RACINE, "app", "index.html")).href;
  await nav.aller(url + "#boeuf", "document.readyState === 'complete' && !!window.ATELIER3D");
  let n = 0;
  for (const a of adresses) {
    const [hash, action] = a.split("!");
    await nav.evaluer(`location.hash = ${JSON.stringify(hash)}`);
    // le squelette est chargé à la demande : attendre qu'il soit affiché
    for (let i = 0; i < 60 && hash.includes("squelette"); i++) {
      if (await nav.evaluer("window.ATELIER3D.modeCourant().squelette")) break;
      await attendre(150);
    }
    if (action) await nav.evaluer(action);
    await attendre(1100);
    await nav.evaluer("window.scrollTo(0,0)");
    const f = join(RACINE, "outils", "controle", `squelette-${++n}.png`);
    await nav.capture(f);
    console.log(a, "->", f, JSON.stringify(await nav.evaluer("window.ATELIER3D.modeCourant()")));
  }
  if (nav.journal.length) console.log("journal :", nav.journal.join("\n"));
} finally {
  await nav.fermer();
}
