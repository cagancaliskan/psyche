#!/usr/bin/env python3
"""
Build four LinkedIn social cards for Psyche in the project's own brand identity
(the "ancient manuscript at dawn" look from psyche-brand.html): ink/parchment/gold,
Cormorant Garamond + Cormorant SC for display, Inter for eyebrows/footers, a faint
fractal-noise grain, and a thin gold hairline.

Each card is a STANDALONE 1200x1200 HTML file with brand fonts base64-embedded, so
it renders identically offline. The cards are then screenshot with headless Chrome
at 2x and downsampled to a crisp 1200x1200 PNG.

Wording follows the project's claim rules (README, REPORT): no claim of a mind,
consciousness, AGI or a validated cognitive model; nothing implying the cognitive
layer works. The Greek mark appears only beside the wordmark, no gloss. Numbers are
exact: 130 / 0 / 56 / 6 / 0.

Requires Pillow (pip install pillow) and Chrome or chrome-headless-shell.
Run:  python3 build_cards.py
"""
import os, re, glob, base64, subprocess, urllib.request, urllib.parse
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
# chrome-headless-shell is purpose-built for screenshots and exits cleanly after
# capture (full Chrome --headless lingers). Fall back to system Chrome if absent.
_shells = glob.glob(os.path.expanduser(
    "~/.cache/puppeteer/chrome-headless-shell/*/chrome-headless-shell-*/chrome-headless-shell"))
CHROME = _shells[0] if _shells else "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# --------------------------------------------------------------------------
# 1) brand fonts: fetch the latin (or text-) subset woff2 and base64-embed
# --------------------------------------------------------------------------
def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()

SRC = re.compile(r"src:\s*url\((https://[^)]+)\)\s*format\(['\"]woff2['\"]\)")
URANGE = re.compile(r"unicode-range:\s*([^;]+);")

def _css(spec):
    url = "https://fonts.googleapis.com/css2?family=" + spec + "&display=swap"
    return _get(url).decode("utf-8", "replace")

def _subset(css, subset):
    """Return (woff2_url, unicode_range) for a named static subset block."""
    blocks = re.split(r"/\*\s*([\w-]+)\s*\*/", css)
    for i in range(1, len(blocks) - 1, 2):
        if blocks[i] == subset:
            m = SRC.search(blocks[i + 1]); u = URANGE.search(blocks[i + 1])
            return m.group(1), (u.group(1).strip() if u else None)
    raise RuntimeError("subset %r not found for css" % subset)

def _b64(woff2_url):
    return base64.b64encode(_get(woff2_url)).decode("ascii")

def face(family, style, weight, b64, urange=None):
    ur = ("unicode-range:%s;" % urange) if urange else ""
    return ("@font-face{font-family:'%s';font-style:%s;font-weight:%d;font-display:block;"
            "src:url(data:font/woff2;base64,%s) format('woff2');%s}"
            % (family, style, weight, b64, ur))

def build_fontfaces():
    cache = os.path.join(HERE, "_fontfaces.css")
    if os.path.exists(cache):
        return open(cache, encoding="utf-8").read()
    latin = [
        ("Cormorant Garamond", "normal", 400, "Cormorant+Garamond:ital,wght@0,400"),
        ("Cormorant Garamond", "normal", 500, "Cormorant+Garamond:ital,wght@0,500"),
        ("Cormorant Garamond", "normal", 600, "Cormorant+Garamond:ital,wght@0,600"),
        ("Cormorant Garamond", "italic", 400, "Cormorant+Garamond:ital,wght@1,400"),
        ("Cormorant Garamond", "italic", 500, "Cormorant+Garamond:ital,wght@1,500"),
        ("Cormorant SC",       "normal", 400, "Cormorant+SC:wght@400"),
        ("Inter",              "normal", 300, "Inter:wght@300"),
        ("Inter",              "normal", 400, "Inter:wght@400"),
    ]
    out = []
    for fam, style, wt, spec in latin:
        url, _ = _subset(_css(spec), "latin")
        out.append(face(fam, style, wt, _b64(url)))
    # Greek mark (ψυχή) from EB Garamond italic (a Garamond cousin to Cormorant);
    # ψ υ χ ή all sit in the 'greek' subset; 'greek-ext' is kept for polytonic forms.
    eb = _css("EB+Garamond:ital,wght@1,500")
    for sub in ("greek", "greek-ext"):
        url, ur = _subset(eb, sub)
        out.append(face("PsycheGreek", "italic", 500, _b64(url), ur))
    css = "\n".join(out)
    with open(os.path.join(HERE, "_fontfaces.css"), "w", encoding="utf-8") as f:
        f.write(css)
    return css

# --------------------------------------------------------------------------
# 2) HTML template (brand frame) + per-card content
# --------------------------------------------------------------------------
TEMPLATE = r"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<style>
/*FONTFACES*/
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box;}
html,body{width:1200px;height:1200px;}
body{background:#0a0908;color:#f5f0e8;font-family:'Cormorant Garamond',Georgia,serif;
  position:relative;overflow:hidden;-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility;}
.glow{position:absolute;left:50%;top:43%;width:1000px;height:1000px;transform:translate(-50%,-50%);
  z-index:0;pointer-events:none;
  background:radial-gradient(ellipse at center, rgba(184,145,58,0.085) 0%, rgba(184,145,58,0) 68%);}
.grain{position:absolute;inset:0;z-index:40;pointer-events:none;opacity:0.55;
  background-image:url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.085'/%3E%3C/svg%3E");}
.frame{position:absolute;inset:0;z-index:10;display:flex;flex-direction:column;
  justify-content:space-between;align-items:center;text-align:center;padding:100px 92px;}
.top{display:flex;flex-direction:column;align-items:center;}
.eyebrow{font-family:'Inter',sans-serif;font-weight:300;text-transform:uppercase;
  letter-spacing:0.34em;font-size:37px;color:#b8913a;}
.eyebrow .dot{color:#8a8278;padding:0 0.08em;}
.eyebrow .greek{font-family:'PsycheGreek','Cormorant Garamond',serif;font-style:italic;
  text-transform:none;letter-spacing:0.02em;font-size:56px;color:#8a8278;vertical-align:-4px;}
.hairline{width:1px;height:74px;margin-top:36px;background:linear-gradient(to bottom,#b8913a,rgba(184,145,58,0));}
.mid{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;}
.main{font-family:'Cormorant Garamond',serif;font-weight:500;color:#f5f0e8;line-height:1.15;letter-spacing:0.004em;}
.main em{font-style:italic;color:#d4ab5a;font-weight:500;}
.main .line{display:block;}
.main .gap{display:block;height:0.42em;}
.subitalic{font-family:'Cormorant Garamond',serif;font-style:italic;font-weight:400;
  color:#d4ab5a;line-height:1.2;}
.stats{display:flex;flex-direction:column;align-items:center;}
.stat{margin-bottom:34px;}
.stat:last-child{margin-bottom:0;}
.num{font-family:'Cormorant SC',serif;font-weight:400;font-size:132px;line-height:0.95;color:#f5f0e8;letter-spacing:0.02em;}
.lbl{font-family:'Inter',sans-serif;font-weight:300;text-transform:uppercase;letter-spacing:0.22em;
  font-size:25px;color:#9a9286;margin-top:16px;}
.foot{font-family:'Inter',sans-serif;font-weight:300;text-transform:uppercase;letter-spacing:0.24em;
  font-size:23px;color:#9a9286;line-height:1.5;}
</style></head>
<body>
<div class="glow"></div>
<div class="frame">
  <div class="top"><div class="eyebrow"><!--EYEBROW--></div><div class="hairline"></div></div>
  <div class="mid"><!--MID--></div>
  <div class="foot"><!--FOOTER--></div>
</div>
<div class="grain"></div>
</body></html>"""

CARDS = [
    dict(name="card1_hook",
         eyebrow='PSYCHE<span class="dot"> &middot; </span><span class="greek">ψυχή</span>',
         mid='<div class="main" style="font-size:100px">'
             '<span class="line">One test passed only</span>'
             '<span class="line">because I had hidden</span>'
             '<span class="line">the answer inside it.</span></div>'
             '<div class="subitalic" style="font-size:62px;margin-top:48px">'
             'Finding that was the point.</div>',
         footer="A different bet on machine memory"),

    dict(name="card2_contrast",
         eyebrow='PSYCHE<span class="dot"> &middot; </span><span class="greek">ψυχή</span>',
         mid='<div class="main" style="font-size:84px">'
             '<span class="line">Most systems are shown</span>'
             '<span class="line">by their best demo.</span>'
             '<span class="gap"></span>'
             '<span class="line">I would rather show you</span>'
             '<span class="line">where mine <em>breaks.</em></span></div>',
         footer="An inspectable memory substrate.<br>Write-up in comments."),

    dict(name="card3_receipts",
         eyebrow='VERIFIED<span class="dot"> &middot; </span><span class="greek">ψυχή</span>',
         mid='<div class="stats">'
             '<div class="stat"><div class="num">130</div>'
             '<div class="lbl">Adversarial tests. Zero failures.</div></div>'
             '<div class="stat"><div class="num">6</div>'
             '<div class="lbl">Structural bugs caught and fixed.</div></div>'
             '<div class="stat"><div class="num">0</div>'
             '<div class="lbl">Third-party dependencies.</div></div></div>'
             '<div class="subitalic" style="font-size:48px;margin-top:50px">'
             'Honest about what is not yet proven.</div>',
         footer="PSYCHE"),

    dict(name="card4_premise",
         eyebrow='PSYCHE<span class="dot"> &middot; </span><span class="greek">ψυχή</span>',
         mid='<div class="main" style="font-size:86px">'
             '<span class="line">A different bet on</span>'
             '<span class="line">machine memory.</span>'
             '<span class="gap"></span>'
             '<span class="line"><em>Structure you can trace,</em></span>'
             '<span class="line">not knowledge baked</span>'
             '<span class="line">into weights.</span></div>',
         footer="Built test-first. Code and report in comments."),
]

# --------------------------------------------------------------------------
# 3) build + render
# --------------------------------------------------------------------------
def main():
    print("fetching + embedding brand fonts ...")
    fontfaces = build_fontfaces()

    paths = []
    for c in CARDS:
        html = (TEMPLATE
                .replace("/*FONTFACES*/", fontfaces)
                .replace("<!--EYEBROW-->", c["eyebrow"])
                .replace("<!--MID-->", c["mid"])
                .replace("<!--FOOTER-->", c["footer"]))
        html_path = os.path.join(HERE, c["name"] + ".html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        raw = os.path.join(HERE, c["name"] + ".2x.png")
        subprocess.run([
            CHROME, "--no-sandbox", "--hide-scrollbars",
            "--force-device-scale-factor=2", "--window-size=1200,1200",
            "--default-background-color=0a0908ff",
            "--screenshot=" + raw, "file://" + html_path,
        ], check=True, capture_output=True, timeout=90)

        img = Image.open(raw).convert("RGB")
        if img.size != (1200, 1200):
            img = img.resize((1200, 1200), Image.LANCZOS)
        out = os.path.join(HERE, c["name"] + ".png")
        img.save(out, "PNG")
        os.remove(raw)
        paths.append(out)
        print("wrote", out, img.size)
    return paths


if __name__ == "__main__":
    for p in main():
        print(p)
