/* Atelier Boucherie — vue 3D des animaux (Three.js, sans dépendance réseau).
 *
 * Chaque animal est un maillage (data/modeles3d.js) et une « carte des pièces » vue de profil :
 * la couleur d'un point du corps est celle de la pièce qui se trouve à sa hauteur et à sa
 * position le long du corps, exactement comme sur une planche de boucherie. Le même calcul
 * sert à savoir quelle pièce est sous le doigt ou la souris.
 *
 * Mode squelette (bœuf) : os réalistes et muscles en volumes (data/anatomie.js, chargé à la
 * demande). Toucher un os « plonge » dessus : la caméra le centre et tourne autour, les autres os
 * s'estompent et les muscles posés dessus apparaissent. Navigation libre : tourner dans tous les
 * sens, zoomer (molette, pincer), déplacer (clic droit, Maj + glisser, deux doigts).
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

  // ---------- anatomie (os réalistes + muscles), chargée à la demande ----------
  let promesseAnatomie = null;
  function chargerAnatomie() {
    if (window.ANATOMIE) return Promise.resolve(window.ANATOMIE);
    if (!promesseAnatomie) {
      promesseAnatomie = new Promise((ok, ko) => {
        const s = document.createElement("script");
        s.src = "data/anatomie.js";
        s.onload = () => (window.ANATOMIE ? ok(window.ANATOMIE) : ko(new Error("anatomie vide")));
        s.onerror = () => { promesseAnatomie = null; ko(new Error("data/anatomie.js introuvable")); };
        document.head.appendChild(s);
      });
    }
    return promesseAnatomie;
  }

  // Un maillage d'os ou de muscle ; miroir = côté droit (z -> -z, triangles retournés).
  function decoderPiece(e, miroir) {
    const q = new Uint16Array(octets(e.sommets).buffer);
    const [lo, hi] = e.boite;
    const pos = new Float32Array(q.length);
    for (let i = 0; i < q.length; i++) {
      const a = i % 3;
      pos[i] = lo[a] + (q[i] / 65535) * (hi[a] - lo[a]);
      if (miroir && a === 2) pos[i] = -pos[i];
    }
    let idx = new Uint16Array(octets(e.triangles).buffer);
    if (miroir) {
      idx = idx.slice();
      for (let i = 0; i < idx.length; i += 3) { const t = idx[i + 1]; idx[i + 1] = idx[i + 2]; idx[i + 2] = t; }
    }
    const g = new T.BufferGeometry();
    g.setAttribute("position", new T.BufferAttribute(pos, 3));
    g.setIndex(new T.BufferAttribute(idx, 1));
    g.setAttribute("partie", new T.BufferAttribute(e.parties ? Float32Array.from(octets(e.parties)) : new Float32Array(q.length / 3), 1));
    g.setAttribute("ombre", new T.BufferAttribute(e.ombre ? Float32Array.from(octets(e.ombre), (v) => v / 255) : new Float32Array(q.length / 3).fill(1), 1));
    g.computeVertexNormals();
    g.computeBoundingSphere();
    g.computeBoundingBox();
    return g;
  }

  // ---------- matériaux ----------
  // Éclairage commun, réaliste et doux : lumière principale enveloppante, lumière d'appoint, ciel,
  // creux assombris (ombre précalculée), reflet discret. Les lumières suivent la caméra (studio).
  const ECLAIRAGE = `
    vec3 eclairer(vec3 base, vec3 N, vec3 V, float ao, float brille, float durete) {
      vec3 L1 = normalize(vec3(-0.45, 0.8, 0.55));
      vec3 L2 = normalize(vec3(0.7, 0.15, 0.4));
      float n1 = dot(N, L1);
      float w1 = max((n1 + 0.35) / 1.35, 0.0);
      float d2 = max(dot(N, L2), 0.0);
      float ciel = 0.55 + 0.45 * N.y;
      vec3 col = base * (0.34 * ciel * ao + 0.7 * w1 * mix(0.78, 1.0, ao) + 0.13 * d2);
      col += pow(max(dot(N, normalize(L1 + V)), 0.0), durete) * brille * ao;
      col += pow(1.0 - max(dot(N, V), 0.0), 3.0) * 0.07 * vec3(1.0, 0.97, 0.92);
      return col;
    }`;

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
    uniform float selection; uniform float survol; uniform vec3 robe; uniform float transparence;
    varying vec3 vPos; varying vec3 vNormale; varying vec4 vPartie; varying vec3 vVue; varying float vOmbre;
    ${ECLAIRAGE}
    float etiquette(vec2 uv) { return floor(textureLod(carte, uv, 0.0).r * 255.0 + 0.5); }
    float autre(float v, float id) { return step(0.5, v) * step(0.5, abs(v - id)); }
    void main() {
      vec2 uv = vec2((vPos.x - boite.x) * boite.z, (boite.y - vPos.y) * boite.w);
      vec2 dx = dFdx(uv) * 1.3, dy = dFdy(uv) * 1.3;
      float id = etiquette(uv);
      float mp = max(max(vPartie.x, vPartie.y), max(vPartie.z, vPartie.w));
      vec3 coul = robe; float bord = 0.0; float brille = 0.06; float durete = 24.0; float fort = 0.0;
      if (mp > 0.5) {
        if (vPartie.x >= mp) { coul = vec3(0.21, 0.18, 0.17); brille = 0.12; }       // sabot
        else if (vPartie.y >= mp) { coul = vec3(0.9, 0.86, 0.76); brille = 0.1; }    // corne
        else if (vPartie.z >= mp) { coul = robe; }                                   // robe
        else { coul = vec3(0.04, 0.035, 0.035); brille = 0.9; durete = 90.0; }       // œil, brillant
      } else {
        if (id > 0.5) {
          vec4 tc = textureLod(couleurs, vec2((id - 0.5) / ${MAX_PIECES}.0, 0.5), 0.0);
          coul = tc.rgb; fort = tc.a;
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
      float ao = mix(0.6, 1.0, smoothstep(0.15, 0.85, vOmbre));
      vec3 col = eclairer(coul, N, V, ao, brille, durete);
      col = mix(col, vec3(0.97, 0.94, 0.88) * (0.8 + 0.2 * max(dot(N, normalize(vec3(-0.45, 0.8, 0.55))), 0.0)), bord * 0.8);
      if (transparence > 0.999) { gl_FragColor = vec4(col, 1.0); return; }
      // mode squelette : peau translucide, plus présente sur les bords (comme une radio)
      float fres = pow(1.0 - max(dot(N, V), 0.0), 2.2);
      vec3 peau = mix(vec3(0.98, 0.94, 0.9), col, 0.35 + 0.4 * fort);
      gl_FragColor = vec4(peau, mix(transparence, 0.5, fres) + 0.25 * fort);
    }`;

  // Os et muscles : même éclairage, ombre précalculée dans les creux.
  const PIECE_VERTEX = `
    attribute float partie; attribute float ombre;
    varying vec3 vN; varying vec3 vV; varying float vPartie; varying float vOmbre;
    void main() {
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      vN = normalize(normalMatrix * normal); vV = -mv.xyz; vPartie = partie; vOmbre = ombre;
      gl_Position = projectionMatrix * mv;
    }`;
  const OS_FRAGMENT = `
    uniform vec3 teinte; uniform float marque; uniform float opacite;
    varying vec3 vN; varying vec3 vV; varying float vPartie; varying float vOmbre;
    ${ECLAIRAGE}
    void main() {
      vec3 N = normalize(vN); vec3 V = normalize(vV);
      if (!gl_FrontFacing) N = -N;
      vec3 base = teinte;
      if (marque < 0.5) {
        if (vPartie > 1.5) base = vec3(0.97, 0.95, 0.9);          // dent
        else if (vPartie > 0.5) base = vec3(0.74, 0.84, 0.87);    // cartilage, nacré
      }
      float ao = mix(0.42, 1.0, smoothstep(0.08, 0.95, vOmbre));
      vec3 col = eclairer(base, N, V, ao, 0.13, 36.0);
      col = mix(col, col * vec3(1.0, 0.88, 0.74), (1.0 - ao) * 0.55);   // creux plus chauds (os poreux)
      gl_FragColor = vec4(col, opacite);
    }`;
  const MUSCLE_FRAGMENT = `
    uniform vec3 teinte; uniform float opacite; uniform float marque;
    varying vec3 vN; varying vec3 vV; varying float vPartie; varying float vOmbre;
    ${ECLAIRAGE}
    void main() {
      vec3 N = normalize(vN); vec3 V = normalize(vV);
      if (!gl_FrontFacing) N = -N;
      float ao = mix(0.5, 1.0, smoothstep(0.1, 0.95, vOmbre));
      vec3 base = mix(teinte, vec3(1.0, 0.86, 0.45), marque * 0.45);
      vec3 col = eclairer(base, N, V, ao, 0.22, 48.0);                // viande : reflet humide
      col += pow(1.0 - max(dot(N, V), 0.0), 2.5) * 0.12 * vec3(1.0, 0.92, 0.88);  // aponévrose nacrée sur les bords
      gl_FragColor = vec4(col, opacite);
    }`;
  const TEINTES_OS = { normal: "#ecdfc4", survol: "#f8efdb", choisi: "#f2d48c", lie: "#efb08a" };
  // Direction de caméra qui montre le mieux chaque os.
  const VUES_OS = {
    crane: { az: -0.9, el: 0.2 }, coccygiennes: { az: 0.85, el: 0.2 }, sternum: { az: -0.2, el: -0.55 },
    dorsales: { az: 0.1, el: 0.45 }, lombaires: { az: 0.2, el: 0.65 }, sacrum: { az: 0.35, el: 0.7 }, coxal: { az: 0.55, el: 0.45 },
    cotes: { az: -0.15, el: 0.15 }, palette: { az: -0.1, el: 0.2 }, humerus: { az: -0.25, el: 0.1 }, radius: { az: -0.2, el: 0.05 },
    "canon-avant": { az: -0.3, el: 0.1 }, femur: { az: 0.35, el: 0.1 }, rotule: { az: -0.5, el: 0.15 }, tibia: { az: 0.3, el: 0.05 },
    "canon-arriere": { az: 0.3, el: 0.1 }, cervicales: { az: -0.25, el: 0.25 },
  };

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
  const ZOOM = { pieces: [0.8, 3.2], squelette: [0.6, 14] };
  const PROCHE_OS = 1.15;     // plongée : distance minimale caméra -> centre de l'os, en rayons de l'os
  const DECAL_PLONGEE = 0.1;  // plongée : l'os est remonté de 10 % de la hauteur de la vue (au-dessus de la carte)

  // ---------- la vue ----------
  window.Vue3D = function (conteneur, rappels) {
    const rendu = new T.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
    rendu.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    rendu.domElement.className = "toile3d";
    conteneur.appendChild(rendu.domElement);

    const scene = new T.Scene();
    const camera = new T.PerspectiveCamera(28, 1, 0.02, 50);
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
        transparence: { value: 1 },
      },
    });

    // ---------- squelette et muscles ----------
    const mode = { squelette: false, eclate: false, eclat: 0 };
    // voir.muscles : muscles de l'os choisi (plongée) ; voir.tous : toute la viande sur le squelette ;
    // voir.autres : autres os nets (sinon estompés) pendant la plongée
    const voir = { muscles: true, tous: false, autres: false };
    let animEclat = null, anat = null;
    // cote : côté (g / d) de l'os pair sur lequel on plonge ; fixé au choix de l'os, pas selon la caméra
    const etatOs = { selection: null, lies: new Set(), survol: null, survolMuscle: null, cote: "g" };
    const calqueOs = document.createElement("div");
    calqueOs.className = "etiquettes3d os";
    conteneur.appendChild(calqueOs);
    const calqueMuscles = document.createElement("div");
    calqueMuscles.className = "etiquettes3d muscles";
    conteneur.appendChild(calqueMuscles);
    let etiquettesOs = [], etiquettesMuscles = [], couleursMuscles = {};

    function preparerAnatomie() {
      if (!modele || !window.ANATOMIE || !window.ANATOMIE[modele.id]) return null;
      if (modele.anat) return modele.anat;
      const A = window.ANATOMIE[modele.id];
      const groupe = new T.Group();
      const C = new T.Vector3();
      A.os.forEach((e) => C.add(new T.Vector3(...e.centre)));
      C.divideScalar(A.os.length);
      const os = [];
      for (const e of A.os) {
        for (const cote of e.pair ? ["g", "d"] : [""]) {
          const g = decoderPiece(e, cote === "d");
          const m = new T.Mesh(g, new T.ShaderMaterial({
            vertexShader: PIECE_VERTEX, fragmentShader: OS_FRAGMENT,
            uniforms: { teinte: { value: new T.Color(TEINTES_OS.normal) }, marque: { value: 0 }, opacite: { value: 1 } },
          }));
          const c = g.boundingSphere.center.clone();
          const d = c.clone().sub(C);
          const s = cote === "g" ? 1 : cote === "d" ? -1 : 0;
          // vue éclatée : chaque os s'écarte du centre du squelette (les os pairs vers l'extérieur)
          m.userData = { type: "os", id: e.id, cote, centre: c, rayon: g.boundingSphere.radius,
            ecart: new T.Vector3(d.x * 0.6, d.y * 0.5 + (d.y > 0 ? 0.08 : -0.02), d.z * 1.2 + s * 0.32) };
          m.renderOrder = 3;
          groupe.add(m);
          os.push(m);
        }
      }
      const muscles = [];
      for (const e of A.muscles || []) {
        for (const cote of e.pair ? ["g", "d"] : [""]) {
          const g = decoderPiece(e, cote === "d");
          const m = new T.Mesh(g, new T.ShaderMaterial({
            vertexShader: PIECE_VERTEX, fragmentShader: MUSCLE_FRAGMENT, transparent: true,
            uniforms: { teinte: { value: new T.Color("#a63b33") }, opacite: { value: 1 }, marque: { value: 0 } },
          }));
          m.userData = { type: "muscle", id: e.id, pieces: e.pieces, cote, centre: g.boundingSphere.center.clone(), rayon: g.boundingSphere.radius };
          m.visible = false;
          m.renderOrder = 4;
          groupe.add(m);
          muscles.push(m);
        }
      }
      groupe.visible = false;
      scene.add(groupe);
      modele.anat = { groupe, os, muscles };
      return modele.anat;
    }

    // Muscles posés sur l'os choisi : ceux de ses pièces (fiche os.js), du côté de l'os sur lequel on plonge.
    function musclesLies() {
      if (!anat || !etatOs.selection) return [];
      const pieces = new Set(etatOs.lies);
      return anat.muscles.filter((m) => m.userData.pieces.some((p) => pieces.has(p))
        && (m.userData.cote === etatOs.cote || m.userData.cote === ""));
    }
    function coteDe(id) { return Math.cos((VUES_OS[id] || VUES.profil).az) >= 0 ? "g" : "d"; }

    // Maillage de l'os choisi, du côté sur lequel on plonge.
    function maillageOsChoisi() {
      if (!anat || !etatOs.selection) return null;
      const ms = anat.os.filter((x) => x.userData.id === etatOs.selection);
      return ms.find((x) => x.userData.cote === etatOs.cote) || ms.find((x) => x.userData.cote === "") || ms[0] || null;
    }
    // Os pair : celui du côté de la caméra.
    function osVisible(ms) {
      const cote = camera.position.z >= 0 ? "g" : "d";
      return ms.find((m) => m.userData.cote === cote) || ms.find((m) => m.userData.cote === "g") || ms[0];
    }

    function appliquerVisibilite() {
      if (!anat) {
        if (maillage) maillage.visible = true;
        demanderRendu();
        return;
      }
      const sel = etatOs.selection;
      const plonge = mode.squelette && !!sel && !mode.eclate;
      const lies = new Set(plonge && voir.muscles ? musclesLies() : []);
      const tousMuscles = mode.squelette && !sel && voir.tous && !mode.eclate;
      for (const m of anat.os) {
        const id = m.userData.id;
        // en plongée sur un os pair, seul l'os du côté choisi est « l'os choisi » ; son jumeau
        // de l'autre côté redevient un os comme les autres (sinon deux fémurs s'allument)
        const estChoisi = id === sel && (!plonge || m.userData.cote === "" || m.userData.cote === etatOs.cote);
        const t = estChoisi ? "choisi" : id === etatOs.survol ? "survol" : "normal";
        const u = m.material.uniforms;
        u.teinte.value.set(TEINTES_OS[t]);
        u.marque.value = t === "normal" ? 0 : 1;
        const fantome = plonge && !estChoisi && !voir.autres;
        u.opacite.value = fantome ? (id === etatOs.survol ? 0.32 : 0.13) : 1;
        m.material.transparent = fantome;
        m.material.depthWrite = !fantome;
        m.renderOrder = fantome ? 5 : 3;
      }
      for (const m of anat.muscles) {
        const vu = tousMuscles || lies.has(m);
        m.visible = vu;
        if (!vu) continue;
        const u = m.material.uniforms;
        const p = m.userData.pieces[0];
        u.teinte.value.set(couleursMuscles[p] || "#a63b33");
        u.marque.value = etatOs.survolMuscle === m.userData.id ? 1 : 0;
        // plongée : muscles un peu transparents pour garder l'os visible à travers
        u.opacite.value = plonge ? 0.62 : 1;
        m.material.depthWrite = !plonge;
        m.renderOrder = plonge ? 6 : 4;
      }
      // la peau translucide gêne pendant la plongée ou quand les muscles sont montrés
      if (maillage) maillage.visible = !(mode.squelette && (mode.eclate || plonge || tousMuscles));
      demanderRendu();
    }

    function appliquerEclat() {
      if (!anat) return;
      for (const m of anat.os) m.position.copy(m.userData.ecart).multiplyScalar(mode.eclat);
    }

    function appliquerMode() {
      anat = mode.squelette ? preparerAnatomie() : (modele && modele.anat) || null;
      const actif = mode.squelette && !!anat;
      if (modele && modele.anat) modele.anat.groupe.visible = actif;
      materiau.transparent = actif;
      materiau.depthWrite = !actif;
      materiau.uniforms.transparence.value = actif ? 0.08 : 1;
      materiau.needsUpdate = true;
      if (maillage) { maillage.renderOrder = actif ? 7 : 0; maillage.visible = true; }
      if (yeux) yeux.visible = !actif;
      // squelette : on peut passer dessous et pincer pour zoomer, la page ne défile plus sous le doigt
      rendu.domElement.style.touchAction = actif ? "none" : "";
      calque.hidden = actif || !nomsVisibles;
      calqueOs.hidden = !actif || !nomsVisibles;
      appliquerVisibilite();
    }

    function preparerEtiquettesOs(nomsOs) {
      calqueOs.textContent = "";
      etiquettesOs = [];
      if (!anat) return;
      const vus = new Set();
      for (const m of anat.os) {
        const id = m.userData.id;
        if (vus.has(id)) continue;
        vus.add(id);
        const el = document.createElement("span");
        el.textContent = nomsOs[id] || id;
        el.dataset.os = id;
        calqueOs.appendChild(el);
        etiquettesOs.push({ id, el, largeur: 0, maillages: anat.os.filter((x) => x.userData.id === id) });
      }
    }
    function preparerEtiquettesMuscles(noms) {
      calqueMuscles.textContent = "";
      etiquettesMuscles = [];
      if (!anat) return;
      for (const m of anat.muscles) {
        const el = document.createElement("span");
        el.textContent = noms[m.userData.pieces[0]] || m.userData.id;
        el.dataset.muscle = m.userData.id;
        calqueMuscles.appendChild(el);
        etiquettesMuscles.push({ m, el, largeur: 0 });
      }
    }

    let maillage = null, modele = null, dernierEtat = null, yeux = null;
    const noirOeil = new T.MeshBasicMaterial({ color: 0x17110f });
    // decal : l'image est remontée de cette fraction de la hauteur de la vue (plongée : l'os choisi reste
    // au-dessus de la carte du bas) ; c'est un décalage d'ÉCRAN, donc la vue tourne et zoome toujours
    // autour du centre (l'os), et l'os ne file pas vers le bord quand on zoome.
    const cam = { az: VUE_DEPART.az, el: VUE_DEPART.el, zoom: 1, centre: new T.Vector3(), base: 5, decal: 0 };
    const centreCorps = new T.Vector3();   // centre de l'animal entier (la caméra y revient hors plongée)
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
        if (!anim.libre) {
          cam.az = anim.de.az + (anim.vers.az - anim.de.az) * e;
          cam.el = anim.de.el + (anim.vers.el - anim.de.el) * e;
          cam.zoom = anim.de.zoom * Math.pow(anim.vers.zoom / anim.de.zoom, e);
        }
        if (anim.vers.centre) cam.centre.lerpVectors(anim.de.centre, anim.vers.centre, e);
        cam.decal = anim.de.decal + (anim.vers.decal - anim.de.decal) * e;
        if (k >= 1) anim = null; else demanderRendu();
      }
      if (animEclat) {
        const k = Math.min(1, (t - (animEclat.debut ??= t)) / 700);
        const e = k < 0.5 ? 2 * k * k : 1 - Math.pow(-2 * k + 2, 2) / 2;
        mode.eclat = animEclat.de + (animEclat.vers - animEclat.de) * e;
        appliquerEclat();
        if (k >= 1) {
          animEclat = null;
          appliquerVisibilite();
        } else demanderRendu();
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
      camera.near = Math.max(0.01, d * 0.02);
      const W = conteneur.clientWidth, H = conteneur.clientHeight;
      if (cam.decal && W && H) camera.setViewOffset(W, H, 0, cam.decal * H, W, H);
      else camera.clearViewOffset();
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
    // Place une étiquette en (x, y) si elle ne chevauche aucune autre déjà placée.
    function poser(e, point, places, W, H, actif) {
      v3.copy(point).project(camera);
      const x = ((v3.x + 1) / 2) * W, y = ((1 - v3.y) / 2) * H;
      if (!e.largeur) e.largeur = e.el.offsetWidth || e.el.textContent.length * 6.5 + 6;
      const w = e.largeur / 2 + 2, h = 9;
      const visible = v3.z < 1 && x - w > 0 && x + w < W && y - h > 0 && y + h < H
        && !places.some((b) => x - w < b[2] && x + w > b[0] && y - h < b[3] && y + h > b[1]);
      if (visible) places.push([x - w, y - h, x + w, y + h]);
      e.el.style.visibility = visible ? "visible" : "hidden";
      if (visible) e.el.style.transform = "translate(" + (x - e.largeur / 2).toFixed(1) + "px, " + (y - 8).toFixed(1) + "px)";
      e.el.classList.toggle("actif", !!actif);
    }
    function placerEtiquettesOs() {
      const W = conteneur.clientWidth, H = conteneur.clientHeight;
      const places = [];
      const sel = etatOs.selection;
      const plonge = sel && !mode.eclate;
      const ordre = sel ? [...etiquettesOs.filter((e) => e.id === sel), ...etiquettesOs.filter((e) => e.id !== sel)] : etiquettesOs;
      // pendant la plongée : le nom de l'os choisi, puis ceux des muscles ; les autres os se taisent
      const coteCamera = camera.position.z >= 0 ? "g" : "d";
      const muscles = etiquettesMuscles.filter((e) => e.m.visible && (plonge || e.m.userData.cote !== (coteCamera === "g" ? "d" : "g")));
      const viande = !sel && voir.tous && !mode.eclate;
      for (const e of ordre) {
        if ((plonge && e.id !== sel && !voir.autres) || viande) { e.el.style.visibility = "hidden"; continue; }
        const m = plonge && e.id === sel ? (e.maillages.find((x) => x.userData.cote === etatOs.cote) || e.maillages[0]) : osVisible(e.maillages);
        poser(e, v3.copy(m.userData.centre).add(m.position), places, W, H, e.id === sel);
      }
      calqueMuscles.hidden = !muscles.length;
      for (const e of etiquettesMuscles) if (!muscles.includes(e)) e.el.style.visibility = "hidden";
      for (const e of muscles) poser(e, e.m.userData.centre, places, W, H, e.m.userData.id === etatOs.survolMuscle);
    }
    function placerEtiquettes() {
      const osActif = mode.squelette && !!anat;
      calque.hidden = osActif || !nomsVisibles;
      calqueOs.hidden = !osActif || !nomsVisibles;
      calqueMuscles.hidden = !osActif || !nomsVisibles;
      if (!nomsVisibles) return;
      if (osActif) { placerEtiquettesOs(); return; }
      if (!etiquettes.length) return;
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
        if (!meilleur || (seulement && !seulement.has(e.piece))) {
          e.el.style.visibility = "hidden";
          e.el.classList.toggle("actif", e.piece === sel);
          continue;
        }
        poser(e, meilleur, places, W, H, e.piece === sel);
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

    function plongee() { return mode.squelette && !!etatOs.selection && !mode.eclate; }
    // En plongée, on peut s'approcher de l'os choisi jusqu'à 1,15 fois son rayon (presque contre sa surface),
    // quelle que soit sa taille : la rotule se zoome autant que le bassin.
    function bornesZoom() {
      if (!mode.squelette) return ZOOM.pieces;
      const m = plongee() ? maillageOsChoisi() : null;
      return m ? [ZOOM.squelette[0], Math.max(ZOOM.squelette[1], cam.base / (PROCHE_OS * m.userData.rayon))] : ZOOM.squelette;
    }
    function bornerEl(el) { return mode.squelette ? Math.max(-1.45, Math.min(1.45, el)) : Math.max(-0.15, Math.min(1.35, el)); }

    function aller(vers, duree = 450) {
      const [zmin, zmax] = bornesZoom();
      const vise = anim && !anim.libre ? anim.vers : cam;
      const cible = { az: vers.az ?? vise.az, el: vers.el ?? vise.el, zoom: Math.max(zmin, Math.min(zmax, vers.zoom ?? vise.zoom)) };
      // tourner par le chemin le plus court
      while (cible.az - cam.az > Math.PI) cible.az -= 2 * Math.PI;
      while (cible.az - cam.az < -Math.PI) cible.az += 2 * Math.PI;
      const centre = vers.centre || (anim && anim.vers.centre);
      if (centre) cible.centre = centre.clone();
      cible.decal = vers.decal ?? (vers.centre === centreCorps ? 0 : anim ? anim.vers.decal : cam.decal);
      if (!duree) {
        cam.az = cible.az; cam.el = cible.el; cam.zoom = cible.zoom; cam.decal = cible.decal;
        if (cible.centre) cam.centre.copy(cible.centre);
        anim = null;
      } else anim = { de: { az: cam.az, el: cam.el, zoom: cam.zoom, centre: cam.centre.clone(), decal: cam.decal }, vers: cible, duree };
      demanderRendu();
    }

    // Déplacer la vue (glisser à deux doigts, clic droit) : le centre suit le doigt dans le plan de l'écran.
    function panner(dx, dy) {
      const d = cam.base / cam.zoom;
      const parPixel = (2 * d * Math.tan(T.MathUtils.degToRad(camera.fov) / 2)) / Math.max(1, conteneur.clientHeight);
      placerCamera();
      const droite = new T.Vector3().setFromMatrixColumn(camera.matrixWorld, 0);
      const haut = new T.Vector3().setFromMatrixColumn(camera.matrixWorld, 1);
      cam.centre.addScaledVector(droite, -dx * parPixel).addScaledVector(haut, dy * parPixel);
      demanderRendu();
    }

    // ---------- quelle pièce est sous ce point de l'écran ? ----------
    const lanceur = new T.Raycaster();
    const souris = new T.Vector2();
    function rayon(clientX, clientY) {
      const r = rendu.domElement.getBoundingClientRect();
      souris.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
      placerCamera();
      camera.updateMatrixWorld();
      lanceur.setFromCamera(souris, camera);
    }
    function toucher(clientX, clientY) {
      if (!maillage) return null;
      rayon(clientX, clientY);
      const h = lanceur.intersectObject(maillage, false)[0];
      if (!h) return null;
      const f = h.face;
      const neutres = (modele.codes[f.a] > 0) + (modele.codes[f.b] > 0) + (modele.codes[f.c] > 0);
      if (neutres >= 2) return null;
      const e = modele.etiquette(h.point.x, h.point.y);
      return e >= 0 ? { piece: modele.pieces[e], point: h.point } : null;
    }
    // Os ou muscle sous le doigt (squelette) : les muscles visibles d'abord, sauf un os net devant eux.
    function toucherAnatomie(clientX, clientY) {
      if (!mode.squelette || !anat) return null;
      rayon(clientX, clientY);
      const cibles = [...anat.os, ...anat.muscles.filter((m) => m.visible)];
      const hs = lanceur.intersectObjects(cibles, false);
      if (!hs.length) return null;
      // un os estompé ne masque pas un muscle visible derrière lui
      const premierNet = hs.find((h) => h.object.userData.type === "muscle" || h.object.material.uniforms.opacite.value > 0.5);
      const h = premierNet || hs[0];
      return { type: h.object.userData.type, id: h.object.userData.id, objet: h.object };
    }
    function viser(x, y) {
      const a = toucherAnatomie(x, y);
      if (a && a.type === "os") return { type: "os", id: a.id };
      if (a && a.type === "muscle") return { type: "muscle", id: a.id, piece: a.objet.userData.pieces[0] };
      if (mode.squelette) return null;  // en mode squelette, seuls os et muscles réagissent (un clic raté ne quitte pas le squelette)
      const p = toucher(x, y);
      return p ? { type: "piece", id: p.piece } : null;
    }

    // ---------- souris et doigts ----------
    const toile = rendu.domElement;
    const pointeurs = new Map();
    let appui = null, geste = null;
    toile.addEventListener("contextmenu", (e) => e.preventDefault());
    toile.addEventListener("pointerdown", (e) => {
      pointeurs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      toile.setPointerCapture(e.pointerId);
      if (anim) anim.libre = true;   // l'angle et le zoom sont au doigt ; le centrage sur l'os se termine
      if (pointeurs.size === 1) {
        appui = { x: e.clientX, y: e.clientY, t: performance.now(), az: cam.az, el: cam.el, glisse: false, type: e.pointerType,
          deplacer: e.button === 2 || e.button === 1 || e.shiftKey, dernier: { x: e.clientX, y: e.clientY } };
      } else if (pointeurs.size === 2) {
        // deux doigts : pincer = zoomer, glisser = déplacer (jamais un clic)
        const [a, b] = [...pointeurs.values()];
        geste = { dist: Math.hypot(a.x - b.x, a.y - b.y) || 1, zoom: cam.zoom, mx: (a.x + b.x) / 2, my: (a.y + b.y) / 2 };
        if (appui) appui.glisse = true;
      }
    });
    toile.addEventListener("pointermove", (e) => {
      if (pointeurs.has(e.pointerId)) pointeurs.set(e.pointerId, { x: e.clientX, y: e.clientY });
      if (geste && pointeurs.size >= 2) {
        const [a, b] = [...pointeurs.values()];
        const [zmin, zmax] = bornesZoom();
        cam.zoom = Math.max(zmin, Math.min(zmax, geste.zoom * (Math.hypot(a.x - b.x, a.y - b.y) / geste.dist)));
        const mx = (a.x + b.x) / 2, my = (a.y + b.y) / 2;
        // en plongée, pincer ne déplace pas la vue : on reste centré sur l'os pour en faire le tour
        if (!plongee()) panner(mx - geste.mx, my - geste.my);
        geste.mx = mx; geste.my = my;
        demanderRendu();
        return;
      }
      if (appui) {
        const dx = e.clientX - appui.x, dy = e.clientY - appui.y;
        if (!appui.glisse && Math.hypot(dx, dy) > 6) { appui.glisse = true; survoler(null); }
        if (appui.glisse) {
          if (appui.deplacer) {
            panner(e.clientX - appui.dernier.x, e.clientY - appui.dernier.y);
          } else {
            cam.az = appui.az - dx * 0.009;
            // souris : haut / bas aussi ; doigt : en mode squelette seulement (sinon la page défile)
            if (appui.type === "mouse" || mode.squelette) cam.el = bornerEl(appui.el + dy * 0.006);
          }
          appui.dernier = { x: e.clientX, y: e.clientY };
          demanderRendu();
        }
        return;
      }
      if (e.pointerType !== "mouse") return;
      survoler(viser(e.clientX, e.clientY), e.clientX, e.clientY);
    });
    const fin = (e) => {
      pointeurs.delete(e.pointerId);
      if (pointeurs.size < 2 && geste) {
        geste = null;
        // il reste un doigt après un pincement : il reprend la rotation depuis là où on en est
        const [r] = [...pointeurs.values()];
        if (r && appui) Object.assign(appui, { x: r.x, y: r.y, az: cam.az, el: cam.el, glisse: true, dernier: { ...r } });
      }
      if (!appui || pointeurs.size) return;
      const clic = !appui.glisse && performance.now() - appui.t < 800;
      appui = null;
      if (clic && e.type === "pointerup") {
        const v = viser(e.clientX, e.clientY);
        if (v && v.type === "os") rappels.surClicOs(v.id);
        else if (v && v.type === "muscle") rappels.surClic(v.piece);
        else if (v) rappels.surClic(v.id);
      }
    };
    toile.addEventListener("pointerup", fin);
    toile.addEventListener("pointercancel", fin);
    toile.addEventListener("pointerleave", () => { if (!appui) survoler(null); });
    toile.addEventListener("wheel", (e) => {
      e.preventDefault();
      if (anim) anim.libre = true;
      const [zmin, zmax] = bornesZoom();
      cam.zoom = Math.max(zmin, Math.min(zmax, cam.zoom * Math.exp(-e.deltaY * 0.0012)));
      demanderRendu();
    }, { passive: false });

    let survolActuel = null;
    function survoler(cible, x, y) {
      const cle = cible ? cible.type + ":" + cible.id : null;
      if (cle !== survolActuel) {
        survolActuel = cle;
        const piece = cible && cible.type === "piece" ? cible.id : null;
        materiau.uniforms.survol.value = piece ? modele.pieces.indexOf(piece) + 1 : 0;
        etatOs.survol = cible && cible.type === "os" ? cible.id : null;
        etatOs.survolMuscle = cible && cible.type === "muscle" ? cible.id : null;
        appliquerVisibilite();
        toile.style.cursor = cible ? "pointer" : "grab";
        demanderRendu();
      }
      rappels.surSurvol(cible && cible.type === "muscle" ? { type: "piece", id: cible.piece } : cible, x, y);
    }

    // Point de l'écran où un maillage est touché en premier (pour les tests) : on essaie plusieurs vues.
    function pointSur(maillages, accepte, vues) {
      const r = toile.getBoundingClientRect();
      for (const vue of vues) {
        aller(vue, 0);
        placerCamera();
        camera.updateMatrixWorld();
        for (const m of maillages) {
          const pos = m.geometry.getAttribute("position");
          const pas = Math.max(1, Math.floor(pos.count / 80));
          for (let i = 0; i < pos.count; i += pas) {
            const p = new T.Vector3().fromBufferAttribute(pos, i).add(m.position).project(camera);
            const x = r.left + ((p.x + 1) / 2) * r.width, y = r.top + ((1 - p.y) / 2) * r.height;
            if (x < r.left + 4 || x > r.right - 4 || y < r.top + 4 || y > r.bottom - 4) continue;
            if ([[0, 0], [3, 0], [-3, 0], [0, 3], [0, -3]].every(([dx, dy]) => accepte(viser(x + dx, y + dy)))) return [x, y];
          }
        }
      }
      return null;
    }

    // ---------- API ----------
    const api = {
      afficher(animalId, noms = {}) {
        if (modele && modele.id === animalId) return;
        modele = cache[animalId] ||= preparer(animalId);
        if (maillage) scene.remove(maillage);
        if (anat) anat.groupe.visible = false;
        anat = null;
        mode.squelette = false; mode.eclate = false; mode.eclat = 0; animEclat = null;
        etatOs.selection = null;
        maillage = new T.Mesh(modele.geometrie, materiau);
        scene.add(maillage);
        // yeux : bille sombre et brillante (sans gros reflet blanc de dessin animé)
        if (yeux) scene.remove(yeux);
        yeux = new T.Group();
        for (const [x, y, z, r] of modele.m.yeux || []) {
          const o = new T.Mesh(new T.SphereGeometry(r * 0.9, 20, 14), noirOeil);
          o.position.set(x, y, z);
          const reflet = new T.Mesh(new T.SphereGeometry(r * 0.16, 8, 6), new T.MeshBasicMaterial({ color: 0xf2efe9 }));
          reflet.position.set(x - r * 0.3, y + r * 0.35, z + Math.sign(z) * r * 0.78);
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
        centreCorps.copy(cam.centre);
        sol.scale.set((b.max.x - b.min.x) * 1.15, (b.max.z - b.min.z) * 2.2, 1);
        sol.position.set(cam.centre.x, b.min.y + 0.002, 0);
        survolActuel = null;
        materiau.uniforms.survol.value = 0;
        preparerEtiquettes(noms);
        cadrer();
        appliquerMode();
        aller({ ...VUE_DEPART, zoom: 1, centre: centreCorps }, 0);
      },
      // L'anatomie 3D (os réalistes, muscles) de cet animal est-elle chargée ?
      anatomiePrete(animalId) { return !!(window.ANATOMIE && window.ANATOMIE[animalId]); },
      chargerAnatomie,
      aSquelette() { return !!(modele && window.ANATOMIE && window.ANATOMIE[modele.id]); },
      // Montre ou cache le squelette (le corps devient translucide). noms : { os: { id: nom }, pieces: { id: nom } }.
      squelette(oui, nomsOs = {}, nomsPieces = {}) {
        oui = !!oui && api.aSquelette();
        if (oui === mode.squelette) return oui;
        mode.squelette = oui;
        if (!oui) {
          if (mode.eclate) { mode.eclate = false; mode.eclat = 0; animEclat = null; appliquerEclat(); }
          etatOs.selection = null;
          aller({ zoom: Math.min(cam.zoom, ZOOM.pieces[1]), el: bornerEl(cam.el), centre: centreCorps });
        }
        appliquerMode();
        if (oui) { preparerEtiquettesOs(nomsOs); preparerEtiquettesMuscles(nomsPieces); appliquerEclat(); }
        return oui;
      },
      // Vue éclatée : les os s'écartent les uns des autres, puis se rassemblent.
      eclater(oui) {
        oui = !!oui && mode.squelette;
        if (oui === mode.eclate) return oui;
        mode.eclate = oui;
        animEclat = { de: mode.eclat, vers: oui ? 1 : 0 };
        appliquerVisibilite();
        if (oui) aller({ zoom: 0.72, centre: centreCorps }, 600);
        demanderRendu();
        return oui;
      },
      // selection : os choisi ; lies : pièces posées sur cet os (leurs muscles s'affichent)
      etatOs({ selection = null, lies = [] } = {}) {
        if (selection && selection !== etatOs.selection) etatOs.cote = coteDe(selection);
        etatOs.selection = selection;
        etatOs.lies = new Set(lies);
        appliquerVisibilite();
      },
      // muscles : afficher les muscles ; autres : garder les autres os nets pendant la plongée
      voir(options = {}) {
        if ("muscles" in options) voir.muscles = !!options.muscles;
        if ("tous" in options) voir.tous = !!options.tous;
        if ("autres" in options) voir.autres = !!options.autres;
        appliquerVisibilite();
        return { ...voir };
      },
      // Plongée : la caméra se place devant l'os, le centre et le cadre (le zoom dépend de sa taille).
      focaliserOs(id, duree = 650) {
        if (!anat) return;
        const ms = anat.os.filter((x) => x.userData.id === id);
        if (!ms.length) return;
        const vue = VUES_OS[id] || VUES.profil;
        const m = ms.find((x) => x.userData.cote === etatOs.cote) || ms.find((x) => x.userData.cote === "") || ms[0];
        // cadrage sur l'étendue RÉELLE de l'os vue depuis la caméra (sa boîte projetée), pas sur la sphère
        // qui l'englobe : celle-ci est très lâche pour un os long ou plat (côtes, palette, bassin)
        const b = m.geometry.boundingBox || (m.geometry.computeBoundingBox(), m.geometry.boundingBox);
        const c = m.userData.centre.clone().add(m.position);           // pivot : le même centre que partout ailleurs
        const dir = new T.Vector3(Math.cos(vue.el) * Math.sin(vue.az), Math.sin(vue.el), Math.cos(vue.el) * Math.cos(vue.az));
        const droite = new T.Vector3().crossVectors(new T.Vector3(0, 1, 0), dir).normalize();
        const haut = new T.Vector3().crossVectors(dir, droite).normalize();
        let lx = 0, ly = 0, lz = 0;
        for (const sx of [b.min.x, b.max.x]) for (const sy of [b.min.y, b.max.y]) for (const sz of [b.min.z, b.max.z]) {
          const q = new T.Vector3(sx, sy, sz).add(m.position).sub(c);
          lx = Math.max(lx, Math.abs(q.dot(droite))); ly = Math.max(ly, Math.abs(q.dot(haut))); lz = Math.max(lz, Math.abs(q.dot(dir)));
        }
        const demi = Math.tan(T.MathUtils.degToRad(camera.fov) / 2);
        const demiH = demi * camera.aspect;
        // marge 25 % ; la carte du bas cache environ un tiers de la hauteur : on compte la hauteur utile
        const d = Math.max((lx * 1.25) / demiH, (ly * 1.25) / (demi * 0.72)) + lz;
        // le centre de rotation est l'os lui-même ; l'image est remontée (décalage d'écran) pour que l'os
        // apparaisse au-dessus de la carte du bas, à la même place quel que soit le zoom ou l'angle
        aller({ ...vue, zoom: cam.base / Math.max(d, 0.05), centre: c, decal: DECAL_PLONGEE }, duree);
      },
      // Revenir à l'animal entier (hors plongée).
      recadrer(duree = 450) { aller({ ...VUE_DEPART, zoom: 1, centre: centreCorps }, duree); },
      osEn(x, y) { const a = toucherAnatomie(x, y); return a && a.type === "os" ? a.id : null; },
      // Pour les tests : où se trouve à l'écran le centre de l'os choisi (pixels de la page), et à quelle distance.
      ecranOsChoisi() {
        const m = maillageOsChoisi();
        if (!m) return null;
        placerCamera();
        camera.updateMatrixWorld();
        const c = m.userData.centre.clone().add(m.position);
        const p = c.clone().project(camera);
        const r = rendu.domElement.getBoundingClientRect();
        return { x: r.left + ((p.x + 1) / 2) * r.width, y: r.top + ((1 - p.y) / 2) * r.height, devant: p.z < 1,
          vue: [r.left, r.top, r.width, r.height], distance: camera.position.distanceTo(c), rayon: m.userData.rayon, zoom: cam.zoom };
      },
      // Pour les tests : un point de l'écran où l'os est visible et touché en premier.
      pointEcranOs(id) {
        if (!anat) return null;
        const vues = [VUES_OS[id] || VUES.profil, VUES.profil, VUES.avant, VUES.arriere, VUES.dessus, { az: Math.PI, el: 0.1 }]
          .map((v) => ({ ...v, zoom: mode.eclate ? 0.72 : 1, centre: centreCorps }));
        const ms = anat.os.filter((x) => x.userData.id === id);
        return pointSur(ms, (v) => v && v.type === "os" && v.id === id, vues);
      },
      // Pour les tests : un point où le muscle visible est touché en premier (vue actuelle d'abord).
      pointEcranMuscle(id) {
        if (!anat) return null;
        const ms = anat.muscles.filter((x) => x.userData.id === id && x.visible);
        const ici = { az: cam.az, el: cam.el, zoom: cam.zoom, centre: cam.centre.clone() };
        const vues = [ici, { ...ici, az: ici.az + 0.6 }, { ...ici, az: ici.az - 0.6 }, { ...ici, el: 0.8 }, { ...ici, az: ici.az + Math.PI }];
        const pt = pointSur(ms, (v) => v && v.type === "muscle" && v.id === id, vues);
        if (!pt) aller(ici, 0);
        return pt;
      },
      modeCourant() {
        return { squelette: mode.squelette, eclate: mode.eclate, eclat: mode.eclat, os: etatOs.selection, lies: [...etatOs.lies],
          muscles: anat ? [...new Set(anat.muscles.filter((m) => m.visible).map((m) => m.userData.id))] : [],
          autresOsNets: !etatOs.selection || voir.autres, corps: !!(maillage && maillage.visible), viande: voir.tous,
          // os dessinés nets et allumés « os choisi » (un os pair ne doit s'allumer que d'un côté)
          osChoisisNets: anat ? anat.os.filter((m) => m.userData.id === etatOs.selection
            && m.material.uniforms.marque.value > 0 && m.material.uniforms.opacite.value >= 1).length : 0 };
      },
      osAffiches() { return etiquettesOs.filter((e) => nomsVisibles && !calqueOs.hidden && e.el.style.visibility === "visible").map((e) => e.id); },
      musclesAffiches() { return etiquettesMuscles.filter((e) => nomsVisibles && !calqueMuscles.hidden && e.el.style.visibility === "visible").map((e) => e.m.userData.id); },
      // couleurs : { idPiece: "#rrggbb" } ; selection : id de pièce ou null
      // etiquettes : liste des pièces dont on écrit le nom (null = toutes)
      etat({ couleurs, selection, etiquettes: noms = null, forts = [] }) {
        dernierEtat = { couleurs: { ...couleurs }, selection: selection || null, forts: [...forts] };
        couleursMuscles = { ...couleurs };
        seulement = noms ? new Set(noms) : null;
        tamponCouleurs.fill(0);
        modele.pieces.forEach((p, i) => {
          const c = new T.Color(couleurs[p] || NEUTRE);
          tamponCouleurs.set([c.r * 255, c.g * 255, c.b * 255, forts.includes(p) ? 255 : 0], i * 4);
        });
        texCouleurs.needsUpdate = true;
        materiau.uniforms.selection.value = selection ? modele.pieces.indexOf(selection) + 1 : 0;
        appliquerVisibilite();
      },
      noms(oui) { nomsVisibles = !!oui; demanderRendu(); return nomsVisibles; },
      nomsAffiches() {
        return etiquettes.filter((e) => nomsVisibles && e.el.style.visibility === "visible").map((e) => e.piece);
      },
      voisins() { return modele.voisins.map((s) => [...s].map((i) => modele.pieces[i])); },
      // vues : autour de l'os choisi pendant la plongée, sinon autour de l'animal
      vue(nom) {
        const m = plongee() ? maillageOsChoisi() : null;
        const z = anim && !anim.libre ? anim.vers.zoom : cam.zoom;
        aller({ ...(VUES[nom] || VUE_DEPART), zoom: m ? z : Math.min(z, 1.2),
          centre: m ? m.userData.centre.clone().add(m.position) : centreCorps, decal: m ? DECAL_PLONGEE : 0 });
      },
      zoomer(f) {
        const [zmin, zmax] = bornesZoom();
        const z = anim && !anim.libre ? anim.vers.zoom : cam.zoom;
        aller({ zoom: Math.max(zmin, Math.min(zmax, z * f)) }, 250);
      },
      deplacer(dx, dy) { panner(dx, dy); },
      focaliser(piece, duree = 550) {
        const i = modele.pieces.indexOf(piece);
        if (i >= 0) aller({ ...modele.directions[i], zoom: 1, centre: centreCorps }, duree);
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
      orientation() { return { az: cam.az, el: cam.el, zoom: cam.zoom, animal: modele && modele.id, centre: cam.centre.toArray() }; },
      etatCourant() { return dernierEtat; },
    };
    redimensionner();
    return api;
  };
  window.Vue3D.ROBES = ROBES;
  window.Vue3D.chargerAnatomie = chargerAnatomie;
})();
