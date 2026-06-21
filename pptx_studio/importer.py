"""
Extract brand tokens (primary color, accent, logo) from an existing PPTX.

Handles both native PowerPoint files and Google Slides PPTX exports.
Google Slides exports use theme color references rather than direct RGB fills,
so we scan slide master + layout XML for srgbClr values in addition to slides.
"""
import io
import re
from collections import Counter

from pptx import Presentation
from pptx.dml.color import RGBColor
from lxml import etree


def _to_hex(rgb: RGBColor) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _lum(h: str) -> float:
    """Perceived luminance 0–1 (ITU-R BT.601)."""
    h = h.lstrip('#')
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    return (0.299 * r + 0.587 * g + 0.114 * b) / 255


def _sat(h: str) -> float:
    """HSV-style saturation 0–1."""
    h = h.lstrip('#')
    r, g, b = int(h[:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:], 16) / 255
    mx, mn = max(r, g, b), min(r, g, b)
    return (mx - mn) / mx if mx > 0 else 0


_SKIP = {
    '#FFFFFF', '#FFFFFE', '#FEFEFE', '#FDFDFD', '#FCFCFC',
    '#000000', '#010101', '#020202', '#030303',
    '#F3F3F3', '#F2F2F2',  # near-white grays common in templates
}

_SRGB_RE = re.compile(r'srgbClr val="([0-9A-Fa-f]{6})"')


def _scan_xml(element, counter: Counter, weight: int = 1):
    """Collect all srgbClr values from an XML element tree."""
    xml_str = etree.tostring(element).decode()
    for val in _SRGB_RE.findall(xml_str):
        counter[f'#{val.upper()}'] += weight


def _collect_direct_rgb(shape, counter: Counter):
    """Extract direct-RGB colors from python-pptx shape API (non-Google-Slides)."""
    try:
        counter[_to_hex(shape.fill.fore_color.rgb)] += 2
    except Exception:
        pass
    if shape.has_text_frame:
        for para in shape.text_frame.paragraphs:
            for run in para.runs:
                try:
                    counter[_to_hex(run.font.color.rgb)] += 1
                except Exception:
                    pass


def _find_logo(prs) -> bytes | None:
    """
    Return the bytes of the most likely logo image:
    - Smallest picture on slides 1-3 that is < 80 KB and > 1 KB
      (large images are content photos; tiny ones are icons/logos)
    """
    candidates = []
    slides = list(prs.slides)
    for i, slide in enumerate(slides[:3]):
        for shape in slide.shapes:
            if shape.shape_type == 13:  # PICTURE
                try:
                    blob = shape.image.blob
                    if 1024 < len(blob) < 80_000:
                        candidates.append((len(blob), blob))
                except Exception:
                    pass
            if shape.shape_type == 6:  # GROUP — recurse one level
                try:
                    for child in shape.shapes:
                        if child.shape_type == 13:
                            blob = child.image.blob
                            if 1024 < len(blob) < 80_000:
                                candidates.append((len(blob), blob))
                except Exception:
                    pass
    if not candidates:
        return None
    # Smallest candidate is most likely the logo (not a content photo)
    candidates.sort(key=lambda x: x[0])
    return candidates[0][1]


def extract_brand(pptx_bytes: bytes) -> dict:
    """
    Scan a PPTX and return:
      primary    – darkest frequently-used color (header / nav background)
      accent     – most-saturated mid-brightness color (CTA / highlight)
      logo_bytes – smallest picture on slides 1-3 within 1-80 KB, or None
      palette    – up to 14 hex colors sorted by frequency
    """
    prs = Presentation(io.BytesIO(pptx_bytes))
    counter: Counter = Counter()

    # ── 1. Slide master (weighted high — defines brand identity)
    try:
        _scan_xml(prs.slide_master.element, counter, weight=3)
    except Exception:
        pass

    # ── 2. Slide layouts (weighted medium — template design)
    try:
        for layout in prs.slide_master.slide_layouts:
            _scan_xml(layout.element, counter, weight=2)
    except Exception:
        pass

    # ── 3. Slides (weighted normal — actual content)
    for i, slide in enumerate(prs.slides):
        w = 1
        _scan_xml(slide.element, counter, weight=w)
        # Also try direct python-pptx API for native PPTX files
        for shape in slide.shapes:
            _collect_direct_rgb(shape, counter)

    # ── Normalise: drop extremes (near-black < 5% and near-white > 95%)
    useful = {}
    for h, c in counter.items():
        if h in _SKIP:
            continue
        lv = _lum(h)
        if lv < 0.05 or lv > 0.95:
            continue
        useful[h] = c

    palette = [h for h, _ in sorted(useful.items(), key=lambda x: -x[1])][:14]

    # ── Primary: darkest frequently-used color (header / nav bar candidate)
    darks = [(h, c) for h, c in useful.items() if _lum(h) < 0.40]
    primary = max(darks, key=lambda x: x[1])[0] if darks else "#1F2937"

    # ── Accent: vivid mid-brightness color, clearly different from primary
    #    Require lum > 0.25 so we don't pick another near-dark color as accent
    mids = [
        (h, c) for h, c in useful.items()
        if 0.25 < _lum(h) < 0.82 and _sat(h) > 0.30 and h != primary
    ]
    accent = max(mids, key=lambda x: x[1])[0] if mids else "#3B82F6"

    # ── Logo
    logo_bytes = _find_logo(prs)

    return {
        "primary": primary,
        "accent": accent,
        "logo_bytes": logo_bytes,
        "palette": palette,
    }
