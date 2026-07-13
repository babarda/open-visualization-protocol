# FN-05 . Numbers, units, and scales

## Numbers

1. Tabular (monospaced-figure) rendering wherever numbers stack in
   columns; right-aligned in tables.
2. Units appear ONCE per chart, not per value:
   - bar charts: on the first (largest) value label ("34 items", then
     "28", "21", ...)
   - line charts: on the top y tick label ("80%", then "60", "40", ...)
3. Missing value = "-" (hyphen nil marker), never zero, never a guess.
4. Titles state the finding with a number. "Backlog overview" fails QA;
   "Electrical holds 34 of 109 open items" passes.

## Scales (deterministic by construction)

Bars start at zero, always, no exceptions. Line charts start at zero by
default; a non-zero baseline requires a written justification in the
entry that uses it.

Tick generation is an algorithm, not taste, so two renders can never
disagree:

```
raw  = max_value / target_ticks        (target_ticks = 5)
mag  = 10 ^ floor(log10(raw))
step = first of {1, 2, 5, 10} * mag that is >= raw
top  = ceil(max_value / step) * step
ticks = 0, step, 2*step, ... top
```

Direct-label bar charts skip the axis entirely and scale bars to the max
value; the labels carry the numbers.

## Float formatting in renders

All coordinates format as max-2-decimal, trailing zeros stripped, "-0"
normalized to "0". This is what makes byte-identical re-renders possible
across machines.
