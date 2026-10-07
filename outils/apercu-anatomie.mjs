// Capture de la planche de contrôle des os : node outils/apercu-anatomie.mjs <fichier.png> [os=a,b] [vues=lat,cra] [muscles=1]
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { lancer, attendre } from "./navigateur.mjs";

const RACINE = dirname(dirname(fileURLToPath(import.meta.url)));
const [fichier = "anatomie.png", ...params] = process.argv.slice(2);
const qs = params.join("&");
const nbLignes = Number((params.find((p) => p.startsWith("lignes=")) || "lignes=6").split("=")[1]);
const nav = await lancer({ largeur: 1600, hauteur: Math.max(400, nbLignes * 304 + 8), port: 9341 });
try {
  await nav.aller(pathToFileURL(join(RACINE, "outils", "apercu-anatomie.html")).href + "?" + qs, "document.title === 'pret'");
  await attendre(200);
  const sortie = join(RACINE, "outils", "controle", fichier);
  await nav.capture(sortie);
  console.log("capture", sortie);
  if (nav.journal.length) console.log("journal :", nav.journal.join("\n"));
} finally {
  await nav.fermer();
}
