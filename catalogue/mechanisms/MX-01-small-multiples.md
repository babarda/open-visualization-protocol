# MX-01 . Small multiples

The faceting mechanism: any chart entry repeated in a grid, one facet
per category, same spec, same scales, same golden data contract.

## The contract

1. Every facet renders the SAME chart spec with the same layout block,
   scaled into its cell; only the data subset changes.
2. One shared scale across all facets, computed on the union of all
   facet data with the FN-05 nice-scale algorithm. Per-facet scales are
   non-conforming: the whole point of multiples is comparability.
3. Grid geometry: cells fill the parent plot area left to right, top to
   bottom, in data order. Gaps are exact px from the layout
   (`facet_gap_x`, `facet_gap_y`). No cell is ever a different size.
4. Each facet carries one label (its category), top-left inside the
   cell, body role, caps. No per-facet titles, sources, or axes beyond
   the first column (y) and last row (x): shared frames are stated
   once.
5. Facet count: 2 to 12. Beyond 12, aggregate first.
6. Bare mode (`_bare`) applies inside facets: the page owns the title
   and source, exactly as recipes do.

## When

- One message repeated across categories ("every region shows the same
  dip") where overlaying lines would tangle.
- Any chart whose entry says "comparing many: use small multiples".

## Not when

- Facets with wildly different magnitudes (a shared scale flattens the
  small ones; consider CH-TIM-14 indexed lines instead).
- Two categories (just draw both on one chart if the entry allows).

## QA

- shared scale across facets, stated once
- facet labels present, caps, body role
- 2 to 12 facets, identical cell geometry
- page title and source drawn by the page, not per facet
