# CH-MAG-01 . COLUMN (vertical bar, natural order)

Family: MAG Magnitude. The message is how big things are, with the
category order kept as given (sites, phases, units).

**Canonical spec: [`specs/CH-MAG-01.json`](../../specs/CH-MAG-01.json).**

Use for magnitude across 8 or fewer short-named categories. Not when
the message is rank (CH-RNK-01 sorts; this entry never does), not for
time series, not for long names (rotated labels mean wrong chart).

Deterministic decisions: input order preserved; columns centered in
equal slots, fixed 64 px width; value labels above columns, no axis,
no gridlines; one `primary` highlight, rest `muted`; unit once on the
first label; baseline hairline at zero.

Goldens: [`data.json`](../../golden/CH-MAG-01/data.json),
[`DL-02`](../../golden/CH-MAG-01/CH-MAG-01_DL-02.svg),
[`DL-03`](../../golden/CH-MAG-01/CH-MAG-01_DL-03.svg).
Copy blocks: `blocks/design-system/CH-MAG-01_DL-xx.md`,
`blocks/skill/CH-MAG-01.md`.
