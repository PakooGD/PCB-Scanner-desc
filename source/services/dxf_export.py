"""
Сборка мозаики из снимков и экспорт контуров в DXF.

Идея:
  1. Все PNG из папки склеиваются в одно большое изображение (мозаика).
  2. Из мозаики выделяются контуры (Canny + findContours).
  3. (Опционально) перед findContours применяется скелетизация —
     тонкие линии дорожек становятся одиночными центральными линиями.
  4. Контуры упрощаются (approxPolyDP) и сохраняются как LWPOLYLINE в DXF.
  5. Опционально сохраняется превью мозаики и отладочная маска.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Callable

import cv2
import numpy as np
import ezdxf

from source.i18n import t


# ============================================================
#  Разбор имени файла → (row, col)
# ============================================================
_RX_COORDS = re.compile(r"r(\d+)_c(\d+)", re.IGNORECASE)
_RX_SEQ    = re.compile(r"^(\d+)", re.IGNORECASE)


def _parse_grid_index(filename: str) -> Optional[Tuple[int, int]]:
    """Возвращает (row, col) или None, если имя не распознано."""
    m = _RX_COORDS.search(filename)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = _RX_SEQ.match(Path(filename).stem)
    if m:
        return -1, int(m.group(1))  # последовательный режим: row неизвестен
    return None


def collect_images(folder: Path,
                   naming: str = "auto") -> List[Tuple[Path, Optional[Tuple[int, int]]]]:
    """
    Возвращает список (путь, (row, col) | None).
    naming: "auto" | "coords" | "seq"
    """
    files = sorted([p for p in folder.iterdir()
                    if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".bmp")])
    result = []
    for p in files:
        rc = _parse_grid_index(p.name)
        if naming == "coords" and (rc is None or rc[0] < 0):
            continue
        if naming == "seq" and (rc is None or rc[0] != -1):
            continue
        result.append((p, rc))
    return result


# ============================================================
#  Мозаика
# ============================================================
def build_mosaic(files: List[Tuple[Path, Optional[Tuple[int, int]]]],
                 cols_override: Optional[int] = None,
                 overlap_px: int = 0) -> Tuple[Optional[np.ndarray], Dict]:
    """
    Склеивает изображения в мозаику.
    Возвращает (image, info).
    """
    if not files:
        return None, {"rows": 0, "cols": 0, "tiles": []}

    imgs = []
    for p, rc in files:
        img = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if img is None:
            continue
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        elif img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        imgs.append((p, rc, img))

    if not imgs:
        return None, {"rows": 0, "cols": 0, "tiles": []}

    have_coords = all(rc is not None and rc[0] >= 0 for _, rc, _ in imgs)

    h = max(im.shape[0] for _, _, im in imgs)
    w = max(im.shape[1] for _, _, im in imgs)

    if have_coords:
        rows = max(rc[0] for _, rc, _ in imgs) + 1
        cols = max(rc[1] for _, rc, _ in imgs) + 1
        placement = [(rc[0], rc[1], im) for _, rc, im in imgs]
    else:
        n = len(imgs)
        if cols_override and cols_override > 0:
            cols = cols_override
        else:
            cols = max(1, int(n ** 0.5) or 1)
        rows = (n + cols - 1) // cols
        placement = [(i // cols, i % cols, im) for i, (_, _, im) in enumerate(imgs)]

    tile_w = w - overlap_px
    tile_h = h - overlap_px
    if tile_w <= 0 or tile_h <= 0:
        tile_w, tile_h = w, h
        overlap_px = 0

    canvas_w = cols * tile_w + overlap_px
    canvas_h = rows * tile_h + overlap_px
    canvas = np.zeros((canvas_h, canvas_w, 3), dtype=np.uint8)

    for r, c, im in placement:
        y0 = r * tile_h
        x0 = c * tile_w
        canvas[y0:y0 + im.shape[0], x0:x0 + im.shape[1]] = im

    info = {
        "rows": rows,
        "cols": cols,
        "tile_w": w,
        "tile_h": h,
        "overlap_px": overlap_px,
        "tiles": [str(p) for p, _, _ in imgs],
    }
    return canvas, info


# ============================================================
#  Скелетизация + очистка
# ============================================================
def _skeletonize_thinning(binary: np.ndarray) -> np.ndarray:
    """Zhang-Suen из opencv-contrib."""
    return cv2.ximgproc.thinning(binary,
                                 thinningType=cv2.ximgproc.THINNING_ZHANGSUEN)


def _skeletonize_morph(binary: np.ndarray, max_iter: int = 50) -> np.ndarray:
    """Fallback: морфологическое утоньшение без contrib."""
    img = binary.copy()
    skel = np.zeros_like(img)
    element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    for _ in range(max_iter):
        eroded = cv2.erode(img, element)
        temp = cv2.dilate(eroded, element)
        temp = cv2.subtract(img, temp)
        skel = cv2.bitwise_or(skel, temp)
        img = eroded
        if cv2.countNonZero(img) == 0:
            break
    return skel


def _prune_skeleton(skel: np.ndarray, min_branch_len: int = 8) -> np.ndarray:
    """
    Убирает короткие веточки скелета (усы, паучки).
    Итеративно: находим концевые точки, идём по ветке,
    если её длина меньше min_branch_len — стираем.
    """
    skel = (skel > 0).astype(np.uint8)
    h, w = skel.shape

    def neighbors(y, x):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                ny, nx = y + dy, x + dx
                if 0 <= ny < h and 0 <= nx < w and skel[ny, nx]:
                    yield ny, nx

    for _ in range(3):
        endpoints = []
        ys, xs = np.where(skel > 0)
        for y, x in zip(ys, xs):
            if sum(1 for _ in neighbors(y, x)) == 1:
                endpoints.append((y, x))

        for y0, x0 in endpoints:
            branch = [(y0, x0)]
            prev = None
            cur = (y0, x0)
            while True:
                nbrs = [n for n in neighbors(*cur) if n != prev]
                if len(nbrs) != 1:
                    break
                prev, cur = cur, nbrs[0]
                branch.append(cur)
                if len(branch) > min_branch_len:
                    break
            if len(branch) < min_branch_len:
                for (yy, xx) in branch[:-1]:
                    skel[yy, xx] = 0

    return (skel * 255).astype(np.uint8)


def _clean_mask(binary: np.ndarray, open_ksize: int = 3) -> np.ndarray:
    """Морфологическое открытие: убирает мелкие точки и одиночные пиксели."""
    if open_ksize < 3:
        return binary
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_ksize, open_ksize))
    return cv2.morphologyEx(binary, cv2.MORPH_OPEN, k)


def skeletonize_edges(edges: np.ndarray,
                      open_ksize: int = 3,
                      prune_len: int = 8) -> np.ndarray:
    """
    Полный конвейер скелетизации с очисткой:
      1. Морфологическое открытие — убирает шум.
      2. Thinning — тонкая центральная линия.
      3. Pruning — срезает короткие веточки.
    """
    bin_img = (edges > 0).astype(np.uint8) * 255

    bin_img = _clean_mask(bin_img, open_ksize)

    if hasattr(cv2, "ximgproc"):
        try:
            skel = _skeletonize_thinning(bin_img)
        except Exception:
            skel = _skeletonize_morph(bin_img)
    else:
        skel = _skeletonize_morph(bin_img)

    skel = _prune_skeleton(skel, min_branch_len=prune_len)

    return skel


# ============================================================
#  Контуры
# ============================================================
def extract_contours(image: np.ndarray,
                     blur: int = 3,
                     canny_low: int = 40,
                     canny_high: int = 120,
                     min_area: float = 30.0,
                     approx_eps: float = 1.5,
                     invert: bool = False,
                     use_adaptive: bool = False,
                     skeletonize: bool = False,
                     skel_open: int = 3,
                     skel_prune: int = 8) -> List[np.ndarray]:
    """
    Возвращает список контуров.
    Если skeletonize=True — маска очищается, утоньшается и прунится,
    затем контуры ищутся по скелету.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    if blur >= 3:
        k = blur if blur % 2 == 1 else blur + 1
        gray = cv2.GaussianBlur(gray, (k, k), 0)

    if use_adaptive:
        edges = cv2.adaptiveThreshold(gray, 255,
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV,
                                      31, 5)
    else:
        edges = cv2.Canny(gray, canny_low, canny_high)
        if invert:
            edges = cv2.bitwise_not(edges)

    if skeletonize:
        edges = skeletonize_edges(edges, open_ksize=skel_open, prune_len=skel_prune)
    else:
        kernel = np.ones((2, 2), np.uint8)
        edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

    result = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue
        approx = cv2.approxPolyDP(cnt, approx_eps, True)
        if len(approx) >= 2:
            result.append(approx)
    return result


# ============================================================
#  DXF
# ============================================================
def write_dxf(contours: List[np.ndarray],
              out_path: Path,
              scale_mm_per_px: float = 0.01,
              layer_name: str = "TRACES",
              flip_y: bool = True) -> None:
    """Сохраняет контуры как LWPOLYLINE в DXF."""
    doc = ezdxf.new(dxfversion="R2010")
    msp = doc.modelspace()

    if layer_name not in doc.layers:
        doc.layers.add(layer_name, color=3)

    h_max = max((int(np.max(c[..., 1])) for c in contours), default=0)

    for cnt in contours:
        pts = cnt.reshape(-1, 2).astype(float)
        pts *= scale_mm_per_px
        if flip_y:
            pts[:, 1] = (h_max * scale_mm_per_px) - pts[:, 1]
        if not np.array_equal(pts[0], pts[-1]):
            pts = np.vstack([pts, pts[0]])
        msp.add_lwpolyline(pts, dxfattribs={"layer": layer_name})

    out_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(str(out_path))


# ============================================================
#  Верхнеуровневая функция
# ============================================================
def images_to_dxf(folder: Path,
                  out_dxf: Path,
                  *,
                  naming: str = "auto",
                  cols_override: Optional[int] = None,
                  overlap_px: int = 0,
                  blur: int = 3,
                  canny_low: int = 40,
                  canny_high: int = 120,
                  min_area: float = 30.0,
                  approx_eps: float = 1.5,
                  invert: bool = False,
                  use_adaptive: bool = False,
                  skeletonize: bool = False,
                  skel_open: int = 3,
                  skel_prune: int = 8,
                  scale_mm_per_px: float = 0.01,
                  save_preview: bool = True,
                  save_mask: bool = False,
                  progress_cb: Optional[Callable[[str], None]] = None,
                  ) -> Dict:
    """
    Полный конвейер: папка → мозаика → контуры → DXF.
    Возвращает dict со статистикой.
    """
    def log(msg: str):
        if progress_cb:
            progress_cb(msg)

    log(t("dxf_step_collect"))
    files = collect_images(folder, naming=naming)
    if not files:
        raise RuntimeError(t("dxf_no_images"))

    log(t("dxf_step_mosaic"))
    mosaic, info = build_mosaic(files, cols_override=cols_override, overlap_px=overlap_px)
    if mosaic is None:
        raise RuntimeError(t("dxf_mosaic_failed"))

    preview_path = None
    if save_preview:
        preview_path = out_dxf.with_name(out_dxf.stem + "_preview.png")
        cv2.imwrite(str(preview_path), mosaic)

    log(t("dxf_step_contours"))
    contours = extract_contours(
        mosaic,
        blur=blur,
        canny_low=canny_low,
        canny_high=canny_high,
        min_area=min_area,
        approx_eps=approx_eps,
        invert=invert,
        use_adaptive=use_adaptive,
        skeletonize=skeletonize,
        skel_open=skel_open,
        skel_prune=skel_prune,
    )

    if save_mask:
        mask = np.zeros_like(mosaic)
        cv2.drawContours(mask, contours, -1, (0, 255, 0), 1)
        mask_path = out_dxf.with_name(out_dxf.stem + "_mask.png")
        cv2.imwrite(str(mask_path), mask)

    log(t("dxf_step_write"))
    write_dxf(contours, out_dxf, scale_mm_per_px=scale_mm_per_px)

    return {
        "images": len(files),
        "rows": info["rows"],
        "cols": info["cols"],
        "mosaic_shape": (mosaic.shape[1], mosaic.shape[0]),
        "contours": len(contours),
        "skeletonized": skeletonize,
        "dxf": str(out_dxf),
        "preview": str(preview_path) if preview_path else None,
    }