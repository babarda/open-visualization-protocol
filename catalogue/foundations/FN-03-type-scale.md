# FN-03 . Type scale

Sizes are fixed per text role on the 960x540 chart canvas. A DL changes
the family and weight, never the size or position (those belong to the
chart spec).

| Text role | Size | Font slot | Notes |
|---|---|---|---|
| Title | 24 px | display | full sentence, states the finding with a number |
| Eyebrow | 11 px | body, weight 600 | CAPS, letter-spacing 2, only if DL chrome |
| Category / series label | 13 px | body | weight 600 only on the highlighted item |
| Value label | 13 px | body | weight 600 only on the highlighted item |
| Tick label | 11 px | body | |
| X-axis label | 11 px | body | |
| Annotation | 12 px | body, italic | |
| Source line | 11 px | body | |

## Rules

1. Two font slots only: `display` (titles) and `body` (everything else).
   A third slot (`mono` for IDs and timestamps) is reserved for DLs that
   declare it; no spec may require it.
2. Every DL family stack ends in an installed-everywhere fallback
   (Segoe UI, Arial, Georgia, Consolas). Silent substitution with a
   different metric font is the failure mode this prevents.
3. Nothing below 11 px on the 960x540 canvas. On the 1280x720 slide
   canvas the floor is 12 px.
4. Emphasis is weight (400 to 600), never a size bump, never underline.
