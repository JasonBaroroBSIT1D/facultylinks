#!/usr/bin/env python3
"""Generate Android launcher mipmaps and adaptive layers from assets/branding/launcher_icon.png."""

from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "assets" / "branding" / "launcher_icon.png"
RES = ROOT / "android" / "app" / "src" / "main" / "res"
LOGO_SRC = ROOT.parent / "branding" / "FacultyLink-logo-original.jpg"
LOGO_DST = ROOT / "assets" / "branding" / "FacultyLink-logo.jpg"

# Legacy launcher icon (48dp base).
LEGACY_PX = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}

# Adaptive foreground / monochrome (108dp base).
ADAPTIVE_PX = {
    "mdpi": 108,
    "hdpi": 162,
    "xhdpi": 216,
    "xxhdpi": 324,
    "xxxhdpi": 432,
}

# Symbol occupies ~62% of canvas (inside 66dp safe zone on 108dp layer).
ICON_FRACTION = 0.62
BG = (255, 255, 255)


def _load_symbol() -> Image.Image:
    return Image.open(SRC).convert("RGBA")


def _fit_on_square(symbol: Image.Image, canvas_px: int, fraction: float) -> Image.Image:
    target = int(canvas_px * fraction)
    sym = symbol.copy()
    sym.thumbnail((target, target), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (canvas_px, canvas_px), (*BG, 255))
    x = (canvas_px - sym.width) // 2
    y = (canvas_px - sym.height) // 2
    canvas.paste(sym, (x, y), sym)
    return canvas


def _legacy_icon(symbol: Image.Image, size: int) -> Image.Image:
    return _fit_on_square(symbol, size, 0.72)


def _foreground_layer(symbol: Image.Image, size: int) -> Image.Image:
    target = int(size * ICON_FRACTION)
    sym = symbol.copy()
    sym.thumbnail((target, target), Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    x = (size - sym.width) // 2
    y = (size - sym.height) // 2
    canvas.paste(sym, (x, y), sym)
    return canvas


def _monochrome_layer(symbol: Image.Image, size: int) -> Image.Image:
    fg = _foreground_layer(symbol, size)
    gray = fg.convert("L")
    # Black glyph on transparent; OS tints monochrome icons.
    mono = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    alpha = fg.split()[3]
    black = Image.new("L", (size, size), 0)
    mono = Image.merge("RGBA", (black, black, black, alpha))
    return mono


def _splash_logo(symbol_path: Path, out: Path, max_width: int = 480) -> None:
    full = Image.open(symbol_path).convert("RGB")
    w, h = full.size
    if w > max_width:
        nh = int(h * max_width / w)
        full = full.resize((max_width, nh), Image.Resampling.LANCZOS)
    out.parent.mkdir(parents=True, exist_ok=True)
    full.save(out, quality=92)


def main() -> None:
    if not SRC.is_file():
        raise SystemExit(f"Missing source icon: {SRC}")

    if LOGO_SRC.is_file():
        shutil.copy2(LOGO_SRC, LOGO_DST)

    symbol = _load_symbol()

    for folder, px in LEGACY_PX.items():
        path = RES / folder
        path.mkdir(parents=True, exist_ok=True)
        _legacy_icon(symbol, px).convert("RGB").save(path / "ic_launcher.png")

    for density, px in ADAPTIVE_PX.items():
        folder = RES / f"drawable-{density}"
        folder.mkdir(parents=True, exist_ok=True)
        _foreground_layer(symbol, px).save(folder / "ic_launcher_foreground.png")
        _monochrome_layer(symbol, px).save(folder / "ic_launcher_monochrome.png")

    _splash_logo(LOGO_DST, RES / "drawable-nodpi" / "splash_logo.png")

    anydpi = RES / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    ic_launcher = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@drawable/ic_launcher_foreground"/>
    <monochrome android:drawable="@drawable/ic_launcher_monochrome"/>
</adaptive-icon>
"""
    (anydpi / "ic_launcher.xml").write_text(ic_launcher, encoding="utf-8")
    (anydpi / "ic_launcher_round.xml").write_text(ic_launcher, encoding="utf-8")

    values = RES / "values"
    values.mkdir(parents=True, exist_ok=True)
    colors = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#FFFFFF</color>
</resources>
"""
    (values / "colors.xml").write_text(colors, encoding="utf-8")

    strings = """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <string name="app_name">FacultyLink</string>
</resources>
"""
    (values / "strings.xml").write_text(strings, encoding="utf-8")

    print("Generated Android launcher assets.")


if __name__ == "__main__":
    main()