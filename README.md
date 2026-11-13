# Crown Masters Adventures — Modern Web Platform

Rebuild of [crownmastersadventures.co.ke](https://crownmastersadventures.co.ke): a fast, SEO- and AEO-optimised site for a Nairobi corporate team building company (team building events, 123 venues across Kenya, Tanzania and Uganda, corporate fitness, group transport).

**Status:** working prototype (v2), 30 pages, awaiting client content sign-off. Items still to confirm are shown on the pages as yellow notes.

## What's here

| Path | What it is |
| --- | --- |
| `data.py` | Single source of truth: business details, 10 regions, 123 venues, legacy-name corrections |
| `build.py` | Static site generator (Python 3, no dependencies) |
| `site/` | Built site, production mode (clean URLs such as `/venues/`) — ready for Cloudflare Pages, Netlify or GitHub Pages |
| `docs/BLUEPRINT.md` | Redesign blueprint v2: audit, blueprint comparison, decisions, sitemap, page spec, SEO/AEO plan, launch plan |
| `docs/client-brief/` | The client's original blueprint (PDF) and sitemap notes |
| `docs/PAGES.md` | Every page with its review link, launch address and what is still outstanding on it (regenerated on each production build) |
| `SECURITY.md` | Security checklist and launch tasks |
| `CLAUDE.md` | Project context for Claude Code sessions |

## Build

```bash
python3 build.py               # demo build: links end in index.html, opens straight from the folder
python3 build.py --production  # clean URLs for deployment (what is committed in site/)
python3 build.py --theme=emerald  # preview another palette: navy (default), emerald, savanna
```

Colours live in the `THEMES` table in `build.py` (light and dark values for each palette). Headings use Fraunces (soft cut), body text Plus Jakarta Sans, both served from `fonts/`.

Edit content in `data.py` (venues, regions, phone, email, hours, geo, founding year), then rebuild. Setting `opening_hours`, `geo` and `founded` switches them on in the LocalBusiness schema automatically.

## Photos

Photo slots fill themselves from the `photos/` folder; see `photos/README.md` for the file name each slot expects. Images in `photos/placeholder/` are shown with a "PLACEHOLDER" watermark.

## Analytics

Google Analytics 4 is built in but off. Set `ga4_id` in `data.py` to the client's Measurement ID and rebuild with `--production`: pages then show a consent bar and load analytics only after a visitor accepts. It never runs in demo builds. The events sent and the switch-on steps are in `docs/PAGES.md`.

## Security

See `SECURITY.md` for the full checklist and what remains for launch. In short: no secrets anywhere, a hash-based Content Security Policy on every page, security headers in `site/_headers`, fonts served from the site itself (no third-party requests except the contact page map), and no server code.

Fonts do not load when a page is opened straight from disk (`file://`), because browsers block that; the text falls back to system fonts. To review locally with the real fonts, run `python3 -m http.server` inside `site/` and open the address it prints.

## Deploy

- **Cloudflare Pages / Netlify:** build output directory `site`, no build command needed (or `python3 build.py --production`). `site/_redirects` holds the 301 map.
- **GitHub Pages:** serve the `site/` folder. `_redirects` is ignored there, so set up redirects at the DNS/CDN level.

## Pages

Home · Team building (+ indoor, outdoor and adventure, virtual and hybrid, transport and logistics) · Venues (+ 10 region pages, venue profile template) · Corporate fitness (+ wellness days) · Guides (4 articles) · Private events · Planning checklist and budget planner · About · Contact (4-step quote engine) · Thank you · Privacy policy · 404

Plus `sitemap.xml`, `robots.txt` (AI crawlers allowed), `llms.txt` and `_redirects`.

## Before launch

See "What we need from the client" and the go-live checklist in `docs/BLUEPRINT.md`.
