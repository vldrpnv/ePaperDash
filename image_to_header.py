#!/usr/bin/env python3
"""
image_to_header.py  -  Convert an image to a C header file for ePaperDash.

Usage
-----
    python3 image_to_header.py <input_image> [options]

    Options:
        -o / --output   Output header file path (default: initial_image.h)
        -W / --width    Target display width  in pixels (default: 800)
        -H / --height   Target display height in pixels (default: 480)
        --dither        Use Floyd-Steinberg dithering instead of hard threshold
        --invert        Invert pixel polarity (swap black and white)
        --threshold N   Grayscale threshold 0-255; pixels darker than N become
                        black (default: 128)

Image format produced
---------------------
    Raw 1-bit-per-pixel bitmap, width × height pixels, MSB-first, row-major.
    Bit value 1 → black  (GxEPD_BLACK),  0 → white  (GxEPD_WHITE).
    Total bytes: width × height / 8  (e.g. 48 000 bytes for 800 × 480).

The image is resized to fit within the display canvas while preserving the
aspect ratio; any unused area is padded with white.
"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required.  Install it with:  pip install Pillow",
          file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def image_to_1bpp(img: Image.Image, width: int, height: int,
                  dither: bool, invert: bool, threshold: int) -> bytes:
    """Return a packed 1-bpp byte array (MSB-first, 1 = black)."""

    # Resize preserving aspect ratio, then paste onto a white canvas
    canvas = Image.new("L", (width, height), 255)  # white background
    img_rgb = img.convert("RGB")
    img_gray = img_rgb.convert("L")
    img_gray.thumbnail((width, height), Image.LANCZOS)
    x_off = (width  - img_gray.width)  // 2
    y_off = (height - img_gray.height) // 2
    canvas.paste(img_gray, (x_off, y_off))

    if dither:
        # Convert to 1-bit with Floyd-Steinberg dithering (PIL default)
        bw = canvas.convert("1", dither=Image.FLOYDSTEINBERG)
    else:
        bw = canvas.point(lambda p: 0 if p < threshold else 255, "L").convert("1")

    # Pack bits – PIL "1" mode pixel values are 0 (black) or 255 (white);
    # we need MSB-first packed bits where bit 1 = black.
    px_access = bw.load()
    total_bits = width * height
    data = bytearray(total_bits // 8)
    for y in range(height):
        for x in range(width):
            px = px_access[x, y]  # 0 = black, 255 = white
            if invert:
                px = 255 - px
            if px == 0:  # black → set bit
                i = y * width + x
                data[i >> 3] |= 0x80 >> (i & 7)
    return bytes(data)


def write_header(data: bytes, out_path: Path, width: int, height: int,
                 source_name: str) -> None:
    """Write a C header file containing the bitmap as a PROGMEM array."""
    hex_rows = []
    bytes_per_row = width // 8
    for row in range(height):
        start = row * bytes_per_row
        chunk = data[start:start + bytes_per_row]
        hex_rows.append("    " + ", ".join(f"0x{b:02X}" for b in chunk))

    total = len(data)
    lines = [
        "#pragma once",
        "",
        "#include <pgmspace.h>",
        "",
        f"// Initial image converted from: {source_name}",
        f"// Size: {width} × {height} px, 1 bpp, MSB-first",
        f"// Bit 1 = black (GxEPD_BLACK),  bit 0 = white",
        f"// Total bytes: {total}",
        "",
        f"static const uint8_t INITIAL_IMAGE[{total}] PROGMEM = {{",
    ]
    lines.append(",\n".join(hex_rows))
    lines.append("};")
    lines.append("")

    out_path.write_text("\n".join(lines))
    print(f"Written {total} bytes → {out_path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Convert an image to a C header for ePaperDash.")
    parser.add_argument("input",         help="Input image file")
    parser.add_argument("-o", "--output", default="initial_image.h",
                        help="Output header file (default: initial_image.h)")
    parser.add_argument("-W", "--width",  type=int, default=800,
                        help="Display width in pixels (default: 800)")
    parser.add_argument("-H", "--height", type=int, default=480,
                        help="Display height in pixels (default: 480)")
    parser.add_argument("--dither",  action="store_true",
                        help="Use Floyd-Steinberg dithering")
    parser.add_argument("--invert",  action="store_true",
                        help="Invert pixel polarity")
    parser.add_argument("--threshold", type=int, default=128,
                        help="Grayscale threshold 0-255 (default: 128)")
    args = parser.parse_args()

    src = Path(args.input)
    if not src.exists():
        print(f"ERROR: File not found: {src}", file=sys.stderr)
        sys.exit(1)

    img = Image.open(src)
    print(f"Opened {src}  ({img.width}×{img.height}, mode={img.mode})")

    data = image_to_1bpp(img, args.width, args.height,
                         args.dither, args.invert, args.threshold)

    write_header(data, Path(args.output), args.width, args.height, src.name)


if __name__ == "__main__":
    main()
