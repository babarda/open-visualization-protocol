# CH-FLO-01 . WATERFALL

Family: FLO Flow. How a total moved from A to B through named drivers:
cost bridges, budget-to-forecast walks.

**Canonical spec: [`specs/CH-FLO-01.json`](../../specs/CH-FLO-01.json).**

Deterministic decisions: the end bar is COMPUTED from start + deltas
(supplying it is a validation error, so a bridge always reconciles);
increases take the `negative` role and decreases `positive` (a cost
bridge reads correctly by default; recipes can invert for revenue);
signed labels; dashed connectors carry the running level; step order is
narrative order, never re-sorted. The validator also blocks any bridge
whose running level dips below zero.

Goldens: `golden/CH-FLO-01/` (16 DLs). Blocks:
`blocks/design-system/CH-FLO-01_DL-xx.md`, `blocks/skill/CH-FLO-01.md`.
