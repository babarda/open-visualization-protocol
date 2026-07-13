"""Generate docs/: the OVP documentation site, ready for GitHub Pages.

Every page is GENERATED from the canonical sources (specs/, tokens/,
patterns/, decision/, components/, recipes/, golden/, PROTOCOL.md,
TAXONOMY.md, catalogue/foundations/). Never hand-edit docs/.

    python tools/build_site.py

Publish: push the repo, then GitHub Settings > Pages > deploy from
branch, folder /docs.
"""

import html
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import build_blocks as B  # noqa: E402
import render as CH  # noqa: E402
import render_cp as CPD  # noqa: E402

OUT = ROOT / "docs"

CSS = """
:root { --ink:#1A2323; --body:#4A5757; --line:#E2E8E8; --accent:#0F766E;
        --accent-soft:#E6F2F1; --bg:#F7F9F9; --card:#FFFFFF; }
* { margin:0; padding:0; box-sizing:border-box; }
html { scroll-behavior:smooth; }
body { font-family:'Segoe UI',system-ui,Arial,sans-serif; color:var(--ink);
       background:var(--bg); font-size:15px; line-height:1.55; }
nav { position:sticky; top:0; z-index:10; background:var(--card);
      border-bottom:1px solid var(--line); padding:0 32px; display:flex;
      align-items:center; gap:4px; flex-wrap:wrap; }
nav .brand { font-weight:700; font-size:15px; color:var(--ink);
             margin-right:16px; padding:14px 0; text-decoration:none; }
nav .brand span { color:var(--accent); }
nav a.item { color:var(--body); text-decoration:none; font-size:13px;
             font-weight:600; padding:14px 10px; border-bottom:2px solid transparent; }
nav a.item:hover { color:var(--ink); }
nav a.item.on { color:var(--accent); border-bottom-color:var(--accent); }
main { max-width:1080px; margin:0 auto; padding:40px 32px 96px; }
h1 { font-size:28px; line-height:1.25; margin-bottom:8px; }
h2 { font-size:20px; margin:36px 0 10px; }
h3 { font-size:16px; margin:24px 0 8px; }
h4 { font-size:14px; margin:18px 0 6px; }
p { margin-bottom:12px; color:var(--body); }
p b, li b { color:var(--ink); }
.lead { font-size:17px; color:var(--body); max-width:760px; }
hr { border:none; border-top:1px solid var(--line); margin:28px 0; }
ul, ol { margin:0 0 14px 22px; color:var(--body); }
li { margin-bottom:4px; }
a { color:var(--accent); }
code { background:var(--accent-soft); border-radius:3px; padding:1px 5px;
       font-size:13px; font-family:Consolas,monospace; color:var(--ink); }
pre { background:#10201E; color:#D9E6E4; border-radius:8px; padding:16px;
      font-size:13px; overflow-x:auto; margin:0 0 16px; }
pre code { background:none; color:inherit; padding:0; }
table { border-collapse:collapse; width:100%; margin:0 0 18px; font-size:13.5px; }
th { text-align:left; font-size:11px; letter-spacing:1px; text-transform:uppercase;
     color:var(--body); border-bottom:2px solid var(--line); padding:8px 10px; }
td { border-bottom:1px solid var(--line); padding:8px 10px; vertical-align:top;
     color:var(--body); }
td:first-child { color:var(--ink); font-weight:600; white-space:nowrap; }
.grid { display:grid; gap:16px; }
.g2 { grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); }
.g3 { grid-template-columns:repeat(auto-fill,minmax(280px,1fr)); }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px;
        padding:20px; }
.card h3 { margin:0 0 6px; font-size:15px; }
.card p { font-size:13.5px; margin-bottom:0; }
a.card { text-decoration:none; display:block; transition:border-color .15s; }
a.card:hover { border-color:var(--accent); }
.tag { display:inline-block; background:var(--accent-soft); color:var(--accent);
       font-size:11px; font-weight:700; border-radius:20px; padding:2px 10px;
       margin:0 4px 4px 0; letter-spacing:.4px; }
.tag.warn { background:#FBEAEA; color:#A33; }
.kicker { font-size:11px; font-weight:700; letter-spacing:2px; color:var(--accent);
          text-transform:uppercase; margin-bottom:6px; }
.hero { padding:24px 0 8px; }
.stats { display:flex; gap:28px; flex-wrap:wrap; margin:24px 0 8px; }
.stat b { display:block; font-size:26px; color:var(--ink); }
.stat span { font-size:12px; color:var(--body); letter-spacing:.5px; }
.swatches { display:flex; height:14px; border-radius:7px; overflow:hidden;
            margin:10px 0 4px; border:1px solid var(--line); }
.swatches i { flex:1; }
.palette td i { display:inline-block; width:14px; height:14px; border-radius:3px;
                border:1px solid var(--line); vertical-align:-2px; margin-right:8px; }
.motto { font-size:17px; font-style:italic; color:var(--ink); margin-bottom:4px; }
figure { background:var(--card); border:1px solid var(--line); border-radius:10px;
         padding:12px; margin-bottom:16px; }
figure svg { width:100%; height:auto; display:block; }
.thumb { border:1px solid var(--line); border-radius:8px; overflow:hidden;
         margin:0 0 12px; line-height:0; }
.thumb svg { width:100%; height:auto; display:block; }
figcaption { font-size:11px; font-weight:700; letter-spacing:1px; color:var(--body);
             margin-bottom:8px; }
.copybar { display:flex; gap:8px; flex-wrap:wrap; margin:14px 0 22px; }
button.copy { font:600 12.5px 'Segoe UI',system-ui,sans-serif; color:#fff;
              background:var(--accent); border:none; border-radius:6px;
              padding:9px 16px; cursor:pointer; }
button.copy.alt { background:var(--card); color:var(--accent);
                  border:1px solid var(--accent); }
button.copy.copied { background:#2E8B57; border-color:#2E8B57; color:#fff; }
.dlbar { display:flex; gap:6px; flex-wrap:wrap; margin:14px 0; }
.dlbtn { font:600 11.5px 'Segoe UI',system-ui,sans-serif; color:var(--body);
         background:var(--card); border:1px solid var(--line); border-radius:20px;
         padding:5px 12px; cursor:pointer; }
.dlbtn.on { background:var(--accent); border-color:var(--accent); color:#fff; }
.two { display:grid; grid-template-columns:2fr 1fr; gap:24px; }
@media (max-width:860px) { .two { grid-template-columns:1fr; } }
details { margin:0 0 14px; }
summary { cursor:pointer; font-weight:600; font-size:14px; }
details > *:not(summary) { margin-top:10px; }
input.search { width:100%; max-width:420px; font-size:14px; padding:10px 14px;
               border:1px solid var(--line); border-radius:8px; margin:8px 0 20px;
               background:var(--card); color:var(--ink); }
footer { border-top:1px solid var(--line); color:var(--body); font-size:12px;
         padding:20px 32px; text-align:center; }
.crumb { font-size:12.5px; margin-bottom:14px; }
.crumb a { text-decoration:none; }
.tocbox { background:var(--card); border:1px solid var(--line); border-radius:10px;
          padding:14px 18px; font-size:13.5px; margin-bottom:24px; }
"""

JS = """
function copyPayload(btn, key) {
  var t = PAYLOADS[key];
  navigator.clipboard.writeText(t).then(function() {
    var old = btn.textContent;
    btn.classList.add('copied'); btn.textContent = 'Copied';
    setTimeout(function(){ btn.classList.remove('copied'); btn.textContent = old; }, 1500);
  }, function() { alert('Clipboard blocked by the browser.'); });
}
function showDL(code) {
  document.querySelectorAll('.dlview').forEach(function(e){ e.style.display = 'none'; });
  var v = document.getElementById('v-' + code);
  if (v) v.style.display = 'block';
  document.querySelectorAll('.dlbtn').forEach(function(b){
    b.classList.toggle('on', b.dataset.dl === code); });
  window.CURRENT_DL = code;
}
function copyDS(btn) { copyPayload(btn, 'ds-' + (window.CURRENT_DL || 'DL-02')); }
function filterCards(q) {
  q = q.toLowerCase();
  document.querySelectorAll('.findable').forEach(function(c) {
    c.style.display = c.textContent.toLowerCase().indexOf(q) >= 0 ? '' : 'none';
  });
}
"""

NAV = [("index.html", "Home"), ("protocol.html", "Protocol"),
       ("foundations.html", "Foundations"), ("taxonomy.html", "Taxonomy"),
       ("languages/index.html", "Languages"), ("charts/index.html", "Charts"),
       ("questions.html", "Questions"),
       ("patterns.html", "Patterns"), ("decider.html", "Decider"),
       ("components.html", "Components"), ("recipes.html", "Recipes"),
       ("implement.html", "Implement"), ("ai.html", "AI")]

# hero slide per language: a realistic deliverable page in that language's
# voice. The chart is matched to what the language ships on; the title and
# eyebrow come from the chart's own golden data (so the headline always
# matches the numbers on the page); the rail carries what that language
# would actually carry (KPI cards, chips, a decision callout).
HERO = {
    "DL-01": {"chart": "CH-FLO-01",   # AGRAW: explain the year to the board
              "kpis": [{"label": "FORECAST", "value": "118 pts",
                        "delta": "+18 vs budget", "tone": "negative"}],
              "chips": [],
              "callout": ["Decision asked of the board:",
                          "resequence to recover 8 points;",
                          "logistics carries two thirds."]},
    "DL-02": {"chart": "CH-TIM-02",   # KATA: weekly progress vs plan
              "kpis": [{"label": "ACTUAL", "value": "63%",
                        "delta": "-9 pts vs plan", "tone": "negative"},
                       {"label": "PLAN", "value": "72%",
                        "delta": "month 8 of 12", "tone": "neutral"}],
              "chips": [],
              "callout": ["Gap steady since April.",
                          "Recovery review each Wednesday."]},
    "DL-03": {"chart": "CH-COR-01",   # LOGOS: evidence, two measures
              "kpis": [],
              "chips": [],
              "callout": ["Claim: low progress pairs with deep punch.",
                          "Evidence: 8 systems plotted, D flagged.",
                          "Next: split D's 63 items by cause."]},
    "DL-04": {"chart": "CH-TIM-09",
              "crop": [0, 104, 960, 344],   # SHILPA: sequenced schedule
              "kpis": [],
              "chips": [{"status": "on_track", "word": "SEQUENCE HOLDS", "w": 160}],
              "callout": ["Hold point: loop tests complete",
                          "before energization.",
                          "Float on the driver: 2 days."]},
    "DL-05": {"chart": "CH-TAB-01",
              "crop": [0, 112, 960, 280],   # OBEYA: the stand-up wall
              "kpis": [],
              "chips": [{"status": "critical", "word": "SYSTEM D . TEST", "w": 170},
                        {"status": "on_track", "word": "A + B . HANDOVER", "w": 175}],
              "callout": ["Owners named in the morning round;",
                          "blockers cleared on the wall."]},
    "DL-06": {"chart": "CH-TIM-15",
              "crop": [0, 210, 960, 210],   # LEX: chronology as argument
              "kpis": [],
              "chips": [],
              "callout": ["Every event carries its reference.",
                          "The chronology is the argument;",
                          "the record decides, not the memory."]},
    "DL-07": {"chart": "CH-TIM-01",   # SAGA: the trend continues the story
              "kpis": [],
              "chips": [],
              "callout": ["The gap opened in April and held.",
                          "Week 28 continues the account",
                          "started in week 1."]},
    "DL-08": {"chart": "CH-TIM-13",   # SENTINEL: watched value, steady state
              "kpis": [{"label": "STOCK", "value": "41 units",
                        "delta": "-23 since June", "tone": "negative"}],
              "chips": [{"status": "watch", "word": "WATCH . REORDER", "w": 165}],
              "callout": ["Alarm level unchanged at 30 units."]},
    "DL-09": {"chart": "CH-COR-02",   # ATLAS: position tells priority
              "kpis": [],
              "chips": [],
              "callout": ["Position tells priority:",
                          "D holds the largest scope",
                          "and the least readiness."]},
    "DL-10": {"chart": "CH-PTW-06",
              "crop": [0, 116, 960, 360],   # BASIRA: progress you can see
              "kpis": [{"label": "COMPLETE", "value": "62%",
                        "delta": "+4 vs last visit", "tone": "positive"}],
              "chips": [],
              "callout": ["Same angle, same light:",
                          "every visit records the change."]},
    "DL-11": {"chart": "CH-RNK-06",
              "crop": [0, 120, 960, 250],   # SUTRA: condensed, exact
              "kpis": [],
              "chips": [],
              "callout": ["One page, exact values,",
                          "nothing left to interpret.",
                          "Piping first: 84 of 213."]},
    "DL-12": {"chart": "CH-MAG-04",
              "crop": [0, 124, 960, 192],   # NOROSHI: the miss, escalated
              "kpis": [],
              "chips": [{"status": "critical", "word": "DOCS ON TIME . -14", "w": 180},
                        {"status": "watch", "word": "DELIVERY OTD . -8", "w": 175}],
              "callout": ["Escalated 07:00, response due 12:00."]},
    "DL-13": {"chart": "CH-DEV-01",
              "crop": [0, 100, 960, 270],   # MIZAN: both sides, one scale
              "kpis": [],
              "chips": [],
              "callout": ["Both sides of the story, one scale.",
                          "Electrical carries the deepest slip;",
                          "mechanical funds the recovery."]},
    "DL-14": {"chart": "CH-RNK-01",
              "crop": [0, 100, 960, 270],   # EVIDENTIA: the exhibit that proves
              "kpis": [],
              "chips": [],
              "callout": ["So what: one section, one crew.",
                          "34 items is the lever;",
                          "everything else is noise."]},
    "DL-15": {"chart": "CH-TIM-05",
              "crop": [0, 100, 960, 376],   # ABRID: the path from A to B
              "kpis": [],
              "chips": [],
              "callout": ["Three disciplines improved,",
                          "mechanical slipped: the paths",
                          "matter more than the points."]},
    "DL-16": {"chart": "CH-MAG-02",   # TELOS: result against intention
              "kpis": [{"label": "Q4 GAP", "value": "+21 k$",
                        "delta": "over budget", "tone": "negative"}],
              "chips": [],
              "callout": ["Result against intention,",
                          "quarter by quarter, no smoothing."]},
}


def _wrap_title(title, width=58):
    if len(title) <= width:
        return [title]
    # balanced two-line wrap: break at the space nearest the midpoint
    target = min(width, len(title) // 2 + 6)
    words = title.split()
    line1 = ""
    while words and (not line1 or len(line1) + len(words[0]) + 1 <= target):
        line1 = (line1 + " " + words.pop(0)).strip()
    return [line1, " ".join(words)]


SHOWCASE_ORDER = ["DL-08", "DL-01", "DL-02", "DL-14", "DL-12", "DL-13"]

# the features reel: the best-looking chart golds, one clean identity
CHART_REEL = ["CH-RNK-01", "CH-TIM-02", "CH-FLO-01", "CH-RNK-04",
              "CH-MAG-04", "CH-DST-07", "CH-FLO-02", "CH-TAB-03",
              "CH-DEV-04", "CH-SPA-03"]


def _carousel(frames, w, h, seg=2.4, fade=0.5):
    """Stacked cross-fade carousel from full-SVG strings (opaque
    backgrounds required). CSS keyframes: plays inside README <img>."""
    n = len(frames)
    total = seg * n
    css = []
    for i in range(1, n):
        s = i * seg / total * 100
        f = (i * seg + fade) / total * 100
        css.append(f"@keyframes k{i} {{ 0%, {s:.2f}% {{ opacity: 0; }} "
                   f"{f:.2f}%, 100% {{ opacity: 1; }} }}")
        css.append(f"#slide{i} {{ opacity: 0; "
                   f"animation: k{i} {total:.1f}s linear infinite; }}")
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" '
             f'height="{h}" viewBox="0 0 {w} {h}">',
             "<style>" + " ".join(css) + "</style>"]
    for i, svg in enumerate(frames):
        inner = svg.split("\n", 1)[1].rsplit("</svg>", 1)[0]
        parts.append(f'<g id="slide{i}">{inner}</g>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def chart_showcase_svg():
    frames = [svg_of(code, "DL-02") for code in CHART_REEL]
    return _carousel(frames, 960, 540)


def showcase_svg(heroes):
    """Hero-slide carousel: six languages, one page each."""
    return _carousel([heroes[c] for c in SHOWCASE_ORDER], 1280, 720,
                     seg=3.0, fade=0.6)


def language_hero(tok, comps):
    """One 1280x720 slide that shows the language doing its job: eyebrow
    and kicker per its chrome, the chart's own action title set large in
    the display font, the occasion-matched chart at full width, and a
    rail of the components this language would really carry."""
    ph = tok["philosophy"]
    pal = tok["palette"]
    body = tok["fonts"]["body"]["family"]
    disp = tok["fonts"]["display"]
    cfg = HERO[tok["code"]]
    data = load(ROOT / "golden" / cfg["chart"] / "data.json")
    spec = load(ROOT / "specs" / f'{cfg["chart"]}.json')

    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" '
             'viewBox="0 0 1280 720">',
             f'<rect width="1280" height="720" fill="{pal["background"]}"/>']

    if tok["chrome"]["kicker"]:
        parts.append(f'<rect x="48" y="50" width="28" height="4" '
                     f'fill="{pal["primary"]}"/>')
    if tok["chrome"]["eyebrow"]:
        parts.append(CH.text(48, 72, data["eyebrow"], 12, body, pal["body"],
                             weight=600, spacing=2))
    lines = _wrap_title(data["title"])
    parts.append(CH.text(48, 112, lines[0], 34, disp["family"], pal["ink"],
                         weight=disp["weight"]))
    if len(lines) > 1:
        parts.append(CH.text(48, 152, lines[1], 34, disp["family"], pal["ink"],
                             weight=disp["weight"]))
    sub_y = 146 if len(lines) == 1 else 182
    motto = ph["motto"].rstrip(".")
    parts.append(CH.text(48, sub_y, f'{motto} . {tok["name"]} on '
                                    f'{tok["occasions"][0]}',
                         15, body, pal["body"]))

    inner = CH.render(spec, tok, data, bare=True)
    chart_body = inner.split("\n", 1)[1].rsplit("</svg>", 1)[0]
    cx, cy, cw, chh = cfg.get("crop", [0, 92, 960, 428])
    disp_h = 832 / cw * chh
    disp_y = 204 + max(0, (371 - disp_h) / 2)
    parts.append(f'<svg x="48" y="{CH.fmt(disp_y)}" width="832" '
                 f'height="{CH.fmt(disp_h)}" viewBox="{cx} {cy} {cw} {chh}">')
    parts.append(chart_body.rstrip("\n"))
    parts.append("</svg>")

    ry = 204
    for card in cfg["kpis"]:
        CPD.draw_kpi_card(parts, tok, comps["CP-KPI-01"], 912, ry, card)
        ry += comps["CP-KPI-01"]["params"]["h"] + 14
    for chip in cfg["chips"]:
        CPD.draw_status_chip(parts, tok, comps["CP-STA-01"], 912, ry, chip)
        ry += comps["CP-STA-01"]["params"]["h"] + 10
    if cfg["callout"]:
        P = comps["CP-CAL-01"]["params"]
        n = len(cfg["callout"])
        ch = 2 * P["pad"] + P["line_height"] * (n - 1) + P["text_size"]
        CPD.draw_callout(parts, tok, comps["CP-CAL-01"], 912, ry + 6,
                         {"w": 320, "h": ch, "lines": cfg["callout"]})

    CPD.draw_source(parts, tok, comps["CP-TXT-02"], 48, 688,
                    {"text": f'{data["source"]}  .  Open Visualization '
                             f'Protocol, {tok["code"]} {tok["name"]}'})
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


FAMILY_NAMES = {
    "RNK": ("Ranking", "who is biggest or smallest, ordered"),
    "MAG": ("Magnitude", "how big things are, natural order kept"),
    "TIM": ("Change over time", "how it moved: trend, progress"),
    "PTW": ("Part-to-whole", "how a total splits"),
    "DEV": ("Deviation", "distance from a reference: plan, budget, zero"),
    "DST": ("Distribution", "how values spread"),
    "COR": ("Correlation", "how two measures relate"),
    "SPA": ("Spatial", "where"),
    "FLO": ("Flow", "movement between states or stages"),
    "TAB": ("Tables", "exact values the reader will look up"),
}


def esc(s):
    return html.escape(str(s), quote=True)


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def payload_script(payloads):
    blob = json.dumps(payloads).replace("</", "<\\/")
    return f"<script>const PAYLOADS = {blob};</script>"


# ------------------------------------------------------------- markdown
def _inline(s):
    s = esc(s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", r'<a href="\2">\1</a>', s)
    return s


def _cells(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def md_to_html(md):
    lines = md.split("\n")
    out = []
    i = 0
    para = []
    lst = None  # "ul" | "ol" | None

    def flush_para():
        if para:
            out.append(f"<p>{_inline(' '.join(para))}</p>")
            para.clear()

    def close_list():
        nonlocal lst
        if lst:
            out.append(f"</{lst}>")
            lst = None

    while i < len(lines):
        ln = lines[i]
        if ln.startswith("```"):
            flush_para(); close_list()
            buf = []
            i += 1
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            out.append("<pre><code>" + esc("\n".join(buf)) + "</code></pre>")
            i += 1
            continue
        if (ln.startswith("|") and i + 1 < len(lines)
                and re.match(r"^\|[\s\-|:]+\|?\s*$", lines[i + 1])):
            flush_para(); close_list()
            head = _cells(ln)
            i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(_cells(lines[i])); i += 1
            out.append("<table><tr>" + "".join(f"<th>{_inline(h)}</th>" for h in head)
                       + "</tr>")
            for r in rows:
                out.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in r)
                           + "</tr>")
            out.append("</table>")
            continue
        m = re.match(r"^(#{1,4})\s+(.*)$", ln)
        if m:
            flush_para(); close_list()
            n = len(m.group(1))
            out.append(f"<h{n}>{_inline(m.group(2))}</h{n}>")
            i += 1
            continue
        if ln.strip() in ("---", "***"):
            flush_para(); close_list()
            out.append("<hr>")
            i += 1
            continue
        m = re.match(r"^[-*]\s+(.*)$", ln)
        if m:
            flush_para()
            if lst != "ul":
                close_list(); out.append("<ul>"); lst = "ul"
            item = m.group(1)
            while i + 1 < len(lines) and re.match(r"^\s{2,}\S", lines[i + 1]):
                i += 1
                item += " " + lines[i].strip()
            out.append(f"<li>{_inline(item)}</li>")
            i += 1
            continue
        m = re.match(r"^\d+\.\s+(.*)$", ln)
        if m:
            flush_para()
            if lst != "ol":
                close_list(); out.append("<ol>"); lst = "ol"
            item = m.group(1)
            while i + 1 < len(lines) and re.match(r"^\s{2,}\S", lines[i + 1]):
                i += 1
                item += " " + lines[i].strip()
            out.append(f"<li>{_inline(item)}</li>")
            i += 1
            continue
        if not ln.strip():
            flush_para(); close_list()
            i += 1
            continue
        para.append(ln.strip())
        i += 1
    flush_para(); close_list()
    return "\n".join(out)


# ----------------------------------------------------------------- shell
def page(title, body, depth=0, active="", extra_head=""):
    pre = "../" * depth
    items = "".join(
        f'<a class="item{" on" if href == active else ""}" '
        f'href="{pre}{href}">{label}</a>'
        for href, label in NAV)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}</style><script>{JS}</script>{extra_head}</head><body>
<nav><a class="brand" href="{pre}index.html">OVP<span>.</span></a>{items}</nav>
<main>
{body}
</main>
<footer>Open Visualization Protocol, v0.1-draft. This site is generated by
tools/build_site.py from the canonical specs and tokens. Do not hand-edit.</footer>
</body></html>"""


def write(rel, content):
    p = OUT / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8", newline="\n")
    print(f"wrote docs/{rel}")


def svg_of(code, dl=None):
    name = f"{code}_{dl}.svg" if dl else f"{code}.svg"
    return (ROOT / "golden" / code / name).read_text(encoding="utf-8")


# ----------------------------------------------------------------- pages
def build_index(toks, specs, pats, comps, recs):
    golden_count = sum(1 for _ in (ROOT / "golden").glob("CH-*/CH-*_DL-*.svg"))
    warn = sum(1 for s in specs if any("warn" in a.lower() or "misread" in a.lower()
                                       for a in []))  # unused; kept simple
    body = f"""
<div class="hero">
<div class="kicker">Open Visualization Protocol</div>
<h1>Describe the chart once.<br>Every renderer draws the same pixels.</h1>
<p class="lead">OVP is an open, deterministic, AI-native standard for
information design. A visualization is an instruction, not an artwork:
<code>Render CH-TIM-02 in DL-03 with data.json</code>. Any agent, human,
or renderer that speaks the protocol produces the same visual result
from the same instruction.</p>
<div class="stats">
<div class="stat"><b>{len(toks)}</b><span>DESIGN LANGUAGES</span></div>
<div class="stat"><b>{len(specs)}</b><span>CHART OBJECTS BUILT</span></div>
<div class="stat"><b>{len(pats)}</b><span>ANALYTICAL PATTERNS</span></div>
<div class="stat"><b>{len(comps)}</b><span>COMPONENTS</span></div>
<div class="stat"><b>{len(recs)}</b><span>RECIPES</span></div>
<div class="stat"><b>{golden_count}</b><span>GOLDEN RENDERS</span></div>
</div>
</div>

<h2>The principles</h2>
<div class="grid g3">
<div class="card"><h3>Deterministic by contract</h3><p>Same spec, same
tokens, same data: byte-identical output, every run, every machine. No
randomness, no timestamps, no jitter. A QA gate re-renders every golden
and blocks the repo on a single byte of drift.</p></div>
<div class="card"><h3>Roles, never hex</h3><p>Chart specs name color
roles (primary, muted, negative). Design languages bind roles to hex.
Rebranding a whole deliverable is swapping one token file; no spec
changes, no re-authoring.</p></div>
<div class="card"><h3>Honest by rule</h3><p>Zero baselines. Direct labels
instead of legends. Declared inputs only: no silent KDE, no silent trend
lines, no unstated normalization. Every chart ships with anti-patterns
and a QA checklist.</p></div>
<div class="card"><h3>Message first</h3><p>Charts are coded by what the
message is (ranking, deviation, distribution), not by shape. The first
question an agent answers is "what is the message"; the shape is
metadata.</p></div>
<div class="card"><h3>AI-native</h3><p>A controlled intent vocabulary,
machine metadata on every object, a decision engine for language choice,
and copy-paste blocks in two flavors: hex-resolved for design systems,
role-based for themeable skills.</p></div>
<div class="card"><h3>Canonical JSON, generated everything else</h3>
<p>Specs and tokens are the source of truth. Blocks, chooser, decider,
pattern docs, previews, and this entire site are generated from them and
drift-gated where it matters.</p></div>
</div>

<h2>How an agent resolves a request</h2>
<div class="tocbox">
<b>1. Decider</b> picks the design language from audience, purpose, and
medium. &nbsp;<b>2. Patterns</b> map what was found in the data to chart
codes. &nbsp;<b>3. Charts</b> disambiguate by message intent, with
"see instead" exits. &nbsp;<b>4. Render</b> the code in the language:
exact px, exact hex, no adjectives.</div>

<h2>Learn</h2>
<div class="grid g2">
<a class="card" href="manifesto.html"><h3>Manifesto</h3>
<p>Why OVP exists and the seven laws that never break: determinism,
roles never hex, honesty by construction, message first.</p></a>
<a class="card" href="foundations.html"><h3>Foundations</h3>
<p>The rule sets everything builds on: token contract, canvas and grid,
type scale, contrast, numbers and scales, perceptual research.</p></a>
</div>
<h2>Reference</h2>
<div class="grid g2">
<a class="card" href="protocol.html"><h3>The protocol</h3>
<p>The normative reference: object grammar, layer model, determinism
contract, conformance levels, lifecycle and stability policy.</p></a>
<a class="card" href="taxonomy.html"><h3>Taxonomy</h3>
<p>The full object map: every family, every entry, statuses, and the
exclusions with their reasons.</p></a>
</div>
<h2>Explore</h2>
<div class="grid g2">
<a class="card" href="languages/index.html"><h3>Design languages</h3>
<p>{len(toks)} complete visual identities, each built on a philosophy:
a civilization, a principle, a motto, and design laws that explain why
the rules exist.</p></a>
<a class="card" href="charts/index.html"><h3>Chart objects</h3>
<p>{len(specs)} built entries coded by message family, each with exact
geometry, honesty rules, QA checklist, golden renders in all
{len(toks)} languages, and one-click copy blocks.</p></a>
</div>
<h2>Build</h2>
<div class="grid g2">
<a class="card" href="questions.html"><h3>Business questions</h3>
<p>Start from what is being asked: each question names its observations,
patterns, charts, and the narrative skeleton that tells the finding.</p></a>
<a class="card" href="patterns.html"><h3>Analytical patterns</h3>
<p>The layer above charts: recognize what the data shows, read its
meaning, take the recommended chart codes.</p></a>
<a class="card" href="decider.html"><h3>Language decider</h3>
<p>Audience, purpose, medium in; design language out. Ordered rules over
a controlled vocabulary, validator-enforced.</p></a>
<a class="card" href="components.html"><h3>Components</h3>
<p>Titles, sources, KPI cards, chips, callouts: the furniture around
charts, same role contract, composable into recipes.</p></a>
<a class="card" href="recipes.html"><h3>Recipes</h3>
<p>Fully determined pages: language, charts, components, exact
positions. A recurring deliverable renders identically forever.</p></a>
</div>
<h2>Implement and automate</h2>
<div class="grid g2">
<a class="card" href="implement.html"><h3>Implement</h3>
<p>Build an OVP-conformant renderer or validator from the published
schemas, the determinism contract, and the conformance levels. No
questions to the authors required.</p></a>
<a class="card" href="ai.html"><h3>AI</h3>
<p>How agents speak OVP: the resolution order, the machine registry,
the controlled vocabularies, and the copy-paste blocks.</p></a>
</div>

<h2>Get the code</h2>
<p>Every chart page carries copy buttons for two block flavors.
<b>Design-system blocks</b> resolve colors to hex for one language:
paste into any CLAUDE.md or design-system doc, zero dependencies.
<b>Skill blocks</b> stay role-based: paste next to a language token
block and re-theme by swapping that one block.</p>
"""
    write("index.html", page("OVP . Open Visualization Protocol", body,
                             active="index.html"))


def build_md_page(rel, title, md_path, active):
    body = f"<h1>{esc(title)}</h1>\n" + md_to_html(
        md_path.read_text(encoding="utf-8"))
    write(rel, page(f"OVP . {title}", body, active=active))


def build_foundations():
    parts = ["<h1>Foundations</h1>",
             "<p class='lead'>The rule sets every language, chart, and page "
             "builds on. Numbered, permanent, cited where perception research "
             "backs a law.</p>"]
    files = sorted((ROOT / "catalogue" / "foundations").glob("FN-*.md"))
    toc = []
    for f in files:
        anchor = f.stem.lower()
        first = f.read_text(encoding="utf-8").split("\n")[0].lstrip("# ")
        toc.append(f'<a href="#{anchor}">{esc(first)}</a>')
    parts.append("<div class='tocbox'>" + " &nbsp;|&nbsp; ".join(toc) + "</div>")
    for f in files:
        anchor = f.stem.lower()
        parts.append(f"<div id='{anchor}'></div><hr>")
        parts.append(md_to_html(f.read_text(encoding="utf-8")))
    write("foundations.html", page("OVP . Foundations", "\n".join(parts),
                                   active="foundations.html"))


def build_languages(toks, specs):
    hero_charts = [c for c in ("CH-RNK-01", "CH-TIM-01", "CH-PTW-01",
                               "CH-DEV-04", "CH-DST-07", "CH-TAB-01")
                   if (ROOT / "specs" / f"{c}.json").exists()]
    comps = {p.stem: load(p)
             for p in sorted((ROOT / "components").glob("CP-*.json"))}
    heroes = {t["code"]: language_hero(t, comps) for t in toks}
    for code, svg in heroes.items():
        write(f"assets/heroes/{code}.svg", svg)
    write("assets/showcase.svg", showcase_svg(heroes))
    write("assets/charts-reel.svg", chart_showcase_svg())
    cards = []
    for t in toks:
        sw = "".join(f'<i style="background:{t["palette"][k]}"></i>'
                     for k in ("background", "ink", "body", "primary",
                               "muted", "positive", "negative"))
        laws = ", ".join(t["philosophy"]["laws"][:3])
        cards.append(f"""<a class="card findable" href="{t['code']}.html">
<div class="kicker">{t['code']} . {esc(t['philosophy']['civilization'])}</div>
<h3>{esc(t['name'])}</h3>
<p class="motto">{esc(t['philosophy']['motto'])}</p>
<div class="swatches">{sw}</div>
<div class="thumb">{heroes[t['code']]}</div>
<p>{esc(t['philosophy']['principle'])}. {esc(laws)}.</p>
<p style="margin-top:8px"><span class="tag">{t['status']}</span>
{"".join(f'<span class="tag">{esc(o)}</span>' for o in t['occasions'][:2])}</p>
</a>""")
    body = (
        "<h1>Design languages</h1>"
        "<p class='lead'>A design language is a complete visual identity: a "
        "palette bound to the role contract, two fonts, chrome rules, and a "
        "philosophy that explains why. Codes are permanent; names are "
        "revisable. Candidate languages promote to adopted after two real "
        "deliverables ship in them.</p>"
        "<input class='search' placeholder='Filter by name, civilization, "
        "principle, occasion...' oninput='filterCards(this.value)'>"
        "<div class='grid g2'>" + "\n".join(cards) + "</div>")
    write("languages/index.html", page("OVP . Design languages", body, depth=1,
                                       active="languages/index.html"))

    for t in toks:
        ph = t["philosophy"]
        pal_rows = "".join(
            f"<tr><td>{k}</td><td><i style='background:{v}'></i>"
            f"<code>{v}</code></td></tr>"
            for k, v in t["palette"].items())
        laws = "".join(f"<li>{esc(law)}</li>" for law in ph["laws"])
        related = ", ".join(esc(r) for r in ph.get("related", []))
        occasions = "".join(f'<span class="tag">{esc(o)}</span>'
                            for o in t["occasions"])
        chrome = ("kicker bar and CAPS eyebrow" if t["chrome"]["eyebrow"]
                  else "no kicker, no eyebrow; the title stands alone")
        figs = []
        for c in hero_charts:
            spec = load(ROOT / "specs" / f"{c}.json")
            figs.append(f"<figure><figcaption>{c} {esc(spec['name'])}"
                        f"</figcaption>{svg_of(c, t['code'])}</figure>")
        blocks = B.build_all()
        payloads = {"dl-md": blocks[f"blocks/skill/{t['code']}.md"],
                    "dl-json": json.dumps(t, indent=2)}
        body = f"""<div class="crumb"><a href="index.html">Languages</a> /
{t['code']}</div>
<div class="kicker">{t['code']} . {esc(ph['civilization'])} .
{t['status']}</div>
<h1>{esc(t['name'])}</h1>
<p class="motto">{esc(ph['motto'])}</p>
<p class="lead">{esc(ph['principle'])}.
{f"Related traditions: {related}." if related else ""}</p>
<div class="copybar">
<button class="copy" onclick="copyPayload(this,'dl-md')">Copy token block
(markdown)</button>
<button class="copy alt" onclick="copyPayload(this,'dl-json')">Copy token
JSON</button>
</div>
<div class="thumb" style="margin-bottom:24px">{heroes[t['code']]}</div>
<div class="two">
<div>
<h2>Design laws</h2><ul>{laws}</ul>
<h2>Constitution</h2>
<p>The deterministic communication contract: these values are
schema-enforced and validator-checked, not styling suggestions.</p>
<table>{''.join(f"<tr><td>{k.replace('_', ' ')}</td><td>{v}</td></tr>"
                for k, v in t['constitution'].items())}</table>
<h2>Occasions</h2><p>{occasions}</p>
<h2>Chrome</h2><p>{chrome}.</p>
</div>
<div>
<h2>Palette</h2>
<table class="palette"><tr><th>Role</th><th>Hex</th></tr>{pal_rows}</table>
<h2>Fonts</h2>
<p>Display: {esc(t['fonts']['display']['family'])}, weight
{t['fonts']['display']['weight']}.<br>
Body: {esc(t['fonts']['body']['family'])}, weight
{t['fonts']['body']['weight']}.</p>
</div>
</div>
<h2>The language in use</h2>
<p>Six chart objects rendered from the same golden data as every other
language. Only the token file differs.</p>
<div class="grid g2">{''.join(figs)}</div>
{payload_script(payloads)}"""
        write(f"languages/{t['code']}.html",
              page(f"OVP . {t['code']} {t['name']}", body, depth=1,
                   active="languages/index.html"))


def build_charts(toks, specs):
    blocks = B.build_all()
    by_family = {}
    for s in specs:
        by_family.setdefault(s["meta"]["relations"]["family"], []).append(s)

    sections = []
    for fam in FAMILY_NAMES:
        if fam not in by_family:
            continue
        fname, fdesc = FAMILY_NAMES[fam]
        cards = []
        for s in sorted(by_family[fam], key=lambda x: x["code"]):
            intents = "".join(f'<span class="tag">{i}</span>'
                              for i in s["meta"]["intent"])
            cards.append(f"""<a class="card findable" href="{s['code']}.html">
<div class="thumb">{svg_of(s['code'], 'DL-02')}</div>
<div class="kicker">{s['code']}</div>
<h3>{esc(s['name'])}</h3>
<p>{esc(s['meta']['form'])}</p>
<p style="margin-top:8px">{intents}</p></a>""")
        sections.append(f"<h2>{fname} <small style='color:var(--body);"
                        f"font-weight:400;font-size:14px'>. {fdesc}</small></h2>"
                        f"<div class='grid g3'>{''.join(cards)}</div>")
    body = (
        "<h1>Chart objects</h1>"
        "<p class='lead'>Built entries only; the full 74-entry map with "
        "planned and excluded types is in the <a href='../taxonomy.html'>"
        "taxonomy</a>. Choose the family by what the message is, the entry "
        "by the data shape, then check the entry's own \"see instead\" "
        "exits before committing.</p>"
        "<input class='search' placeholder='Filter by code, name, intent, "
        "form...' oninput='filterCards(this.value)'>"
        + "\n".join(sections))
    write("charts/index.html", page("OVP . Chart objects", body, depth=1,
                                    active="charts/index.html"))

    for s in specs:
        code = s["code"]
        data = load(ROOT / "golden" / code / "data.json")
        rel = s["meta"]["relations"]
        views, btns = [], []
        for j, t in enumerate(toks):
            shown = " style='display:block'" if j == 0 else " style='display:none'"
            views.append(f"<div class='dlview' id='v-{t['code']}'{shown}>"
                         f"<figure><figcaption>{t['code']} {esc(t['name'])}"
                         f"</figcaption>{svg_of(code, t['code'])}</figure></div>")
            btns.append(f"<button class='dlbtn{' on' if j == 0 else ''}' "
                        f"data-dl='{t['code']}' onclick=\"showDL('{t['code']}')\">"
                        f"{t['code']} {esc(t['name'])}</button>")
        payloads = {"skill": blocks[f"blocks/skill/{code}.md"],
                    "data": json.dumps(data, indent=2),
                    "spec": json.dumps(s, indent=2)}
        for t in toks:
            payloads[f"ds-{t['code']}"] = \
                blocks[f"blocks/design-system/{code}_{t['code']}.md"]

        def lis(items):
            return "".join(f"<li>{esc(i)}</li>" for i in items)

        see = "".join(f"<li>{esc(si['when'])}: <a href='{si['use']}.html'>"
                      f"{si['use']}</a></li>" for si in rel.get("see_instead", []))
        alts = "".join(f"<li>{esc(a)}</li>" for a in rel.get("alternatives", []))
        shape = "".join(f"<tr><td>{esc(k)}</td><td>{esc(v)}</td></tr>"
                        for k, v in s["data_shape"].items())
        intents = "".join(f'<span class="tag">{i}</span>'
                          for i in s["meta"]["intent"])
        body = f"""<div class="crumb"><a href="index.html">Charts</a> /
{code}</div>
<div class="kicker">{code} . family {rel['family']}</div>
<h1>{esc(s['name'])}</h1>
<p class="lead">{esc(s['meta']['form'])}. Needs:
{esc(s['meta']['data_required'])}.</p>
<p>{intents}</p>
<div class="copybar">
<button class="copy" onclick="copyDS(this)">Copy design-system block
(current language)</button>
<button class="copy alt" onclick="copyPayload(this,'skill')">Copy skill
block (themeable)</button>
<button class="copy alt" onclick="copyPayload(this,'data')">Copy sample
data</button>
<button class="copy alt" onclick="copyPayload(this,'spec')">Copy spec
JSON</button>
</div>
<div class="dlbar">{''.join(btns)}</div>
{''.join(views)}
<div class="two">
<div>
<h2>Use when</h2><ul>{lis(s['use_when'])}</ul>
<h2>Do not use when</h2><ul>{lis(s['not_when'])}</ul>
{f"<h2>See instead</h2><ul>{see}</ul>" if see else ""}
{f"<h2>Alternatives</h2><ul>{alts}</ul>" if alts else ""}
<h2>Rules</h2><ul>{lis(s['rules'])}</ul>
<h2>Never do this</h2><ul>{lis(s['anti_patterns'])}</ul>
<h2>QA before delivering</h2><ul>{lis(s['qa'])}</ul>
</div>
<div>
<h2>Data shape</h2>
<table>{shape}</table>
<details><summary>Sample data (golden)</summary>
<pre><code>{esc(json.dumps(data, indent=2))}</code></pre></details>
</div>
</div>
{payload_script(payloads)}"""
        write(f"charts/{code}.html",
              page(f"OVP . {code} {s['name']}", body, depth=1,
                   active="charts/index.html"))


def build_patterns(pats, specs):
    codes = {s["code"] for s in specs}
    cards = []
    for p in pats:
        show = "".join(
            f"<a class='tag' style='text-decoration:none' "
            f"href='charts/{c}.html'>{c}</a>" if c in codes
            else f"<span class='tag'>{c}</span>"
            for c in p["show_with"])
        avoid = "".join(f"<li>{esc(a)}</li>" for a in p["avoid"])
        cards.append(f"""<div class="card findable">
<div class="kicker">{p['code']}</div>
<h3>{esc(p['name'])}</h3>
<p><b>Recognize:</b> {esc(p['recognition'])}</p>
<p><b>It means:</b> {esc(p['meaning'])}</p>
<p><b>Business reading:</b> {esc(p['business_reading'])}</p>
<p style="margin:8px 0"><b>Show with:</b> {show}</p>
<p><b>Avoid:</b></p><ul>{avoid}</ul>
</div>""")
    body = ("<h1>Analytical patterns</h1>"
            "<p class='lead'>The layer above charts. First recognize what the "
            "data shows, then read what it means, then take the recommended "
            "chart codes into the language chosen via the decider.</p>"
            "<div class='grid g2'>" + "\n".join(cards) + "</div>")
    write("patterns.html", page("OVP . Analytical patterns", body,
                                active="patterns.html"))


def build_decider(toks):
    engine = load(ROOT / "decision" / "engine.json")
    names = {t["code"]: t["name"] for t in toks}
    rows = []
    for i, r in enumerate(engine["rules"], 1):
        cond = ", ".join(f"{k} = {v}" for k, v in r["if"].items())
        rows.append(f"<tr><td>{i}</td><td>{esc(cond)}</td>"
                    f"<td><a href='languages/{r['then']}.html'>{r['then']} "
                    f"{esc(names[r['then']])}</a></td><td>{esc(r['why'])}</td></tr>")
    fb = engine["fallback"]
    vocab = "".join(f"<p><b>{k}:</b> {', '.join(v)}</p>"
                    for k, v in engine["vocabulary"].items())
    body = f"""<h1>Language decider</h1>
<p class="lead">Resolve the design language first: audience, purpose,
medium. Rules match top-down; every condition must hold; the first full
match wins. Then pick the chart via patterns or the chart index.</p>
<table><tr><th>#</th><th>If</th><th>Then</th><th>Why</th></tr>
{''.join(rows)}</table>
<p>No match: <a href="languages/{fb['then']}.html">{fb['then']}
{esc(names[fb['then']])}</a> ({esc(fb['why'])}).</p>
<h2>Controlled vocabulary</h2>
{vocab}
<p>Chart specs draw <code>meta.intent</code> from the intent list; the
validator rejects anything off-vocabulary.</p>"""
    write("decider.html", page("OVP . Language decider", body,
                               active="decider.html"))


def build_components(comps):
    blocks = B.build_all()
    payloads = {}
    cards = []
    for cp in comps:
        payloads[cp["code"]] = blocks[f"blocks/skill/{cp['code']}.md"]
        figs = "".join(
            f"<figure style='margin-bottom:8px'><figcaption>{dl}</figcaption>"
            f"{svg_of(cp['code'], dl)}</figure>"
            for dl in ("DL-02", "DL-03", "DL-08"))
        rules = "".join(f"<li>{esc(r)}</li>" for r in cp["rules"])
        cards.append(f"""<div class="card findable">
<div class="kicker">{cp['code']}</div>
<h3>{esc(cp['name'])}</h3>
<p>{esc(cp['purpose'])}</p>
{figs}
<ul>{rules}</ul>
<div class="copybar"><button class="copy"
onclick="copyPayload(this,'{cp['code']}')">Copy skill block</button></div>
</div>""")
    body = ("<h1>Components</h1>"
            "<p class='lead'>The furniture around charts: titles, sources, "
            "KPI cards, status chips, callouts. Same role contract, same "
            "determinism, composable into recipes.</p>"
            "<div class='grid g2'>" + "\n".join(cards) + "</div>"
            + payload_script(payloads))
    write("components.html", page("OVP . Components", body,
                                  active="components.html"))


def build_recipes(recs):
    parts = ["<h1>Recipes</h1>",
             "<p class='lead'>A recipe pins everything: language, charts, "
             "components, exact positions on the 1280x720 canvas. A recurring "
             "deliverable references a recipe code and renders identically "
             "forever.</p>"]
    for rc in recs:
        parts.append(f"<h2>{rc['code']} . {esc(rc['name'])} "
                     f"<small style='color:var(--body);font-weight:400'>"
                     f"({rc['dl']})</small></h2>")
        parts.append(f"<figure>{svg_of(rc['code'])}</figure>")
    write("recipes.html", page("OVP . Recipes", "\n".join(parts),
                               active="recipes.html"))


def build_questions(specs):
    bqs = [load(p) for p in sorted((ROOT / "questions").glob("BQ-*.json"))]
    nrs = [load(p) for p in sorted((ROOT / "narratives").glob("NR-*.json"))]
    names = {s["code"]: s["name"] for s in specs}
    nr_names = {n["code"]: n["name"] for n in nrs}
    cards = []
    for b in bqs:
        charts = "".join(f"<a class='tag' style='text-decoration:none' "
                         f"href='charts/{c}.html'>{c} {esc(names.get(c, ''))}</a>"
                         for c in b["charts"])
        pats = ", ".join(b["patterns"]) if b["patterns"] else "none"
        cards.append(f"""<div class="card findable">
<div class="kicker">{b['code']}</div>
<h3>{esc(b['question'])}</h3>
<p><b>You will observe:</b> {esc('; '.join(b['observations']))}</p>
<p><b>Patterns:</b> {esc(pats)} &nbsp; <b>Tell it as:</b>
{b['narrative']} {esc(nr_names[b['narrative']])}</p>
<p style="margin-top:8px">{charts}</p>
</div>""")
    skels = []
    for n in nrs:
        secs = " &rarr; ".join(s["role"] for s in n["sections"])
        rows = "".join(f"<tr><td>{s['role']}</td><td>{esc(s['guidance'])}</td></tr>"
                       for s in n["sections"])
        skels.append(f"""<div class="card findable">
<div class="kicker">{n['code']} . {n['decision_style']}</div>
<h3>{esc(n['name'])}</h3>
<p><b>{secs}</b></p>
<table>{rows}</table>
</div>""")
    body = ("<h1>Business questions</h1>"
            "<p class='lead'>The top of the resolution chain. Match the "
            "question being asked, confirm the observations in the data, "
            "then take the pattern, the charts, and the narrative skeleton. "
            "The language comes from the <a href='decider.html'>decider</a>."
            "</p>"
            "<input class='search' placeholder='Filter questions...' "
            "oninput='filterCards(this.value)'>"
            "<div class='grid g2'>" + "\n".join(cards) + "</div>"
            "<h2>Narrative skeletons</h2>"
            "<p>How the finding is told, ordered by the language's "
            "decision_style. Guidance per section:</p>"
            "<div class='grid g2'>" + "\n".join(skels) + "</div>")
    write("questions.html", page("OVP . Business questions", body,
                                 active="questions.html"))


def build_implement(toks, specs):
    schemas = sorted(p.name for p in (ROOT / "schema").glob("*.json"))
    schema_rows = "".join(f"<tr><td><a href='schemas/{n}'>{n}</a></td>"
                          f"<td>{n.split('.')[0].upper()} objects</td></tr>"
                          for n in schemas)
    body = f"""<h1>Implement OVP</h1>
<p class="lead">Everything needed to build a conformant parser,
renderer, validator, or composer, without asking the authors anything.
The reference implementation lives in <code>tools/</code> in the
repository; this page is the contract it implements.</p>

<h2>Conformance levels</h2>
<table>
<tr><th>Level</th><th>Name</th><th>You can claim it when</th></tr>
<tr><td>1</td><td>Parser</td><td>you read specs and tokens and validate
them against the published schemas</td></tr>
<tr><td>2</td><td>Renderer</td><td>you reproduce the golden renders for
at least one chart family from spec + tokens + data</td></tr>
<tr><td>3</td><td>Presenter</td><td>you compose recipes (language +
charts + components) on the slide canvas</td></tr>
<tr><td>4</td><td>Advisor</td><td>you use the machine metadata to pick
the right object for a message</td></tr>
<tr><td>5</td><td>Full</td><td>you deterministically reproduce every
golden across all built objects</td></tr>
</table>

<h2>The determinism contract</h2>
<ul>
<li>Same spec + same tokens + same data = the same output. For SVG,
byte-identical; for container formats with volatile envelopes (PPTX zip
timestamps), member-identical.</li>
<li>Specs carry exact px values and color ROLES. Resolve a role chain
like <code>benchmark -&gt; muted</code> to the first role the palette
defines.</li>
<li>Merge a spec's <code>overrides[DL-xx]</code> block over the spec
before rendering in that language.</li>
<li>Float formatting: at most 2 decimals, trailing zeros stripped,
never <code>-0</code>.</li>
<li>Nice-tick algorithm (normative, FN-05): raw = max / target_ticks;
mag = 10^floor(log10(raw)); step = first of nice_steps x mag &gt;= raw;
top = ceil(max / step) x step.</li>
<li>No randomness, no timestamps, no environment-dependent values,
ever. Deterministic layout algorithms are part of the spec (squarified
treemap, first-free-lane beeswarm packing).</li>
</ul>

<h2>What you need</h2>
<table>
<tr><th>File</th><th>Validates</th></tr>
{schema_rows}
<tr><td><a href='schemas/engine.json'>engine.json</a></td>
<td>decision rules + the controlled vocabularies</td></tr>
<tr><td><a href='REGISTRY.json'>REGISTRY.json</a></td>
<td>the machine index of every object</td></tr>
</table>
<p>Golden renders and their input data live under <code>golden/</code>
in the repository: one folder per object, <code>data.json</code> plus
one render per design language. They are the conformance test suite:
re-render and compare bytes.</p>

<h2>Self-test</h2>
<pre><code>for each golden folder:
    output = render(spec, tokens[dl], data)
    assert output == stored_golden_bytes   # svg: byte-identical</code></pre>
<p>The reference gate (<code>tools/validate.py</code>) also checks
schema validity, hex discipline (#RRGGBB uppercase only, in tokens
only), WCAG AA contrast for ink and body on background, and per-chart
data sanity (waterfalls reconcile, cumulative curves never decrease,
rank columns are permutations, five-number summaries are ordered).</p>"""
    write("implement.html", page("OVP . Implement", body,
                                 active="implement.html"))


def build_ai(toks, specs):
    reg = json.loads(B.build_all()["REGISTRY.json"])
    sample = next(o for o in reg["objects"] if o["type"] == "chart")
    engine = load(ROOT / "decision" / "engine.json")
    vocab = "".join(f"<p><b>{k}:</b> {', '.join(v)}</p>"
                    for k, v in engine["vocabulary"].items())
    body = f"""<h1>OVP for AI agents</h1>
<p class="lead">OVP is written for machine consumption first: controlled
vocabularies, machine metadata on every object, a generated registry,
and copy-paste blocks. An agent that follows this page produces
deterministic, honest visuals instead of plausible ones.</p>

<h2>The instruction grammar</h2>
<pre><code>Render CH-TIM-02 in DL-03 with data.json</code></pre>
<p>Object code + design language + data. Nothing else is needed,
because the spec and the token file determine everything else.</p>

<h2>Resolution order</h2>
<ol>
<li><b><a href="questions.html">Questions</a></b>: match the business
question; confirm its observations in the data.</li>
<li><b><a href="decider.html">Decider</a></b>: audience + purpose +
medium resolve the design language; its constitution sets the
communication contract.</li>
<li><b><a href="patterns.html">Patterns</a></b>: what you found in the
data maps to chart codes.</li>
<li><b><a href="charts/index.html">Charts</a></b>: disambiguate by
message intent; honor every <code>see_instead</code> exit before
committing.</li>
<li><b>Narrative</b>: structure the telling with the question's NR
skeleton, ordered by the language's decision_style.</li>
<li><b>Render</b> the code in the language: exact px, exact hex, no
adjectives, then run the object's QA checklist.</li>
</ol>

<h2>The registry</h2>
<p>Resolve objects through <a href="REGISTRY.json">REGISTRY.json</a>
rather than walking the repository. One entry per object:</p>
<pre><code>{esc(json.dumps(sample, indent=2))}</code></pre>

<h2>Controlled vocabularies</h2>
{vocab}
<p>Chart specs draw <code>meta.intent</code> from the intent list; the
validator rejects anything off-vocabulary.</p>

<h2>The runtime contract</h2>
<p>Three products, three audiences: the <b>handbook</b> (this site) is
for humans; the <b>registry</b> is for machine lookup; the
<b>runtime</b> is what an agent loads to execute one request, and it is
deliberately tiny:</p>
<pre><code>request
  -> registry lookup (one entry)
  -> one DL token block
  -> matched chart block(s), within charts_per_page
  -> the narrative skeleton the question names
  -> render</code></pre>
<p>Never load the handbook into an agent context: the copy blocks are
self-contained on purpose, and token efficiency is a protocol
objective (PROTOCOL 2.1). Registry chart entries carry the reverse
edges (<code>answers</code>, <code>recommended_by</code>,
<code>used_in</code>) so resolution is one lookup, not a crawl.</p>

<h2>Copy blocks: two flavors</h2>
<p><b>Design-system blocks</b> (per chart per language) resolve every
color to hex: paste one into a CLAUDE.md or system prompt and the agent
needs nothing else. <b>Skill blocks</b> (per chart) stay role-based:
paste next to one language token block and re-theme by swapping that
block. Both are on every <a href="charts/index.html">chart page</a>,
generated from the canonical specs and drift-gated.</p>"""
    write("ai.html", page("OVP . AI", body, active="ai.html"))


def llms_txt(toks, specs):
    fams = {}
    for s in specs:
        fams.setdefault(s["meta"]["relations"]["family"], []).append(s["code"])
    fam_lines = "\n".join(f"- {FAMILY_NAMES[f][0]} ({f}): {', '.join(sorted(cs))}"
                          for f, cs in fams.items() if f in FAMILY_NAMES)
    dl_lines = "\n".join(f"- {t['code']} {t['name']}: "
                         f"{t['philosophy']['principle']}; speaks on "
                         f"{t['occasions'][0]}" for t in toks)
    return f"""# Open Visualization Protocol (OVP)

> Deterministic, AI-native visualization skills: {len(specs)} chart
> objects x {len(toks)} design languages. Same spec + same tokens +
> same data = the same pixels, from any agent or renderer.
> Copy-paste blocks give an LLM exact geometry and colors: no
> adjectives, no improvisation, no lying axes.

## Machine entry points (load these, not the handbook)

- REGISTRY.json: every object with id, status, relations, reverse
  edges (answers, recommended_by, used_in). Resolve here first.
- schemas/: JSON Schemas for every object type and every chart's data.
- blocks (in the repository): the runtime payloads. Two flavors:
  blocks/design-system/CH-xxx_DL-yy.md (hex-resolved, zero deps) and
  blocks/skill/CH-xxx.md + blocks/skill/DL-yy.md (role-based,
  themeable).

## Resolution order for agents

1. Match the business question (BQ objects, questions.html).
2. Resolve the design language from audience/purpose/medium
   (decider.html); its constitution sets density, annotation,
   highlight, and narrative policy.
3. Map findings to patterns (patterns.html), disambiguate by intent
   (charts/), honor every see_instead exit.
4. Structure the telling with the narrative skeleton (NR objects).
5. Render: `Render CH-TIM-02 in DL-03 with data.json`. Exact px,
   exact hex. Run the object's QA checklist.

## Design languages

{dl_lines}

## Chart objects by family

{fam_lines}

## Pages

- index.html: principles and the six-door map
- protocol.html: the normative reference (v1.0, frozen as RFC-0001)
- implement.html: build a conformant renderer without asking anyone
- ai.html: the runtime contract and copy blocks
"""


def main():
    toks = [load(p) for p in sorted((ROOT / "tokens").glob("DL-*.json"))]
    specs = [load(p) for p in sorted((ROOT / "specs").glob("CH-*.json"))]
    pats = [load(p) for p in sorted((ROOT / "patterns").glob("PT-*.json"))]
    comps = [load(p) for p in sorted((ROOT / "components").glob("CP-*.json"))]
    recs = [load(p) for p in sorted((ROOT / "recipes").glob("RC-*.json"))]

    (OUT / ".nojekyll").parent.mkdir(parents=True, exist_ok=True)
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    write("llms.txt", llms_txt(toks, specs))

    build_index(toks, specs, pats, comps, recs)
    build_md_page("protocol.html", "The protocol", ROOT / "PROTOCOL.md",
                  "protocol.html")
    build_md_page("taxonomy.html", "Taxonomy", ROOT / "TAXONOMY.md",
                  "taxonomy.html")
    build_md_page("manifesto.html", "Manifesto", ROOT / "MANIFESTO.md",
                  "index.html")
    build_md_page("contributing.html", "Contributing", ROOT / "CONTRIBUTING.md",
                  "index.html")
    build_questions(specs)
    build_implement(toks, specs)
    build_ai(toks, specs)
    for p in sorted((ROOT / "schema").glob("*.json")):
        write(f"schemas/{p.name}", p.read_text(encoding="utf-8"))
    write("schemas/engine.json",
          (ROOT / "decision" / "engine.json").read_text(encoding="utf-8"))
    write("REGISTRY.json", B.build_all()["REGISTRY.json"])
    build_foundations()
    build_languages(toks, specs)
    build_charts(toks, specs)
    build_patterns(pats, specs)
    build_decider(toks)
    build_components(comps)
    build_recipes(recs)
    print(f"\nsite: {OUT / 'index.html'}")


if __name__ == "__main__":
    main()
