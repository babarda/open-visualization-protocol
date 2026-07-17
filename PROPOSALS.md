# Open proposals against OVP

Contributions are proposals against this repository until the formal
RFC process starts at v1.0 (CONTRIBUTING.md, PROTOCOL.md section 6).
This file holds the proposals that are open: what real use exposed,
what it cost, and what the fix would be. A proposal leaves this file
when it lands in PROTOCOL.md or when it is rejected with a reason.

Nothing here is normative. Do not implement from this file.

---

## PR-01 . `palette.warning` is optional, so every three-state encoding invents its own middle

Status: open. Raised 2026-07-17 from the first production binding of
the languages (the XER Gantt on babarda.com).

`schema/dl.schema.json` requires `positive` and `negative` in every
palette. It does not require `warning`. Three of the sixteen languages
declare one:

| Declares `warning` | Does not |
|---|---|
| DL-02 KATA, DL-04 SHILPA, DL-12 NOROSHI | the other thirteen |

The gap only shows up when something real binds the tokens. A schedule
Gantt reads three states, not two: on track, at risk, late. So does a
budget, a register of actions, a punch list, a RAG status. In thirteen
languages out of sixteen the renderer has no role to ask for, and the
protocol's first law is that a renderer never names a colour. The XER
Gantt now mixes `negative` and `positive` to make the middle state and
says so in its status line, which is a workaround wearing a label, not
a binding.

The cost: two renderers that both speak OVP will draw at-risk in
different colours from the same tokens. That breaks determinism, which
MANIFESTO.md states as the law that never breaks.

Options, in the order they look defensible:

1. Require `warning` in `dl.schema.json` and write one into all
   thirteen languages. This is a minor `ovp_version` bump plus a
   migration note under section 6.2, and it is additive at 1.0, so it
   survives the freeze either way. It costs thirteen authored colours,
   each of which is a real design decision that the language's author
   should make rather than a mixer.
2. Keep it optional but publish a normative derivation, so every
   renderer derives the same middle from the same two roles. Cheaper
   now, and it makes an aesthetic accident permanent: a mix of
   AGRAW's negative and positive is not a colour anyone chose.
3. Leave it. Then a three-state chart is out of scope for thirteen
   languages, and CHOOSER should say so rather than let a renderer
   discover it.

Recommendation: option 1. The whole point of a design language is that
someone decided.

---

## PR-02 . `legend_policy` has nothing to say about marks coloured by role

Status: open. Raised 2026-07-17, same source.

Wave B made `legend_policy` required in every language, with
`direct-labels-only` as the common value. It assumes a legend decodes
series, so removing it and labelling each series in place is strictly
better.

That assumption holds for a line chart and fails for a Gantt. A Gantt
bar carries its state in its fill: complete, remaining, critical,
near-critical, baseline. There is no series to label and no room to
write the state on a bar four pixels tall. Drop the key and the chart
stops being readable, so the XER Gantt keeps the key in every language
and leaves `legend_policy` unbound. A required field that a conforming
renderer must ignore is worse than no field: it reads as governed.

Options:

1. Scope the policy in PROTOCOL.md: `legend_policy` governs
   series-encoded marks. Marks encoded by palette role always carry a
   role key. Documentation only, no schema change.
2. Add a `role-key-required` value and set it per language.
3. Move the policy from the language to the chart entry, since whether
   direct labels are possible is a property of the chart, not of the
   taste of the language.

Recommendation: option 1 now, option 3 as the honest version if the
same gap turns up in a second chart family. CH-TIM-09 GANTT is the
known case; SPA and FLO entries are worth a look before deciding.
