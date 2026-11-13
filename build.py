#!/usr/bin/env python3
"""Crown Masters Adventures — static site generator (demo v2).

  python3 build.py               demo build: links end in index.html, works from a folder or zip
  python3 build.py --production  clean URLs (/venues/) for deployment
Output goes to ./site
"""
import base64, hashlib, html, json, os, re, sys, shutil
from data import DOMAIN, UPDATED, UPDATED_TEXT, BUSINESS as B, REGIONS, CORRECTIONS, CLIENTS

PROD = "--production" in sys.argv
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "site")
E = lambda s: html.escape(str(s), quote=True)
TOTAL = sum(len(r["venues"]) for r in REGIONS)
for r in REGIONS:
    r["count"] = len(r["venues"])

# ------------------------------------------------------------------ paths
def file_of(p):
    p = p.split("#")[0]
    last = p.rstrip("/").rsplit("/", 1)[-1]
    if "." in last and not p.endswith("/"):
        return p.lstrip("/")
    return (p.strip("/") + "/index.html").lstrip("/")

def link(target, here):
    """Relative link from page `here` (production path) to `target` (production path)."""
    if target.startswith(("http", "mailto:", "tel:")):
        return target
    anchor = ("#" + target.split("#", 1)[1]) if "#" in target else ""
    if PROD:
        return target.split("#")[0] + anchor
    rel = os.path.relpath(file_of(target), os.path.dirname(file_of(here)) or ".")
    return rel + anchor

# ------------------------------------------------------------------ schema
ORG_ID = DOMAIN + "/#business"
def org():
    o = {"@type": ["LocalBusiness", "TravelAgency"], "@id": ORG_ID, "name": B["name"],
         "alternateName": "Crownmasters Adventures", "url": DOMAIN + "/",
         "logo": DOMAIN + "/assets/logo.svg", "image": DOMAIN + "/assets/og-default.jpg",
         "description": f"Nairobi-based corporate team building company: facilitated team building events, booking of {TOTAL} team building venues across Kenya, Tanzania and Uganda, corporate fitness and group transport.",
         "telephone": B["phone"], "email": B["email"],
         "address": {"@type": "PostalAddress", "streetAddress": B["street"], "addressLocality": B["city"], "addressCountry": B["country"]},
         "areaServed": [{"@type": "Country", "name": n} for n in ("Kenya", "Tanzania", "Uganda")],
         "sameAs": list(B["social"].values()),
         "contactPoint": {"@type": "ContactPoint", "telephone": B["phone"], "email": B["email"], "contactType": "sales",
                          "availableLanguage": ["English", "Swahili"]},
         "knowsAbout": ["Corporate team building", "Team building facilitation", "Team building venues in Kenya",
                        "Corporate fitness", "Corporate retreats", "Group transport"]}
    if B["geo"]:
        o["geo"] = {"@type": "GeoCoordinates", "latitude": B["geo"]["lat"], "longitude": B["geo"]["lng"]}
    if B["opening_hours"]:
        o["openingHours"] = B["opening_hours"]
    if B["founded"]:
        o["foundingDate"] = str(B["founded"])
    return o

def ld(*objs):
    g = {"@context": "https://schema.org", "@graph": [org(), {"@type": "WebSite", "@id": DOMAIN + "/#website",
         "url": DOMAIN + "/", "name": B["name"], "inLanguage": "en-KE", "publisher": {"@id": ORG_ID}}, *objs]}
    return '<script type="application/ld+json">' + json.dumps(g, ensure_ascii=False, separators=(",", ":")) + "</script>"

def crumbs_ld(items):
    return {"@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + p} for i, (n, p) in enumerate(items)]}

def faq_ld(faqs, path):
    return {"@type": "FAQPage", "@id": DOMAIN + path + "#faq", "mainEntity": [
        {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]}

def service_ld(path, name, stype, desc):
    return {"@type": "Service", "@id": DOMAIN + path + "#service", "name": name, "serviceType": stype,
            "description": desc, "provider": {"@id": ORG_ID}, "url": DOMAIN + path,
            "areaServed": [{"@type": "Country", "name": "Kenya"}]}

def page_ld(path, name, typ="WebPage"):
    return {"@type": typ, "@id": DOMAIN + path + "#webpage", "url": DOMAIN + path, "name": name,
            "isPartOf": {"@id": DOMAIN + "/#website"}, "about": {"@id": ORG_ID}, "dateModified": UPDATED, "inLanguage": "en-KE"}

# ------------------------------------------------------------------ design
# ------------------------------------------------------------------ themes
# Three premium palettes. Navy is the default; preview another with
#   python3 build.py --theme=emerald   (or --theme=savanna)
# Token order: ink, ink-2, paper, card, line, soft, gold (accent), on-gold, gold-ink (accent as text),
# grass (links / secondary), grass-2 (tint), deep (dark bands, header, footer), deep-2, on-deep, gold-on-deep
_T = "ink ink-2 paper card line soft gold on-gold gold-ink grass grass-2 deep deep-2 on-deep gold-on-deep".split()
THEMES = {
    "emerald": {  # Emerald and brass: deep forest green, warm ivory, brushed gold
        "light": "#13231D #4A5A53 #FAF7F1 #FFFFFF #E3DCCE #F3EEE3 #C6A15B #1B1505 #76571A #1D5C46 #E7EFE9 #0E2A22 #153A2F #F4EFE3 #D8B877",
        "dark":  "#EEE9DC #B4BDB4 #0A1612 #11221C #25392F #152A22 #D4B26C #1B1505 #D4B26C #86C5A6 #173127 #12291F #1A3A2D #F4EFE3 #D8B877"},
    "navy": {     # Midnight navy and champagne gold: the classic corporate-premium pairing
        "light": "#111B2E #4D586B #F8F6F2 #FFFFFF #DFDBD1 #F0EDE6 #C9A45C #1A1405 #74561A #1F4A7A #E7EDF5 #0D1A33 #162848 #F3EEE2 #DBBB7A",
        "dark":  "#ECE9E1 #B0B7C4 #090F1D #111B30 #25324A #152039 #D6B570 #1A1405 #D6B570 #8FB6E6 #17253F #121E38 #1B2B4D #F3EEE2 #DBBB7A"},
    "savanna": {  # Charcoal, sand and terracotta: warmer and earthier, still restrained
        "light": "#1E1B18 #5A534C #F8F3EC #FFFFFF #E3D9CB #F1E9DD #B5522D #FFFFFF #8E3D1E #46522A #ECEEDD #26211C #352E27 #F5EDE0 #EBA785",
        "dark":  "#F0E9DF #BDB3A7 #141110 #1E1A17 #37302A #231E1A #DB7A50 #1A0C05 #EBA785 #B9C58A #2A2D1C #241F1B #332C26 #F5EDE0 #EBA785"},
}
THEME = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--theme=")), "navy")
if THEME not in THEMES:
    sys.exit(f"Unknown theme {THEME!r}. Choose from: {', '.join(THEMES)}")
def _tokens(mode):
    return ";".join(f"--{k}:{v}" for k, v in zip(_T, THEMES[THEME][mode].split()))
_LIGHT = _tokens("light") + ";color-scheme:light;--focus:#1D5FD1;--warn-bg:#FFF6DD;--warn-line:#E6C568;--hdr:72px;--r:14px;--shadow:0 1px 2px rgba(16,24,20,.05),0 14px 34px -14px rgba(16,24,20,.16)"
_DARK = _tokens("dark") + ";color-scheme:dark;--focus:#8AB4FF;--warn-bg:#2E2712;--warn-line:#8A6B1E;--shadow:none"
DEEP = THEMES[THEME]["light"].split()[_T.index("deep")]
ACCENT = THEMES[THEME]["light"].split()[_T.index("gold")]

CSS = (":root{" + _LIGHT + "}\n@media (prefers-color-scheme:dark){:root:not([data-theme=\"light\"]){" + _DARK + "}}\n:root[data-theme=\"dark\"]{" + _DARK + "}\n") + r"""
[hidden]{display:none!important}*{box-sizing:border-box}html{scroll-behavior:smooth;-webkit-text-size-adjust:100%}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto}*{transition:none!important;animation:none!important}}
body{margin:0;background:var(--paper);color:var(--ink);font:400 1rem/1.7 "Plus Jakarta Sans",system-ui,-apple-system,"Segoe UI",sans-serif;-webkit-font-smoothing:antialiased}
body{font-variation-settings:"SOFT" 100,"WONK" 0}
h1,h2,h3,h4{font-family:"Fraunces",Georgia,"Times New Roman",serif;font-optical-sizing:auto;line-height:1.14;letter-spacing:-.015em;margin:0 0 .5em;text-wrap:balance}
h1{font-size:clamp(2.15rem,5vw,3.9rem);font-weight:500;letter-spacing:-.022em;line-height:1.08}h2{font-size:clamp(1.65rem,3vw,2.35rem);font-weight:500}h3{font-size:1.25rem;font-weight:600;letter-spacing:-.005em}h4{font-size:1.05rem;font-weight:600}
h1 em{font-style:italic;font-weight:400;color:var(--gold-ink)}.hero h1 em{color:var(--gold-on-deep)}
.eyebrow{display:flex;align-items:center;gap:12px;font:700 .74rem/1.3 "Plus Jakarta Sans",sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--gold-ink);margin:0 0 18px}.eyebrow::before{content:"";width:32px;height:1px;background:currentColor;flex:none}
p{margin:0 0 1em;max-width:68ch}ul,ol{max-width:68ch}
a{color:var(--grass);overflow-wrap:anywhere;text-underline-offset:.18em;text-decoration-thickness:1px}a:hover{color:var(--ink)}
:focus-visible{outline:3px solid var(--focus);outline-offset:2px}
img,svg{max-width:100%}
.wrap{max-width:1200px;margin:0 auto;padding:0 max(16px,env(safe-area-inset-right)) 0 max(16px,env(safe-area-inset-left))}
@media (min-width:760px){.wrap{padding:0 max(32px,env(safe-area-inset-right)) 0 max(32px,env(safe-area-inset-left))}}
.narrow{max-width:760px}
.skip{position:absolute;left:-999px}.skip:focus{left:16px;top:8px;background:var(--card);padding:8px 12px;z-index:20}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}
/* header */
header.site{position:sticky;top:0;z-index:10;background:var(--deep);color:var(--on-deep);border-bottom:1px solid color-mix(in srgb,var(--gold-on-deep) 38%,transparent)}
header.site :focus-visible,footer :focus-visible,.hero :focus-visible,.cta :focus-visible{outline-color:var(--gold-on-deep)}
.bar{display:flex;align-items:center;gap:12px;min-height:var(--hdr)}
.brand{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--on-deep);font:600 1.18rem/1.1 "Fraunces",Georgia,serif;letter-spacing:.005em;margin-right:auto}
.brand:hover{color:var(--on-deep)}
.brand small{display:block;font:600 .66rem "Plus Jakarta Sans",sans-serif;color:var(--gold-on-deep);letter-spacing:.2em;text-transform:uppercase;margin-top:4px}
.nav{display:flex;list-style:none;margin:0;padding:0;gap:2px}
.nav>li{position:relative}
.nav a,.nav .top{display:block;padding:10px 10px;border-radius:8px;text-decoration:none;color:var(--on-deep);font-weight:600;font-size:.92rem;white-space:nowrap}
.nav a:hover,.nav .top:hover{color:var(--gold-on-deep)}
.nav [aria-current="page"],.nav .here>.top{color:var(--gold-on-deep);box-shadow:inset 0 -2px 0 var(--gold-on-deep);border-radius:0}
.sub{display:none;position:absolute;left:0;top:100%;min-width:260px;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:8px;list-style:none;margin:0;box-shadow:var(--shadow)}
.nav>li:hover>.sub,.nav>li:focus-within>.sub{display:block}
.sub a{font-weight:500;white-space:normal}
@media (min-width:1021px){.sub a{color:var(--ink)}.sub a:hover{background:var(--soft);color:var(--ink)}.sub [aria-current="page"]{color:var(--grass);box-shadow:none;border-radius:8px}}
.shortlist{display:inline-flex;align-items:center;gap:6px;padding:7px 12px;border-radius:999px;border:1px solid color-mix(in srgb,var(--on-deep) 30%,transparent);text-decoration:none;color:var(--on-deep);font-weight:700;font-size:.95rem}
.shortlist:hover{color:var(--on-deep)}
.shortlist b{background:var(--gold);color:var(--on-gold);border-radius:999px;min-width:22px;height:22px;display:inline-grid;place-items:center;font-size:.8rem}
.shortlist[data-n="0"]{display:none}@media (max-width:600px){.shortlist .sl-t{display:none}}@media (max-width:380px){.brand small{display:none}}
.menu-btn{display:none;background:transparent;border:1px solid color-mix(in srgb,var(--on-deep) 35%,transparent);border-radius:8px;padding:9px 14px;min-height:44px;color:var(--on-deep);font:700 .95rem "Plus Jakarta Sans",sans-serif;letter-spacing:.04em;cursor:pointer}
@media (max-width:1020px){.menu-btn{display:block}.navwrap{display:none;position:absolute;left:0;right:0;top:100%;background:var(--deep);border-bottom:1px solid color-mix(in srgb,var(--gold-on-deep) 38%,transparent);max-height:calc(100vh - var(--hdr));max-height:calc(100dvh - var(--hdr));overflow:auto;overscroll-behavior:contain;padding:8px max(16px,env(safe-area-inset-right)) 20px max(16px,env(safe-area-inset-left))}.navwrap.open{display:block}.nav{flex-direction:column}.nav a,.nav .top{padding:12px}.sub{display:block;position:static;border:0;box-shadow:none;padding:0 0 8px 12px;background:none}.sub a{color:color-mix(in srgb,var(--on-deep) 82%,transparent)}.bar .hdr-cta{display:none}}
/* phones held sideways: use the width, two menu columns */
@media (max-width:1020px) and (min-width:600px) and (orientation:landscape){.nav{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:4px 16px;align-items:start}}
/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;padding:13px 26px;min-height:48px;border-radius:8px;font:700 .95rem "Plus Jakarta Sans",sans-serif;letter-spacing:.01em;text-decoration:none;border:1.5px solid transparent;cursor:pointer;line-height:1.2;transition:background-color .18s,color .18s,border-color .18s,transform .18s,box-shadow .18s}
.btn-gold{background:var(--gold);color:var(--on-gold);box-shadow:0 1px 0 rgba(255,255,255,.25) inset,0 8px 20px -10px color-mix(in srgb,var(--gold) 80%,transparent)}.btn-gold:hover{filter:brightness(1.07);color:var(--on-gold);transform:translateY(-1px)}
.btn-line{border-color:color-mix(in srgb,currentColor 55%,transparent);color:var(--ink);background:transparent}.btn-line:hover{border-color:currentColor}
.btn-sm{padding:8px 16px;min-height:40px;font-size:.92rem}
.btn[disabled]{opacity:.45;cursor:not-allowed}
.actions{display:flex;gap:12px;flex-wrap:wrap;margin-top:24px}
/* layout */
section{padding:clamp(56px,7.5vw,96px) 0}section.tight{padding:clamp(32px,4vw,48px) 0}
.band{background:var(--soft);border-block:1px solid var(--line)}.band-ink{background:var(--deep);color:var(--on-deep)}.band-ink a{color:var(--gold-on-deep)}
/* home hero */
.hero{background:radial-gradient(120% 140% at 85% 0%,var(--deep-2) 0%,var(--deep) 62%);color:var(--on-deep);padding:clamp(40px,6vw,88px) 0 clamp(48px,6.5vw,96px)}
.hero .eyebrow{color:var(--gold-on-deep)}.hero .lede,.hero .muted{color:color-mix(in srgb,var(--on-deep) 80%,transparent)}.hero a:not(.btn){color:var(--gold-on-deep)}.hero .btn-line{color:var(--on-deep)}
.hero .ph{border-color:color-mix(in srgb,var(--gold-on-deep) 40%,transparent);background:linear-gradient(135deg,color-mix(in srgb,var(--on-deep) 12%,var(--deep)),var(--deep-2));box-shadow:0 30px 60px -30px rgba(0,0,0,.55)}
.hero .ph::before{background:repeating-linear-gradient(-45deg,transparent 0 14px,color-mix(in srgb,var(--on-deep) 6%,transparent) 14px 15px)}.hero .ph svg.mtn path{fill:var(--gold-on-deep)}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:40px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px}
.grid4{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:20px}
@media (max-width:960px){.grid4{grid-template-columns:repeat(2,minmax(0,1fr))}.grid3{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:700px){.grid2,.grid3,.grid4{grid-template-columns:minmax(0,1fr)}}
.split{display:grid;grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr);gap:clamp(28px,4.5vw,64px);align-items:center}
@media (max-width:900px){.split{grid-template-columns:minmax(0,1fr)}.split>.ph,.split>.ph.tall{aspect-ratio:16/9}}
/* phones held sideways keep the hero side by side instead of stacking a huge photo */
@media (max-width:900px) and (min-width:620px) and (orientation:landscape){.hero .split,.page-head .split{grid-template-columns:minmax(0,1.25fr) minmax(0,.75fr);gap:24px}.hero .split>.ph,.page-head .split>.ph{aspect-ratio:4/3}}
.lede{font-size:clamp(1.06rem,1.5vw,1.18rem);color:var(--ink-2);max-width:58ch}
.muted{color:var(--ink-2)}.small{font-size:.92rem}
.crumbs{font-size:.92rem;color:var(--ink-2);padding-top:20px}
.crumbs ol{list-style:none;display:flex;flex-wrap:wrap;gap:6px;padding:0;margin:0}
.crumbs li+li::before{content:"/";margin-right:6px;color:var(--line)}
.crumbs a{color:var(--ink-2)}
.page-head{padding:24px 0 40px}
/* answer box */
.answer{border:1px solid var(--line);border-left:3px solid var(--gold);background:var(--card);padding:18px 22px;border-radius:0 var(--r) var(--r) 0;margin:24px 0;max-width:72ch;box-shadow:var(--shadow)}
.answer p{margin:0}
/* to-confirm flags */
.confirm{display:flex;gap:12px;background:var(--warn-bg);border:1px solid var(--warn-line);border-radius:12px;padding:12px 16px;font-size:.95rem;margin:16px 0;max-width:72ch}
.confirm::before{content:"!";flex:none;display:grid;place-items:center;width:22px;height:22px;border-radius:50%;background:var(--warn-line);color:#1C1400;font-weight:800}
.tbc{display:inline-block;font-size:.78rem;font-weight:700;color:var(--gold-ink);background:var(--warn-bg);border:1px solid var(--warn-line);border-radius:999px;padding:1px 8px;white-space:nowrap}
/* photo slots */
.ph{position:relative;border-radius:var(--r);overflow:hidden;background:linear-gradient(135deg,var(--grass-2),var(--soft));aspect-ratio:4/3;display:flex;align-items:flex-end;border:1px solid var(--line)}
.ph::before{content:"";position:absolute;inset:0;background:repeating-linear-gradient(-45deg,transparent 0 14px,color-mix(in srgb,var(--grass) 7%,transparent) 14px 15px)}
.ph svg.mtn{position:absolute;inset:auto 0 0 0;width:100%;height:55%;opacity:.5}
.ph figcaption{position:relative;margin:16px;background:var(--card);border-radius:10px;padding:8px 12px;font-size:.88rem;color:var(--ink-2);box-shadow:var(--shadow)}
.ph figcaption b{color:var(--ink)}
.ph.has-img::before{display:none}.ph img{position:absolute;inset:0;width:100%;height:100%;object-fit:cover}
.ph .wm{position:absolute;inset:0;display:grid;place-items:center;font:700 clamp(1.1rem,3.2vw,2.2rem) "Plus Jakarta Sans",sans-serif;letter-spacing:.3em;text-transform:uppercase;color:rgba(255,255,255,.82);text-shadow:0 1px 10px rgba(0,0,0,.55);transform:rotate(-18deg);pointer-events:none}
/* home hero with a photo slideshow behind the headline */
.hero-bg{position:relative;overflow:hidden;isolation:isolate;display:flex;align-items:center;min-height:clamp(540px,82vh,800px);padding:clamp(48px,7vw,96px) 0 clamp(72px,8vw,104px)}
.hero-bg>.wrap{position:relative;z-index:3;width:100%}
.hero-text{max-width:660px}.hero-bg h1,.hero-bg .lede{text-shadow:0 2px 24px rgba(0,0,0,.35)}
.hero-bg .lede{color:color-mix(in srgb,var(--on-deep) 92%,transparent)}
.hero-slides,.hero-scrim{position:absolute;inset:0}.hero-slides{z-index:0;background:var(--deep)}
.hero-slide{position:absolute;inset:0;opacity:0;transition:opacity 1.6s cubic-bezier(.4,0,.2,1)}.hero-slide.on{opacity:1}
.hero-slide img{width:100%;height:100%;object-fit:cover;transform:scale(1.14);transition:transform 9s cubic-bezier(.2,.6,.2,1);transform-origin:70% 40%}
.hero-slide:nth-child(even) img{transform-origin:30% 60%}.hero-slide.on img{transform:scale(1.02)}
.hero-scrim{z-index:1;background:linear-gradient(90deg,color-mix(in srgb,var(--deep) 94%,transparent) 0%,color-mix(in srgb,var(--deep) 82%,transparent) 42%,color-mix(in srgb,var(--deep) 30%,transparent) 100%),linear-gradient(to top,color-mix(in srgb,var(--deep) 75%,transparent) 0%,transparent 34%)}
.hero-wm{position:absolute;z-index:2;right:6%;top:42%;font:700 clamp(1rem,2.6vw,2rem) "Plus Jakarta Sans",sans-serif;letter-spacing:.32em;text-transform:uppercase;color:rgba(255,255,255,.55);text-shadow:0 1px 10px rgba(0,0,0,.5);transform:rotate(-14deg);pointer-events:none}
.hero-ctl{display:flex;align-items:center;gap:16px;flex-wrap:wrap;margin-top:clamp(28px,5vw,56px)}
.hero-dots{display:flex;gap:8px}
.hero-dot{position:relative;width:44px;height:28px;padding:0;background:none;border:0;cursor:pointer}
.hero-dot::before,.hero-dot i{content:"";position:absolute;left:0;top:13px;height:2px;border-radius:2px}
.hero-dot::before{width:100%;background:color-mix(in srgb,var(--on-deep) 35%,transparent)}
.hero-dot i{width:0;background:var(--gold-on-deep)}.hero-dot[aria-current] i{width:100%}.hero-bg.run .hero-dot[aria-current] i{animation:show-fill 6s linear both}
.hero-note{font-size:.78rem;color:color-mix(in srgb,var(--on-deep) 75%,transparent);margin-left:auto}
@media (max-width:900px){.hero-scrim{background:linear-gradient(to top,color-mix(in srgb,var(--deep) 96%,transparent) 0%,color-mix(in srgb,var(--deep) 82%,transparent) 55%,color-mix(in srgb,var(--deep) 70%,transparent) 100%)}.hero-wm{display:none}.hero-note{margin-left:0;flex-basis:100%}}
@media (max-width:760px){.hero-bg{min-height:0}}
@media (max-height:520px) and (orientation:landscape){.hero-bg{min-height:0;padding:28px 0 32px}.hero-ctl{margin-top:16px}}
@media (pointer:coarse){.hero-dot{height:44px}.hero-dot::before,.hero-dot i{top:21px}}
/* hero collage: one large photo, two small; still, no motion */
.collage{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(0,1fr);grid-template-rows:repeat(2,minmax(0,1fr));gap:12px;aspect-ratio:1/1}
.collage .ph{aspect-ratio:auto;height:100%;min-height:0}.collage .ph:first-child{grid-row:1/3}
.collage .ph figcaption{margin:10px;padding:0 10px;border-block:6px solid var(--card);font-size:.76rem;line-height:1.4;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:3;overflow:hidden}
.collage .ph .wm{font-size:clamp(.7rem,1.6vw,1.1rem)}
@media (max-width:900px){.collage{aspect-ratio:16/11}.collage .ph:not(:first-child) figcaption{-webkit-line-clamp:2}}
@media (max-width:900px) and (min-width:620px) and (orientation:landscape){.hero .collage{aspect-ratio:5/4}}
@keyframes show-fill{from{width:0}to{width:100%}}
.ph.wide{aspect-ratio:16/9}.ph.tall{aspect-ratio:4/5}.ph.short{aspect-ratio:21/9}
figure{margin:0}
/* cards */
.card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:28px;box-shadow:var(--shadow);display:flex;flex-direction:column;transition:transform .2s,border-color .2s,box-shadow .2s}
.card h3 a{color:var(--ink);text-decoration:none}.card h3 a::after{content:"";position:absolute;inset:0}
.card.link{position:relative}.card.link:hover{border-color:var(--gold);transform:translateY(-3px)}
.card .meta{margin-top:auto;padding-top:12px;font-size:.92rem;color:var(--ink-2)}
.icon{width:48px;height:48px;border-radius:10px;background:var(--deep);display:grid;place-items:center;margin-bottom:20px;color:var(--gold-on-deep)}
/* trust */
/* client strip: one row, slow loop, uniform cells */
.cl-head{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:16px}.cl-head .eyebrow{margin:0}
.cl-pause{background:none;border:1px solid var(--line);border-radius:8px;padding:4px 12px;min-height:32px;color:var(--ink-2);font:700 .78rem "Plus Jakarta Sans",sans-serif;letter-spacing:.06em;cursor:pointer}
.clients{overflow:hidden;-webkit-mask-image:linear-gradient(90deg,transparent,#000 7%,#000 93%,transparent);mask-image:linear-gradient(90deg,transparent,#000 7%,#000 93%,transparent)}
.cl-track{display:flex;width:max-content;animation:cl-scroll 90s linear infinite}
.clients:hover .cl-track,.clients.paused .cl-track{animation-play-state:paused}
.cl-track ul{display:flex;gap:12px;list-style:none;margin:0;padding:0 12px 0 0;max-width:none}
.cl-track li{flex:none;display:grid;place-items:center;height:68px;min-width:132px;padding:0 24px;border:1px solid var(--line);border-radius:10px;background:#fff;color:#1B2436;font:700 .95rem "Plus Jakarta Sans",sans-serif;letter-spacing:.01em;white-space:nowrap}
.cl-track img{display:block;height:34px;width:auto;max-width:150px;object-fit:contain;filter:grayscale(1);opacity:.78;transition:filter .25s,opacity .25s}
.cl-track li:hover img{filter:none;opacity:1}
.cl-text{margin:14px 0 0;max-width:none}
@keyframes cl-scroll{to{transform:translateX(-50%)}}
@media (prefers-reduced-motion:reduce){.cl-track{animation:none}.clients{overflow-x:auto;-webkit-mask-image:none;mask-image:none}.cl-track ul[aria-hidden]{display:none}}
@media (pointer:coarse){.cl-pause{min-height:44px}}
.logos{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:12px}
@media (max-width:800px){.logos{grid-template-columns:repeat(3,minmax(0,1fr))}}
.logo-slot{height:64px;border:1px dashed var(--line);border-radius:12px;display:grid;place-items:center;font-size:.8rem;color:var(--ink-2);background:var(--card)}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;margin-top:24px}
@media (max-width:700px){.stats{grid-template-columns:repeat(2,minmax(0,1fr))}}
.stat{border-top:1px solid var(--gold);padding-top:14px;color:var(--ink-2);font-size:.97rem}
.stat b{display:block;font:500 2.3rem/1.15 "Fraunces",Georgia,serif;color:var(--ink);letter-spacing:-.02em}
.rating{display:grid;grid-template-columns:auto minmax(0,1fr) auto;gap:20px 32px;align-items:center;background:var(--card);border:1px solid var(--line);border-top:2px solid var(--gold);border-radius:var(--r);padding:clamp(20px,3vw,32px);box-shadow:var(--shadow);margin-top:20px}
@media (max-width:760px){.rating{grid-template-columns:auto minmax(0,1fr)}.rating .actions{grid-column:1/-1}}
.rating-score b{display:block;font:500 clamp(3rem,6vw,4.2rem)/1 "Fraunces",Georgia,serif;letter-spacing:-.03em}.rating-score span{font-size:.85rem;color:var(--ink-2)}
.stars{display:flex;gap:2px;color:var(--gold);margin:0 0 6px}.rating-t{font-weight:600;margin:0 0 2px}
.quote-card{background:var(--card);border:1px solid var(--line);border-top:2px solid var(--gold);border-radius:var(--r);padding:28px;margin:0}
.quote-card{display:flex;flex-direction:column}.quote-card blockquote{margin:0 0 18px;font:400 1.02rem/1.6 "Fraunces",Georgia,serif}.quote-card blockquote.clamp{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:6;overflow:hidden;margin-bottom:10px}
.rv-more{align-self:flex-start;background:none;border:0;padding:6px 0;min-height:32px;margin:0 0 10px;color:var(--grass);font:700 .9rem "Plus Jakarta Sans",sans-serif;text-decoration:underline;text-underline-offset:.18em;cursor:pointer}.rv-more:hover{color:var(--ink)}
@media (pointer:coarse){.rv-more{min-height:44px}}
.quote-card figcaption{margin-top:auto;padding-top:14px;border-top:1px solid var(--line)}.quote-card figcaption b{color:var(--ink)}
.quote-card figcaption{font-size:.92rem;color:var(--ink-2)}
/* drive-time chart */
details.dt{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:0 20px;max-width:920px}
details.dt summary{padding:14px 0;font-size:1.05rem}details.dt>div{padding-bottom:16px}
.dt-list{list-style:none;margin:0;padding:0;max-width:none;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:0 40px}
@media (max-width:760px){.dt-list{grid-template-columns:minmax(0,1fr)}}
.dt-list a{display:flex;justify-content:space-between;align-items:baseline;gap:4px 16px;flex-wrap:wrap;padding:8px 0;border-top:1px solid var(--line);text-decoration:none;color:var(--ink)}
.dt-list a:hover b{color:var(--grass);text-decoration:underline}.dt-list span{font-size:.88rem;color:var(--ink-2)}
/* steps */
.steps{counter-reset:s;list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:24px;max-width:none}
@media (max-width:900px){.steps{grid-template-columns:repeat(2,minmax(0,1fr))}}@media (max-width:520px){.steps{grid-template-columns:minmax(0,1fr)}}
.steps li{counter-increment:s}
.steps li::before{content:counter(s);display:grid;place-items:center;width:44px;height:44px;border-radius:50%;border:1px solid var(--gold);color:var(--gold-ink);font:500 1.2rem "Fraunces",Georgia,serif;margin-bottom:14px}
/* agenda */
.agenda{list-style:none;padding:0;margin:0;border-left:1px solid var(--gold);max-width:none}
.agenda li{display:grid;grid-template-columns:90px minmax(0,1fr);gap:16px;padding:0 0 18px 20px;position:relative}
.agenda li::before{content:"";position:absolute;left:-6px;top:8px;width:11px;height:11px;border-radius:50%;background:var(--gold)}
.agenda time{font-weight:700}
/* tabs */
.tabs [role=tablist]{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px}
.tabs [role=tab]{padding:10px 18px;min-height:44px;border-radius:8px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:700 .95rem "Plus Jakarta Sans",sans-serif;cursor:pointer}
.tabs [role=tab][aria-selected=true]{background:var(--deep);color:var(--on-deep);border-color:var(--deep)}
.tabs [role=tabpanel]{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:24px}
.tabs dl{display:grid;grid-template-columns:200px minmax(0,1fr);gap:12px 24px;margin:0}
@media (max-width:600px){.tabs dl{grid-template-columns:minmax(0,1fr)}}
.tabs dt{font-weight:700}.tabs dd{margin:0}
/* faq */
details{border-top:1px solid var(--line)}details:last-of-type{border-bottom:1px solid var(--line)}
summary{cursor:pointer;padding:20px 0;font:500 1.15rem/1.35 "Fraunces",Georgia,serif;list-style:none;display:flex;justify-content:space-between;gap:16px}
summary::-webkit-details-marker{display:none}
summary::after{content:"+";font:300 1.6rem/1 "Plus Jakarta Sans",sans-serif;color:var(--gold-ink);flex:none}
details[open] summary::after{content:"\2212"}
details>div{padding-bottom:16px}
/* cta */
.cta{background:radial-gradient(120% 160% at 100% 0%,var(--deep-2) 0%,var(--deep) 60%);color:var(--on-deep);border:1px solid color-mix(in srgb,var(--gold-on-deep) 35%,transparent);border-radius:var(--r);padding:clamp(32px,5vw,56px) clamp(20px,4.5vw,56px);display:flex;justify-content:space-between;gap:24px;flex-wrap:wrap;align-items:center}
.cta h2{margin:0 0 .25em}.cta p{margin:0;color:color-mix(in srgb,var(--on-deep) 80%,transparent)}
.cta .btn-line{color:var(--on-deep)}
/* venues */
.finder{position:sticky;top:var(--hdr);z-index:5;background:color-mix(in srgb,var(--paper) 96%,transparent);backdrop-filter:blur(8px);padding:14px 0 10px;border-block:1px solid var(--line)}
.frow{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.frow input[type=search]{flex:1 1 260px;padding:11px 16px;border:1.5px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
.frow select{width:auto;flex:0 1 auto;padding:10px 12px;border-radius:8px}
.chips{display:flex;gap:8px;overflow-x:auto;padding:10px 0 4px;scrollbar-width:thin}
.chip{flex:none;padding:8px 14px;min-height:40px;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--ink);font:600 .93rem "Plus Jakarta Sans",sans-serif;cursor:pointer}
.chip[aria-pressed=true]{background:var(--deep);color:var(--on-deep);border-color:var(--deep)}
.result-count{font-size:.95rem;color:var(--ink-2);margin:8px 0 0}
/* small screens: the filter bar must not eat the screen */
@media (max-width:760px){.finder{padding:10px 0 6px}.frow{gap:8px}.frow input[type=search]{flex:1 1 100%}.frow select{flex:1 1 0;min-width:0}.frow select[disabled]{display:none}.chips{padding:8px 0 2px}.result-count{font-size:.85rem;margin:2px 0 0}}
@media (max-height:520px) and (orientation:landscape){.finder{position:static}.frow input[type=search]{flex:1 1 220px}.frow select{flex:0 1 auto}}
.region{padding:44px 0;border-bottom:1px solid var(--line);scroll-margin-top:calc(var(--hdr) + 150px)}
.region-head{display:flex;justify-content:space-between;align-items:baseline;gap:16px;flex-wrap:wrap}
.region-head h2{font-size:clamp(1.35rem,2.4vw,1.8rem);margin:0}
.tags{display:flex;gap:8px;flex-wrap:wrap;margin:10px 0 14px}
.tag{font-size:.85rem;font-weight:600;padding:3px 10px;border-radius:999px;background:var(--soft);border:1px solid var(--line)}
.vgrid{list-style:none;padding:0;margin:0;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;max-width:none}
@media (max-width:900px){.vgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}@media (max-width:560px){.vgrid{grid-template-columns:minmax(0,1fr)}}
.vcard{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px 14px;display:flex;justify-content:space-between;align-items:center;gap:10px}
.vcard .vn{font-weight:700;line-height:1.3}
.vcard .vs{display:block;font-size:.85rem;color:var(--ink-2);font-weight:400}
.add{flex:none;border:1px solid var(--line);background:var(--paper);color:var(--ink);border-radius:8px;padding:8px 12px;min-height:40px;font:700 .85rem "Plus Jakarta Sans",sans-serif;cursor:pointer;white-space:nowrap}
.add[aria-pressed=true]{background:var(--deep);border-color:var(--deep);color:var(--on-deep)}
.empty{display:none;padding:32px 0}
/* forms */
label{display:block;font-weight:700;margin-bottom:6px}
input,select,textarea{width:100%;padding:12px 14px;border:1.5px solid var(--line);border-radius:8px;background:var(--card);color:var(--ink);font:inherit}
input:focus,select:focus,textarea:focus{border-color:var(--grass);outline:none;box-shadow:0 0 0 3px color-mix(in srgb,var(--grass) 25%,transparent)}
.hint{font-size:.9rem;color:var(--ink-2);margin:4px 0 0}
.err{color:#B3261E;font-size:.9rem;font-weight:700;margin:6px 0 0;min-height:1.2em}
.fgrid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
@media (max-width:600px){.fgrid2{grid-template-columns:minmax(0,1fr)}}
.full{grid-column:1/-1}
.radio-cards{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
@media (max-width:600px){.radio-cards{grid-template-columns:minmax(0,1fr)}}
.radio-cards label{border:1.5px solid var(--line);border-radius:10px;padding:14px 16px;cursor:pointer;background:var(--card);margin:0;display:grid;grid-template-columns:auto minmax(0,1fr);gap:3px 12px;align-items:center;align-content:center;min-height:76px;transition:border-color .15s,background-color .15s}
.radio-cards label:hover{border-color:var(--gold)}.radio-cards b{font-weight:700;line-height:1.25}
.radio-cards input{width:18px;height:18px;margin:0;accent-color:var(--grass)}
.radio-cards label:has(input:checked){border-color:var(--grass);background:var(--grass-2)}
.radio-cards small{grid-column:2;font-size:.86rem;line-height:1.35;font-weight:400;color:var(--ink-2)}
@media (max-width:1100px) and (min-width:901px){.radio-cards{grid-template-columns:minmax(0,1fr)}.radio-cards label{min-height:0}}
.chk{display:flex;align-items:center;gap:10px;font-weight:500;margin:10px 0 0}.chk input{width:18px;height:18px;flex:none;accent-color:var(--grass)}
.sent{text-align:left}.sent .tick{width:56px;height:56px;border-radius:50%;display:grid;place-items:center;background:var(--grass-2);color:var(--grass);margin-bottom:16px}
.wizard{background:var(--card);border:1px solid var(--line);border-top:2px solid var(--gold);border-radius:var(--r);padding:clamp(20px,3.2vw,36px);box-shadow:var(--shadow)}
@media (max-width:600px){.wizard{padding:20px 16px}}
.progress{display:flex;gap:6px;list-style:none;padding:0;margin:0 0 24px;max-width:none}
.progress li{flex:1;font-size:.8rem;font-weight:700;letter-spacing:.04em;color:var(--ink-2);border-top:3px solid var(--line);padding-top:8px}
.progress li.on{color:var(--ink);border-color:var(--gold)}
.progress li.done{border-color:var(--grass)}
.wstep[hidden]{display:none}
.wnav{display:flex;justify-content:space-between;gap:12px;margin-top:24px;flex-wrap:wrap}
.review{background:var(--soft);border-radius:12px;padding:16px;white-space:pre-wrap;font:inherit;font-size:.95rem;margin:0}
.picked{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.picked span{background:var(--grass-2);border-radius:999px;padding:4px 10px;font-size:.9rem;font-weight:600}
dl.nap{display:grid;grid-template-columns:auto minmax(0,1fr);gap:10px 20px;margin:0}
dl.nap dt{font-weight:700}dl.nap dd{margin:0}
.map{border:0;width:100%;aspect-ratio:4/3;border-radius:var(--r);background:var(--soft)}
/* checklist + planner */
.check{list-style:none;padding:0;max-width:none}
.check li{display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid var(--line)}
.check input{width:20px;height:20px;margin-top:3px;flex:none;accent-color:var(--grass)}
.check label{font-weight:500;margin:0}
.check input:checked+label{color:var(--ink-2);text-decoration:line-through}
.planner{background:var(--card);border:1px solid var(--line);border-radius:var(--r);padding:clamp(20px,3vw,28px)}
.ptotal{background:var(--deep);color:var(--on-deep);border-radius:10px;padding:20px;margin-top:20px;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.ptotal b{display:block;color:var(--gold-on-deep);font:500 1.8rem "Fraunces",Georgia,serif}
/* article */
.prose{max-width:720px}.prose h2{margin-top:1.6em;font-size:1.7rem}.prose li{margin:.35em 0}
.byline{font-size:.95rem;color:var(--ink-2);display:flex;gap:16px;flex-wrap:wrap;margin-bottom:24px}
.toc{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 20px;margin:24px 0}
.toc ol{margin:8px 0 0;padding-left:1.2em}
table.t{border-collapse:collapse;width:100%;font-size:.97rem;margin:16px 0}
table.t th,table.t td{text-align:left;padding:10px 12px;border-bottom:1px solid var(--line);vertical-align:top}
table.t th{font:700 .8rem "Plus Jakarta Sans",sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2);background:var(--soft)}
.tscroll{overflow-x:auto}
/* footer */
footer{border-top:1px solid color-mix(in srgb,var(--gold-on-deep) 38%,transparent);padding:clamp(48px,6vw,80px) 0 110px;font-size:.97rem;color:color-mix(in srgb,var(--on-deep) 74%,transparent);background:var(--deep)}
footer h2{font:700 .78rem "Plus Jakarta Sans",sans-serif;letter-spacing:.16em;text-transform:uppercase;color:var(--gold-on-deep);margin-bottom:16px}
footer .fcols>div:first-child h2{font:500 1.35rem "Fraunces",Georgia,serif;letter-spacing:0;text-transform:none;color:var(--on-deep)}
footer ul{list-style:none;padding:0;margin:0}footer li{margin:8px 0}footer a{color:color-mix(in srgb,var(--on-deep) 82%,transparent);text-decoration:none}footer a:hover{color:var(--gold-on-deep);text-decoration:underline}
.fcols{display:grid;grid-template-columns:minmax(0,2.15fr) repeat(3,minmax(0,1.05fr)) minmax(0,.8fr);gap:28px}.fcols>div{min-width:0}footer address a{overflow-wrap:anywhere}
footer .social{display:flex;flex-wrap:wrap;gap:8px;max-width:160px}footer .social li{margin:0}
footer .social a{display:grid;place-items:center;width:38px;height:38px;padding:0;border-radius:50%;border:1px solid color-mix(in srgb,var(--gold-on-deep) 45%,transparent);color:var(--on-deep);transition:background-color .18s,color .18s,border-color .18s,transform .18s}
footer .social a:hover{background:var(--gold);border-color:var(--gold);color:var(--on-gold);transform:translateY(-2px);text-decoration:none}
@media (max-width:960px){.fcols{grid-template-columns:repeat(2,minmax(0,1fr))}}@media (max-width:480px){.fcols{grid-template-columns:minmax(0,1fr)}}
@media (max-width:960px) and (min-width:620px) and (orientation:landscape){.fcols{grid-template-columns:repeat(3,minmax(0,1fr))}}
.legal{margin-top:40px;padding-top:20px;border-top:1px solid color-mix(in srgb,var(--on-deep) 16%,transparent);display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;font-size:.88rem}
.wa{position:fixed;right:max(16px,env(safe-area-inset-right));bottom:max(16px,env(safe-area-inset-bottom));z-index:9;background:#1E8F4E;color:#fff;border-radius:999px;padding:12px 18px;min-height:48px;font-weight:700;text-decoration:none;box-shadow:0 10px 24px -8px rgba(0,0,0,.45);display:flex;gap:8px;align-items:center}
.wa:hover{color:#fff;background:#18773F}
@media (max-width:600px),(max-height:520px){.wa{padding:0;width:52px;height:52px;justify-content:center}.wa span{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0)}.wa svg{width:26px;height:26px}}
.consent{position:fixed;left:max(16px,env(safe-area-inset-left));bottom:max(16px,env(safe-area-inset-bottom));z-index:12;max-width:min(560px,calc(100vw - 100px));background:var(--card);color:var(--ink);border:1px solid var(--line);border-top:2px solid var(--gold);border-radius:var(--r);padding:16px 18px;box-shadow:0 18px 40px -16px rgba(0,0,0,.45);font-size:.9rem}
.consent p{margin:0 0 12px;max-width:none}.consent-btns{display:flex;gap:10px;flex-wrap:wrap}.consent-btns .btn{flex:1 1 120px}
.cookie-settings{background:none;border:0;padding:0;color:inherit;font:inherit;text-decoration:underline;cursor:pointer}.cookie-settings:hover{color:var(--gold-on-deep)}
.demo-ribbon{background:var(--soft);color:var(--ink-2);font-size:.85rem;text-align:center;padding:6px 16px;border-bottom:1px solid var(--line)}
.demo-ribbon a{color:var(--grass)}
/* short landscape screens (phones held sideways): slimmer header, tighter rhythm */
@media (max-height:520px) and (orientation:landscape){:root{--hdr:54px}.brand{font-size:1.05rem}.brand svg{width:30px;height:30px}.menu-btn{min-height:38px;padding:6px 12px}h1{font-size:clamp(1.8rem,4.4vw,2.5rem)}h2{font-size:clamp(1.45rem,3vw,1.9rem)}section{padding:40px 0}section.tight{padding:24px 0}.hero{padding:28px 0 36px}.page-head{padding:16px 0 28px}.eyebrow{margin-bottom:10px}.actions{margin-top:18px}}
/* touch devices: comfortable tap targets */
@media (pointer:coarse){.add,.chip{min-height:44px}.nav a,.nav .top{padding-block:12px}footer li{margin:0}footer li a{display:inline-block;padding:8px 0}}
/* large desktops */
@media (min-width:1500px){.wrap{max-width:1280px}body{font-size:1.09rem}}
@media print{header.site,.wa,footer,.demo-ribbon,.cta,.noprint{display:none!important}body{background:#fff}}
"""

# Fonts are served from the site itself (fonts/, SIL Open Font License), so no third-party requests are made.
FONTS = ('<link rel="preload" href="__ASSETS__fonts/plus-jakarta-sans-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>'
         '<link rel="preload" href="__ASSETS__fonts/fraunces-latin-full-normal.woff2" as="font" type="font/woff2" crossorigin>')
FONT_CSS = ('@font-face{font-family:"Plus Jakarta Sans";font-style:normal;font-weight:200 800;font-display:swap;src:url(__ASSETS__fonts/plus-jakarta-sans-latin-wght-normal.woff2) format("woff2")}'
            '@font-face{font-family:"Fraunces";font-style:normal;font-weight:100 900;font-display:swap;src:url(__ASSETS__fonts/fraunces-latin-full-normal.woff2) format("woff2")}'
            '@font-face{font-family:"Fraunces";font-style:italic;font-weight:100 900;font-display:swap;src:url(__ASSETS__fonts/fraunces-latin-full-italic.woff2) format("woff2")}')

# Minimal crown mark: redrawn from the client's crown, without the figures, script lettering or tagline.
LOGO_SVG = (f'<svg width="40" height="40" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="23" fill="{DEEP}" stroke="{ACCENT}" stroke-width="1"/>'
            f'<g fill="{ACCENT}"><path d="M13.2 33.4 8.6 18.6l6.6 5.2 2.3-9.6 4 8.2L24 10.2l2.5 12.2 4-8.2 2.3 9.6 6.6-5.2-4.6 14.8Q24 29.6 13.2 33.4Z" stroke="{ACCENT}" stroke-width="1.1" stroke-linejoin="round"/>'
            '<circle cx="8.4" cy="17.4" r="1.7"/><circle cx="17.4" cy="13" r="1.7"/><circle cx="30.6" cy="13" r="1.7"/><circle cx="39.6" cy="17.4" r="1.7"/>'
            '<path d="M24 5.2c1.5 1.7 2.3 3 2.3 4.2a2.3 2.3 0 0 1-4.6 0c0-1.2.8-2.5 2.3-4.2Z"/>'
            f'<path d="M14.6 36.6Q24 33.2 33.4 36.6" fill="none" stroke="{ACCENT}" stroke-width="1.5" stroke-linecap="round"/></g></svg>')

ICONS = {
    "team": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6M15 14.5c2.8 0 5 2.2 5 5"/></svg>',
    "pin": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/></svg>',
    "fit": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M6 7v10M18 7v10M3 10v4M21 10v4M6 12h12"/></svg>',
    "bus": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="4" y="3" width="16" height="14" rx="2"/><path d="M4 11h16M7 21v-4M17 21v-4"/><circle cx="8" cy="14" r=".5"/><circle cx="16" cy="14" r=".5"/></svg>',
    "indoor": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><path d="M3 10 12 4l9 6v10H3z"/><path d="M9 20v-6h6v6"/></svg>',
    "mountain": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M2 20 9 7l4 6 3-4 6 11z"/></svg>',
    "screen": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/></svg>',
    "heart": '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" aria-hidden="true"><path d="M12 20s-8-4.6-8-10.5A4.5 4.5 0 0 1 12 7a4.5 4.5 0 0 1 8 2.5C20 15.4 12 20 12 20z"/></svg>',
}
# Social logos: shapes from Simple Icons (CC0)
SOCIAL_ICONS = {'Facebook': 'M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z', 'Instagram': 'M12 0C8.74 0 8.333.015 7.053.072 5.775.132 4.905.333 4.14.63c-.789.306-1.459.717-2.126 1.384S.935 3.35.63 4.14C.333 4.905.131 5.775.072 7.053.012 8.333 0 8.74 0 12s.015 3.667.072 4.947c.06 1.277.261 2.148.558 2.913.306.788.717 1.459 1.384 2.126.667.666 1.336 1.079 2.126 1.384.766.296 1.636.499 2.913.558C8.333 23.988 8.74 24 12 24s3.667-.015 4.947-.072c1.277-.06 2.148-.262 2.913-.558.788-.306 1.459-.718 2.126-1.384.666-.667 1.079-1.335 1.384-2.126.296-.765.499-1.636.558-2.913.06-1.28.072-1.687.072-4.947s-.015-3.667-.072-4.947c-.06-1.277-.262-2.149-.558-2.913-.306-.789-.718-1.459-1.384-2.126C21.319 1.347 20.651.935 19.86.63c-.765-.297-1.636-.499-2.913-.558C15.667.012 15.26 0 12 0zm0 2.16c3.203 0 3.585.016 4.85.071 1.17.055 1.805.249 2.227.415.562.217.96.477 1.382.896.419.42.679.819.896 1.381.164.422.36 1.057.413 2.227.057 1.266.07 1.646.07 4.85s-.015 3.585-.074 4.85c-.061 1.17-.256 1.805-.421 2.227-.224.562-.479.96-.899 1.382-.419.419-.824.679-1.38.896-.42.164-1.065.36-2.235.413-1.274.057-1.649.07-4.859.07-3.211 0-3.586-.015-4.859-.074-1.171-.061-1.816-.256-2.236-.421-.569-.224-.96-.479-1.379-.899-.421-.419-.69-.824-.9-1.38-.165-.42-.359-1.065-.42-2.235-.045-1.26-.061-1.649-.061-4.844 0-3.196.016-3.586.061-4.861.061-1.17.255-1.814.42-2.234.21-.57.479-.96.9-1.381.419-.419.81-.689 1.379-.898.42-.166 1.051-.361 2.221-.421 1.275-.045 1.65-.06 4.859-.06l.045.03zm0 3.678c-3.405 0-6.162 2.76-6.162 6.162 0 3.405 2.76 6.162 6.162 6.162 3.405 0 6.162-2.76 6.162-6.162 0-3.405-2.76-6.162-6.162-6.162zM12 16c-2.21 0-4-1.79-4-4s1.79-4 4-4 4 1.79 4 4-1.79 4-4 4zm7.846-10.405c0 .795-.646 1.44-1.44 1.44-.795 0-1.44-.646-1.44-1.44 0-.794.646-1.439 1.44-1.439.793-.001 1.44.645 1.44 1.439z', 'TikTok': 'M12.525.02c1.31-.02 2.61-.01 3.91-.02.08 1.53.63 3.09 1.75 4.17 1.12 1.11 2.7 1.62 4.24 1.79v4.03c-1.44-.05-2.89-.35-4.2-.97-.57-.26-1.1-.59-1.62-.93-.01 2.92.01 5.84-.02 8.75-.08 1.4-.54 2.79-1.35 3.94-1.31 1.92-3.58 3.17-5.91 3.21-1.43.08-2.86-.31-4.08-1.03-2.02-1.19-3.44-3.37-3.65-5.71-.02-.5-.03-1-.01-1.49.18-1.9 1.12-3.72 2.58-4.96 1.66-1.44 3.98-2.13 6.15-1.72.02 1.48-.04 2.96-.04 4.44-.99-.32-2.15-.23-3.02.37-.63.41-1.11 1.04-1.36 1.75-.21.51-.15 1.07-.14 1.61.24 1.64 1.82 3.02 3.5 2.87 1.12-.01 2.19-.66 2.77-1.61.19-.33.4-.67.41-1.06.1-1.79.06-3.57.07-5.36.01-4.03-.01-8.05.02-12.07z', 'YouTube': 'M23.498 6.186a3.016 3.016 0 0 0-2.122-2.136C19.505 3.545 12 3.545 12 3.545s-7.505 0-9.377.505A3.017 3.017 0 0 0 .502 6.186C0 8.07 0 12 0 12s0 3.93.502 5.814a3.016 3.016 0 0 0 2.122 2.136c1.871.505 9.376.505 9.376.505s7.505 0 9.377-.505a3.015 3.015 0 0 0 2.122-2.136C24 15.93 24 12 24 12s0-3.93-.502-5.814zM9.545 15.568V8.432L15.818 12l-6.273 3.568z', 'LinkedIn': 'M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z'}
WA_ICON = '<svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8s-.4-.1-.6.1-.7.8-.8 1-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.3-.4.7-1.3a.5.5 0 0 0 0-.5l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.8 11.8 0 0 0 4.5 4c1.7.7 2.3.8 3.2.6a2.7 2.7 0 0 0 1.7-1.2 2.2 2.2 0 0 0 .2-1.2c-.1-.1-.3-.2-.5-.3z"/></svg>'

MTN = '<svg class="mtn" viewBox="0 0 400 120" preserveAspectRatio="none" aria-hidden="true"><path d="M0 120 70 52l40 36 70-74 60 58 40-30 120 78z" fill="var(--grass)" opacity=".35"/><path d="M0 120 110 76l60 26 90-50 140 68z" fill="var(--grass)" opacity=".5"/></svg>'

# Photo slots. Drop an image named after the slot into photos/placeholder/ (stand-in, shown with a
# PLACEHOLDER watermark) or photos/ (final client photo, no watermark) and rebuild. See photos/README.md.
PHOTO_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "photos")
PHOTO_SLOTS = {}
def photo_slug(caption):
    return re.sub(r"[^a-z0-9]+", "-", caption.lower()).strip("-")[:44].strip("-")

def photo_src(caption):
    """(src, is_stand_in) for a slot, or (None, False) when no image has been supplied yet."""
    slug = photo_slug(caption)
    PHOTO_SLOTS[slug] = caption
    for sub, stand_in in (("", False), ("placeholder", True)):
        for ext in ("jpg", "jpeg", "webp", "png"):
            if os.path.exists(os.path.join(PHOTO_DIR, sub, f"{slug}.{ext}")):
                return "__ASSETS__photos/" + (sub + "/" if sub else "") + f"{slug}.{ext}", stand_in
    return None, False

def photo(caption, cls=""):
    slug = photo_slug(caption)
    PHOTO_SLOTS[slug] = caption
    for sub, stand_in in (("", False), ("placeholder", True)):
        for ext in ("jpg", "jpeg", "webp", "png"):
            if os.path.exists(os.path.join(PHOTO_DIR, sub, f"{slug}.{ext}")):
                src = "__ASSETS__photos/" + (sub + "/" if sub else "") + f"{slug}.{ext}"
                if stand_in:
                    return (f'<figure class="ph has-img is-placeholder {cls}"><img src="{src}" alt="Placeholder image. To be replaced with: {E(caption)}" loading="lazy" decoding="async">'
                            f'<span class="wm" aria-hidden="true">Placeholder</span><figcaption><b>Placeholder. Photo to supply:</b> {E(caption)}</figcaption></figure>')
                return f'<figure class="ph has-img {cls}"><img src="{src}" alt="{E(caption[:1].upper() + caption[1:])}" loading="lazy" decoding="async"></figure>'
    return f'<figure class="ph {cls}" role="img" aria-label="Photo placeholder: {E(caption)}">{MTN}<figcaption><b>Photo to supply:</b> {E(caption)}</figcaption></figure>'

def confirm(text):
    return f'<p class="confirm"><span><b>To confirm with client:</b> {text}</span></p>'

# ------------------------------------------------------------------ navigation
NAV = [
    ("/team-building/", "Team building", [("/team-building/", "Overview"), ("/team-building/indoor/", "Indoor team building"),
        ("/team-building/outdoor-adventure/", "Outdoor and adventure"), ("/team-building/virtual-hybrid/", "Virtual and hybrid"),
        ("/team-building/transport-logistics/", "Transport and logistics")]),
    ("/venues/", "Venues", [("/venues/", f"All {TOTAL} venues")] + [(f"/venues/{r['slug']}/", r["short"]) for r in REGIONS[:6]] + [("/venues/#regions", "More regions")]),
    ("/corporate-fitness/", "Corporate fitness", [("/corporate-fitness/", "Office fitness programmes"), ("/corporate-fitness/wellness-days/", "Wellness days")]),
    ("/blog/", "Guides", None),
    ("/about-us/", "About", None),
    ("/contact-us/", "Contact", None),
]

def header(here):
    items = []
    for path, name, sub in NAV:
        active = here == path or (path != "/" and here.startswith(path))
        if sub:
            subl = "".join(f'<li><a href="{link(p, here)}"{" aria-current=\"page\"" if p == here else ""}>{E(n)}</a></li>' for p, n in sub)
            items.append(f'<li class="{"here" if active else ""}"><a class="top" href="{link(path, here)}">{E(name)}</a><ul class="sub">{subl}</ul></li>')
        else:
            items.append(f'<li><a href="{link(path, here)}"{" aria-current=\"page\"" if active else ""}>{E(name)}</a></li>')
    return f"""<header class="site"><div class="wrap bar">
<a class="brand" href="{link('/', here)}" aria-label="{B['name']} home">{LOGO_SVG}<span>Crown Masters<small>Adventures{(' · since ' + str(B['founded'])) if B['founded'] else ''}</small></span></a>
<nav class="navwrap" id="menu" aria-label="Main"><ul class="nav">{''.join(items)}</ul></nav>
<a class="shortlist" data-n="0" href="{link('/contact-us/#quote', here)}" aria-label="Venues added to your quote"><b class="sl-count">0</b><span class="sl-t">In quote</span></a>
<a class="btn btn-gold btn-sm hdr-cta" href="{link('/contact-us/#quote', here)}" data-ev="cta_header">Request a quote</a>
<button class="menu-btn" aria-expanded="false" aria-controls="menu">Menu</button>
</div></header>"""

def footer(here):
    reg = "".join(f'<li><a href="{link("/venues/" + r["slug"] + "/", here)}">{E(r["short"])}</a></li>' for r in REGIONS)
    svc = "".join(f'<li><a href="{link(p, here)}">{E(n)}</a></li>' for p, n in [
        ("/team-building/", "Team building events"), ("/team-building/outdoor-adventure/", "Outdoor and adventure"),
        ("/team-building/indoor/", "Indoor team building"), ("/team-building/transport-logistics/", "Transport and logistics"),
        ("/corporate-fitness/", "Corporate fitness"), ("/corporate-fitness/wellness-days/", "Wellness days"), ("/private-events/", "Private events")])
    res = "".join(f'<li><a href="{link(p, here)}">{E(n)}</a></li>' for p, n in [
        ("/blog/", "Planning guides"), ("/planning-checklist/", "Checklist and budget planner"), ("/about-us/", "About us"),
        ("/contact-us/", "Contact"), ("/privacy-policy/", "Privacy policy")])
    soc = "".join(f'<li><a href="{u}" target="_blank" rel="noopener noreferrer me" aria-label="{n} (opens in a new tab)" title="{n}">'
                  f'<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="{SOCIAL_ICONS[n]}"/></svg></a></li>' for n, u in B["social"].items())
    return f"""<footer><div class="wrap">
<div class="fcols">
<div><h2>{B['name']}</h2><p>Corporate team building, venue booking, corporate fitness and group transport across Kenya, Tanzania and Uganda.</p>
<address style="font-style:normal;line-height:1.9">{E(B['street'])}, {B['city']}<br><a href="tel:{B['phone']}" data-ev="tel_footer">{B['phone_display']}</a><br><a href="mailto:{B['email']}" data-ev="email_footer">{B['email'].replace('@', '@<wbr>')}</a><br>{E(B['hours_display'])}</address></div>
<div><h2>Services</h2><ul>{svc}</ul></div>
<div><h2>Venue regions</h2><ul>{reg}</ul></div>
<div><h2>Resources</h2><ul>{res}</ul></div>
<div><h2>Follow us</h2><ul class="social">{soc}</ul></div>
</div>
<div class="legal"><span>© 2026 {B['name']}. All rights reserved.</span><span>{'<button type="button" class="cookie-settings">Cookie settings</button> · ' if GA else ''}Last updated <time datetime="{UPDATED}">{UPDATED_TEXT}</time></span></div>
</div></footer>"""

COMMON_JS = r"""
(function(){
var d=document;
var b=d.querySelector('.menu-btn'),m=d.getElementById('menu');
if(b)b.addEventListener('click',function(){var o=m.classList.toggle('open');b.setAttribute('aria-expanded',o)});
function track(n,p){p=p||{};var m=/^(cta|tel|whatsapp|email)_(.+)$/.exec(n);if(m){p.location=m[2];n={cta:'cta_click',tel:'phone_click',whatsapp:'whatsapp_click',email:'email_click'}[m[1]]}if(window.gtag)window.gtag('event',n,p)}
window.CMA_track=track;
d.addEventListener('click',function(e){var a=e.target.closest('[data-ev]');if(a)track(a.getAttribute('data-ev'))});
var KEY='cma_shortlist';
function get(){try{return JSON.parse(localStorage.getItem(KEY)||'[]')}catch(x){return []}}
function set(v){try{localStorage.setItem(KEY,JSON.stringify(v))}catch(x){}paint()}
function paint(){var v=get();d.querySelectorAll('.shortlist').forEach(function(s){s.setAttribute('data-n',v.length);s.querySelector('.sl-count').textContent=v.length});
 d.querySelectorAll('.add').forEach(function(btn){var on=v.indexOf(btn.dataset.v)>-1;btn.setAttribute('aria-pressed',on);btn.textContent=on?'Added':'Add to quote';btn.setAttribute('aria-label',(on?'Remove ':'Add ')+btn.dataset.v+(on?' from':' to')+' your quote')});
 var ev=new CustomEvent('shortlist',{detail:v});d.dispatchEvent(ev);}
d.addEventListener('click',function(e){var btn=e.target.closest('.add');if(!btn)return;var v=get(),i=v.indexOf(btn.dataset.v);if(i>-1)v.splice(i,1);else{v.push(btn.dataset.v);track('venue_add',{venue:btn.dataset.v})}set(v)});
window.CMA={get:get,set:set};
if(d.readyState!=='loading')paint();else d.addEventListener('DOMContentLoaded',paint);
})();
"""

# Google Analytics 4: production builds only, and only once data.py has a Measurement ID.
GA = B.get("ga4_id") if PROD else None
GA_JS = r"""
(function(){var K='cma_consent',ID='__GA__',d=document,bar=d.getElementById('consent'),yes=d.getElementById('consent-yes');
function load(){if(window.gtag)return;window.dataLayer=window.dataLayer||[];window.gtag=function(){window.dataLayer.push(arguments)};
window.gtag('js',new Date());window.gtag('config',ID);var s=d.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id='+ID;d.head.appendChild(s)}
function get(){try{return localStorage.getItem(K)}catch(e){return null}}
function set(v){try{localStorage.setItem(K,v)}catch(e){}bar.hidden=true;window['ga-disable-'+ID]=v!=='granted';if(v==='granted')load()}
var c=get();if(c==='granted')load();else if(!c)bar.hidden=false;
yes.addEventListener('click',function(){set('granted')});d.getElementById('consent-no').addEventListener('click',function(){set('denied')});
d.addEventListener('click',function(e){if(e.target.closest('.cookie-settings')){bar.hidden=false;yes.focus()}});
})();
""".replace("__GA__", GA or "")
_GA_SCRIPT = " https://www.googletagmanager.com" if GA else ""
_GA_CONNECT = " https://www.google-analytics.com https://*.google-analytics.com https://*.analytics.google.com https://www.googletagmanager.com" if GA else ""
_GA_IMG = " https://www.google-analytics.com https://www.googletagmanager.com" if GA else ""

CSP_BASE = ("default-src 'self'; script-src 'self' {hashes}" + _GA_SCRIPT + "; style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; img-src 'self' data:" + _GA_IMG + "; frame-src https://www.google.com; connect-src 'self'" + _GA_CONNECT + "; "
            "object-src 'none'; base-uri 'self'; form-action 'self'")
SCRIPT_HASHES = set()
def with_csp(page):
    """Allow only this page's own inline scripts, by SHA-256 hash. No 'unsafe-inline' for scripts."""
    hs = []
    for m in re.finditer(r"<script>(.*?)</script>", page, re.S):
        h = "'sha256-" + base64.b64encode(hashlib.sha256(m.group(1).encode()).digest()).decode() + "'"
        if h not in hs:
            hs.append(h)
    SCRIPT_HASHES.update(hs)
    return page.replace("__CSP__", CSP_BASE.format(hashes=" ".join(hs)))

def consent_bar(here):
    if not GA:
        return ""
    return (f'<div class="consent" id="consent" hidden role="region" aria-label="Cookie consent"><p><b>Can we count your visit?</b> We would like to use Google Analytics cookies '
            f'to see how this site is used and improve it. Nothing is collected unless you accept. <a href="{link("/privacy-policy/", here)}">Privacy policy</a></p>'
            '<div class="consent-btns"><button type="button" class="btn btn-gold btn-sm" id="consent-yes">Accept</button>'
            '<button type="button" class="btn btn-line btn-sm" id="consent-no">Decline</button></div></div>'
            f'<script>{GA_JS}</script>')

def layout(here, title, desc, body, schema, scripts="", og_type="website", noindex=False):
    assets = "/assets/" if PROD else link("/assets/favicon.svg", here)[:-len("favicon.svg")]
    return with_csp(_layout(here, title, desc, body, schema, scripts, og_type, noindex)).replace("__ASSETS__", assets)

def _layout(here, title, desc, body, schema, scripts="", og_type="website", noindex=False):
    canonical = DOMAIN + here if here != "/404.html" else DOMAIN + "/"
    # demo builds (the review sandbox) are never indexable; only the production build is
    robots = "noindex, nofollow" if not PROD else "noindex, follow" if noindex else "index, follow, max-image-preview:large, max-snippet:-1"
    ribbon = "" if PROD else f'<div class="demo-ribbon">Demo v2 for review. Yellow notes mark items to confirm. <a href="{link("/", here)}">Home</a></div>'
    return f"""<!doctype html>
<html lang="en-KE">
<head>
<meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="__CSP__">
<meta name="referrer" content="strict-origin-when-cross-origin">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{E(title)}</title>
<meta name="description" content="{E(desc)}">
<link rel="canonical" href="{canonical}">
<meta name="robots" content="{robots}">
<meta property="og:type" content="{og_type}"><meta property="og:site_name" content="{B['name']}"><meta property="og:locale" content="en_KE">
<meta property="og:title" content="{E(title)}"><meta property="og:description" content="{E(desc)}"><meta property="og:url" content="{canonical}">
<meta property="og:image" content="{DOMAIN}/assets/og-default.jpg"><meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="{DEEP}">
<link rel="icon" href="{link('/assets/favicon.svg', here) if not PROD else '/assets/favicon.svg'}" type="image/svg+xml">
{FONTS}
<style>{FONT_CSS}{CSS}</style>
{schema}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
{ribbon}
{header(here)}
<script>{COMMON_JS}</script>
{consent_bar(here)}
<main id="main">
{body}
</main>
{footer(here)}
<a class="wa" href="{B['whatsapp']}?text=Hi%20Crown%20Masters%2C%20I%27d%20like%20to%20plan%20a%20team%20event." rel="noopener noreferrer" data-ev="whatsapp_float" aria-label="Chat with us on WhatsApp">{WA_ICON}<span>WhatsApp</span></a>
{scripts}
</body>
</html>"""

# ------------------------------------------------------------------ shared blocks
def crumbs(items, here):
    lis = "".join(f'<li><a href="{link(p, here)}">{E(n)}</a></li>' if p != here else f'<li aria-current="page">{E(n)}</li>' for n, p in items)
    return f'<nav class="crumbs wrap" aria-label="Breadcrumb"><ol>{lis}</ol></nav>'

def faq_block(faqs, heading="Frequently asked questions", sub="Straight answers to the questions HR and admin teams ask us most."):
    items = "".join(f"<details><summary>{E(q)}</summary><div><p>{E(a)}</p></div></details>" for q, a in faqs)
    return f'<section id="faq"><div class="wrap grid2"><div><h2>{heading}</h2><p class="muted">{sub}</p></div><div>{items}</div></div></section>'

def cta(here, title="Planning a team event?", text="Send your group size, dates and budget. We reply with venue options and a quote."):
    return (f'<section class="tight"><div class="wrap"><div class="cta"><div><h2>{E(title)}</h2><p>{E(text)}</p></div>'
            f'<div class="actions" style="margin:0"><a class="btn btn-gold" href="{link("/contact-us/#quote", here)}" data-ev="cta_band">Request a quote</a>'
            f'<a class="btn btn-line" href="{B["whatsapp"]}?text=Hi%20Crown%20Masters%2C%20I%27d%20like%20a%20team%20building%20quote." rel="noopener noreferrer" data-ev="whatsapp_band">WhatsApp us</a></div></div></div></section>')

def drive_chart(here, regions=REGIONS, title="How far each region is from Nairobi"):
    # Collapsed travel-time list: one line when closed, readable on phones when open.
    rows = "".join(
        f'<li><a href="{link("/venues/" + r["slug"] + "/", here)}"><b>{E(r["short"])}</b>'
        f'<span>{E(r["travel"][:1].upper() + r["travel"][1:])}</span></a></li>' for r in regions)
    return (f'<details class="dt"><summary>{E(title)}</summary>'
            f'<div><ul class="dt-list">{rows}</ul><p class="small muted" style="margin:10px 0 0">Approximate door-to-door times. Select a region to see its venues.</p></div></details>')

def venue_card(v, region):
    tbc = v.endswith("?")
    name = v.rstrip("?")
    flag = ' <span class="tbc">name to confirm</span>' if tbc else ""
    return (f'<li class="vcard" data-n="{E(name.lower())}"><span class="vn">{E(name)}{flag}<span class="vs">{E(region["setting"])}</span></span>'
            f'<button type="button" class="add" data-v="{E(name)}" aria-pressed="false">Add to quote</button></li>')

TRIP = {"day": "Day trips", "overnight": "Overnight stays", "both": "Day trips or overnight"}

# ================================================================== PAGES
pages = []
def add(path, fn):
    pages.append((path, fn))

# ---------------- home
G = B["google"]
FAQ_HOME = [
    ("What does Crown Masters Adventures do?",
     f"Crown Masters Adventures is a Nairobi-based team building company. We plan and facilitate corporate team building events, book team building venues across Kenya, Tanzania and Uganda, run corporate fitness programmes at your office, and arrange group transport, getaways and expeditions."),
    ("Where can we find a team building venue in Kenya?",
     f"We work with {TOTAL} venues in {len(REGIONS)} regions: day-trip gardens around Nairobi, lakeside resorts in Naivasha, Nakuru and Elementaita, river and adventure camps in Sagana, highland lodges in Nanyuki, and beach hotels in Mombasa and Diani. We also book venues in Tanzania, Zanzibar and Uganda."),
    ("How do we find the best team building facilitators in Kenya?",
     f"The best facilitators for your team are the ones who build the day around your goal, not a fixed list of games. Ask who will run your event on the day, how they handle safety on activities such as rafting, what happens if it rains, and how they close the day with a debrief. At Crown Masters Adventures our facilitators plan and run the programme, and clients rate us {G['rating']} out of 5 on Google from {G['reviews']} reviews ({G['as_of']})."),
    ("Are there affordable team building packages in Kenya?",
     "Yes. The price per person depends mostly on the venue, travel distance, meals and whether you stay overnight. The most affordable options are a half-day session at your own office or a day trip to a garden venue around Nairobi, on a weekday outside the November and December peak. Tell us your budget per person and we build the package to fit it."),
    ("What should we look for in the best corporate team building companies in Kenya?",
     f"Look for one company that handles the facilitation, venue, meals and transport together, gives a written quote priced per person, offers a real choice of venues, and can show reviews from other organisations. Crown Masters Adventures is based in Parklands, Nairobi, plans and facilitates the programme, books from {TOTAL} venues in {len(REGIONS)} regions, and arranges group transport."),
    ("How much does corporate team building cost in Kenya?",
     "The cost depends on group size, the venue, whether you stay overnight, transport and the activities you choose. Send us your headcount, dates and budget and we quote options that fit. Our free budget planner shows how each cost adds up."),
    ("How far ahead should we book?",
     "As early as you can. Popular resorts fill quickly for November and December year-end events and around public holidays, so start planning six to eight weeks ahead for those dates."),
    ("Can you run team building at our office instead of a venue?",
     "Yes. Indoor team building and our corporate fitness sessions only need an open space, such as a boardroom, a parking area, a rooftop or a nearby field."),
    ("How do we book?",
     f"Request a quote online, call or WhatsApp {B['phone_display']}, or email {B['email']}. Tell us your group size, dates and budget and we reply with options."),
]

STAR = '<svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="m12 2.6 2.9 6 6.5.9-4.7 4.6 1.1 6.5-5.8-3.1-5.8 3.1 1.1-6.5L2.6 9.5l6.5-.9z"/></svg>'

RV_JS = r"""
(function(){var d=document;[].forEach.call(d.querySelectorAll('.quote-card'),function(c){var q=c.querySelector('blockquote'),b=c.querySelector('.rv-more');if(!q||!b)return;
q.classList.add('clamp');if(q.scrollHeight<=q.clientHeight+2){q.classList.remove('clamp');return}
b.hidden=false;b.addEventListener('click',function(){var open=q.classList.toggle('clamp')===false;b.setAttribute('aria-expanded',open);b.textContent=open?'Read less':'Read more'})})})();
"""
CL_JS = r"""
(function(){var d=document,s=d.querySelector('.clients'),b=d.querySelector('.cl-pause');if(!s||!b)return;
if(window.matchMedia('(prefers-reduced-motion:reduce)').matches){b.hidden=true;return}
b.addEventListener('click',function(){var p=s.classList.toggle('paused');b.setAttribute('aria-pressed',p);b.textContent=p?'Play':'Pause'});})();
"""

def client_strip():
    """One-row client strip: logo where a file exists in photos/logos/, otherwise the name as text."""
    def item(name, slug):
        for ext in ("svg", "png", "webp"):
            if os.path.exists(os.path.join(PHOTO_DIR, "logos", f"{slug}.{ext}")):
                return f'<li><img src="__ASSETS__photos/logos/{slug}.{ext}" alt="{E(name)}" height="34" loading="lazy" decoding="async"></li>'
        return f'<li><span>{E(name)}</span></li>'
    items = "".join(item(n, sl) for n, sl in CLIENTS)
    lead = ", ".join(E(n) for n, _ in CLIENTS[:10])
    return (f'<div class="cl-head"><p class="eyebrow">Proud to have served</p><button type="button" class="cl-pause" aria-pressed="false">Pause</button></div>'
            f'<div class="clients"><div class="cl-track"><ul>{items}</ul><ul aria-hidden="true">{items}</ul></div></div>'
            f'<p class="small muted cl-text">Teams we have served include {lead} and {len(CLIENTS) - 10} more organisations.</p>'
            + confirm("Client names were read from the 'Proud to have served' graphic. Confirm the list and permission to show each brand, and supply original logo files; names without a logo file are shown as text."))

HERO_SLOTS = [  # background slideshow behind the home headline, in order
    "two teams competing in an outdoor challenge, wide shot showing the venue",
    "rafting team at Sagana",
    "a group on the lawn of a lakeside resort",
    "indoor problem-solving challenge",
    "venue lawn or main activity area",
]
HERO_JS = r"""
(function(){var d=document,root=d.querySelector('.hero-bg');if(!root)return;
var S=[].slice.call(root.querySelectorAll('.hero-slide')),D=[].slice.call(root.querySelectorAll('.hero-dot')),
i=0,t,paused=false,reduce=window.matchMedia('(prefers-reduced-motion:reduce)').matches;
function load(el){var im=el.querySelector('img[data-src]');if(im){im.src=im.getAttribute('data-src');im.removeAttribute('data-src')}}
function tick(){clearTimeout(t);root.classList.remove('run');if(paused||reduce||d.hidden||S.length<2)return;void root.offsetWidth;root.classList.add('run');t=setTimeout(function(){go(i+1)},6000)}
function go(n){S[i].classList.remove('on');D[i].removeAttribute('aria-current');i=(n+S.length)%S.length;load(S[i]);load(S[(i+1)%S.length]);
S[i].classList.add('on');D[i].setAttribute('aria-current','true');tick()}
D.forEach(function(b,n){b.addEventListener('click',function(){go(n)})});
d.addEventListener('visibilitychange',tick);
if(reduce||S.length<2){var c=root.querySelector('.hero-ctl');if(c)c.hidden=true;return}
function start(){load(S[1]);tick()}
if(d.readyState==='complete')start();else window.addEventListener('load',start);
})();
"""

def hero(here):
    text = f"""<p class="eyebrow">Corporate team building · Nairobi, Kenya</p>
<h1>Team building in Kenya, <em>planned and run for you</em></h1>
<p class="lede">We plan the programme, book the venue, get your team there and facilitate the day, from Nairobi gardens to Naivasha, Sagana, Nanyuki and the coast.</p>
<div class="actions"><a class="btn btn-gold" href="{link('/contact-us/#quote', here)}" data-ev="cta_hero">Request a quote</a><a class="btn btn-line" href="{link('/venues/', here)}">Browse {TOTAL} venues</a></div>
<p class="small muted" style="margin-top:16px">Prefer to talk? Call or WhatsApp <a href="tel:{B['phone']}" data-ev="tel_hero">{B['phone_display']}</a></p>"""
    shots = [photo_src(c) for c in HERO_SLOTS]
    shots = [(src, stand_in) for src, stand_in in shots if src]
    if not shots:  # no photos supplied yet: plain hero with one photo slot
        return f'<section class="hero"><div class="wrap split"><div>{text}</div>{photo(HERO_SLOTS[0], "tall")}</div></section>'
    slides = "".join(
        f'<div class="hero-slide{" on" if n == 0 else ""}"><img {"src" if n == 0 else "data-src"}="{src}" alt=""{" fetchpriority=\"high\"" if n == 0 else ""} decoding="async"></div>'
        for n, (src, _) in enumerate(shots))
    dots = "".join(f'<button type="button" class="hero-dot"{" aria-current=\"true\"" if n == 0 else ""} aria-label="Show photo {n + 1} of {len(shots)}"><i></i></button>' for n in range(len(shots)))
    stand_in = any(st for _, st in shots)
    wm = '<span class="hero-wm" aria-hidden="true">Placeholder</span>' if stand_in else ""
    note = '<span class="hero-note">Placeholder photos, to be replaced with client event photos</span>' if stand_in else ""
    return f"""<section class="hero hero-bg">
<div class="hero-slides" aria-hidden="true">{slides}</div><div class="hero-scrim" aria-hidden="true"></div>{wm}
<div class="wrap"><div class="hero-text">{text}</div>
<div class="hero-ctl"><div class="hero-dots">{dots}</div>{note}</div>
</div></section>"""

def home(here):
    services = [
        ("team", "/team-building/", "Team building events", "Facilitated indoor, outdoor and adventure programmes built around what you want the team to come away with."),
        ("pin", "/venues/", "Venue booking", f"We shortlist venues from {TOTAL} options that fit your budget and headcount, then handle the booking."),
        ("fit", "/corporate-fitness/", "Corporate fitness", "Trainers come to your office with Zumba, aerobics, circuits and more, plus fitness testing and nutrition guidance."),
        ("bus", "/team-building/transport-logistics/", "Transport and logistics", "Executive transport hire to get your group to the venue and home again, on schedule."),
    ]
    svc = "".join(f'<div class="card link"><div class="icon">{ICONS[i]}</div><h3><a href="{link(p, here)}">{t}</a></h3><p>{d}</p></div>' for i, p, t, d in services)
    feat = REGIONS[:6]
    regcards = "".join(f'<div class="card link"><h3><a href="{link("/venues/" + r["slug"] + "/", here)}">{E(r["short"])}</a></h3><p>{E(r["setting"])}. {E(r["best"].split(",")[0])}.</p><p class="meta">{r["count"]} venues · {E(r["travel"])}</p></div>' for r in feat)
    guides = "".join(f'<div class="card link"><h3><a href="{link(p, here)}">{E(t)}</a></h3><p>{E(d)}</p><p class="meta">Guide</p></div>' for p, t, d, _ in ARTICLES)
    if B["reviews"]:
        reviews = '<div class="grid3" style="margin-top:20px;align-items:start">' + "".join(
            f'<figure class="quote-card"><blockquote>“{E(r["text"])}”</blockquote>'
            f'<button type="button" class="rv-more" hidden aria-expanded="false">Read more</button><figcaption><b>{E(r["name"])}</b> · Google review{", " + E(r["date"]) if r.get("date") else ""}</figcaption></figure>' for r in B["reviews"]) + "</div>"
    else:
        reviews = confirm("Review quotes go here. Paste 3 to 6 reviews from the Google Business Profile, word for word with the reviewer's name, and they will appear as cards under the rating. Re-check the rating and review count at launch.")
    body = f"""
{hero(here)}

<section class="tight"><div class="wrap">
<div class="stats" style="margin-top:0">
<div class="stat"><b>{TOTAL}</b>venues in {len(REGIONS)} regions</div>
<div class="stat"><b>3</b>countries: Kenya, Tanzania, Uganda</div>
<div class="stat"><b>{B['events_delivered'] or '<span class="tbc">to supply</span>'}</b>events delivered</div>
<div class="stat"><b>{G['rating']}</b>Google rating from {G['reviews']} reviews</div>
</div>
</div></section>

<section class="tight"><div class="wrap">
<div class="answer"><p><strong>In short:</strong> {B['name']} is a corporate team building company based in Parklands, Nairobi. We plan and facilitate team building events, book venues across Kenya, Tanzania and Uganda, deliver corporate fitness at clients' offices and arrange group transport.</p></div>
</div></section>

<section><div class="wrap">
<h2>What we do</h2>
<p class="muted">Four services that work together, so one call covers the whole event. We also plan <a href="{link('/private-events/', here)}">private events</a> such as baby showers, graduations and birthdays.</p>
<div class="grid4" style="margin-top:24px">{svc}</div>
</div></section>

<section><div class="wrap">
<h2>How booking works</h2>
<ol class="steps" style="margin-top:24px">
<li><h3>Share the brief</h3><p>Group size, dates, budget and what you want the event to achieve.</p></li>
<li><h3>Compare venues</h3><p>We send a shortlist with costs, so you can choose with your finance team.</p></li>
<li><h3>Agree the programme</h3><p>Activities, meals, transport and timings, confirmed in writing before the day.</p></li>
<li><h3>Your team takes part</h3><p>Our facilitators run the day, so the organiser joins in instead of managing it.</p></li>
</ol>
</div></section>

<section class="band"><div class="wrap">
<div class="region-head"><div><h2>Choose a region by how far you want to travel</h2>
<p>Most one-day events stay within two hours of Nairobi. Overnight retreats usually head to the Rift Valley lakes or Mount Kenya, and reward trips to the coast.</p></div>
<a class="btn btn-line" href="{link('/venues/', here)}">Compare all regions</a></div>
<div class="grid3" style="margin-top:24px">{regcards}</div>
</div></section>

<section><div class="wrap">
<h2>What clients say</h2>
<div class="rating">
<div class="rating-score"><b>{G['rating']}</b><span>out of 5</span></div>
<div><p class="stars" role="img" aria-label="Rated {G['rating']} out of 5 on Google">{STAR * 5}</p>
<p class="rating-t">Rated {G['rating']} out of 5 on Google, from {G['reviews']} reviews.</p>
<p class="small muted" style="margin:0">Figures from our Google Business Profile, {G['as_of']}.</p></div>
<div class="actions" style="margin:0"><a class="btn btn-line" href="{G['url']}" target="_blank" rel="noopener noreferrer" data-ev="google_reviews">Read the reviews on Google<span class="sr"> (opens in a new tab)</span></a></div>
</div>
{reviews}
</div></section>

<section class="band"><div class="wrap">
<h2>Planning guides</h2>
<p class="muted">Practical answers for whoever has been asked to organise this year's event.</p>
<div class="grid4" style="margin-top:24px">{guides}</div>
</div></section>

{faq_block(FAQ_HOME)}
{cta(here)}
<section class="tight clients-sec"><div class="wrap">
{client_strip()}
</div></section>
"""
    schema = ld(page_ld("/", "Corporate team building in Kenya"), faq_ld(FAQ_HOME, "/"))
    return layout(here, "Corporate Team Building in Kenya | Crown Masters Adventures",
                  f"Nairobi team building company. We plan and facilitate corporate team building, book {TOTAL} venues across Kenya, Tanzania and Uganda, and run office fitness.",
                  body, schema, scripts=f"<script>{HERO_JS}</script><script>{CL_JS}</script><script>{RV_JS}</script>")
add("/", home)

# ---------------- team building pillar
TB_FAQ = [
    ("What is corporate team building?", "Corporate team building is a planned day or retreat of group activities that helps colleagues communicate, cooperate and trust each other. A facilitator runs the activities and links them back to how the team works day to day."),
    ("How long does a team building event last?", "Most events are a single day at a venue near Nairobi, roughly from a morning departure to an early evening return. Retreats in Naivasha, Nanyuki or the coast usually run two or three days with overnight stays."),
    ("Can you tailor activities to our goals?", "Yes. Tell us what you want the team to come away with, such as better communication, a new team getting to know each other, or a reward for a strong year, and we design the programme around it."),
    ("What do your team building packages include?", "Each package is built for the group: a facilitated programme, the venue booking, meals at the venue, and transport if you need it. Overnight retreats add accommodation. We quote per person and show each cost line, so you can adjust the package to fit your budget."),
    ("Who facilitates the day?", "Our facilitators run the activities. They brief the group, keep the programme on time, and end with a debrief that links the activities back to how the team works."),
    ("Do you provide transport?", "Yes. We arrange executive transport so your group travels to and from the venue together."),
    ("What should staff wear and bring?", "Comfortable clothes and closed shoes for outdoor activities, a hat, sunscreen and a water bottle. For overnight trips we send a packing list with the programme."),
]
GROUPS = [
    ("small", "Up to 20", "Leadership teams, departments, start-ups",
     "Facilitated workshop plus a few focused challenges", "Boutique gardens near Nairobi, Nanyuki lodges", "One minibus or self-drive", "A day, or one night for a strategy retreat"),
    ("mid", "20 to 80", "Departments and small companies",
     "Rotating outdoor challenges in teams of 8 to 10, then a group finale", "Garden venues around Nairobi, Naivasha resorts", "One or two coaches", "A day, or two days and one night"),
    ("large", "80 to 300", "Whole companies and year-end events",
     "Several facilitators running stations in parallel, a shared opening and closing", "Large resorts in Naivasha, Machakos or the coast", "Several coaches on a timed schedule", "Usually a day; overnight at larger resorts"),
    ("xl", "300 and above", "Large organisations, conferences with activities",
     "A staged programme with lead and station facilitators, timed zones", "The largest resorts and grounds; confirmed per event", "Coach fleet and arrival waves", "Planned per event"),
]

def team_building(here):
    formats = [("indoor", "/team-building/indoor/", "Indoor team building", "Problem-solving and communication challenges in a hall or boardroom."),
               ("mountain", "/team-building/outdoor-adventure/", "Outdoor and adventure", "Obstacle courses, treasure hunts and rafting at lakes, rivers and gardens."),
               ("screen", "/team-building/virtual-hybrid/", "Virtual and hybrid", "Sessions for teams spread across offices or working remotely."),
               ("bus", "/team-building/transport-logistics/", "Transport and logistics", "Coaches and timings that get everyone there and back.")]
    fh = "".join(f'<div class="card link"><div class="icon">{ICONS[i]}</div><h3><a href="{link(p, here)}">{t}</a></h3><p>{d}</p></div>' for i, p, t, d in formats)
    tabs = "".join(f'<button role="tab" id="tab-{k}" aria-controls="panel-{k}" aria-selected="{"true" if j == 0 else "false"}" tabindex="{0 if j == 0 else -1}">{E(n)} people</button>' for j, (k, n, *_ ) in enumerate(GROUPS))
    panels = "".join(f'<div role="tabpanel" id="panel-{k}" aria-labelledby="tab-{k}" {"" if j == 0 else "hidden"}><dl><dt>Typical teams</dt><dd>{E(who)}</dd><dt>Format</dt><dd>{E(fmt)}</dd><dt>Where</dt><dd>{E(where)}</dd><dt>Transport</dt><dd>{E(tr)}</dd><dt>Length</dt><dd>{E(ln)}</dd></dl>{confirm("Events for 1,000+ people appear in the blueprint. Add a 1,000+ tier only once the client confirms they have delivered one.") if k == "xl" else ""}</div>' for j, (k, n, who, fmt, where, tr, ln) in enumerate(GROUPS))
    body = f"""
{crumbs([("Home", "/"), ("Team building", here)], here)}
<section class="page-head"><div class="wrap split">
<div><h1>Corporate team building in Kenya</h1>
<div class="answer"><p>{B['name']} plans and runs corporate team building events in Kenya. We agree your goals, book a venue that fits your budget from {TOTAL} options, arrange transport and meals, and facilitate indoor, outdoor or adventure activities on the day, for teams from a handful of people to whole companies.</p></div>
<div class="actions"><a class="btn btn-gold" href="{link('/contact-us/#quote', here)}" data-ev="cta_tb">Request a quote</a><a class="btn btn-line" href="{link('/venues/', here)}">Find a venue</a></div></div>
{photo("two teams competing in an outdoor challenge, wide shot showing the venue")}
</div></section>

<section style="padding-top:16px"><div class="wrap">
<h2>Choose a format</h2>
<div class="grid4" style="margin-top:24px">{fh}</div>
</div></section>

<section class="band"><div class="wrap">
<h2>What changes with group size</h2>
<p class="muted">Pick your headcount to see how we usually shape an event of that size.</p>
<div class="tabs" id="sizes"><div role="tablist" aria-label="Group size">{tabs}</div>{panels}</div>
</div></section>

<section><div class="wrap grid2">
<div><h2>Example one-day programme</h2><p class="muted">A typical day at a venue within two hours of Nairobi. Every programme is agreed with you in advance.</p>
{photo("facilitator briefing a group before an activity", "wide")}</div>
<ol class="agenda">
<li><time>7:00</time><span>Coaches leave your office</span></li>
<li><time>9:00</time><span>Arrival, tea and a welcome briefing</span></li>
<li><time>9:30</time><span>Icebreakers to mix departments into teams</span></li>
<li><time>10:30</time><span>Team challenges in rotation</span></li>
<li><time>13:00</time><span>Lunch</span></li>
<li><time>14:00</time><span>Group finale that needs every team to succeed</span></li>
<li><time>15:30</time><span>Debrief: what worked and what the team takes back</span></li>
<li><time>16:30</time><span>Coaches return to Nairobi</span></li>
</ol>
</div></section>

<section class="band"><div class="wrap grid2">
<div><h2>What a package covers</h2><p>Every event is quoted for your group. A typical package includes the items here; tell us what to leave out.</p></div>
<ul style="line-height:2;margin:0">
<li>A planning call and a written programme</li><li>Venue shortlist with prices, then the booking</li>
<li>Facilitators and all activity equipment</li><li>Meals and refreshments arranged with the venue</li>
<li>Transport to and from the venue (optional)</li><li>A debrief at the end of the day</li></ul>
</div></section>

<section><div class="wrap">
<h2>Photos and video from past events</h2>
<p class="muted">Hosted on this site, so visitors stay here instead of leaving for Facebook or YouTube.</p>
<div class="grid3" style="margin-top:20px">{photo("rafting team at Sagana")}{photo("year-end group photo at a Naivasha resort")}{photo("indoor problem-solving challenge")}</div>
</div></section>

{faq_block(TB_FAQ)}
{cta(here)}
<script>
(function(){{var tl=document.querySelector('#sizes [role=tablist]');if(!tl)return;var tabs=[].slice.call(tl.querySelectorAll('[role=tab]'));
function sel(t){{tabs.forEach(function(x){{var on=x===t;x.setAttribute('aria-selected',on);x.tabIndex=on?0:-1;document.getElementById(x.getAttribute('aria-controls')).hidden=!on}});t.focus()}}
tabs.forEach(function(t,i){{t.addEventListener('click',function(){{sel(t)}});t.addEventListener('keydown',function(e){{if(e.key==='ArrowRight')sel(tabs[(i+1)%tabs.length]);if(e.key==='ArrowLeft')sel(tabs[(i-1+tabs.length)%tabs.length])}})}});}})();
</script>
"""
    schema = ld(service_ld(here, "Corporate team building", "Corporate team building facilitation",
                           "Planning and facilitation of corporate team building events in Kenya, with venue booking, transport and meals."),
                crumbs_ld([("Home", "/"), ("Team building", here)]), faq_ld(TB_FAQ, here))
    return layout(here, "Team Building Activities & Packages in Kenya | Crown Masters",
                  "Facilitated corporate team building in Kenya: indoor, outdoor and adventure formats, sized for 10 to 300+ staff, with venue, transport and meals arranged.",
                  body, schema)
add("/team-building/", team_building)

def sub_page(here, h1, title, desc, answer, sections, faqs, photo_caption, flag=None, stype=None, parent=("Team building", "/team-building/")):
    trail = [("Home", "/")] + ([parent] if parent else []) + [(h1, here)]
    secs = "".join(f'<section class="{"band" if i % 2 == 0 else ""}"><div class="wrap grid2"><div><h2>{E(h)}</h2>{intro}</div><div>{content}</div></div></section>' for i, (h, intro, content) in enumerate(sections))
    body = f"""
{crumbs(trail, here)}
<section class="page-head"><div class="wrap split">
<div><h1>{E(h1)}</h1>{confirm(flag) if flag else ""}
<div class="answer"><p>{answer}</p></div>
<div class="actions"><a class="btn btn-gold" href="{link('/contact-us/#quote', here)}" data-ev="cta_sub">Request a quote</a></div></div>
{photo(photo_caption)}
</div></section>
{secs}
{faq_block(faqs)}
{cta(here)}
"""
    schema = ld(service_ld(here, h1, stype or h1, desc), crumbs_ld(trail), faq_ld(faqs, here))
    return layout(here, title, desc, body, schema)

add("/private-events/", lambda here: sub_page(here, "Private events",
    "Private Events: Baby Showers, Graduations | Crown Masters",
    "Crown Masters Adventures also plans private events in Kenya, including baby showers, graduation parties and birthdays, with a venue, group games and transport.",
    "Alongside corporate work, Crown Masters Adventures plans non-corporate events such as baby showers, graduation parties and birthdays. We help you choose a venue, run games and activities for your guests, and arrange group transport if you need it.",
    [("Occasions we plan", "<p>Family and social events, for small or large groups.</p>",
      ul(["Baby showers", "Graduation parties", "Birthdays", "Other family and social gatherings on request"])),
     ("How we help", "<p>The same planning we do for companies, sized for a private occasion.</p>",
      ul(["A venue that suits your guest list and budget", "Games and activities led by our facilitators", "Group transport for your guests, if needed", "One contact person from first call to the day itself"]))],
    [("Do you only work with companies?", "No. Most of our work is corporate team building, but we also plan private events such as baby showers, graduation parties and birthdays."),
     ("How do we get a price for a private event?", f"Send us the occasion, the number of guests, your date and your budget. Request a quote online, or call or WhatsApp {B['phone_display']}.")],
    "a decorated venue set up for a private celebration",
    flag="Taken from the WhatsApp catalogue item 'Non corporate events (baby showers, graduation, birth...)'. Confirm the full list of occasions and what the service includes (for example decor or catering) before launch.",
    stype="Private event planning", parent=None))

def ul(items):
    return "<ul style='line-height:1.9;margin:0'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"

add("/team-building/indoor/", lambda here: sub_page(here, "Indoor team building",
    "Indoor Team Building in Nairobi | Crown Masters Adventures",
    "Indoor team building in Nairobi: problem-solving challenges, communication games and icebreakers in your boardroom, a hotel hall or a venue conference room.",
    "Indoor team building brings facilitated problem-solving, communication and creative challenges into a boardroom, hotel hall or conference room. It suits rainy-season dates, half-day sessions, and teams that cannot travel far from the office.",
    [("When to choose indoor", "<p>Indoor sessions work well when time, weather or budget rule out a full day away.</p>",
      ul(["Half-day sessions before or after work", "The long rains (roughly March to May) and short rains (roughly October to December)", "Conferences that need a team activity between sessions", "Teams that cannot leave the office for a full day"])),
     ("Activities we run indoors", "<p>Each one is chosen for what you want the team to practise.</p>",
      ul(["Problem-solving puzzles solved against the clock", "Communication games where only one person sees the instructions", "Build challenges with limited materials", "Team quizzes and icebreakers to mix departments", "Reflection and debrief led by a facilitator"])),
     ("What we need from you", "<p>Very little. We bring the facilitators and the equipment.</p>",
      ul(["A room with space to move, with tables that can be cleared", "A headcount and the time available", "Anything you want the session to focus on"]))],
    [("Can you run team building in our own office?", "Yes. A boardroom or open-plan area with the furniture moved back is usually enough for groups of up to about 30; for more people we suggest a hotel hall."),
     ("How long is an indoor session?", "From about two hours for a focused session to a full day with lunch at a venue."),
     ("Is indoor team building cheaper?", "Usually, because there is no venue hire or transport if you use your own space. We quote it per session.")],
    "indoor problem-solving challenge in a hotel hall", stype="Indoor team building"))

add("/team-building/outdoor-adventure/", lambda here: sub_page(here, "Outdoor and adventure team building",
    "Outdoor & Adventure Team Building in Kenya | Crown Masters",
    "Outdoor team building in Kenya: obstacle courses, treasure hunts and relays at garden venues, plus rafting at Sagana and cycling at Hell's Gate.",
    "Outdoor team building uses open lawns, lakes and rivers for obstacle courses, treasure hunts, relays and group challenges. Adventure options add white-water rafting at Sagana, cycling and walking at Hell's Gate near Naivasha, and forest walks at Ngare Ndare near Nanyuki.",
    [("Outdoor challenges", "<p>Run in rotating teams, so everyone takes part and no one sits out for long.</p>",
      ul(["Obstacle courses and relay races", "Treasure hunts across the venue grounds", "Tug of war and team sports", "Raft and structure building", "A group finale that needs every team to succeed"])),
     ("Adventure activities", "<p>For teams that want more of a challenge. These are run at specialist venues with the venue's own guides and equipment.</p>",
      ul([f'White-water rafting at Sagana (<a href="{link("/venues/muranga-sagana-nyeri-nyahururu/", here)}">see Sagana venues</a>)',
          f'Cycling and walking at Hell\'s Gate National Park (<a href="{link("/venues/naivasha-nakuru-elementaita/", here)}">Naivasha venues</a>)',
          f'Guided forest walks at Ngare Ndare (<a href="{link("/venues/nanyuki-isiolo/", here)}">Nanyuki venues</a>)',
          "Camping for overnight programmes"])),
     ("Safety and inclusion", "<p>Not everyone wants to raft. Every programme has options for different fitness levels.</p>",
      ul(["Activities chosen to suit the group's fitness range", "Safety briefing before every activity", "Lower-intensity roles in every team challenge", "Ask us about guides, equipment and first aid at a specific venue"]))],
    [("What is the best place for adventure team building near Nairobi?", "Sagana, about two hours north of Nairobi, is the best-known option for rafting and river activities. Naivasha and Hell's Gate are popular for cycling and walking."),
     ("Do staff need to be fit for outdoor team building?", "No. Activities are chosen for the whole group, and every team challenge has roles that suit people who prefer to take it easy."),
     ("What happens if it rains?", "We plan an indoor or covered fallback at every venue, and adjust the timings on the day.")],
    "a team crossing an obstacle course on a lawn", stype="Outdoor team building"))

add("/team-building/virtual-hybrid/", lambda here: sub_page(here, "Virtual and hybrid team building",
    "Virtual & Hybrid Team Building | Crown Masters Adventures",
    "Virtual and hybrid team building for remote and multi-office teams: facilitated online challenges, quizzes and icebreakers that include everyone.",
    "Virtual team building runs facilitated challenges, quizzes and icebreakers over a video call, so remote staff and teams in different offices take part together. Hybrid sessions link a group in one room with colleagues joining online.",
    [("Who it is for", "<p>Teams that rarely meet in one place.</p>", ul(["Remote and hybrid teams", "Companies with offices in several towns or countries", "Short sessions between quarterly meet-ups"])),
     ("What a session looks like", "<p>About 60 to 90 minutes, led live by a facilitator.</p>", ul(["Warm-up and introductions", "Small-group challenges in breakout rooms", "A team quiz or puzzle round", "A short debrief"])),
     ("What you need", "<p>Very little set-up.</p>", ul(["A video call link (Zoom, Google Meet or Teams)", "A camera and stable internet for each person", "For hybrid: a screen, camera and microphone in the room"]))],
    [("How many people can join a virtual session?", "Group sizes are confirmed per session; breakout rooms keep each team small."),
     ("Which platforms do you use?", "Zoom, Google Meet or Microsoft Teams, whichever your company already uses.")],
    "a hybrid session with a room group and remote colleagues on screen",
    flag="Virtual and hybrid sessions are proposed in the blueprint but are not offered on the current site. Publish this page only if the client runs them.", stype="Virtual team building"))

add("/team-building/transport-logistics/", lambda here: sub_page(here, "Transport and logistics",
    "Group Transport for Corporate Events | Crown Masters",
    "Executive transport hire for team building and corporate events in Kenya: Coaster buses with 22 to 33 seats from your office to the venue and back, on schedule.",
    "We arrange executive transport for team building and corporate events, so your whole group travels together from the office to the venue and back on a schedule agreed in advance. Transport can be booked with an event or on its own.",
    [("What we arrange", "<p>Vehicles sized to your headcount and route.</p>",
      ul(["Coaster buses with 22, 28, 30, 31 and 33 seats", "Executive vans and minibuses for smaller groups", "Coaches for large groups", "Pick-ups from one or several office locations", "Airport and SGR station transfers for coast and cross-border trips"])),
     ("How it runs on the day", "<p>Everything is timed against the programme.</p>",
      ul(["A departure plan shared with your team the week before", "One contact person for drivers and staff", "Return timings agreed before the event"]))],
    [("What size buses can we hire?", "Our executive transport includes Coaster buses with 22, 28, 30, 31 and 33 seats. Tell us your headcount and route and we match the vehicles to the group."),
     ("Can we book transport without a team building event?", "Yes. Executive transport hire is available on its own for corporate trips and events."),
     ("Do you arrange travel to the coast?", "Yes. For Mombasa and Diani we plan around flights or the SGR train, with road transfers at each end.")],
    "a coach loading a team outside an office",
    flag="The blueprint adds overland trucks and SGR coordination. Confirm which vehicle types the client provides before launch.", stype="Group transport"))

# ---------------- venues directory
def venues(here):
    chips = '<button class="chip" aria-pressed="true" data-r="all">All regions</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-r="{r["slug"]}">{E(r["short"])}</button>' for r in REGIONS)
    settings = sorted({r["setting"] for r in REGIONS})
    sopts = "".join(f'<option value="{E(s)}">{E(s)}</option>' for s in settings)
    blocks = []
    items = []
    pos = 0
    for r in REGIONS:
        lis = []
        for v in r["venues"]:
            pos += 1
            items.append({"@type": "ListItem", "position": pos, "item": {"@type": "Place", "name": v.rstrip("?"),
                          "containedInPlace": {"@type": "Place", "name": r["name"]}}})
            lis.append(venue_card(v, r))
        blocks.append(f"""<section class="region" id="{r['slug']}" data-r="{r['slug']}" data-trip="{r['trip']}" data-set="{E(r['setting'])}" aria-labelledby="h-{r['slug']}">
<div class="region-head"><h2 id="h-{r['slug']}">Venues in {E(r['name'])}</h2><a href="{link('/venues/' + r['slug'] + '/', here)}">Region guide</a></div>
<div class="tags"><span class="tag">{r['count']} venues</span><span class="tag">{E(TRIP[r['trip']])}</span><span class="tag">{E(r['setting'])}</span><span class="tag">{E(r['travel'])}</span></div>
<p>{E(r['intro'])}</p>
<ul class="vgrid">{''.join(lis)}</ul></section>""")
    faqs = [("Which are the best team building venues near Nairobi?", "For a one-day event, common choices within about two hours of Nairobi include Lukenya Getaway, Maanzoni Lodge, Brackenhurst Hotel, Fred's Ranch in Kitengela, and gardens such as Stedmark and Zen Gardens. The best one depends on group size, budget and the activities you want."),
            ("Where should we go for a two-day team building retreat?", "Naivasha, Elementaita and Nanyuki are the usual choices for overnight retreats. They are a few hours from Nairobi and have resorts with space for group activities."),
            ("Which venues are best for adventure activities?", "Sagana, at venues such as Rapids Camp, Savage Wilderness and Sagana Getaway, is known for white-water rafting and river activities."),
            ("Do you run team building in Amboseli?", "Yes. We facilitate team building in Amboseli. Venues there are booked on request, so send us your dates and group size and we will suggest options."),
            ("Can you book a venue that is not on this list?", "Yes. The list covers the venues we use most, and we can book others on request.")]
    body = f"""
{crumbs([("Home", "/"), ("Venues", here)], here)}
<section class="page-head" style="padding-bottom:24px"><div class="wrap split">
<div><h1>Venues in Kenya, Tanzania and Uganda</h1>
<div class="answer"><p>We book and run team building events at {TOTAL} venues across {len(REGIONS)} regions, from day-trip gardens around Nairobi to lakeside resorts in Naivasha, adventure camps in Sagana, Mount Kenya lodges and beach hotels in Mombasa and Diani. Add venues to your quote and we'll check availability and prices for your dates.</p></div>
<p class="small muted">Venue list last reviewed <time datetime="{UPDATED}">{UPDATED_TEXT}</time>.</p></div>
{photo("a group on the lawn of a lakeside resort")}
</div>
<div class="wrap" style="margin-top:32px">{drive_chart(here)}</div></section>
<div class="finder" id="regions"><div class="wrap">
<div class="frow"><label class="sr" for="q">Search venues or towns</label><input id="q" type="search" placeholder="Search a venue or town, e.g. Naivasha" autocomplete="off">
<label class="sr" for="trip">Trip type</label><select id="trip"><option value="all">Day trip or overnight</option><option value="day">Day trips</option><option value="overnight">Overnight stays</option></select>
<label class="sr" for="set">Setting</label><select id="set"><option value="all">Any setting</option>{sopts}</select></div>
<div class="chips" role="group" aria-label="Filter by region">{chips}</div>
<p class="result-count" id="rc" aria-live="polite"></p>
</div></div>
<div class="wrap">{''.join(blocks)}
<p class="empty" id="empty">No venues match those filters. Clear the search, or <a href="{link('/contact-us/#quote', here)}">tell us what you need</a> and we'll suggest options, including venues not listed here.</p>
<section class="tight">{confirm(f"Capacity, amenities and photos are not yet recorded for each venue. Amboseli appears in the WhatsApp catalogue but has no venues listed here yet: supply the venues used there to add it as a region. A sample <a href='{link('/venues/profile-template/', here)}'>venue profile page</a> shows the layout each venue will get.")}</section>
</div>
{faq_block(faqs, "Choosing a venue")}
{cta(here, "Not sure which venue fits?", "Send your group size, dates and budget. We come back with three venue options and a quote.")}
<script>
(function(){{var d=document,q=d.getElementById('q'),trip=d.getElementById('trip'),st=d.getElementById('set'),chips=[].slice.call(d.querySelectorAll('.chip')),regs=[].slice.call(d.querySelectorAll('.region')),empty=d.getElementById('empty'),rc=d.getElementById('rc'),cur='all';
function run(){{var t=q.value.trim().toLowerCase(),n=0,shownR=0;
regs.forEach(function(r){{var ok=(cur==='all'||r.dataset.r===cur)&&(trip.value==='all'||r.dataset.trip===trip.value||r.dataset.trip==='both')&&(st.value==='all'||r.dataset.set===st.value);
var meta=(r.querySelector('h2').textContent+' '+r.querySelector('p').textContent).toLowerCase(),k=0;
[].forEach.call(r.querySelectorAll('.vcard'),function(li){{var hit=!t||li.dataset.n.indexOf(t)>-1||meta.indexOf(t)>-1;li.hidden=!hit;if(hit)k++}});
r.hidden=!(ok&&k>0);if(!r.hidden){{n+=k;shownR++}}}});
empty.style.display=n?'none':'block';rc.textContent=n+' venue'+(n===1?'':'s')+' in '+shownR+' region'+(shownR===1?'':'s');}}
q.addEventListener('input',run);trip.addEventListener('change',run);st.addEventListener('change',run);
chips.forEach(function(c){{c.addEventListener('click',function(){{cur=c.dataset.r;chips.forEach(function(x){{x.setAttribute('aria-pressed',x===c)}});run();}})}});
run();}})();
</script>
"""
    schema = ld({"@type": "CollectionPage", "@id": DOMAIN + here + "#webpage", "url": DOMAIN + here,
                 "name": "Team building venues in Kenya, Tanzania and Uganda", "dateModified": UPDATED, "about": {"@id": ORG_ID},
                 "mainEntity": {"@type": "ItemList", "name": "Team building venues", "numberOfItems": TOTAL, "itemListElement": items}},
                crumbs_ld([("Home", "/"), ("Venues", here)]), faq_ld(faqs, here))
    return layout(here, f"{TOTAL} Team Building Venues in East Africa | Crown Masters",
                  f"Compare {TOTAL} team building venues near Nairobi and in Naivasha, Sagana, Nanyuki, Mombasa, Diani, Tanzania and Uganda. Filter by region and trip type.",
                  body, schema)
add("/venues/", venues)

def region_page(r):
    def fn(here):
        names = [v.rstrip("?") for v in r["venues"]]
        others = [o for o in REGIONS if o is not r][:3]
        faqs = [(f"How far is {r['short'] if r['short'] != 'Around Nairobi' else 'this region'} from Nairobi?",
                 f"Typical travel time is {r['travel']}. Road times vary with traffic, so we plan departures to arrive before the first activity."),
                (f"Is {r['name']} better for a day trip or an overnight stay?",
                 {"day": "It is best for day trips; most venues are close enough to return the same evening.",
                  "overnight": "It is best for overnight stays; the travel time makes a same-day return tiring.",
                  "both": "It works for both. Closer venues suit day trips, and the resorts suit one or two nights."}[r["trip"]]),
                (f"Which team building venues do you use in {r['name']}?",
                 f"We work with {r['count']} venues here, including {', '.join(names[:5])}. See the full list on this page and add any of them to your quote."),
                (f"What kind of team is {r['name']} best for?", r["best"])]
        lis = "".join(venue_card(v, r) for v in r["venues"])
        oth = "".join(f'<div class="card link"><h3><a href="{link("/venues/" + o["slug"] + "/", here)}">{E(o["short"])}</a></h3><p>{E(o["setting"])}, {o["count"]} venues.</p><p class="meta">{E(o["travel"])}</p></div>' for o in others)
        tbc = [v.rstrip("?") for v in r["venues"] if v.endswith("?")]
        body = f"""
{crumbs([("Home", "/"), ("Venues", "/venues/"), (r["short"], here)], here)}
<section class="page-head"><div class="wrap split">
<div><h1>Venues in {E(r['name'])}</h1>
<div class="answer"><p>{B['name']} books and runs team building events at {r['count']} venues in {E(r['name'])}, {E(r['travel'])} from Nairobi. {E(r['intro'])}</p></div>
<div class="tags"><span class="tag">{E(TRIP[r['trip']])}</span><span class="tag">{E(r['setting'])}</span><span class="tag">Towns: {E(', '.join(r['towns']))}</span></div>
<div class="actions"><a class="btn btn-gold" href="{link('/contact-us/#quote', here)}" data-ev="cta_region">Get venue options</a><a class="btn btn-line" href="{link('/venues/', here)}">All regions</a></div></div>
{photo(f"a team event at a venue in {r['short']}")}
</div></section>
<section style="padding-top:8px"><div class="wrap">
<h2>{r['count']} venues in {E(r['name'])}</h2>
<p class="muted">Add the venues you like to your quote. We check availability and prices for your dates.</p>
{confirm("Names marked “name to confirm” need checking against the venue's official name: " + ", ".join(tbc) + ".") if tbc else ""}
<ul class="vgrid" style="margin-top:16px">{lis}</ul>
</div></section>
<section class="band"><div class="wrap grid2">
<div><h2>Best for</h2><p>{E(r['best'])}</p></div>
<div><h2>Planning tips</h2><ul style="line-height:1.9;margin:0"><li>Typical travel: {E(r['travel'])}</li><li>{E(TRIP[r['trip']])}</li><li>Book six to eight weeks ahead for November, December and public holidays</li></ul></div>
</div></section>
{faq_block(faqs, f"Team building in {r['short']}: questions")}
<section><div class="wrap"><h2>Other regions to compare</h2><div class="grid3" style="margin-top:20px">{oth}</div></div></section>
{cta(here)}
"""
        schema = ld({"@type": "CollectionPage", "@id": DOMAIN + here + "#webpage", "url": DOMAIN + here,
                     "name": f"Team building venues in {r['name']}", "dateModified": UPDATED, "about": {"@id": ORG_ID},
                     "mainEntity": {"@type": "ItemList", "numberOfItems": r["count"], "itemListElement": [
                         {"@type": "ListItem", "position": i + 1, "item": {"@type": "Place", "name": n, "address": {"@type": "PostalAddress", "addressRegion": r["name"]}}}
                         for i, n in enumerate(names)]}},
                    crumbs_ld([("Home", "/"), ("Venues", "/venues/"), (r["short"], here)]), faq_ld(faqs, here))
        t0 = f"Team Building Venues in {r['name']}"
        title = t0 + " | Crown Masters" if len(t0) <= 49 else (t0 if len(t0) <= 62 else f"Team Building Venues: {r['short']} | Crown Masters")
        return layout(here, title,
                      (lambda dsc: dsc if len(dsc) <= 160 else f"{r['count']} team building venues in {r['name']}: {r['setting'].lower()} for {TRIP[r['trip']].lower()}. Compare venues and request a quote.")(f"{r['count']} team building venues in {r['name']}, {r['travel']} from Nairobi. Compare venues and request a quote."),
                      body, schema)
    return fn
for r in REGIONS:
    add(f"/venues/{r['slug']}/", region_page(r))

def profile_template(here):
    body = f"""
{crumbs([("Home", "/"), ("Venues", "/venues/"), ("Venue profile template", here)], here)}
<section class="page-head"><div class="wrap">
{confirm("This is a layout template, not a real venue. Each venue gets a page like this once its details and photos are collected. It is set to noindex.")}
<h1>[Venue name], [Town]</h1>
<div class="tags"><span class="tag">[Region]</span><span class="tag">[Setting]</span><span class="tag">[Day trip / overnight]</span></div>
<div class="grid3" style="margin-top:24px">{photo("venue lawn or main activity area", "wide")}{photo("conference hall or indoor breakout room", "wide")}{photo("rooms or dining area", "wide")}</div>
</div></section>
<section style="padding-top:0"><div class="wrap grid2">
<div><h2>About this venue</h2><p>[Two or three sentences: what the venue is like, what it is best for, and how far it is from Nairobi.]</p>
<h3>Best for</h3><p>[e.g. one-day events for 50 to 150 people, outdoor challenges, year-end parties]</p></div>
<div><h2>At a glance</h2><div class="tscroll"><table class="t"><tbody>
<tr><th>Group capacity</th><td>[outdoor] · [conference seated] · [rooms]</td></tr>
<tr><th>Activity spaces</th><td>[lawns, halls, pool, river, trails]</td></tr>
<tr><th>Accommodation</th><td>[number of rooms, or day venue only]</td></tr>
<tr><th>Travel from Nairobi</th><td>[time and route]</td></tr>
<tr><th>Good to know</th><td>[parking, accessibility, park fees, booking lead time]</td></tr>
</tbody></table></div>
<div class="actions"><button type="button" class="add btn" data-v="[Venue name]" aria-pressed="false">Add to quote</button></div></div>
</div></section>
{cta(here)}
"""
    return layout(here, "Venue Profile Template | Crown Masters Adventures", "Layout template for individual venue pages.", body,
                  ld(crumbs_ld([("Home", "/"), ("Venues", "/venues/"), ("Venue profile template", here)])), noindex=True)
add("/venues/profile-template/", profile_template)

# ---------------- corporate fitness
FIT_FAQ = [
    ("What is corporate fitness?", "Corporate fitness is a workout programme delivered at your workplace. Our trainers come to your premises, design sessions for your team and lead them, so staff exercise together without travelling to a gym after work."),
    ("What workouts do you offer?", "Zumba, aerobics, calisthenics, high-intensity (insanity-style) workouts, interval training and circuit training, chosen to suit your team's fitness levels."),
    ("What space do we need?", "An open area: a boardroom with the tables moved back, a parking space, a rooftop or a field near your office."),
    ("Is it suitable for staff who don't exercise?", "Yes. Everyone does a fitness test first, and sessions are scaled so beginners and regular exercisers can train side by side. We also give nutrition guidance."),
    ("How often are sessions held?", "Frequency is agreed with you; weekly and twice-weekly programmes are the most common choices for office teams."),
]

def fitness(here):
    body = f"""
{crumbs([("Home", "/"), ("Corporate fitness", here)], here)}
<section class="page-head"><div class="wrap split">
<div><h1>Corporate fitness and wellness programmes</h1>
<div class="answer"><p>{B['name']} runs corporate fitness programmes at offices in Nairobi and beyond. Our trainers fitness-test every participant, design sessions for your team and lead them on site. All you need is an open space, such as a boardroom, parking area, rooftop or nearby field.</p></div>
<div class="actions"><a class="btn btn-gold" href="#book" data-ev="cta_fit">Book a trial session</a><a class="btn btn-line" href="{link('/corporate-fitness/wellness-days/', here)}">Wellness days</a></div></div>
{photo("staff in an office car park doing a group workout")}
</div></section>

<section class="band"><div class="wrap">
<h2>Sessions we run</h2>
<div class="grid3" style="margin-top:24px">
<div class="card"><h3>Zumba</h3><p>Dance-based cardio that most beginners enjoy from the first session.</p></div>
<div class="card"><h3>Aerobics</h3><p>Low-impact, steady cardio for all fitness levels.</p></div>
<div class="card"><h3>Calisthenics</h3><p>Bodyweight strength training with no equipment needed.</p></div>
<div class="card"><h3>High-intensity workouts</h3><p>Short, demanding insanity-style sessions for teams that want a challenge.</p></div>
<div class="card"><h3>Interval training</h3><p>Alternating effort and rest, easy to scale for each person.</p></div>
<div class="card"><h3>Circuit training</h3><p>Stations that mix strength and cardio, ideal for larger groups.</p></div>
</div></div></section>

<section><div class="wrap grid2">
<div><h2>Why companies bring fitness to the office</h2><p>Most office staff sit for most of the day, and many cannot fit a gym in around work and Nairobi traffic. Over time that builds an inactive workforce and raises the risk of lifestyle diseases.</p>{photo("before and after a boardroom stretch session", "wide")}</div>
<ul style="line-height:2;margin:0">
<li>No commute to a gym: sessions happen at work</li><li>Colleagues train together and keep each other going</li>
<li>A fitness test for every participant</li><li>Nutrition guidance alongside the workouts</li>
<li>Programmes designed for your team's fitness levels</li><li>Sessions can be scheduled around shifts</li></ul>
</div></section>

<section class="band"><div class="wrap">
<h2>How a programme runs</h2>
<ol class="steps" style="margin-top:24px">
<li><h3>Planning call</h3><p>Team size, location, preferred days and any health considerations.</p></li>
<li><h3>Fitness tests</h3><p>A short test for each participant to set a starting point.</p></li>
<li><h3>Your programme</h3><p>Session types and frequency agreed with you.</p></li>
<li><h3>Sessions on site</h3><p>Our trainers lead every session at your premises.</p></li>
</ol>
{confirm("Add session frequency options, trainer names and qualifications, and one client result. None of these are on the current site.")}
</div></section>

<section id="book"><div class="wrap grid2">
<div><h2>Book a trial session</h2><p>For HR, admin and wellness coordinators. Tell us about your team and we'll suggest a programme and a date for a trial.</p>
<dl class="nap" style="margin-top:24px"><dt>Call</dt><dd><a href="tel:{B['phone']}">{B['phone_display']}</a></dd><dt>Email</dt><dd><a href="mailto:{B['email']}">{B['email']}</a></dd></dl></div>
<form class="wizard" id="fitform" novalidate>
<div class="fgrid2">
<div><label for="f-name">Your name</label><input id="f-name" name="Name" maxlength="100" required autocomplete="name"></div>
<div><label for="f-co">Company</label><input id="f-co" name="Company" maxlength="120" required autocomplete="organization"></div>
<div><label for="f-em">Work email</label><input id="f-em" name="Email" maxlength="254" type="email" required autocomplete="email"></div>
<div><label for="f-ph">Phone</label><input id="f-ph" name="Phone" maxlength="30" type="tel" autocomplete="tel"></div>
<div><label for="f-n">Staff taking part</label><input id="f-n" name="Staff" type="number" min="1" max="5000" inputmode="numeric"></div>
<div><label for="f-loc">Office location</label><input id="f-loc" name="Location" maxlength="120" placeholder="e.g. Westlands, Nairobi"></div>
<div class="full"><label for="f-type">Session types of interest</label><select id="f-type" name="Sessions"><option>Not sure yet</option><option>Zumba</option><option>Aerobics</option><option>Calisthenics</option><option>High-intensity</option><option>Interval or circuit training</option><option>A mix</option></select></div>
<div class="full"><label for="f-msg">Preferred days and anything else</label><textarea id="f-msg" name="Notes" maxlength="1500" rows="3"></textarea></div>
</div>
<p class="err" id="f-err" role="alert"></p>
<div class="wnav"><button class="btn btn-gold" type="submit" data-ev="fit_submit">Send request</button></div>
</form>
</div></section>
{faq_block(FIT_FAQ)}
{cta(here, "Bring fitness to your office", "Tell us your team size and location and we'll plan a programme and a trial session.")}
<script>
(function(){{var f=document.getElementById('fitform');f.addEventListener('submit',function(e){{e.preventDefault();var bad=[].filter.call(f.querySelectorAll('[required]'),function(x){{return !x.checkValidity()}});
if(bad.length){{document.getElementById('f-err').textContent='Please add your '+bad.map(function(x){{return x.name.toLowerCase()}}).join(', ')+'.';bad[0].focus();return}}
var l=[].map.call(f.elements,function(x){{return x.name&&x.value?x.name+': '+x.value:null}}).filter(Boolean);
location.href='mailto:{B['email']}?subject='+encodeURIComponent('Corporate fitness enquiry – '+f.Company.value)+'&body='+encodeURIComponent(l.join('\\n'));}});}})();
</script>
"""
    schema = ld({**service_ld(here, "Corporate fitness programmes", "Workplace fitness and wellness",
                              "On-site corporate fitness with fitness testing, nutrition guidance and trainer-led sessions."),
                 "hasOfferCatalog": {"@type": "OfferCatalog", "name": "Session types", "itemListElement": [
                     {"@type": "Offer", "itemOffered": {"@type": "Service", "name": n}} for n in
                     ("Zumba", "Aerobics", "Calisthenics", "High-intensity workouts", "Interval training", "Circuit training")]}},
                crumbs_ld([("Home", "/"), ("Corporate fitness", here)]), faq_ld(FIT_FAQ, here))
    return layout(here, "Corporate Fitness Programmes in Nairobi | Crown Masters",
                  "On-site corporate fitness in Nairobi: Zumba, aerobics, calisthenics, HIIT, circuit and interval training at your office, with fitness tests and nutrition guidance.",
                  body, schema)
add("/corporate-fitness/", fitness)

def wellness(here):
    faqs = [("What is a corporate wellness day?", "A wellness day is a single on-site event focused on staff health: group workouts, fitness tests and nutrition guidance, scheduled around the working day."),
            ("Can a wellness day start a longer fitness programme?", "Yes. Many companies use a wellness day to introduce staff to the trainers before starting regular sessions.")]
    body = f"""
{crumbs([("Home", "/"), ("Corporate fitness", "/corporate-fitness/"), ("Wellness days", here)], here)}
<section class="page-head"><div class="wrap split">
<div><h1>Corporate wellness days</h1>
{confirm("Wellness days and ergonomics talks are proposed in the blueprint. Confirm what the client delivers before publishing.")}
<div class="answer"><p>A corporate wellness day brings health activities to your office for a day or half day: group workouts led by our trainers, fitness tests for each participant and nutrition guidance, arranged around your team's working hours.</p></div>
<div class="actions"><a class="btn btn-gold" href="{link('/corporate-fitness/#book', here)}">Plan a wellness day</a></div></div>
{photo("a wellness day station with staff taking a fitness test")}
</div></section>
<section class="band"><div class="wrap">
<h2>What a wellness day can include</h2>
<div class="grid3" style="margin-top:24px">
<div class="card"><h3>Fitness tests</h3><p>A quick baseline for every participant.</p></div>
<div class="card"><h3>Group workouts</h3><p>Short sessions staff can join between meetings.</p></div>
<div class="card"><h3>Nutrition guidance</h3><p>Practical advice on eating well around a busy work day.</p></div>
<div class="card"><h3>Desk stretches</h3><p>Simple routines staff can repeat at their desks.</p></div>
<div class="card"><h3>Ergonomics talk <span class="tbc">to confirm</span></h3><p>Setting up a desk and chair to reduce strain.</p></div>
<div class="card"><h3>Team challenge</h3><p>A friendly competition to end the day.</p></div>
</div></div></section>
{faq_block(faqs)}
{cta(here, "Plan a wellness day", "Tell us your date, headcount and location.")}
"""
    schema = ld(service_ld(here, "Corporate wellness days", "Workplace wellness event", "On-site corporate wellness days with workouts, fitness tests and nutrition guidance."),
                crumbs_ld([("Home", "/"), ("Corporate fitness", "/corporate-fitness/"), ("Wellness days", here)]), faq_ld(faqs, here))
    return layout(here, "Corporate Wellness Days in Nairobi | Crown Masters Adventures",
                  "On-site corporate wellness days: group workouts, fitness tests, nutrition guidance and desk stretches for your team, arranged around the working day.", body, schema)
add("/corporate-fitness/wellness-days/", wellness)

# ---------------- articles
ARTICLES = [
    ("/blog/plan-team-building-event-kenya/", "How to plan a corporate team building event in Kenya",
     "A step-by-step plan for organisers: goals, budget, dates, venue, activities and logistics.", "plan"),
    ("/blog/team-building-venues-near-nairobi/", "Team building near Nairobi: day trip or overnight?",
     "How travel time, budget and goals decide between a one-day event and a retreat.", "near"),
    ("/blog/choose-team-building-company-kenya/", "How to choose a team building company in Kenya",
     "What to check before you hire team building facilitators: fit, safety, venues, pricing and proof.", "choose"),
    ("/blog/team-building-budget-kenya/", "What goes into a team building budget in Kenya",
     "Every cost line explained, so your quote holds no surprises.", "budget"),
]

def article(path, title, summary, key):
    def fn(here):
        if key == "plan":
            toc = ["Start with the goal", "Fix headcount, budget and dates", "Choose a region by travel time", "Decide day trip or overnight", "Pick activities that fit everyone", "Plan transport and timings", "Tell staff what to expect", "Follow up afterwards"]
            content = f"""
<p>A good team building event is planned backwards from what you want the team to do differently afterwards. These eight steps take you from a vague brief to a confirmed booking.</p>
<h2 id="s1">1. Start with the goal</h2><p>Write one sentence on why the event is happening. Common goals are helping a new team get to know each other, rebuilding communication after a hard quarter, or rewarding a strong year. The goal decides almost everything else: a reward trip needs a nice venue and light activities; a communication goal needs a skilled facilitator and a proper debrief.</p>
<h2 id="s2">2. Fix headcount, budget and dates</h2><p>Get an approved budget and a headcount range before you contact venues. Give two or three possible dates. November and December fill up fast for year-end events, as do weekends around public holidays, so allow six to eight weeks for those periods.</p>
<h2 id="s3">3. Choose a region by travel time</h2><p>Travel eats into the day. Venues around Nairobi are 30 minutes to two hours away; Naivasha and Sagana about two to three hours; Nanyuki three to four. See our <a href="{link('/venues/', here)}">venue directory</a> for typical times to each region.</p>
<h2 id="s4">4. Decide day trip or overnight</h2><p>A day trip is simpler and cheaper. An overnight stay gives time for an evening together, which is often where relationships form. Read <a href="{link('/blog/team-building-venues-near-nairobi/', here)}">day trip or overnight</a> for the trade-offs.</p>
<h2 id="s5">5. Pick activities that fit everyone</h2><p>Choose activities that every person can take part in, with lower-intensity roles for those who need them. Mix team challenges with at least one activity that needs the whole group. Leave 30 minutes for a debrief at the end.</p>
<h2 id="s6">6. Plan transport and timings</h2><p>Book transport with the event so departures, arrival and return are timed together. Share the schedule with staff a week ahead, including the departure point and return time.</p>
<h2 id="s7">7. Tell staff what to expect</h2><p>Send a short note: the date, what to wear, what to bring, the schedule, and any dietary or accessibility needs you need to know about. Anxiety about unknown activities is the main reason people stay away.</p>
<h2 id="s8">8. Follow up afterwards</h2><p>Within a week, share photos and the two or three things the team agreed in the debrief. That is what turns a fun day into a change at work.</p>
<p>Use our free <a href="{link('/planning-checklist/', here)}">planning checklist and budget planner</a> to track each step.</p>"""
        elif key == "near":
            toc = ["The short answer", "When a day trip is right", "When to stay overnight", "Regions compared"]
            rows = "".join(f'<tr><td><a href="{link("/venues/" + r["slug"] + "/", here)}">{E(r["short"])}</a></td><td>{E(r["travel"])}</td><td>{E(TRIP[r["trip"]])}</td><td>{r["count"]}</td></tr>' for r in REGIONS[:6])
            content = f"""
<h2 id="s1">The short answer</h2><p>Stay within about two hours of Nairobi for a one-day event; go further, to Naivasha, Nanyuki or the coast, only if you stay at least one night. Long drives on a day trip leave little time for the activities.</p>
<h2 id="s2">When a day trip is right</h2><ul><li>Budgets that cannot cover accommodation</li><li>Large groups, where rooms are hard to find</li><li>Staff with family commitments who cannot stay away</li><li>Goals that need a focused few hours, not a retreat</li></ul>
<h2 id="s3">When to stay overnight</h2><ul><li>Leadership and strategy retreats that need two days of thinking time</li><li>Reward trips, where rest is part of the purpose</li><li>Teams from different offices meeting for the first time</li><li>Programmes that include an evening event</li></ul>
<h2 id="s4">Regions compared</h2><div class="tscroll"><table class="t"><thead><tr><th>Region</th><th>Travel from Nairobi</th><th>Best for</th><th>Venues</th></tr></thead><tbody>{rows}</tbody></table></div>
<p class="small muted">Travel times are approximate and depend on traffic.</p>"""
        elif key == "choose":
            toc = ["Start from your goal", "Ask who will facilitate on the day", "Check how safety is handled", "Look at venues and logistics together", "Compare quotes line by line", "Where affordable packages really save money", "Ask for proof", "Questions to send every provider", "How Crown Masters Adventures fits"]
            content = f"""
<p>Searches for the best team building facilitators or the best corporate team building companies in Kenya return long lists that all sound alike. The best company for your team is the one that fits your goal, your group and your budget. These checks help an HR or admin lead compare providers fairly.</p>
<h2 id="s1">Start from your goal</h2><p>Decide what the day is for before you ask for quotes: a new team getting to know each other, better communication between departments, or a reward after a strong year. A good provider asks about this first and shapes the programme around it. Be wary of a fixed list of games sent before anyone has asked what you want to achieve.</p>
<h2 id="s2">Ask who will facilitate on the day</h2><p>The facilitator matters more than the venue. Ask who will lead your event, how many facilitators come for your group size, and how they end the day. A short debrief that links the activities back to work is what separates team building from a day out.</p>
<h2 id="s3">Check how safety is handled</h2><p>For adventure activities such as white-water rafting at Sagana or cycling at Hell's Gate, ask who provides the equipment, who briefs the group, and what the plan is for people who prefer not to take part. Ask about the wet-weather plan too, since rain can change an outdoor programme at short notice.</p>
<h2 id="s4">Look at venues and logistics together</h2><p>An event has four moving parts: the venue, meals, transport and the programme. When one company handles all four, timings line up and there is one person to call. Ask how many venues the provider can offer in your preferred region, so you are choosing from options and not being steered to one place. Our <a href="{link('/venues/', here)}">venue directory</a> shows what is available by region.</p>
<h2 id="s5">Compare quotes line by line</h2><p>Many organisations in Kenya need three quotes before approval. Send every provider the same brief (headcount, dates, region, goal and budget per person) so the quotes can be compared. Ask for each cost to be listed separately, and check that the provider issues a proper tax invoice your finance team can process. Our guide to <a href="{link('/blog/team-building-budget-kenya/', here)}">what goes into a team building budget</a> explains each line.</p>
<h2 id="s6">Where affordable packages really save money</h2><p>Real savings come from the shape of the event, not from cutting the programme:</p><ul><li>A half-day at your office or a day trip around Nairobi avoids accommodation and long transport.</li><li>Weekdays and dates outside November and December are easier to book.</li><li>One full coach costs less per person than several small vehicles.</li><li>A venue package that includes meals is usually simpler than paying for each item.</li></ul><p>Savings to question: fewer facilitators than the group needs, no wet-weather plan, and no contingency in the budget.</p>
<h2 id="s7">Ask for proof</h2><p>Read the provider's Google reviews, ask for photos from real events with groups of your size, and ask for a contact at an organisation like yours. Proof from similar teams tells you more than a long client list.</p>
<h2 id="s8">Questions to send every provider</h2><ul><li>What will the programme look like for our goal and group size?</li><li>Who facilitates, and how many facilitators will attend?</li><li>Which venues do you recommend for our dates, and why?</li><li>What is included per person, line by line?</li><li>What deposit is needed, and what is the cancellation policy?</li><li>What happens if it rains or our headcount changes?</li></ul>
<h2 id="s9">How Crown Masters Adventures fits</h2><p>{B['name']} is based in Parklands, Nairobi. We plan and facilitate the programme, book from {TOTAL} venues in {len(REGIONS)} regions across Kenya, Tanzania and Uganda, and arrange group transport, so one quote covers the whole event. Clients rate us {G['rating']} out of 5 on Google from {G['reviews']} reviews ({G['as_of']}). <a href="{link('/contact-us/#quote', here)}">Request a quote</a> with your group size, dates and budget per person.</p>"""
        else:
            toc = ["Venue", "Meals", "Accommodation", "Transport", "Facilitation and equipment", "Activity and park fees", "Contingency", "Questions to ask before you pay"]
            content = f"""
<p>Team building quotes in Kenya are usually priced per person, but they bundle several separate costs. Knowing each line helps you compare quotes fairly and spot what is missing.</p>
<h2 id="s1">Venue</h2><p>Most venues charge a per-person day or conference package that includes the grounds or a hall, and sometimes meals. Check whether exclusive use of a space costs extra.</p>
<h2 id="s2">Meals</h2><p>Morning tea, lunch and afternoon tea are standard for a day event. Confirm whether drinks and special diets are included.</p>
<h2 id="s3">Accommodation</h2><p>For overnight trips, rooms are often priced per person sharing, full board. Single rooms cost more, so agree the sharing policy early.</p>
<h2 id="s4">Transport</h2><p>Usually a fixed price per vehicle for the round trip, so the cost per person falls as more people share a coach.</p>
<h2 id="s5">Facilitation and equipment</h2><p>Facilitators, activity materials and set-up. This is where providers differ most, so ask what the facilitation fee covers.</p>
<h2 id="s6">Activity and park fees</h2><p>Some activities carry their own fees, such as rafting or entry to a national park like Hell's Gate. Check whether these are in the quote.</p>
<h2 id="s7">Contingency</h2><p>Keep 5 to 10 percent aside for late additions, extra transport or a change in headcount.</p>
<h2 id="s8">Questions to ask before you pay</h2><ul><li>What is included per person, line by line?</li><li>What deposit is needed, and when is the balance due?</li><li>What is the cancellation and headcount-change policy?</li><li>What happens if it rains?</li></ul>
<p>Our <a href="{link('/planning-checklist/', here)}#planner">budget planner</a> adds these lines up for you.</p>"""
        tochtml = "".join(f'<li><a href="#s{i + 1}">{E(t)}</a></li>' for i, t in enumerate(toc))
        body = f"""
{crumbs([("Home", "/"), ("Guides", "/blog/"), (title, here)], here)}
<article class="wrap" style="padding:24px 16px 48px">
<div class="prose">
<h1 style="font-size:clamp(2rem,4.4vw,3rem)">{E(title)}</h1>
<div class="byline"><span>By the {B['name']} team</span><span>Updated <time datetime="{UPDATED}">{UPDATED_TEXT}</time></span></div>
<div class="answer"><p>{E(summary)}</p></div>
<nav class="toc" aria-label="In this guide"><b>In this guide</b><ol>{tochtml}</ol></nav>
{content}
</div>
</article>
<section class="band tight"><div class="wrap grid2"><div><h2>Free planning checklist and budget planner</h2><p>Every step in one list, plus a planner that totals your costs per person. No sign-up needed.</p></div><div class="actions"><a class="btn btn-gold" href="{link('/planning-checklist/', here)}" data-ev="lead_checklist">Open the checklist</a></div></div></section>
{cta(here)}
"""
        schema = ld({"@type": "Article", "@id": DOMAIN + here + "#article", "headline": title, "description": summary,
                     "datePublished": UPDATED, "dateModified": UPDATED, "author": {"@id": ORG_ID}, "publisher": {"@id": ORG_ID},
                     "mainEntityOfPage": DOMAIN + here, "inLanguage": "en-KE"},
                    crumbs_ld([("Home", "/"), ("Guides", "/blog/"), (title, here)]))
        return layout(here, title if len(title) > 48 else f"{title} | Crown Masters", summary + " A planning guide from Crown Masters Adventures, Nairobi.", body, schema, og_type="article")
    return fn
for p, t, s, k in ARTICLES:
    add(p, article(p, t, s, k))

def blog(here):
    cards = "".join(f'<div class="card link">{photo("article image", "short")}<h3 style="margin-top:16px"><a href="{link(p, here)}">{E(t)}</a></h3><p>{E(s)}</p><p class="meta">Updated {UPDATED_TEXT}</p></div>' for p, t, s, _ in ARTICLES)
    body = f"""
{crumbs([("Home", "/"), ("Guides", here)], here)}
<section class="page-head"><div class="wrap">
<h1>Team building planning guides</h1>
<p class="lede">Practical guides for HR, admin and office managers who have been asked to organise the next team event.</p>
<div class="grid4" style="margin-top:32px">{cards}</div>
{confirm("Publish one new guide a month. Suggested next topics: icebreakers for new teams, team building in the rainy season, a Naivasha retreat programme, and case studies from real events.")}
</div></section>
{cta(here)}
"""
    schema = ld({"@type": "Blog", "@id": DOMAIN + here + "#blog", "url": DOMAIN + here, "name": "Team building planning guides",
                 "publisher": {"@id": ORG_ID}, "blogPost": [{"@type": "BlogPosting", "headline": t, "url": DOMAIN + p} for p, t, _, _ in ARTICLES]},
                crumbs_ld([("Home", "/"), ("Guides", here)]))
    return layout(here, "Team Building Planning Guides | Crown Masters Adventures",
                  "Guides for HR and office managers planning team building in Kenya: step-by-step planning, day trip or overnight, and budgeting.", body, schema)
add("/blog/", blog)

def checklist(here):
    tasks = ["Write one sentence on the goal of the event", "Agree the budget and who approves it", "Confirm a headcount range",
             "Choose two or three possible dates", "Pick a region by travel time", "Decide day trip or overnight",
             "Shortlist venues and request quotes", "Agree the programme and activities", "Book transport and confirm timings",
             "Collect dietary and accessibility needs", "Send staff the schedule and packing list", "Confirm final numbers with the venue",
             "Share photos and debrief notes afterwards"]
    lis = "".join(f'<li><input type="checkbox" id="c{i}"><label for="c{i}">{E(t)}</label></li>' for i, t in enumerate(tasks))
    body = f"""
{crumbs([("Home", "/"), ("Planning checklist", here)], here)}
<section class="page-head"><div class="wrap">
<h1>Team building planning checklist and budget planner</h1>
<p class="lede">Tick off each step as you go and total your costs per person. Your ticks are saved in this browser. Print it to share with your manager.</p>
<div class="actions noprint"><button class="btn btn-line" type="button" id="print-btn">Print or save as PDF</button></div>
</div></section>
<section style="padding-top:0"><div class="wrap grid2">
<div><h2>Checklist</h2><ul class="check" id="checklist">{lis}</ul></div>
<div id="planner"><h2>Budget planner</h2><p class="muted small">Enter the figures from your quotes in Kenya shillings. Nothing is sent anywhere.</p>
<form class="planner" id="pl">
<div class="fgrid2">
<div><label for="p-n">People</label><input id="p-n" type="number" min="1" max="5000" value="50" inputmode="numeric"></div>
<div><label for="p-v">Venue package per person</label><input id="p-v" type="number" min="0" value="0" inputmode="numeric"></div>
<div><label for="p-nights">Nights</label><input id="p-nights" type="number" min="0" value="0" inputmode="numeric"></div>
<div><label for="p-room">Accommodation per person per night</label><input id="p-room" type="number" min="0" value="0" inputmode="numeric"></div>
<div><label for="p-t">Transport, total</label><input id="p-t" type="number" min="0" value="0" inputmode="numeric"></div>
<div><label for="p-f">Facilitation and equipment, total</label><input id="p-f" type="number" min="0" value="0" inputmode="numeric"></div>
<div><label for="p-a">Activity or park fees per person</label><input id="p-a" type="number" min="0" value="0" inputmode="numeric"></div>
<div><label for="p-c">Contingency %</label><input id="p-c" type="number" min="0" max="50" value="10" inputmode="numeric"></div>
</div>
<div class="ptotal" aria-live="polite"><div>Total<b id="p-total">KES 0</b></div><div>Per person<b id="p-pp">KES 0</b></div></div>
</form></div>
</div></section>
{cta(here, "Want us to fill in the numbers?", "Send your headcount and dates and we'll quote each line.")}
<script>
function calc(){{var g=function(i){{return Math.max(0,parseFloat(document.getElementById(i).value)||0)}};var n=Math.max(1,g('p-n'));
var sub=n*g('p-v')+n*g('p-nights')*g('p-room')+g('p-t')+g('p-f')+n*g('p-a');var tot=sub*(1+g('p-c')/100);
var fmt=function(x){{return 'KES '+Math.round(x).toLocaleString('en-KE')}};document.getElementById('p-total').textContent=fmt(tot);document.getElementById('p-pp').textContent=fmt(tot/n);}}
calc();document.getElementById('pl').addEventListener('input',calc);document.getElementById('print-btn').addEventListener('click',function(){{window.print()}});
(function(){{var K='cma_checklist',s;try{{s=JSON.parse(localStorage.getItem(K)||'{{}}')}}catch(e){{s={{}}}}
[].forEach.call(document.querySelectorAll('#checklist input'),function(c){{c.checked=!!s[c.id];c.addEventListener('change',function(){{s[c.id]=c.checked;try{{localStorage.setItem(K,JSON.stringify(s))}}catch(e){{}}}})}});}})();
</script>
"""
    schema = ld(page_ld(here, "Team building planning checklist and budget planner"), crumbs_ld([("Home", "/"), ("Planning checklist", here)]))
    return layout(here, "Free Team Building Checklist & Budget Planner | Crown Masters",
                  "Free team building planning checklist and budget planner: 13 steps from goal to debrief, and a calculator that totals your costs per person.", body, schema)
add("/planning-checklist/", checklist)

# ---------------- about
def about(here):
    body = f"""
{crumbs([("Home", "/"), ("About", here)], here)}
<section class="page-head"><div class="wrap split">
<div><h1>About {B['name']}</h1>
<div class="answer"><p>{B['name']} is a corporate team building company based at {E(B['street'])}, Nairobi. We plan and facilitate team building events, book venues across Kenya, Tanzania and Uganda, run corporate fitness programmes, and arrange group transport, getaways and expeditions.</p></div>
{confirm("Add the year the company started, the founder's name and story, and the size of the team. Google and AI assistants weigh who is behind a business when deciding whom to recommend.")}</div>
{photo("the Crown Masters team together, smiling, at a venue")}
</div></section>
<section class="band"><div class="wrap grid3">
<div><h2>What we believe</h2><p>A team building day should change something at work on Monday. That is why every programme starts with a goal and ends with a debrief.</p></div>
<div><h2>How we work</h2><p>One contact person from the first call to the last coach home. Written programmes and line-by-line quotes, so there are no surprises.</p></div>
<div><h2>Where we work</h2><p>From our Parklands office we run events at {TOTAL} venues in {len(REGIONS)} regions, and at clients' own offices.</p></div>
</div></section>
<section><div class="wrap">
<h2>Our team</h2>
<div class="grid4" style="margin-top:24px">{''.join(f'<div class="card">{photo("team member portrait", "tall")}<h3 style="margin-top:12px">[Name]</h3><p class="muted">[Role] · [one line of experience]</p></div>' for _ in range(4))}</div>
</div></section>
{cta(here)}
"""
    schema = ld({"@type": "AboutPage", "@id": DOMAIN + here + "#webpage", "url": DOMAIN + here, "name": f"About {B['name']}", "about": {"@id": ORG_ID}},
                crumbs_ld([("Home", "/"), ("About", here)]))
    return layout(here, "About Us | Crown Masters Adventures, Nairobi",
                  "Crown Masters Adventures is a Nairobi team building company in Parklands: team building events, venue booking, corporate fitness and group transport.", body, schema)
add("/about-us/", about)

# ---------------- contact / quote engine
def contact(here):
    regs = "".join(f'<option>{E(r["name"])}</option>' for r in REGIONS)
    budgets = ["Not sure yet", "Under KES 3,000", "KES 3,000 to 6,000", "KES 6,000 to 10,000", "KES 10,000 to 20,000", "Over KES 20,000"]
    bopts = "".join(f"<option>{E(b)}</option>" for b in budgets)
    maps_q = "Park+Place,+2nd+Avenue,+Parklands,+Nairobi"
    body = f"""
{crumbs([("Home", "/"), ("Contact", here)], here)}
<section class="page-head" style="padding-bottom:24px"><div class="wrap">
<h1>Request a team building quote</h1>
<p class="lede">Four short steps. We usually need your group size, dates and a budget range to send venue options and a price.</p>
</div></section>
<section style="padding-top:0"><div class="wrap split" style="align-items:start">
<form class="wizard" id="quote" novalidate>
<ol class="progress" aria-label="Quote steps"><li class="on">1. You</li><li>2. Event</li><li>3. Place</li><li>4. Budget</li></ol>

<fieldset class="wstep" data-step="0" style="border:0;padding:0;margin:0"><legend class="sr">About you</legend>
<h2 style="font-size:1.4rem">About you</h2>
<div class="fgrid2">
<div><label for="q-name">Your name</label><input id="q-name" name="Name" maxlength="100" required autocomplete="name"></div>
<div><label for="q-co">Company</label><input id="q-co" name="Company" maxlength="120" required autocomplete="organization"></div>
<div><label for="q-em">Work email</label><input id="q-em" name="Email" maxlength="254" type="email" required autocomplete="email"></div>
<div><label for="q-ph">Phone or WhatsApp</label><input id="q-ph" name="Phone" maxlength="30" type="tel" required autocomplete="tel"></div>
</div></fieldset>

<fieldset class="wstep" data-step="1" hidden style="border:0;padding:0;margin:0"><legend class="sr">Your event</legend>
<h2 style="font-size:1.4rem">Your event</h2>
<div class="fgrid2">
<div class="full"><label for="q-svc">What do you need?</label><select id="q-svc" name="Service"><option>Team building event</option><option>Venue booking only</option><option>Corporate fitness</option><option>Transport hire</option><option>Getaway or expedition</option><option>Private event (baby shower, graduation, birthday)</option></select></div>
<div><label for="q-n">Group size</label><input id="q-n" name="Group size" type="number" min="1" max="5000" required inputmode="numeric"></div>
<div><label for="q-d">Preferred date</label><input id="q-d" name="Preferred date" type="date" required><label class="chk" for="q-flex"><input id="q-flex" type="checkbox" name="Dates flexible" value="Yes">My dates are flexible</label></div>
<div class="full"><span style="display:block;font-weight:700;margin-bottom:6px">Duration</span><div class="radio-cards" role="radiogroup">
<label><input type="radio" name="Duration" value="Half day"><b>Half day</b><small>At your office or nearby</small></label>
<label><input type="radio" name="Duration" value="Day trip" checked><b>Day trip</b><small>Back the same evening</small></label>
<label><input type="radio" name="Duration" value="Overnight"><b>Overnight</b><small>One night or more</small></label></div></div>
</div></fieldset>

<fieldset class="wstep" data-step="2" hidden style="border:0;padding:0;margin:0"><legend class="sr">Where</legend>
<h2 style="font-size:1.4rem">Where</h2>
<label for="q-reg">Region</label><select id="q-reg" name="Region"><option>Not sure, please suggest</option><option>At our office</option>{regs}</select>
<div style="margin-top:16px"><span style="display:block;font-weight:700">Venues added to your quote</span><div class="picked" id="picked"></div>
<p class="hint" id="picked-hint">None yet. You can <a href="{link('/venues/', here)}">browse venues</a> and add any you like.</p></div>
<div style="margin-top:12px"><label for="q-ven">Other venues you have in mind</label><input id="q-ven" name="Other venues" maxlength="300"></div>
</fieldset>

<fieldset class="wstep" data-step="3" hidden style="border:0;padding:0;margin:0"><legend class="sr">Budget and notes</legend>
<h2 style="font-size:1.4rem">Budget and anything else</h2>
<label for="q-b">Budget per person</label><select id="q-b" name="Budget per person">{bopts}</select>
<p class="hint">A rough range helps us shortlist venues you can afford. Try the <a href="{link('/planning-checklist/#planner', here)}">budget planner</a>.</p>
<div style="margin-top:12px"><label for="q-m">Goals, activities or questions</label><textarea id="q-m" name="Notes" maxlength="1500" rows="4"></textarea></div>
<h3 style="margin-top:20px">Your request</h3><pre class="review" id="review"></pre>
<p class="hint">By sending, you agree we may contact you about this request. See our <a href="{link('/privacy-policy/', here)}">privacy policy</a>.</p>
</fieldset>

<p class="err" id="q-err" role="alert"></p>
<div class="wnav"><button type="button" class="btn btn-line" id="back" hidden>Back</button><span></span>
<button type="button" class="btn btn-gold" id="next">Continue</button>
<span id="send" hidden style="gap:10px;flex-wrap:wrap"><button type="button" class="btn btn-gold" id="send-email" data-ev="quote_email">Send by email</button><button type="button" class="btn btn-line" id="send-wa" data-ev="quote_whatsapp">Send on WhatsApp</button></span></div>
<p class="hint">Demo: sending opens your email app or WhatsApp with the request filled in. In production the form posts to the site's form handler and shows the thank-you page.</p>
</form>
<div class="wizard sent" id="sent" hidden tabindex="-1" role="status">
<div class="tick"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg></div>
<h2 style="font-size:1.6rem">Request sent</h2>
<p>Thank you. We will come back to you with venue options and a quote.</p>
<p class="hint">If your email app or WhatsApp opened with the request filled in, press send there to finish. This form has been cleared.</p>
<div class="actions"><button type="button" class="btn btn-line" id="again">Start a new request</button></div>
</div>

<aside>
<h2>Contact details</h2>
<dl class="nap">
<dt>Office</dt><dd>{E(B['street'])}, {B['city']}</dd>
<dt>Phone</dt><dd><a href="tel:{B['phone']}" data-ev="tel_contact">{B['phone_display']}</a></dd>
<dt>WhatsApp</dt><dd><a href="{B['whatsapp']}" rel="noopener noreferrer" data-ev="whatsapp_contact">{B['phone_display']}</a></dd>
<dt>Email</dt><dd><a href="mailto:{B['email']}" data-ev="email_contact">{B['email']}</a></dd>
<dt>Hours</dt><dd>{E(B['hours_display'])}</dd>
</dl>
<iframe class="map" style="margin-top:24px" title="Map showing the Crown Masters Adventures office in Parklands, Nairobi" loading="lazy" referrerpolicy="no-referrer-when-downgrade" src="https://www.google.com/maps?q={maps_q}&output=embed"></iframe>
{confirm("Confirm the exact office pin and opening hours, then claim the Google Business Profile so the map and reviews match this page.")}
</aside>
</div></section>
<script>
(function(){{var f=document.getElementById('quote'),steps=[].slice.call(f.querySelectorAll('.wstep')),prog=[].slice.call(f.querySelectorAll('.progress li')),cur=0,
next=document.getElementById('next'),back=document.getElementById('back'),send=document.getElementById('send'),err=document.getElementById('q-err');
function picked(){{var v=window.CMA.get(),box=document.getElementById('picked');box.textContent='';v.forEach(function(n){{var s=document.createElement('span');s.textContent=n;box.appendChild(s)}});document.getElementById('picked-hint').style.display=v.length?'none':'block';}}
var dt=document.getElementById('q-d');
function today(){{var n=new Date();return n.getFullYear()+'-'+('0'+(n.getMonth()+1)).slice(-2)+'-'+('0'+n.getDate()).slice(-2)}}
function setMin(){{dt.min=today()}}setMin();dt.addEventListener('focus',setMin);
function nice(v){{var p=v.split('-');if(p.length!==3)return v;return new Date(+p[0],p[1]-1,+p[2]).toLocaleDateString('en-KE',{{weekday:'long',day:'numeric',month:'long',year:'numeric'}})}}
function summary(){{var l=[];[].forEach.call(f.elements,function(x){{if(!x.name||!x.value)return;if((x.type==='radio'||x.type==='checkbox')&&!x.checked)return;l.push(x.name+': '+(x.type==='date'?nice(x.value):x.value))}});var v=window.CMA.get();if(v.length)l.push('Shortlisted venues: '+v.join(', '));return l.join('\\n');}}
function show(i){{cur=i;steps.forEach(function(s,j){{s.hidden=j!==i}});prog.forEach(function(p,j){{p.className=j<i?'done':(j===i?'on':'')}});
back.hidden=i===0;var last=i===steps.length-1;next.hidden=last;send.hidden=!last;send.style.display=last?'flex':'';err.textContent='';
if(last)document.getElementById('review').textContent=summary();if(i===2)picked();var h=steps[i].querySelector('h2');if(h){{h.tabIndex=-1;h.focus()}}
window.CMA_track('quote_step',{{step:i+1}});}}
function valid(){{var bad=[].filter.call(steps[cur].querySelectorAll('[required]'),function(x){{return !x.checkValidity()}});
setMin();if(steps[cur].contains(dt)&&dt.value&&dt.value<dt.min){{err.textContent='That date has already passed. Please choose today or a later date.';dt.focus();return false}}
if(bad.length){{err.textContent='Please check: '+bad.map(function(x){{return x.name.toLowerCase()}}).join(', ')+'.';bad[0].focus();return false}}return true}}
next.addEventListener('click',function(){{if(valid())show(cur+1)}});back.addEventListener('click',function(){{show(cur-1)}});
var sent=document.getElementById('sent');
function done(how){{window.CMA_track('generate_lead',{{method:how,service:f.Service.value}});window.setTimeout(function(){{f.reset();window.CMA.set([]);show(0);f.hidden=true;sent.hidden=false;sent.focus()}},400)}}
document.getElementById('again').addEventListener('click',function(){{sent.hidden=true;f.hidden=false;show(0)}});
document.getElementById('send-email').addEventListener('click',function(){{location.href='mailto:{B['email']}?subject='+encodeURIComponent('Quote request – '+f.Company.value)+'&body='+encodeURIComponent(summary());done('email');}});
document.getElementById('send-wa').addEventListener('click',function(){{window.open('{B['whatsapp']}?text='+encodeURIComponent('Quote request\\n'+summary()),'_blank','noopener,noreferrer');done('whatsapp');}});
document.addEventListener('shortlist',picked);show(0);
var h1=document.querySelector('h1');if(h1)h1.focus&&false;}})();
</script>
"""
    schema = ld({"@type": "ContactPage", "@id": DOMAIN + here + "#webpage", "url": DOMAIN + here, "name": f"Contact {B['name']}", "about": {"@id": ORG_ID}},
                crumbs_ld([("Home", "/"), ("Contact", here)]))
    return layout(here, "Contact Us & Request a Quote | Crown Masters Adventures",
                  f"Request a team building, venue or fitness quote in four steps, or call or WhatsApp {B['phone_display']}. Office in Parklands, Nairobi.",
                  body, schema)
add("/contact-us/", contact)

def thanks(here):
    body = f"""<section><div class="wrap narrow"><h1>Thank you, your request is in</h1><p class="lede">We'll reply with venue options and a quote. If it's urgent, call or WhatsApp <a href="tel:{B['phone']}">{B['phone_display']}</a>.</p>
<h2>While you wait</h2><ul><li><a href="{link('/planning-checklist/', here)}">Use the planning checklist</a></li><li><a href="{link('/blog/', here)}">Read our planning guides</a></li><li><a href="{link('/venues/', here)}">Browse more venues</a></li></ul></div></section>"""
    return layout(here, "Thank You | Crown Masters Adventures", "Your quote request has been received.", body, ld(), noindex=True)
add("/contact-us/thank-you/", thanks)

def privacy(here):
    if GA:
        cookies = ("<p>With your consent, we use Google Analytics 4 to count visits and see which pages and buttons are used, so we can improve the site. "
                   "It sets cookies in your browser and sends usage data to Google. It does not run unless you choose Accept on the cookie notice, "
                   'and you can change your choice at any time with the "Cookie settings" link at the bottom of every page.</p>'
                   "<p>This site also saves your venue shortlist, checklist ticks and cookie choice in your own browser. These stay on your device.</p>")
    else:
        cookies = "<p>This site does not use analytics or advertising cookies. It saves your venue shortlist and checklist ticks in your own browser only; these stay on your device.</p>"
    body = f"""
{crumbs([("Home", "/"), ("Privacy policy", here)], here)}
<section class="page-head"><div class="wrap prose">
<h1>Privacy policy</h1>
{confirm("Draft for review by the client's lawyer. Kenya's Data Protection Act, 2019 applies to personal data collected through this site.")}
<p class="muted">Last updated <time datetime="{UPDATED}">{UPDATED_TEXT}</time></p>
<h2>Who we are</h2><p>{B['name']}, {E(B['street'])}, Nairobi, Kenya. Contact: <a href="mailto:{B['email']}">{B['email']}</a>.</p>
<h2>What we collect</h2><p>When you request a quote or book a session, we collect your name, company, email, phone number and the event details you give us. If you message us on WhatsApp, we receive the details you send there.</p>
<h2>How we use it</h2><p>Only to reply to your request, prepare quotes and deliver the services you book. We do not sell your data.</p>
<h2>Who we share it with</h2><p>Venues and transport providers, only as needed to check availability and make your booking.</p>
<h2>How long we keep it</h2><p>[Retention period to confirm, for example 24 months after your last enquiry.]</p>
<h2>Your rights</h2><p>You can ask to see, correct or delete your data by emailing us.</p>
<h2>Cookies and analytics</h2>{cookies}
</div></section>"""
    return layout(here, "Privacy Policy | Crown Masters Adventures", "How Crown Masters Adventures collects and uses personal data from enquiries and bookings.", body,
                  ld(crumbs_ld([("Home", "/"), ("Privacy policy", here)])))
add("/privacy-policy/", privacy)

def notfound(here):
    body = f"""<section><div class="wrap narrow"><h1>We couldn't find that page</h1><p class="lede">It may have moved when we rebuilt the site. These links should get you there:</p>
<ul style="line-height:2"><li><a href="{link('/team-building/', here)}">Team building</a></li><li><a href="{link('/venues/', here)}">All {TOTAL} venues</a></li><li><a href="{link('/corporate-fitness/', here)}">Corporate fitness</a></li><li><a href="{link('/contact-us/#quote', here)}">Request a quote</a></li></ul></div></section>"""
    return layout(here, "Page Not Found | Crown Masters Adventures", "Page not found.", body, ld(), noindex=True)
add("/404.html", notfound)

# ================================================================== extras
def extras():
    idx = [p for p, _ in pages if p not in ("/404.html", "/contact-us/thank-you/", "/venues/profile-template/")]
    sm = "".join(f"<url><loc>{DOMAIN}{p}</loc><lastmod>{UPDATED}</lastmod></url>" for p in idx)
    files = {
        "sitemap.xml": f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{sm}</urlset>\n',
        "robots.txt": f"""# Crown Masters Adventures
User-agent: *
Allow: /
Disallow: /contact-us/thank-you/

# Search and AI answer engines are welcome, so the business can be found and cited
User-agent: Googlebot
Allow: /
User-agent: Bingbot
Allow: /
User-agent: Google-Extended
Allow: /
User-agent: GPTBot
Allow: /
User-agent: OAI-SearchBot
Allow: /
User-agent: ChatGPT-User
Allow: /
User-agent: ClaudeBot
Allow: /
User-agent: Claude-SearchBot
Allow: /
User-agent: PerplexityBot
Allow: /
User-agent: Applebot-Extended
Allow: /

Sitemap: {DOMAIN}/sitemap.xml
""",
        "_redirects": "\n".join([
            "# 301 redirects for Cloudflare Pages / Netlify. Keep legacy URLs alive.",
            "/home/            /                     301",
            "/teambuilding/    /team-building/       301",
            "/corporatefitness/ /corporate-fitness/  301",
            "/contact/         /contact-us/          301",
            "/newsite/*        /:splat               301",
            "/wp-content/uploads/2022/03/location-1024x683.jpg /assets/og-default.jpg 301",
            "/category/*       /blog/                301",
            "/feed/            /blog/                301",
            "", ]),
        "_headers": "\n".join([
            "# Security headers for Cloudflare Pages / Netlify. Each page also carries its own CSP meta tag.",
            "/*",
            "  Strict-Transport-Security: max-age=63072000; includeSubDomains; preload",
            "  Content-Security-Policy: " + CSP_BASE.format(hashes=" ".join(sorted(SCRIPT_HASHES))) + "; frame-ancestors 'none'; upgrade-insecure-requests",
            "  X-Content-Type-Options: nosniff",
            "  X-Frame-Options: DENY",
            "  Referrer-Policy: strict-origin-when-cross-origin",
            "  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
            "  Cross-Origin-Opener-Policy: same-origin",
            "  Cross-Origin-Resource-Policy: same-origin",
            "", ]),
        "assets/favicon.svg": LOGO_SVG.replace('width="40" height="40" ', 'xmlns="http://www.w3.org/2000/svg" ').replace(' aria-hidden="true"', ""),
        "assets/logo.svg": LOGO_SVG.replace('width="40" height="40" ', 'xmlns="http://www.w3.org/2000/svg" ').replace(' aria-hidden="true"', ""),
    }
    reg = "\n".join(f"- [{r['name']}]({DOMAIN}/venues/{r['slug']}/): {r['count']} venues, {r['setting'].lower()}, {r['travel']} from Nairobi. Best for: {r['best']}" for r in REGIONS)
    files["llms.txt"] = f"""# {B['name']}

> Corporate team building company based in Parklands, Nairobi, Kenya. Plans and facilitates team building events, books {TOTAL} team building venues across Kenya, Tanzania and Uganda, runs on-site corporate fitness programmes, and arranges group transport.

## Contact
- Office: {B['street']}, {B['city']}, Kenya
- Phone and WhatsApp: {B['phone_display']}
- Email: {B['email']}
- Quote form: {DOMAIN}/contact-us/

## Services
- [Corporate team building]({DOMAIN}/team-building/): facilitated events for teams of all sizes, with venue, transport and meals arranged
- [Indoor team building]({DOMAIN}/team-building/indoor/): problem-solving and communication challenges in a hall or boardroom
- [Outdoor and adventure]({DOMAIN}/team-building/outdoor-adventure/): obstacle courses, treasure hunts, rafting at Sagana, cycling at Hell's Gate
- [Transport and logistics]({DOMAIN}/team-building/transport-logistics/): executive transport hire for groups, including Coaster buses with 22 to 33 seats
- [Private events]({DOMAIN}/private-events/): baby showers, graduation parties and birthdays, with venue, games and transport
- [Corporate fitness]({DOMAIN}/corporate-fitness/): Zumba, aerobics, calisthenics, HIIT, interval and circuit training at clients' offices, with fitness tests and nutrition guidance

## Venue regions
{reg}

## Guides
""" + "\n".join(f"- [{t}]({DOMAIN}{p}): {s}" for p, t, s, _ in ARTICLES) + "\n"
    files["README.md"] = f"""# Crown Masters Adventures — website demo v2

Static site generated from `data.py` by `build.py` ({len(pages)} pages).

- Open `index.html` in a browser to review the demo (links work offline).
- `python3 build.py --production` writes clean URLs (`/venues/`) for deployment.
- Edit venues, regions and contact details in `data.py`, then rebuild.
- Items marked "to confirm" (yellow notes) need client sign-off before launch.
- `_redirects` holds the 301 map for Cloudflare Pages or Netlify.
"""
    return files

# ================================================================== write
if os.path.exists(OUT):
    shutil.rmtree(OUT)
RENDERED = {}
for path, fn in pages:
    fp = os.path.join(OUT, file_of(path))
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    RENDERED[path] = fn(path)
    with open(fp, "w") as fh:
        fh.write(RENDERED[path])
for name, txt in extras().items():
    fp = os.path.join(OUT, name)
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    with open(fp, "w") as fh:
        fh.write(txt)
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
os.makedirs(os.path.join(OUT, "assets", "fonts"), exist_ok=True)
for n in os.listdir(FONT_DIR):
    shutil.copy2(os.path.join(FONT_DIR, n), os.path.join(OUT, "assets", "fonts"))
if os.path.isdir(PHOTO_DIR):
    for root, _, names in os.walk(PHOTO_DIR):
        for n in names:
            if n.lower().endswith((".jpg", ".jpeg", ".webp", ".png", ".svg")):
                dst = os.path.join(OUT, "assets", "photos", os.path.relpath(root, PHOTO_DIR))
                os.makedirs(dst, exist_ok=True)
                shutil.copy2(os.path.join(root, n), dst)
# ---- docs/PAGES.md: page inventory and launch checklist, regenerated on every production build
SANDBOX = "https://wachirachris.github.io/Crown-Masters-Adventures-Modern-Web-Platform"
def write_inventory():
    groups = [("Home", lambda p: p == "/"), ("Team building", lambda p: p.startswith("/team-building/")),
              ("Venues", lambda p: p.startswith("/venues/")), ("Corporate fitness", lambda p: p.startswith("/corporate-fitness/")),
              ("Private events", lambda p: p.startswith("/private-events/")), ("Guides", lambda p: p.startswith("/blog/")),
              ("Tools, company and contact", lambda p: True)]
    seen, out, totals = set(), [], [0, 0, 0, 0]
    for gname, test in groups:
        rows = []
        for path, _ in pages:
            if path in seen or not test(path):
                continue
            seen.add(path)
            h = RENDERED[path]
            title = html.unescape(re.search(r"<title>(.*?)</title>", h).group(1)).replace("|", "\\|")
            notes = len(re.findall(r'class="confirm"', h))
            tags = len(re.findall(r'class="tbc"', h))
            stand_in = len(re.findall(r'class="ph has-img is-placeholder', h)) + len(re.findall(r'class="hero-slide', h)) * ("hero-note" in h)
            empty = len(re.findall(r'<figure class="ph (?!has-img)', h))
            noindex = "noindex" in re.search(r'<meta name="robots" content="([^"]*)"', h).group(1)
            for i, v in enumerate((notes, tags, stand_in, empty)):
                totals[i] += v
            live = DOMAIN + ("/" if path == "/404.html" else path)
            rows.append(f"| ☐ | {title} | [{path}]({SANDBOX}{path}) | {live if path != '/404.html' else 'shown for any missing address'} | "
                        f"{notes or '-'} | {tags or '-'} | {stand_in or '-'} | {empty or '-'} | {'hidden from search' if noindex else 'yes'} |")
        if rows:
            out.append(f"## {gname} ({len(rows)})\n\n| Done | Page | Review link (sandbox) | Address at launch | To-confirm notes | To-supply tags | Placeholder photos | Empty photo slots | In Google |\n"
                       "| --- | --- | --- | --- | --- | --- | --- | --- | --- |\n" + "\n".join(rows))
    redirects = "\n".join(f"| `{a}` | `{b}` |" for a, b, _ in (l.split() for l in extras()["_redirects"].splitlines() if l.startswith("/")))
    doc = f"""# Page inventory and launch checklist

Generated by `python3 build.py --production`. Do not edit by hand: change the site and rebuild.

Last built {UPDATED_TEXT}. **{len(pages)} pages.** Across the site there are still **{totals[0]} to-confirm notes**, **{totals[1]} to-supply tags**, **{totals[2]} placeholder photos** and **{totals[3]} empty photo slots** to clear before launch.

How to use it: open each review link, clear the items counted in its row, then tick the Done box. A page is ready when every count in its row shows `-`.

- **To-confirm notes**: yellow boxes asking the client to confirm a fact or service.
- **To-supply tags**: small yellow tags where a figure or name is missing.
- **Placeholder photos**: stock images marked "PLACEHOLDER" (see `photos/placeholder/CREDITS.md`).
- **Empty photo slots**: "Photo to supply" panels with no image yet.

"""
    doc += "\n\n".join(out)
    doc += f"""

## Old addresses that redirect ({redirects.count(chr(10)) + 1})

These keep links to the old site working. They are in `site/_redirects`, which works on Cloudflare Pages and Netlify; on other hosts set them up in the server settings.

| Old address | Goes to |
| --- | --- |
{redirects}

## Files that are not pages

| File | Purpose | Check at launch |
| --- | --- | --- |
| `sitemap.xml` | List of pages for search engines | Submit in Google Search Console |
| `robots.txt` | Tells search engines and AI assistants what they may read | Opens at `{DOMAIN}/robots.txt` |
| `llms.txt` | Summary of the business for AI assistants | Opens at `{DOMAIN}/llms.txt` |
| `_headers` | Security headers | See `SECURITY.md` |
| `_redirects` | Old-address redirects | Test each row of the table above |
| `assets/og-default.jpg` | Image shown when a page is shared on WhatsApp or social media | {'Present' if os.path.exists(os.path.join(PHOTO_DIR, 'og-default.jpg')) else '**Missing.** Supply a 1200 x 630 px image'} |

## Analytics (Google Analytics 4)

Status: {"**switched on** with Measurement ID `" + GA + "`" if GA else "**built but switched off**. No Measurement ID has been added yet, so no analytics code or consent bar is in the pages"}.

To switch it on:

- [ ] Client creates a Google Analytics 4 property for `{DOMAIN.split("//")[1]}` under their own Google account
- [ ] Put its Measurement ID (looks like `G-AB12CD34EF`) in `data.py` as `ga4_id`, then rebuild with `--production`
- [ ] On the live site, check the consent bar appears, and that visits show in GA4 "Realtime" only after choosing Accept
- [ ] In GA4, mark `generate_lead` as a key event (it fires when a quote request is sent)
- [ ] In GA4, build a funnel from `quote_step` (steps 1 to 4) to `generate_lead` to see where people drop out
- [ ] Verify the domain in Google Search Console and submit `sitemap.xml`
- [ ] Have the client's lawyer review the cookie wording in the privacy policy

Events the site sends once analytics is on: `cta_click`, `phone_click`, `whatsapp_click`, `email_click` (each with a `location`), `venue_add`, `quote_step`, `quote_email`, `quote_whatsapp`, `generate_lead`, `google_reviews`, `lead_checklist`. Analytics never runs on the review sandbox.

## Site-wide items before launch

- [ ] Client has confirmed phone, email, office address and opening hours (`data.py`)
- [ ] Client list and permission to show each brand confirmed; logo files supplied (`photos/logos/`)
- [ ] Google rating and review count re-checked; review quotes supplied
- [ ] All placeholder photos replaced with client event photos
- [ ] Quote form connected to a form handler (it currently opens email or WhatsApp)
- [ ] Security launch tasks in `SECURITY.md` done
- [ ] Built with `python3 build.py --production` and deployed from `site/`
"""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "PAGES.md"), "w") as fh:
        fh.write(doc)
if PROD:
    write_inventory()
print(f"{len(pages)} pages, {TOTAL} venues, {len(REGIONS)} regions -> {OUT}{' (production)' if PROD else ''}")
