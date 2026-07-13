# CH-DEV-01 . DIVERGING BAR

Family: DEV Deviation. Signed variance per category against a
meaningful zero: ahead/behind plan, over/under budget.

**Canonical spec: [`specs/CH-DEV-01.json`](../../specs/CH-DEV-01.json).**

Deterministic decisions: zero line at plot center, both sides on the
same symmetric scale (max absolute value); positives grow right in the
`positive` role, negatives left in `negative`; every label signed, so
the sign never depends on color perception; rows sorted descending
(best on top, worst at the bottom, where the eye lands last and the
title already pointed). One-signed data belongs in CH-RNK-01;
sequential deltas in CH-FLO-01.

Goldens: `golden/CH-DEV-01/` (16 DLs). Blocks:
`blocks/design-system/CH-DEV-01_DL-xx.md`, `blocks/skill/CH-DEV-01.md`.
