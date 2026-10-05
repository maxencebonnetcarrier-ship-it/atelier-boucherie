/* Atelier Boucherie — vue 3D des animaux (Three.js, sans dépendance réseau).
 *
 * Chaque animal est un maillage (data/modeles3d.js) et une « carte des pièces » vue de profil :
 * la couleur d'un point du corps est celle de la pièce qui se trouve à sa hauteur et à sa
 * position le long du corps, exactement comme sur une planche de boucherie. Le même calcul
 * sert à savoir quelle pièce est sous le doigt ou la souris.
 */
(function () {
  "use strict";
  const T = window.THREE;
  const MAX_PIECES = 64;
  const NEUTRE = "#cbbcae";
  // Robe (pelage) de chaque animal, sur ce qui n'est pas une pièce : tête, bas des pattes, oreilles, queue.
  const ROBES = { boeuf: "#a8683f", veau: "#dcc19e", porc: "#efb3ab", agneau: "#ece2d0" };

  // ---------- décodage des données compressées ----------
  function octets(b64) {
    const bin = atob(b64);
    const out = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }
  function plages(b64, n) {
    const b = octets(b64);
    const out = new Uint8Array(n);
    let o = 0;
    for (let i = 0; i < b.length; i += 3) {
      const l = b[i + 1] | (b[i + 2] << 8);
      out.fill(b[i], o, o + l);
      o += l;
    }
    return out;
  }

  function preparer(animalId) {
    const m = window.MODELES3D[animalId];
    const q = new Uint16Array(octets(m.sommets).buffer);
    const [lo, hi] = m.boite;
    const pos = new Float32Array(q.length);
    for (let i = 0; i < q.length; i++) { const a = i % 3; pos[i] = lo[a] + (q[i] / 65535) * (hi[a] - lo[a]); }
    const tri = octets(m.triangles);
    const idx = m.indices32 ? new Uint32Array(tri.buffer) : new Uint16Array(tri.buffer);
    // partie : 1 sabot, 2 corne, 3 robe, 4 œil (0 = suit la carte des pièces)
    const codes = octets(m.parties);
    const partie = new Float32Array(codes.length * 4);
    for (let i = 0; i < codes.length; i++) if (codes[i] > 0) partie[i * 4 + codes[i] - 1] = 1;
    const ombre = new Float32Array(octets(m.ombre)).map((v) => v / 255);

    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.BufferAttribute(pos, 3));
    g.setAttribute("partie", new T.BufferAttribute(partie, 4));
    g.setAttribute("ombre", new T.BufferAttribute(ombre, 1));
    g.setIndex(new T.BufferAttribute(idx, 1));
    g.computeVertexNormals();
    g.computeBoundingBox();
    g.computeBoundingSphere();

    const c = m.carte;
    const carte = plages(c.rle, c.largeur * c.hauteur); // valeur = indice de pièce + 1 (0 = aucune)
    const tex = new T.DataTexture(carte, c.largeur, c.hauteur, T.RedFormat, T.UnsignedByteType);
    tex.magFilter = tex.minFilter = T.NearestFilter;
    tex.unpackAlignment = 1;
    tex.generateMipmaps = false;
    tex.needsUpdate = true;

    const modele = { id: animalId, m, geometrie: g, codes, carte, tex, pieces: m.pieces };
    modele.etiquette = (x, y) => {
      const col = Math.floor(((x - c.x0) / (c.x1 - c.x0)) * c.largeur);
      const lig = Math.floor(((c.y1 - y) / (c.y1 - c.y0)) * c.hauteur);
      if (col < 0 || lig < 0 || col >= c.largeur || lig >= c.hauteur) return -1;
      return carte[lig * c.largeur + col] - 1;
    };
    // Pièces voisines (pour varier les teintes) et direction moyenne de chaque pièce (pour la montrer).
    modele.voisins = voisinage(carte, c.largeur, c.hauteur, m.pieces.length);
    modele.directions = directions(modele, pos, g.getAttribute("normal").array);
    return modele;
  }

  function voisinage(carte, w, h, n) {
    const v = Array.from({ length: n }, () => new Set());
    for (let y = 0; y < h - 1; y += 2) {
      for (let x = 0; x < w - 1; x += 2) {
        const a = carte[y * w + x], b = carte[y * w + x + 2] ?? 0, d = carte[(y + 2) * w + x] ?? 0;
        if (a && b && a !== b) { v[a - 1].add(b - 1); v[b - 1].add(a - 1); }
        if (a && d && a !== d) { v[a - 1].add(d - 1); v[d - 1].add(a - 1); }
      }
    }
    return v;
  }

  function directions(modele, pos, nor) {
    const n = modele.pieces.length;
    const somme = Array.from({ length: n }, () => [0, 0, 0, 0]);
    for (let i = 0; i < pos.length / 3; i++) {
      if (modele.codes[i] || pos[i * 3 + 2] < 0) continue; // côté visible par défaut (z > 0)
      const e = modele.etiquette(pos[i * 3], pos[i * 3 + 1]);
      if (e < 0) continue;
      const s = somme[e];
      s[0] += nor[i * 3]; s[1] += nor[i * 3 + 1]; s[2] += nor[i * 3 + 2]; s[3]++;
    }
    return somme.map(([x, y, z, k]) => {
      if (!k) return { az: 0, el: 0.2 };
      const l = Math.hypot(x, y, z) || 1;
      const el = Math.asin(Math.max(-1, Math.min(1, y / l)));
      return { az: Math.atan2(x, z), el: Math.max(-0.1, Math.min(1.2, el * 0.8 + 0.12)) };
    });
  }

  // ---------- matériau : couleur par pièce + traits de découpe + éclairage studio ----------
  const VERTEX = `
    attribute vec4 partie; attribute float ombre;
    varying vec3 vPos; varying vec3 vNormale; varying vec4 vPartie; varying vec3 vVue; varying float vOmbre;
    void main() {
      vPos = position; vPartie = partie; vOmbre = ombre;
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      vNormale = normalize(normalMatrix * normal);
      vVue = -mv.xyz;
      gl_Position = projectionMatrix * mv;
    }`;
  const FRAGMENT = `
    uniform sampler2D carte; uniform sampler2D couleurs; uniform vec4 boite;
    uniform float selection; uniform float survol; uniform vec3 robe;
    varying vec3 vPos; varying vec3 vNormale; varying vec4 vPartie; varying vec3 vVue; varying float vOmbre;
    float etiquette(vec2 uv) { return floor(textureLod(carte, uv, 0.0).r * 255.0 + 0.5); }
    float autre(float v, float id) { return step(0.5, v) * step(0.5, abs(v - id)); }
    void main() {
      vec2 uv = vec2((vPos.x - boite.x) * boite.z, (boite.y - vPos.y) * boite.w);
      vec2 dx = dFdx(uv) * 1.3, dy = dFdy(uv) * 1.3;
      float id = etiquette(uv);
      float mp = max(max(vPartie.x, vPartie.y), max(vPartie.z, vPartie.w));
      vec3 coul = robe; float bord = 0.0; float brille = 1.0; float durete = 30.0;
      if (mp > 0.5) {
        if (vPartie.x >= mp) { coul = vec3(0.21, 0.18, 0.17); }                 // sabot
        else if (vPartie.y >= mp) { coul = vec3(0.95, 0.91, 0.82); }            // corne
        else if (vPartie.z >= mp) { coul = robe; }                              // robe
        else { coul = vec3(0.04, 0.035, 0.035); brille = 6.0; durete = 90.0; }  // œil
      } else {
        if (id > 0.5) {
          coul = textureLod(couleurs, vec2((id - 0.5) / ${MAX_PIECES}.0, 0.5), 0.0).rgb;
          if (abs(id - survol) < 0.5) coul = mix(coul, vec3(1.0, 0.97, 0.9), 0.3);
          if (abs(id - selection) < 0.5) coul = mix(coul, vec3(1.0, 0.8, 0.2), 0.62);
        }
        // trait de découpe (clair, comme sur une planche) seulement entre deux vraies pièces
        float e = autre(etiquette(uv + dx), id) + autre(etiquette(uv - dx), id)
                + autre(etiquette(uv + dy), id) + autre(etiquette(uv - dy), id);
        bord = min(e, 1.0) * step(0.5, id);
      }
      vec3 N = normalize(vNormale); vec3 V = normalize(vVue);
      if (!gl_FrontFacing) N = -N;
      vec3 L1 = normalize(vec3(-0.45, 0.8, 0.55));
      vec3 L2 = normalize(vec3(0.7, 0.1, 0.35));
      float creux = mix(0.45, 1.0, vOmbre);
      float dif = (max(dot(N, L1), 0.0) * 0.62 + max(dot(N, L2), 0.0) * 0.16) * mix(0.7, 1.0, vOmbre);
      float amb = (0.40 + 0.12 * N.y) * creux;
      float spec = pow(max(dot(N, normalize(L1 + V)), 0.0), durete) * 0.1 * brille * vOmbre;
      float rim = pow(1.0 - max(dot(N, V), 0.0), 3.0) * 0.14 * vOmbre;
      vec3 col = coul * (amb + dif) + spec + rim * vec3(1.0, 0.95, 0.9);
      col = mix(col, vec3(0.98, 0.95, 0.89) * (0.75 + 0.25 * dif), bord * 0.88);
      gl_FragColor = vec4(col, 1.0);
    }`;

  function ombre() {
    const c = document.createElement("canvas");
    c.width = c.height = 128;
    const x = c.getContext("2d");
    const g = x.createRadialGradient(64, 64, 4, 64, 64, 64);
    g.addColorStop(0, "rgba(60,40,30,0.38)");
    g.addColorStop(1, "rgba(60,40,30,0)");
    x.fillStyle = g;
    x.fillRect(0, 0, 128, 128);
    const t = new T.CanvasTexture(c);
    return new T.Mesh(new T.PlaneGeometry(1, 1),
      new T.MeshBasicMaterial({ map: t, transparent: true, depthWrite: false }));
  }

  const VUES = {
    profil: { az: 0, el: 0.1 },
    avant: { az: -0.8, el: 0.28 },
    arriere: { az: 0.85, el: 0.28 },
    dessus: { az: 0, el: 1.25 },
  };
  const VUE_DEPART = { az: -0.42, el: 0.22 };

  // ---------- la vue ----------
  window.Vue3D = function (conteneur, rappels) {
    const rendu = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    rendu.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    rendu.domElement.className = "toile3d";
    conteneur.appendChild(rendu.domElement);

    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(28, 1, 0.1, 50);
    const sol = ombre();
    sol.rotation.x = -Math.PI / 2;
    scene.add(sol);

    // Noms écrits sur les pièces, comme sur une planche (calque HTML au-dessus de la 3D).
    const calque = document.createElement("div");
    calque.className = "etiquettes3d";
    conteneur.appendChild(calque);
    let etiquettes = [], nomsVisibles = true, seulement = null;

    const cache = {};
    const tamponCouleurs = new Uint8Array(MAX_PIECES * 4);
    const texCouleurs = new T.DataTexture(tamponCouleurs, MAX_PIECES, 1, T.RGBAFormat, T.UnsignedByteType);
    texCouleurs.magFilter = texCouleurs.minFilter = T.NearestFilter;
    const neutre = new T.Color(NEUTRE);
    const materiau = new T.ShaderMaterial({
      vertexShader: VERTEX, fragmentShader: FRAGMENT,
      uniforms: {
        carte: { value: null }, couleurs: { value: texCouleurs }, boite: { value: new T.Vector4() },
        selection: { value: 0 }, survol: { value: 0 }, robe: { value: new T.Vector3(neutre.r, neutre.g, neutre.b) },
      },
    });
    let maillage = null, modele = null, dernierEtat = null, yeux = null;
    const noirOeil = new T.MeshBasicMaterial({ color: 0x17110f });
    const blancReflet = new T.MeshBasicMaterial({ color: 0xffffff });
    const cam = { az: VUE_DEPART.az, el: VUE_DEPART.el, zoom: 1, centre: new T.Vector3(), base: 5 };
    let anim = null, prevu = false;

    function demanderRendu() {
      if (prevu) return;
      prevu = true;
      requestAnimationFrame(boucle);
    }
    function boucle(t) {
      prevu = false;
      if (anim) {
        const k = Math.min(1, (t - (anim.debut ??= t)) / anim.duree);
        const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        cam.az = anim.de.az + (anim.vers.az - anim.de.az) * e;
        cam.el = anim.de.el + (anim.vers.el - anim.de.el) * e;
        cam.zoom = anim.de.zoom + (anim.vers.zoom - anim.de.zoom) * e;
        if (k >= 1) anim = null; else demanderRendu();
      }
      placerCamera();
      rendu.render(scene, camera);
      placerEtiquettes();
    }
    function placerCamera() {
      const d = cam.base / cam.zoom;
      camera.position.set(
        cam.centre.x + d * Math.cos(cam.el) * Math.sin(cam.az),
        cam.centre.y + d * Math.sin(cam.el),
        cam.centre.z + d * Math.cos(cam.el) * Math.cos(cam.az));
      camera.lookAt(cam.centre);
    }
    // Un point d'ancrage par pièce et par côté de l'animal : la surface au centre de la pièce.
    function preparerEtiquettes(noms) {
      calque.textContent = "";
      etiquettes = [];
      const lanceurE = new T.Raycaster();
      for (const piece of modele.pieces) {
        const c = modele.m.centres[piece];
        if (!c) continue;
        lanceurE.set(new T.Vector3(c[0], c[1], 5), new T.Vector3(0, 0, -1));
        const h = lanceurE.intersectObject(maillage, false)[0];
        if (!h) continue;
        const n = h.face.normal.clone();
        const el = document.createElement("span");
        el.textContent = noms[piece] || piece;
        el.dataset.piece = piece;
        calque.appendChild(el);
        etiquettes.push({
          piece, el, largeur: 0, aire: modele.m.aires[piece] || 0,
          cotes: [[h.point.clone(), n], [new T.Vector3(h.point.x, h.point.y, -h.point.z), new T.Vector3(n.x, n.y, -n.z)]],
        });
      }
      etiquettes.sort((a, b) => b.aire - a.aire);
    }

    const v3 = new T.Vector3();
    function placerEtiquettes() {
      calque.hidden = !nomsVisibles;
      if (!nomsVisibles || !etiquettes.length) return;
      const W = conteneur.clientWidth, H = conteneur.clientHeight;
      const places = [];
      const sel = dernierEtat && dernierEtat.selection;
      // la pièce choisie passe en premier : son nom n'est jamais caché par un voisin
      const ordre = sel ? [...etiquettes.filter((e) => e.piece === sel), ...etiquettes.filter((e) => e.piece !== sel)] : etiquettes;
      for (const e of ordre) {
        let meilleur = null, score = 0.22;
        for (const [p, n] of e.cotes) {
          v3.copy(camera.position).sub(p).normalize();
          const d = v3.dot(n);
          if (d > score) { score = d; meilleur = p; }
        }
        let visible = !!meilleur && (!seulement || seulement.has(e.piece));
        let x = 0, y = 0;
        if (visible) {
          v3.copy(meilleur).project(camera);
          x = ((v3.x + 1) / 2) * W; y = ((1 - v3.y) / 2) * H;
          if (!e.largeur) e.largeur = e.el.offsetWidth || e.el.textContent.length * 6.5 + 6;
          const w = e.largeur / 2 + 2, h = 9;
          visible = x - w > 0 && x + w < W && y - h > 0 && y + h < H
            && !places.some((b) => x - w < b[2] && x + w > b[0] && y - h < b[3] && y + h > b[1]);
          if (visible) places.push([x - w, y - h, x + w, y + h]);
        }
        e.el.style.visibility = visible ? "visible" : "hidden";
        if (visible) e.el.style.transform = "translate(" + (x - e.largeur / 2).toFixed(1) + "px, " + (y - 8).toFixed(1) + "px)";
        e.el.classList.toggle("actif", e.piece === sel);
      }
    }

    function cadrer() {
      if (!modele) return;
      const b = modele.geometrie.boundingBox;
      const lx = b.max.x - b.min.x, ly = b.max.y - b.min.y, lz = b.max.z - b.min.z;
      const vf = T.MathUtils.degToRad(camera.fov) / 2;
      const hf = Math.atan(Math.tan(vf) * camera.aspect);
      const demi = Math.hypot(lx, lz) / 2;
      cam.base = Math.max(demi / Math.tan(hf), (ly / 2 + 0.06) / Math.tan(vf)) * 0.98 + lz / 2;
    }
    function redimensionner() {
      const w = conteneur.clientWidth, h = conteneur.clientHeight;
      if (!w || !h) return;
      rendu.setSize(w, h, false);
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      cadrer();
      demanderRendu();
    }
    new ResizeObserver(redimensionner).observe(conteneur);

    function aller(vers, duree = 450) {
      const cible = { az: vers.az ?? cam.az, el: vers.el ?? cam.el, zoom: vers.zoom ?? cam.zoom };
      // tourner par le chemin le plus court
      while (cible.az - cam.az > Math.PI) cible.az -= 2 * Math.PI;
      while (cible.az - cam.az < -Math.PI) cible.az += 2 * Math.PI;
      if (!duree) { Object.assign(cam, cible); anim = null; } else anim = { de: { az: cam.az, el: cam.el, zoom: cam.zoom }, vers: cible, duree };
      demanderRendu();
    }

    // ---------- quelle pièce est sous ce point de l'écran ? ----------
    const lanceur = new T.Raycaster();
    const souris = new T.Vector2();
    function toucher(clientX, clientY) {
      if (!maillage) return null;
      const r = rendu.domElement.getBoundingClientRect();
      souris.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
      placerCamera();
      camera.updateMatrixWorld();
      lanceur.setFromCamera(souris, camera);
      const h = lanceur.intersectObject(maillage, false)[0];
      if (!h) return null;
      const f = h.face;
      const neutres = (modele.codes[f.a] > 0) + (modele.codes[f.b] > 0) + (modele.codes[f.c] > 0);
      if (neutres >= 2) return null;
      const e = modele.etiquette(h.point.x, h.point.y);
      return e >= 0 ? { piece: modele.pieces[e], point: h.point } : null;
    }

    // ---------- souris et doigts ----------
    const toile = rendu.domElement;
    let appui = null;
    toile.addEventListener("pointerdown", (e) => {
      appui = { x: e.clientX, y: e.clientY, t: performance.now(), az: cam.az, el: cam.el, glisse: false, type: e.pointerType };
      anim = null;
      toile.setPointerCapture(e.pointerId);
    });
    toile.addEventListener("pointermove", (e) => {
      if (appui) {
        const dx = e.clientX - appui.x, dy = e.clientY - appui.y;
        if (!appui.glisse && Math.hypot(dx, dy) > 6) { appui.glisse = true; survoler(null); }
        if (appui.glisse) {
          cam.az = appui.az - dx * 0.009;
          if (appui.type === "mouse") cam.el = Math.max(-0.15, Math.min(1.35, appui.el + dy * 0.006));
          demanderRendu();
        }
        return;
      }
      if (e.pointerType !== "mouse") return;
      const p = toucher(e.clientX, e.clientY);
      survoler(p && p.piece, e.clientX, e.clientY);
    });
    const fin = (e) => {
      if (!appui) return;
      const clic = !appui.glisse && performance.now() - appui.t < 800;
      appui = null;
      if (clic && e.type === "pointerup") {
        const p = toucher(e.clientX, e.clientY);
        if (p) rappels.surClic(p.piece);
      }
    };
    toile.addEventListener("pointerup", fin);
    toile.addEventListener("pointercancel", fin);
    toile.addEventListener("pointerleave", () => { if (!appui) survoler(null); });
    toile.addEventListener("wheel", (e) => {
      e.preventDefault();
      cam.zoom = Math.max(0.8, Math.min(3.2, cam.zoom * Math.exp(-e.deltaY * 0.0012)));
      demanderRendu();
    }, { passive: false });

    let survolActuel = null;
    function survoler(piece, x, y) {
      if (piece !== survolActuel) {
        survolActuel = piece;
        materiau.uniforms.survol.value = piece ? modele.pieces.indexOf(piece) + 1 : 0;
        toile.style.cursor = piece ? "pointer" : "grab";
        demanderRendu();
      }
      rappels.surSurvol(piece, x, y);
    }

    // ---------- API ----------
    const api = {
      afficher(animalId, noms = {}) {
        if (modele && modele.id === animalId) return;
        modele = cache[animalId] ||= preparer(animalId);
        if (maillage) scene.remove(maillage);
        maillage = new T.Mesh(modele.geometrie, materiau);
        scene.add(maillage);
        // yeux : bille sombre + petit reflet blanc tourné vers la lumière
        if (yeux) scene.remove(yeux);
        yeux = new T.Group();
        for (const [x, y, z, r] of modele.m.yeux || []) {
          const o = new T.Mesh(new T.SphereGeometry(r, 20, 14), noirOeil);
          o.position.set(x, y, z);
          const reflet = new T.Mesh(new T.SphereGeometry(r * 0.32, 10, 8), blancReflet);
          reflet.position.set(x - r * 0.35, y + r * 0.45, z + Math.sign(z) * r * 0.62);
          yeux.add(o, reflet);
        }
        scene.add(yeux);
        const c = modele.m.carte;
        materiau.uniforms.carte.value = modele.tex;
        const robe = new T.Color(ROBES[animalId] || NEUTRE);
        materiau.uniforms.robe.value.set(robe.r, robe.g, robe.b);
        materiau.uniforms.boite.value.set(c.x0, c.y1, 1 / (c.x1 - c.x0), 1 / (c.y1 - c.y0));
        const b = modele.geometrie.boundingBox;
        cam.centre.set((b.min.x + b.max.x) / 2, (b.min.y + b.max.y) / 2 + 0.02, 0);
        sol.scale.set((b.max.x - b.min.x) * 1.15, (b.max.z - b.min.z) * 2.2, 1);
        sol.position.set(cam.centre.x, b.min.y + 0.002, 0);
        survolActuel = null;
        materiau.uniforms.survol.value = 0;
        preparerEtiquettes(noms);
        cadrer();
        aller({ ...VUE_DEPART, zoom: 1 }, 0);
      },
      // couleurs : { idPiece: "#rrggbb" } ; selection : id de pièce ou null
      // etiquettes : liste des pièces dont on écrit le nom (null = toutes)
      etat({ couleurs, selection, etiquettes: noms = null }) {
        dernierEtat = { couleurs: { ...couleurs }, selection: selection || null };
        seulement = noms ? new Set(noms) : null;
        tamponCouleurs.fill(0);
        modele.pieces.forEach((p, i) => {
          const c = new T.Color(couleurs[p] || NEUTRE);
          tamponCouleurs.set([c.r * 255, c.g * 255, c.b * 255, 255], i * 4);
        });
        texCouleurs.needsUpdate = true;
        materiau.uniforms.selection.value = selection ? modele.pieces.indexOf(selection) + 1 : 0;
        demanderRendu();
      },
      noms(oui) { nomsVisibles = !!oui; demanderRendu(); return nomsVisibles; },
      nomsAffiches() {
        return etiquettes.filter((e) => nomsVisibles && e.el.style.visibility === "visible").map((e) => e.piece);
      },
      voisins() { return modele.voisins.map((s) => [...s].map((i) => modele.pieces[i])); },
      vue(nom) { aller(VUES[nom] || VUE_DEPART); },
      zoomer(f) { aller({ zoom: Math.max(0.8, Math.min(3.2, cam.zoom * f)) }, 250); },
      focaliser(piece, duree = 550) {
        const i = modele.pieces.indexOf(piece);
        if (i >= 0) aller({ ...modele.directions[i], zoom: Math.max(cam.zoom, 1) }, duree);
      },
      pieceEn(x, y) { const p = toucher(x, y); return p ? p.piece : null; },
      // Pour les tests : montre la pièce de face et rend un point de l'écran où elle est visible.
      pointEcran(piece) {
        const i = modele.pieces.indexOf(piece);
        const c = modele.m.centres[piece];
        if (i < 0 || !c) return null;
        api.focaliser(piece, 0);
        placerCamera();
        camera.updateMatrixWorld();
        const r = toile.getBoundingClientRect();
        // point de la surface au centre de la pièce, côté caméra
        const depart = new T.Vector3(c[0], c[1], 5), dir = new T.Vector3(0, 0, -1);
        lanceur.set(depart, dir);
        const h = lanceur.intersectObject(maillage, false)[0];
        if (!h) return null;
        const p = h.point.clone().project(camera);
        return [r.left + ((p.x + 1) / 2) * r.width, r.top + ((1 - p.y) / 2) * r.height];
      },
      rendre() { placerCamera(); rendu.render(scene, camera); },
      // Lecture seule, pour les tests : ce qui est réellement affiché.
      orientation() { return { az: cam.az, el: cam.el, zoom: cam.zoom, animal: modele && modele.id }; },
      etatCourant() { return dernierEtat; },
    };
    redimensionner();
    return api;
  };
  window.Vue3D.ROBES = ROBES;
})();
