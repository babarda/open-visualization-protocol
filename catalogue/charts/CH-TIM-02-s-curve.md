# CH-TIM-02 . S-CURVE (cumulative progress vs plan)

Family: TIM Change over time. The planning S-curve: cumulative
progress against plan, where the gap IS the message.

**Canonical spec: [`specs/CH-TIM-02.json`](../../specs/CH-TIM-02.json).**

Shares the LINE geometry (same renderer, `chart_type: line`) but is a
distinct entry because the usage rules differ: values must be
cumulative and non-decreasing (the validator checks), y-zero is
non-negotiable (a cut baseline lies about progress), Actual is always
the key series, Plan and Forecast are context, and the annotation names
the gap or the inflection.

Not for period (non-cumulative) values: that is CH-TIM-01.

Goldens: [`data.json`](../../golden/CH-TIM-02/data.json),
[`DL-02`](../../golden/CH-TIM-02/CH-TIM-02_DL-02.svg),
[`DL-03`](../../golden/CH-TIM-02/CH-TIM-02_DL-03.svg).
Copy blocks: `blocks/design-system/CH-TIM-02_DL-xx.md`,
`blocks/skill/CH-TIM-02.md`.
