# CH-PTW-02 . STACKED BAR 100%

Family: PTW Part-to-whole. The MIX over time; totals normalized away.

**Canonical spec: [`specs/CH-PTW-02.json`](../../specs/CH-PTW-02.json).**

Same renderer as CH-PTW-01 with `scale.normalize: true`. Deterministic
decisions: all columns full height; the KEY (first) segment's share
labeled above each column with the % sign; swatch + name at the last
column. Its anti-pattern is its own trap: 100% stacked hides growth
and shrinkage, so the entry sends you back to CH-PTW-01 whenever the
total matters.

Goldens: `golden/CH-PTW-02/` (16 DLs). Blocks:
`blocks/design-system/CH-PTW-02_DL-xx.md`, `blocks/skill/CH-PTW-02.md`.
