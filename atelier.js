/* Page atelier : une région (la cuisse, l'épaule), une pièce (ses muscles) ou un os (ses repères), en grand.
 *   atelier.html?region=cuisse                    la cuisse entière, muscle par muscle (ou ?region=epaule)
 *   atelier.html?region=cuisse&piece=tranche-grasse   une pièce et ses muscles
 *   atelier.html?os=coxal                         un os, ses repères nommés et les muscles posés dessus
 * Les formes 3D de la région sont chargées à la demande : data/atelier-<région>.js.
 * Glisser = tourner ; molette / pincer = zoomer ; clic droit / deux doigts = déplacer ; double-clic = s'approcher.
 */
(function () {
  "use strict";
  const T = window.THREE;
  const A = window.ATELIER;
  let MAILL = null;
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s == null ? "" : s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const PIECES = (window.PIECES && window.PIECES.boeuf) || [];
  const OS_APP = (window.OS && window.OS.boeuf) || [];
  const nomPiece = (id) => (PIECES.find((p) => p.id === id) || {}).nom || id;
  const nomOs = (id) => (A.os[id] && A.os[id].nom) || (OS_APP.find((o) => o.id === id) || {}).nom || id;

  // ---------- adresse ----------
  const q = new URLSearchParams(location.search);
  const osDemande = q.get("os");
  // la région qui contient l'os demandé, sinon celle de l'adresse (la cuisse par défaut)
  const REGION_ID = osDemande ? (Object.keys(A.regions).find((r) => A.regions[r].os.includes(osDemande)) || "cuisse")
    : A.regions[q.get("region")] ? q.get("region") : "cuisse";
  const REGION = A.regions[REGION_ID];
  const vue = osDemande ? { type: "os", id: osDemande }
    : { type: "region", id: REGION_ID, piece: REGION.pieces[q.get("piece")] ? q.get("piece") : null };
  // parcours guidé (?pas=1) : désosser la région (ou séparer la pièce) une étape à la fois, rien d'autre à l'écran
  const PAS = vue.type === "region" && q.get("pas") === "1";
  let infoPas = null;            // muscle touché pendant le parcours : son « comment le séparer » dans la carte
  if (PAS) document.body.classList.add("pas-a-pas");

  // ---------- décodage des formes ----------
  function octets(b64) {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  function geometrie(e) {
    const q16 = new Uint16Array(octets(e.sommets).buffer);
    const [lo, hi] = e.boite;
    const pos = new Float32Array(q16.length);
    for (let i = 0; i < q16.length; i++) { const a = i % 3; pos[i] = lo[a] + (q16[i] / 65535) * (hi[a] - lo[a]); }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.BufferAttribute(pos, 3));
    g.setIndex(new T.BufferAttribute(new Uint16Array(octets(e.triangles).buffer), 1));
    for (const [cle, attr, brut] of [["ombre", "ombre"], ["gras", "gras"], ["nacre", "nacre"], ["parties", "partie", true]]) {
      if (!e[cle]) continue;
      const b = octets(e[cle]);
      const f = new Float32Array(b.length);
      for (let i = 0; i < b.length; i++) f[i] = brut ? b[i] : b[i] / 255;
      g.setAttribute(attr, new T.BufferAttribute(f, 1));
    }
    g.computeVertexNormals(); g.computeBoundingSphere(); g.computeBoundingBox();
    return g;
  }

  // ---------- ce qu'on montre ----------
  const objets = [];            // { id, type: "muscle" | "gras" | "os", nom, mesh, centre, dir, ancre, pos, cible }
  const parId = new Map();
  let reperes = [];             // { id, point (Vector3), info }
  let osCentral = null;         // vue « os » : l'os au centre

  function ajouter(type, id, g, mat, extra = {}) {
    const mesh = new T.Mesh(g, mat);
    const o = { id, type, mesh, nom: extra.nom || id, montre: true, leve: false, courant: false, ...extra };
    mesh.userData.objet = o;
    objets.push(o); parId.set(id, o);
    return o;
  }

  function musclesDeLaVue() {
    if (vue.type === "region" && vue.piece) return REGION.pieces[vue.piece].slice();
    if (vue.type === "region") return [GRAS_ID, ...Object.values(REGION.pieces).flat()];
    return (A.os[vue.id] && A.os[vue.id].muscles) || [];
  }
  function osDeLaVue() {
    if (vue.type === "os") return [vue.id];
    if (vue.piece) {
      const mus = new Set(REGION.pieces[vue.piece]);
      return Object.keys(A.os).filter((id) => A.os[id].muscles.some((m) => mus.has(m)));
    }
    return REGION.os;
  }
  const GRAS_ID = REGION.gras;

  function construire() {
    if (!MAILL) throw new Error(`data/atelier-${REGION_ID}.js absent`);
    const mDispo = new Map(MAILL.muscles.map((m) => [m.id, m]));
    const oDispo = new Map(MAILL.os.map((o) => [o.id, o]));
    for (const id of osDeLaVue()) {
      const e = oDispo.get(id);
      if (!e) continue;
      // demi-carcasse : la colonne (sacrum, vertèbres) est fendue au milieu, on ne garde que le côté gauche (z ≥ 0)
      const mat = window.Materiaux3D.os({ coupeZ: (REGION.fendus || []).includes(id) ? 0 : -10,
        couleursParties: A.partiesCoxal.map((p) => p.couleur) });
      const o = ajouter("os", id, geometrie(e), mat, { nom: nomOs(id) });
      o.mesh.renderOrder = 1;
      if (vue.type === "os") osCentral = o;
    }
    for (const id of musclesDeLaVue()) {
      const e = mDispo.get(id);
      if (!e) continue;
      const info = A.muscles[id] || {};
      const mat = id === GRAS_ID ? window.Materiaux3D.gras()
        : window.Materiaux3D.viande({ teinte: info.teinte, persille: info.persille || 0, fibre: e.fibre });
      const o = ajouter(id === GRAS_ID ? "gras" : "muscle", id, geometrie(e), mat, { nom: info.nom || id, info, piece: e.piece });
      o.mesh.renderOrder = 2;
    }
    if (vue.type === "os" && MAILL.reperes[vue.id]) {
      const pos = osCentral.mesh.geometry.getAttribute("position");
      reperes = MAILL.reperes[vue.id].map((r) => {
        // posé sur le sommet de l'os le plus proche
        const p = new T.Vector3(...r.point), v = new T.Vector3();
        let best = Infinity, bi = 0;
        for (let i = 0; i < pos.count; i++) {
          v.fromBufferAttribute(pos, i);
          const d = v.distanceToSquared(p);
          if (d < best) { best = d; bi = i; }
        }
        return { id: r.id, point: new T.Vector3().fromBufferAttribute(pos, bi), info: A.reperes[r.id] || { nom: r.id } };
      });
    }
    // centre de référence, direction de séparation et point d'ancrage des étiquettes
    const boite = new T.Box3(), boiteMuscles = new T.Box3();
    for (const o of objets) {
      boite.union(o.mesh.geometry.boundingBox);
      if (o.type === "muscle") boiteMuscles.union(o.mesh.geometry.boundingBox);
    }
    // centre d'où les muscles s'écartent : l'os (vue os), la pièce elle-même (vue pièce), toute la cuisse
    const C = osCentral ? osCentral.mesh.geometry.boundingSphere.center.clone()
      : vue.piece && !boiteMuscles.isEmpty() ? boiteMuscles.getCenter(new T.Vector3()) : boite.getCenter(new T.Vector3());
    for (const o of objets) {
      const g = o.mesh.geometry;
      o.centre = g.boundingSphere.center.clone();
      o.dir = o.centre.clone().sub(C);
      if (o.type === "gras") o.dir.set(0.15, 1, 0.6);
      if (o.dir.lengthSq() < 1e-6) o.dir.set(0, 0, 1);
      o.dir.normalize();
      const pos = g.getAttribute("position"), v = new T.Vector3();
      let best = -Infinity;
      o.ancre = o.centre.clone();
      for (let i = 0; i < pos.count; i += 3) {
        v.fromBufferAttribute(pos, i);
        const s = v.clone().sub(C).dot(o.dir);
        if (s > best) { best = s; o.ancre.copy(v); }
      }
      o.pos = new T.Vector3(); o.cible = new T.Vector3();
      scene.add(o.mesh);
    }
    centreScene.copy(C);
    rayonScene = boite.getSize(new T.Vector3()).length() / 2;
    // écartement des muscles : à l'échelle de la pièce dans une vue « pièce » (un onglet n'est pas écarté
    // comme une cuisse entière), de toute la scène sinon
    rayonSeparation = vue.piece && !boiteMuscles.isEmpty() ? Math.max(boiteMuscles.getSize(new T.Vector3()).length() / 2, 0.05)
      : Math.max(rayonScene, 0.25);
  }

  // ---------- rendu ----------
  const sceneEl = $("scene");
  const rendu = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  rendu.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  rendu.setClearColor(0x000000, 0);
  sceneEl.insertBefore(rendu.domElement, sceneEl.firstChild);
  const scene = new T.Scene();
  const camera = new T.PerspectiveCamera(32, 1, 0.001, 50);
  const centreScene = new T.Vector3();
  let rayonScene = 1, rayonSeparation = 1;
  const cam = { az: 0.45, el: 0.22, dist: 3, cible: new T.Vector3() };
  let animCam = null, prevu = false, enMouvement = false;

  function demanderRendu() { if (!prevu) { prevu = true; requestAnimationFrame(boucle); } }
  function placerCamera() {
    camera.position.set(cam.cible.x + cam.dist * Math.cos(cam.el) * Math.sin(cam.az), cam.cible.y + cam.dist * Math.sin(cam.el),
      cam.cible.z + cam.dist * Math.cos(cam.el) * Math.cos(cam.az));
    camera.near = Math.max(0.0008, cam.dist * 0.01);
    camera.far = cam.dist + rayonScene * 6 + 2;
    camera.updateProjectionMatrix();
    camera.lookAt(cam.cible);
    camera.updateMatrixWorld();
  }
  const lisse = (k) => (k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2);
  function boucle(t) {
    prevu = false;
    let encore = false;
    if (animCam) {
      const k = Math.min(1, (t - (animCam.t0 ??= t)) / animCam.duree), e = lisse(k);
      cam.az = animCam.de.az + (animCam.vers.az - animCam.de.az) * e;
      cam.el = animCam.de.el + (animCam.vers.el - animCam.de.el) * e;
      cam.dist = animCam.de.dist * Math.pow(animCam.vers.dist / animCam.de.dist, e);
      cam.cible.lerpVectors(animCam.de.cible, animCam.vers.cible, e);
      if (k >= 1) animCam = null; else encore = true;
    }
    for (const o of objets) {
      if (o.pos.distanceToSquared(o.cible) > 1e-8) { o.pos.lerp(o.cible, 0.16); encore = true; } else o.pos.copy(o.cible);
      o.mesh.position.copy(o.pos);
    }
    placerCamera();
    rendu.render(scene, camera);
    placerEtiquettes();
    enMouvement = encore;
    if (encore) demanderRendu(); else planifierOcclusion();
  }
  function redimensionner() {
    const w = sceneEl.clientWidth, h = sceneEl.clientHeight;
    if (!w || !h) return;
    rendu.setSize(w, h, false);
    camera.aspect = w / h;
    demanderRendu();
  }
  new ResizeObserver(redimensionner).observe(sceneEl);

  function aller(vers, duree = 600) {
    const de = { az: cam.az, el: cam.el, dist: cam.dist, cible: cam.cible.clone() };
    const v = { az: vers.az ?? cam.az, el: vers.el ?? cam.el, dist: vers.dist ?? cam.dist, cible: (vers.cible || cam.cible).clone() };
    while (v.az - de.az > Math.PI) v.az -= 2 * Math.PI;
    while (v.az - de.az < -Math.PI) v.az += 2 * Math.PI;
    if (!duree) { Object.assign(cam, v); animCam = null; } else animCam = { de, vers: v, duree };
    demanderRendu();
  }
  // Cadre une liste d'objets (leur boîte, à leur position actuelle ou visée) : la largeur et la hauteur de la
  // boîte vues depuis la caméra remplissent l'écran (une épaule haute et étroite n'est pas rapetissée).
  function cadrer(liste, duree = 650, vers = {}) {
    const b = new T.Box3();
    for (const o of liste) {
      const bb = o.mesh.geometry.boundingBox.clone().translate(o.cible);
      b.union(bb);
    }
    if (b.isEmpty()) return;
    const c = b.getCenter(new T.Vector3());
    const az = vers.az ?? cam.az, el = vers.el ?? cam.el;
    const recul = new T.Vector3(Math.cos(el) * Math.sin(az), Math.sin(el), Math.cos(el) * Math.cos(az));   // de la cible vers la caméra
    const droite = new T.Vector3(0, 1, 0).cross(recul).normalize();
    const haut = recul.clone().cross(droite).normalize();
    let lx = 0, ly = 0, lz = 0;
    const p = new T.Vector3();
    for (const x of [b.min.x, b.max.x]) for (const y of [b.min.y, b.max.y]) for (const z of [b.min.z, b.max.z]) {
      p.set(x, y, z).sub(c);
      lx = Math.max(lx, Math.abs(p.dot(droite))); ly = Math.max(ly, Math.abs(p.dot(haut))); lz = Math.max(lz, Math.abs(p.dot(recul)));
    }
    const t = Math.tan(T.MathUtils.degToRad(camera.fov) / 2);
    // un os seul : plus de marge, pour que les noms posés à ses bouts restent dans le cadre
    const marge = vue.type === "os" ? 1.22 : 1.08;
    const dist = Math.max(lx / (t * Math.max(camera.aspect, 0.1)), ly / t) * marge + lz * 0.5;
    aller({ ...vers, cible: c, dist: Math.max(0.05, dist) }, duree);
  }

  // ---------- état : séparation, étapes, visibilité ----------
  // vue « os » : l'os seul d'abord ; « Muscles autour » les montre, écartés pour garder l'os visible
  const voir = { gras: true, nacre: true, os: true, noms: true, parties: false, autour: vue.type !== "os" };
  let separer = 0, etape = -1, choisi = null, survol = null;

  function listeEtapes() {
    if (vue.type !== "region") return [];
    return vue.piece ? (REGION.etapesPieces[vue.piece] || []) : REGION.etapes;
  }
  function majPositions() {
    const et = listeEtapes();
    const leves = new Set(), courants = new Set();
    et.forEach((e, i) => { if (i < etape) e.muscles.forEach((m) => leves.add(m)); else if (i === etape) e.muscles.forEach((m) => courants.add(m)); });
    for (const o of objets) {
      o.leve = leves.has(o.id); o.courant = courants.has(o.id);
      const k = o.type === "os" ? 0 : (o.leve ? 0.5 : 0) + (o.courant ? (PAS ? 0.2 : 0.1) : 0) + separer * (vue.type === "os" ? 0.75 : vue.piece ? 0.55 : 0.26);
      o.cible.copy(o.dir).multiplyScalar(k * rayonSeparation * (vue.type === "os" ? 1.4 : 1));
    }
    demanderRendu();
  }
  function majApparence() {
    for (const o of objets) {
      const u = o.mesh.material.uniforms;
      let vu = o.montre;
      if (o.type === "os") vu = vu && voir.os;
      if (o.type === "gras") vu = vu && voir.gras && !o.leve;
      if (o.type === "muscle" && vue.type === "os") vu = vu && voir.autour;
      o.mesh.visible = vu;
      u.marque.value = o === choisi || o.courant ? 1 : 0;
      u.survol.value = o === survol ? 1 : 0;
      if (u.voirGras) u.voirGras.value = voir.gras ? 1 : 0;
      if (u.voirNacre) u.voirNacre.value = voir.nacre ? 1 : 0;
      if (u.voirParties) u.voirParties.value = voir.parties ? 1 : 0;
      // vue « os » : les muscles autour sont en transparence tant qu'on ne les écarte pas
      let op = 1;
      if (o.type === "gras" && vue.type === "region" && !vue.piece) op = Math.max(0, 1 - separer * 3);
      if (o.type === "gras" && op < 0.02) o.mesh.visible = false;
      u.opacite.value = op;
      o.mesh.material.transparent = op < 0.999;
      o.mesh.material.depthWrite = op >= 0.999;
      o.mesh.renderOrder = op < 0.999 ? 5 : (o.type === "os" ? 1 : 2);
    }
    majListes();
    demanderRendu();
  }

  // ---------- étiquettes ----------
  const calque = $("etiquettes");
  let etiquettes = [];
  function preparerEtiquettes() {
    calque.innerHTML = "";
    etiquettes = [];
    const mk = (cls, texte, objet, point, repere) => {
      const el = document.createElement("div");
      el.className = "et " + cls;
      el.textContent = texte;
      el.addEventListener("click", (ev) => { ev.stopPropagation(); repere ? choisirRepere(repere) : choisir(objet); });
      calque.appendChild(el);
      etiquettes.push({ el, objet, point, repere, cache: false });
    };
    for (const o of objets) {
      if (o.type === "muscle" || o.type === "gras") mk("", o.nom, o, o.ancre);
      else if (vue.type === "region") mk("os", o.nom, o, o.ancre);
    }
    for (const r of reperes) mk("os", r.info.nom, osCentral, r.point, r);
  }
  const v3 = new T.Vector3();
  function placerEtiquettes() {
    const W = sceneEl.clientWidth, H = sceneEl.clientHeight;
    const places = [];
    const ordre = etiquettes.slice().sort((a, b) => (b.objet === choisi) - (a.objet === choisi));
    for (const e of ordre) {
      const o = e.objet;
      const fini = PAS && etape >= listeEtapes().length;
      const utile = !PAS || o.type === "os" || o.courant || (fini && o.type === "muscle");
      const montre = voir.noms && o.mesh.visible && utile;
      if (!montre) { e.el.style.visibility = "hidden"; continue; }
      v3.copy(e.point).add(o.mesh.position).project(camera);
      if (v3.z > 1 || Math.abs(v3.x) > 1.05 || Math.abs(v3.y) > 1.05) { e.el.style.visibility = "hidden"; continue; }
      const x = ((v3.x + 1) / 2) * W, y = ((1 - v3.y) / 2) * H;
      const w = e.el.offsetWidth || 60, h = 20;
      const r = { x0: x - w / 2, x1: x + w / 2, y0: y - h - 10, y1: y - 10 };
      const chevauche = places.some((p) => r.x0 < p.x1 && r.x1 > p.x0 && r.y0 < p.y1 && r.y1 > p.y0);
      if (chevauche && e.objet !== choisi && !(e.repere && e.repere === repereChoisi)) { e.el.style.visibility = "hidden"; continue; }
      places.push(r);
      e.el.style.visibility = "visible";
      e.el.style.left = x + "px";
      e.el.style.top = (y - 8) + "px";
      e.el.classList.toggle("choisi", e.objet === choisi && (!e.repere || e.repere === repereChoisi));
      e.el.classList.toggle("cache", e.cache);
    }
  }
  // Étiquette derrière la matière : estompée (vérifié quand la vue s'arrête, c'est un calcul coûteux).
  let minuteurOcclusion = 0;
  const lanceur = new T.Raycaster();
  function planifierOcclusion() {
    clearTimeout(minuteurOcclusion);
    minuteurOcclusion = setTimeout(() => {
      const cibles = objets.filter((o) => o.mesh.visible && o.mesh.material.uniforms.opacite.value > 0.6).map((o) => o.mesh);
      for (const e of etiquettes) {
        if (e.el.style.visibility !== "visible") continue;
        const p = e.point.clone().add(e.objet.mesh.position);
        const d = p.distanceTo(camera.position);
        lanceur.set(camera.position, p.clone().sub(camera.position).normalize());
        lanceur.far = d - 0.004;
        const hs = lanceur.intersectObjects(cibles, false);
        e.cache = hs.length > 0 && hs[0].object !== e.objet.mesh;
        e.el.classList.toggle("cache", e.cache);
      }
    }, 220);
  }

  // ---------- choix (clic) et carte ----------
  let repereChoisi = null;
  function lienFiche(piece) { return piece ? `<a href="index.html#boeuf/${encodeURIComponent(piece)}">Fiche « ${esc(nomPiece(piece))} » →</a>` : ""; }
  function lienSource(cle) {
    const s = A.sources[cle];
    if (!s) return "";
    return s.url ? `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.titre)}</a>` : esc(s.titre);
  }
  function carteHtml(o) {
    if (!o) return "";
    if (o.type === "os") {
      const i = A.os[o.id] || {};
      return `<h3>${esc(o.nom)}</h3><p class="latin">${esc(i.latin || "")}</p><p>${esc(i.info || "")}</p>
        <div class="liens">${vue.type !== "os" && A.os[o.id] ? `<a href="atelier.html?os=${o.id}">Voir l’os seul et ses repères →</a>` : ""}</div>`;
    }
    const i = o.info || {};
    return `<h3>${esc(o.nom)}</h3>
      ${i.anat ? `<p class="latin">${esc(i.anat)}</p>` : ""}
      <p>${esc(i.info || "")}</p>
      ${i.separer ? `<p><strong>Comment le séparer :</strong> ${esc(i.separer)}</p>` : ""}
      ${i.usage ? `<p><strong>Usage :</strong> ${esc(i.usage)}</p>` : ""}
      ${i.lettre ? `<p class="src">Lettre ${esc(i.lettre)} sur le tableau n° 2 du classeur.</p>` : ""}
      <div class="liens">${lienFiche(o.piece)}${o.piece && vue.piece !== o.piece && REGION.pieces[o.piece] && REGION.pieces[o.piece].length > 1
        ? `<a href="atelier.html?region=${REGION_ID}&piece=${o.piece}">Séparer « ${esc(nomPiece(o.piece))} » →</a>` : ""}</div>
`;
  }
  function montrerCarte(html) {
    const c = $("carte");
    if (!html) { c.hidden = true; c.innerHTML = ""; return; }
    c.innerHTML = `<button type="button" class="fermer" aria-label="Fermer">×</button>` + html;
    c.querySelector(".fermer").onclick = () => choisir(null);
    c.hidden = false;
  }
  function choisir(o, cadrerDessus = false) {
    if (PAS) { choisi = o; repereChoisi = null; infoPas = o || null; rendrePas(); majApparence(); return; }
    choisi = o; repereChoisi = null;
    montrerCarte(carteHtml(o));
    // choisi dans une liste : on le MONTRE. Le gras de couverture qui le recouvre est retiré (le bouton « Gras »
    // le remet).
    if (o && cadrerDessus && o.type === "muscle" && voir.gras && objets.some((x) => x.type === "gras")) {
      voir.gras = false;
      const b = document.querySelector('#bascules [data-voir="gras"]');
      if (b) b.setAttribute("aria-pressed", "false");
    }
    if (o && cadrerDessus) { cadrer([o]); montrerScene(); }
    majApparence();
  }
  // Sur téléphone, le panneau (listes, étapes) est sous la 3D : choisir dans une liste remonte jusqu'à la 3D
  // pour VOIR ce qu'on a choisi, si elle n'est pas déjà à l'écran.
  function montrerScene() {
    if (!window.matchMedia("(max-width: 900px)").matches || document.fullscreenElement) return;
    const r = sceneEl.getBoundingClientRect();
    if (r.top >= 0 && r.bottom <= window.innerHeight) return;
    window.scrollTo({ top: Math.max(0, r.top + window.scrollY - 6), behavior: "smooth" });
  }
  function choisirRepere(r) {
    choisi = osCentral; repereChoisi = r;
    montrerCarte(`<h3>${esc(r.info.nom)}</h3><p class="latin">${esc(r.info.latin || "")}</p>
      <p>${esc(r.info.boucher || "")}</p>`);
    aller({ cible: r.point.clone().add(osCentral.mesh.position), dist: Math.max(0.12, cam.dist * 0.6) });
    majApparence();
    montrerScene();
  }

  // ---------- souris et doigts ----------
  const toile = rendu.domElement;
  const souris = new T.Vector2();
  function viser(cx, cy) {
    const r = toile.getBoundingClientRect();
    souris.set(((cx - r.left) / r.width) * 2 - 1, -((cy - r.top) / r.height) * 2 + 1);
    placerCamera();
    lanceur.far = Infinity;
    lanceur.setFromCamera(souris, camera);
    const cibles = objets.filter((o) => o.mesh.visible).map((o) => o.mesh);
    const hs = lanceur.intersectObjects(cibles, false);
    // une chose en transparence ne cache pas ce qui est net derrière elle
    const net = hs.find((h) => h.object.material.uniforms.opacite.value > 0.6);
    return net || hs[0] || null;
  }
  const pointeurs = new Map();
  let appui = null, geste = null, dernierClic = 0;
  toile.addEventListener("contextmenu", (e) => e.preventDefault());
  toile.addEventListener("pointerdown", (e) => {
    pointeurs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    toile.setPointerCapture(e.pointerId);
    animCam = null;
    if (pointeurs.size === 1) {
      appui = { x: e.clientX, y: e.clientY, t: performance.now(), az: cam.az, el: cam.el, glisse: false,
        deplacer: e.button === 2 || e.button === 1 || e.shiftKey, dernier: { x: e.clientX, y: e.clientY } };
    } else if (pointeurs.size === 2) {
      const [a, b] = [...pointeurs.values()];
      geste = { dist: Math.hypot(a.x - b.x, a.y - b.y) || 1, camDist: cam.dist, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
      if (appui) appui.glisse = true;
    }
  });
  function panner(dx, dy) {
    const parPixel = (2 * cam.dist * Math.tan(T.MathUtils.degToRad(camera.fov) / 2)) / Math.max(1, sceneEl.clientHeight);
    const droite = new T.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
    const haut = new T.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
    cam.cible.addScaledVector(droite, -dx * parPixel).addScaledVector(haut, dy * parPixel);
  }
  toile.addEventListener("pointermove", (e) => {
    if (pointeurs.has(e.pointerId)) pointeurs.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (geste && pointeurs.size >= 2) {
      const [a, b] = [...pointeurs.values()];
      cam.dist = Math.max(0.03, Math.min(rayonScene * 8, geste.camDist * geste.dist / (Math.hypot(a.x - b.x, a.y - b.y) || 1)));
      const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
      panner(mx - geste.mx, my - geste.my);
      geste.mx = mx; geste.my = my;
      demanderRendu();
      return;
    }
    if (appui) {
      const dx = e.clientX - appui.x, dy = e.clientY - appui.y;
      if (!appui.glisse && Math.hypot(dx, dy) > 6) appui.glisse = true;
      if (appui.glisse) {
        if (appui.deplacer) panner(e.clientX - appui.dernier.x, e.clientY - appui.dernier.y);
        else { cam.az = appui.az - dx * 0.008; cam.el = Math.max(-1.45, Math.min(1.45, appui.el + dy * 0.006)); }
        appui.dernier = { x: e.clientX, y: e.clientY };
        demanderRendu();
      }
      return;
    }
    if (e.pointerType === "mouse") survoler(e.clientX, e.clientY);
  });
  let minuteurSurvol = 0;
  function survoler(x, y) {
    clearTimeout(minuteurSurvol);
    minuteurSurvol = setTimeout(() => {
      const h = viser(x, y);
      const o = h ? h.object.userData.objet : null;
      if (o !== survol) { survol = o; majApparence(); }
      toile.style.cursor = o ? "pointer" : "grab";
    }, 40);
  }
  const fin = (e) => {
    pointeurs.delete(e.pointerId);
    if (pointeurs.size < 2 && geste) {
      geste = null;
      const [r] = [...pointeurs.values()];
      if (r && appui) Object.assign(appui, { x: r.x, y: r.y, az: cam.az, el: cam.el, glisse: true, dernier: { ...r } });
    }
    if (!appui || pointeurs.size) return;
    const clic = !appui.glisse && performance.now() - appui.t < 700 && e.type === "pointerup";
    appui = null;
    if (!clic) return;
    const maintenant = performance.now();
    const h = viser(e.clientX, e.clientY);
    if (maintenant - dernierClic < 320 && h) {           // double-clic : on s'approche du point touché
      aller({ cible: h.point.clone(), dist: Math.max(0.04, cam.dist * 0.5) });
      dernierClic = 0;
      return;
    }
    dernierClic = maintenant;
    choisir(h ? h.object.userData.objet : null);
  };
  toile.addEventListener("pointerup", fin);
  toile.addEventListener("pointercancel", fin);
  // molette sur toute la scène, noms des muscles compris (sinon un nom passé sous la souris bloque le zoom) ;
  // la carte d'explication et les boutons gardent leur comportement normal
  sceneEl.addEventListener("wheel", (e) => {
    if (e.target.closest(".carte-choix, .boutons-scene")) return;
    e.preventDefault();
    animCam = null;
    cam.dist = Math.max(0.03, Math.min(rayonScene * 8, cam.dist * Math.exp(e.deltaY * 0.0012)));
    demanderRendu();
  }, { passive: false });

  // ---------- panneau ----------
  const pastille = (o) => o.type === "gras" ? "#efe2c4" : o.type === "os" ? "#e8dcc1" : (o.info && o.info.teinte) || "#a33";
  function majListes() {
    document.querySelectorAll("[data-objet]").forEach((li) => li.classList.toggle("choisi", choisi && li.dataset.objet === choisi.id));
    document.querySelectorAll("[data-oeil]").forEach((b) => { const o = parId.get(b.dataset.oeil); b.setAttribute("aria-pressed", o && o.montre ? "true" : "false"); });
    document.querySelectorAll("[data-etape]").forEach((li) => {
      const i = +li.dataset.etape;
      li.classList.toggle("faite", i < etape); li.classList.toggle("courante", i === etape);
    });
  }
  function ligneObjet(o) {
    const i = o.info || {};
    return `<li data-objet="${esc(o.id)}"><span class="pastille" style="background:${pastille(o)}"></span>
      <span>${esc(o.nom)}${i.anat ? `<br><small>${esc(i.anat)}</small>` : ""}</span>
      <button type="button" class="oeil" data-oeil="${esc(o.id)}" aria-pressed="true" title="Montrer / cacher">👁</button></li>`;
  }
  function construirePanneau() {
    // titre
    const titre = vue.type === "os" ? nomOs(vue.id) : vue.piece ? nomPiece(vue.piece) : REGION.nom;
    $("titre").textContent = titre;
    $("sous-titre").textContent = vue.type === "os" ? (A.os[vue.id] ? A.os[vue.id].latin : "")
      : vue.piece ? "Ses muscles, un par un, et comment les séparer" : REGION.sousTitre;
    document.title = titre + " — Atelier 3D";
    // autres vues
    // les vues de cette région, puis l'entrée des autres régions
    const liens = [...REGION.vues, ...Object.entries(A.regions).filter(([r]) => r !== REGION_ID).map(([r, R]) => [R.court, `?region=${r}`])];
    $("vues").innerHTML = liens.map(([n, h]) => `<a href="atelier.html${h}" class="${location.search === h ? "actif" : ""}">${esc(n)}</a>`).join("");
    // bascules
    const bascules = [["gras", "Gras", objets.some((o) => o.type === "gras")], ["nacre", "Peaux nacrées", true],
      ["os", "Os", vue.type !== "os"], ["noms", "Noms", true], ["parties", "Parties de l’os", vue.type === "os" && vue.id === "coxal"],
      ["autour", "Muscles autour", vue.type === "os" && objets.some((o) => o.type === "muscle")]];
    $("bascules").innerHTML = bascules.filter((b) => b[2]).map(([k, n]) => `<button type="button" data-voir="${k}" aria-pressed="${voir[k]}">${esc(n)}</button>`).join("");
    $("bascules").onclick = (e) => {
      const b = e.target.closest("[data-voir]");
      if (!b) return;
      voir[b.dataset.voir] = !voir[b.dataset.voir];
      b.setAttribute("aria-pressed", voir[b.dataset.voir]);
      if (b.dataset.voir === "autour" && voir.autour) {
        if (separer < 0.3) { separer = 0.6; $("separer").value = 60; $("separer-val").textContent = "60 %"; majPositions(); }
        majApparence();
        cadrer(objets.filter((o) => o.mesh.visible), 700);
        return;
      }
      majApparence();
    };
    // muscles, groupés par pièce
    const mus = objets.filter((o) => o.type === "muscle" || o.type === "gras");
    $("titre-muscles").textContent = vue.type === "os" ? "Muscles posés sur l’os" : "Muscles";
    if (vue.type === "region" && !vue.piece) {
      const gras = mus.filter((o) => o.type === "gras");
      $("muscles").innerHTML = (gras.length ? `<div class="groupe-muscles"><ul>${gras.map(ligneObjet).join("")}</ul></div>` : "")
        + Object.entries(REGION.pieces).map(([p, ids]) => `<div class="groupe-muscles"><h3><a href="atelier.html?region=${REGION_ID}&piece=${p}">${esc(nomPiece(p))}</a></h3>
          <ul>${ids.map((id) => parId.get(id)).filter(Boolean).map(ligneObjet).join("")}</ul></div>`).join("");
    } else {
      $("muscles").innerHTML = mus.length ? `<div class="groupe-muscles"><ul>${mus.map(ligneObjet).join("")}</ul></div>` : `<p class="note">Aucun muscle détaillé pour cet os.</p>`;
    }
    $("muscles").onclick = (e) => {
      const oeil = e.target.closest("[data-oeil]");
      if (oeil) { const o = parId.get(oeil.dataset.oeil); o.montre = !o.montre; majApparence(); return; }
      const li = e.target.closest("[data-objet]");
      if (li) choisir(parId.get(li.dataset.objet), true);
    };
    // os
    const os = objets.filter((o) => o.type === "os");
    $("bloc-os").hidden = !os.length;
    $("liste-os").innerHTML = os.map((o) => `<li data-objet="${esc(o.id)}"><span class="pastille" style="background:#e8dcc1"></span><span>${esc(o.nom)}</span>
      ${A.os[o.id] && vue.type !== "os" ? `<a class="oeil" href="atelier.html?os=${o.id}" title="Voir l’os seul" onclick="event.stopPropagation()">↗</a>` : ""}</li>`).join("");
    $("liste-os").onclick = (e) => { const li = e.target.closest("[data-objet]"); if (li) choisir(parId.get(li.dataset.objet), true); };
    // repères
    $("bloc-reperes").hidden = !reperes.length;
    $("reperes").innerHTML = reperes.map((r, i) => `<li data-repere="${i}"><span class="pastille" style="background:#fff"></span>
      <span><strong>${esc(r.info.nom)}</strong> <small>${esc(r.info.latin || "")}</small><br><small>${esc(r.info.boucher || "")}</small></span></li>`).join("")
      + (vue.id === "coxal" ? `<li class="note">${A.partiesCoxal.map((p) => `<span class="pastille" style="background:${p.couleur}"></span> ${esc(p.nom)}`).join(" · ")} : bouton « Parties de l’os » (limites approximatives, les trois os sont soudés chez l’adulte).</li>` : "");
    $("reperes").onclick = (e) => { const li = e.target.closest("[data-repere]"); if (li) choisirRepere(reperes[+li.dataset.repere]); };
    // étapes
    const et = listeEtapes();
    $("bloc-etapes").hidden = !et.length;
    $("lien-pas").href = `atelier.html?region=${REGION_ID}${vue.piece ? `&piece=${vue.piece}` : ""}&pas=1`;
    if (PAS) {
      $("titre").textContent = (vue.piece ? "Séparer pas à pas : " : "Désosser pas à pas : ") + titre;
      $("sous-titre").textContent = "Une étape à la fois";
      document.title = $("titre").textContent + " — Atelier 3D";
    }
    $("etapes").innerHTML = et.map((e, i) => `<li data-etape="${i}"><strong>${esc(e.titre)}</strong><p>${esc(e.texte)}</p></li>`).join("");
    $("etapes").onclick = (e) => { const li = e.target.closest("[data-etape]"); if (li) allerEtape(+li.dataset.etape); };
    $("e-prec").onclick = () => allerEtape(Math.max(-1, etape - 1));
    $("e-suiv").onclick = () => allerEtape(Math.min(et.length - 1, etape + 1));
    $("e-zero").onclick = () => allerEtape(-1);
    // sources citées sur la page (repliées en bas : elles n'alourdissent plus le texte)
    const cles = new Set();
    for (const o of objets) (o.info && o.info.sources || []).forEach((s) => cles.add(s));
    et.forEach((e) => (e.sources || []).forEach((s) => cles.add(s)));
    for (const o of objets) if (o.info && o.info.anatSource) cles.add(o.info.anatSource);
    if (reperes.length) cles.add((A.os[vue.id] && A.os[vue.id].sourceReperes) || "imaios");
    cles.add("planches"); cles.add("reussir");
    $("sources").innerHTML = [...cles].filter((c) => A.sources[c]).map((c) => `<li>${lienSource(c)}</li>`).join("");
    // séparer
    $("separer").oninput = (e) => {
      separer = +e.target.value / 100;
      $("separer-val").textContent = Math.round(separer * 100) + " %";
      majPositions(); majApparence();
    };
    $("b-recadrer").onclick = () => recadrer();
    $("b-plein").onclick = () => {
      if (document.fullscreenElement) document.exitFullscreen();
      else if ($("colonne-scene").requestFullscreen) $("colonne-scene").requestFullscreen().catch(() => {});
    };
  }
  // ---------- parcours guidé ----------
  function rendrePas() {
    const et = listeEtapes(), n = et.length, c = $("carte-pas");
    const nom = vue.piece ? nomPiece(vue.piece) : REGION.nom;
    const sortir = `atelier.html?region=${REGION_ID}${vue.piece ? `&piece=${vue.piece}` : ""}`;
    let corps;
    if (etape < 0) {
      corps = `<h3>${vue.piece ? "Séparer" : "Désosser"} : ${esc(nom)}</h3>
        <p>${n} étapes, une à la fois. À chaque étape, ce qu’il faut lever est <b>surligné en doré</b> ; ce qui est déjà levé est posé à côté.</p>
        <p class="astuce">Fais tourner la 3D avec le doigt pour regarder sous tous les angles. Touche un muscle pour savoir comment le séparer.</p>`;
    } else if (etape >= n) {
      corps = `<h3>C’est fini !</h3>
        <p>${esc(nom)} : ${vue.piece ? "chaque muscle est séparé, posé à côté des autres" : "chaque morceau est levé et posé autour de l’os"}.</p>`;
    } else {
      const e = et[etape];
      corps = `<h3>${esc(e.titre)}</h3><p>${esc(e.texte)}</p>
        <div class="a-lever">À lever : ${e.muscles.map((m) => parId.get(m)).filter(Boolean)
          .map((o) => `<button type="button" data-m="${esc(o.id)}" aria-pressed="${infoPas === o}">${esc(o.nom)}</button>`).join("")}</div>`;
    }
    const texteInfo = infoPas && ((infoPas.info && (infoPas.info.separer || infoPas.info.info)) || (A.os[infoPas.id] && A.os[infoPas.id].info) || "");
    const info = infoPas ? `<p class="info-muscle"><b>${esc(infoPas.nom)}</b> : ${esc(texteInfo)}</p>` : "";
    const fait = etape < 0 ? 0 : Math.min(n, etape + 1);
    c.innerHTML = `<div class="pas-entete"><span>${etape < 0 ? "Avant de commencer" : etape >= n ? "Terminé" : `Étape ${etape + 1} sur ${n}`}</span>
        <progress max="${n}" value="${fait}"></progress></div>
      ${corps}${info}
      <div class="nav-pas">
        ${etape >= 0 ? `<button type="button" data-pas="prec">◀ Précédente</button>` : ""}
        ${etape < n ? `<button type="button" data-pas="suiv" class="principal">${etape < 0 ? "Commencer ▶" : etape === n - 1 ? "Terminer ▶" : "Suivante ▶"}</button>`
          : `<button type="button" data-pas="zero" class="principal">↺ Recommencer</button>`}
      </div>
      <a class="quitter" href="${sortir}">Quitter le pas à pas</a>`;
    c.hidden = false;
  }
  function allerPas(i) {
    const n = listeEtapes().length;
    etape = Math.max(-1, Math.min(n, i));
    infoPas = null; choisi = null;
    majPositions(); majApparence();
    placerEtiquettes();          // les noms changent tout de suite (pas un nom d'étape d'avant qui traîne)
    rendrePas();
    if (etape < 0) recadrer();
    else if (etape >= n) cadrer(objets.filter((o) => o.mesh.visible), 700);      // tous les morceaux autour de l'os
    else {
      // ce qui reste de la pièce (le morceau à lever compris) ; ce qui est déjà levé est posé à côté
      const reste = objets.filter((o) => o.mesh.visible && !o.leve);
      cadrer(reste.length ? reste : objets.filter((o) => o.courant), 700);
    }
  }
  $("carte-pas").addEventListener("click", (e) => {
    const b = e.target.closest("[data-pas]");
    if (b) { allerPas(b.dataset.pas === "zero" ? -1 : etape + (b.dataset.pas === "suiv" ? 1 : -1)); return; }
    const m = e.target.closest("[data-m]");
    if (m) choisir(parId.get(m.dataset.m));
  });
  document.addEventListener("keydown", (e) => {
    if (!PAS || e.target.closest("input, textarea")) return;
    if (e.key === "ArrowRight") allerPas(etape + 1);
    if (e.key === "ArrowLeft") allerPas(etape - 1);
  });

  function allerEtape(i) {
    etape = i;
    majPositions(); majApparence();
    const et = listeEtapes()[i];
    if (et) {
      const os = et.muscles.map((m) => parId.get(m)).filter(Boolean);
      if (os.length) { choisir(null); cadrer(objets.filter((o) => o.mesh.visible || os.includes(o)), 700); }
      montrerCarte(`<h3>Étape ${i + 1} : ${esc(et.titre)}</h3><p>${esc(et.texte)}</p>`);
      montrerScene();
    } else { montrerCarte(""); recadrer(); }
  }
  // angle de départ : l'os du bassin vu de trois quarts par-dessous (plancher et trou obturé visibles)
  function VUE_DEPART() {
    if (vue.type === "os") return (A.os[vue.id] && A.os[vue.id].vue) || { az: 0.5, el: 0.25 };
    return REGION.vue || { az: 0.55, el: 0.2 };
  }
  // ce qu'on cadre : l'os seul (vue os), les muscles de la pièce (vue pièce), tout (cuisse)
  function aCadrer(o) { return vue.type === "os" ? o.type === "os" : vue.piece ? o.type === "muscle" : true; }
  function recadrer() {
    const vus = objets.filter((o) => o.mesh.visible && aCadrer(o));
    const vers = VUE_DEPART();
    cadrer(vus.length ? vus : objets, 600, vers);
  }

  // ---------- démarrage : les formes 3D de la région sont chargées à la demande ----------
  function demarrer() {
    MAILL = (window.ATELIER_MAILLAGES || {})[REGION_ID] || null;
    try {
      construire();
      if (!objets.length) throw new Error("rien à montrer pour cette adresse");
      preparerEtiquettes();
      construirePanneau();
      majPositions(); majApparence();
      redimensionner();
      cadrer(objets.filter(aCadrer), 0, VUE_DEPART());
      if (PAS) allerPas(-1);
      $("chargement").hidden = true;
    } catch (err) {
      $("chargement").textContent = "Impossible d’afficher cette vue : " + err.message;
      console.error(err);
    }
    exposer();
  }
  const script = document.createElement("script");
  script.src = `data/atelier-${REGION_ID}.js`;
  script.onload = demarrer;
  script.onerror = () => { $("chargement").textContent = `Impossible de charger les formes 3D (data/atelier-${REGION_ID}.js).`; exposer(); };
  document.head.appendChild(script);

  // ---------- accès pour les tests automatiques (une fois la vue construite) ----------
  function exposer() {
  window.ATELIER3D = {
    pret: objets.length > 0,
    region: REGION_ID,
    vue: () => ({ ...vue }),
    objets: () => objets.map((o) => ({ id: o.id, type: o.type, visible: o.mesh.visible, opacite: o.mesh.material.uniforms.opacite.value,
      decale: o.mesh.position.length(), leve: o.leve, courant: o.courant })),
    reperes: () => reperes.map((r) => r.id),
    selection: () => (choisi ? { id: choisi.id, repere: repereChoisi && repereChoisi.id } : null),
    carte: () => ($("carte").hidden ? null : $("carte").innerText),
    etape: () => etape,
    pas: () => (PAS ? { etape, total: listeEtapes().length, texte: $("carte-pas").innerText } : null),
    immobile: () => !enMouvement && !animCam && !prevu,
    orientation: () => ({ az: cam.az, el: cam.el, dist: cam.dist, cible: cam.cible.toArray() }),
    etiquettesVisibles: () => etiquettes.filter((e) => e.el.style.visibility === "visible").map((e) => e.repere ? e.repere.id : e.objet.id),
    // ce que toucherait un clic en (x, y) (pixels de la page) : l'objet 3D visé et l'élément de la page dessus
    toucher(x, y) {
      const h = viser(x, y), el = document.elementFromPoint(x, y);
      return { objet: h ? h.object.userData.objet.id : null, element: el === toile ? "scene" : el ? el.className || el.tagName : null };
    },
    // un point de l'écran (pixels de la page) où l'objet est touché en premier ; tourne la vue si besoin
    pointEcran(id) {
      const o = parId.get(id);
      if (!o) return null;
      const r = toile.getBoundingClientRect();
      const ici = { az: cam.az, el: cam.el };
      for (const daz of [0, 0.7, -0.7, 1.6, -1.6, Math.PI]) {
        for (const del of [0, 0.5, -0.4]) {
          cam.az = ici.az + daz; cam.el = Math.max(-1.4, Math.min(1.4, ici.el + del));
          placerCamera(); rendu.render(scene, camera);
          const pos = o.mesh.geometry.getAttribute("position"), p = new T.Vector3();
          const pas = Math.max(1, Math.floor(pos.count / 120));
          for (let i = 0; i < pos.count; i += pas) {
            p.fromBufferAttribute(pos, i).add(o.mesh.position).project(camera);
            if (Math.abs(p.x) > 0.85 || Math.abs(p.y) > 0.85 || p.z > 1) continue;
            const x = r.left + ((p.x + 1) / 2) * r.width, y = r.top + ((1 - p.y) / 2) * r.height;
            // un point franchement dans l'objet : il est encore touché 2 px plus loin dans chaque direction (un sommet
            // pris sur le contour peut tomber à côté au moindre arrondi de la position du clic)
            if ([[0, 0], [2, 0], [-2, 0], [0, 2], [0, -2]].some(([dx, dy]) => { const h = viser(x + dx, y + dy); return !h || h.object !== o.mesh; })) continue;
            placerEtiquettes();
            // pas sous une étiquette ni sous la carte (elles prennent le clic)
            if (document.elementFromPoint(x, y) === toile) return [x, y];
          }
        }
      }
      cam.az = ici.az; cam.el = ici.el; demanderRendu();
      return null;
    },
  };
  }
})();
