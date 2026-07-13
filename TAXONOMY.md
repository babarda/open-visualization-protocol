# TAXONOMY . the coding grammar and the full catalogue map

This is the index an information designer uses to talk to an agent:
pick a code, name a language, get a determined visual. Example
instructions: "CH-TIM-02 in DL-03", "CH-RNK-01 in DL-02, highlight
Electrical".

## Code grammar

```
FN-nn            foundation (token contract, grid, type, numbers, perception)
DL-nn            design language (complete visual identity + philosophy + constitution)
BQ-nn            business question (what is being asked -> patterns, charts, narrative)
PT-nn            analytical pattern (what the data shows -> which charts)
NR-nn            narrative skeleton (how the finding is told, per decision_style)
CH-FAM-nn        chart entry: family code + number within family
CP-FAM-nn        component entry: family code + number within family
RC-nnn           recipe: a fully determined page (DL + CH + CP set)
```

Built PT patterns: PT-01 TREND, PT-02 OUTLIER, PT-03 GAP-TO-PLAN,
PT-04 CONCENTRATION, PT-05 MIX-SHIFT, PT-06 THRESHOLD-BREACH,
PT-07 DRIVER-DECOMPOSITION, PT-08 CYCLE (see PATTERNS.md, generated).
Language selection rules live in decision/engine.json (see DECIDER.md).

Codes are permanent. An entry is never renumbered and never reused;
retired entries keep their code with status `retired`. New entries take
the next free number in their family. This is what lets external skills
and design systems reference codes forever.

Statuses: `spec` = built, validated, golden renders shipped.
`planned` = named and scoped, not yet built. `warn` = will be built
with heavy anti-pattern warnings (exists because people ask for it).

## CH chart families

Adapted from the information-design canon (FT Visual Vocabulary
lineage): choose the family by WHAT THE MESSAGE IS, then the entry by
the data shape.

| Family | Code | The message is... |
|---|---|---|
| Ranking | RNK | who is biggest/smallest, ordered |
| Magnitude | MAG | how big things are, natural order kept |
| Change over time | TIM | how it moved, trend, progress |
| Part-to-whole | PTW | how a total splits |
| Deviation | DEV | distance from a reference (plan, budget, zero) |
| Distribution | DST | how values spread |
| Correlation | COR | how two measures relate |
| Spatial | SPA | where |
| Flow | FLO | movement between states or stages |
| Tables | TAB | exact values the reader will look up |

### CH-RNK Ranking

| Code | Entry | Status |
|---|---|---|
| CH-RNK-01 | BAR-H, horizontal bar, sorted descending | spec |
| CH-RNK-02 | ORDERED COLUMN, vertical, sorted | spec |
| CH-RNK-03 | LOLLIPOP | spec |
| CH-RNK-04 | BUMP, rank over time | spec |
| CH-RNK-05 | DOT STRIP, ordered | spec |
| CH-RNK-06 | TABLE WITH BARS | spec |

### CH-MAG Magnitude

| Code | Entry | Status |
|---|---|---|
| CH-MAG-01 | COLUMN, vertical bar, input order kept | spec |
| CH-MAG-02 | PAIRED COLUMN, two measures side by side | spec |
| CH-MAG-03 | PAIRED BAR | spec |
| CH-MAG-04 | BULLET, actual vs target vs bands | spec |
| CH-MAG-05 | PROPORTIONAL SYMBOL | spec |
| CH-MAG-06 | PICTOGRAM / ISOTYPE | spec |
| CH-MAG-07 | RADAR | spec (warn) |
| CH-MAG-08 | PARLIAMENT / SEAT CHART | spec |
| CH-MAG-09 | GAUGE | spec (warn) |

### CH-TIM Change over time

| Code | Entry | Status |
|---|---|---|
| CH-TIM-01 | LINE, trend, 2-4 series | spec |
| CH-TIM-02 | S-CURVE, cumulative progress vs plan | spec |
| CH-TIM-03 | AREA | spec |
| CH-TIM-04 | STACKED AREA | spec |
| CH-TIM-05 | SLOPE, two-point change | spec |
| CH-TIM-06 | SPARKLINE, inline micro-trend | spec |
| CH-TIM-07 | CALENDAR HEATMAP | spec |
| CH-TIM-08 | FAN, forecast with uncertainty bands | spec |
| CH-TIM-09 | GANTT, schedule bars with milestones | spec |
| CH-TIM-10 | CONNECTED SCATTER | spec |
| CH-TIM-11 | STREAMGRAPH | spec (warn) |
| CH-TIM-12 | HORIZON, dense multi-series in tight rows | spec (warn) |
| CH-TIM-13 | STEP, values that hold between changes (rates, policies, stock) | spec |
| CH-TIM-14 | INDEXED LINE, series rebased to 100 at a common start | spec |
| CH-TIM-15 | EVENT TIMELINE, dated milestones and annotations | spec |

### CH-PTW Part-to-whole

| Code | Entry | Status |
|---|---|---|
| CH-PTW-01 | STACKED BAR | spec |
| CH-PTW-02 | 100% STACKED BAR | spec |
| CH-PTW-03 | PIE, 3 slices max | spec (warn) |
| CH-PTW-04 | DONUT | spec (warn) |
| CH-PTW-05 | TREEMAP | spec |
| CH-PTW-06 | WAFFLE | spec |
| CH-PTW-07 | MARIMEKKO | spec |
| CH-PTW-08 | FUNNEL | spec |
| CH-PTW-09 | SUNBURST | spec (warn) |
| CH-PTW-10 | CIRCLE PACK | spec (warn) |

### CH-DEV Deviation

| Code | Entry | Status |
|---|---|---|
| CH-DEV-01 | DIVERGING BAR, +/- from reference | spec |
| CH-DEV-02 | DUMBBELL, before/after per category | spec |
| CH-DEV-03 | SPINE | spec |
| CH-DEV-04 | SURPLUS/DEFICIT AREA | spec |
| CH-DEV-05 | DIVERGING STACKED, sentiment scales | spec |

### CH-DST Distribution

| Code | Entry | Status |
|---|---|---|
| CH-DST-01 | HISTOGRAM | spec |
| CH-DST-02 | DOT PLOT | spec |
| CH-DST-03 | DOT STRIP | spec |
| CH-DST-04 | BOXPLOT | spec |
| CH-DST-05 | POPULATION PYRAMID | spec |
| CH-DST-06 | CUMULATIVE CURVE | spec |
| CH-DST-07 | BEESWARM | spec |
| CH-DST-08 | VIOLIN | spec (warn) |
| CH-DST-09 | DENSITY CURVE (KDE) | spec |
| CH-DST-10 | ERROR BARS & BANDS, uncertainty overlays for any mark | spec |

### CH-COR Correlation

| Code | Entry | Status |
|---|---|---|
| CH-COR-01 | SCATTER | spec |
| CH-COR-02 | BUBBLE, third measure as size | spec |
| CH-COR-03 | XY HEATMAP | spec |
| CH-COR-04 | COLUMN + LINE, two measures, labeled scales | spec |
| CH-COR-05 | HEXBIN, binned scatter for hundreds of points | spec |
| CH-COR-06 | PARALLEL COORDINATES | spec (warn) |
| CH-COR-07 | SCATTERPLOT MATRIX (SPLOM) | spec (warn) |

### CH-SPA Spatial

| Code | Entry | Status |
|---|---|---|
| CH-SPA-01 | CHOROPLETH | spec |
| CH-SPA-02 | PROPORTIONAL SYMBOL MAP | spec |
| CH-SPA-03 | ROUTE PROGRESS, done/pending along a corridor | spec |
| CH-SPA-04 | DOT DENSITY | spec |
| CH-SPA-05 | FLOW MAP | spec |

### CH-FLO Flow

| Code | Entry | Status |
|---|---|---|
| CH-FLO-01 | WATERFALL, start to end via +/- steps | spec |
| CH-FLO-02 | SANKEY | spec |
| CH-FLO-03 | NETWORK | spec |
| CH-FLO-04 | CHORD | spec (warn) |

### CH-TAB Tables

| Code | Entry | Status |
|---|---|---|
| CH-TAB-01 | STATUS MATRIX, entities x stages with status words | spec |
| CH-TAB-02 | HEATMAP TABLE | spec |
| CH-TAB-03 | KPI TABLE, values + deltas + micro-trends | spec |

## CP component families

| Code | Entry | Status |
|---|---|---|
| CP-TXT-01 | ACTION TITLE (with DL chrome) | spec |
| CP-TXT-02 | SOURCE LINE | spec |
| CP-KPI-01 | KPI CARD | spec |
| CP-STA-01 | STATUS CHIP (outlined, dot + word) | spec |
| CP-CAL-01 | INSIGHT CALLOUT | spec |
| CP-KPI-02 | BIG NUMBER | spec |
| CP-STA-02 | OUTLINED STAMP (blueprint register) | spec |
| CP-STR-01 | HEADER BAND | spec |
| CP-STR-02 | DRAWING TITLE BLOCK | spec |
| CP-LAB-01 | LEADER-LINE ANNOTATION (standalone) | spec |
| CP-CAL-02 | EXCEPTION ROW | spec |

## RC recipes

A recipe pins everything: DL + charts + components + exact positions on
the 1280x720 canvas. Recurring deliverables reference a recipe code, so
a weekly deck renders identically forever.

| Code | Recipe | DL | Status |
|---|---|---|---|
| RC-001 | WEEKLY PROGRESS PAGE: title + KPI strip + S-curve + chips + callout | DL-02 | spec |
| RC-002 | ANALYSIS PAGE: kicker title + waterfall at 70% of page | DL-03 | spec |
| RC-003 | READINESS BOARD: title + status matrix + critical chip + callout | DL-04 | spec |
| RC-004 | EXECUTIVE BRIEF: claim + big number + bridge + decision + owner (NR-01) | DL-01 | spec |
| RC-005 | EXCEPTION FLASH: header band + bullet board + exception rows + stamp (NR-04) | DL-12 | spec |
| RC-006 | EVIDENCE READOUT: question + exhibit + finding + evidence-only stamp (NR-02) | DL-14 | spec |

## Cross-cutting mechanisms (MX, built as specs)

| Code | Mechanism | Status |
|---|---|---|
| MX-01 | SMALL MULTIPLES, faceting any chart entry into a shared-scale grid | spec |
| MX-02 | FIT OVERLAYS, declared fits on COR charts (no silent trend lines) | spec |

Specs: `catalogue/mechanisms/`.

## Excluded, with reasons (benchmarked against Datawrapper, Flourish, Vega-Lite, Observable)

| Type | Why OVP excludes it |
|---|---|
| Bar/line chart races, animation | v0.1 is a static, deterministic, print-safe protocol; motion is a future layer, not a chart |
| Word clouds | area encodes string length, not value; perceptually dishonest |
| 3D anything | violates the AI-tells blacklist and Cleveland-McGill; no exceptions |
| Radial bar, pyramid pie | angle+radius double-distortion (FN-06) |
| Ternary, Q-Q, contour, raster | scientific niches outside the reporting domain; adopt on demand via PR |
| Candlestick | finance-domain-specific; add when a finance adopter exists |
| Trail / comet marks | decoration over information |
| Quiz, survey cards, interactive stories | applications, not visualizations; out of protocol scope |

## Output targets

The catalogue is renderer-agnostic by design: specs are exact px/hex,
so any backend can consume them. Current reference implementation: SVG
(`tools/render.py`). Planned backends, in order: PPTX (python-pptx),
HTML, XLSX, Power BI themes. Not now; specs first.
