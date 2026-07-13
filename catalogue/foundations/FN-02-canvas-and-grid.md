# FN-02 . Canvas and spacing grid

## Canvases

| Target | Size | Use |
|---|---|---|
| Chart entry golden render | 960 x 540 px | every CH-xx golden |
| Full slide (16:9) | 1280 x 720 px | recipes (DL/CH/CP combinations) |

All positions and sizes in specs are exact pixels on these canvases.
Adjectives ("comfortable margin", "medium bar") are banned in specs; a
value the renderer cannot consume is not a spec.

## The 8px grid

Every structural distance is a multiple of 8: margins, offsets, bar
heights, gaps, plot bounds.

| Distance | Value |
|---|---|
| Canvas edge to content | 32 px |
| Title block to plot area | >= 40 px |
| Bar height / bar gap (CH-01) | 32 / 16 px |
| Label offset from mark | 8 or 16 px |

Text sizes are exempt from the 8-multiple (they follow FN-03) but their
anchor positions are not.

## Fixed furniture on every chart canvas

- Title: x=32, baseline y=56 (y=88 when the DL chrome adds an eyebrow).
- Source line: x=32, baseline y=516, always present, always bottom-left.
- Kicker + eyebrow: only when the DL's `chrome` block asks for them;
  kicker 24x4 px at (32, 28), eyebrow 11 px caps at (32, 52).
