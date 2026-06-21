"""
Design system — color tokens, typography tokens, 5 pre-built themes.
Non-engineers pick a theme; every slide uses the same tokens automatically.
"""
import copy
from dataclasses import dataclass, field
from typing import Dict, Optional
from pptx.dml.color import RGBColor


def hex_rgb(h: str) -> RGBColor:
    h = h.lstrip('#')[:6]  # ignore alpha channel if present
    return RGBColor(int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16))


@dataclass
class Colors:
    primary: str = "#1F2937"       # Dark header / accent bar bg
    secondary: str = "#374151"     # Slightly lighter dark
    accent: str = "#3B82F6"        # Brand CTA / highlight
    accent_soft: str = "#DBEAFE"   # Tinted accent bg for cards
    surface: str = "#FFFFFF"       # Slide / card background
    surface_alt: str = "#F9FAFB"   # Alternate row / card fill
    text_dark: str = "#111827"     # Primary body text
    text_mid: str = "#6B7280"      # Secondary text / labels
    text_light: str = "#FFFFFF"    # Text on dark backgrounds
    divider: str = "#E5E7EB"       # Lines, borders


@dataclass
class Typo:
    sz_huge: int = 40    # Title slide main text
    sz_h1: int = 26      # Slide title (in title bar)
    sz_h2: int = 20      # Section heading
    sz_h3: int = 15      # Card / column subheading
    sz_kpi: int = 42     # Big KPI number
    sz_body: int = 13    # Body / bullet text
    sz_sm: int = 10      # Caption / footer


@dataclass
class Theme:
    key: str
    name: str
    emoji: str
    colors: Colors = field(default_factory=Colors)
    typo: Typo = field(default_factory=Typo)


def _soft(hex_color: str, factor: float = 0.82) -> str:
    """Return a light tint of hex_color for soft/background use."""
    h = hex_color.lstrip('#')[:6]
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02X}{g:02X}{b:02X}"


def with_brand(
    base: Theme,
    primary: Optional[str] = None,
    accent: Optional[str] = None,
) -> Theme:
    """Return a copy of base with optional color overrides applied."""
    t = copy.deepcopy(base)
    if primary:
        t.colors.primary = primary
        t.colors.secondary = primary
    if accent:
        t.colors.accent = accent
        t.colors.accent_soft = _soft(accent)
    return t


THEMES: Dict[str, Theme] = {
    "navy": Theme(
        "navy", "コーポレートネイビー", "🔵",
        Colors(primary="#1F2937", secondary="#374151",
               accent="#3B82F6", accent_soft="#DBEAFE"),
    ),
    "forest": Theme(
        "forest", "モダングリーン", "🟢",
        Colors(primary="#064E3B", secondary="#065F46",
               accent="#10B981", accent_soft="#D1FAE5"),
    ),
    "charcoal": Theme(
        "charcoal", "クールグレー", "⚫",
        Colors(primary="#0F172A", secondary="#1E293B",
               accent="#6366F1", accent_soft="#EEF2FF"),
    ),
    "crimson": Theme(
        "crimson", "プロフェッショナルレッド", "🔴",
        Colors(primary="#1F2937", secondary="#374151",
               accent="#DC2626", accent_soft="#FEE2E2"),
    ),
    "gold": Theme(
        "gold", "プレミアムゴールド", "🟡",
        Colors(primary="#1C1917", secondary="#292524",
               accent="#D97706", accent_soft="#FEF3C7"),
    ),
}
