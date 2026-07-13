# CH-PTW-01 . STACKED BAR

Family: PTW Part-to-whole. How a total splits, tracked across periods:
the pipeline chart (delivered / in transit / pending).

**Canonical spec: [`specs/CH-PTW-01.json`](../../specs/CH-PTW-01.json).**

Deterministic decisions: segments stack bottom-up in data order, 4 max;
totals labeled above columns, unit once; segments identified by
swatch + name at the last column, never a legend; segment colors from
role chains (primary, muted, benchmark, gridline). Use CH-PTW-02 when
shares matter more than totals.

Goldens: `golden/CH-PTW-01/` (16 DLs). Blocks:
`blocks/design-system/CH-PTW-01_DL-xx.md`, `blocks/skill/CH-PTW-01.md`.
