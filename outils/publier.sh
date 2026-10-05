#!/usr/bin/env bash
# Met à jour le site en ligne (GitHub Pages) avec le contenu actuel du dossier app/.
# Usage : bash outils/publier.sh   (après avoir commité tes modifications)
# Le site est servi depuis la branche gh-pages, qui contient uniquement le dossier app/.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -n "$(git status --porcelain)" ]; then
  echo "Des modifications ne sont pas commitées : commite-les d'abord (git add -A && git commit)." >&2
  exit 1
fi
node outils/verifier.mjs
git subtree split -q --prefix app -b gh-pages-tmp
git branch -f gh-pages gh-pages-tmp
git branch -D -q gh-pages-tmp
git push origin main
git push origin gh-pages
echo "Publié : https://maxencebonnetcarrier-ship-it.github.io/atelier-boucherie/ (mise à jour en 1 à 2 minutes)"
