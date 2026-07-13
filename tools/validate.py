"""QA gate for the VizCatalogue repo. Exit 2 blocks shipping.

Checks:
 1. Every tokens/DL-*.json and specs/CH-*.json parses and passes its schema
    (jsonschema library if installed, built-in structural checks otherwise).
 2. Hex discipline: every palette value is #RRGGBB uppercase.
 3. WCAG AA: ink and body text contrast >= 4.5:1 on background.
 4. Golden data sanity (bar: one highlight max, values >= 0;
    line: series lengths match x, exactly one key series).
 5. Determinism: every golden SVG re-renders byte-identical from
    spec + tokens + data.
 6. blocks/ (the copy-paste product) rebuilds byte-identical: generated
    blocks may never drift from specs and tokens.
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import render as R  # noqa: E402
import render_cp as C  # noqa: E402
import render_rc as RR  # noqa: E402
import build_blocks as B  # noqa: E402

HEX = re.compile(r"^#[0-9A-F]{6}$")
FAILS = []


def report(ok, msg):
    print(f"{'PASS' if ok else 'FAIL'}  {msg}")
    if not ok:
        FAILS.append(msg)


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def schema_check(doc, schema, label):
    try:
        import jsonschema
        jsonschema.validate(doc, schema)
        report(True, f"{label}: schema (jsonschema)")
    except ImportError:
        missing = [k for k in schema.get("required", []) if k not in doc]
        report(not missing, f"{label}: required keys{' missing ' + str(missing) if missing else ''} (builtin)")
    except Exception as e:
        report(False, f"{label}: schema: {str(e).splitlines()[0]}")


def _lin(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def contrast(h1, h2):
    def lum(h):
        r, g, b = int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)
        return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)
    l1, l2 = lum(h1), lum(h2)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def main():
    dl_schema = load(ROOT / "schema" / "dl.schema.json")
    ch_schema = load(ROOT / "schema" / "ch.schema.json")

    tokens = {}
    for p in sorted((ROOT / "tokens").glob("DL-*.json")):
        tok = load(p)
        tokens[tok["code"]] = tok
        schema_check(tok, dl_schema, p.name)
        bad = [k for k, v in tok["palette"].items()
               if not (isinstance(v, str) and HEX.match(v))]
        report(not bad, f"{p.name}: palette all #RRGGBB uppercase"
               + (f" (bad: {bad})" if bad else ""))
        bg = tok["palette"]["background"]
        for role in ("ink", "body"):
            c = contrast(tok["palette"][role], bg)
            report(c >= 4.5, f"{p.name}: {role} on background {c:.2f}:1 (AA >= 4.5)")

    engine = load(ROOT / "decision" / "engine.json")
    intents = set(engine["vocabulary"]["intent"])
    for code, tok in tokens.items():
        c = tok.get("constitution", {})
        bad = [k for k, v in c.items() if k != "charts_per_page"
               and (k not in engine["vocabulary"]
                    or v not in engine["vocabulary"][k])]
        ok = not bad and isinstance(c.get("charts_per_page"), int) \
            and 1 <= c["charts_per_page"] <= 6
        report(ok, f"{code}: constitution in controlled vocabulary"
               + (f" (bad: {bad})" if bad else ""))
    for r in engine["rules"]:
        report(all(k in engine["vocabulary"] and v in engine["vocabulary"][k]
                   for k, v in r["if"].items()) if r["if"] else False,
               f"engine rule -> {r['then']}: conditions use the vocabulary")

    specs = {}
    for p in sorted((ROOT / "specs").glob("CH-*.json")):
        spec = load(p)
        specs[spec["code"]] = spec
        schema_check(spec, ch_schema, p.name)
        bad = [i for i in spec["meta"]["intent"] if i not in intents]
        report(not bad, f"{p.name}: meta.intent in controlled vocabulary"
               + (f" (bad: {bad})" if bad else ""))

    pat_codes = set()
    for p in sorted((ROOT / "patterns").glob("PT-*.json")):
        pat = load(p)
        pat_codes.add(pat["code"])
        missing = [k for k in ("code", "name", "recognition", "meaning",
                               "business_reading", "show_with", "avoid")
                   if k not in pat]
        report(not missing, f"{p.name}: pattern fields complete"
               + (f" (missing {missing})" if missing else ""))
        unknown = [c for c in pat["show_with"] if c not in specs]
        report(not unknown, f"{p.name}: show_with charts exist"
               + (f" (unknown {unknown})" if unknown else ""))

    nr_schema = load(ROOT / "schema" / "nr.schema.json")
    bq_schema = load(ROOT / "schema" / "bq.schema.json")
    nr_codes = set()
    for p in sorted((ROOT / "narratives").glob("NR-*.json")):
        nr = load(p)
        nr_codes.add(nr["code"])
        schema_check(nr, nr_schema, p.name)
    for p in sorted((ROOT / "questions").glob("BQ-*.json")):
        bq = load(p)
        schema_check(bq, bq_schema, p.name)
        bad = [i for i in bq["intent"] if i not in intents]
        report(not bad, f"{p.name}: intent in controlled vocabulary"
               + (f" (bad: {bad})" if bad else ""))
        unknown = ([c for c in bq["charts"] if c not in specs]
                   + [c for c in bq["patterns"] if c not in pat_codes])
        report(not unknown and bq["narrative"] in nr_codes,
               f"{p.name}: chart, pattern, and narrative references exist"
               + (f" (unknown {unknown})" if unknown else ""))

    cp_schema = load(ROOT / "schema" / "cp.schema.json")
    rc_schema = load(ROOT / "schema" / "rc.schema.json")
    comps = {}
    for p in sorted((ROOT / "components").glob("CP-*.json")):
        cp = load(p)
        comps[cp["code"]] = cp
        schema_check(cp, cp_schema, p.name)
    recs = {}
    for p in sorted((ROOT / "recipes").glob("RC-*.json")):
        rc = load(p)
        recs[rc["code"]] = rc
        schema_check(rc, rc_schema, p.name)
        report(rc["dl"] in tokens, f"{p.name}: dl {rc['dl']} exists")
        cap = tokens[rc["dl"]]["constitution"]["charts_per_page"]
        n_charts = sum(1 for el in rc["elements"] if el["type"] == "chart")
        report(n_charts <= cap,
               f"{p.name}: {n_charts} chart(s) within {rc['dl']}'s "
               f"charts_per_page = {cap}")

    for d in sorted((ROOT / "golden").iterdir()):
        if not d.is_dir():
            continue
        if d.name.startswith("CP-"):
            for svg_path in sorted(d.glob("CP-*_DL-*.svg")):
                dl = svg_path.stem.split("_")[1]
                fresh = C.render_component(comps[d.name], tokens[dl])
                same = fresh.encode() == svg_path.read_bytes().replace(b"\r\n", b"\n")
                report(same, f"{svg_path.relative_to(ROOT)}: re-render byte-identical")
            continue
        if d.name.startswith("RC-"):
            fresh = RR.render_recipe(recs[d.name])
            svg_path = d / f"{d.name}.svg"
            same = fresh.encode() == svg_path.read_bytes().replace(b"\r\n", b"\n")
            report(same, f"{svg_path.relative_to(ROOT)}: re-render byte-identical")
            continue
        data = load(d / "data.json")
        spec = specs[d.name]
        ct = spec["chart_type"]
        dsp = ROOT / "schema" / "data" / f"{ct}.schema.json"
        if dsp.exists():
            schema_check(data, load(dsp), f"{d.name}/data.json ({ct})")
        if ct == "dots_h":
            lens = {len(r["values"]) for r in data["categories"]}
            report(lens in ({1}, {2}),
                   f"{d.name}/data.json: 1 or 2 dots per row, consistent")
        elif ct == "bullet":
            ok = all(r["bands"] == sorted(r["bands"]) and r["value"] >= 0
                     and r["target"] >= 0 for r in data["categories"])
            report(ok, f"{d.name}/data.json: bands ascending, values non-negative")
        elif ct == "slope":
            report(len(data["categories"]) <= 7
                   and all(r["a"] >= 0 and r["b"] >= 0 for r in data["categories"]),
                   f"{d.name}/data.json: <= 7 lines, values non-negative")
        elif ct == "bar_paired":
            n = len(data["x"])
            report(len(data["series"]) == 2
                   and all(len(s["values"]) == n for s in data["series"]),
                   f"{d.name}/data.json: exactly 2 series, lengths match x")
        elif ct == "waffle":
            report(0 <= data["percent"] <= 100,
                   f"{d.name}/data.json: percent in 0-100")
        elif ct == "funnel":
            vals = [s["value"] for s in data["stages"]]
            report(vals == sorted(vals, reverse=True) and len(vals) <= 6,
                   f"{d.name}/data.json: stages non-increasing, <= 6")
        elif ct in ("bar_h", "bar_v", "lollipop"):
            cats = data["categories"]
            report(sum(1 for c in cats if c.get("highlight")) <= 1,
                   f"{d.name}/data.json: highlight count <= 1")
            report(all(c["value"] >= 0 for c in cats),
                   f"{d.name}/data.json: values >= 0")
        elif ct in ("line", "area", "step", "indexed_line"):
            n = len(data["x"])
            report(all(len(s["values"]) == n for s in data["series"]),
                   f"{d.name}/data.json: series lengths match x")
            report(sum(1 for s in data["series"] if s["role"] == "key") == 1,
                   f"{d.name}/data.json: exactly one key series")
            if "non-decreasing" in " ".join(spec["qa"]):
                mono = all(a <= b for s in data["series"]
                           for a, b in zip(s["values"], s["values"][1:]))
                report(mono, f"{d.name}/data.json: cumulative series non-decreasing")
        elif ct == "bar_v_stacked":
            n = len(data["x"])
            report(all(len(s["values"]) == n for s in data["series"]),
                   f"{d.name}/data.json: segment lengths match x")
            report(len(data["series"]) <= 4,
                   f"{d.name}/data.json: segments <= 4")
            report(all(v >= 0 for s in data["series"] for v in s["values"]),
                   f"{d.name}/data.json: segment values >= 0")
        elif ct == "waterfall":
            report("end" not in data,
                   f"{d.name}/data.json: end total computed, not supplied")
            cum = data["start"]["value"]
            ok = cum >= 0
            for st in data["steps"]:
                cum += st["delta"]
                ok = ok and cum >= 0
            report(ok, f"{d.name}/data.json: cumulative level never below zero")
        elif ct == "bar_h_div":
            vals = [c["value"] for c in data["categories"]]
            report(any(v > 0 for v in vals) and any(v < 0 for v in vals),
                   f"{d.name}/data.json: both signs present (else use CH-RNK-01)")
        elif ct == "matrix":
            nc = len(data["columns"])
            report(all(len(r["cells"]) == nc for r in data["rows"]),
                   f"{d.name}/data.json: cells per row match columns")
            valid = set(spec["display"].keys())
            report(all(c in valid for r in data["rows"] for c in r["cells"]),
                   f"{d.name}/data.json: all statuses in the display enum")
        elif ct == "pie":
            report(all(s["value"] > 0 for s in data["slices"]),
                   f"{d.name}/data.json: slice values > 0")
            report(len(data["slices"]) <= 3,
                   f"{d.name}/data.json: slices <= 3")
        elif ct == "scatter":
            pts = data["points"]
            report(all(q["x"] >= 0 and q["y"] >= 0 for q in pts),
                   f"{d.name}/data.json: points non-negative")
            report(sum(1 for q in pts if q.get("highlight")) <= 1,
                   f"{d.name}/data.json: highlight count <= 1")
        elif ct == "heatmap":
            nc = len(data["columns"])
            report(all(len(r["values"]) == nc for r in data["rows"]),
                   f"{d.name}/data.json: values per row match columns")
            report(all(v >= 0 for r in data["rows"] for v in r["values"]),
                   f"{d.name}/data.json: values >= 0")
        elif ct == "timeline":
            evs = data["events"]
            report(all(0 <= e["pos"] <= 100 for e in evs),
                   f"{d.name}/data.json: positions in 0-100")
            report(all(e["kind"] in ("event", "milestone", "critical") for e in evs)
                   and len(evs) <= 8,
                   f"{d.name}/data.json: kinds valid, events <= 8")
        elif ct == "interval":
            report(all(r["low"] <= r["value"] <= r["high"]
                       for r in data["categories"]),
                   f"{d.name}/data.json: low <= value <= high")
        elif ct == "gantt":
            n = len(data["axis"]["labels"])
            ok = 0 <= data["today"] <= n
            for tk in data["tasks"]:
                if "start" in tk:
                    ok = ok and tk["start"] < tk["end"] <= n
                    if "done_to" in tk:
                        ok = ok and tk["start"] <= tk["done_to"] <= tk["end"]
            report(ok and len(data["tasks"]) <= 10,
                   f"{d.name}/data.json: task bounds valid, tasks <= 10")
        elif ct == "treemap":
            cats = data["categories"]
            report(4 <= len(cats) <= 12,
                   f"{d.name}/data.json: 4 to 12 cells")
            report(all(c["value"] > 0 for c in cats),
                   f"{d.name}/data.json: values > 0")
            report(sum(1 for c in cats if c.get("highlight")) <= 1,
                   f"{d.name}/data.json: highlight count <= 1")
        elif ct == "bump":
            m = len(data["series"])
            n = len(data["x"])
            ok = all(len(s["ranks"]) == n for s in data["series"])
            perm = all(sorted(s["ranks"][i] for s in data["series"])
                       == list(range(1, m + 1)) for i in range(n))
            report(ok and perm and m <= 8,
                   f"{d.name}/data.json: full rank permutation per period, <= 8 series")
        elif ct == "table_bars":
            cats = data["categories"]
            report(all(c["value"] >= 0 and "delta" in c for c in cats)
                   and sum(1 for c in cats if c.get("highlight")) <= 1,
                   f"{d.name}/data.json: values >= 0, deltas present, highlight <= 1")
        elif ct == "bar_paired_h":
            report(all(len(r["values"]) == 2 and min(r["values"]) >= 0
                       for r in data["categories"]),
                   f"{d.name}/data.json: exactly 2 non-negative values per row")
        elif ct == "spine":
            report(all(r["a"] >= 0 and r["b"] >= 0 and r["a"] + r["b"] > 0
                       for r in data["categories"]),
                   f"{d.name}/data.json: two non-negative parts per row")
        elif ct == "surplus_deficit":
            vals = data["values"]
            report(len(vals) == len(data["x"]),
                   f"{d.name}/data.json: values length matches x")
            report(any(v > 0 for v in vals) and any(v < 0 for v in vals),
                   f"{d.name}/data.json: both signs present (else use CH-TIM-03)")
        elif ct == "likert":
            nl = len(data["levels"])
            report(nl == 4 and all(len(r["values"]) == nl
                                   and min(r["values"]) >= 0
                                   for r in data["categories"]),
                   f"{d.name}/data.json: 4 levels, 4 non-negative values per row")
        elif ct == "histogram":
            e, c = data["edges"], data["counts"]
            report(len(e) == len(c) + 1 and e == sorted(e) and len(c) <= 20
                   and all(v >= 0 for v in c),
                   f"{d.name}/data.json: edges ascending, counts >= 0, bins <= 20")
        elif ct == "strip":
            report(all(len(r["values"]) >= 3 and min(r["values"]) >= 0
                       for r in data["categories"]),
                   f"{d.name}/data.json: >= 3 non-negative values per row")
        elif ct == "boxplot":
            report(all(r["min"] <= r["q1"] <= r["med"] <= r["q3"] <= r["max"]
                       for r in data["categories"]),
                   f"{d.name}/data.json: five-number summaries ordered")
        elif ct == "pyramid":
            report(all(r["a"] >= 0 and r["b"] >= 0 for r in data["bands"])
                   and len(data["bands"]) <= 12,
                   f"{d.name}/data.json: sides non-negative, <= 12 bands")
        elif ct == "beeswarm":
            pts = data["points"]
            report(all(q["value"] >= 0 for q in pts) and len(pts) <= 60
                   and sum(1 for q in pts if q.get("highlight")) <= 1,
                   f"{d.name}/data.json: values >= 0, <= 60 points, highlight <= 1")
        elif ct == "area_stacked":
            n = len(data["x"])
            report(len(data["series"]) <= 4
                   and all(len(s["values"]) == n for s in data["series"])
                   and all(v >= 0 for s in data["series"] for v in s["values"]),
                   f"{d.name}/data.json: <= 4 non-negative components, lengths match x")
        elif ct == "sparkline_strip":
            report(all(len(r["values"]) >= 5 and r.get("good") in ("up", "down")
                       for r in data["rows"]),
                   f"{d.name}/data.json: >= 5 points and declared good direction per row")
        elif ct == "fan":
            m = len(data["x"]) - data["split"]
            ok = (len(data["actual"]) == data["split"]
                  and len(data["median"]) == m
                  and len(data["band50"]) == m and len(data["band90"]) == m)
            nest = all(o[0] <= i[0] <= md <= i[1] <= o[1]
                       for md, i, o in zip(data["median"], data["band50"],
                                           data["band90"]))
            report(ok and nest,
                   f"{d.name}/data.json: band90 contains band50 contains median")
        elif ct == "marimekko":
            cols = data["columns"]
            ns = len(data["segment_names"])
            report(len(cols) <= 6 and ns <= 4
                   and all(len(c["segments"]) == ns
                           and min(c["segments"]) >= 0 for c in cols),
                   f"{d.name}/data.json: <= 6x4 cells, segments match names, >= 0")
        elif ct == "column_line":
            n = len(data["x"])
            report(len(data["bars"]["values"]) == n
                   and len(data["line"]["values"]) == n,
                   f"{d.name}/data.json: bar and line lengths match x")
        elif ct == "hexbin":
            pts = data["points"]
            report(len(pts) >= 50
                   and all(q["x"] >= 0 and q["y"] >= 0 for q in pts),
                   f"{d.name}/data.json: >= 50 non-negative points")
        elif ct == "kpi_table":
            report(all(len(r["trend"]) >= 4 and r.get("good") in ("up", "down")
                       for r in data["rows"]),
                   f"{d.name}/data.json: >= 4 trend points and declared good direction")
        elif ct == "prop_symbol":
            cats = data["categories"]
            report(len(cats) <= 7 and all(c["value"] > 0 for c in cats)
                   and sum(1 for c in cats if c.get("highlight")) <= 1,
                   f"{d.name}/data.json: <= 7 positive symbols, highlight <= 1")
        elif ct == "pictogram":
            report(data["unit_value"] > 0
                   and all(c["value"] >= 0 for c in data["categories"]),
                   f"{d.name}/data.json: declared unit value, counts >= 0")
        elif ct == "radar":
            k = len(data["axes"])
            report(3 <= k <= 6 and len(data["series"]) <= 2
                   and all(len(s["values"]) == k and min(s["values"]) >= 0
                           for s in data["series"]),
                   f"{d.name}/data.json: 3-6 shared-unit axes, <= 2 series")
        elif ct == "parliament":
            ps = data["parties"]
            report(len(ps) <= 6 and all(p["seats"] > 0
                                        and isinstance(p["seats"], int)
                                        for p in ps)
                   and sum(p["seats"] for p in ps) <= 200,
                   f"{d.name}/data.json: <= 6 groups, integer seats, total <= 200")
        elif ct == "gauge":
            b = data["bands"]
            report(b == sorted(b) and b[-1] == data["max"]
                   and data["min"] <= data["value"] <= data["max"]
                   and data["min"] <= data["target"] <= data["max"],
                   f"{d.name}/data.json: bands ascending, value and target in range")
        elif ct == "streamgraph":
            n = len(data["x"])
            report(len(data["series"]) <= 4
                   and all(len(s["values"]) == n and min(s["values"]) >= 0
                           for s in data["series"]),
                   f"{d.name}/data.json: <= 4 non-negative bands, lengths match x")
        elif ct == "horizon":
            report(len(data["rows"]) <= 12
                   and all(len(r["values"]) >= 8 and min(r["values"]) >= 0
                           for r in data["rows"]),
                   f"{d.name}/data.json: <= 12 rows, >= 8 non-negative points each")
        elif ct == "sunburst":
            gs = data["groups"]
            report(len(gs) <= 4
                   and all(len(g["children"]) <= 4
                           and all(c["value"] > 0 for c in g["children"])
                           for g in gs),
                   f"{d.name}/data.json: <= 4 groups x 4 children, values > 0")
        elif ct == "circle_pack":
            cats = data["categories"]
            report(3 <= len(cats) <= 12 and all(c["value"] > 0 for c in cats)
                   and sum(1 for c in cats if c.get("highlight")) <= 1,
                   f"{d.name}/data.json: 3-12 positive circles, highlight <= 1")
        elif ct == "parallel":
            k = len(data["axes"])
            its = data["items"]
            report(3 <= k <= 5 and len(its) <= 12
                   and all(len(it["values"]) == k and min(it["values"]) >= 0
                           for it in its)
                   and sum(1 for it in its if it.get("highlight")) <= 1,
                   f"{d.name}/data.json: 3-5 axes, <= 12 items, highlight <= 1")
        elif ct == "splom":
            report(len(data["axes"]) == 3 and len(data["points"]) <= 30
                   and all(len(q["values"]) == 3 and min(q["values"]) >= 0
                           for q in data["points"]),
                   f"{d.name}/data.json: exactly 3 variables, <= 30 points")
        elif ct == "chord":
            M = data["flows"]
            k = len(data["nodes"])
            report(k <= 6 and len(M) == k
                   and all(len(row) == k and min(row) >= 0 for row in M)
                   and all(M[i][i] == 0 for i in range(k)),
                   f"{d.name}/data.json: square matrix, zero diagonal, <= 6 nodes")
        elif ct == "choropleth":
            rs = data["regions"]
            report(all(len(r["polygon"]) >= 3 and r["value"] >= 0
                       and all(0 <= x <= 100 and 0 <= y <= 100
                               for x, y in r["polygon"]) for r in rs),
                   f"{d.name}/data.json: closed polygons in unit square, values >= 0")
        elif ct == "symbol_map":
            report(all(q["value"] > 0 and 0 <= q["at"][0] <= 100
                       and 0 <= q["at"][1] <= 100 for q in data["places"])
                   and len(data["places"]) <= 10,
                   f"{d.name}/data.json: <= 10 positive placed symbols")
        elif ct == "route_progress":
            fr = [st["at"] for st in data["stations"]]
            report(0 <= data["done_to"] <= 1 and fr == sorted(fr)
                   and all(st["kind"] in ("done", "current", "pending")
                           for st in data["stations"])
                   and sum(1 for st in data["stations"]
                           if st["kind"] == "current") <= 1,
                   f"{d.name}/data.json: stations ordered, one current, done in 0-1")
        elif ct == "dot_density":
            report(data["unit_value"] > 0
                   and all(0 <= x <= 100 and 0 <= y <= 100
                           for x, y in data["dots"]),
                   f"{d.name}/data.json: declared dot value, dots in unit square")
        elif ct == "flow_map":
            report(len(data["flows"]) <= 8
                   and all(f["value"] > 0 for f in data["flows"]),
                   f"{d.name}/data.json: <= 8 positive flows")
        elif ct == "sankey":
            names = {nd["name"]: (ci, nd["value"])
                     for ci, c in enumerate(data["columns"])
                     for nd in c["nodes"]}
            ok = len(data["columns"]) in (2, 3)
            outs = {}
            ins = {}
            for lk in data["links"]:
                ok = ok and lk["from"] in names and lk["to"] in names
                ok = ok and names[lk["to"]][0] == names[lk["from"]][0] + 1
                outs[lk["from"]] = outs.get(lk["from"], 0) + lk["value"]
                ins[lk["to"]] = ins.get(lk["to"], 0) + lk["value"]
            for name, (ci, v) in names.items():
                if ci == 0:
                    ok = ok and outs.get(name, 0) == v
                elif ci == len(data["columns"]) - 1:
                    ok = ok and ins.get(name, 0) == v
            report(ok, f"{d.name}/data.json: adjacent links, per-node conservation")
        elif ct == "network":
            ids = {nd["id"] for nd in data["nodes"]}
            report(len(data["nodes"]) <= 15
                   and all(e["a"] in ids and e["b"] in ids
                           for e in data["edges"])
                   and sum(1 for nd in data["nodes"]
                           if nd.get("highlight")) <= 1,
                   f"{d.name}/data.json: <= 15 nodes, edges resolve, highlight <= 1")
        elif ct == "violin":
            ok = all(len(r["grid"]) == len(r["density"])
                     and r["grid"] == sorted(r["grid"])
                     and min(r["density"]) >= 0
                     and r["grid"][0] <= r["median"] <= r["grid"][-1]
                     for r in data["categories"])
            report(ok, f"{d.name}/data.json: grids ascending, densities >= 0, "
                       f"median in range")

        for svg_path in sorted(d.glob("CH-*_DL-*.svg")):
            dl_code = svg_path.stem.split("_")[1]
            fresh = R.render(spec, tokens[dl_code], data)
            same = fresh.encode() == svg_path.read_bytes().replace(b"\r\n", b"\n")
            report(same, f"{svg_path.relative_to(ROOT)}: re-render byte-identical")

    import io
    import zipfile
    try:
        import render_pptx as P
        for pp in sorted((ROOT / "golden").glob("*/*.pptx")):
            svg = pp.with_suffix(".svg").read_text(encoding="utf-8")
            fresh = P.convert(svg)
            def members(b):
                with zipfile.ZipFile(io.BytesIO(b)) as z:
                    return {n: z.read(n) for n in z.namelist()}
            same = members(fresh) == members(pp.read_bytes())
            report(same, f"{pp.relative_to(ROOT)}: pptx members match SVG source")
    except ImportError:
        report(False, "python-pptx missing: pptx conformance set not checked")

    for rel, content in B.build_all().items():
        p = ROOT / rel
        if not p.exists():
            report(False, f"{rel}: missing (run tools/build_blocks.py)")
            continue
        same = content.encode() == p.read_bytes().replace(b"\r\n", b"\n")
        report(same, f"{rel}: matches specs/tokens")

    print()
    if FAILS:
        print(f"BLOCKED: {len(FAILS)} failure(s)")
        return 2
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
