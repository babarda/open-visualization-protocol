"""Recipe compositor: a recipe spec + its DL + component and chart specs
-> one fully determined 1280x720 page, byte-stable.

    python tools/render_rc.py --recipe recipes/RC-001.json --out golden/RC-001/RC-001.svg
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import render as CH  # noqa: E402
import render_cp as CP  # noqa: E402


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def render_recipe(rc, root=ROOT):
    tok = load(root / "tokens" / f'{rc["dl"]}.json')
    comps = {p.stem: load(p) for p in sorted((root / "components").glob("CP-*.json"))}
    W, H = rc["canvas"]["width"], rc["canvas"]["height"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
             f'viewBox="0 0 {W} {H}">',
             f'<rect width="{W}" height="{H}" fill="{tok["palette"]["background"]}"/>']

    for el in rc["elements"]:
        t = el["type"]
        if t == "title":
            CP.draw_action_title(parts, tok, comps["CP-TXT-01"], el["x"], el["y"], el["data"])
        elif t == "kpi_strip":
            cp = comps["CP-KPI-01"]
            step = cp["params"]["w"] + el["gap"]
            for i, card in enumerate(el["cards"]):
                CP.draw_kpi_card(parts, tok, cp, el["x"] + i * step, el["y"], card)
        elif t == "chip":
            CP.draw_status_chip(parts, tok, comps["CP-STA-01"], el["x"], el["y"], el["data"])
        elif t == "callout":
            CP.draw_callout(parts, tok, comps["CP-CAL-01"], el["x"], el["y"], el["data"])
        elif t == "source":
            CP.draw_source(parts, tok, comps["CP-TXT-02"], el["x"], el["y"],
                           {"text": el["text"]})
        elif t == "big_number":
            CP.draw_big_number(parts, tok, comps["CP-KPI-02"], el["x"],
                               el["y"], el["data"])
        elif t == "header_band":
            CP.draw_header_band(parts, tok, comps["CP-STR-01"], el["x"],
                                el["y"], el["data"])
        elif t == "exception_row":
            CP.draw_exception_row(parts, tok, comps["CP-CAL-02"], el["x"],
                                  el["y"], el["data"])
        elif t == "stamp":
            CP.draw_stamp(parts, tok, comps["CP-STA-02"], el["x"], el["y"],
                          el["data"])
        elif t == "chart":
            spec = load(root / "specs" / f'{el["ref"]}.json')
            data = load(root / el["data_ref"])
            inner = CH.render(spec, tok, data, bare=True)
            body = inner.split("\n", 1)[1].rsplit("</svg>", 1)[0]
            cx, cy, cw, chh = el["crop"]
            parts.append(f'<svg x="{fmt_n(el["x"])}" y="{fmt_n(el["y"])}" '
                         f'width="{fmt_n(el["w"])}" height="{fmt_n(el["h"])}" '
                         f'viewBox="{cx} {cy} {cw} {chh}">')
            parts.append(body.rstrip("\n"))
            parts.append("</svg>")
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def fmt_n(v):
    return CH.fmt(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--recipe", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rc = load(a.recipe)
    svg = render_recipe(rc)
    Path(a.out).write_text(svg, encoding="utf-8", newline="\n")
    print(f"rendered {a.out}")


if __name__ == "__main__":
    main()
