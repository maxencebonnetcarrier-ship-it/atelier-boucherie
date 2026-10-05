// Captures d'aperçu de la vue 3D : node outils/apercu.mjs <animal> [vue ...]
// Vues possibles : depart, profil, avant, arriere, dessus. Images dans outils/controle/apercu-<animal>-<vue>.png
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { lancer, attendre } from "./navigateur.mjs";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
const [animal = "boeuf", ...vues] = process.argv.slice(2);
const nav = await lancer({ largeur: 1400, hauteur: 1000, port: 9338 });
try {
  await nav.aller(pathToFileURL(join(RACINE, "app", "index.html")).href + "#" + animal,
    "document.readyState === 'complete' && !!window.ATELIER3D");
  await attendre(400);
  for (const v of vues.length ? vues : ["depart"]) {
    if (v !== "depart") await nav.evaluer(`window.ATELIER3D.vue(${JSON.stringify(v)})`);
    await attendre(700);
    const fichier = join(RACINE, "outils", "controle", `apercu-${animal}-${v}.png`);
    await nav.capture(fichier);
    console.log("capture", fichier);
  }
  if (nav.journal.length) console.log("journal :", nav.journal.join("\n"));
} finally {
  await nav.fermer();
}
