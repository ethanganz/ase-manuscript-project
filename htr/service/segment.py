"""Split a manuscript page into line boxes with a horizontal ink profile.

Simple on purpose: works for fairly straight lines with white space between them.
Strongly slanted or touching lines and marginal notes need a trained segmenter.
"""
import numpy as np
from PIL import Image, ImageOps


def _otsu_threshold(gray: np.ndarray) -> int:
    """Gray level that best separates ink from paper."""
    hist = np.bincount(gray.ravel(), minlength=256).astype(float)
    levels = np.arange(256)
    weight_bg = np.cumsum(hist)
    weight_fg = weight_bg[-1] - weight_bg
    sum_bg = np.cumsum(hist * levels)
    mean_bg = sum_bg / np.maximum(weight_bg, 1)
    mean_fg = (sum_bg[-1] - sum_bg) / np.maximum(weight_fg, 1)
    between = weight_bg * weight_fg * (mean_bg - mean_fg) ** 2
    return int(np.argmax(between))


def _split_tall(start: int, end: int, profile: np.ndarray, typical: float) -> list[tuple[int, int]]:
    """Cut a band that holds several touching lines at its emptiest rows."""
    count = round((end - start) / typical)
    if count < 2:
        return [(start, end)]
    cuts, reach = [start], max(1, int(typical / 3))
    for i in range(1, count):
        target = start + int(i * (end - start) / count)
        lo, hi = max(cuts[-1] + 1, target - reach), min(end - 1, target + reach)
        cuts.append(lo + int(np.argmin(profile[lo : hi + 1])) if hi > lo else target)
    cuts.append(end)
    return list(zip(cuts[:-1], cuts[1:]))


def find_lines(image: Image.Image) -> list[tuple[int, int, int, int]]:
    """Line boxes (left, top, right, bottom) in reading order, top to bottom.

    An image that already holds a single line comes back as one box covering it.
    """
    gray = np.asarray(ImageOps.grayscale(image), dtype=np.uint8)
    height, width = gray.shape
    ink = gray <= _otsu_threshold(gray)
    # Dark scan borders and ruled edges would join every line together.
    ink[:, ink.mean(axis=0) > 0.8] = False
    ink[ink.mean(axis=1) > 0.8, :] = False

    window = max(1, height // 150)
    profile = np.convolve(ink.sum(axis=1), np.ones(window) / window, mode="same")
    if profile.max() == 0:
        return []
    rows = profile > 0.2 * np.percentile(profile[profile > 0], 95)

    bands, start = [], None
    for y, on in enumerate(np.append(rows, False)):
        if on and start is None:
            start = y
        elif not on and start is not None:
            bands.append((start, y))
            start = None
    # Specks and stray diacritics: too thin to be a line of their own.
    typical = float(np.median([b - a for a, b in bands]))
    bands = [(a, b) for a, b in bands if b - a >= 0.35 * typical]
    typical = float(np.median([b - a for a, b in bands]))
    bands = [part for a, b in bands for part in _split_tall(a, b, profile, typical)]
    if len(bands) <= 1:
        return [(0, 0, width, height)] if bands else []

    pad = int(0.35 * typical)
    boxes = []
    for top, bottom in bands:
        top, bottom = max(0, top - pad), min(height, bottom + pad)
        cols = np.flatnonzero(ink[top:bottom].sum(axis=0) > 1)
        if cols.size == 0:
            continue
        left, right = max(0, cols[0] - 2 * pad), min(width, cols[-1] + 1 + 2 * pad)
        boxes.append((int(left), int(top), int(right), int(bottom)))
    return boxes
