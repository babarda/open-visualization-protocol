# The OVP Manifesto

The constitutional layer of the Open Visualization Protocol. PROTOCOL.md
says how; this document says why, and names the laws that never break.

## The problem

Every organization redraws the same charts every week, and every one of
them redraws them differently: different colors, different baselines,
different lies. Style guides do not fix this because prose does not
compile. Reviewers catch a truncated axis one week and miss it the
next.

AI made this worse before it made it better. Agents produce plausible
charts at scale: each one reasonable alone, no two consistent, and none
accountable to a rule. Asking a model to "make it look professional"
outsources judgment to noise.

## The idea

A visualization is an instruction, not an artwork:

```
Render CH-TIM-02 in DL-03 with data.json
```

If the instruction is exact, the output is exact. Design judgment moves
out of each deliverable and into the protocol, once, where it can be
reviewed, versioned, and validated. Humans decide the rules; every
render after that is reproduction, not re-invention.

## The laws

1. **Determinism.** Same spec, same tokens, same data: the same output,
   byte for byte, every run, every machine. No randomness, no
   timestamps, no jitter, no "approximately".
2. **Roles, never hex.** Specs name color roles; design languages bind
   roles to hex. Rebranding is swapping one token file.
3. **Honesty by construction.** Zero baselines. Direct labels, not
   legends. Declared inputs only: no silent smoothing, no silent trend
   lines, no unstated normalization. Every chart names its
   anti-patterns and ships a QA checklist.
4. **Message first.** Charts are coded by what the message is
   (ranking, deviation, distribution), never by shape. The first
   question is always "what am I saying", not "which chart is pretty".
5. **Canonical JSON, generated everything else.** Specs and tokens are
   the single source of truth. Blocks, choosers, registries, previews,
   and the website are generated from them. Duplication is drift, and
   drift is a validation failure.
6. **The gate is law.** Nothing ships unless validation passes:
   schemas, contrast, data sanity, and byte-identical golden
   re-renders. A red gate blocks everything, always.
7. **Codes are forever.** An identifier is never renumbered and never
   reused. Retired objects keep their code. External references must
   stay valid for decades.

## What OVP is not

Not a charting library: it does not compete with renderers, it makes
them exchangeable. Not a BI tool: it has no data pipeline and wants
none. Not a style guide: prose that cannot fail validation is opinion,
and OVP has no opinions it cannot enforce. Not a gallery: the count of
charts is the least interesting number in the repository.

## The bet

If describing a visualization exactly is possible, then the same
description can drive a slide, a dashboard, a printed page, and an AI
agent, and they will all agree. Design becomes infrastructure.
