"""Component drawers + standalone golden renderer for CP-xxx specs.

Drawers append SVG fragments at an origin; render_component wraps one
drawer call in the component's golden canvas using its embedded sample.

    python tools/render_cp.py --spec components/CP-KPI-01.json \
        --tokens tokens/DL-02.json --out golden/CP-KPI-01/CP-KPI-01_DL-02.svg
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from render import fmt, text, resolve_role  # noqa: E402


def draw_action_title(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    disp = tok["fonts"]["display"]
    if tok["chrome"]["eyebrow"] and data.get("eyebrow"):
        if tok["chrome"]["kicker"]:
            parts.append(f'<rect x="{fmt(x)}" y="{fmt(y + P["kicker_dy"])}" '
                         f'width="{fmt(P["kicker_w"])}" height="{fmt(P["kicker_h"])}" '
                         f'fill="{resolve_role(pal, R["kicker"])}"/>')
        parts.append(text(x, y + P["eyebrow_dy"], data["eyebrow"], P["eyebrow_size"],
                          tok["fonts"]["body"]["family"], resolve_role(pal, R["eyebrow"]),
                          weight=600, spacing=P["eyebrow_letter_spacing"]))
    parts.append(text(x, y, data["title"], P["title_size"], disp["family"],
                      resolve_role(pal, R["title"]), weight=disp["weight"]))


def draw_source(parts, tok, cp, x, y, data):
    parts.append(text(x, y, data["text"], cp["params"]["size"],
                      tok["fonts"]["body"]["family"],
                      resolve_role(tok["palette"], cp["roles"]["text"])))


def draw_kpi_card(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(P["w"])}" '
                 f'height="{fmt(P["h"])}" fill="{resolve_role(pal, R["card_bg"])}" '
                 f'stroke="{resolve_role(pal, R["border"])}" stroke-width="1"/>')
    parts.append(text(x + P["pad"], y + P["label_dy"], data["label"], P["label_size"],
                      body, resolve_role(pal, R["label"]), weight=600, spacing=1))
    parts.append(text(x + P["pad"], y + P["value_dy"], data["value"], P["value_size"],
                      body, resolve_role(pal, R["value"]), weight=600))
    parts.append(text(x + P["pad"], y + P["delta_dy"], data["delta"], P["delta_size"],
                      body, resolve_role(pal, R[f'delta_{data["tone"]}'])))


def draw_status_chip(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    scolor = resolve_role(pal, R[f'status_{data["status"]}'])
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(data["w"])}" '
                 f'height="{fmt(P["h"])}" rx="{fmt(P["radius"])}" fill="none" '
                 f'stroke="{scolor}" stroke-width="1.5"/>')
    cy = y + P["h"] / 2
    parts.append(f'<circle cx="{fmt(x + P["pad_x"])}" cy="{fmt(cy)}" '
                 f'r="{fmt(P["dot_r"])}" fill="{scolor}"/>')
    parts.append(text(x + P["pad_x"] + 10, cy, data["word"], P["text_size"],
                      tok["fonts"]["body"]["family"],
                      resolve_role(pal, R["text"]), weight=600,
                      baseline="middle", spacing=1))


def draw_callout(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(data["w"])}" '
                 f'height="{fmt(data["h"])}" fill="{resolve_role(pal, R["box_bg"])}" '
                 f'stroke="{resolve_role(pal, R["border"])}" stroke-width="1"/>')
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(P["bar_w"])}" '
                 f'height="{fmt(data["h"])}" fill="{resolve_role(pal, R["bar"])}"/>')
    tx = x + P["bar_w"] + P["pad"]
    for i, line in enumerate(data["lines"]):
        ty = y + P["pad"] + P["line_height"] * i + P["text_size"] * 0.75
        role = R["lead"] if i == 0 else R["text"]
        parts.append(text(tx, ty, line, P["text_size"], body,
                          resolve_role(pal, role), weight=600 if i == 0 else 400))


def draw_big_number(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    disp = tok["fonts"]["display"]
    parts.append(text(x, y + P["label_dy"], data["label"], P["label_size"],
                      body, resolve_role(pal, R["label"]),
                      weight=600, spacing=2))
    parts.append(text(x, y + P["value_dy"], data["value"], P["value_size"],
                      disp["family"], resolve_role(pal, R["value"]),
                      weight=disp["weight"]))
    parts.append(text(x, y + P["context_dy"], data["context"],
                      P["context_size"], body,
                      resolve_role(pal, R["context"])))


def draw_stamp(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    color = resolve_role(pal, R[f'stamp_{data["tone"]}'])
    w, h = data["w"], P["h"]
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" '
                 f'height="{fmt(h)}" fill="none" stroke="{color}" '
                 f'stroke-width="2"/>')
    parts.append(f'<rect x="{fmt(x + 4)}" y="{fmt(y + 4)}" '
                 f'width="{fmt(w - 8)}" height="{fmt(h - 8)}" fill="none" '
                 f'stroke="{color}" stroke-width="1"/>')
    parts.append(text(x + w / 2, y + h / 2, data["word"], P["text_size"],
                      body, color, weight=600, anchor="middle",
                      baseline="middle", spacing=3))


def draw_header_band(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    disp = tok["fonts"]["display"]
    w, h = data["w"], P["h"]
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" '
                 f'height="{fmt(h)}" fill="{resolve_role(pal, R["band_bg"])}"/>')
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y + h - P["rule_h"])}" '
                 f'width="{fmt(w)}" height="{fmt(P["rule_h"])}" '
                 f'fill="{resolve_role(pal, R["rule"])}"/>')
    parts.append(text(x + P["pad"], y + P["title_dy"], data["title"],
                      P["title_size"], disp["family"],
                      resolve_role(pal, R["title"]), weight=disp["weight"]))
    parts.append(text(x + w - P["pad"], y + P["title_dy"], data["meta"],
                      P["meta_size"], body, resolve_role(pal, R["meta"]),
                      weight=600, anchor="end", spacing=1))


def draw_title_block(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    w = data["w"]
    rows = data["rows"]
    rh = P["row_height"]
    h = rh * len(rows)
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" '
                 f'height="{fmt(h)}" fill="{resolve_role(pal, R["block_bg"])}" '
                 f'stroke="{resolve_role(pal, R["frame"])}" stroke-width="1.5"/>')
    for i, (lab, val) in enumerate(rows):
        ry = y + i * rh
        if i:
            parts.append(f'<line x1="{fmt(x)}" y1="{fmt(ry)}" '
                         f'x2="{fmt(x + w)}" y2="{fmt(ry)}" '
                         f'stroke="{resolve_role(pal, R["rule"])}" '
                         f'stroke-width="1"/>')
        parts.append(text(x + P["pad"], ry + P["label_dy"], lab,
                          P["label_size"], body,
                          resolve_role(pal, R["label"]),
                          weight=600, spacing=1))
        parts.append(text(x + P["pad"], ry + P["value_dy"], val,
                          P["value_size"], body,
                          resolve_role(pal, R["value"])))


def draw_leader(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    px, py = data["px"], data["py"]
    parts.append(f'<circle cx="{fmt(px)}" cy="{fmt(py)}" r="{fmt(P["dot_r"])}" '
                 f'fill="{resolve_role(pal, R["dot"])}"/>')
    anchor = data.get("anchor", "start")
    lx = x + 4 if anchor == "end" else x - 4
    parts.append(f'<line x1="{fmt(px)}" y1="{fmt(py)}" x2="{fmt(lx)}" '
                 f'y2="{fmt(y - 5)}" '
                 f'stroke="{resolve_role(pal, R["leader"])}" stroke-width="1"/>')
    parts.append(text(x, y, data["text"], P["text_size"], body,
                      resolve_role(pal, R["text"]), anchor=anchor,
                      style=P["style"]))


def draw_exception_row(parts, tok, cp, x, y, data):
    pal, P, R = tok["palette"], cp["params"], cp["roles"]
    body = tok["fonts"]["body"]["family"]
    w, h = data["w"], P["h"]
    scolor = resolve_role(pal, R[f'status_{data["status"]}'])
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(w)}" '
                 f'height="{fmt(h)}" fill="{resolve_role(pal, R["row_bg"])}" '
                 f'stroke="{resolve_role(pal, R["rule"])}" stroke-width="1"/>')
    parts.append(f'<rect x="{fmt(x)}" y="{fmt(y)}" width="{fmt(P["bar_w"])}" '
                 f'height="{fmt(h)}" fill="{scolor}"/>')
    cy = y + h / 2
    parts.append(f'<circle cx="{fmt(x + P["pad"])}" cy="{fmt(cy)}" r="4" '
                 f'fill="{scolor}"/>')
    parts.append(text(x + P["pad"] + 14, cy, data["claim"], P["claim_size"],
                      body, resolve_role(pal, R["claim"]),
                      weight=600, baseline="middle"))
    parts.append(text(x + w - P["pad"], cy,
                      f'{data["owner"]} . {data["due"]}', P["meta_size"],
                      body, resolve_role(pal, R["meta"]),
                      weight=600, anchor="end", baseline="middle", spacing=1))


DRAW = {"CP-TXT-01": draw_action_title, "CP-TXT-02": draw_source,
        "CP-KPI-01": draw_kpi_card, "CP-STA-01": draw_status_chip,
        "CP-CAL-01": draw_callout, "CP-KPI-02": draw_big_number,
        "CP-STA-02": draw_stamp, "CP-STR-01": draw_header_band,
        "CP-STR-02": draw_title_block, "CP-LAB-01": draw_leader,
        "CP-CAL-02": draw_exception_row}


def render_component(cp, tok):
    W, H = cp["golden_canvas"]["w"], cp["golden_canvas"]["h"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{tok["palette"]["background"]}"/>']
    DRAW[cp["code"]](parts, tok, cp, cp["golden_origin"]["x"],
                     cp["golden_origin"]["y"], cp["sample"])
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", required=True)
    ap.add_argument("--tokens", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    cp = json.loads(Path(a.spec).read_text(encoding="utf-8"))
    tok = json.loads(Path(a.tokens).read_text(encoding="utf-8"))
    svg = render_component(cp, tok)
    Path(a.out).write_text(svg, encoding="utf-8", newline="\n")
    print(f"rendered {a.out}")


if __name__ == "__main__":
    main()
