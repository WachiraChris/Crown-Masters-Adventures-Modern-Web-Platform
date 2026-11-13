# Security checklist

Status of the site against the agreed security checklist. "Done" items are enforced by `build.py` and checked on every page; "At launch" items depend on the hosting, the form handler or the domain and cannot be done in this repository.

## 1. Secrets

| Item | Status |
| --- | --- |
| No API keys, passwords or webhook URLs in the pages or the repository | Done. There are none: the map uses Google's keyless embed, and the quote form opens the visitor's own email or WhatsApp. |
| `.env` and key files ignored by git | Done (`.gitignore`). |
| No production source maps | Done. There is no bundler; nothing is minified or mapped. |
| Domain-restrict public keys | At launch, only if a Google Maps API key or analytics ID is added. Restrict it to `crownmastersadventures.co.ke` by HTTP referrer. |

## 2. HTTP security headers

Done for Cloudflare Pages and Netlify through `site/_headers`: `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options: DENY` with `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `Permissions-Policy` and cross-origin isolation headers.

Every page also carries its own Content Security Policy in a meta tag. Scripts run only if their SHA-256 hash is listed, so injected scripts are blocked; fonts, styles and images load only from the site itself. The only third-party content is the Google Maps frame on the contact page. When a Google Analytics 4 Measurement ID is added (`ga4_id` in `data.py`), the policy also allows Google's analytics hosts, and the analytics script loads only after a visitor accepts the consent bar.

At launch: GitHub Pages and cPanel ignore `_headers`. On those hosts the same headers must be set in the server configuration. Check the live site with securityheaders.com.

## 3. Quote form

| Item | Status |
| --- | --- |
| No sensitive data in hidden inputs | Done. The forms have no hidden inputs. |
| Length limits on every field | Done in the browser (`maxlength`, number ranges, date not in the past). |
| Server-side validation and sanitising | At launch. The form currently has no server: nothing is stored or processed by the site. Whichever form handler is chosen must validate types, strip HTML and enforce the same limits. |
| Anti-spam and rate limiting | At launch, with the form handler: Cloudflare Turnstile plus a honeypot field and rate limiting. If the handler needs a new host, add it to `connect-src` / `form-action` in `CSP_BASE`. |

## 4. HTML, links and third-party scripts

| Item | Status |
| --- | --- |
| `rel="noopener noreferrer"` on every external link | Done. |
| Safe DOM updates | Done. Scripts use `textContent` and DOM methods; no `innerHTML`, `eval` or `document.write`. No inline event handlers. |
| Subresource Integrity | Not needed: no scripts, styles or fonts are loaded from a CDN. Fonts are served from `fonts/`. |
| Clean production markup | Done for code comments (none are emitted). At launch: remove the yellow "to confirm" notes, the "PLACEHOLDER" photos and the demo hint under the quote form by supplying the real content. |

## 5. Infrastructure, domain and repository

All at launch, by the domain and account owners:

- HTTPS with automatic HTTP-to-HTTPS redirect and TLS 1.3 on `crownmastersadventures.co.ke`.
- SPF, DKIM and DMARC records for the domain's email, to stop invoice spoofing.
- Two-factor authentication on the GitHub account, and Dependabot alerts on the repository.
- This repository is public and contains the client's brief (`docs/client-brief/`) and client list (`data.py`). Make it private, or remove those files, if they should not be public. A private repository cannot use free GitHub Pages; host the review copy on Cloudflare Pages instead.
