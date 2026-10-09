/* Matériaux « comme le vrai » pour la page atelier (Three.js, shaders maison, sans texture à télécharger).
 *
 * Viande : rouge cerise avec ses FIBRES (fines stries dans le sens du muscle), les liserés blancs des
 * faisceaux, le PERSILLÉ (gras dans le muscle, réglable), la NACRE (peau argentée, l'aponévrose, sur les
 * faces collées à un autre muscle ou à un os : c'est le raccord que suit le couteau) et le GRAS de
 * couverture sur la face extérieure. Gras : blanc crème, légèrement translucide.
 * Os : ivoire veiné, cartilage bleuté et brillant ; face sciée (os coupé au milieu de la carcasse) en os
 * spongieux rosé.
 * Attributs par sommet (0 à 1) : ombre (creux), gras, nacre ; pour les os : partie (code).
 * Éclairage lié à la caméra (une lumière principale en haut à gauche, une de remplissage, un ciel).
 */
(function () {
  const T = window.THREE;

  const BRUIT = `
    float h3(vec3 p) { p = fract(p * 0.3183099 + vec3(0.11, 0.17, 0.13)); p *= 17.0; return fract(p.x * p.y * p.z * (p.x + p.y + p.z)); }
    float bruit(vec3 x) {
      vec3 i = floor(x); vec3 f = fract(x); f = f * f * (3.0 - 2.0 * f);
      return mix(mix(mix(h3(i), h3(i + vec3(1, 0, 0)), f.x), mix(h3(i + vec3(0, 1, 0)), h3(i + vec3(1, 1, 0)), f.x), f.y),
                 mix(mix(h3(i + vec3(0, 0, 1)), h3(i + vec3(1, 0, 1)), f.x), mix(h3(i + vec3(0, 1, 1)), h3(i + vec3(1, 1, 1)), f.x), f.y), f.z);
    }
    float fbm(vec3 p) { float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++) { s += a * bruit(p); p = p * 2.03 + 0.7; a *= 0.5; } return s; }
    vec3 lumiere(vec3 base, vec3 N, vec3 V, float ao, float brillance, float durete) {
      vec3 L1 = normalize(vec3(-0.45, 0.65, 0.62));
      vec3 L2 = normalize(vec3(0.7, -0.15, 0.45));
      float d1 = max(dot(N, L1), 0.0), d2 = max(dot(N, L2), 0.0);
      float ciel = 0.5 + 0.5 * N.y;
      vec3 c = base * (0.24 * mix(0.55, 1.0, ciel) * ao + 0.86 * d1 * mix(0.75, 1.0, ao) + 0.22 * d2 * ao);
      vec3 H = normalize(L1 + V);
      c += vec3(1.0, 0.97, 0.94) * pow(max(dot(N, H), 0.0), durete) * brillance;
      c += vec3(0.95, 0.9, 0.88) * pow(1.0 - max(dot(N, V), 0.0), 3.0) * 0.08 * ao;
      return c;
    }`;

  const SOMMETS = `
    attribute float ombre;
    attribute float gras;
    attribute float nacre;
    attribute float partie;
    varying vec3 vN; varying vec3 vV; varying vec3 vP;
    varying float vO; varying float vG; varying float vA; varying float vPart;
    void main() {
      vec4 mv = modelViewMatrix * vec4(position, 1.0);
      vN = normalize(normalMatrix * normal); vV = -mv.xyz; vP = position;
      vO = ombre; vG = gras; vA = nacre; vPart = partie;
      gl_Position = projectionMatrix * mv;
    }`;

  const VIANDE = `
    uniform vec3 teinte; uniform vec3 fibre; uniform float persille; uniform float marque; uniform float opacite;
    uniform float voirGras; uniform float voirNacre; uniform float survol;
    varying vec3 vN; varying vec3 vV; varying vec3 vP; varying float vO; varying float vG; varying float vA;
    ${BRUIT}
    void main() {
      vec3 N = normalize(vN); if (!gl_FrontFacing) N = -N; vec3 V = normalize(vV);
      vec3 f = normalize(fibre);
      float le = dot(vP, f);
      vec3 q = vP - f * le;
      // fibres : bruit très fin en travers, étiré le long du muscle
      float s = fbm(q * 300.0 + f * le * 14.0);
      float stries = smoothstep(0.32, 0.78, s);
      // faisceaux (périmysium) : fins liserés plus clairs
      float fx = fbm(q * 120.0 + f * le * 5.0 + 3.1);
      float lis = smoothstep(0.62, 0.66, fx) * (1.0 - smoothstep(0.66, 0.7, fx));
      vec3 c = teinte * (0.82 + 0.26 * stries);
      c = mix(c, vec3(0.83, 0.66, 0.58), lis * 0.14);
      // variation de couleur d'un endroit à l'autre (sang, oxygénation)
      c *= 0.92 + 0.14 * fbm(vP * 9.0);
      // persillé : petites veines de gras dans le muscle
      // fines veines étirées dans le sens des fibres
      float m = 0.75 * fbm(q * 120.0 + f * le * 10.0 + 7.3) + 0.25 * fbm(vP * 45.0);
      float pers = smoothstep(0.72 - persille * 0.22, 0.76 - persille * 0.22, m) * step(0.001, persille);
      c = mix(c, vec3(0.91, 0.83, 0.64), pers * 0.85);
      // nacre (aponévrose) sur les faces de raccord
      // voile fin et irrégulier : on voit la viande au travers, il accroche la lumière
      float na = vA * voirNacre;
      float voile = smoothstep(0.35, 0.75, fbm(q * 90.0 + f * le * 18.0));
      c = mix(c, vec3(0.7, 0.72, 0.78), na * (0.03 + 0.13 * voile));
      // sous le gras de couverture : quelques restes de gras sur la face extérieure
      float g = smoothstep(0.5, 0.95, vG) * voirGras * smoothstep(0.55, 0.8, fbm(vP * 30.0));
      vec3 grasC = vec3(0.88, 0.75, 0.49) * (0.9 + 0.14 * fbm(vP * 55.0));
      c = mix(c, grasC, g * 0.8);
      float brille = 0.14 + na * (0.12 + 0.22 * voile) + g * 0.08;
      vec3 col = lumiere(c, N, V, mix(0.45, 1.0, vO), brille, 42.0 + na * 30.0);
      col = mix(col, col * 1.18 + vec3(0.1, 0.07, 0.0), survol * 0.6);
      // choisi : un liseré doré sur le contour, la viande reste visible
      float bord = pow(1.0 - max(dot(N, V), 0.0), 2.5);
      col = mix(col, vec3(1.0, 0.62, 0.05), marque * 0.75 * bord) + marque * 0.04;
      gl_FragColor = linearToOutputTexel(vec4(col, opacite));
    }`;

  const GRAS = `
    uniform float marque; uniform float opacite; uniform float survol;
    varying vec3 vN; varying vec3 vV; varying vec3 vP; varying float vO;
    ${BRUIT}
    void main() {
      vec3 N = normalize(vN); if (!gl_FrontFacing) N = -N; vec3 V = normalize(vV);
      vec3 c = vec3(0.88, 0.77, 0.5) * (0.88 + 0.16 * fbm(vP * 48.0)) - vec3(0.0, 0.02, 0.05) * fbm(vP * 9.0);
      vec3 col = lumiere(c, N, V, mix(0.55, 1.0, vO), 0.22, 30.0);
      col = mix(col, col * 1.12, survol * 0.6);
      col = mix(col, vec3(1.0, 0.68, 0.07), marque * 0.3);
      gl_FragColor = linearToOutputTexel(vec4(col, opacite));
    }`;

  const OS = `
    uniform vec3 teinte; uniform float marque; uniform float opacite; uniform float voirParties; uniform float coupeZ;
    uniform vec3 p3; uniform vec3 p4; uniform vec3 p5; uniform float survol;
    varying vec3 vN; varying vec3 vV; varying vec3 vP; varying float vO; varying float vPart;
    ${BRUIT}
    void main() {
      if (vP.z < coupeZ) discard;
      vec3 V = normalize(vV);
      if (!gl_FrontFacing) {
        // face sciée : os spongieux, moelle rosée
        float a = fbm(vP * 260.0);
        vec3 c = mix(vec3(0.57, 0.27, 0.19), vec3(0.85, 0.69, 0.48), smoothstep(0.4, 0.62, a));
        gl_FragColor = linearToOutputTexel(vec4(c * 0.92, opacite));
        return;
      }
      vec3 N = normalize(vN);
      vec3 c = teinte * (0.9 + 0.12 * fbm(vP * 18.0)) - vec3(0.02, 0.03, 0.05) * fbm(vP * 70.0 + 2.0);
      // veinules et petits trous des vaisseaux
      float v = fbm(vP * 140.0);
      c *= 1.0 - 0.1 * smoothstep(0.7, 0.78, v);
      float brille = 0.1;
      float durete = 24.0;
      if (vPart > 0.5 && vPart < 1.5) { c = vec3(0.66, 0.78, 0.85); brille = 0.45; durete = 70.0; }      // cartilage
      else if (vPart > 1.5 && vPart < 2.5) { c = vec3(0.91, 0.87, 0.71); brille = 0.4; durete = 60.0; }  // dent
      else if (voirParties > 0.5 && vPart > 2.5) {
        vec3 pc = vPart < 3.5 ? p3 : (vPart < 4.5 ? p4 : p5);
        c = mix(c, pc, 0.55);
      }
      vec3 col = lumiere(c, N, V, mix(0.45, 1.0, vO), brille, durete);
      col = mix(col, col * 1.12 + vec3(0.08, 0.06, 0.0), survol * 0.6);
      float bord = pow(1.0 - max(dot(N, V), 0.0), 2.5);
      col = mix(col, vec3(1.0, 0.6, 0.03), marque * 0.75 * bord) + marque * 0.04;
      gl_FragColor = linearToOutputTexel(vec4(col, opacite));
    }`;

  function couleur(c) { return new T.Color(c); }

  window.Materiaux3D = {
    viande({ teinte = "#b0302b", persille = 0.05, fibre = [0, 1, 0] } = {}) {
      return new T.ShaderMaterial({
        vertexShader: SOMMETS, fragmentShader: VIANDE,
        uniforms: {
          teinte: { value: couleur(teinte) }, fibre: { value: new T.Vector3(...fibre) }, persille: { value: persille },
          marque: { value: 0 }, opacite: { value: 1 }, voirGras: { value: 1 }, voirNacre: { value: 1 }, survol: { value: 0 },
        },
      });
    },
    gras() {
      return new T.ShaderMaterial({
        vertexShader: SOMMETS, fragmentShader: GRAS,
        uniforms: { marque: { value: 0 }, opacite: { value: 1 }, survol: { value: 0 } },
      });
    },
    os({ teinte = "#e8dcc1", couleursParties = ["#d9b45a", "#6fa5c8", "#9bbf6a"], coupeZ = -10 } = {}) {
      return new T.ShaderMaterial({
        // face arrière visible seulement pour un os scié (le sacrum, coupé au milieu de la carcasse)
        vertexShader: SOMMETS, fragmentShader: OS, side: coupeZ > -1 ? T.DoubleSide : T.FrontSide,
        uniforms: {
          teinte: { value: couleur(teinte) }, marque: { value: 0 }, opacite: { value: 1 }, voirParties: { value: 0 },
          coupeZ: { value: coupeZ }, survol: { value: 0 },
          p3: { value: couleur(couleursParties[0]) }, p4: { value: couleur(couleursParties[1]) }, p5: { value: couleur(couleursParties[2]) },
        },
      });
    },
  };
})();
