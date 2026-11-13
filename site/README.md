# Crown Masters Adventures — website demo v2

Static site generated from `data.py` by `build.py` (32 pages).

- Open `index.html` in a browser to review the demo (links work offline).
- `python3 build.py --production` writes clean URLs (`/venues/`) for deployment.
- Edit venues, regions and contact details in `data.py`, then rebuild.
- Items marked "to confirm" (yellow notes) need client sign-off before launch.
- `_redirects` holds the 301 map for Cloudflare Pages or Netlify.
