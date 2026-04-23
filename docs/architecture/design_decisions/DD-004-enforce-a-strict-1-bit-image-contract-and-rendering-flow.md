# DD-004: Enforce a strict 1-bit image contract and rendering flow

## Decision

The device accepts only a raw 800 × 480, 1-bit-per-pixel, MSB-first bitmap and renders it through the display library using a full-window paged refresh.

## Rationale

- Keeps the embedded device free from image decoding complexity.
- Makes the publisher responsible for normalization.
- Aligns the data contract with the display hardware and GxEPD2 drawing model.

## Evidence

- `README.md` defines the payload format and size.
- `ePaperDash.ino` draws the bitmap with `drawBitmap()` inside the GxEPD2 page loop.
