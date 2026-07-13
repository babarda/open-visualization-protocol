# FN-01 . Token contract

The rule that makes the whole catalogue themeable and deterministic:

**Chart and component specs reference color ROLES, never hex values.
Design languages (DL files) bind roles to hex. Rebranding = swapping the
DL token file. No spec changes, no re-authoring.**

## Required roles (every DL must bind all of these)

| Role | Meaning |
|---|---|
| `background` | page/canvas fill |
| `ink` | headings, key numbers, strongest text |
| `body` | supporting text, labels, sources |
| `primary` | the one accent; highlights, key series |
| `muted` | context series, de-emphasized marks |
| `gridline` | chart gridlines |
| `hairline` | rules, baselines, separators |
| `positive` | good deltas (always paired with a word, never alone) |
| `negative` | bad deltas (same) |

Optional roles a DL may add: `panel`, `benchmark`, `warning`, `primaryDark`,
and others. Specs that want an optional role declare a fallback chain, for
example `"context": ["benchmark", "muted"]`: first role present in the
palette wins. The renderer resolves the chain, so a spec never breaks on a
DL that lacks an optional role.

## Rules

1. Hex values live in `tokens/DL-xx.json` only. A hex value inside a chart
   spec or component spec fails validation on sight.
2. All hex is `#RRGGBB` uppercase. Enforced by `schema/dl.schema.json` and
   `tools/validate.py`.
3. `ink` and `body` must reach 4.5:1 contrast on `background` (WCAG AA).
   Enforced by `tools/validate.py`.
4. Fonts follow the same contract: specs reference `display` or `body`,
   the DL binds each to a family stack whose last entries are
   installed-everywhere fallbacks.
