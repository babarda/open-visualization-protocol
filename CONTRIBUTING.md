# Contributing to OVP

Until a formal RFC process exists (it starts at v1.0, see PROTOCOL.md
section 6), contributions are proposals against this repository. Every
contribution, without exception, ends with `python tools/validate.py`
printing ALL CHECKS PASSED.

## Ground rules

- Canonical files are JSON under `specs/`, `tokens/`, `patterns/`,
  `components/`, `recipes/`, `decision/`. Everything else that a tool
  can generate IS generated: never hand-edit `blocks/`, `docs/`,
  `preview.html`, `CHOOSER.md`, `DECIDER.md`, `PATTERNS.md`,
  `REGISTRY.json`, or `catalogue/languages/INDEX.md`.
- After any canonical change run, in order: `tools/render.py` for
  affected goldens, `tools/build_blocks.py`, `tools/preview.py`,
  `tools/build_site.py`, then `tools/validate.py`.
- No hex values and no adjectives inside specs. Colors are roles;
  positions are px.
- Brand-agnostic everywhere public: no client names, no project names.
- Codes are permanent. Take the next free number; never renumber,
  never reuse.
- Prose style: plain, direct, no em-dashes.

## Adding a chart object (CH)

1. A real occasion no existing entry serves; check TAXONOMY.md and the
   `see_instead` exits of neighboring entries first.
2. Full spec: `meta` (intent from the controlled vocabulary), use_when,
   not_when, data_shape, exact layout in px, rules, role chains,
   anti_patterns, qa.
3. Renderer support in `tools/render.py` (deterministic: no randomness,
   no dates, fixed float formatting) and a data-sanity check in
   `tools/validate.py`.
4. Golden data plus renders in all 16 design languages under
   `golden/<code>/` (protocol minimum is 2 DLs; this repo renders all).
5. TAXONOMY.md row set to `spec` in the same commit.

## Adding a design language (DL)

1. An occasion no existing language serves.
2. Complete token file against `schema/dl.schema.json`: all required
   roles, installed fallback fonts, chrome flags, philosophy block
   (civilization, principle, motto, laws), status `candidate`.
3. AA contrast (ink and body on background >= 4.5:1); the validator
   checks it.
4. One signature move: something this language does that no other does.
5. Golden renders regenerate for every chart; candidate promotes to
   adopted after two real deliverables ship in it.

## Adding a pattern (PT)

Recognition, meaning, business_reading, show_with (existing CH codes
only; validated), avoid. Perceptual claims trace to a named source, as
in FN-06.

## Changing anything that exists

Before 1.0: allowed with a minor `ovp_version` bump on the touched
files and a migration note in the commit. Golden churn must be
deliberate: re-render, inspect, commit the new baseline in one change.
After 1.0: never break, only extend (PROTOCOL.md section 6.2).
