# FN-04 . Contrast and color use

## Hard limits (validated, not advisory)

1. `ink` and `body` reach 4.5:1 on `background` (WCAG AA body text).
   `tools/validate.py` computes this from the DL token file and blocks
   on failure.
2. Meaning is never carried by color alone. Status, deltas, and
   exceptions always pair color with a word or a number.
3. One saturated highlight per chart. The `primary` role appears on the
   one mark the title talks about; everything else uses `muted` or
   `benchmark`.

## Discipline

- Series count before color count: if a chart needs more than 4 colors,
  the chart is wrong (split into small multiples), not the palette.
- `positive` and `negative` mark deltas and status, never decorate.
- Charts must survive grayscale: the highlighted mark must still read as
  the highlight through weight, position, or label emphasis.

## The banned list (applies to every DL, every chart)

- Purple/blue gradient backgrounds, "hero" gradient bands
- Rainbow categorical palettes (one hue per bar)
- Color-only status dots
- Anything below AA contrast, including gray-on-gray captions
- 3D depth, glassmorphism, heavy drop shadows
