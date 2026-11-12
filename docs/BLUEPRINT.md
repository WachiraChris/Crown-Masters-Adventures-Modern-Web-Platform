# Crown Masters Adventures — Website Redesign Blueprint v2

12 November 2026 · Live, editable version: https://claude.ai/artifact/FGJUHJ3NFmpiT577uuGTxF

## Summary

Version 2 merges the best of the client blueprint (structure, filters, quote engine, stack and launch discipline) with the strengths of demo v1 (clean venue data, schema, llms.txt, no invented claims), and grows the demo from 5 pages to a full site of 30 pages.

The decisions that matter most:

- **Keep every legacy URL** (`/venues/`, `/corporate-fitness/`, `/contact-us/`, `/blog/`) and add `/team-building/` as the new pillar page. Rankings the site already has are not put at risk.
- **Ten regional venue pages** (`/venues/naivasha-nakuru-elementaita/` and so on). Each one targets a real search such as "team building venues in Naivasha". This is the single biggest SEO gain in v2.
- **A four-step quote engine** with a budget planner, venue "add to quote" from the directory, and WhatsApp hand-off. Quote requests are the business goal, so every page leads there.
- **Nothing invented.** Group capacities, client numbers, testimonials, prices, hours and services the client has not confirmed (virtual sessions, 1,000+ pax events, ergonomics) are shown as clearly marked items to confirm, never as facts.
- **Recommended stack: Astro on Cloudflare Pages with a headless CMS for venues and blog**, private GitHub repo, staging link for client review. WordPress remains the fallback if the client must edit pages themselves without help.

## Current site audit

Reviewed page by page on 12 November 2026 (Venues, Corporate Fitness, Blog, Contact). 11 defects; the four marked High block rankings or enquiries directly.

| Area | Defect found | Impact | Severity |
| --- | --- | --- | --- |
| Titles and meta | Every page shares one keyword-stuffed title; `og:type` set to article on service pages | Titles truncated; reads as spam; low click-through | High |
| Architecture | No team building page; no regional pages | Nothing to rank for "team building in Kenya" or "team building venues in Naivasha" | High |
| Brand visibility | A search for "Crown Masters Adventures" did not return the site | Prospects who hear the name cannot find it | High |
| Local and schema | No LocalBusiness data; footer email is Gmail, contact page uses the domain email | Weak map presence; inconsistent details | High |
| Content | Blog empty; gallery and videos link to Facebook and YouTube; pages last updated 2022 | No content earning links; looks abandoned | Medium |
| AEO | No FAQ, no who/what/where summary, no llms.txt, no AI crawler policy | AI assistants cannot confidently cite the business | Medium |
| Venue data | About 20 typos and duplicates | Looks careless to corporate buyers | Medium |
| Trust | No testimonials, client logos, map, hours or team | Nothing to persuade an HR buyer | Medium |
| Images | No alt text; GIF logo; OG image points at old `/newsite/` folder | Accessibility gaps; broken social previews | Medium |
| UX | "Content is protected" right-click blocker | Blocks copying the phone number | Low |
| Footer | Developer credit links to `#`; copyright reads 2025 | Visible neglect | Low |

The homepage could not be fetched by the review tools; confirm its findings in a browser before sign-off.

## Blueprint vs demo v1

The client blueprint is the stronger plan; demo v1 was the stronger build.

| Topic | Client blueprint | Demo v1 | Verdict for v2 |
| --- | --- | --- | --- |
| Site structure | 6 sections, 4 team building sub-services, 2 fitness, blog hub | 5 flat pages | Blueprint wins; add regional venue pages |
| Venue directory | Filters by region, capacity, setting; detail cards; attach venue to quote | 123 cleaned venues, search, region filter | Combine; capacity field built but pending data |
| Regions | 3 regions, a duplicated Naivasha entry, adds Maasai Mara | 10 regions from the client's venue list | v1 wins; Maasai Mara only if venues are confirmed |
| Quote form | Multi-step with duration and budget | Single form | Blueprint wins |
| Hero | Background video or carousel | Text headline | Neither: one strong photo slot plus a drive-time map |
| Headline | "Kenya's Premier…" | Plain, factual | v1 tone; superlatives are unprovable |
| Trust | Logo marquee, ticker, ratings, testimonial carousel | Placeholder | Blueprint layout, real numbers only |
| Services | Adds virtual/hybrid, overland trucks, SGR, wellness days, ergonomics, 1,000+ pax | Only stated services | Build the pages, flag each new claim |
| Lead capture | Exit-intent popup with checklist PDF | None | Checklist and planner as pages; no popup |
| Tech stack | Astro/Next.js on edge CDN, or lean WordPress; GitHub; CWV targets | None | Blueprint wins |
| Schema and AEO | Full set incl. geo and hours | All but geo and hours | v2 adds geo, hours, Article |
| Launch | Sign-off checklist | None | Blueprint wins; v2 adds redirects and measurement |
| URL slugs | Mixes `/teambuilding/`, `/team-building/`, `/corporatefitness/` | Consistent | `/team-building/` and `/corporate-fitness/` everywhere |

## Decisions for v2

**Adopted:** team building pillar with 4 sub-pages; fitness with wellness days and coordinator form; multi-step quote engine; venue filters, profiles and add-to-quote; unified NAP; Google Map; SVG logo, no right-click blocker; private GitHub and staging; Search Console and schema validation before cutover.

**Adapted:** group-size planner (up to 20, 20–80, 80–300, 300+; 1,000+ only once confirmed); capacity filter switches on when data exists; trust bar empty until real numbers; checklist and budget planner as pages, not a popup; photo hero instead of video.

**Rejected:** background video hero (breaks the 2 s LCP target); exit-intent popup (Google penalises intrusive mobile interstitials); superlatives.

**Added:** 10 regional pages; day trip / overnight filter; About page; 3 starter guides; 404, thank-you and privacy pages; geo/hours/Article schema; 301 map; analytics events.

## Sitemap, URL plan and redirects

30 pages in 7 sections. Home `/`, Team building `/team-building/` (new), Venues `/venues/`, Corporate fitness `/corporate-fitness/`, Guides `/blog/`, About `/about-us/` (new), Contact `/contact-us/`. Utility: privacy policy, 404, sitemap.xml, robots.txt, llms.txt, _redirects.

| Old URL or pattern | New URL | Why |
| --- | --- | --- |
| `/teambuilding/` | `/team-building/` | Slug variant |
| `/corporatefitness/` | `/corporate-fitness/` | Slug variant |
| `/contact/` | `/contact-us/` | Common guess |
| `/home/` | `/` | Old WordPress slug |
| `/newsite/*` | Same path without `/newsite/` | Old OG image path |
| `/category/*`, `/feed/` | `/blog/` | Empty archives |
| Any other URL in Search Console | Closest new page | Check before cutover |

## Page-by-page specification

| Page or template | Target search | Key components | Schema |
| --- | --- | --- | --- |
| Home | team building company Kenya | Hero photo, logo bar, stats, 4 services, booking steps, regions with travel times, testimonials, guides, FAQ | LocalBusiness, WebSite, WebPage, FAQPage |
| Team building | corporate team building Kenya | Direct answer, 4 formats, group-size tabs, sample agenda, inclusions, gallery, FAQ | Service, Breadcrumb, FAQPage |
| Sub-services (4) | indoor / outdoor / virtual team building; group transport | Answer, when to choose, activities, needs, FAQ, region links | Service, Breadcrumb, FAQPage |
| Venues | team building venues Kenya | Collapsed travel-time list, sticky finder, 123 cards with add-to-quote, live count | CollectionPage, ItemList, Breadcrumb, FAQPage |
| Region pages (10) | team building venues in [region] | Answer with travel time, tags, venues, best for, tips, 4 FAQs, other regions | CollectionPage, ItemList, Breadcrumb, FAQPage |
| Venue profile template | [venue] team building | Gallery, at-a-glance table, add to quote (noindex) | Place once real |
| Corporate fitness | corporate fitness Nairobi | Answer, 6 sessions, benefits, 4 steps, booking form, FAQ | Service + OfferCatalog |
| Wellness days | corporate wellness day | Answer, 6 components, FAQ (flagged) | Service, FAQPage |
| Guides + 3 articles | planning, day trip vs overnight, budget | Byline, updated date, answer, TOC, question-led H2s | Blog, Article |
| Checklist and planner | team building checklist | 13 steps saved in browser, KES cost planner, print | WebPage |
| About | Crown Masters Adventures | Answer, beliefs, how we work, team | AboutPage |
| Contact | contact / quote | 4-step quote engine, NAP, map | ContactPage |

Quote engine fields: name, company, work email, phone; service, group size, dates, duration; region, shortlisted venues, other venues; budget band, notes, review, then email or WhatsApp.

## Technical SEO and schema

All 30 pages: one H1, unique title under 65 characters, description 70–165, canonical, valid JSON-LD. Title pattern `[Topic] in [Place] | Crown Masters`. Breadcrumbs visible and in schema. Every sub-service links to its region page; every region page links to three others. `lang="en-KE"`. Alt text on every real photo (who, what, where).

Schema: LocalBusiness + TravelAgency on every page (one `@id`; geo and hours switch on from `data.py`); Service on 7 pages; CollectionPage + ItemList on venues and regions; FAQPage on 19 pages; Article and Blog on guides; BreadcrumbList on all sub-pages.

Local SEO: verify the Google Business Profile at the Parklands address, identical NAP everywhere, categories Team building company and Event planner, monthly photos, a review request after every event.

## AEO plan

On the site: direct answer on every core page; 19 FAQ sections; question-led headings; specific facts (123 venues, 10 regions, 3 countries, travel times); visible updated dates; `llms.txt`; `robots.txt` allowing Googlebot, Bingbot, Google-Extended, GPTBot, OAI-SearchBot, ChatGPT-User, ClaudeBot, Claude-SearchBot, PerplexityBot, Applebot-Extended.

Off the site: Google Business Profile with reviews; Bing Places; identical details on all social profiles; Kenyan directory listings; two or three media mentions a year. Monthly check: ask ChatGPT, Gemini and Perplexity three fixed questions and record whether Crown Masters is named.

## Performance, accessibility and conversion

| Target | Standard | How |
| --- | --- | --- |
| LCP | < 2.0 s on mobile 4G | Inline CSS, no render-blocking JS, AVIF/WebP hero at 1600 px, preloaded |
| CLS | < 0.1 | Fixed aspect-ratio photo slots, font-display swap |
| INP | < 200 ms | Under 4 KB vanilla JS per page |
| Page weight | < 1 MB with photos | Compression, lazy loading, one map embed |
| Accessibility | WCAG 2.2 AA | Skip link, focus, labels, keyboard tabs, live regions, reduced motion, dark mode |
| Mobile | 320 px | No horizontal scroll on any page at 390 px (tested) |

Conversion: quote CTA in header, hero and closing band; floating WhatsApp; tap-to-call; add-to-quote on 123 venues carried into the form; 4-step form with review; checklist offered after every guide. Every CTA has a `data-ev` tag for GA4 via Tag Manager.

## Venue data corrections

20 fixes made (see `CORRECTIONS` in `data.py`). Names to confirm: Phoenicial Resort (Kiambu), Mat Farm Hotel (Nakuru), Great Rift Valley Lodge, Lala Nasi Hotel, Aberdare Country Club, Mcellys Hotel (Arusha), Asmini Palace Hotel (Zanzibar), Source of the Nile Resort (Jinja). Data to collect per venue: outdoor capacity, seated capacity, rooms, activity spaces, three photos.

## What we need from the client

Before launch:
- [ ] Official email (retire the Gmail address)
- [ ] Single phone/WhatsApp number
- [ ] Exact office address and Google Maps pin
- [ ] Opening hours, day by day
- [ ] Vector logo
- [ ] Yes/no on virtual and hybrid, overland trucks, SGR coordination, wellness days, ergonomics, 1,000+ events
- [ ] The 8 venue names and sign-off on the 10 regions
- [ ] At least 12 real event photos with permission
- [ ] Founding year and company story
- [ ] Privacy policy reviewed by a lawyer

First month:
- [ ] 6 client logos
- [ ] 3–6 testimonials with name, role, company
- [ ] Real trust-bar numbers
- [ ] Team names, roles, portraits
- [ ] Capacity, rooms and photos for the top 20 venues
- [ ] Fitness frequency options and trainer qualifications
- [ ] Google Business Profile access
- [ ] Short event videos hosted on the site

## Launch checklist and timeline

Proposed: Sign-off (weeks 1–2) → gate: content approved → Build (weeks 2–4: Astro + CMS, real content, staging review) → gate: staging approved → Launch (week 5: redirects, Search Console, GA4, schema validated) → gate: go-live checks pass → Grow (months 2–6: a guide a month, reviews, venue profiles, monthly AI check).

Go-live checklist:
- [ ] Private repo with staging deploys
- [ ] Production build; placeholders replaced or hidden
- [ ] Every legacy URL returns 200 or a single 301
- [ ] Rich Results Test passes on key templates
- [ ] PageSpeed mobile: LCP < 2.0 s, CLS < 0.1
- [ ] Quote form posts to a real handler and lands on the thank-you page
- [ ] Search Console and Bing Webmaster verified; sitemap submitted
- [ ] GA4 key events: quote sent, WhatsApp click, phone tap
- [ ] HTTPS enforced; old WordPress backed up, then switched off

Measure monthly: quote and WhatsApp enquiries (GA4), clicks by page and rankings for 10 tracked searches (Search Console), AI mentions (manual check), Google reviews, mobile LCP.
