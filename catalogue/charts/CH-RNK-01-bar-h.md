# CH-RNK-01 . BAR-H (horizontal bar, ranked)

Family: RNK Ranking. The message is who is biggest, in order.

**Canonical spec: [`specs/CH-RNK-01.json`](../../specs/CH-RNK-01.json).**

Use for ranking under 12 categories or long category names. Not for
time series (CH-TIM-01), natural-order magnitude (CH-MAG-01), or
part-to-whole. The renderer sorts rows descending; ties break
alphabetically so output stays deterministic.

Deterministic decisions: no value axis, bars scale to the max value,
direct labels carry the numbers; one `primary` highlight, rest `muted`;
unit once on the first label; baseline hairline at zero; bar 32 px,
gap 16 px.

Goldens: [`data.json`](../../golden/CH-RNK-01/data.json),
[`DL-02`](../../golden/CH-RNK-01/CH-RNK-01_DL-02.svg),
[`DL-03`](../../golden/CH-RNK-01/CH-RNK-01_DL-03.svg).
Copy blocks: `blocks/design-system/CH-RNK-01_DL-xx.md`,
`blocks/skill/CH-RNK-01.md`.
