# Superpose une grille coordonnée sur une image source (aide au placement des zones).
import sys, cv2, numpy as np
src, dst, step, scale = sys.argv[1], sys.argv[2], int(sys.argv[3]), float(sys.argv[4])
im = cv2.imdecode(np.fromfile(src, np.uint8), cv2.IMREAD_UNCHANGED)
if im.ndim == 3 and im.shape[2] == 4:
    a = im[:, :, 3:4] / 255.0
    im = (im[:, :, :3] * a + 255 * (1 - a)).astype(np.uint8)
h, w = im.shape[:2]
big = cv2.resize(im, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_NEAREST)
for x in range(0, w, step):
    cv2.line(big, (int(x * scale), 0), (int(x * scale), big.shape[0]), (255, 160, 0), 1)
    cv2.putText(big, str(x), (int(x * scale) + 2, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 0), 1)
for y in range(0, h, step):
    cv2.line(big, (0, int(y * scale)), (big.shape[1], int(y * scale)), (255, 160, 0), 1)
    cv2.putText(big, str(y), (2, int(y * scale) - 2), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 100, 0), 1)
cv2.imencode('.png', big)[1].tofile(dst)
