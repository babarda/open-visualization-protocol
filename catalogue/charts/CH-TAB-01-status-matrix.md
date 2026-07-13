# CH-TAB-01 . STATUS MATRIX

Family: TAB Tables. Entities x stages readiness grid; the reader looks
up THEIR row.

**Canonical spec: [`specs/CH-TAB-01.json`](../../specs/CH-TAB-01.json).**

Deterministic decisions: every cell is swatch + word, never color
alone; five statuses with fixed role bindings (complete->positive,
on_track->primary, watch->warning|muted, critical->negative,
na->hairline with the nil hyphen); stage columns in process order, rows
in the reader's natural order, never re-sorted by health; hairline row
rules, no zebra. Numeric cells belong to CH-TAB-02 when built.

Goldens: `golden/CH-TAB-01/` (16 DLs). Blocks:
`blocks/design-system/CH-TAB-01_DL-xx.md`, `blocks/skill/CH-TAB-01.md`.
