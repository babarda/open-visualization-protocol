# CH-TIM-01 . LINE

Family: TIM Change over time. Trend over ordered periods, 2 to 4
series, the plan-vs-actual chart for period values.

**Canonical spec: [`specs/CH-TIM-01.json`](../../specs/CH-TIM-01.json).**

Not for categorical comparison (CH-RNK-01 / CH-MAG-01), cumulative
progress (CH-TIM-02 S-CURVE), or more than 4 series (small multiples).

Deterministic decisions: y starts at zero; ticks from the FN-05
nice-scale algorithm so two renders can never pick different scales;
series labeled at line ends, never a legend; one `key` series on role
`primary` (stroke 2.5), context on `benchmark -> muted` (stroke 2);
horizontal gridlines only; unit once on the top tick; annotation names
a data point and gets a leader line.

Goldens: [`data.json`](../../golden/CH-TIM-01/data.json),
[`DL-02`](../../golden/CH-TIM-01/CH-TIM-01_DL-02.svg),
[`DL-03`](../../golden/CH-TIM-01/CH-TIM-01_DL-03.svg).
Copy blocks: `blocks/design-system/CH-TIM-01_DL-xx.md`,
`blocks/skill/CH-TIM-01.md`.
