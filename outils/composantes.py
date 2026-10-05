# Découvre les zones d'une planche : composantes connexes d'un masque "intérieur de zone",
# numérotées sur une image de contrôle. Usage: composantes.py <image> <mode> <sortie.png> [fermeture]
import sys, cv2, numpy as np
src, mode, dst = sys.argv[1], sys.argv[2], sys.argv[3]
close = int(sys.argv[4]) if len(sys.argv) > 4 else 0
im = cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_UNCHANGED)
if im.ndim == 3 and im.shape[2] == 4:
    a = im[:, :, 3:4] / 255.0
    im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
b, g, r = [im[:, :, i].astype(int) for i in range(3)]
if mode == 'rouge':      # zones rouges séparées par traits blancs/noirs
    m = (r - np.maximum(g, b)) > 60
elif mode == 'blanc':    # zones blanches séparées par traits noirs
    m = (np.minimum(np.minimum(r, g), b) > 200) | ((r - np.maximum(g, b)) > 60)
elif mode == 'rose':     # zones roses séparées par pointillés blancs
    m = (r > 200) & (g < 196) & (r - g > 40)
elif mode == 'clair':    # silhouette blanche sur fond noir, pointillés noirs
    m = np.minimum(np.minimum(r, g), b) > 140
m = m.astype(np.uint8)
if close:
    # pointillés : on érode l'intérieur pour fermer les trous entre tirets
    m = cv2.erode(m, np.ones((close, close), np.uint8))
n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=4)
vis = im.copy()
rng = np.random.default_rng(3)
keep = []
for i in range(1, n):
    if st[i, cv2.CC_STAT_AREA] < 120: continue
    keep.append(i)
    col = rng.integers(40, 255, 3)
    vis[lab == i] = (vis[lab == i] * 0.3 + col * 0.7).astype(np.uint8)
scale = 2 if im.shape[1] < 600 else 1.5
vis = cv2.resize(vis, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)
for i in keep:
    # point intérieur le plus éloigné du bord (lisible même pour formes concaves)
    mi = (lab == i).astype(np.uint8)
    d = cv2.distanceTransform(mi, cv2.DIST_L2, 3)
    y, x = np.unravel_index(np.argmax(d), d.shape)
    cv2.putText(vis, str(i), (int(x * scale) - 8, int(y * scale) + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3)
    cv2.putText(vis, str(i), (int(x * scale) - 8, int(y * scale) + 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    print(i, st[i, cv2.CC_STAT_AREA], int(x), int(y))
cv2.imencode('.png', vis)[1].tofile(dst)
