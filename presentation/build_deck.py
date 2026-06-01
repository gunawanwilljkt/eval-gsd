#!/usr/bin/env python3
"""
GSD presentation generator.

One content source -> three self-contained HTML decks that differ ONLY by palette:
  - gsd-presentation-dark.html
  - gsd-presentation-light.html
  - gsd-presentation-print.html   (no filled backgrounds, ink-economical, page-break per slide)

Design constraints (locked):
  * Fixed 1280x720 canvas, scaled to viewport on screen, one slide per page in print.
  * Flow layout inside each slide -> no text-on-text overlap by construction.
  * overflow:hidden on the slide clips any residual spill; the fit-check sweep
    (scrollHeight > clientHeight) is the deterministic "this slide is crowded" gate.
  * Inline CSS/JS, system font stack -> works offline and prints correctly.
"""

import os

# --------------------------------------------------------------------------------------
# PALETTES — the ONLY thing that differs between the three files.
# --------------------------------------------------------------------------------------
PALETTES = {
    "dark": {
        "--bg":          "#0A0C12",
        "--page-grad":   "radial-gradient(1200px 700px at 12% -10%, rgba(124,108,255,.18), transparent 55%), radial-gradient(1000px 700px at 110% 120%, rgba(45,212,191,.12), transparent 55%), #0A0C12",
        "--text":        "#EAEEF7",
        "--muted":       "#9AA4BA",
        "--faint":       "#69728A",
        "--border":      "#242C3E",
        "--surface":     "#12172110",   # placeholder, overwritten below
        "--surface-bg":  "rgba(255,255,255,.025)",
        "--surface2-bg": "rgba(255,255,255,.05)",
        "--accent":      "#8B7BFF",
        "--accent2":     "#2DD4BF",
        "--accent-soft": "rgba(139,123,255,.16)",
        "--on-accent":   "#0A0C12",
        "--grad":        "linear-gradient(120deg,#8B7BFF 0%,#5FE0C8 100%)",
        "--pbar":        "linear-gradient(120deg,#8B7BFF,#5FE0C8)",
        "--rail-grad":   "linear-gradient(180deg,#8B7BFF,#2DD4BF)",
        "--code-bg":     "#0C1018",
        "--code-text":   "#D7E0F0",
        "--code-border": "#202838",
        "--codedot":     "#202838",
        "--code-com":    "#5F6B85",
        "--code-str":    "#7FE0B6",
        "--code-kw":     "#9FB0FF",
        "--good":        "#46D98C",
        "--bad":         "#FF7A7A",
        "--warn":        "#F5C451",
        "--shadow":      "0 18px 50px rgba(0,0,0,.45)",
        "--chip-bg":     "rgba(139,123,255,.14)",
        "--chip-border": "rgba(139,123,255,.32)",
        "--chip-text":   "#CBC6FF",
        "--hero-border": "transparent",
        "--wordmark":    "#69728A",
        "--th-bg":       "rgba(255,255,255,.04)",
        "--row-alt":     "rgba(255,255,255,.018)",
    },
    "light": {
        "--bg":          "#EEF1F8",
        "--page-grad":   "radial-gradient(1100px 650px at 10% -12%, rgba(109,77,246,.10), transparent 55%), radial-gradient(900px 650px at 112% 118%, rgba(16,158,142,.09), transparent 55%), #EEF1F8",
        "--text":        "#161B26",
        "--muted":       "#566076",
        "--faint":       "#8A93A6",
        "--border":      "#DDE3EE",
        "--surface-bg":  "#FFFFFF",
        "--surface2-bg": "#F4F6FB",
        "--accent":      "#6D4DF6",
        "--accent2":     "#109E8E",
        "--accent-soft": "rgba(109,77,246,.09)",
        "--on-accent":   "#FFFFFF",
        "--grad":        "linear-gradient(120deg,#6D4DF6 0%,#10A99A 100%)",
        "--pbar":        "linear-gradient(120deg,#6D4DF6,#10A99A)",
        "--rail-grad":   "linear-gradient(180deg,#6D4DF6,#10A99A)",
        "--code-bg":     "#0E1320",
        "--code-text":   "#DCE4F2",
        "--code-border": "#0E1320",
        "--codedot":     "#0E1320",
        "--code-com":    "#7C879F",
        "--code-str":    "#7FE0B6",
        "--code-kw":     "#A9B6FF",
        "--good":        "#0E9F5B",
        "--bad":         "#D1453B",
        "--warn":        "#B7791F",
        "--shadow":      "0 14px 40px rgba(26,38,71,.12)",
        "--chip-bg":     "rgba(109,77,246,.08)",
        "--chip-border": "rgba(109,77,246,.28)",
        "--chip-text":   "#5436C9",
        "--hero-border": "transparent",
        "--wordmark":    "#9AA3B6",
        "--th-bg":       "#F4F6FB",
        "--row-alt":     "#F8FAFD",
    },
    "print": {
        "--bg":          "#FFFFFF",
        "--page-grad":   "#FFFFFF",
        "--text":        "#15181F",
        "--muted":       "#414956",
        "--faint":       "#6B7280",
        "--border":      "#C2C8D2",
        "--surface-bg":  "#FFFFFF",
        "--surface2-bg": "#FFFFFF",
        "--accent":      "#262A33",
        "--accent2":     "#3C4150",
        "--accent-soft": "transparent",
        "--on-accent":   "#15181F",
        "--grad":        "#2A2F3A",
        "--pbar":        "transparent",
        "--rail-grad":   "transparent",
        "--code-bg":     "#FFFFFF",
        "--code-text":   "#1B2230",
        "--code-border": "#C8CDD6",
        "--codedot":     "transparent",
        "--code-com":    "#7A8290",
        "--code-str":    "#1F6B45",
        "--code-kw":     "#3A3FA0",
        "--good":        "#1B7A45",
        "--bad":         "#B0322A",
        "--warn":        "#8A6A10",
        "--shadow":      "none",
        "--chip-bg":     "transparent",
        "--chip-border": "#9CA3AF",
        "--chip-text":   "#2A2F3A",
        "--hero-border": "#C2C8D2",
        "--wordmark":    "#8A93A6",
        "--th-bg":       "#FFFFFF",
        "--row-alt":     "#FFFFFF",
    },
}

# --------------------------------------------------------------------------------------
# CSS (identical across files; only :root vars are swapped)
# --------------------------------------------------------------------------------------
CSS = r"""
*{margin:0;padding:0;box-sizing:border-box}
html,body{height:100%}
body{
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  background:var(--bg);color:var(--text);
  -webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;
}
#stage{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:var(--page-grad);overflow:hidden}
#deck{width:1280px;height:720px;position:relative;transform-origin:center center}

/* ---- slide shell ---- */
.slide{
  position:absolute;inset:0;display:none;flex-direction:column;
  padding:50px 76px 44px;background:transparent;overflow:hidden;
}
.slide.active{display:flex}
.slide .rail{position:absolute;left:0;top:64px;bottom:60px;width:5px;border-radius:0 4px 4px 0;background:var(--rail-grad)}

/* ---- header ---- */
.wm{position:absolute;top:30px;right:76px;font-size:12px;letter-spacing:.22em;font-weight:700;color:var(--wordmark);text-transform:uppercase}
.kicker{display:flex;align-items:center;gap:10px;font-size:13.5px;font-weight:700;letter-spacing:.18em;text-transform:uppercase;
  background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.kicker .dot{width:7px;height:7px;border-radius:50%;background:var(--accent)}
.title{font-size:40px;line-height:1.08;font-weight:760;letter-spacing:-.018em;margin-top:14px;max-width:1040px}
.title.sm{font-size:33px}
.subtitle{font-size:18px;color:var(--muted);margin-top:12px;max-width:920px;line-height:1.5}

/* ---- body ---- */
.body{flex:1;min-height:0;display:flex;flex-direction:column;justify-content:center;margin-top:26px}
.body.top{justify-content:flex-start}
.lead{font-size:21px;line-height:1.55;color:var(--text);max-width:980px}
.lead .hl{color:var(--accent);font-weight:680}

/* ---- footer ---- */
.foot{position:absolute;left:76px;right:76px;bottom:26px;display:flex;align-items:center;justify-content:space-between;
  font-size:12.5px;color:var(--faint);letter-spacing:.04em}
.foot .sec{text-transform:uppercase;letter-spacing:.16em;font-weight:600}
.pbar{position:absolute;left:0;bottom:0;height:3px;background:var(--pbar);opacity:.9}

/* ---- cards grid ---- */
.grid{display:grid;gap:16px;width:100%}
.card{background:var(--surface-bg);border:1px solid var(--border);border-radius:14px;padding:20px 20px 18px;box-shadow:var(--shadow)}
.card .ico{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:19px;
  background:var(--accent-soft);border:1px solid var(--chip-border);margin-bottom:13px}
.card h3{font-size:17.5px;font-weight:680;letter-spacing:-.01em;margin-bottom:6px}
.card p{font-size:14.5px;line-height:1.5;color:var(--muted)}
.card .num{font-size:13px;font-weight:800;color:var(--accent);letter-spacing:.1em;margin-bottom:8px}

/* ---- columns ---- */
.cols{display:flex;gap:24px;width:100%;align-items:stretch}
.col{flex:1;min-width:0}
.col.s{flex:0 0 38%}

/* ---- bullets ---- */
.bul{list-style:none;display:flex;flex-direction:column;gap:13px}
.bul li{position:relative;padding-left:26px;font-size:17px;line-height:1.45;color:var(--text)}
.bul li::before{content:"";position:absolute;left:2px;top:9px;width:9px;height:9px;border-radius:3px;background:var(--grad)}
.bul li b{font-weight:680}
.bul li .d{color:var(--muted);font-weight:400}
.bul.sm li{font-size:15px;padding-left:22px}
.bul.sm li::before{top:7px;width:7px;height:7px}

/* ---- callout ---- */
.callout{border:1px solid var(--chip-border);background:var(--accent-soft);border-left:4px solid var(--accent);
  border-radius:10px;padding:16px 20px;font-size:16px;line-height:1.5;color:var(--text)}
.callout b{color:var(--accent)}

/* ---- chips / badges ---- */
.chip{display:inline-flex;align-items:center;gap:7px;font-size:13px;font-weight:600;padding:5px 12px;border-radius:999px;
  background:var(--chip-bg);border:1px solid var(--chip-border);color:var(--chip-text)}
.badge{display:inline-flex;align-items:center;gap:6px;font-size:12.5px;font-weight:700;padding:3px 10px;border-radius:6px;border:1px solid transparent}
.badge.code{color:var(--accent2);border-color:var(--accent2)}
.badge.good{color:var(--good);border-color:var(--good)}
.badge.bad{color:var(--bad);border-color:var(--bad)}
.badge.warn{color:var(--warn);border-color:var(--warn)}
.tags{display:flex;flex-wrap:wrap;gap:9px}

/* ---- code ---- */
.code{background:var(--code-bg);border:1px solid var(--code-border);border-radius:12px;overflow:hidden;box-shadow:var(--shadow)}
.code .bar{display:flex;align-items:center;gap:7px;padding:9px 14px;border-bottom:1px solid var(--code-border);font-size:12px;color:var(--code-com);letter-spacing:.04em}
.code .bar .d{width:9px;height:9px;border-radius:50%;background:var(--codedot)}
.code pre{padding:14px 16px;font-family:"SF Mono","JetBrains Mono","Fira Code",ui-monospace,Menlo,Consolas,monospace;
  font-size:13px;line-height:1.55;color:var(--code-text);white-space:pre;overflow:hidden}
.code .c{color:var(--code-com)}
.code .s{color:var(--code-str)}
.code .k{color:var(--code-kw);font-weight:600}

/* ---- table ---- */
table.t{width:100%;border-collapse:collapse;font-size:13.5px}
table.t th{text-align:left;font-weight:700;padding:9px 12px;background:var(--th-bg);color:var(--text);
  border-bottom:1px solid var(--border);font-size:12px;letter-spacing:.05em;text-transform:uppercase}
table.t td{padding:9px 12px;border-bottom:1px solid var(--border);color:var(--muted);vertical-align:top;line-height:1.4}
table.t td b{color:var(--text);font-weight:650}
table.t tr:nth-child(even) td{background:var(--row-alt)}
table.t code,.mono{font-family:"SF Mono","JetBrains Mono",ui-monospace,Menlo,Consolas,monospace;font-size:12.5px;color:var(--accent2)}
table.t.sm{font-size:12.5px}
table.t.sm th,table.t.sm td{padding:7px 10px}

/* ---- pipeline ---- */
.pipe{display:flex;align-items:stretch;gap:0;width:100%}
.pstep{flex:1;background:var(--surface-bg);border:1px solid var(--border);border-radius:12px;padding:15px 14px;text-align:center;box-shadow:var(--shadow)}
.pstep .pn{font-size:11px;font-weight:800;letter-spacing:.12em;color:var(--accent);text-transform:uppercase}
.pstep .pt{font-size:15.5px;font-weight:680;margin-top:6px}
.pstep .pd{font-size:12px;color:var(--muted);margin-top:5px;line-height:1.4}
.parrow{flex:0 0 30px;display:flex;align-items:center;justify-content:center;color:var(--accent2);font-size:20px;font-weight:700}

/* ---- stat row ---- */
.stats{display:flex;gap:20px;width:100%}
.stat{flex:1;background:var(--surface-bg);border:1px solid var(--border);border-radius:14px;padding:20px;box-shadow:var(--shadow)}
.stat .n{font-size:38px;font-weight:800;letter-spacing:-.02em;background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;line-height:1}
.stat .l{font-size:14px;color:var(--muted);margin-top:8px;line-height:1.4}

/* ---- flow / arrows for artifact chains ---- */
.chain{display:flex;flex-direction:column;gap:10px;width:100%}
.crow{display:flex;align-items:center;gap:14px}
.cnode{flex:0 0 188px;background:var(--surface-bg);border:1px solid var(--border);border-radius:10px;padding:11px 14px;box-shadow:var(--shadow)}
.cnode .cf{font-family:"SF Mono",ui-monospace,Menlo,monospace;font-size:13px;font-weight:650;color:var(--accent)}
.cnode .cl{font-size:11.5px;color:var(--muted);margin-top:3px}
.cdesc{flex:1;font-size:14px;color:var(--muted);line-height:1.45}
.cdesc b{color:var(--text);font-weight:620}

/* ---- title (hero) slide ---- */
.hero{align-items:flex-start;justify-content:center;padding:0 92px}
.hero .eyebrow{display:inline-flex;align-items:center;gap:10px;font-size:14px;font-weight:700;letter-spacing:.2em;text-transform:uppercase;
  color:var(--chip-text);border:1px solid var(--chip-border);background:var(--chip-bg);padding:8px 16px;border-radius:999px}
.hero h1{font-size:74px;line-height:1.0;font-weight:800;letter-spacing:-.03em;margin-top:26px}
.hero h1 .g{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero .tag{font-size:23px;color:var(--muted);margin-top:22px;max-width:820px;line-height:1.45}
.hero .meta{margin-top:40px;display:flex;gap:10px;flex-wrap:wrap}

/* ---- section divider ---- */
.divider{justify-content:center;padding:0 92px}
.divider .dnum{font-size:150px;font-weight:850;letter-spacing:-.04em;line-height:.8;
  background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent;opacity:.9}
.divider h2{font-size:48px;font-weight:780;letter-spacing:-.02em;margin-top:14px}
.divider p{font-size:19px;color:var(--muted);margin-top:14px;max-width:760px;line-height:1.5}
.divider .rail{display:none}

/* ---- misc ---- */
.navhint{position:fixed;right:16px;bottom:14px;font-size:11px;color:var(--faint);letter-spacing:.05em;z-index:50;opacity:.7}
.sb{color:var(--text);font-weight:650}
.acc{color:var(--accent);font-weight:650}
.good{color:var(--good)} .bad{color:var(--bad)} .warn{color:var(--warn)}
.mtop{margin-top:16px}.mtop-s{margin-top:10px}.mtop-l{margin-top:22px}
.center{text-align:center}

/* ============ PRINT ============ */
@media print{
  @page{size:1280px 720px;margin:0}
  html,body{background:#fff!important}
  #stage{position:static;display:block;overflow:visible;background:#fff}
  #deck{transform:none!important;width:1280px;height:auto}
  .slide{position:relative;display:flex!important;page-break-after:always;break-after:page;height:720px;border-bottom:none}
  .slide:last-child{page-break-after:auto}
  .navhint{display:none!important}
  /* gradient-clipped text leaves faint box hairlines in Chrome's PDF path -> render solid */
  .kicker,.dnum,.stat .n,.hero h1 .g{
    background:none!important;-webkit-text-fill-color:var(--accent)!important;color:var(--accent)!important;
  }
  .code .bar .d{display:none!important}   /* drop traffic-light dots for zero-fill print */
  *{-webkit-print-color-adjust:exact;print-color-adjust:exact}
}
"""

# --------------------------------------------------------------------------------------
# JS (identical across files)
# --------------------------------------------------------------------------------------
JS = r"""
(function(){
  var deck=document.getElementById('deck');
  var slides=[].slice.call(document.querySelectorAll('.slide'));
  var i=0;
  function fit(){
    var s=Math.min(window.innerWidth/1280, window.innerHeight/720);
    deck.style.transform='scale('+s+')';
  }
  function show(n){
    i=Math.max(0,Math.min(slides.length-1,n));
    slides.forEach(function(s,k){s.classList.toggle('active',k===i)});
    try{ if(history.replaceState) history.replaceState(null,'','#'+(i+1)); }catch(e){}
  }
  window.addEventListener('resize',fit);
  document.addEventListener('keydown',function(e){
    if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' ')  {show(i+1);e.preventDefault();}
    else if(e.key==='ArrowLeft'||e.key==='PageUp'){show(i-1);e.preventDefault();}
    else if(e.key==='Home'){show(0);}
    else if(e.key==='End'){show(slides.length-1);}
  });
  document.addEventListener('click',function(e){
    if(e.target.closest('a'))return;
    var x=e.clientX/window.innerWidth;
    if(x>0.62) show(i+1); else if(x<0.38) show(i-1);
  });
  // fit-check hook: returns slides whose content overflows the 720px canvas.
  // Measures the slide AND its inner .body (the latter catches centered overflow,
  // which a bare scrollHeight check on a justify-center container can hide).
  window.__overflow=function(){
    var prev=slides.map(function(s){return s.style.display});
    slides.forEach(function(s){s.style.display='flex'});
    var bad=[];
    slides.forEach(function(s,k){
      var b=s.querySelector('.body');
      var so=s.scrollHeight-s.clientHeight;
      var bo=b?(b.scrollHeight-b.clientHeight):0;
      var over=Math.max(so,bo);
      if(over>1) bad.push({i:k+1, slideOver:so, bodyOver:bo});
    });
    slides.forEach(function(s,k){s.style.display=prev[k]||''});
    return bad;
  };
  var start=parseInt((location.hash||'#1').slice(1),10);
  fit(); show(isNaN(start)?0:start-1);
})();
"""

# --------------------------------------------------------------------------------------
# Component helpers
# --------------------------------------------------------------------------------------
SLIDES = []
SECTIONS = []  # parallel list of section names for footer

def add(html, section="GSD"):
    SLIDES.append(html)
    SECTIONS.append(section)

def _foot(section, n, total):
    return (f'<div class="foot"><span class="sec">{section}</span>'
            f'<span class="num">GSD · {n:02d} / {total:02d}</span></div>'
            f'<div class="pbar" style="width:{n/total*100:.1f}%"></div>')

def slide(section, kicker, title, body, *, title_sm=False, body_top=True, subtitle=None):
    sub = f'<div class="subtitle">{subtitle}</div>' if subtitle else ''
    tcls = "title sm" if title_sm else "title"
    bcls = "body top" if body_top else "body"
    return (f'<section class="slide">'
            f'<span class="rail"></span><span class="wm">GSD</span>'
            f'<div class="kicker"><span class="dot"></span>{kicker}</div>'
            f'<div class="{tcls}">{title}</div>{sub}'
            f'<div class="{bcls}">{body}</div>'
            f'__FOOT__</section>')

def hero(eyebrow, title_html, tag, chips):
    chiprow = ''.join(f'<span class="chip">{c}</span>' for c in chips)
    return (f'<section class="slide hero">'
            f'<div class="eyebrow"><span class="dot" style="width:7px;height:7px;border-radius:50%;background:var(--accent);display:inline-block"></span>{eyebrow}</div>'
            f'<h1>{title_html}</h1><div class="tag">{tag}</div>'
            f'<div class="meta">{chiprow}</div>__FOOT__</section>')

def divider(num, title, desc):
    return (f'<section class="slide divider">'
            f'<div class="dnum">{num}</div><h2>{title}</h2><p>{desc}</p>__FOOT__</section>')

def cards(items, cols=3):
    cs = ''
    for it in items:
        ico = f'<div class="ico">{it["ico"]}</div>' if it.get("ico") else ''
        num = f'<div class="num">{it["num"]}</div>' if it.get("num") else ''
        cs += f'<div class="card">{ico}{num}<h3>{it["h"]}</h3><p>{it["p"]}</p></div>'
    return f'<div class="grid" style="grid-template-columns:repeat({cols},1fr)">{cs}</div>'

def bullets(items, small=False):
    cls = "bul sm" if small else "bul"
    lis = ''.join(f'<li>{x}</li>' for x in items)
    return f'<ul class="{cls}">{lis}</ul>'

def cols(*columns, sizes=None):
    out = ''
    for idx, c in enumerate(columns):
        cls = "col"
        if sizes and sizes[idx]:
            cls += " " + sizes[idx]
        out += f'<div class="{cls}">{c}</div>'
    return f'<div class="cols">{out}</div>'

def code(text, label="", highlight=True):
    bar = (f'<div class="bar"><span class="d"></span><span class="d"></span><span class="d"></span>'
           f'<span style="margin-left:6px">{label}</span></div>') if label else ''
    return f'<div class="code">{bar}<pre>{text}</pre></div>'

def table(headers, rows, small=False, mono_cols=None):
    cls = "t sm" if small else "t"
    th = ''.join(f'<th>{h}</th>' for h in headers)
    body = ''
    for r in rows:
        tds = ''.join(f'<td>{c}</td>' for c in r)
        body += f'<tr>{tds}</tr>'
    return f'<table class="{cls}"><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>'

def pipe(steps):
    parts = []
    for k, s in enumerate(steps):
        parts.append(f'<div class="pstep"><div class="pn">{s["n"]}</div>'
                     f'<div class="pt">{s["t"]}</div><div class="pd">{s["d"]}</div></div>')
        if k < len(steps) - 1:
            parts.append('<div class="parrow">→</div>')
    return f'<div class="pipe">{"".join(parts)}</div>'

def stats(items):
    out = ''.join(f'<div class="stat"><div class="n">{i["n"]}</div><div class="l">{i["l"]}</div></div>' for i in items)
    return f'<div class="stats">{out}</div>'

def callout(text):
    return f'<div class="callout">{text}</div>'

def chain(rows):
    out = ''
    for r in rows:
        out += (f'<div class="crow"><div class="cnode"><div class="cf">{r["f"]}</div>'
                f'<div class="cl">{r["l"]}</div></div><div class="cdesc">{r["d"]}</div></div>')
    return f'<div class="chain">{out}</div>'

# --------------------------------------------------------------------------------------
# CONTENT  (vertical-slice sample slides — replaced by full deck later)
# --------------------------------------------------------------------------------------
def build_sample():
    SLIDES.clear(); SECTIONS.clear()

    add(hero(
        "Get Shit Done · v1.2.0 + eval-first",
        'A spec-driven way to ship<br>real software with <span class="g">Claude Code</span>',
        "Phase-by-phase planning, locked eval contracts, and orchestrated agents — from idea to merged PR.",
        ["Eval-first contracts", "Work ledger", "Autonomous waves", "67 commands"]),
        "Title")

    add(divider("01", "What GSD is", "A mental model before the mechanics."), "Section")

    # text-heavy with cards
    add(slide("Foundations", "The core idea",
        "Software as a sequence of <span class='acc'>gated phases</span>",
        cards([
            {"ico":"◳","h":"Decompose","p":"Every project breaks into vertical phases — each a complete, testable slice of user value, not a horizontal layer."},
            {"ico":"✓","h":"Gate with evals","p":"Each phase locks an eval contract before code. Deterministic rows become the executor's hard gate."},
            {"ico":"⚡","h":"Orchestrate","p":"Specialized subagents — planner, executor, verifier — run in dependency-ordered parallel waves."},
            {"ico":"◆","h":"Persist","p":"A git-verified work ledger survives context resets, so any session resumes exactly where the last stopped."},
            {"ico":"↑","h":"Verify backward","p":"Verification works back from the phase goal — task done ≠ goal achieved."},
            {"ico":"⎘","h":"Audit","p":"Every decision, commit, and gate result is captured as a durable artifact in .planning/."},
        ], cols=3)), "Foundations")

    # wide table
    add(slide("Foundations", "Artifact ecosystem",
        "Everything lives in <span class='mono acc'>.planning/</span>",
        table(
            ["Artifact", "Holds", "Written by"],
            [["<b>PROJECT.md</b>","Vision, core value, validated vs active requirements","new-project"],
             ["<b>REQUIREMENTS.md</b>","REQ-01..N with acceptance criteria + traceability","new-project / discuss"],
             ["<b>ROADMAP.md</b>","Phases with goals, deps, success criteria","roadmapper"],
             ["<b>NN-CONTEXT.md</b>","Locked decisions, domain terms, code refs","discuss-phase"],
             ["<b>NN-EVAL-CONTRACT.md</b>","Code / Judge / Human rows + <code>locked_hash</code>","spec / discuss"],
             ["<b>NN-YY-PLAN.md</b>","Typed tasks with <code>acceptance_criteria</code>","planner"],
             ["<b>NN-VERIFICATION.md</b>","Must-haves verdict + eval verdict","verifier"],
             ["<b>LEDGER.md</b>","Task records, evidence hashes, escalations","execute (orchestrator)"]],
            small=True)), "Foundations")

    # pipeline diagram
    add(slide("Lifecycle", "End to end",
        "One project, repeated per phase",
        pipe([
            {"n":"Init","t":"new-project","d":"Questioning → requirements → roadmap"},
            {"n":"Per phase","t":"discuss","d":"Lock decisions in CONTEXT.md"},
            {"n":"Per phase","t":"plan","d":"Planner ↔ checker loop"},
            {"n":"Per phase","t":"execute","d":"Parallel waves, hard gates"},
            {"n":"Per phase","t":"verify","d":"Goal-backward + eval verdict"},
            {"n":"Close","t":"ship","d":"PR + review"},
        ]) + '<div class="mtop-l">' + callout("<b>Autonomous mode</b> loops discuss→plan→execute→verify across every remaining phase, escalating to you only on a blocked gate or a genuine decision.") + '</div>',
        ), "Lifecycle")

    # code + two column
    add(slide("Eval-first", "The contract",
        "Quality gates are locked <span class='acc'>before</span> a line is written",
        cols(
            code(
"<span class='c'># NN-EVAL-CONTRACT.md  (status: locked)</span>\n"
"<span class='c'>| id   | req    | behavior        | measure | sev  |</span>\n"
"| EC-1 | REQ-01 | add(2,3)==5     | Code    | gate |\n"
"| EC-2 | REQ-02 | sub(5,3)==2     | Code    | gate |\n"
"| EC-3 | REQ-05 | error UX clear  | Judge   | warn |\n"
"\n"
"<span class='k'>locked_hash:</span> <span class='s'>sha256(normalized_rows)</span>",
                label="eval-contract.md"),
            bullets([
                "<b>Code</b> <span class='d'>— deterministic CLI; the executor's hard gate (~80%).</span>",
                "<b>Judge</b> <span class='d'>— rubric-scored by a model for subjective quality.</span>",
                "<b>Human</b> <span class='d'>— UAT / felt experience, batched for you.</span>",
                "<b>Weakening guard</b> <span class='d'>— verify recomputes the hash; a softened gate is caught.</span>",
                "<b>Gaming guard</b> <span class='d'>— a Code row edited in its own commit is flagged.</span>",
            ], small=True),
            sizes=[None, None]
        )), "Eval-first")

    # artifact chain
    add(slide("Walkthrough", "Artifact chain",
        "How one phase flows, file by file",
        chain([
            {"f":"NN-CONTEXT.md","l":"discuss","d":"<b>Decision locked:</b> JWT in HTTP-only cookie; refresh rotates."},
            {"f":"NN-EVAL-CONTRACT.md","l":"spec","d":"<b>EC-1 (Code, gate):</b> POST /login returns 200 + Set-Cookie."},
            {"f":"NN-01-PLAN.md","l":"planner","d":"<b>T1 acceptance:</b> <span class='mono'>curl -si .../login | grep 'Set-Cookie: sid'</span>"},
            {"f":"NN-01-SUMMARY.md","l":"executor","d":"<b>Commit a1b2c3d</b> — T1 done, self-check PASSED."},
            {"f":"NN-VERIFICATION.md","l":"verifier","d":"<b>status: passed</b> — 1/1 must-have, eval verdict clean."},
        ])), "Walkthrough")

    return None

def compare(left_title, left_items, right_title, right_items):
    def block(t, items, bad):
        lis = ''.join(f'<li>{x}</li>' for x in items)
        clr = 'var(--bad)' if bad else 'var(--accent2)'
        return (f'<div class="card"><h3 style="color:{clr}">{t}</h3>'
                f'<ul class="bul sm" style="margin-top:12px">{lis}</ul></div>')
    return (f'<div class="grid" style="grid-template-columns:1fr 1fr">'
            f'{block(left_title,left_items,True)}{block(right_title,right_items,False)}</div>')

# --------------------------------------------------------------------------------------
# FULL DECK
# --------------------------------------------------------------------------------------
def build_deck():
    SLIDES.clear(); SECTIONS.clear()
    M = "mono"

    # ===================== OPEN =====================
    add(hero(
        "Get Shit Done · v1.2.0 + eval-first layer",
        'Ship real software with<br><span class="g">Claude Code</span>, phase by phase',
        "A spec-driven framework: locked eval contracts, orchestrated agents, and a git-verified work ledger — from a raw idea to a merged PR.",
        ["Eval-first contracts", "Work ledger", "Autonomous waves", "67 commands"]),
        "Title")

    add(slide("Agenda", "What this deck covers",
        "Four ideas, then two builds end to end",
        cards([
            {"num":"01","h":"What GSD is","p":"The mental model — gated phases, agents, and the artifacts that hold project truth."},
            {"num":"02","h":"How it works","p":"The lifecycle: new-project → discuss → plan → execute → verify → ship."},
            {"num":"03","h":"Key capabilities","p":"Eval-first, MVP/SPIDR, TDD, quality gates, AI phases, mobile scaffolds."},
            {"num":"04","h":"How to use it","p":"The command surface and the everyday loop you actually type."},
            {"num":"05","h":"Example · SaaS","p":"“TaskFlow” team app — one phase walked file by file."},
            {"num":"06","h":"Example · Payments","p":"“PayLink” gateway — mobile app + backend + admin dashboard."},
        ], cols=3)), "Agenda")

    # ===================== PART 1 — WHAT GSD IS =====================
    add(divider("01", "What GSD is", "A mental model before the mechanics."), "What GSD is")

    add(slide("The problem", "Why structure beats vibes",
        "AI writes code fast — and drifts fast",
        compare(
            "Unstructured AI coding",
            ["Scope creeps mid-session; the goal quietly moves",
             "“Looks right” passes for done — no objective proof",
             "Context runs out and the thread loses the plot",
             "No audit trail: why was this built this way?"],
            "GSD’s answer",
            ["Phases lock scope; gray areas resolved up front",
             "A <b>locked eval contract</b> proves done, deterministically",
             "A <b>work ledger</b> survives resets — resume exactly where you stopped",
             "Every decision &amp; gate is a durable artifact in <span class='mono'>.planning/</span>"])),
        "What GSD is")

    add(slide("Definition", "In one sentence",
        "GSD turns an idea into shipped code through <span class='acc'>gated phases</span>",
        f'<div class="lead">Each phase is a vertical slice of user value that is <span class="hl">discussed</span>, '
        f'<span class="hl">planned</span>, <span class="hl">executed</span> and <span class="hl">verified</span> by specialized '
        f'agents — and it cannot pass until its pre-committed evals go green.</div>'
        f'<div class="mtop-l">'
        + callout("This install is <b>eval-gsd</b>: original GSD <i>plus</i> an additive eval-first + context-resilient layer. "
                  "Turn the layer off in config and it behaves exactly like classic GSD. Same 67 commands, two modes.")
        + '</div>', body_top=False), "What GSD is")

    add(slide("Foundations", "The core idea",
        "Six principles that hold the whole thing together",
        cards([
            {"ico":"⊞","h":"Decompose","p":"Projects break into vertical phases — each a complete, testable slice of value, not a horizontal layer."},
            {"ico":"✓","h":"Gate with evals","p":"Every phase locks an eval contract before code. Deterministic rows become the executor’s hard gate."},
            {"ico":"✦","h":"Orchestrate","p":"Specialized subagents — planner, executor, verifier — run in dependency-ordered parallel waves."},
            {"ico":"◆","h":"Persist","p":"A git-verified work ledger survives context resets, so any session resumes exactly where the last stopped."},
            {"ico":"↑","h":"Verify backward","p":"Verification works back from the phase goal — task done ≠ goal achieved."},
            {"ico":"▤","h":"Audit","p":"Every decision, commit and gate result is captured as a durable artifact under .planning/."},
        ], cols=3)), "What GSD is")

    add(slide("Roles", "Who does what",
        "You are the visionary; Claude is the builder",
        cols(
            '<div class="card"><div class="ico">◉</div><h3>You decide</h3>'
            + bullets(["<b>What</b> to build and how it should behave",
                       "Trade-offs at genuine decision points",
                       "Sign-off on human-verify checkpoints"], small=True) + '</div>',
            '<div class="card"><div class="ico">✦</div><h3>Claude builds</h3>'
            + bullets(["Technical <b>how</b>, feasibility, edge cases",
                       "Plans, code, tests, commits, PRs",
                       "Escalates only on a blocked gate or real choice"], small=True) + '</div>',
            '<div class="card"><div class="ico">✓</div><h3>Gates enforce</h3>'
            + bullets(["Pre-flight, revision, escalation, abort",
                       "Eval rows that must go green to pass",
                       "Weakening &amp; gaming detection at verify"], small=True) + '</div>',
        )), "What GSD is")

    add(slide("Foundations", "Artifact ecosystem",
        "Project truth lives in <span class='mono acc'>.planning/</span>",
        table(
            ["Artifact", "Holds", "Written by"],
            [["<b>PROJECT.md</b>","Vision, core value, validated vs active requirements","new-project"],
             ["<b>REQUIREMENTS.md</b>","REQ-01..N with acceptance criteria + traceability","new-project / discuss"],
             ["<b>ROADMAP.md</b>","Phases with goals, dependencies, success criteria","roadmapper"],
             ["<b>NN-CONTEXT.md</b>","Locked decisions, domain terms, code references","discuss-phase"],
             ["<b>NN-EVAL-CONTRACT.md</b>","Code / Judge / Human rows + <code>locked_hash</code>","spec / discuss"],
             ["<b>NN-YY-PLAN.md</b>","Typed tasks with <code>acceptance_criteria</code>","planner"],
             ["<b>NN-VERIFICATION.md</b>","Must-haves verdict + eval verdict","verifier"],
             ["<b>LEDGER.md</b>","Task records, evidence hashes, escalations","execute (orchestrator)"]],
            small=True)), "What GSD is")

    add(slide("Foundations", "The agents",
        "A team of specialists, not one prompt",
        cols(
            table(["Agent", "Job"],
              [["<b>roadmapper</b>","Requirements → phased roadmap"],
               ["<b>phase-researcher</b>","Investigate unknowns before planning"],
               ["<b>planner</b>","Phase scope → typed task plans"],
               ["<b>plan-checker</b>","Validate plans; loop back to planner"],
               ["<b>executor</b>","Run tasks, commit per task, hit gates"],
               ["<b>verifier</b>","Goal-backward + eval verdict"],
               ["<b>code / security / ui</b>","Review &amp; audit specialists"]], small=True),
            bullets([
              "<b>Named contracts</b> <span class='d'>— each agent has a defined input, output marker, and done-condition.</span>",
              "<b>Wave parallelism</b> <span class='d'>— plans group into W1→W2→W3 by dependency; same-wave plans run concurrently.</span>",
              "<b>Worktree isolation</b> <span class='d'>— executors run in their own git worktree; the main tree stays clean.</span>",
              "<b>Fresh context</b> <span class='d'>— each agent starts clean and reads only the artifacts it needs.</span>",
            ], small=True),
            sizes=["s", None])), "What GSD is")

    # ===================== PART 2 — HOW IT WORKS =====================
    add(divider("02", "How it works", "The lifecycle you run, stage by stage."), "How it works")

    add(slide("Lifecycle", "End to end",
        "One project, this loop per phase",
        pipe([
            {"n":"Init","t":"new-project","d":"Questioning → requirements → roadmap"},
            {"n":"Per phase","t":"discuss","d":"Lock decisions in CONTEXT.md"},
            {"n":"Per phase","t":"plan","d":"Planner ↔ checker loop"},
            {"n":"Per phase","t":"execute","d":"Parallel waves, hard gates"},
            {"n":"Per phase","t":"verify","d":"Goal-backward + eval verdict"},
            {"n":"Close","t":"ship","d":"PR from artifacts"},
        ]) + '<div class="mtop-l">' + callout(
            "<b>Autonomous mode</b> drives discuss→plan→execute→verify across every remaining phase, "
            "escalating to you only on a blocked gate or a genuine decision.") + '</div>'),
        "How it works")

    add(slide("Stage 1", "new-project",
        "From a fuzzy idea to a locked roadmap",
        cols(
            pipe([
                {"n":"Step 1","t":"Question","d":"Vision, users, must-haves vs nice-to-haves"},
                {"n":"Step 2","t":"Research","d":"Parallel agents probe unknowns"},
                {"n":"Step 3","t":"Requirements","d":"REQ-01..N, each testable"},
                {"n":"Step 4","t":"Roadmap","d":"Phases + success criteria"},
            ]),
        ) + '<div class="mtop-l">' + callout(
            "Produces <span class='mono'>PROJECT.md</span>, <span class='mono'>REQUIREMENTS.md</span>, "
            "<span class='mono'>ROADMAP.md</span>, <span class='mono'>STATE.md</span> — committed together as the project’s spine.")
        + '</div>'), "How it works")

    add(slide("Stage 1", "Slicing the roadmap",
        "Vertical slices, not horizontal layers",
        compare_or := compare(
            "Horizontal (avoid)",
            ["Build all of the DB, then all of the API, then all of the UI",
             "Nothing is demoable until the very end",
             "Integration risk piles up to the finish"],
            "Vertical (GSD default)",
            ["Each phase cuts through every layer for <b>one</b> capability",
             "Phase 1 is a working, shippable thin slice",
             "Risk is retired continuously, phase by phase"])),
        "How it works")

    add(slide("Stage 2", "discuss-phase",
        "Resolve the gray areas before planning",
        cols(
            '<h3 style="font-size:16px;color:var(--accent);margin-bottom:10px">Claude surfaces gray areas</h3>'
            + bullets(["“Auth: JWT in a cookie, or a bearer token?”",
                       "“Errors: retry, or surface to the user?”",
                       "“Layout: sidebar, or top nav?”"], small=True)
            + '<div class="mtop"><span class="chip">Scope guard</span> <span class="chip">No creep</span></div>',
            '<h3 style="font-size:16px;color:var(--accent2);margin-bottom:10px">You answer → it locks them</h3>'
            + bullets(["Decisions written to <span class='mono'>NN-CONTEXT.md</span>",
                       "Domain terms + canonical code references",
                       "Deferred ideas parked so they’re not re-asked"], small=True)
            + '<div class="mtop">' + callout("New scope? “That’s a new phase, not this one.”") + '</div>',
        )), "How it works")

    add(slide("Stage 2.5", "Eval-first contract",
        "Quality gates are locked <span class='acc'>before</span> any code",
        cols(
            code(
"<span class='c'># NN-EVAL-CONTRACT.md   status: locked</span>\n"
"<span class='c'>| id   | req    | behavior          | measure | sev  |</span>\n"
"| EC-1 | REQ-01 | login → 200 + cookie | Code    | gate |\n"
"| EC-2 | REQ-02 | bad creds → 401     | Code    | gate |\n"
"| EC-3 | REQ-03 | error copy is clear | Judge   | warn |\n"
"| EC-4 | REQ-01 | flow feels smooth   | Human   | warn |\n"
"\n"
"<span class='k'>locked_hash:</span> <span class='s'>sha256(normalized_rows)</span>",
                label="eval-contract.md"),
            bullets([
                "<b>Code</b> <span class='d'>— deterministic CLI; the executor’s hard gate (~80%).</span>",
                "<b>Judge</b> <span class='d'>— rubric scored by a model for subjective quality.</span>",
                "<b>Human</b> <span class='d'>— UAT / felt experience, batched for you.</span>",
                "<b>Coverage gate</b> <span class='d'>— every in-scope REQ needs ≥1 row; no orphans.</span>",
            ], small=True))), "How it works")

    add(slide("Stage 3", "plan-phase",
        "Scope becomes executable tasks",
        cols(
            pipe([
                {"n":"In","t":"context + reqs","d":"CONTEXT.md, requirements, research"},
                {"n":"Plan","t":"planner","d":"Emits typed tasks + waves"},
                {"n":"Check","t":"plan-checker","d":"Validates; loops ≤ 3×"},
                {"n":"Out","t":"PLAN.md","d":"Tasks with acceptance_criteria"},
            ]),
        ) + '<div class="mtop-l">' + callout(
            "Each <span class='mono'>Code</span> + <span class='mono'>gate</span> contract row becomes a task’s "
            "<span class='mono'>&lt;acceptance_criteria&gt;</span> — a CLI command the executor must run green.")
        + '</div>'), "How it works")

    add(slide("Stage 4", "execute-phase",
        "Parallel waves, every task gated",
        cols(
            bullets([
                "<b>Dependency analysis</b> <span class='d'>— plans grouped into waves W1→W2→W3.</span>",
                "<b>Parallel executors</b> <span class='d'>— same-wave plans run at once, in isolated worktrees.</span>",
                "<b>Hard gate per task</b> <span class='d'>— run acceptance_criteria; exit ≠ 0 stops &amp; escalates.</span>",
                "<b>Commit per task</b> <span class='d'>— traceable history; SUMMARY.md records hashes + self-check.</span>",
                "<b>Ledger is truth</b> <span class='d'>— orchestrator is the sole writer of LEDGER.md.</span>",
            ], small=True),
            code(
"<span class='c'>&lt;task type=\"auto\"&gt;</span>\n"
"  &lt;name&gt;POST /login issues a session&lt;/name&gt;\n"
"  <span class='k'>&lt;acceptance_criteria&gt;</span>\n"
"    curl -si localhost:3000/login \\\n"
"      -d '{\"email\":\"a@b.co\",\"pw\":\"x\"}' \\\n"
"      | grep -q 'Set-Cookie: sid='\n"
"  <span class='k'>&lt;/acceptance_criteria&gt;</span>\n"
"<span class='c'>&lt;/task&gt;   # exit 0 → commit · else → halt</span>",
                label="plan task — hard gate"),
            sizes=[None, None])), "How it works")

    add(slide("Stage 5", "verify-phase",
        "Task done ≠ goal achieved",
        cols(
            '<h3 style="font-size:16px;color:var(--accent);margin-bottom:10px">Goal-backward check</h3>'
            + bullets(["Pull <b>must-haves</b> from the phase goal &amp; success criteria",
                       "Each truth: <span class='good'>✓ verified</span> / <span class='bad'>✗ failed</span> / <span class='warn'>? human</span>",
                       "Stubs and unwired code are caught here"], small=True),
            '<h3 style="font-size:16px;color:var(--accent2);margin-bottom:10px">Eval verdict</h3>'
            + bullets(["<b>Coverage</b> — REQ ⇄ eval bijection holds",
                       "<b>Weakening</b> — recompute <span class='mono'>locked_hash</span>; must match",
                       "<b>Gaming</b> — a Code row edited in its own commit is flagged",
                       "<b>Gate rows green</b> — proven from ledger evidence"], small=True),
        ) + '<div class="mtop">' + callout(
            "Writes <span class='mono'>NN-VERIFICATION.md</span> with status <span class='good'>passed</span> / "
            "<span class='bad'>failed</span> / <span class='warn'>human_needed</span>.") + '</div>'),
        "How it works")

    add(slide("Stage 6", "ship & autonomous",
        "Close the phase — or let the loop run",
        cols(
            '<div class="card"><div class="ico">↗</div><h3>/gsd-ship</h3>'
            + bullets(["Pre-flight: verification <b>passed</b>, tree clean, on a branch",
                       "PR body built from goal + commits + eval verdict",
                       "Optional <span class='mono'>--review</span> spawns code-reviewer"], small=True) + '</div>',
            '<div class="card"><div class="ico">↻</div><h3>/gsd-autonomous</h3>'
            + bullets(["Loops every remaining phase hands-free",
                       "Loop-control: detects non-convergence (S1/S2)",
                       "Escalates &amp; pauses instead of thrashing"], small=True) + '</div>',
        )), "How it works")

    add(slide("Guardrails", "Gates & checkpoints",
        "Where the framework stops to think — or to ask you",
        cols(
            table(["Gate", "Fires when"],
              [["<b>Pre-flight</b>","A precondition is missing"],
               ["<b>Revision</b>","Output quality is insufficient → loop"],
               ["<b>Escalation</b>","A human decision is required"],
               ["<b>Abort</b>","Continuing would cause damage"]], small=True),
            table(["Checkpoint", "Means"],
              [["<b>human-verify</b>","“Look at it &amp; confirm” (batched at phase end)"],
               ["<b>decision</b>","“Choose A or B” — blocks until answered"],
               ["<b>human-action</b>","“Enter the secret / API key”"]], small=True),
        )), "How it works")

    add(slide("Continuity", "The work ledger",
        "Why a dropped session is a non-event",
        cols(
            bullets([
                "<b>Single source of truth</b> <span class='d'>— every task: status, evidence hash, attempts, green-eval count.</span>",
                "<b>Git-verified</b> <span class='d'>— a “done” task is re-checked against its commit on resume.</span>",
                "<b>Context-resilient</b> <span class='d'>— at the context warning, the agent checkpoints the ledger; handoff is automatic.</span>",
                "<b>Stall detection</b> <span class='d'>— attempts spike → escalate, instead of looping forever.</span>",
            ], small=True),
            code(
"<span class='c'># .planning/LEDGER.md  —  HEAD</span>\n"
"| task     | phase    | status    | evidence |\n"
"|----------|----------|-----------|----------|\n"
"| 01-01-T1 | 01-auth  | <span class='s'>COMPLETED</span> | c36ae3c  |\n"
"| 01-01-T2 | 01-auth  | <span class='s'>COMPLETED</span> | a91f4d2  |\n"
"| 02-01-T1 | 02-board | IN_PROGRESS| —        |\n"
"\n"
"<span class='c'>resume → reads HEAD, git-verifies, continues</span>",
                label="ledger.md"),
            sizes=[None, None])), "How it works")

    add(slide("Milestones", "Shipping boundaries",
        "Phases ship; milestones graduate",
        pipe([
            {"n":"Open","t":"new-milestone","d":"“What’s next?” + planted seeds"},
            {"n":"Run","t":"phases","d":"discuss→plan→execute→verify"},
            {"n":"Audit","t":"audit-milestone","d":"Coverage + cross-phase integration"},
            {"n":"Close","t":"complete-milestone","d":"Archive roadmap; validate reqs"},
        ]) + '<div class="mtop-l">' + callout(
            "<b>complete-milestone</b> archives the roadmap and promotes shipped requirements into "
            "<span class='mono'>PROJECT.md</span>’s <i>Validated</i> section — ready for the next cycle.") + '</div>'),
        "How it works")

    # ===================== PART 3 — KEY CAPABILITIES =====================
    add(divider("03", "Key capabilities", "The features that make it more than a checklist."), "Capabilities")

    add(slide("Eval-first", "Measurement split",
        "Prove ~80% by machine; reserve humans for what only they can judge",
        stats([
            {"n":"~80%","l":"<b>Code</b> rows — deterministic CLI gates the executor runs every task"},
            {"n":"~15%","l":"<b>Judge</b> rows — model-scored rubrics for subjective quality"},
            {"n":"~5%","l":"<b>Human</b> rows — felt experience &amp; UAT, batched at phase end"},
        ]) + '<div class="mtop-l">' + callout(
            "The split <b>drives architecture</b>: if a behavior can’t be tested without a browser or device, "
            "factor the logic into a pure module so the ~80% stays machine-gatable.") + '</div>'),
        "Capabilities")

    add(slide("Splitting", "MVP mode + SPIDR",
        "When a story is too big, split on one axis",
        table(["Axis", "Trigger", "Split into"],
          [["<b>Spike</b>","An unknown needs research first","Spike phase → implementation phase"],
           ["<b>Paths</b>","Happy path + error paths","Happy path first → error cases"],
           ["<b>Interfaces</b>","Web / mobile / API surfaces","One phase per interface"],
           ["<b>Data</b>","Multiple data scopes","Small scope (one user) → larger"],
           ["<b>Rules</b>","Many business rules","Basic rules first → complex policy"]], small=True)
        + '<div class="mtop">' + callout(
            "MVP mode opens with a <b>walking skeleton</b> — one task proving core value across every layer. "
            "Stories read <span class='mono'>As a [role], I want [action], so that [value]</span>.") + '</div>'),
        "Capabilities")

    add(slide("Discipline", "TDD mode",
        "Behavior-adding tasks go red before green",
        pipe([
            {"n":"Red","t":"Write failing test","d":"Commit the intent, watch it fail"},
            {"n":"Green","t":"Make it pass","d":"Smallest implementation that satisfies"},
            {"n":"Refactor","t":"Clean up","d":"Improve with the test as a net"},
        ]) + '<div class="mtop-l">'
        + cols(
            '<b style="color:var(--accent2)">Use for</b>' + bullets(["Business logic, validation, transforms","Algorithms &amp; API contracts"], small=True),
            '<b style="color:var(--bad)">Skip for</b>' + bullets(["UI styling, config, glue code","Exploratory prototyping"], small=True))
        + '</div>'), "Capabilities")

    add(slide("Quality gates", "Review on demand",
        "Three specialist audits you can run any time",
        cards([
            {"ico":"✓","h":"/gsd-code-review","p":"Diff reviewed for bugs, simplification and risky patterns. Post inline (--comment) or auto-apply (--fix)."},
            {"ico":"◈","h":"/gsd-secure-phase","p":"STRIDE threat model vs the code: input validation, auth, crypto, secrets. Produces SECURITY.md."},
            {"ico":"▤","h":"/gsd-ui-review","p":"Live UI audited against UI-SPEC.md across six visual pillars. Produces a scored UI-REVIEW.md."},
        ], cols=3)), "Capabilities")

    add(slide("AI features", "ai-integration-phase",
        "A dedicated track for phases that call an LLM",
        cols(
            pipe([
                {"n":"1","t":"Framework","d":"Pick SDK / LangChain / …"},
                {"n":"2","t":"AI-SPEC","d":"Prompts, guardrails, cost"},
                {"n":"3","t":"Eval plan","d":"Quality, latency, cost rows"},
            ]),
        ) + '<div class="mtop-l">' + callout(
            "Output is an <span class='mono'>AI-SPEC.md</span>: framework decision, a prompt reference library, "
            "and an eval strategy so model quality is measured — not hoped for.") + '</div>'),
        "Capabilities")

    add(slide("Mobile & full-stack", "Eval hooks",
        "Mobile is ~80% gatable — here’s how (React Native)",
        table(["Behavior", "command_or_rubric", "Severity"],
          [["Types sound","<code>npx tsc --noEmit</code>","<span class='badge good'>gate</span>"],
           ["Lint clean","<code>npx eslint . --max-warnings=0</code>","<span class='badge good'>gate</span>"],
           ["Tests pass","<code>npm test -- --ci</code>","<span class='badge good'>gate</span>"],
           ["JS bundles","<code>npx expo export --platform ios</code>","<span class='badge good'>gate</span>"],
           ["Native build","<code>xcodebuild … / gradlew assembleDebug</code>","<span class='badge warn'>warn*</span>"],
           ["E2E on sim","<code>maestro test .maestro/</code>","<span class='badge warn'>warn*</span>"],
           ["Feels right","manual UAT","<span class='badge bad'>Human</span>"]], small=True)
        + '<div class="mtop-s" style="font-size:12.5px;color:var(--faint)">* warn = gate-skips when the SDK / simulator is absent — and the skip is logged, never silently “covered”.</div>'),
        "Capabilities")

    # ===================== PART 4 — HOW TO USE =====================
    add(divider("04", "How to use it", "The commands you actually type."), "Using GSD")

    add(slide("Commands", "The surface, grouped",
        "67 commands — the dozen you’ll live in",
        cols(
            '<h3 style="font-size:15px;color:var(--accent);margin-bottom:8px">Lifecycle</h3>'
            + bullets(["<span class='mono'>/gsd-new-project</span>","<span class='mono'>/gsd-new-milestone</span>","<span class='mono'>/gsd-ship</span>","<span class='mono'>/gsd-complete-milestone</span>"], small=True),
            '<h3 style="font-size:15px;color:var(--accent);margin-bottom:8px">Per phase</h3>'
            + bullets(["<span class='mono'>/gsd-discuss-phase N</span>","<span class='mono'>/gsd-spec-phase N</span>","<span class='mono'>/gsd-plan-phase N</span>","<span class='mono'>/gsd-execute-phase N</span>","<span class='mono'>/gsd-verify-phase N</span>"], small=True),
            '<h3 style="font-size:15px;color:var(--accent);margin-bottom:8px">Quality &amp; auto</h3>'
            + bullets(["<span class='mono'>/gsd-autonomous</span>","<span class='mono'>/gsd-code-review</span>","<span class='mono'>/gsd-secure-phase N</span>","<span class='mono'>/gsd-ui-review</span>","<span class='mono'>/gsd-ai-integration-phase</span>"], small=True),
        )), "Using GSD")

    add(slide("Commands", "The everyday loop",
        "Three commands carry most days",
        cards([
            {"ico":"◉","h":"/gsd-progress","p":"The situational command. Reads STATE + ledger, tells you exactly what to do next, and routes there."},
            {"ico":"→","h":"/gsd-next","p":"Advance to the next action or phase without thinking about which command comes next."},
            {"ico":"↻","h":"/gsd-resume-work","p":"Reads LEDGER HEAD, git-verifies done work, halts on open escalations — full context restored."},
        ], cols=3)
        + '<div class="mtop-l">' + callout(
            "Lost? <span class='mono'>/gsd-progress</span> always knows where you are and what’s next. "
            "<span class='mono'>/gsd-health</span> and <span class='mono'>/gsd-stats</span> diagnose the project at a glance.") + '</div>'),
        "Using GSD")

    add(slide("Quickstart", "Zero to shipped",
        "A whole project in a handful of commands",
        code(
"<span class='c'># 1 · scope it — questioning → requirements → roadmap</span>\n"
"/gsd-new-project\n\n"
"<span class='c'># 2 · per phase: lock decisions, plan, build, verify</span>\n"
"/gsd-discuss-phase 1\n"
"/gsd-plan-phase 1\n"
"/gsd-execute-phase 1     <span class='c'># waves + hard gates + verify</span>\n\n"
"<span class='c'># 3 · or let it run the rest hands-free</span>\n"
"/gsd-autonomous          <span class='c'># escalates only when it must</span>\n\n"
"<span class='c'># 4 · close it out</span>\n"
"/gsd-ship 1 --review     <span class='c'># PR + code review</span>",
            label="terminal")), "Using GSD")

    # ===================== PART 5 — EXAMPLE 1: SAAS =====================
    add(divider("05", "Example 1 · SaaS app", "“TaskFlow” — a team task-management product."), "Example 1 · SaaS")

    add(slide("Example 1", "Meet TaskFlow",
        "A multi-tenant team task app",
        cols(
            '<div class="lead" style="font-size:18px">Workspaces with teams, a task board, real-time collaboration, '
            'and Stripe subscription billing. We’ll scope it, then walk <span class="hl">Phase 1 (Auth)</span> '
            'file by file — the same loop every phase follows.</div>',
            '<div class="card"><h3 style="font-size:15px">Constraints locked at new-project</h3>'
            + bullets(["Multi-tenant: a user belongs to many workspaces","Postgres + a Node/TS API + React SPA","Stripe for subscriptions","Ship thin slices weekly"], small=True) + '</div>',
            sizes=[None, "s"])), "Example 1 · SaaS")

    add(slide("Example 1", "new-project output",
        "Vision and testable requirements",
        cols(
            code(
"<span class='c'># PROJECT.md</span>\n"
"<span class='k'>Core value:</span> a team plans &amp; tracks work\n"
"  in shared workspaces, in real time.\n\n"
"<span class='k'>Active requirements:</span>\n"
"  REQ-01  email + password auth\n"
"  REQ-02  workspaces &amp; membership\n"
"  REQ-03  tasks: create / assign / move\n"
"  REQ-04  realtime board updates\n"
"  REQ-05  Stripe subscription billing",
                label="PROJECT.md"),
            code(
"<span class='c'># REQUIREMENTS.md — each one testable</span>\n"
"<span class='k'>REQ-01</span> Auth\n"
"  AC: POST /login with valid creds\n"
"      → 200 + HttpOnly session cookie\n"
"  AC: invalid creds → 401, no cookie\n"
"  AC: error copy never says which\n"
"      field was wrong\n"
"  phase: 01",
                label="REQUIREMENTS.md"),
            sizes=[None, None])), "Example 1 · SaaS")

    add(slide("Example 1", "The roadmap",
        "Five vertical slices, each shippable",
        table(["Phase", "Goal", "Reqs", "Ships"],
          [["<b>01 · Auth</b>","Email/password login + sessions","REQ-01","Users can sign in"],
           ["<b>02 · Workspaces</b>","Create workspace, invite members","REQ-02","Teams exist"],
           ["<b>03 · Board</b>","Create / assign / move tasks","REQ-03","A usable task board"],
           ["<b>04 · Realtime</b>","Live board updates over WebSocket","REQ-04","Collaboration"],
           ["<b>05 · Billing</b>","Stripe subscriptions + webhooks","REQ-05","Revenue"]], small=True)
        + '<div class="mtop">' + callout(
            "Dependencies: 02→01, 03→02, 04→03, 05→02. The executor reads these and waves the work; "
            "01 is a complete, demoable slice on its own.") + '</div>'), "Example 1 · SaaS")

    add(slide("Example 1 · Phase 1", "discuss → CONTEXT",
        "Gray areas in, locked decisions out",
        cols(
            '<h3 style="font-size:15px;color:var(--accent);margin-bottom:10px">Claude asks</h3>'
            + bullets(["Session: JWT-in-cookie or server session?","Password hashing: bcrypt or argon2?","Lockout after N failed attempts?"], small=True),
            '<h3 style="font-size:15px;color:var(--accent2);margin-bottom:10px">You decide → NN-CONTEXT.md</h3>'
            + bullets(["<b>HttpOnly cookie</b> holding a rotating session id","<b>argon2id</b>, per-user salt","Lockout deferred to the hardening phase"], small=True),
            sizes=[None, None])
        + '<div class="mtop">' + callout(
            "“Add SSO?” → parked in <i>Deferred</i>, not built now. The phase scope stays exactly REQ-01.") + '</div>'),
        "Example 1 · SaaS")

    add(slide("Example 1 · Phase 1", "The eval contract",
        "Locked before a single line of auth code",
        code(
"<span class='c'># 01-EVAL-CONTRACT.md          status: locked</span>\n"
"<span class='c'>| id   | req    | behavior                       | measure | sev  |</span>\n"
"| EC-1 | REQ-01 | valid login → 200 + Set-Cookie   | Code    | gate |\n"
"| EC-2 | REQ-01 | bad creds → 401, no cookie       | Code    | gate |\n"
"| EC-3 | REQ-01 | password stored argon2id, never plaintext | Code | gate |\n"
"| EC-4 | REQ-01 | error copy never reveals which field failed | Judge | warn |\n"
"| EC-5 | REQ-01 | sign-in flow feels smooth on mobile web      | Human | warn |\n"
"\n"
"<span class='k'>coverage:</span> <span class='s'>REQ-01 → 5 rows (clean)</span>     <span class='k'>locked_hash:</span> <span class='s'>9f2a…c7</span>",
            label="01-EVAL-CONTRACT.md")
        + '<div class="mtop-s"><span class="chip">3 Code gates</span> <span class="chip">1 Judge</span> <span class="chip">1 Human</span></div>'),
        "Example 1 · SaaS")

    add(slide("Example 1 · Phase 1", "plan → execute → summary",
        "The contract becomes runnable tasks",
        chain([
            {"f":"01-01-PLAN.md","l":"planner","d":"<b>T1</b> hash+store user · <b>T2</b> POST /login · <b>T3</b> session cookie middleware"},
            {"f":"T2 acceptance","l":"hard gate","d":"<span class='mono'>curl -si .../login -d @ok.json | grep -q 'Set-Cookie: sid='</span>  → EC-1"},
            {"f":"T1 acceptance","l":"hard gate","d":"<span class='mono'>node test/hash.mjs</span> asserts stored value starts <span class='mono'>$argon2id$</span>  → EC-3"},
            {"f":"01-01-SUMMARY.md","l":"executor","d":"Commits <span class='mono'>c36ae3c</span>, <span class='mono'>a91f4d2</span>, <span class='mono'>7b1e0aa</span> · self-check <span class='good'>PASSED</span>"},
        ])
        + '<div class="mtop">' + callout(
            "EC-2 also runs green. EC-4 (Judge) is scored by a model; EC-5 (Human) is queued to the phase-end UAT batch.") + '</div>'),
        "Example 1 · SaaS")

    add(slide("Example 1 · Phase 1", "verify & ship",
        "Proven, not assumed — then a PR",
        cols(
            code(
"<span class='c'># 01-VERIFICATION.md</span>\n"
"<span class='k'>status:</span> <span class='s'>passed</span>\n"
"<span class='k'>eval_verdict:</span>\n"
"  coverage:  <span class='s'>clean</span>\n"
"  weakening: <span class='s'>clean  (hash matches)</span>\n"
"  gaming:    <span class='s'>none</span>\n"
"  gate_rows: <span class='s'>3/3 green</span>\n\n"
"| must-have            | result |\n"
"| login issues session | <span class='s'>✓ PASS</span> |\n"
"| secrets never stored | <span class='s'>✓ PASS</span> |",
                label="01-VERIFICATION.md"),
            bullets([
                "<b>/gsd-ship 1 --review</b>",
                "PR body auto-built: goal, the 3 commits, eval verdict, UAT note",
                "code-reviewer scans the diff before merge",
                "<span class='good'>Phase 1 shipped</span> — the loop repeats for 02–05",
            ], small=True),
            sizes=[None, None])), "Example 1 · SaaS")

    add(slide("Example 1", "Scaling out",
        "The same loop, four more times",
        table(["Phase", "Notable eval rows", "Mix"],
          [["<b>02 Workspaces</b>","membership query returns only my workspaces (Code)","Code-heavy"],
           ["<b>03 Board</b>","move task persists column + order (Code); board reads clean (Judge)","Code + Judge"],
           ["<b>04 Realtime</b>","2 clients converge on edit (Code, headless); latency feels live (Human)","Code + Human"],
           ["<b>05 Billing</b>","Stripe webhook is idempotent (Code); failed-card UX (Judge); receipt (Human)","All three"]], small=True)
        + '<div class="mtop">' + callout(
            "<b>complete-milestone</b> archives the roadmap and promotes REQ-01..05 to <i>Validated</i>. "
            "TaskFlow v1 is done; v2 starts with <span class='mono'>/gsd-new-milestone</span>.") + '</div>'),
        "Example 1 · SaaS")

    # ===================== PART 6 — EXAMPLE 2: PAYMENT GATEWAY =====================
    add(divider("06", "Example 2 · Payment gateway",
        "“PayLink” — merchant mobile app + backend + admin dashboard."), "Example 2 · Payments")

    add(slide("Example 2", "Meet PayLink",
        "One product, three surfaces, one shared backbone",
        cards([
            {"ico":"▢","h":"Merchant app","p":"React Native. Onboard, accept a payment, watch balance &amp; payouts, get push receipts."},
            {"ico":"⌗","h":"Backend / API","p":"Node + TS. Accounts, charge creation, idempotent webhooks, payout ledger — the dependency for everything."},
            {"ico":"▤","h":"Admin dashboard","p":"Web. Merchant management, transaction monitoring, disputes, metrics — behind RBAC."},
        ], cols=3)
        + '<div class="mtop-l">' + callout(
            "Money + three clients + compliance = exactly where eval-first earns its keep. We’ll see the "
            "<b>SPIDR Interfaces</b> split, real <b>mobile eval hooks</b>, a <b>STRIDE</b> pass, and an AI phase.") + '</div>'),
        "Example 2 · Payments")

    add(slide("Example 2", "Requirements across surfaces",
        "Numbered once, traced everywhere",
        table(["Surface", "Requirements"],
          [["<b>Backend</b>","REQ-01 merchant auth · REQ-02 create charge · REQ-03 idempotent webhook · REQ-04 payout ledger"],
           ["<b>Merchant app</b>","REQ-05 onboarding · REQ-06 accept payment (QR) · REQ-07 balance &amp; payouts · REQ-08 push receipts"],
           ["<b>Admin</b>","REQ-09 merchant management · REQ-10 txn monitoring · REQ-11 disputes · REQ-12 metrics (RBAC)"],
           ["<b>Cross-cutting</b>","REQ-13 fraud-risk score · REQ-14 PCI-aligned hardening · REQ-15 rate limits"]], small=True)),
        "Example 2 · Payments")

    add(slide("Example 2", "SPIDR · Interfaces split",
        "“Accept a payment” spans three clients → three phases",
        cols(
            '<div class="callout"><b>One story, too big:</b><br>“As a merchant, I want to take a card payment '
            'and see it land in my balance, so that I get paid.”</div>'
            + '<div class="mtop-s" style="font-size:14px;color:var(--muted)">Touches API + mobile + admin and crosses '
            'the happy/error paths. SPIDR splits it on the <b style="color:var(--accent)">Interfaces</b> axis first, '
            'then <b>Paths</b> within each.</div>',
            pipe([
                {"n":"depends","t":"Backend","d":"charge + webhook is the contract everyone calls"},
                {"n":"then","t":"Mobile","d":"merchant initiates &amp; sees the result"},
                {"n":"then","t":"Admin","d":"staff monitor &amp; resolve"},
            ]),
            sizes=["s", None])), "Example 2 · Payments")

    add(slide("Example 2", "Roadmap across surfaces",
        "Backend first; mobile and admin parallelize as workstreams",
        table(["Phase", "Surface", "Goal"],
          [["<b>01</b>","Backend","Merchant auth + accounts API"],
           ["<b>02</b>","Backend","Create charge + <b>idempotent</b> webhook"],
           ["<b>03</b>","Backend","Payout ledger (double-entry)"],
           ["<b>04</b>","Mobile","Onboarding + accept payment (RN)"],
           ["<b>05</b>","Mobile","Balance, payout history, push"],
           ["<b>06</b>","Admin","Merchant management + RBAC"],
           ["<b>07</b>","Admin","Txn monitoring + disputes + metrics"],
           ["<b>08</b>","AI","Fraud-risk scoring assist"],
           ["<b>09</b>","All","PCI-aligned hardening + rate limits"]], small=True)
        + '<div class="mtop-s" style="font-size:12.5px;color:var(--faint)">Phases 04 and 06 both depend only on the backend — run them as parallel <span class="mono">--ws</span> workstreams.</div>'),
        "Example 2 · Payments")

    add(slide("Example 2 · Phase 02", "Backend: the meaty gate",
        "Idempotency is a deterministic <span class='acc'>Code</span> gate",
        cols(
            code(
"<span class='c'># 02-EVAL-CONTRACT.md          status: locked</span>\n"
"| id   | req    | behavior                  | measure |\n"
"| EC-1 | REQ-02 | POST /charges → 201 + id   | Code    |\n"
"| EC-2 | REQ-03 | replayed webhook applies  | Code    |\n"
"|      |        | <b>exactly once</b>              |         |\n"
"| EC-3 | REQ-03 | bad signature → 401       | Code    |\n"
"| EC-4 | REQ-02 | decline UX is clear       | Judge   |",
                label="02-EVAL-CONTRACT.md"),
            code(
"<span class='c'># the EC-2 gate (acceptance_criteria)</span>\n"
"node test/webhook-dedupe.mjs\n"
"  <span class='c'># posts same event twice with one</span>\n"
"  <span class='c'># Idempotency-Key; asserts the</span>\n"
"  <span class='c'># ledger moved balance ONCE</span>\n"
"<span class='s'>→ exit 0  ✓ EC-2 green</span>",
                label="hard gate — exactly-once"),
            sizes=[None, None])
        + '<div class="mtop-s">' + callout(
            "Authoring the contract first forces the design: an <b>Idempotency-Key</b> table and a double-entry "
            "ledger — because that’s the only way EC-2 can go green.") + '</div>'),
        "Example 2 · Payments")

    add(slide("Example 2 · Phase 02", "secure-phase · STRIDE",
        "Threat-model the charge endpoint before shipping",
        table(["STRIDE", "Threat", "Mitigation (verified in code)"],
          [["<b>Tampering</b>","Forged webhook body","HMAC signature check → EC-3 gate"],
           ["<b>Repudiation</b>","“I never got paid”","Append-only ledger + evidence hashes"],
           ["<b>Info disclosure</b>","PAN in logs","No card data stored; tokens only (PCI)"],
           ["<b>DoS</b>","Charge-spam a merchant","Per-key rate limit → REQ-15"],
           ["<b>Elevation</b>","Merchant A reads B’s charges","Tenant scoping on every query"]], small=True)
        + '<div class="mtop-s" style="font-size:12.5px;color:var(--faint)">/gsd-secure-phase writes SECURITY.md and verifies each mitigation actually exists in the diff — not just claimed.</div>'),
        "Example 2 · Payments")

    add(slide("Example 2 · Phase 04", "Mobile: real eval hooks",
        "React Native is ~80% gatable — the contract proves it",
        table(["Behavior (merchant app)", "command_or_rubric", "Sev"],
          [["Types &amp; lint sound","<code>npx tsc --noEmit</code> · <code>eslint</code>","<span class='badge good'>gate</span>"],
           ["Charge-flow logic unit-tested","<code>npm test -- --ci</code>","<span class='badge good'>gate</span>"],
           ["App bundles for iOS","<code>npx expo export --platform ios</code>","<span class='badge good'>gate</span>"],
           ["Accept-payment e2e on sim","<code>maestro test .maestro/pay.yaml</code>","<span class='badge warn'>warn*</span>"],
           ["Tap-to-pay <i>feels</i> instant","manual UAT on a real device","<span class='badge bad'>Human</span>"]], small=True)
        + '<div class="mtop-s">' + callout(
            "Logic is factored <b>out of the components</b> (the <span class='mono'>call-core.js</span> discipline), so the "
            "charge state machine is unit-gated without a render surface.") + '</div>'),
        "Example 2 · Payments")

    add(slide("Example 2 · Phase 04", "Mobile: decisions & split",
        "discuss locks the platform questions; the mix stays honest",
        cols(
            '<h3 style="font-size:15px;color:var(--accent);margin-bottom:10px">CONTEXT.md decisions</h3>'
            + bullets(["Expo managed RN (no custom native module needed)","QR-presented charge; card entry stays server-side (PCI)","Optimistic UI, reconciled by webhook"], small=True),
            '<h3 style="font-size:15px;color:var(--accent2);margin-bottom:10px">Measurement mix</h3>'
            + bullets(["<b>Code</b> gates: types, tests, bundle — always run","<b>warn</b>: sim e2e &amp; device build — skip+log if no SDK","<b>Human</b>: gesture feel, push-receipt UX","Store submission → Human, never a Code gate"], small=True),
            sizes=[None, None])), "Example 2 · Payments")

    add(slide("Example 2 · Phase 06–07", "Admin: RBAC + UI review",
        "Read-only first; privileged actions split out by Paths",
        cols(
            bullets([
                "<b>RBAC gate (Code)</b> <span class='d'>— a support role hitting a refund route gets 403.</span>",
                "<b>Tenant isolation (Code)</b> <span class='d'>— admin queries scope to permitted merchants only.</span>",
                "<b>Metrics correctness (Code)</b> <span class='d'>— daily volume = sum of settled charges, asserted.</span>",
                "<b>/gsd-ui-review</b> <span class='d'>— dashboard audited vs UI-SPEC.md across six visual pillars.</span>",
            ], small=True),
            '<div class="card"><h3 style="font-size:15px">Paths split</h3>'
            + bullets(["P06: view &amp; manage merchants (read)","P07: disputes &amp; refunds (privileged write)","Risky writes get their own gates + human-verify"], small=True) + '</div>',
            sizes=[None, "s"])), "Example 2 · Payments")

    add(slide("Example 2 · Phase 08", "AI: fraud-risk assist",
        "An LLM phase gets its own spec and evals",
        cols(
            pipe([
                {"n":"1","t":"Framework","d":"Claude SDK + tool use"},
                {"n":"2","t":"AI-SPEC","d":"Prompt, guardrails, cost cap"},
                {"n":"3","t":"Eval plan","d":"Labeled set + thresholds"},
            ]),
        ) + '<div class="mtop-l">' + cols(
            '<b style="color:var(--accent2)">Code/Judge evals</b>'
            + bullets(["Precision/recall vs a labeled charge set ≥ target","p95 latency &lt; budget; cost/call &lt; cap","Never auto-blocks — only <i>flags</i> for review"], small=True),
            '<b style="color:var(--bad)">Human evals</b>'
            + bullets(["Analyst agrees the flag reasons are sensible","False-positive friction is acceptable"], small=True))
        + '</div>'), "Example 2 · Payments")

    add(slide("Example 2", "Autonomous + integration",
        "Run the surfaces, then prove they connect",
        cols(
            bullets([
                "<b>/gsd-autonomous --from 2</b> <span class='d'>— drives backend, mobile and admin phases; pauses only on decisions or a blocked gate.</span>",
                "<b>Loop-control</b> <span class='d'>— if an eval won’t converge (S1 retries / S2 negative progress), it escalates instead of thrashing.</span>",
                "<b>audit-milestone</b> <span class='d'>— integration-checker verifies the e2e flow: app charge → backend → webhook → admin sees it.</span>",
            ], small=True),
            code(
"<span class='c'># cross-surface e2e (warn smoke)</span>\n"
"mobile: maestro pay.yaml  <span class='s'>→ charge id</span>\n"
"backend: replay webhook   <span class='s'>→ ledger +1</span>\n"
"admin: GET /txns/&lt;id&gt;     <span class='s'>→ settled</span>\n"
"<span class='s'>✓ the slice works end-to-end</span>",
                label="integration check"),
            sizes=[None, None])
        + '<div class="mtop-s">' + callout(
            "<b>complete-milestone</b> promotes REQ-01..15 to <i>Validated</i>. PayLink v1 ships with a proof trail "
            "for every surface — exactly what an auditor (or a future you) needs.") + '</div>'),
        "Example 2 · Payments")

    # ===================== PART 7 — CLOSE =====================
    add(divider("07", "Wrap-up", "When to reach for it, and how to start."), "Wrap-up")

    add(slide("Fit", "When GSD shines — and when it doesn’t",
        "Match the tool to the job",
        compare(
            "Overkill for",
            ["A one-off script or throwaway spike","A tiny fix with no real spec","Pure exploration where the goal is still unknown"],
            "Built for",
            ["Multi-phase products with real requirements","Teams that want autonomy <b>and</b> governance","Anything where “prove it works” matters — payments, data, AI"])
        + '<div class="mtop-s" style="font-size:12.5px;color:var(--faint)">Need classic-GSD speed? Set <span class="mono">eval_first.require_contract: false</span> and the gating layer no-ops.</div>'),
        "Wrap-up")

    add(slide("Takeaways", "Four things to remember",
        "If you keep only this",
        cards([
            {"num":"01","h":"Gated phases","p":"Small vertical slices, each with locked scope and a pre-committed definition of done."},
            {"num":"02","h":"Eval-first","p":"~80% proven by deterministic Code gates; humans judge only what only they can."},
            {"num":"03","h":"Orchestrated","p":"Specialist agents run in parallel waves; you decide, gates enforce, the loop drives."},
            {"num":"04","h":"Resumable","p":"A git-verified ledger means a dropped context is a non-event — resume and continue."},
        ], cols=2)), "Wrap-up")

    add(slide("Start", "Your first hour",
        "Three commands and you’re moving",
        cols(
            code(
"<span class='c'># point GSD at your idea</span>\n"
"/gsd-new-project\n\n"
"<span class='c'># build the first slice, end to end</span>\n"
"/gsd-discuss-phase 1\n"
"/gsd-plan-phase 1\n"
"/gsd-execute-phase 1\n\n"
"<span class='c'># lost? this always knows what’s next</span>\n"
"/gsd-progress",
                label="get started"),
            bullets([
                "<b>Explore the install</b> <span class='d'>— references/ explains every concept in depth.</span>",
                "<b>Real examples</b> <span class='d'>— the slugify, WebRTC and dogfood projects show full .planning/ trails.</span>",
                "<b>Tune it</b> <span class='d'>— /gsd-config toggles eval-first, TDD, MVP and model profiles.</span>",
                "<b>Help</b> <span class='d'>— /gsd-help lists all 67 commands with usage.</span>",
            ], small=True),
            sizes=[None, None])
        + '<div class="mtop">' + callout("<b>Get shit done</b> — from idea to merged PR, with proof at every gate.") + '</div>'),
        "Wrap-up")

    return None

# --------------------------------------------------------------------------------------
# Render
# --------------------------------------------------------------------------------------
def render(theme):
    pal = PALETTES[theme]
    rootvars = "\n".join(f"  {k}:{v};" for k, v in pal.items() if not k.startswith("--surface\""))
    rootvars = "\n".join(f"  {k}:{v};" for k, v in pal.items())
    total = len(SLIDES)
    body = ""
    for n, (html, sec) in enumerate(zip(SLIDES, SECTIONS), start=1):
        html = html.replace("__FOOT__", _foot(sec, n, total))
        body += html
    return f"""<!DOCTYPE html>
<html lang="en" data-theme="{theme}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GSD — How it works &amp; how to use it ({theme})</title>
<style>
:root {{
{rootvars}
}}
{CSS}
</style>
</head>
<body>
<div id="stage"><div id="deck">{body}</div></div>
<div class="navhint">← → navigate · {theme} theme</div>
<script>{JS}</script>
</body>
</html>"""

def write_all(prefix="gsd-presentation"):
    here = os.path.dirname(os.path.abspath(__file__))
    paths = {}
    for theme in ("dark", "light", "print"):
        p = os.path.join(here, f"{prefix}-{theme}.html")
        with open(p, "w") as f:
            f.write(render(theme))
        paths[theme] = p
    return paths

if __name__ == "__main__":
    build_deck()
    paths = write_all()
    for t, p in paths.items():
        print(f"{t:6s} -> {p}  ({len(SLIDES)} slides)")
