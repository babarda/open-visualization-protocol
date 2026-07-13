# MX-02 . Fit overlays

The declared-fit mechanism for correlation charts: a trend or fit line
may appear on CH-COR entries ONLY as declared data, never as silent
renderer computation.

## The contract

1. A fit overlay is supplied in the data as
   `fit: {kind, points: [[x, y], ...], label}`. The renderer draws the
   polyline through the supplied points; it never computes a
   regression.
2. `kind` names the method exactly as the analyst ran it
   ("OLS linear", "LOESS span 0.6", "quantile p50"). The source line
   MUST repeat it.
3. The fit renders in the `muted` role chain, dashed (6 4), 1.5px:
   fits comment on evidence, they are not evidence.
4. `label` renders at the line's right end, italic, body role, and
   MUST state the strength honestly (e.g. "OLS fit, r2 = 0.66").
5. One fit maximum per chart. Competing fits are competing claims:
   show them as separate charts.
6. Extrapolation beyond the data's x range is non-conforming; the
   supplied points must stay inside the observed domain.

## When

- A CH-COR chart where the analyst has actually fitted something and
  can name the method and the strength.

## Not when

- The fit would be decoration ("add a trend line so it looks
  analyzed"). No declared method, no line.

## QA

- fit points supplied as data, method named in kind AND source
- dashed, muted, one fit maximum
- label states the strength with a number
- no extrapolation beyond observed x
