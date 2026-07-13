# CH-TIM-03 . AREA

Family: TIM Change over time. One quantity where the volume matters:
output, throughput, stock.

**Canonical spec: [`specs/CH-TIM-03.json`](../../specs/CH-TIM-03.json).**

Deterministic decisions: exactly one filled series (fill primary at the
fixed 0.15 opacity, stroke primary 2.5); context reference lines
allowed, never filled; y-zero without exception (a cut baseline lies
twice as hard with fill); ticks from the FN-05 algorithm; labels at
line ends. Two or more compared series is CH-TIM-01's job.

Goldens: `golden/CH-TIM-03/` (16 DLs). Blocks:
`blocks/design-system/CH-TIM-03_DL-xx.md`, `blocks/skill/CH-TIM-03.md`.
