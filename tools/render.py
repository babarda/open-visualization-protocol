"""Deterministic SVG renderer for VizCatalogue chart entries.

Same spec + same tokens + same data = byte-identical SVG, every run,
every machine. No timestamps, no randomness, fixed float formatting.

Usage:
    python tools/render.py --spec specs/CH-01.json --tokens tokens/DL-02.json \
        --data golden/CH-01/data.json --out golden/CH-01/CH-01_DL-02.svg
"""

import argparse
import json
import math
import sys
from pathlib import Path


def fmt(v):
    """Fixed float formatting: max 2 decimals, no trailing zeros, no -0."""
    s = f"{float(v):.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def merge(base, over):
    out = dict(base)
    for k, v in over.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = merge(out[k], v)
        else:
            out[k] = v
    return out


def resolve_role(palette, role_chain):
    """First palette key present in the chain wins (e.g. benchmark then muted)."""
    for role in role_chain:
        if role in palette:
            return palette[role]
    raise KeyError(f"none of roles {role_chain} in palette")


def nice_top(maxv, target=5, steps=(1, 2, 5, 10)):
    """Deterministic nice-scale: top of axis and tick step."""
    if maxv <= 0:
        return 1, 1
    raw = maxv / target
    mag = 10 ** math.floor(math.log10(raw))
    step = steps[-1] * mag
    for m in steps:
        if m * mag >= raw:
            step = m * mag
            break
    top = math.ceil(maxv / step) * step
    return top, step


def text(x, y, s, size, family, fill, weight=400, anchor="start",
         baseline=None, spacing=None, style=None):
    a = [f'x="{fmt(x)}"', f'y="{fmt(y)}"', f'font-size="{fmt(size)}"',
         f'font-family="{family}"', f'fill="{fill}"', f'font-weight="{weight}"']
    if anchor != "start":
        a.append(f'text-anchor="{anchor}"')
    if baseline:
        a.append(f'dominant-baseline="{baseline}"')
    if spacing:
        a.append(f'letter-spacing="{fmt(spacing)}"')
    if style:
        a.append(f'font-style="{style}"')
    return f'<text {" ".join(a)}>{esc(s)}</text>'


def line_el(x1, y1, x2, y2, stroke, width=1):
    return (f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" y2="{fmt(y2)}" '
            f'stroke="{stroke}" stroke-width="{fmt(width)}"/>')


def chrome_and_title(parts, spec, tok, data):
    """Kicker + eyebrow (if the DL asks) + action title. Returns nothing; appends."""
    if spec.get("_bare"):
        return
    pal, L = tok["palette"], spec["layout"]
    disp = tok["fonts"]["display"]
    with_eyebrow = tok["chrome"]["eyebrow"] and data.get("eyebrow")
    if tok["chrome"]["kicker"]:
        k = L["kicker"]
        parts.append(f'<rect x="{fmt(k["x"])}" y="{fmt(k["y"])}" width="{fmt(k["w"])}" '
                     f'height="{fmt(k["h"])}" fill="{pal["primary"]}"/>')
    if with_eyebrow:
        e = L["eyebrow"]
        parts.append(text(e["x"], e["y"], data["eyebrow"], e["size"],
                          tok["fonts"]["body"]["family"], pal["body"],
                          weight=600, spacing=e["letter_spacing"]))
    t = L["title"]
    ty = t["y_with_eyebrow"] if with_eyebrow else t["y"]
    parts.append(text(t["x"], ty, data["title"], t["size"], disp["family"],
                      pal["ink"], weight=disp["weight"]))


def source_line(parts, spec, tok, data):
    if spec.get("_bare"):
        return
    s = spec["layout"]["source"]
    parts.append(text(s["x"], s["y"], data["source"], s["size"],
                      tok["fonts"]["body"]["family"], tok["palette"]["body"]))


def render_bar_h(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    bh, gap = L["bar_height"], L["bar_gap"]

    rows = sorted(data["categories"], key=lambda r: (-r["value"], r["label"]))
    vmax = max(r["value"] for r in rows)
    span = p["right"] - p["left"]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    for i, r in enumerate(rows):
        y = p["top"] + i * (bh + gap)
        w = (r["value"] / vmax) * span
        hi = bool(r.get("highlight"))
        fill = resolve_role(pal, roles["bar_highlight"] if hi else roles["bar"])
        parts.append(f'<rect x="{fmt(p["left"])}" y="{fmt(y)}" width="{fmt(w)}" '
                     f'height="{fmt(bh)}" fill="{fill}"/>')
        cy = y + bh / 2
        cl = L["category_label"]
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
        vl = L["value_label"]
        label = f'{r["value"]} {data["unit"]}' if i == 0 else str(r["value"])
        parts.append(text(p["left"] + w + vl["offset"], cy, label, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600 if hi else 400, baseline="middle"))

    y_end = p["top"] + len(rows) * (bh + gap) - gap + 8
    parts.append(line_el(p["left"], p["top"] - 8, p["left"], y_end,
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_bar_v(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    bw = L["bar_width"]

    rows = data["categories"]  # input order preserved unless the spec sorts
    if spec.get("scale", {}).get("sort") == "desc":
        rows = sorted(rows, key=lambda r: (-r["value"], r["label"]))
    vmax = max(r["value"] for r in rows)
    n = len(rows)
    slot = (p["right"] - p["left"]) / n

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    for i, r in enumerate(rows):
        cx = p["left"] + (i + 0.5) * slot
        h = (r["value"] / vmax) * (p["bottom"] - p["top"])
        y = p["bottom"] - h
        hi = bool(r.get("highlight"))
        fill = resolve_role(pal, roles["bar_highlight"] if hi else roles["bar"])
        parts.append(f'<rect x="{fmt(cx - bw / 2)}" y="{fmt(y)}" width="{fmt(bw)}" '
                     f'height="{fmt(h)}" fill="{fill}"/>')
        vl = L["value_label"]
        label = f'{r["value"]} {data["unit"]}' if i == 0 else str(r["value"])
        parts.append(text(cx, y - vl["offset"], label, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600 if hi else 400, anchor="middle"))
        cl = L["category_label"]
        parts.append(text(cx, p["bottom"] + cl["offset"], r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="middle"))

    parts.append(line_el(p["left"], p["bottom"], p["right"], p["bottom"],
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_line(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]

    xs = data["x"]
    n = len(xs)
    vmax = max(max(s["values"]) for s in data["series"])
    top, step = nice_top(vmax, sc["target_ticks"], tuple(sc["nice_steps"]))

    def X(i):
        return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

    def Y(v):
        return p["bottom"] - (v / top) * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    t = 0
    while t <= top:
        y = Y(t)
        stroke = resolve_role(pal, roles["zero_line"] if t == 0 else roles["gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        label = f"{t}{data['unit']}" if t == top else str(t)
        parts.append(text(p["left"] - tl["offset"], y, label, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += step

    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(X(i), p["bottom"] + xl["offset"], lab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))

    ordered = ([s for s in data["series"] if s["role"] == "context"]
               + [s for s in data["series"] if s["role"] == "key"])
    sl = L["series_label"]
    for s in ordered:
        key = s["role"] == "key"
        stroke = resolve_role(pal, roles["key"] if key else roles["context"])
        pts = " ".join(f"{fmt(X(i))},{fmt(Y(v))}" for i, v in enumerate(s["values"]))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" '
                     f'stroke-width="{fmt(L["stroke"]["key" if key else "context"])}"/>')
        parts.append(text(p["right"] + sl["offset"], Y(s["values"][-1]), s["name"],
                          sl["size"], body,
                          resolve_role(pal, roles["key_label" if key else "context_label"]),
                          weight=600 if key else 400, baseline="middle"))

    ann = data.get("annotation")
    if ann:
        series = next(s for s in data["series"] if s["name"] == ann["series"])
        px, py = X(ann["index"]), Y(series["values"][ann["index"]])
        an = L["annotation"]
        anchor = ann.get("anchor", "start")
        lx = ann["tx"] + 4 if anchor == "end" else ann["tx"] - 4
        parts.append(line_el(px, py, lx, ann["ty"] - 5,
                             resolve_role(pal, roles["annotation"])))
        parts.append(text(ann["tx"], ann["ty"], ann["text"], an["size"], body,
                          resolve_role(pal, roles["annotation"]),
                          anchor=anchor, style=an["style"]))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_bar_v_stacked(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    bw = L["bar_width"]
    normalize = spec.get("scale", {}).get("normalize", False)

    xs = data["x"]
    segs = data["series"]
    n = len(xs)
    totals = [sum(s["values"][i] for s in segs) for i in range(n)]
    vmax = max(totals)
    PH = p["bottom"] - p["top"]
    slot = (p["right"] - p["left"]) / n

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    vl = L["value_label"]
    xl = L["x_label"]
    for i, x in enumerate(xs):
        cx = p["left"] + (i + 0.5) * slot
        ycur = p["bottom"]
        for j, s in enumerate(segs):
            h = (s["values"][i] / totals[i] if normalize
                 else s["values"][i] / vmax) * PH
            ycur -= h
            fill = resolve_role(pal, roles["segments"][j])
            parts.append(f'<rect x="{fmt(cx - bw / 2)}" y="{fmt(ycur)}" '
                         f'width="{fmt(bw)}" height="{fmt(h)}" fill="{fill}"/>')
        if normalize:
            label = f'{segs[0]["values"][i] / totals[i] * 100:.0f}%'
        else:
            label = f'{totals[i]} {data["unit"]}' if i == 0 else str(totals[i])
        parts.append(text(cx, ycur - vl["offset"], label, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), anchor="middle"))
        parts.append(text(cx, p["bottom"] + xl["offset"], x, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))

    sl = L["segment_label"]
    lx = p["right"] + sl["offset"]
    ycur = p["bottom"]
    last_total = totals[-1]
    for j, s in enumerate(segs):
        h = (s["values"][-1] / last_total if normalize
             else s["values"][-1] / vmax) * PH
        cy = ycur - h / 2
        ycur -= h
        fill = resolve_role(pal, roles["segments"][j])
        parts.append(f'<rect x="{fmt(lx)}" y="{fmt(cy - 4)}" width="8" height="8" '
                     f'fill="{fill}"/>')
        parts.append(text(lx + 14, cy, s["name"], sl["size"], body,
                          resolve_role(pal, roles["segment_label"]), baseline="middle"))

    parts.append(line_el(p["left"], p["bottom"], p["right"], p["bottom"],
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_area(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]

    xs = data["x"]
    n = len(xs)
    vmax = max(max(s["values"]) for s in data["series"])
    top, step = nice_top(vmax, sc["target_ticks"], tuple(sc["nice_steps"]))

    def X(i):
        return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

    def Y(v):
        return p["bottom"] - (v / top) * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    t = 0
    while t <= top:
        y = Y(t)
        stroke = resolve_role(pal, roles["zero_line"] if t == 0 else roles["gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        label = f"{t}{data['unit']}" if t == top else str(t)
        parts.append(text(p["left"] - tl["offset"], y, label, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += step

    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(X(i), p["bottom"] + xl["offset"], lab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))

    sl = L["series_label"]
    key = next(s for s in data["series"] if s["role"] == "key")
    ctx = [s for s in data["series"] if s["role"] == "context"]
    for s in ctx:
        stroke = resolve_role(pal, roles["context"])
        pts = " ".join(f"{fmt(X(i))},{fmt(Y(v))}" for i, v in enumerate(s["values"]))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" '
                     f'stroke-width="{fmt(L["stroke"]["context"])}"/>')
        parts.append(text(p["right"] + sl["offset"], Y(s["values"][-1]), s["name"],
                          sl["size"], body, resolve_role(pal, roles["context_label"]),
                          baseline="middle"))
    kfill = resolve_role(pal, roles["key"])
    poly = " ".join(f"{fmt(X(i))},{fmt(Y(v))}" for i, v in enumerate(key["values"]))
    parts.append(f'<polygon points="{fmt(p["left"])},{fmt(p["bottom"])} {poly} '
                 f'{fmt(p["right"])},{fmt(p["bottom"])}" fill="{kfill}" '
                 f'fill-opacity="{fmt(L["fill_opacity"])}"/>')
    parts.append(f'<polyline points="{poly}" fill="none" stroke="{kfill}" '
                 f'stroke-width="{fmt(L["stroke"]["key"])}"/>')
    parts.append(text(p["right"] + sl["offset"], Y(key["values"][-1]), key["name"],
                      sl["size"], body, resolve_role(pal, roles["key_label"]),
                      weight=600, baseline="middle"))

    ann = data.get("annotation")
    if ann:
        series = next(s for s in data["series"] if s["name"] == ann["series"])
        px, py = X(ann["index"]), Y(series["values"][ann["index"]])
        an = L["annotation"]
        anchor = ann.get("anchor", "start")
        lx = ann["tx"] + 4 if anchor == "end" else ann["tx"] - 4
        parts.append(line_el(px, py, lx, ann["ty"] - 5,
                             resolve_role(pal, roles["annotation"])))
        parts.append(text(ann["tx"], ann["ty"], ann["text"], an["size"], body,
                          resolve_role(pal, roles["annotation"]),
                          anchor=anchor, style=an["style"]))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_waterfall(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    bw = L["bar_width"]

    start = data["start"]
    steps = data["steps"]
    cums = [start["value"]]
    for st in steps:
        cums.append(cums[-1] + st["delta"])
    end_val = cums[-1]
    vmax = max(cums)
    n = len(steps) + 2
    slot = (p["right"] - p["left"]) / n
    PH = p["bottom"] - p["top"]

    def Y(v):
        return p["bottom"] - (v / vmax) * PH

    def CX(k):
        return p["left"] + (k + 0.5) * slot

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    vl = L["value_label"]
    xl = L["x_label"]
    tot = resolve_role(pal, roles["total"])
    labels = [start["label"]] + [st["label"] for st in steps] + [data["end_label"]]

    parts.append(f'<rect x="{fmt(CX(0) - bw / 2)}" y="{fmt(Y(start["value"]))}" '
                 f'width="{fmt(bw)}" height="{fmt(p["bottom"] - Y(start["value"]))}" fill="{tot}"/>')
    parts.append(text(CX(0), Y(start["value"]) - vl["offset"],
                      f'{start["value"]} {data["unit"]}', vl["size"], body,
                      resolve_role(pal, roles["value_label"]), anchor="middle"))

    for i, st in enumerate(steps):
        k = i + 1
        y1, y2 = Y(cums[i]), Y(cums[i + 1])
        top_y, h = min(y1, y2), abs(y1 - y2)
        role = roles["increase"] if st["delta"] > 0 else roles["decrease"]
        parts.append(f'<rect x="{fmt(CX(k) - bw / 2)}" y="{fmt(top_y)}" '
                     f'width="{fmt(bw)}" height="{fmt(h)}" fill="{resolve_role(pal, role)}"/>')
        lab = f'+{st["delta"]}' if st["delta"] > 0 else str(st["delta"])
        parts.append(text(CX(k), top_y - vl["offset"], lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), anchor="middle"))

    parts.append(f'<rect x="{fmt(CX(n - 1) - bw / 2)}" y="{fmt(Y(end_val))}" '
                 f'width="{fmt(bw)}" height="{fmt(p["bottom"] - Y(end_val))}" fill="{tot}"/>')
    parts.append(text(CX(n - 1), Y(end_val) - vl["offset"], str(end_val), vl["size"],
                      body, resolve_role(pal, roles["value_label"]),
                      weight=600, anchor="middle"))

    conn = resolve_role(pal, roles["connector"])
    for k in range(n - 1):
        y = Y(cums[k])
        parts.append(f'<line x1="{fmt(CX(k) + bw / 2)}" y1="{fmt(y)}" '
                     f'x2="{fmt(CX(k + 1) - bw / 2)}" y2="{fmt(y)}" '
                     f'stroke="{conn}" stroke-width="1" stroke-dasharray="4 3"/>')

    for k, lab in enumerate(labels):
        parts.append(text(CX(k), p["bottom"] + xl["offset"], lab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))
    parts.append(line_el(p["left"], p["bottom"], p["right"], p["bottom"],
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_bar_h_div(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    bh, gap = L["bar_height"], L["bar_gap"]

    rows = sorted(data["categories"], key=lambda r: (-r["value"], r["label"]))
    amax = max(abs(r["value"]) for r in rows)
    zero_x = (p["left"] + p["right"]) / 2
    half = (p["right"] - p["left"]) / 2

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    vl = L["value_label"]
    cl = L["category_label"]
    for i, r in enumerate(rows):
        y = p["top"] + i * (bh + gap)
        cy = y + bh / 2
        w = abs(r["value"]) / amax * half
        pos = r["value"] >= 0
        fill = resolve_role(pal, roles["positive_bar" if pos else "negative_bar"])
        x = zero_x if pos else zero_x - w
        parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" '
                     f'height="{fmt(bh)}" fill="{fill}"/>')
        lab = f'+{r["value"]}' if r["value"] > 0 else str(r["value"])
        if i == 0:
            lab = f'{lab} {data["unit"]}'
        lx = zero_x + w + vl["offset"] if pos else zero_x - w - vl["offset"]
        parts.append(text(lx, cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          anchor="start" if pos else "end", baseline="middle"))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))

    y_end = p["top"] + len(rows) * (bh + gap) - gap + 8
    parts.append(line_el(zero_x, p["top"] - 8, zero_x, y_end,
                         resolve_role(pal, roles["zero_line"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_matrix(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    rh = L["row_height"]

    cols = data["columns"]
    rows = data["rows"]
    cw = (p["right"] - p["left"]) / len(cols)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    hl = L["header_label"]
    for j, c in enumerate(cols):
        parts.append(text(p["left"] + j * cw + 12, p["top"] - hl["offset"], c,
                          hl["size"], body, resolve_role(pal, roles["header"]),
                          weight=600, spacing=1))

    rl = L["row_label"]
    st = L["status"]
    hair = resolve_role(pal, roles["rule"])
    for i, r in enumerate(rows):
        y = p["top"] + i * rh
        cy = y + rh / 2
        parts.append(line_el(p["left"] - L["row_label"]["gutter"], y, p["right"], y, hair))
        parts.append(text(p["left"] - rl["offset"], cy, r["label"], rl["size"], body,
                          resolve_role(pal, roles["row_label"]),
                          weight=600, anchor="end", baseline="middle"))
        for j, cell in enumerate(r["cells"]):
            cx = p["left"] + j * cw + 12
            fill = resolve_role(pal, roles[f"status_{cell}"])
            parts.append(f'<rect x="{fmt(cx)}" y="{fmt(cy - 4)}" width="8" height="8" '
                         f'fill="{fill}"/>')
            parts.append(text(cx + 14, cy, spec["display"][cell], st["size"], body,
                              resolve_role(pal, roles["status_word"]),
                              baseline="middle"))
    y_end = p["top"] + len(rows) * rh
    parts.append(line_el(p["left"] - L["row_label"]["gutter"], y_end, p["right"], y_end, hair))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def mix_hex(c1, c2, t):
    """Deterministic linear blend c1 -> c2 at t in [0,1]."""
    def ch(a, b):
        return round(int(a, 16) + (int(b, 16) - int(a, 16)) * t)
    return "#" + "".join(f"{ch(c1[i:i + 2], c2[i:i + 2]):02X}"
                         for i in (1, 3, 5))


def render_pie(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    cx, cy, r = L["cx"], L["cy"], L["r"]
    inner = L.get("inner_r", 0)

    rows = sorted(data["slices"], key=lambda s: (-s["value"], s["label"]))
    total = sum(s["value"] for s in rows)

    def pt(deg, rad):
        th = math.radians(deg)
        return cx + rad * math.cos(th), cy + rad * math.sin(th)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    ang = -90.0
    for i, row in enumerate(rows):
        f = row["value"] / total
        a2 = ang + f * 360.0
        large = 1 if f > 0.5 else 0
        x1, y1 = pt(ang, r)
        x2, y2 = pt(a2, r)
        fill = resolve_role(pal, roles["slices"][i])
        if inner:
            xi1, yi1 = pt(ang, inner)
            xi2, yi2 = pt(a2, inner)
            path = (f"M {fmt(x1)},{fmt(y1)} A {fmt(r)} {fmt(r)} 0 {large} 1 "
                    f"{fmt(x2)},{fmt(y2)} L {fmt(xi2)},{fmt(yi2)} "
                    f"A {fmt(inner)} {fmt(inner)} 0 {large} 0 {fmt(xi1)},{fmt(yi1)} Z")
        else:
            path = (f"M {fmt(cx)},{fmt(cy)} L {fmt(x1)},{fmt(y1)} "
                    f"A {fmt(r)} {fmt(r)} 0 {large} 1 {fmt(x2)},{fmt(y2)} Z")
        parts.append(f'<path d="{path}" fill="{fill}" '
                     f'stroke="{pal["background"]}" stroke-width="2"/>')
        mid = (ang + a2) / 2
        lx, ly = pt(mid, r + L["label_offset"])
        anchor = "start" if math.cos(math.radians(mid)) >= 0 else "end"
        parts.append(text(lx, ly, f'{row["label"]}  {round(f * 100)}%',
                          L["label_size"], body, resolve_role(pal, roles["label"]),
                          anchor=anchor, baseline="middle"))
        ang = a2

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_scatter(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]

    pts = data["points"]
    topx, stepx = nice_top(max(q["x"] for q in pts), sc["target_ticks"],
                           tuple(sc["nice_steps"]))
    topy, stepy = nice_top(max(q["y"] for q in pts), sc["target_ticks"],
                           tuple(sc["nice_steps"]))
    sized = any("size" in q for q in pts)
    smax = max(q.get("size", 1) for q in pts)

    def X(v):
        return p["left"] + (v / topx) * (p["right"] - p["left"])

    def Y(v):
        return p["bottom"] - (v / topy) * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    t = 0
    while t <= topy:
        y = Y(t)
        stroke = resolve_role(pal, roles["zero_line"] if t == 0 else roles["gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        lab = f'{t}{data["unit_y"]}' if t == topy else str(t)
        parts.append(text(p["left"] - tl["offset"], y, lab, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += stepy
    t = 0
    while t <= topx:
        x = X(t)
        stroke = resolve_role(pal, roles["zero_line"] if t == 0 else roles["gridline"])
        parts.append(line_el(x, p["top"], x, p["bottom"], stroke))
        lab = f'{t}{data["unit_x"]}' if t == topx else str(t)
        parts.append(text(x, p["bottom"] + L["x_label"]["offset"], lab,
                          L["x_label"]["size"], body,
                          resolve_role(pal, roles["tick_label"]), anchor="middle"))
        t += stepx

    if spec["scale"].get("connect"):
        trail = " ".join(f"{fmt(X(q['x']))},{fmt(Y(q['y']))}" for q in pts)
        parts.append(f'<polyline points="{trail}" fill="none" '
                     f'stroke="{resolve_role(pal, roles["point"])}" stroke-width="1.5"/>')

    pl = L["point_label"]
    for q in pts:
        hi = bool(q.get("highlight"))
        if sized:
            rr = max(4, math.sqrt(q.get("size", 1) / smax) * L["bubble_max_r"])
        else:
            rr = L["dot_r"]
        fill = resolve_role(pal, roles["point_highlight" if hi else "point"])
        parts.append(f'<circle cx="{fmt(X(q["x"]))}" cy="{fmt(Y(q["y"]))}" '
                     f'r="{fmt(rr)}" fill="{fill}"/>')
        parts.append(text(X(q["x"]) + rr + pl["offset"], Y(q["y"]), q["label"],
                          pl["size"], body,
                          resolve_role(pal, roles["label_highlight" if hi else "label"]),
                          weight=600 if hi else 400, baseline="middle"))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_heatmap(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    rh = L["row_height"]
    per_column = spec["scale"]["normalize"] == "column"

    cols = data["columns"]
    rows = data["rows"]
    cw = (p["right"] - p["left"]) / len(cols)
    lo = resolve_role(pal, roles["cell_low"])
    hi = resolve_role(pal, roles["cell_high"])

    if per_column:
        maxes = [max(r["values"][j] for r in rows) for j in range(len(cols))]
    else:
        gmax = max(v for r in rows for v in r["values"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    hl = L["header_label"]
    for j, c in enumerate(cols):
        parts.append(text(p["left"] + (j + 0.5) * cw, p["top"] - hl["offset"], c,
                          hl["size"], body, resolve_role(pal, roles["header"]),
                          weight=600, anchor="middle", spacing=1))
    rl = L["row_label"]
    vl = L["value_label"]
    for i, r in enumerate(rows):
        y = p["top"] + i * rh
        cy = y + rh / 2
        parts.append(text(p["left"] - rl["offset"], cy, r["label"], rl["size"], body,
                          resolve_role(pal, roles["row_label"]),
                          weight=600, anchor="end", baseline="middle"))
        for j, v in enumerate(r["values"]):
            t = v / (maxes[j] if per_column else gmax)
            cell = mix_hex(lo, hi, t)
            parts.append(f'<rect x="{fmt(p["left"] + j * cw + 1)}" y="{fmt(y + 1)}" '
                         f'width="{fmt(cw - 2)}" height="{fmt(rh - 2)}" fill="{cell}"/>')
            tfill = lo if t > 0.55 else resolve_role(pal, roles["value"])
            parts.append(text(p["left"] + (j + 0.5) * cw, cy, str(v), vl["size"],
                              body, tfill, anchor="middle", baseline="middle"))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _sq_worst(row, side):
    s = sum(row)
    return max(max(side * side * a / (s * s), s * s / (side * side * a)) for a in row)


def _sq_layout(row, x, y, w, h, rects):
    s = sum(row)
    if w >= h:
        rw = s / h
        ry = y
        for a in row:
            rects.append((x, ry, rw, a / rw))
            ry += a / rw
        return x + rw, y, w - rw, h
    rh = s / w
    rx = x
    for a in row:
        rects.append((rx, y, a / rh, rh))
        rx += a / rh
    return x, y + rh, w, h - rh


def squarify(areas, x, y, w, h):
    """Bruls squarified treemap; deterministic for a fixed input order."""
    rects = []
    row = []
    areas = list(areas)
    while areas:
        side = min(w, h)
        a = areas[0]
        if not row or _sq_worst(row + [a], side) <= _sq_worst(row, side):
            row.append(a)
            areas.pop(0)
        else:
            x, y, w, h = _sq_layout(row, x, y, w, h, rects)
            row = []
    if row:
        _sq_layout(row, x, y, w, h, rects)
    return rects


def render_treemap(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]

    rows = sorted(data["categories"], key=lambda r: (-r["value"], r["label"]))
    pw, ph = p["right"] - p["left"], p["bottom"] - p["top"]
    scale = pw * ph / sum(r["value"] for r in rows)
    rects = squarify([r["value"] * scale for r in rows],
                     p["left"], p["top"], pw, ph)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    nl = L["name_label"]
    vl = L["value_label"]
    for r, (x, y, w, h) in zip(rows, rects):
        hi = bool(r.get("highlight"))
        fill = resolve_role(pal, roles["cell_highlight" if hi else "cell"])
        parts.append(f'<rect x="{fmt(x + 1)}" y="{fmt(y + 1)}" width="{fmt(w - 2)}" '
                     f'height="{fmt(h - 2)}" fill="{fill}"/>')
        if w >= L["label_min_w"] and h >= L["label_min_h"]:
            parts.append(text(x + 10, y + 22, r["label"], nl["size"], body,
                              resolve_role(pal, roles["name"]),
                              weight=600 if hi else 400))
            lab = f'{r["value"]} {data["unit"]}' if r is rows[0] else str(r["value"])
            parts.append(text(x + 10, y + 40, lab, vl["size"], body,
                              resolve_role(pal, roles["value"])))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _line_frame(spec, tok, data, series, top, ymin, step):
    """Shared frame for line-family variants: gridlines, ticks, x labels,
    polylines (optionally stepped), end labels, annotation. Returns parts."""
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    xs = data["x"]
    n = len(xs)
    stepped = spec["scale"].get("step", False)

    def X(i):
        return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

    def Y(v):
        return p["bottom"] - (v - ymin) / (top - ymin) * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    base = spec["scale"].get("index_base")
    t = ymin
    while t <= top:
        y = Y(t)
        if base is not None and t == base:
            stroke = resolve_role(pal, roles["index_base_line"])
        elif t == ymin:
            stroke = resolve_role(pal, roles["zero_line"])
        else:
            stroke = resolve_role(pal, roles["gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        lab = f"{t}{data['unit']}" if t == top else str(t)
        parts.append(text(p["left"] - tl["offset"], y, lab, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += step

    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(X(i), p["bottom"] + xl["offset"], lab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))

    def pts_of(vals):
        pts = []
        prev_y = None
        for i, v in enumerate(vals):
            x, y = X(i), Y(v)
            if stepped and prev_y is not None:
                pts.append(f"{fmt(x)},{fmt(prev_y)}")
            pts.append(f"{fmt(x)},{fmt(y)}")
            prev_y = y
        return " ".join(pts)

    ordered = ([s for s in series if s["role"] == "context"]
               + [s for s in series if s["role"] == "key"])
    sl = L["series_label"]
    for s in ordered:
        key = s["role"] == "key"
        stroke = resolve_role(pal, roles["key"] if key else roles["context"])
        parts.append(f'<polyline points="{pts_of(s["values"])}" fill="none" '
                     f'stroke="{stroke}" '
                     f'stroke-width="{fmt(L["stroke"]["key" if key else "context"])}"/>')
        parts.append(text(p["right"] + sl["offset"], Y(s["values"][-1]), s["name"],
                          sl["size"], body,
                          resolve_role(pal, roles["key_label" if key else "context_label"]),
                          weight=600 if key else 400, baseline="middle"))

    ann = data.get("annotation")
    if ann:
        s = next(q for q in series if q["name"] == ann["series"])
        px, py = X(ann["index"]), Y(s["values"][ann["index"]])
        an = L["annotation"]
        anchor = ann.get("anchor", "start")
        lx = ann["tx"] + 4 if anchor == "end" else ann["tx"] - 4
        parts.append(line_el(px, py, lx, ann["ty"] - 5,
                             resolve_role(pal, roles["annotation"])))
        parts.append(text(ann["tx"], ann["ty"], ann["text"], an["size"], body,
                          resolve_role(pal, roles["annotation"]),
                          anchor=anchor, style=an["style"]))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_step(spec, tok, data):
    sc = spec["scale"]
    vmax = max(max(s["values"]) for s in data["series"])
    top, tick = nice_top(vmax, sc["target_ticks"], tuple(sc["nice_steps"]))
    return _line_frame(spec, tok, data, data["series"], top, 0, tick)


def render_indexed_line(spec, tok, data):
    sc = spec["scale"]
    base = sc["index_base"]
    series = [{**s, "values": [round(v / s["values"][0] * base, 1) for v in s["values"]]}
              for s in data["series"]]
    vmax = max(max(s["values"]) for s in series)
    vmin = min(min(s["values"]) for s in series)
    top, tick = nice_top(vmax, sc["target_ticks"], tuple(sc["nice_steps"]))
    ymin = math.floor(vmin / tick) * tick
    return _line_frame(spec, tok, data, series, top, ymin, tick)


def render_timeline(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    ay = L["axis_y"]

    def X(pos):
        return p["left"] + pos / 100 * (p["right"] - p["left"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    parts.append(line_el(p["left"], ay, p["right"], ay,
                         resolve_role(pal, roles["axis"]), 2))
    al = L["axis_label"]
    parts.append(text(p["left"], ay + al["offset"], data["axis"]["start_label"],
                      al["size"], body, resolve_role(pal, roles["axis_label"])))
    parts.append(text(p["right"], ay + al["offset"], data["axis"]["end_label"],
                      al["size"], body, resolve_role(pal, roles["axis_label"]),
                      anchor="end"))

    el_ = L["event_label"]
    for i, ev in enumerate(data["events"]):
        x = X(ev["pos"])
        role = roles[f'kind_{ev["kind"]}']
        color = resolve_role(pal, role)
        if ev["kind"] == "event":
            parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(ay)}" r="6" fill="{color}"/>')
        else:
            parts.append(f'<path d="M {fmt(x)},{fmt(ay - 8)} L {fmt(x + 8)},{fmt(ay)} '
                         f'L {fmt(x)},{fmt(ay + 8)} L {fmt(x - 8)},{fmt(ay)} Z" '
                         f'fill="{color}"/>')
        above = i % 2 == 0
        ly = ay - L["leader"] if above else ay + L["leader"]
        ty = ly - 18 if above else ly + 24
        sy = ty + 15 if above else ty + 15
        parts.append(line_el(x, ay - 10 if above else ay + 10, x, ly,
                             resolve_role(pal, roles["leader"])))
        anchor = "middle"
        if ev["pos"] >= 90:
            anchor = "end"
        elif ev["pos"] <= 10:
            anchor = "start"
        parts.append(text(x, ty, ev["label"], el_["size"], body,
                          resolve_role(pal, roles["label"]), weight=600, anchor=anchor))
        parts.append(text(x, sy, ev["sub"], el_["sub_size"], body,
                          resolve_role(pal, roles["sub"]), anchor=anchor))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_interval(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    bh, gap = L["row_height"], L["row_gap"]

    rows = data["categories"]
    vmax = max(r["high"] for r in rows)
    span = p["right"] - p["left"]

    def X(v):
        return p["left"] + v / vmax * span

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    cl = L["category_label"]
    vl = L["value_label"]
    for i, r in enumerate(rows):
        cy = p["top"] + i * (bh + gap) + bh / 2
        hi = bool(r.get("highlight"))
        iv = resolve_role(pal, roles["interval"])
        parts.append(line_el(X(r["low"]), cy, X(r["high"]), cy, iv, 2))
        parts.append(line_el(X(r["low"]), cy - 6, X(r["low"]), cy + 6, iv, 2))
        parts.append(line_el(X(r["high"]), cy - 6, X(r["high"]), cy + 6, iv, 2))
        dot = resolve_role(pal, roles["dot_highlight" if hi else "dot"])
        parts.append(f'<circle cx="{fmt(X(r["value"]))}" cy="{fmt(cy)}" r="7" '
                     f'fill="{dot}"/>')
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
        lab = f'{r["value"]} [{r["low"]}-{r["high"]}]'
        if i == 0:
            lab = f'{r["value"]} {data["unit"]} [{r["low"]}-{r["high"]}]'
        parts.append(text(X(r["high"]) + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600 if hi else 400, baseline="middle"))

    y_end = p["top"] + len(rows) * (bh + gap) - gap + 8
    parts.append(line_el(p["left"], p["top"] - 8, p["left"], y_end,
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_gantt(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    bh, gap = L["row_height"], L["row_gap"]

    labels = data["axis"]["labels"]
    n = len(labels)

    def X(u):
        return p["left"] + u / n * (p["right"] - p["left"])

    rows = data["tasks"]
    y_end = p["top"] + len(rows) * (bh + gap) - gap + 8

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    hl = L["header_label"]
    for i in range(n + 1):
        parts.append(line_el(X(i), p["top"] - 8, X(i), y_end,
                             resolve_role(pal, roles["grid"])))
    for i, lab in enumerate(labels):
        parts.append(text(X(i + 0.5), p["top"] - hl["offset"], lab, hl["size"], body,
                          resolve_role(pal, roles["header"]), anchor="middle"))

    cl = L["category_label"]
    for i, r in enumerate(rows):
        y = p["top"] + i * (bh + gap)
        cy = y + bh / 2
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
        if "start" in r:
            parts.append(f'<rect x="{fmt(X(r["start"]))}" y="{fmt(y)}" '
                         f'width="{fmt(X(r["end"]) - X(r["start"]))}" height="{fmt(bh)}" '
                         f'fill="{resolve_role(pal, roles["bar"])}"/>')
            if "done_to" in r:
                parts.append(f'<rect x="{fmt(X(r["start"]))}" y="{fmt(y)}" '
                             f'width="{fmt(X(r["done_to"]) - X(r["start"]))}" '
                             f'height="{fmt(bh)}" '
                             f'fill="{resolve_role(pal, roles["done"])}"/>')
        if "milestone_at" in r:
            mx = X(r["milestone_at"])
            parts.append(f'<path d="M {fmt(mx)},{fmt(cy - 9)} L {fmt(mx + 9)},{fmt(cy)} '
                         f'L {fmt(mx)},{fmt(cy + 9)} L {fmt(mx - 9)},{fmt(cy)} Z" '
                         f'fill="{resolve_role(pal, roles["milestone"])}"/>')

    tx = X(data["today"])
    parts.append(f'<line x1="{fmt(tx)}" y1="{fmt(p["top"] - 8)}" x2="{fmt(tx)}" '
                 f'y2="{fmt(y_end)}" stroke="{resolve_role(pal, roles["today"])}" '
                 f'stroke-width="1.5" stroke-dasharray="5 4"/>')
    parts.append(text(tx, y_end + 16, "today", L["today_label"]["size"], body,
                      resolve_role(pal, roles["today"]), anchor="middle"))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _hrow_frame(spec, tok, data, rows):
    """Shared opening for horizontal-row charts: canvas, chrome, row centers."""
    pal = tok["palette"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = spec["layout"]["plot"]
    bh, gap = spec["layout"]["row_height"], spec["layout"]["row_gap"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    centers = [p["top"] + i * (bh + gap) + bh / 2 for i in range(len(rows))]
    return parts, p, centers


def render_lollipop(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = sorted(data["categories"], key=lambda r: (-r["value"], r["label"]))
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    vmax = max(r["value"] for r in rows)

    def X(v):
        return p["left"] + v / vmax * (p["right"] - p["left"])

    cl, vl = L["category_label"], L["value_label"]
    for r, cy in zip(rows, centers):
        hi = bool(r.get("highlight"))
        parts.append(line_el(p["left"], cy, X(r["value"]), cy,
                             resolve_role(pal, roles["stick"]), 2))
        dot = resolve_role(pal, roles["dot_highlight" if hi else "dot"])
        parts.append(f'<circle cx="{fmt(X(r["value"]))}" cy="{fmt(cy)}" r="7" '
                     f'fill="{dot}"/>')
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
        lab = f'{r["value"]} {data["unit"]}' if r is rows[0] else str(r["value"])
        parts.append(text(X(r["value"]) + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600 if hi else 400, baseline="middle"))
    parts.append(line_el(p["left"], p["top"] - 8, p["left"], centers[-1] + 24,
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_dots_h(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    vmax = max(v for r in rows for v in r["values"])

    def X(v):
        return p["left"] + v / vmax * (p["right"] - p["left"])

    cl, vl = L["category_label"], L["value_label"]
    two = len(rows[0]["values"]) == 2
    if two and data.get("series_labels"):
        for j, name in enumerate(data["series_labels"]):
            parts.append(text(X(rows[0]["values"][j]), centers[0] - 16, name, 10,
                              body, resolve_role(pal, roles["dot_b" if j else "dot_a"]),
                              weight=600, anchor="middle"))
    for r, cy in zip(rows, centers):
        hi = bool(r.get("highlight"))
        vs = r["values"]
        if two:
            parts.append(line_el(X(vs[0]), cy, X(vs[1]), cy,
                                 resolve_role(pal, roles["connector"]), 2))
            parts.append(f'<circle cx="{fmt(X(vs[0]))}" cy="{fmt(cy)}" r="6" '
                         f'fill="{resolve_role(pal, roles["dot_a"])}"/>')
            parts.append(f'<circle cx="{fmt(X(vs[1]))}" cy="{fmt(cy)}" r="6" '
                         f'fill="{resolve_role(pal, roles["dot_b"])}"/>')
            lab = f'{vs[0]} > {vs[1]}'
        else:
            parts.append(f'<circle cx="{fmt(X(vs[0]))}" cy="{fmt(cy)}" r="6" '
                         f'fill="{resolve_role(pal, roles["dot_b" if hi else "dot_a"])}"/>')
            lab = str(vs[0])
        if r is rows[0]:
            lab = f'{lab} {data["unit"]}'
        parts.append(text(X(max(vs)) + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600 if hi else 400, baseline="middle"))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_bullet(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    vmax = max(max(r["bands"][-1], r["value"], r["target"]) for r in rows)
    ink = resolve_role(pal, roles["measure"])
    bg = pal["background"]

    def X(v):
        return p["left"] + v / vmax * (p["right"] - p["left"])

    cl, vl = L["category_label"], L["value_label"]
    for r, cy in zip(rows, centers):
        prev = 0
        for j, b in enumerate(r["bands"]):
            shade = mix_hex(bg, pal["ink"], 0.07 + 0.07 * j)
            parts.append(f'<rect x="{fmt(X(prev))}" y="{fmt(cy - 10)}" '
                         f'width="{fmt(X(b) - X(prev))}" height="20" fill="{shade}"/>')
            prev = b
        parts.append(f'<rect x="{fmt(p["left"])}" y="{fmt(cy - 4)}" '
                     f'width="{fmt(X(r["value"]) - p["left"])}" height="8" fill="{ink}"/>')
        parts.append(line_el(X(r["target"]), cy - 10, X(r["target"]), cy + 10,
                             resolve_role(pal, roles["target"]), 2.5))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
        lab = f'{r["value"]} {data["unit"]}' if r is rows[0] else str(r["value"])
        parts.append(text(X(r["bands"][-1]) + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_slope(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    rows = data["categories"]
    top, _ = nice_top(max(max(r["a"], r["b"]) for r in rows),
                      spec["scale"]["target_ticks"], tuple(spec["scale"]["nice_steps"]))

    def Y(v):
        return p["bottom"] - v / top * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    pl_ = L["period_label"]
    for x, lab, anchor in ((p["left"], data["periods"][0], "end"),
                           (p["right"], data["periods"][1], "start")):
        parts.append(line_el(x, p["top"] - 8, x, p["bottom"] + 8,
                             resolve_role(pal, roles["axis"])))
        parts.append(text(x, p["top"] - pl_["offset"], lab, pl_["size"], body,
                          resolve_role(pal, roles["period_label"]),
                          weight=600, anchor="middle", spacing=1))
    ll = L["line_label"]
    for r in rows:
        hi = bool(r.get("highlight"))
        stroke = resolve_role(pal, roles["slope_highlight" if hi else "slope"])
        parts.append(line_el(p["left"], Y(r["a"]), p["right"], Y(r["b"]), stroke,
                             2.5 if hi else 2))
        lfill = resolve_role(pal, roles["label_highlight" if hi else "label"])
        parts.append(text(p["left"] - ll["offset"], Y(r["a"]),
                          f'{r["label"]}  {r["a"]}', ll["size"], body, lfill,
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
        parts.append(text(p["right"] + ll["offset"], Y(r["b"]), str(r["b"]),
                          ll["size"], body, lfill,
                          weight=600 if hi else 400, baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_bar_paired(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    a, b = data["series"]
    vmax = max(max(a["values"]), max(b["values"]))
    n = len(data["x"])
    fa = resolve_role(pal, roles["series_a"])
    fb = resolve_role(pal, roles["series_b"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    bw = L["bar_width"]
    PH = p["bottom"] - p["top"]
    slot = (p["right"] - p["left"]) / n
    vl, xl = L["value_label"], L["x_label"]
    for i, xlab in enumerate(data["x"]):
        cx = p["left"] + (i + 0.5) * slot
        for j, (s, fill) in enumerate(((a, fa), (b, fb))):
            v = s["values"][i]
            h = v / vmax * PH
            x0 = cx - bw - 2 if j == 0 else cx + 2
            parts.append(f'<rect x="{fmt(x0)}" y="{fmt(p["bottom"] - h)}" '
                         f'width="{fmt(bw)}" height="{fmt(h)}" fill="{fill}"/>')
            lab = f'{v} {data["unit"]}' if i == 0 and j == 0 else str(v)
            parts.append(text(x0 + bw / 2, p["bottom"] - h - vl["offset"], lab,
                              vl["size"], body, resolve_role(pal, roles["value_label"]),
                              anchor="middle"))
            if i == 0:
                parts.append(text(x0 + bw / 2, p["top"] - 6, s["name"], 10, body,
                                  fill, weight=600, anchor="middle"))
        parts.append(text(cx, p["bottom"] + xl["offset"], xlab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))
    parts.append(line_el(p["left"], p["bottom"], p["right"], p["bottom"],
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_waffle(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    g = L["grid"]
    n = round(data["percent"])
    on = resolve_role(pal, roles["filled"])
    off = resolve_role(pal, roles["empty"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    for i in range(100):
        row = i // 10
        col = i % 10
        x = g["x"] + col * (g["cell"] + g["gap"])
        y = g["y"] + (9 - row) * (g["cell"] + g["gap"])
        parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(g["cell"])}" '
                     f'height="{fmt(g["cell"])}" fill="{on if i < n else off}"/>')
    bx = g["x"] + 10 * (g["cell"] + g["gap"]) + L["big"]["offset"]
    parts.append(text(bx, g["y"] + L["big"]["dy"], f'{data["percent"]}%',
                      L["big"]["size"], body, on, weight=600))
    parts.append(text(bx, g["y"] + L["big"]["dy"] + 30, data["label"], 14, body,
                      resolve_role(pal, roles["label"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_funnel(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    stages = data["stages"]
    vmax = stages[0]["value"]
    cx = (p["left"] + p["right"]) / 2
    maxw = p["right"] - p["left"]
    bh, gap = L["row_height"], L["row_gap"]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    vl = L["value_label"]
    for i, s in enumerate(stages):
        w = s["value"] / vmax * maxw
        y = p["top"] + i * (bh + gap)
        fill = resolve_role(pal, roles["stage_first" if i == 0 else "stage"])
        parts.append(f'<rect x="{fmt(cx - w / 2)}" y="{fmt(y)}" width="{fmt(w)}" '
                     f'height="{fmt(bh)}" fill="{fill}"/>')
        parts.append(text(cx - w / 2 - 12, y + bh / 2, s["label"], vl["size"], body,
                          resolve_role(pal, roles["stage_label"]),
                          anchor="end", baseline="middle"))
        lab = f'{s["value"]} {data["unit"]}' if i == 0 else str(s["value"])
        parts.append(text(cx + w / 2 + 12, y + bh / 2, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), baseline="middle"))
        if i > 0:
            pct = s["value"] / stages[i - 1]["value"] * 100
            parts.append(text(cx, y - gap / 2, f'{pct:.0f}%', 10, body,
                              resolve_role(pal, roles["conversion"]),
                              anchor="middle", baseline="middle", style="italic"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _value_axis(parts, spec, tok, y, top, step, unit):
    """Bottom value axis for row-distribution charts: baseline, ticks,
    unit on the top tick."""
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    p = L["plot"]
    base = resolve_role(pal, roles["baseline"])
    parts.append(line_el(p["left"], y, p["right"], y, base))
    tl = L["tick_label"]
    t = 0
    while t <= top:
        x = p["left"] + t / top * (p["right"] - p["left"])
        parts.append(line_el(x, y, x, y + 4, base))
        lab = f"{fmt(t)}{unit}" if t + step > top else fmt(t)
        parts.append(text(x, y + tl["offset"], lab, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]), anchor="middle"))
        t += step


def render_bump(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    xs = data["x"]
    series = data["series"]
    n, m = len(xs), len(series)

    def X(i):
        return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

    def Y(rank):
        return p["top"] + (rank - 1) * (p["bottom"] - p["top"]) / (m - 1)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(X(i), p["bottom"] + xl["offset"], lab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))

    ll = L["line_label"]
    ordered = ([s for s in series if not s.get("highlight")]
               + [s for s in series if s.get("highlight")])
    for s in ordered:
        hi = bool(s.get("highlight"))
        stroke = resolve_role(pal, roles["line_highlight" if hi else "line"])
        pts = " ".join(f"{fmt(X(i))},{fmt(Y(r))}" for i, r in enumerate(s["ranks"]))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" '
                     f'stroke-width="{fmt(L["stroke"]["highlight" if hi else "line"])}"/>')
        for i, r in enumerate(s["ranks"]):
            parts.append(f'<circle cx="{fmt(X(i))}" cy="{fmt(Y(r))}" '
                         f'r="{fmt(L["dot_r"])}" fill="{stroke}"/>')
        lfill = resolve_role(pal, roles["label_highlight" if hi else "label"])
        parts.append(text(p["left"] - ll["offset"], Y(s["ranks"][0]),
                          f'{s["ranks"][0]}. {s["name"]}', ll["size"], body, lfill,
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
        parts.append(text(p["right"] + ll["offset"], Y(s["ranks"][-1]),
                          f'{s["ranks"][-1]}. {s["name"]}', ll["size"], body, lfill,
                          weight=600 if hi else 400, baseline="middle"))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_table_bars(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    rh = L["row_height"]

    rows = sorted(data["categories"], key=lambda r: (-r["value"], r["label"]))
    vmax = max(r["value"] for r in rows)
    span = p["right"] - p["left"]
    gut = p["left"] - L["label_gutter"]
    dx = L["delta_x"]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    hl = L["header_label"]
    hfill = resolve_role(pal, roles["header"])
    parts.append(text(p["left"], p["top"] - hl["offset"], data["value_header"],
                      hl["size"], body, hfill, weight=600, spacing=1))
    parts.append(text(dx, p["top"] - hl["offset"], data["delta_header"],
                      hl["size"], body, hfill, weight=600, spacing=1, anchor="end"))

    hair = resolve_role(pal, roles["rule"])
    cl, vl = L["category_label"], L["value_label"]
    for i, r in enumerate(rows):
        y = p["top"] + i * rh
        cy = y + rh / 2
        hi = bool(r.get("highlight"))
        parts.append(line_el(gut, y, dx, y, hair))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
        w = r["value"] / vmax * span
        fill = resolve_role(pal, roles["bar_highlight" if hi else "bar"])
        parts.append(f'<rect x="{fmt(p["left"])}" y="{fmt(cy - 8)}" width="{fmt(w)}" '
                     f'height="16" fill="{fill}"/>')
        lab = f'{r["value"]} {data["unit"]}' if i == 0 else str(r["value"])
        parts.append(text(p["left"] + w + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600 if hi else 400, baseline="middle"))
        d = r["delta"]
        dfill = resolve_role(pal, roles["delta_pos" if d >= 0 else "delta_neg"])
        parts.append(text(dx, cy, f'+{d}' if d > 0 else str(d), vl["size"], body,
                          dfill, weight=600, anchor="end", baseline="middle"))
    parts.append(line_el(gut, p["top"] + len(rows) * rh, dx,
                         p["top"] + len(rows) * rh, hair))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_bar_paired_h(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]  # input order kept: magnitude, not ranking
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    vmax = max(v for r in rows for v in r["values"])
    bh = L["bar_height"]
    fills = [resolve_role(pal, roles["series_a"]), resolve_role(pal, roles["series_b"])]

    def X(v):
        return p["left"] + v / vmax * (p["right"] - p["left"])

    cl, vl = L["category_label"], L["value_label"]
    for r, cy in zip(rows, centers):
        for j, v in enumerate(r["values"]):
            y = cy - bh - 1 if j == 0 else cy + 1
            parts.append(f'<rect x="{fmt(p["left"])}" y="{fmt(y)}" '
                         f'width="{fmt(X(v) - p["left"])}" height="{fmt(bh)}" '
                         f'fill="{fills[j]}"/>')
            ly = y + bh / 2
            if r is rows[0]:
                lab = f'{v} {data["unit"]}  {data["series_labels"][j]}'
                parts.append(text(X(v) + vl["offset"], ly, lab, vl["size"], body,
                                  fills[j], weight=600, baseline="middle"))
            else:
                parts.append(text(X(v) + vl["offset"], ly, str(v), vl["size"], body,
                                  resolve_role(pal, roles["value_label"]),
                                  baseline="middle"))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
    parts.append(line_el(p["left"], p["top"] - 8, p["left"], centers[-1] + 24,
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_spine(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    half = (p["right"] - p["left"]) / 2
    cx = (p["left"] + p["right"]) / 2
    fa = resolve_role(pal, roles["side_a"])
    fb = resolve_role(pal, roles["side_b"])
    bh = L["bar_height"]

    sl = L["series_label"]
    parts.append(text(cx - sl["offset"], centers[0] - bh / 2 - sl["gap"],
                      data["series_labels"][0], sl["size"], body, fa,
                      weight=600, anchor="end"))
    parts.append(text(cx + sl["offset"], centers[0] - bh / 2 - sl["gap"],
                      data["series_labels"][1], sl["size"], body, fb, weight=600))

    cl, vl = L["category_label"], L["value_label"]
    for r, cy in zip(rows, centers):
        tot = r["a"] + r["b"]
        lw = r["a"] / tot * half
        rw = r["b"] / tot * half
        parts.append(f'<rect x="{fmt(cx - lw)}" y="{fmt(cy - bh / 2)}" '
                     f'width="{fmt(lw)}" height="{fmt(bh)}" fill="{fa}"/>')
        parts.append(f'<rect x="{fmt(cx)}" y="{fmt(cy - bh / 2)}" '
                     f'width="{fmt(rw)}" height="{fmt(bh)}" fill="{fb}"/>')
        la = f'{r["a"]}{data["unit"]}' if r is rows[0] else str(r["a"])
        lb = f'{r["b"]}{data["unit"]}' if r is rows[0] else str(r["b"])
        parts.append(text(cx - lw - vl["offset"], cy, la, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          anchor="end", baseline="middle"))
        parts.append(text(cx + rw + vl["offset"], cy, lb, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), baseline="middle"))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
    parts.append(line_el(cx, p["top"] - 8, cx, centers[-1] + bh / 2 + 8,
                         resolve_role(pal, roles["axis"]), 1.5))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_surplus_deficit(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]

    xs = data["x"]
    vals = data["values"]
    n = len(xs)
    amax = max(abs(v) for v in vals)
    top, step = nice_top(amax, sc["target_ticks"], tuple(sc["nice_steps"]))

    def X(i):
        return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

    def Y(v):
        return p["bottom"] - (v + top) / (2 * top) * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    t = -top
    while t <= top:
        y = Y(t)
        if t != 0:
            parts.append(line_el(p["left"], y, p["right"], y,
                                 resolve_role(pal, roles["gridline"])))
            lab = fmt(t) if t < 0 else f'+{fmt(t)}'
            if t + step > top:
                lab = f'{lab}{data["unit"]}'
            parts.append(text(p["left"] - tl["offset"], y, lab, tl["size"], body,
                              resolve_role(pal, roles["tick_label"]),
                              anchor="end", baseline="middle"))
        t += step

    # insert zero crossings so the fill splits exactly where the sign flips
    pts = []
    for i, v in enumerate(vals):
        if i and (vals[i - 1] < 0 < v or v < 0 < vals[i - 1]):
            xc = X(i - 1) + (X(i) - X(i - 1)) * (0 - vals[i - 1]) / (v - vals[i - 1])
            pts.append((xc, 0))
        pts.append((X(i), v))
    y0 = Y(0)
    for sign, role in ((1, "positive"), (-1, "negative")):
        poly = " ".join(f"{fmt(x)},{fmt(Y(max(v, 0) if sign > 0 else min(v, 0)))}"
                        for x, v in pts)
        parts.append(f'<polygon points="{fmt(pts[0][0])},{fmt(y0)} {poly} '
                     f'{fmt(pts[-1][0])},{fmt(y0)}" '
                     f'fill="{resolve_role(pal, roles[role])}" '
                     f'fill-opacity="{fmt(L["fill_opacity"])}"/>')
    line_pts = " ".join(f"{fmt(x)},{fmt(Y(v))}" for x, v in pts)
    parts.append(f'<polyline points="{line_pts}" fill="none" '
                 f'stroke="{resolve_role(pal, roles["line"])}" '
                 f'stroke-width="{fmt(L["stroke"])}"/>')
    parts.append(line_el(p["left"], y0, p["right"], y0,
                         resolve_role(pal, roles["zero_line"]), 1.5))

    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(X(i), p["bottom"] + xl["offset"], lab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_likert(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    neg = spec["scale"]["negative_levels"]
    cx = (p["left"] + p["right"]) / 2
    halfspan = (p["right"] - p["left"]) / 2
    bg = pal["background"]
    sn = resolve_role(pal, roles["strong_neg"])
    sp = resolve_role(pal, roles["strong_pos"])
    colors = [sn, mix_hex(bg, sn, 0.45), mix_hex(bg, sp, 0.45), sp]
    half = max(max(sum(r["values"][:neg]), sum(r["values"][neg:])) for r in rows)
    bh = L["bar_height"]

    lg = L["legend"]
    for k, name in enumerate(data["levels"]):
        sx = p["left"] + k * lg["slot"]
        parts.append(f'<rect x="{fmt(sx)}" y="{fmt(lg["y"] - 9)}" width="10" '
                     f'height="10" fill="{colors[k]}"/>')
        parts.append(text(sx + 16, lg["y"], name, lg["size"], body,
                          resolve_role(pal, roles["legend_label"])))

    cl, vl = L["category_label"], L["value_label"]
    for r, cy in zip(rows, centers):
        x = cx
        for j in range(neg - 1, -1, -1):
            w = r["values"][j] / half * halfspan
            x -= w
            parts.append(f'<rect x="{fmt(x)}" y="{fmt(cy - bh / 2)}" '
                         f'width="{fmt(w)}" height="{fmt(bh)}" fill="{colors[j]}"/>')
        xn = x
        x = cx
        for j in range(neg, len(colors)):
            w = r["values"][j] / half * halfspan
            parts.append(f'<rect x="{fmt(x)}" y="{fmt(cy - bh / 2)}" '
                         f'width="{fmt(w)}" height="{fmt(bh)}" fill="{colors[j]}"/>')
            x += w
        tn, tp = sum(r["values"][:neg]), sum(r["values"][neg:])
        ln = f'{tn}{data["unit"]}' if r is rows[0] else str(tn)
        lp = f'{tp}{data["unit"]}' if r is rows[0] else str(tp)
        parts.append(text(xn - vl["offset"], cy, ln, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          anchor="end", baseline="middle"))
        parts.append(text(x + vl["offset"], cy, lp, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), baseline="middle"))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
    parts.append(line_el(cx, centers[0] - bh / 2 - 8, cx,
                         centers[-1] + bh / 2 + 8,
                         resolve_role(pal, roles["axis"]), 1.5))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_histogram(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]

    counts = data["counts"]
    edges = data["edges"]
    n = len(counts)
    top, step = nice_top(max(counts), sc["target_ticks"], tuple(sc["nice_steps"]))
    slot = (p["right"] - p["left"]) / n
    PH = p["bottom"] - p["top"]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    t = 0
    while t <= top:
        y = p["bottom"] - t / top * PH
        stroke = resolve_role(pal, roles["zero_line" if t == 0 else "gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        lab = f'{fmt(t)} {data["unit"]}' if t + step > top else fmt(t)
        parts.append(text(p["left"] - tl["offset"], y, lab, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += step

    fill = resolve_role(pal, roles["bar"])
    for i, c in enumerate(counts):
        h = c / top * PH
        parts.append(f'<rect x="{fmt(p["left"] + i * slot + 0.5)}" '
                     f'y="{fmt(p["bottom"] - h)}" width="{fmt(slot - 1)}" '
                     f'height="{fmt(h)}" fill="{fill}"/>')

    xl = L["x_label"]
    for k, e in enumerate(edges):
        parts.append(text(p["left"] + k * slot, p["bottom"] + xl["offset"], str(e),
                          xl["size"], body, resolve_role(pal, roles["x_label"]),
                          anchor="middle"))

    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_strip(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    sc = spec["scale"]
    top, step = nice_top(max(v for r in rows for v in r["values"]),
                         sc["target_ticks"], tuple(sc["nice_steps"]))

    def X(v):
        return p["left"] + v / top * (p["right"] - p["left"])

    cl = L["category_label"]
    dot = resolve_role(pal, roles["dot"])
    for r, cy in zip(rows, centers):
        hi = bool(r.get("highlight"))
        for v in r["values"]:
            parts.append(f'<circle cx="{fmt(X(v))}" cy="{fmt(cy)}" '
                         f'r="{fmt(L["dot_r"])}" fill="{dot}"/>')
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="end", baseline="middle"))

    y_end = centers[-1] + L["row_height"] / 2 + 12
    _value_axis(parts, spec, tok, y_end, top, step, data["unit"])
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_boxplot(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    sc = spec["scale"]
    top, step = nice_top(max(r["max"] for r in rows),
                         sc["target_ticks"], tuple(sc["nice_steps"]))

    def X(v):
        return p["left"] + v / top * (p["right"] - p["left"])

    cl, vl = L["category_label"], L["value_label"]
    whisk = resolve_role(pal, roles["whisker"])
    box = resolve_role(pal, roles["box"])
    med = resolve_role(pal, roles["median"])
    for r, cy in zip(rows, centers):
        hi = bool(r.get("highlight"))
        parts.append(line_el(X(r["min"]), cy, X(r["q1"]), cy, whisk, 1.5))
        parts.append(line_el(X(r["q3"]), cy, X(r["max"]), cy, whisk, 1.5))
        for v in (r["min"], r["max"]):
            parts.append(line_el(X(v), cy - 6, X(v), cy + 6, whisk, 1.5))
        parts.append(f'<rect x="{fmt(X(r["q1"]))}" y="{fmt(cy - 9)}" '
                     f'width="{fmt(X(r["q3"]) - X(r["q1"]))}" height="18" '
                     f'fill="{box}"/>')
        parts.append(line_el(X(r["med"]), cy - 9, X(r["med"]), cy + 9, med, 2.5))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="end", baseline="middle"))
        lab = (f'median {r["med"]} {data["unit"]}' if r is rows[0]
               else str(r["med"]))
        parts.append(text(X(r["max"]) + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), baseline="middle"))

    y_end = centers[-1] + L["row_height"] / 2 + 12
    _value_axis(parts, spec, tok, y_end, top, step, data["unit"])
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_pyramid(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["bands"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    g = L["gutter"]
    cx = (p["left"] + p["right"]) / 2
    halfspan = (p["right"] - p["left"]) / 2 - g / 2
    vmax = max(max(r["a"], r["b"]) for r in rows)
    bh = L["row_height"]
    fa = resolve_role(pal, roles["side_a"])
    fb = resolve_role(pal, roles["side_b"])

    sl = L["series_label"]
    parts.append(text(cx - g / 2, centers[0] - bh / 2 - sl["gap"],
                      data["series_labels"][0], sl["size"], body, fa,
                      weight=600, anchor="end"))
    parts.append(text(cx + g / 2, centers[0] - bh / 2 - sl["gap"],
                      data["series_labels"][1], sl["size"], body, fb, weight=600))

    bl, vl = L["band_label"], L["value_label"]
    for r, cy in zip(rows, centers):
        lw = r["a"] / vmax * halfspan
        rw = r["b"] / vmax * halfspan
        parts.append(f'<rect x="{fmt(cx - g / 2 - lw)}" y="{fmt(cy - bh / 2)}" '
                     f'width="{fmt(lw)}" height="{fmt(bh)}" fill="{fa}"/>')
        parts.append(f'<rect x="{fmt(cx + g / 2)}" y="{fmt(cy - bh / 2)}" '
                     f'width="{fmt(rw)}" height="{fmt(bh)}" fill="{fb}"/>')
        parts.append(text(cx, cy, r["label"], bl["size"], body,
                          resolve_role(pal, roles["band_label"]),
                          anchor="middle", baseline="middle"))
        la = f'{r["a"]} {data["unit"]}' if r is rows[0] else str(r["a"])
        parts.append(text(cx - g / 2 - lw - vl["offset"], cy, la, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          anchor="end", baseline="middle"))
        parts.append(text(cx + g / 2 + rw + vl["offset"], cy, str(r["b"]),
                          vl["size"], body,
                          resolve_role(pal, roles["value_label"]), baseline="middle"))

    y_end = centers[-1] + bh / 2 + 8
    base = resolve_role(pal, roles["baseline"])
    parts.append(line_el(cx - g / 2, p["top"] - 8, cx - g / 2, y_end, base))
    parts.append(line_el(cx + g / 2, p["top"] - 8, cx + g / 2, y_end, base))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_beeswarm(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]
    r_dot = L["dot_r"]
    lane_h = 2 * r_dot + 1

    pts = sorted(data["points"], key=lambda q: (q["value"], q["label"]))
    top, step = nice_top(max(q["value"] for q in pts),
                         sc["target_ticks"], tuple(sc["nice_steps"]))

    def X(v):
        return p["left"] + v / top * (p["right"] - p["left"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    # deterministic swarm: sorted by value, first free lane out from center
    lanes = {}
    lb = L["point_label"]
    for q in pts:
        x = X(q["value"])
        k = 0
        i = 0
        while any(abs(x - x2) < lane_h for x2 in lanes.get(k, [])):
            i += 1
            k = (i + 1) // 2 * (1 if i % 2 else -1)
        lanes.setdefault(k, []).append(x)
        cy = L["center_y"] - k * lane_h
        hi = bool(q.get("highlight"))
        fill = resolve_role(pal, roles["dot_highlight" if hi else "dot"])
        parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(cy)}" r="{fmt(r_dot)}" '
                     f'fill="{fill}"/>')
        if hi:
            parts.append(text(x, cy - r_dot - lb["offset"],
                              f'{q["label"]}  {q["value"]} {data["unit"]}',
                              lb["size"], body, resolve_role(pal, roles["label"]),
                              weight=600, anchor="middle"))

    _value_axis(parts, spec, tok, L["axis_y"], top, step, data["unit"])
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_violin(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    sc = spec["scale"]
    top, step = nice_top(max(g for r in rows for g in r["grid"]),
                         sc["target_ticks"], tuple(sc["nice_steps"]))
    dmax = max(d for r in rows for d in r["density"])
    hmax = L["half_height"]

    def X(v):
        return p["left"] + v / top * (p["right"] - p["left"])

    cl, vl = L["category_label"], L["value_label"]
    vfill = resolve_role(pal, roles["violin"])
    med = resolve_role(pal, roles["median"])
    for r, cy in zip(rows, centers):
        halves = [d / dmax * hmax for d in r["density"]]
        upper = [f'{fmt(X(g))},{fmt(cy - h)}' for g, h in zip(r["grid"], halves)]
        lower = [f'{fmt(X(g))},{fmt(cy + h)}'
                 for g, h in zip(reversed(r["grid"]), reversed(halves))]
        parts.append(f'<polygon points="{" ".join(upper + lower)}" fill="{vfill}"/>')
        idx = min(range(len(r["grid"])),
                  key=lambda i: (abs(r["grid"][i] - r["median"]), i))
        hm = halves[idx]
        parts.append(line_el(X(r["median"]), cy - hm, X(r["median"]), cy + hm,
                             med, 2.5))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
        lab = (f'median {r["median"]} {data["unit"]}' if r is rows[0]
               else str(r["median"]))
        parts.append(text(X(r["grid"][-1]) + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]), baseline="middle"))

    y_end = centers[-1] + L["row_height"] / 2 + 12
    _value_axis(parts, spec, tok, y_end, top, step, data["unit"])
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _grid_frame(spec, tok, data, top, step, unit):
    """Standard opening for xy charts: canvas, chrome, horizontal grid,
    y ticks with unit on top, x labels. Returns (parts, X, Y, p)."""
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    xs = data["x"]
    n = len(xs)

    def X(i):
        return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

    def Y(v):
        return p["bottom"] - v / top * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    tl = L["tick_label"]
    t = 0
    while t <= top:
        y = Y(t)
        stroke = resolve_role(pal, roles["zero_line" if t == 0 else "gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        lab = f"{fmt(t)}{unit}" if t + step > top else fmt(t)
        parts.append(text(p["left"] - tl["offset"], y, lab, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += step
    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(X(i), p["bottom"] + xl["offset"], lab, xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))
    return parts, X, Y, p


def render_area_stacked(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    sc = spec["scale"]
    segs = data["series"]  # bottom-up
    n = len(data["x"])
    totals = [sum(s["values"][i] for s in segs) for i in range(n)]
    top, step = nice_top(max(totals), sc["target_ticks"], tuple(sc["nice_steps"]))
    parts, X, Y, p = _grid_frame(spec, tok, data, top, step, data["unit"])

    sl = L["segment_label"]
    prev = [0] * n
    for j, s in enumerate(segs):
        cur = [prev[i] + s["values"][i] for i in range(n)]
        fwd = " ".join(f"{fmt(X(i))},{fmt(Y(cur[i]))}" for i in range(n))
        back = " ".join(f"{fmt(X(i))},{fmt(Y(prev[i]))}"
                        for i in range(n - 1, -1, -1))
        fill = resolve_role(pal, roles["segments"][j])
        parts.append(f'<polygon points="{fwd} {back}" fill="{fill}" '
                     f'fill-opacity="{fmt(L["fill_opacity"])}"/>')
        parts.append(f'<polyline points="{fwd}" fill="none" stroke="{fill}" '
                     f'stroke-width="1.5"/>')
        parts.append(text(p["right"] + sl["offset"],
                          Y((cur[-1] + prev[-1]) / 2), s["name"], sl["size"],
                          body, fill, weight=600, baseline="middle"))
        prev = cur
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_sparkline_strip(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["rows"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    sx1, sx2 = L["spark_left"], L["spark_right"]
    hh = L["spark_half"]
    cl, vl = L["category_label"], L["value_label"]

    for r, cy in zip(rows, centers):
        vs = r["values"]
        lo, hi = min(vs), max(vs)
        span = hi - lo or 1

        def SX(i, m=len(vs) - 1):
            return sx1 + i * (sx2 - sx1) / m

        def SY(v, lo=lo, span=span):
            return cy + hh - (v - lo) / span * 2 * hh

        pts = " ".join(f"{fmt(SX(i))},{fmt(SY(v))}" for i, v in enumerate(vs))
        parts.append(f'<polyline points="{pts}" fill="none" '
                     f'stroke="{resolve_role(pal, roles["line"])}" '
                     f'stroke-width="1.5"/>')
        parts.append(f'<circle cx="{fmt(SX(len(vs) - 1))}" cy="{fmt(SY(vs[-1]))}" '
                     f'r="4" fill="{resolve_role(pal, roles["dot"])}"/>')
        lab = f'{vs[-1]}{data["unit"]}' if r is rows[0] else str(vs[-1])
        parts.append(text(sx2 + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600, baseline="middle"))
        d = vs[-1] - vs[0]
        tone = "delta_pos" if (d >= 0) == (r["good"] == "up") else "delta_neg"
        if d == 0:
            tone = "value_label"
        parts.append(text(L["delta_x"], cy, f'+{d}' if d > 0 else str(d),
                          vl["size"], body, resolve_role(pal, roles[tone]),
                          weight=600, anchor="end", baseline="middle"))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"],
                          body, resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_fan(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    sc = spec["scale"]
    k = data["split"]
    highs = [h for lo, h in data["band90"]] + data["actual"]
    top, step = nice_top(max(highs), sc["target_ticks"], tuple(sc["nice_steps"]))
    parts, X, Y, p = _grid_frame(spec, tok, data, top, step, data["unit"])

    anchor_x, anchor_v = X(k - 1), data["actual"][-1]
    for band, op in (("band90", L["fill_opacity"]["outer"]),
                     ("band50", L["fill_opacity"]["inner"])):
        fwd = " ".join(f"{fmt(X(k + i))},{fmt(Y(hi))}"
                       for i, (lo, hi) in enumerate(data[band]))
        back = " ".join(f"{fmt(X(k + i))},{fmt(Y(lo))}"
                        for i, (lo, hi) in reversed(list(enumerate(data[band]))))
        parts.append(f'<polygon points="{fmt(anchor_x)},{fmt(Y(anchor_v))} '
                     f'{fwd} {back}" '
                     f'fill="{resolve_role(pal, roles["band"])}" '
                     f'fill-opacity="{fmt(op)}"/>')
    act = " ".join(f"{fmt(X(i))},{fmt(Y(v))}" for i, v in enumerate(data["actual"]))
    parts.append(f'<polyline points="{act}" fill="none" '
                 f'stroke="{resolve_role(pal, roles["actual"])}" stroke-width="2.5"/>')
    med = (f"{fmt(anchor_x)},{fmt(Y(anchor_v))} "
           + " ".join(f"{fmt(X(k + i))},{fmt(Y(v))}"
                      for i, v in enumerate(data["median"])))
    parts.append(f'<polyline points="{med}" fill="none" '
                 f'stroke="{resolve_role(pal, roles["median"])}" '
                 f'stroke-width="2" stroke-dasharray="6 4"/>')
    parts.append(f'<line x1="{fmt(anchor_x)}" y1="{fmt(p["top"])}" '
                 f'x2="{fmt(anchor_x)}" y2="{fmt(p["bottom"])}" '
                 f'stroke="{resolve_role(pal, roles["divider"])}" '
                 f'stroke-width="1" stroke-dasharray="4 3"/>')
    parts.append(text(anchor_x + 8, p["top"] + 14, "FORECAST", 10, body,
                      resolve_role(pal, roles["label"]), weight=600, spacing=2))
    sl = L["series_label"]
    parts.append(text(p["right"] + sl["offset"], Y(data["median"][-1]),
                      f'{data["median"][-1]} median', sl["size"], body,
                      resolve_role(pal, roles["median"]),
                      weight=600, baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_marimekko(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    cols = data["columns"]
    total_all = sum(sum(c["segments"]) for c in cols)
    span, PH = p["right"] - p["left"], p["bottom"] - p["top"]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    xl, vl, sl = L["x_label"], L["value_label"], L["segment_label"]
    x = p["left"]
    for ci, c in enumerate(cols):
        ctot = sum(c["segments"])
        w = ctot / total_all * span
        y = p["bottom"]
        for j, v in enumerate(c["segments"]):
            h = v / ctot * PH
            y -= h
            fill = resolve_role(pal, roles["segments"][j])
            parts.append(f'<rect x="{fmt(x + 1)}" y="{fmt(y + 1)}" '
                         f'width="{fmt(w - 2)}" height="{fmt(h - 2)}" '
                         f'fill="{fill}"/>')
            if w >= 64 and h >= 22:
                share = v / ctot * 100
                parts.append(text(x + w / 2, y + h / 2, f'{share:.0f}%',
                                  vl["size"], body, pal["background"],
                                  weight=600, anchor="middle",
                                  baseline="middle"))
            if ci == 0:
                parts.append(text(p["left"] - sl["offset"], y + h / 2,
                                  data["segment_names"][j], sl["size"], body,
                                  fill, weight=600, anchor="end",
                                  baseline="middle"))
        parts.append(text(x + w / 2, p["bottom"] + xl["offset"], c["label"],
                          xl["size"], body,
                          resolve_role(pal, roles["x_label"]), anchor="middle"))
        lab = f'{ctot} {data["unit"]}' if ci == 0 else str(ctot)
        parts.append(text(x + w / 2, p["bottom"] + xl["offset"] + 16, lab, 10,
                          body, resolve_role(pal, roles["value_label"]),
                          anchor="middle"))
        x += w
    parts.append(line_el(p["left"], p["bottom"], p["right"], p["bottom"],
                         resolve_role(pal, roles["baseline"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_column_line(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]
    xs = data["x"]
    bars, line = data["bars"], data["line"]
    n = len(xs)
    topb, stepb = nice_top(max(bars["values"]), sc["target_ticks"],
                           tuple(sc["nice_steps"]))
    topl, stepl = nice_top(max(line["values"]), sc["target_ticks"],
                           tuple(sc["nice_steps"]))
    slot = (p["right"] - p["left"]) / n
    bw = L["bar_width"]
    PH = p["bottom"] - p["top"]

    def CX(i):
        return p["left"] + (i + 0.5) * slot

    def YB(v):
        return p["bottom"] - v / topb * PH

    def YL(v):
        return p["bottom"] - v / topl * PH

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    t = 0
    while t <= topb:
        y = YB(t)
        stroke = resolve_role(pal, roles["zero_line" if t == 0 else "gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        lab = f'{fmt(t)} {bars["unit"]}' if t + stepb > topb else fmt(t)
        parts.append(text(p["left"] - tl["offset"], y, lab, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += stepb
    t = 0
    while t <= topl:
        y = YL(t)
        lab = f'{fmt(t)}{line["unit"]}' if t + stepl > topl else fmt(t)
        parts.append(text(p["right"] + tl["offset"], y, lab, tl["size"], body,
                          resolve_role(pal, roles["line"]),
                          baseline="middle"))
        t += stepl

    bfill = resolve_role(pal, roles["bar"])
    for i, v in enumerate(bars["values"]):
        parts.append(f'<rect x="{fmt(CX(i) - bw / 2)}" y="{fmt(YB(v))}" '
                     f'width="{fmt(bw)}" height="{fmt(p["bottom"] - YB(v))}" '
                     f'fill="{bfill}"/>')
    parts.append(text(p["left"], p["top"] - 8,
                      f'{bars["name"]} (left scale)', 10, body, bfill,
                      weight=600))
    lfill = resolve_role(pal, roles["line"])
    pts = " ".join(f"{fmt(CX(i))},{fmt(YL(v))}"
                   for i, v in enumerate(line["values"]))
    parts.append(f'<polyline points="{pts}" fill="none" stroke="{lfill}" '
                 f'stroke-width="2.5"/>')
    parts.append(text(p["right"], p["top"] - 8,
                      f'{line["name"]} (right scale)', 10, body, lfill,
                      weight=600, anchor="end"))
    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(CX(i), p["bottom"] + xl["offset"], lab, xl["size"],
                          body, resolve_role(pal, roles["x_label"]),
                          anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_hexbin(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    sc = spec["scale"]
    R = L["hex_r"]
    pts = data["points"]
    topx, stepx = nice_top(max(q["x"] for q in pts), sc["target_ticks"],
                           tuple(sc["nice_steps"]))
    topy, stepy = nice_top(max(q["y"] for q in pts), sc["target_ticks"],
                           tuple(sc["nice_steps"]))

    def X(v):
        return p["left"] + v / topx * (p["right"] - p["left"])

    def Y(v):
        return p["bottom"] - v / topy * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    tl = L["tick_label"]
    t = 0
    while t <= topy:
        y = Y(t)
        stroke = resolve_role(pal, roles["zero_line" if t == 0 else "gridline"])
        parts.append(line_el(p["left"], y, p["right"], y, stroke))
        lab = f'{fmt(t)}{data["unit_y"]}' if t + stepy > topy else fmt(t)
        parts.append(text(p["left"] - tl["offset"], y, lab, tl["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="end", baseline="middle"))
        t += stepy
    t = 0
    while t <= topx:
        parts.append(text(X(t), p["bottom"] + L["x_label"]["offset"],
                          f'{fmt(t)}{data["unit_x"]}' if t + stepx > topx else fmt(t),
                          L["x_label"]["size"], body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="middle"))
        t += stepx

    s3 = math.sqrt(3)
    counts = {}
    for q in pts:
        px, py = X(q["x"]) - p["left"], Y(q["y"]) - p["top"]
        aq = (s3 / 3 * px - py / 3) / R
        ar = 2 / 3 * py / R
        cx_, cz = aq, ar
        cy_ = -cx_ - cz
        rx, ry, rz = round(cx_), round(cy_), round(cz)
        dx, dy, dz = abs(rx - cx_), abs(ry - cy_), abs(rz - cz)
        if dx > dy and dx > dz:
            rx = -ry - rz
        elif dy > dz:
            ry = -rx - rz
        else:
            rz = -rx - ry
        counts[(rx, rz)] = counts.get((rx, rz), 0) + 1
    cmax = max(counts.values())
    hi = resolve_role(pal, roles["cell_high"])

    def hexagon(cx0, cy0, r):
        return " ".join(f"{fmt(cx0 + r * math.cos(math.radians(60 * i - 30)))},"
                        f"{fmt(cy0 + r * math.sin(math.radians(60 * i - 30)))}"
                        for i in range(6))

    for (aq, ar), c in sorted(counts.items()):
        cx0 = p["left"] + R * s3 * (aq + ar / 2)
        cy0 = p["top"] + R * 1.5 * ar
        fill = mix_hex(pal["background"], hi, 0.25 + 0.75 * c / cmax)
        parts.append(f'<polygon points="{hexagon(cx0, cy0, R - 0.5)}" '
                     f'fill="{fill}"/>')

    kx = p["right"] - 150
    for i, c in enumerate((1, (cmax + 1) // 2, cmax)):
        fill = mix_hex(pal["background"], hi, 0.25 + 0.75 * c / cmax)
        parts.append(f'<polygon points="{hexagon(kx + i * 52, p["top"] - 14, 8)}" '
                     f'fill="{fill}"/>')
        parts.append(text(kx + i * 52 + 12, p["top"] - 10, str(c), 10, body,
                          resolve_role(pal, roles["tick_label"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_kpi_table(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    rh = L["row_height"]
    rows = data["rows"]
    gut = L["label_x"]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    hl = L["header_label"]
    hfill = resolve_role(pal, roles["header"])
    for xh, lab, anchor in ((L["value_x"], data["value_header"], "end"),
                            (L["delta_x"], data["delta_header"], "end"),
                            (L["spark_left"], data["trend_header"], "start")):
        parts.append(text(xh, p["top"] - hl["offset"], lab, hl["size"], body,
                          hfill, weight=600, spacing=1, anchor=anchor))
    hair = resolve_role(pal, roles["rule"])
    cl, vl = L["category_label"], L["value_label"]
    for i, r in enumerate(rows):
        y = p["top"] + i * rh
        cy = y + rh / 2
        parts.append(line_el(gut, y, L["spark_right"] + 20, y, hair))
        parts.append(text(gut, cy, r["label"], cl["size"], body,
                          resolve_role(pal, roles["category_label"]),
                          weight=600, baseline="middle"))
        parts.append(text(L["value_x"], cy, r["value"], vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600, anchor="end", baseline="middle"))
        d = r["delta"]
        tone = "delta_pos" if (d >= 0) == (r["good"] == "up") else "delta_neg"
        if d == 0:
            tone = "value_label"
        parts.append(text(L["delta_x"], cy, f'+{d}' if d > 0 else str(d),
                          cl["size"], body, resolve_role(pal, roles[tone]),
                          weight=600, anchor="end", baseline="middle"))
        vs = r["trend"]
        lo, hivals = min(vs), max(vs)
        span = hivals - lo or 1
        sx1, sx2 = L["spark_left"], L["spark_right"]
        spts = " ".join(
            f"{fmt(sx1 + k * (sx2 - sx1) / (len(vs) - 1))},"
            f"{fmt(cy + 11 - (v - lo) / span * 22)}"
            for k, v in enumerate(vs))
        parts.append(f'<polyline points="{spts}" fill="none" '
                     f'stroke="{resolve_role(pal, roles["trend"])}" '
                     f'stroke-width="1.5"/>')
        parts.append(f'<circle cx="{fmt(sx2)}" '
                     f'cy="{fmt(cy + 11 - (vs[-1] - lo) / span * 22)}" r="3.5" '
                     f'fill="{resolve_role(pal, roles["dot"])}"/>')
    y_end = p["top"] + len(rows) * rh
    parts.append(line_el(gut, y_end, L["spark_right"] + 20, y_end, hair))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _ramp(pal, k):
    """Deterministic monochrome category ramp: primary at full strength
    stepping toward the background. Honest for ordered categorical sets."""
    if k == 1:
        return [pal["primary"]]
    return [mix_hex(pal["background"], pal["primary"], 1 - i * 0.65 / (k - 1))
            for i in range(k)]


def render_prop_symbol(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    rows = data["categories"]
    vmax = max(r["value"] for r in rows)
    n = len(rows)
    cy = L["cy"]
    rmax = L["r_max"]

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    cl, vl = L["category_label"], L["value_label"]
    for i, r in enumerate(rows):
        cx = p["left"] + (i + 0.5) * (p["right"] - p["left"]) / n
        rr = math.sqrt(r["value"] / vmax) * rmax
        hi = bool(r.get("highlight"))
        fill = resolve_role(pal, roles["symbol_highlight" if hi else "symbol"])
        parts.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rr)}" '
                     f'fill="{fill}"/>')
        lab = f'{r["value"]} {data["unit"]}' if i == 0 else str(r["value"])
        parts.append(text(cx, cy - rr - vl["offset"], lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          weight=600 if hi else 400, anchor="middle"))
        parts.append(text(cx, cy + rmax + cl["offset"], r["label"], cl["size"],
                          body, resolve_role(pal, roles["category_label"]),
                          weight=600 if hi else 400, anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_pictogram(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["categories"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    u = data["unit_value"]
    cell, gap = L["cell"], L["cell_gap"]
    fill = resolve_role(pal, roles["unit"])
    cl, vl = L["category_label"], L["value_label"]

    for ri, (r, cy) in enumerate(zip(rows, centers)):
        full, part = divmod(r["value"], u)
        x = p["left"]
        for i in range(int(full)):
            parts.append(f'<rect x="{fmt(x)}" y="{fmt(cy - cell / 2)}" '
                         f'width="{fmt(cell)}" height="{fmt(cell)}" '
                         f'fill="{fill}"/>')
            x += cell + gap
        if part:
            parts.append(f'<rect x="{fmt(x)}" y="{fmt(cy - cell / 2)}" '
                         f'width="{fmt(cell * part / u)}" height="{fmt(cell)}" '
                         f'fill="{fill}"/>')
            x += cell + gap
        lab = f'{r["value"]} {data["unit"]}' if ri == 0 else str(r["value"])
        parts.append(text(x + vl["offset"], cy, lab, vl["size"], body,
                          resolve_role(pal, roles["value_label"]),
                          baseline="middle"))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"],
                          body, resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
    parts.append(text(p["left"], centers[-1] + L["row_height"] / 2 + 24,
                      f'one square = {u} {data["unit"]}', 11, body,
                      resolve_role(pal, roles["key"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_radar(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    cx, cy, rmax = L["cx"], L["cy"], L["r_max"]
    axes = data["axes"]
    k = len(axes)
    sc = spec["scale"]
    vmax = max(v for s in data["series"] for v in s["values"])
    top, step = nice_top(vmax, sc["target_ticks"], tuple(sc["nice_steps"]))

    def pt(ai, v):
        th = math.radians(-90 + ai * 360 / k)
        rr = v / top * rmax
        return cx + rr * math.cos(th), cy + rr * math.sin(th)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    grid = resolve_role(pal, roles["gridline"])
    t = step
    while t <= top:
        ring = " ".join(f"{fmt(x)},{fmt(y)}"
                        for x, y in (pt(i, t) for i in range(k)))
        parts.append(f'<polygon points="{ring}" fill="none" stroke="{grid}" '
                     f'stroke-width="1"/>')
        t += step
    al = L["axis_label"]
    for i, name in enumerate(axes):
        ex, ey = pt(i, top)
        parts.append(line_el(cx, cy, ex, ey, grid))
        lx, ly = pt(i, top * 1.12)
        anchor = "middle"
        if lx > cx + 4:
            anchor = "start"
        elif lx < cx - 4:
            anchor = "end"
        parts.append(text(lx, ly, name, al["size"], body,
                          resolve_role(pal, roles["axis_label"]),
                          anchor=anchor, baseline="middle"))
    parts.append(text(cx + 6, cy - top / top * rmax - 4, f'{fmt(top)}{data["unit"]}',
                      10, body, resolve_role(pal, roles["tick_label"])))

    sl = L["series_label"]
    for si, s in enumerate(data["series"]):
        key = si == 0
        stroke = resolve_role(pal, roles["series_a" if key else "series_b"])
        poly = " ".join(f"{fmt(x)},{fmt(y)}"
                        for x, y in (pt(i, v) for i, v in enumerate(s["values"])))
        parts.append(f'<polygon points="{poly}" fill="{stroke}" '
                     f'fill-opacity="0.12" stroke="{stroke}" stroke-width="2"/>')
        parts.append(text(L["legend_x"], L["legend_y"] + si * 20, s["name"],
                          sl["size"], body, stroke, weight=600))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_parliament(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    cx, cy = L["cx"], L["cy"]
    r_in, r_out = L["r_inner"], L["r_outer"]
    parties = data["parties"]
    total = sum(pp["seats"] for pp in parties)
    n_rows = max(3, math.ceil(total / 26))
    radii = [r_in + i * (r_out - r_in) / (n_rows - 1) for i in range(n_rows)]
    raw = [rr / sum(radii) * total for rr in radii]
    per_row = [round(x) for x in raw]
    per_row[-1] = total - sum(per_row[:-1])

    seats = []
    for ri, cnt in enumerate(per_row):
        if cnt <= 0:
            continue
        for j in range(cnt):
            ang = math.pi - (j * math.pi / (cnt - 1) if cnt > 1 else math.pi / 2)
            seats.append((ang, ri))
    seats.sort(key=lambda s: (-s[0], s[1]))

    colors = _ramp(pal, len(parties))
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    si = 0
    for pi, pp in enumerate(parties):
        for _ in range(pp["seats"]):
            ang, ri = seats[si]
            si += 1
            x = cx + radii[ri] * math.cos(ang)
            y = cy - radii[ri] * math.sin(ang)
            parts.append(f'<circle cx="{fmt(x)}" cy="{fmt(y)}" '
                         f'r="{fmt(L["seat_r"])}" fill="{colors[pi]}"/>')
    ll = L["legend_label"]
    lx = L["legend_x"]
    for pi, pp in enumerate(parties):
        parts.append(f'<rect x="{fmt(lx)}" y="{fmt(L["legend_y"] + pi * 22 - 8)}" '
                     f'width="10" height="10" fill="{colors[pi]}"/>')
        lab = f'{pp["name"]}  {pp["seats"]}'
        if pi == 0:
            lab = f'{pp["name"]}  {pp["seats"]} {data["unit"]}'
        parts.append(text(lx + 16, L["legend_y"] + pi * 22, lab, ll["size"],
                          body, resolve_role(pal, roles["legend"]),
                          baseline="middle"))
    parts.append(text(cx, cy - 10, str(total), L["total_size"], body,
                      resolve_role(pal, roles["total"]),
                      weight=600, anchor="middle"))
    parts.append(text(cx, cy + 10, f'total {data["unit"]}', 11, body,
                      resolve_role(pal, roles["legend"]), anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_gauge(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    cx, cy, rr = L["cx"], L["cy"], L["r"]
    thick = L["thickness"]
    lo, hi_v = data["min"], data["max"]

    def pt(v, rad):
        frac = (v - lo) / (hi_v - lo)
        th = math.pi - frac * math.pi
        return cx + rad * math.cos(th), cy - rad * math.sin(th)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    prev = lo
    for bi, b in enumerate(data["bands"]):
        shade = mix_hex(pal["background"], pal["ink"], 0.08 + 0.08 * bi)
        x1, y1 = pt(prev, rr)
        x2, y2 = pt(b, rr)
        xi2, yi2 = pt(b, rr - thick)
        xi1, yi1 = pt(prev, rr - thick)
        large = 1 if (b - prev) / (hi_v - lo) > 0.5 else 0
        parts.append(f'<path d="M {fmt(x1)},{fmt(y1)} '
                     f'A {fmt(rr)} {fmt(rr)} 0 {large} 1 {fmt(x2)},{fmt(y2)} '
                     f'L {fmt(xi2)},{fmt(yi2)} '
                     f'A {fmt(rr - thick)} {fmt(rr - thick)} 0 {large} 0 '
                     f'{fmt(xi1)},{fmt(yi1)} Z" fill="{shade}"/>')
        prev = b
    tx, ty = pt(data["target"], rr + 6)
    tx2, ty2 = pt(data["target"], rr - thick - 6)
    parts.append(line_el(tx, ty, tx2, ty2,
                         resolve_role(pal, roles["target"]), 2.5))
    nx, ny = pt(data["value"], rr - thick / 2)
    parts.append(line_el(cx, cy, nx, ny, resolve_role(pal, roles["needle"]), 3))
    parts.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="7" '
                 f'fill="{resolve_role(pal, roles["needle"])}"/>')
    for v, anchor in ((lo, "middle"), (hi_v, "middle")):
        lx, ly = pt(v, rr + 18)
        parts.append(text(lx, ly + 4, str(v), 11, body,
                          resolve_role(pal, roles["tick_label"]), anchor=anchor))
    parts.append(text(cx, cy + L["big"]["dy"], f'{data["value"]}{data["unit"]}',
                      L["big"]["size"], body, resolve_role(pal, roles["value"]),
                      weight=600, anchor="middle"))
    parts.append(text(cx, cy + L["big"]["dy"] + 24,
                      f'target {data["target"]}{data["unit"]}', 12, body,
                      resolve_role(pal, roles["tick_label"]), anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_streamgraph(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    segs = data["series"]
    xs = data["x"]
    n = len(xs)
    totals = [sum(s["values"][i] for s in segs) for i in range(n)]
    vmax = max(totals)
    mid = (p["top"] + p["bottom"]) / 2
    half = (p["bottom"] - p["top"]) / 2

    def X(i):
        return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

    def Y(v):  # v measured from the silhouette center; extremes = +-vmax/2
        return mid - v / vmax * 2 * half

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    xl = L["x_label"]
    for i, lab in enumerate(xs):
        parts.append(text(X(i), p["bottom"] + xl["offset"], lab, xl["size"],
                          body, resolve_role(pal, roles["x_label"]),
                          anchor="middle"))
    base = [-totals[i] / 2 for i in range(n)]
    sl = L["segment_label"]
    prev = base
    for j, s in enumerate(segs):
        cur = [prev[i] + s["values"][i] for i in range(n)]
        fwd = " ".join(f"{fmt(X(i))},{fmt(Y(cur[i]))}" for i in range(n))
        back = " ".join(f"{fmt(X(i))},{fmt(Y(prev[i]))}"
                        for i in range(n - 1, -1, -1))
        fill = resolve_role(pal, roles["segments"][j])
        parts.append(f'<polygon points="{fwd} {back}" fill="{fill}" '
                     f'fill-opacity="0.85"/>')
        parts.append(text(p["right"] + sl["offset"],
                          Y((cur[-1] + prev[-1]) / 2), s["name"], sl["size"],
                          body, fill, weight=600, baseline="middle"))
        prev = cur
    lab = f'{totals[-1]} {data["unit"]}'
    parts.append(text(p["right"] + sl["offset"], Y(base[-1]) + 16, f'total {lab}',
                      11, body, resolve_role(pal, roles["x_label"]),
                      baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_horizon(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    rows = data["rows"]
    parts, p, centers = _hrow_frame(spec, tok, data, rows)
    layers = L["layers"]
    bh = L["row_height"]
    vmax = max(v for r in rows for v in r["values"])
    step_v = vmax / layers
    hi = resolve_role(pal, roles["band"])
    cl = L["category_label"]

    for r, cy in zip(rows, centers):
        vs = r["values"]
        n = len(vs)
        y0 = cy + bh / 2

        def X(i, n=n):
            return p["left"] + i * (p["right"] - p["left"]) / (n - 1)

        for layer in range(layers):
            lo_t = layer * step_v
            seg = [min(max(v - lo_t, 0), step_v) / step_v * bh for v in vs]
            if not any(seg):
                continue
            fwd = " ".join(f"{fmt(X(i))},{fmt(y0 - h)}"
                           for i, h in enumerate(seg))
            back = f'{fmt(X(n - 1))},{fmt(y0)} {fmt(X(0))},{fmt(y0)}'
            parts.append(f'<polygon points="{fwd} {back}" fill="{hi}" '
                         f'fill-opacity="{fmt(0.28 + 0.24 * layer)}"/>')
        parts.append(line_el(p["left"], y0, p["right"], y0,
                             resolve_role(pal, roles["baseline"])))
        parts.append(text(p["left"] - cl["offset"], cy, r["label"], cl["size"],
                          body, resolve_role(pal, roles["category_label"]),
                          anchor="end", baseline="middle"))
    parts.append(text(p["left"], centers[-1] + bh / 2 + 24,
                      f'{layers} layers, each {fmt(vmax / layers)} '
                      f'{data["unit"]}; darker = higher', 11, body,
                      resolve_role(pal, roles["key"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_sunburst(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    cx, cy = L["cx"], L["cy"]
    r0, r1, r2 = L["r_hole"], L["r_inner"], L["r_outer"]
    groups = data["groups"]
    total = sum(sum(c["value"] for c in g["children"]) for g in groups)
    colors = _ramp(pal, len(groups))

    def pt(deg, rad):
        th = math.radians(deg)
        return cx + rad * math.cos(th), cy + rad * math.sin(th)

    def ring(a1, a2, ri, ro, fill):
        large = 1 if a2 - a1 > 180 else 0
        x1, y1 = pt(a1, ro)
        x2, y2 = pt(a2, ro)
        xi2, yi2 = pt(a2, ri)
        xi1, yi1 = pt(a1, ri)
        return (f'<path d="M {fmt(x1)},{fmt(y1)} '
                f'A {fmt(ro)} {fmt(ro)} 0 {large} 1 {fmt(x2)},{fmt(y2)} '
                f'L {fmt(xi2)},{fmt(yi2)} '
                f'A {fmt(ri)} {fmt(ri)} 0 {large} 0 {fmt(xi1)},{fmt(yi1)} Z" '
                f'fill="{fill}" stroke="{pal["background"]}" stroke-width="2"/>')

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    ll = L["label"]
    ang = -90.0
    for gi, g in enumerate(groups):
        gtot = sum(c["value"] for c in g["children"])
        ga2 = ang + gtot / total * 360
        parts.append(ring(ang, ga2, r0, r1, colors[gi]))
        mid = (ang + ga2) / 2
        if ga2 - ang >= 24:
            lx, ly = pt(mid, (r0 + r1) / 2)
            parts.append(text(lx, ly, g["name"], ll["size"], body,
                              pal["background"], weight=600,
                              anchor="middle", baseline="middle"))
        ca = ang
        for ci, c in enumerate(g["children"]):
            ca2 = ca + c["value"] / total * 360
            shade = mix_hex(pal["background"], colors[gi],
                            0.62 - 0.18 * (ci % 2))
            parts.append(ring(ca, ca2, r1, r2, shade))
            cmid = (ca + ca2) / 2
            if ca2 - ca >= 14:
                lx, ly = pt(cmid, r2 + ll["offset"])
                anchor = "start" if math.cos(math.radians(cmid)) >= 0 else "end"
                share = c["value"] / total * 100
                parts.append(text(lx, ly, f'{c["name"]}  {share:.0f}%',
                                  ll["size"], body,
                                  resolve_role(pal, roles["label"]),
                                  anchor=anchor, baseline="middle"))
            ca = ca2
        ang = ga2
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_circle_pack(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    rows = sorted(data["categories"], key=lambda r: (-r["value"], r["label"]))
    vmax = rows[0]["value"]
    base_r = L["r_max"]
    radii = [math.sqrt(r["value"] / vmax) * base_r for r in rows]

    # deterministic spiral packing: each circle walks an Archimedean
    # spiral from the origin until it collides with nothing placed
    placed = []  # (x, y, r)
    for rr in radii:
        if not placed:
            placed.append((0.0, 0.0, rr))
            continue
        t = 0.0
        while True:
            t += 0.02
            x = 2.2 * t * math.cos(t)
            y = 2.2 * t * math.sin(t)
            if all((x - qx) ** 2 + (y - qy) ** 2 >= (rr + qr + 1.5) ** 2
                   for qx, qy, qr in placed):
                placed.append((x, y, rr))
                break
    xs = [x - r for (x, y, r) in placed] + [x + r for (x, y, r) in placed]
    ys = [y - r for (x, y, r) in placed] + [y + r for (x, y, r) in placed]
    w0, h0 = max(xs) - min(xs), max(ys) - min(ys)
    scale = min((p["right"] - p["left"]) / w0, (p["bottom"] - p["top"]) / h0)
    ox = (p["left"] + p["right"]) / 2 - (max(xs) + min(xs)) / 2 * scale
    oy = (p["top"] + p["bottom"]) / 2 - (max(ys) + min(ys)) / 2 * scale

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    nl = L["name_label"]
    for row, (x, y, rr) in zip(rows, placed):
        X0, Y0, R0 = x * scale + ox, y * scale + oy, rr * scale
        hi = bool(row.get("highlight"))
        fill = resolve_role(pal, roles["cell_highlight" if hi else "cell"])
        parts.append(f'<circle cx="{fmt(X0)}" cy="{fmt(Y0)}" r="{fmt(R0)}" '
                     f'fill="{fill}" stroke="{pal["background"]}" '
                     f'stroke-width="2"/>')
        if R0 >= 34:
            parts.append(text(X0, Y0 - 4, row["label"], nl["size"], body,
                              pal["background"], weight=600, anchor="middle"))
            lab = (f'{row["value"]} {data["unit"]}' if row is rows[0]
                   else str(row["value"]))
            parts.append(text(X0, Y0 + 14, lab, nl["size"] - 1, body,
                              pal["background"], anchor="middle"))
        else:
            parts.append(text(X0, Y0 - R0 - 6, f'{row["label"]} {row["value"]}',
                              nl["size"] - 2, body,
                              resolve_role(pal, roles["label"]),
                              anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_parallel(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    axes = data["axes"]  # [{name, unit}]
    k = len(axes)
    items = data["items"]
    sc = spec["scale"]
    tops = []
    for ai in range(k):
        top, _ = nice_top(max(it["values"][ai] for it in items),
                          sc["target_ticks"], tuple(sc["nice_steps"]))
        tops.append(top)

    def AX(ai):
        return p["left"] + ai * (p["right"] - p["left"]) / (k - 1)

    def Y(ai, v):
        return p["bottom"] - v / tops[ai] * (p["bottom"] - p["top"])

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    al = L["axis_label"]
    axis = resolve_role(pal, roles["axis"])
    for ai, a in enumerate(axes):
        x = AX(ai)
        parts.append(line_el(x, p["top"], x, p["bottom"], axis))
        parts.append(text(x, p["top"] - al["offset"], a["name"], al["size"],
                          body, resolve_role(pal, roles["axis_label"]),
                          weight=600, anchor="middle"))
        parts.append(text(x, p["top"] - al["offset"] + 14,
                          f'0 to {fmt(tops[ai])}{a["unit"]}', 10, body,
                          resolve_role(pal, roles["tick_label"]),
                          anchor="middle"))
    ll = L["line_label"]
    ordered = ([it for it in items if not it.get("highlight")]
               + [it for it in items if it.get("highlight")])
    for it in ordered:
        hi = bool(it.get("highlight"))
        stroke = resolve_role(pal, roles["line_highlight" if hi else "line"])
        pts = " ".join(f"{fmt(AX(ai))},{fmt(Y(ai, v))}"
                       for ai, v in enumerate(it["values"]))
        parts.append(f'<polyline points="{pts}" fill="none" stroke="{stroke}" '
                     f'stroke-width="{2.5 if hi else 1.5}"'
                     f'{"" if hi else " stroke-opacity=\"0.55\""}/>')
        if hi:
            parts.append(text(p["right"] + ll["offset"],
                              Y(k - 1, it["values"][-1]), it["label"],
                              ll["size"], body, stroke,
                              weight=600, baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_splom(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    axes = data["axes"]
    k = len(axes)
    items = data["points"]
    sc = spec["scale"]
    tops = []
    for ai in range(k):
        top, _ = nice_top(max(it["values"][ai] for it in items),
                          sc["target_ticks"], tuple(sc["nice_steps"]))
        tops.append(top)
    gap = L["cell_gap"]
    cw = ((p["right"] - p["left"]) - (k - 1) * gap) / k
    chh = ((p["bottom"] - p["top"]) - (k - 1) * gap) / k

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    hair = resolve_role(pal, roles["frame"])
    dot = resolve_role(pal, roles["dot"])
    dhi = resolve_role(pal, roles["dot_highlight"])
    al = L["axis_label"]
    for r in range(k):
        for c in range(k):
            x0 = p["left"] + c * (cw + gap)
            y0 = p["top"] + r * (chh + gap)
            parts.append(f'<rect x="{fmt(x0)}" y="{fmt(y0)}" width="{fmt(cw)}" '
                         f'height="{fmt(chh)}" fill="none" stroke="{hair}"/>')
            if r == c:
                parts.append(text(x0 + cw / 2, y0 + chh / 2, axes[r]["name"],
                                  al["size"], body,
                                  resolve_role(pal, roles["axis_label"]),
                                  weight=600, anchor="middle",
                                  baseline="middle"))
                parts.append(text(x0 + cw / 2, y0 + chh / 2 + 16,
                                  f'0 to {fmt(tops[r])}{axes[r]["unit"]}', 9,
                                  body, resolve_role(pal, roles["tick_label"]),
                                  anchor="middle"))
                continue
            for it in items:
                px = x0 + it["values"][c] / tops[c] * cw
                py = y0 + chh - it["values"][r] / tops[r] * chh
                hi = bool(it.get("highlight"))
                parts.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" '
                             f'r="{3.5 if hi else 2.5}" '
                             f'fill="{dhi if hi else dot}"/>')
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_chord(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    cx, cy, rr = L["cx"], L["cy"], L["r"]
    nodes = data["nodes"]
    M = data["flows"]  # M[i][j] = flow i -> j
    k = len(nodes)
    totals = [sum(M[i]) + sum(M[j][i] for j in range(k)) for i in range(k)]
    grand = sum(totals)
    colors = _ramp(pal, k)
    gap_deg = 4

    spans = []
    ang = -90.0
    for i in range(k):
        sweep = totals[i] / grand * (360 - k * gap_deg)
        spans.append((ang, ang + sweep))
        ang += sweep + gap_deg

    def pt(deg, rad):
        th = math.radians(deg)
        return cx + rad * math.cos(th), cy + rad * math.sin(th)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    fmax = max(v for row in M for v in row) or 1
    for i in range(k):
        for j in range(k):
            v = M[i][j]
            if not v:
                continue
            a1 = (spans[i][0] + spans[i][1]) / 2
            a2 = (spans[j][0] + spans[j][1]) / 2
            x1, y1 = pt(a1, rr - 8)
            x2, y2 = pt(a2, rr - 8)
            wdt = 1.5 + v / fmax * L["ribbon_max"]
            parts.append(f'<path d="M {fmt(x1)},{fmt(y1)} '
                         f'Q {fmt(cx)},{fmt(cy)} {fmt(x2)},{fmt(y2)}" '
                         f'fill="none" stroke="{colors[i]}" '
                         f'stroke-width="{fmt(wdt)}" stroke-opacity="0.45"/>')
    ll = L["label"]
    for i, nd in enumerate(nodes):
        a1, a2 = spans[i]
        large = 1 if a2 - a1 > 180 else 0
        x1, y1 = pt(a1, rr)
        x2, y2 = pt(a2, rr)
        parts.append(f'<path d="M {fmt(x1)},{fmt(y1)} '
                     f'A {fmt(rr)} {fmt(rr)} 0 {large} 1 {fmt(x2)},{fmt(y2)}" '
                     f'fill="none" stroke="{colors[i]}" stroke-width="10"/>')
        mid = (a1 + a2) / 2
        lx, ly = pt(mid, rr + ll["offset"])
        anchor = "start" if math.cos(math.radians(mid)) >= 0 else "end"
        lab = f'{nd}  {totals[i]}'
        if i == 0:
            lab = f'{nd}  {totals[i]} {data["unit"]}'
        parts.append(text(lx, ly, lab, ll["size"], body,
                          resolve_role(pal, roles["label"]),
                          anchor=anchor, baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def _map_project(p):
    """Unit-square (0-100) map coordinates -> plot box. The author owns
    projection and aspect; the renderer only scales."""
    def M(x, y):
        return (p["left"] + x / 100 * (p["right"] - p["left"]),
                p["top"] + y / 100 * (p["bottom"] - p["top"]))
    return M


def _map_frame(spec, tok, data):
    pal = tok["palette"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)
    return parts, spec["layout"]["plot"]


def _basemap(parts, pal, M, regions, fill=None):
    for rg in regions:
        pts = " ".join(f"{fmt(px)},{fmt(py)}"
                       for px, py in (M(x, y) for x, y in rg["polygon"]))
        parts.append(f'<polygon points="{pts}" '
                     f'fill="{fill or mix_hex(pal["background"], pal["ink"], 0.06)}" '
                     f'stroke="{pal["background"]}" stroke-width="2"/>')


def render_choropleth(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    parts, p = _map_frame(spec, tok, data)
    M = _map_project(p)
    regions = data["regions"]
    vmax = max(r["value"] for r in regions)
    hi = resolve_role(pal, roles["fill_high"])
    ll = L["label"]
    for rg in regions:
        t = 0.15 + 0.85 * rg["value"] / vmax
        pts = " ".join(f"{fmt(px)},{fmt(py)}"
                       for px, py in (M(x, y) for x, y in rg["polygon"]))
        parts.append(f'<polygon points="{pts}" '
                     f'fill="{mix_hex(pal["background"], hi, t)}" '
                     f'stroke="{pal["background"]}" stroke-width="2"/>')
    for i, rg in enumerate(regions):
        lx, ly = M(*rg["label_at"])
        tfill = (pal["background"] if rg["value"] / vmax > 0.55
                 else resolve_role(pal, roles["label"]))
        parts.append(text(lx, ly, rg["name"], ll["size"], body, tfill,
                          weight=600, anchor="middle"))
        lab = f'{rg["value"]} {data["unit"]}' if i == 0 else str(rg["value"])
        parts.append(text(lx, ly + 15, lab, ll["size"] - 1, body, tfill,
                          anchor="middle"))
    kx, ky = L["key_x"], L["key_y"]
    for i, v in enumerate((0, vmax // 2, vmax)):
        t = 0.15 + 0.85 * (v / vmax if vmax else 0)
        parts.append(f'<rect x="{fmt(kx + i * 54)}" y="{fmt(ky - 10)}" '
                     f'width="14" height="14" '
                     f'fill="{mix_hex(pal["background"], hi, t)}" '
                     f'stroke="{pal["hairline"]}"/>')
        parts.append(text(kx + i * 54 + 20, ky + 1, str(v), 10, body,
                          resolve_role(pal, roles["label"]), baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_symbol_map(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    parts, p = _map_frame(spec, tok, data)
    M = _map_project(p)
    _basemap(parts, pal, M, data["regions"])
    places = data["places"]
    vmax = max(q["value"] for q in places)
    ll = L["label"]
    for i, q in enumerate(places):
        cx, cy = M(*q["at"])
        rr = math.sqrt(q["value"] / vmax) * L["r_max"]
        hi = bool(q.get("highlight"))
        fill = resolve_role(pal, roles["symbol_highlight" if hi else "symbol"])
        parts.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rr)}" '
                     f'fill="{fill}" fill-opacity="0.8" '
                     f'stroke="{fill}" stroke-width="1.5"/>')
        lab = f'{q["name"]}  {q["value"]}'
        if i == 0:
            lab = f'{q["name"]}  {q["value"]} {data["unit"]}'
        parts.append(text(cx, cy - rr - 6, lab, ll["size"], body,
                          resolve_role(pal, roles["label"]),
                          weight=600 if hi else 400, anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_route_progress(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    parts, p = _map_frame(spec, tok, data)
    M = _map_project(p)
    path = [M(x, y) for x, y in data["corridor"]]
    lens = [math.dist(path[i], path[i + 1]) for i in range(len(path) - 1)]
    total = sum(lens)

    def at_frac(f):
        target = f * total
        run = 0.0
        for i, seg in enumerate(lens):
            if run + seg >= target:
                t = (target - run) / seg if seg else 0
                return (path[i][0] + (path[i + 1][0] - path[i][0]) * t,
                        path[i][1] + (path[i + 1][1] - path[i][1]) * t)
            run += seg
        return path[-1]

    full = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in path)
    parts.append(f'<polyline points="{full}" fill="none" '
                 f'stroke="{resolve_role(pal, roles["pending"])}" '
                 f'stroke-width="5"/>')
    donef = data["done_to"]
    done_pts = []
    run = 0.0
    for i, seg in enumerate(lens):
        done_pts.append(path[i])
        if (run + seg) / total >= donef:
            done_pts.append(at_frac(donef))
            break
        run += seg
    else:
        done_pts.append(path[-1])
    dstr = " ".join(f"{fmt(x)},{fmt(y)}" for x, y in done_pts)
    parts.append(f'<polyline points="{dstr}" fill="none" '
                 f'stroke="{resolve_role(pal, roles["done"])}" '
                 f'stroke-width="5"/>')
    ll = L["label"]
    for i, st in enumerate(data["stations"]):
        sx, sy = at_frac(st["at"])
        fill = resolve_role(pal, roles[f'station_{st["kind"]}'])
        if st["kind"] == "current":
            parts.append(f'<path d="M {fmt(sx)},{fmt(sy - 9)} '
                         f'L {fmt(sx + 9)},{fmt(sy)} L {fmt(sx)},{fmt(sy + 9)} '
                         f'L {fmt(sx - 9)},{fmt(sy)} Z" fill="{fill}"/>')
        else:
            parts.append(f'<circle cx="{fmt(sx)}" cy="{fmt(sy)}" r="6" '
                         f'fill="{fill}"/>')
        above = i % 2 == 0
        ly = sy - 16 if above else sy + 22
        parts.append(text(sx, ly, st["name"], ll["size"], body,
                          resolve_role(pal, roles["label"]),
                          weight=600 if st["kind"] == "current" else 400,
                          anchor="middle"))
    dx, dy = at_frac(donef)
    parts.append(text(dx + 10, dy - 10,
                      f'{round(donef * 100)}{data["unit"]} complete', 12, body,
                      resolve_role(pal, roles["done"]), weight=600))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_dot_density(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    parts, p = _map_frame(spec, tok, data)
    M = _map_project(p)
    _basemap(parts, pal, M, data["regions"])
    dot = resolve_role(pal, roles["dot"])
    for x, y in data["dots"]:
        dx, dy = M(x, y)
        parts.append(f'<circle cx="{fmt(dx)}" cy="{fmt(dy)}" r="2.5" '
                     f'fill="{dot}"/>')
    ll = L["label"]
    for rg in data["regions"]:
        lx, ly = M(*rg["label_at"])
        parts.append(text(lx, ly, rg["name"], ll["size"], body,
                          resolve_role(pal, roles["label"]),
                          weight=600, anchor="middle"))
    parts.append(text(p["left"], p["bottom"] + 24,
                      f'one dot = {data["unit_value"]} {data["unit"]}', 11,
                      body, resolve_role(pal, roles["label"])))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_flow_map(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    parts, p = _map_frame(spec, tok, data)
    M = _map_project(p)
    _basemap(parts, pal, M, data["regions"])
    flows = data["flows"]
    fmax = max(f["value"] for f in flows)
    stroke = resolve_role(pal, roles["flow"])
    ll = L["label"]
    for i, f in enumerate(flows):
        x1, y1 = M(*f["from"])
        x2, y2 = M(*f["to"])
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = x2 - x1, y2 - y1
        norm = math.hypot(dx, dy) or 1
        cxx = mx - dy / norm * 0.18 * norm
        cyy = my + dx / norm * 0.18 * norm
        wdt = 1.5 + f["value"] / fmax * L["flow_max"]
        parts.append(f'<path d="M {fmt(x1)},{fmt(y1)} '
                     f'Q {fmt(cxx)},{fmt(cyy)} {fmt(x2)},{fmt(y2)}" '
                     f'fill="none" stroke="{stroke}" '
                     f'stroke-width="{fmt(wdt)}" stroke-opacity="0.65"/>')
        ux, uy = x2 - cxx, y2 - cyy
        un = math.hypot(ux, uy) or 1
        ux, uy = ux / un, uy / un
        px, py = -uy, ux
        ah = 6 + wdt
        parts.append(f'<polygon points="{fmt(x2)},{fmt(y2)} '
                     f'{fmt(x2 - ux * ah + px * ah * 0.5)},'
                     f'{fmt(y2 - uy * ah + py * ah * 0.5)} '
                     f'{fmt(x2 - ux * ah - px * ah * 0.5)},'
                     f'{fmt(y2 - uy * ah - py * ah * 0.5)}" fill="{stroke}"/>')
        if f["value"] == fmax:
            parts.append(text(cxx, cyy - 6,
                              f'{f["value"]} {data["unit"]}', ll["size"], body,
                              resolve_role(pal, roles["label"]),
                              weight=600, anchor="middle"))
    for pl in data["places"]:
        cx, cy = M(*pl["at"])
        parts.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="5" '
                     f'fill="{resolve_role(pal, roles["place"])}"/>')
        parts.append(text(cx, cy - 10, pl["name"], ll["size"], body,
                          resolve_role(pal, roles["label"]),
                          weight=600, anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_sankey(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    W, H = spec["canvas"]["width"], spec["canvas"]["height"]
    p = L["plot"]
    cols = data["columns"]
    k = len(cols)
    nw = L["node_width"]
    gap = L["node_gap"]
    PH = p["bottom"] - p["top"]
    grand = max(sum(nd["value"] for nd in c["nodes"]) for c in cols)
    scale = (PH - gap * (max(len(c["nodes"]) for c in cols) - 1)) / grand

    geo = {}
    for ci, c in enumerate(cols):
        x = p["left"] + ci * (p["right"] - p["left"] - nw) / (k - 1)
        tot_h = sum(nd["value"] for nd in c["nodes"]) * scale \
            + gap * (len(c["nodes"]) - 1)
        y = p["top"] + (PH - tot_h) / 2
        for nd in c["nodes"]:
            h = nd["value"] * scale
            geo[nd["name"]] = {"x": x, "y": y, "h": h, "col": ci,
                               "out_off": 0.0, "in_off": 0.0}
            y += h + gap

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{pal["background"]}"/>']
    chrome_and_title(parts, spec, tok, data)

    band = resolve_role(pal, roles["link"])
    for lk in data["links"]:
        a, b = geo[lk["from"]], geo[lk["to"]]
        h = lk["value"] * scale
        y1 = a["y"] + a["out_off"] + h / 2
        y2 = b["y"] + b["in_off"] + h / 2
        a["out_off"] += h
        b["in_off"] += h
        x1, x2 = a["x"] + nw, b["x"]
        cx1, cx2 = x1 + (x2 - x1) * 0.45, x2 - (x2 - x1) * 0.45
        parts.append(f'<path d="M {fmt(x1)},{fmt(y1)} '
                     f'C {fmt(cx1)},{fmt(y1)} {fmt(cx2)},{fmt(y2)} '
                     f'{fmt(x2)},{fmt(y2)}" fill="none" stroke="{band}" '
                     f'stroke-width="{fmt(h)}" stroke-opacity="0.35"/>')
    nfill = resolve_role(pal, roles["node"])
    ll = L["label"]
    first = True
    for c in cols:
        for nd in c["nodes"]:
            g = geo[nd["name"]]
            parts.append(f'<rect x="{fmt(g["x"])}" y="{fmt(g["y"])}" '
                         f'width="{fmt(nw)}" height="{fmt(g["h"])}" '
                         f'fill="{nfill}"/>')
            lab = f'{nd["name"]}  {nd["value"]}'
            if first:
                lab = f'{nd["name"]}  {nd["value"]} {data["unit"]}'
                first = False
            left_side = g["col"] == 0
            lx = g["x"] - 8 if left_side else g["x"] + nw + 8
            parts.append(text(lx, g["y"] + g["h"] / 2, lab, ll["size"], body,
                              resolve_role(pal, roles["label"]),
                              anchor="end" if left_side else "start",
                              baseline="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def render_network(spec, tok, data):
    pal, L = tok["palette"], spec["layout"]
    body = tok["fonts"]["body"]["family"]
    roles = spec["roles"]
    parts, p = _map_frame(spec, tok, data)
    M = _map_project(p)
    nodes = {nd["id"]: nd for nd in data["nodes"]}
    vmax = max(nd["value"] for nd in data["nodes"])
    wmax = max(e.get("weight", 1) for e in data["edges"])
    edge = resolve_role(pal, roles["edge"])
    for e in data["edges"]:
        x1, y1 = M(*nodes[e["a"]]["at"])
        x2, y2 = M(*nodes[e["b"]]["at"])
        w = 1 + e.get("weight", 1) / wmax * L["edge_max"]
        parts.append(f'<line x1="{fmt(x1)}" y1="{fmt(y1)}" x2="{fmt(x2)}" '
                     f'y2="{fmt(y2)}" stroke="{edge}" '
                     f'stroke-width="{fmt(w)}" stroke-opacity="0.6"/>')
    ll = L["label"]
    for i, nd in enumerate(data["nodes"]):
        cx, cy = M(*nd["at"])
        rr = math.sqrt(nd["value"] / vmax) * L["r_max"]
        hi = bool(nd.get("highlight"))
        fill = resolve_role(pal, roles["node_highlight" if hi else "node"])
        parts.append(f'<circle cx="{fmt(cx)}" cy="{fmt(cy)}" r="{fmt(rr)}" '
                     f'fill="{fill}" stroke="{pal["background"]}" '
                     f'stroke-width="2"/>')
        lab = f'{nd["id"]}  {nd["value"]}'
        if i == 0:
            lab = f'{nd["id"]}  {nd["value"]} {data["unit"]}'
        parts.append(text(cx, cy - rr - 7, lab, ll["size"], body,
                          resolve_role(pal, roles["label"]),
                          weight=600 if hi else 400, anchor="middle"))
    source_line(parts, spec, tok, data)
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


RENDERERS = {"bar_h": render_bar_h, "bar_v": render_bar_v,
             "bar_v_stacked": render_bar_v_stacked, "line": render_line,
             "area": render_area, "waterfall": render_waterfall,
             "bar_h_div": render_bar_h_div, "matrix": render_matrix,
             "pie": render_pie, "scatter": render_scatter,
             "heatmap": render_heatmap, "treemap": render_treemap,
             "step": render_step, "indexed_line": render_indexed_line,
             "timeline": render_timeline, "interval": render_interval,
             "gantt": render_gantt, "lollipop": render_lollipop,
             "dots_h": render_dots_h, "bullet": render_bullet,
             "slope": render_slope, "bar_paired": render_bar_paired,
             "waffle": render_waffle, "funnel": render_funnel,
             "bump": render_bump, "table_bars": render_table_bars,
             "bar_paired_h": render_bar_paired_h, "spine": render_spine,
             "surplus_deficit": render_surplus_deficit, "likert": render_likert,
             "histogram": render_histogram, "strip": render_strip,
             "boxplot": render_boxplot, "pyramid": render_pyramid,
             "beeswarm": render_beeswarm, "violin": render_violin,
             "area_stacked": render_area_stacked,
             "sparkline_strip": render_sparkline_strip, "fan": render_fan,
             "marimekko": render_marimekko, "column_line": render_column_line,
             "hexbin": render_hexbin, "kpi_table": render_kpi_table,
             "prop_symbol": render_prop_symbol, "pictogram": render_pictogram,
             "radar": render_radar, "parliament": render_parliament,
             "gauge": render_gauge, "streamgraph": render_streamgraph,
             "horizon": render_horizon, "sunburst": render_sunburst,
             "circle_pack": render_circle_pack, "parallel": render_parallel,
             "splom": render_splom, "chord": render_chord,
             "choropleth": render_choropleth, "symbol_map": render_symbol_map,
             "route_progress": render_route_progress,
             "dot_density": render_dot_density, "flow_map": render_flow_map,
             "sankey": render_sankey, "network": render_network}


def _strip_key(obj, key):
    if isinstance(obj, dict):
        obj.pop(key, None)
        for v in obj.values():
            _strip_key(v, key)
    elif isinstance(obj, list):
        for v in obj:
            _strip_key(v, key)


def _apply_constitution(spec, data, cons):
    """The behavioral layer: a language's constitution changes WHAT
    renders, deterministically (PROTOCOL 3.6). Three render-time hooks;
    charts_per_page is enforced on recipes by the validator."""
    delta = {"executive": 1, "scientific": -1}.get(cons.get("density"), 0)
    if delta:
        lay = json.loads(json.dumps(spec["layout"]))
        for k, v in lay.items():
            if isinstance(v, dict) and "size" in v and (
                    k.endswith("_label") or k == "label"):
                v["size"] = v["size"] + delta
        spec = {**spec, "layout": lay}
    if cons.get("highlight_policy") == "none":
        data = json.loads(json.dumps(data))
        _strip_key(data, "highlight")
    if cons.get("annotation_policy") == "none" and "annotation" in data:
        data = {k: v for k, v in data.items() if k != "annotation"}
    return spec, data


def render(spec, tok, data, bare=False):
    spec = merge(spec, spec.get("overrides", {}).get(tok["code"], {}))
    cons = tok.get("constitution", {})
    if cons:
        spec, data = _apply_constitution(spec, data, cons)
    if bare:
        spec = {**spec, "_bare": True}  # recipes draw their own title and source
    return RENDERERS[spec["chart_type"]](spec, tok, data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--tokens", required=True)
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    spec = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    tok = json.loads(Path(a.tokens).read_text(encoding="utf-8"))
    data = json.loads(Path(a.data).read_text(encoding="utf-8"))
    svg = render(spec, tok, data)
    Path(a.out).write_text(svg, encoding="utf-8", newline="\n")
    print(f"rendered {a.out} ({len(svg)} bytes)")


if __name__ == "__main__":
    sys.exit(main())
