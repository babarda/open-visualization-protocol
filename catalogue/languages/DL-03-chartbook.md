# DL-03 . LOGOS (formerly CHARTBOOK)

Motto: Evidence before opinion. (Ancient Greece: logic and evidence.)

Editorial analysis on warm paper. The chart IS the page; the argument
lives in the annotation, not a legend. Deliberately does not use teal:
the paper `#FDF4EA` plus claret `#9E2B25` is the signature.

**Canonical tokens: [`tokens/DL-03.json`](../../tokens/DL-03.json).**
The JSON file is the single source of truth; this page is commentary.

## Signature

Claret kicker bar (24x4 px) above a CAPS eyebrow ("PROGRESS . H1 2026"),
then the finding as title, then one chart at 65-75% of the page.
Highlight series in claret, everything else recedes to warm gray
`#B8B2A7`. Series labeled at line ends; legends do not survive here.

## Chrome

Kicker and eyebrow on (`chrome: {kicker: true, eyebrow: true}`).
Titles shift down to y=88 to clear the eyebrow; the renderer handles
this from the chrome flags.

## Banned in this language

KPI cards, status chips, two charts on one page, brand teal, legends.

## QA additions

- Every chart carries an annotation anchored at the data.
- Every chart carries a source line.
- No legend survives.

## Golden renders

- [CH-01 in DL-03](../../golden/CH-01/CH-01_DL-03.svg)
- [CH-02 in DL-03](../../golden/CH-02/CH-02_DL-03.svg)
