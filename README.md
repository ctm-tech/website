# CTM Tech — site

Static multi-page site + one Cloudflare Pages Function for the contact form.

```
.
├── src/
│   ├── pages/*.html        # page content; meta block at the top (path, title, description, crumbs, cta…)
│   ├── assets/             # shared site.css and site.js
│   └── favicon.svg
├── build.py                # wraps pages in the shared header/footer, adds SEO tags + JSON-LD,
│                           # writes sitemap.xml, robots.txt and 404.html → dist/
├── check.py                # validates HTML nesting, JSON-LD, internal links and anchors
├── dist/                   # the built site — committed, this is what Pages serves
├── functions/
│   └── api/
│       └── contact.js      # POST /api/contact — validates, spam-checks, emails via Resend
└── README.md
```

---

## 1. Editing

Edit files in `src/`, then:

```bash
python build.py
python check.py
```

Commit both `src/` and `dist/`. Never edit `dist/` by hand — it is overwritten on every build.

Header, footer, nav and the "Get in touch" band live in `build.py`. The page list comes from
`src/pages/`: add a file with a meta block and it appears in the sitemap automatically.

### Before going live

- Contact page: fill in and uncomment the phone/email block in `src/pages/contact.html`.
- Privacy page: add legal entity name (and company number if Ltd) and ICO registration number.
- When Control4 dealer status is confirmed: update the "Independent by choice" paragraph on the
  homepage and the Control4 section in `src/pages/home-assistant.html`.
- Cyber Essentials: only claim certification once certified.

---

## 2. Cloudflare Pages settings

Workers & Pages → project → **Settings → Build**:

| Setting | Value |
|---|---|
| Framework preset | None |
| Build command | *(empty)* |
| Build output directory | **`dist`** |
| Root directory | *(empty)* — `functions/` must stay at the repo root |

Push to a branch other than `main` to get a preview deployment; merge to `main` to go live.
Roll back from **Deployments** → previous deployment → **Rollback**.

After a content change, submit `https://ctm-tech.co.uk/sitemap.xml` in Google Search Console.

---

## 3. Email delivery (Resend)

1. Sign up at resend.com. Free tier covers 3,000 emails/month.
2. **Domains** → add the domain. Resend gives you DKIM and SPF records.
3. Add them in Cloudflare DNS. **Set those records to DNS-only (grey cloud), not proxied.**
4. Wait for verification (usually minutes).
5. **API Keys** → create one with **Sending access** only.

Add a DMARC record, starting in monitor mode, then tighten `p=none` to `p=quarantine` once nothing
legitimate is failing.

---

## 4. Environment variables

Pages → project → **Settings** → **Environment variables**. Add to **both Production and Preview**,
or preview deploys will 500. Redeploy after adding — env vars are bound at deploy time.

| Name | Value | Type |
|---|---|---|
| `RESEND_API_KEY` | `re_...` | **Secret** |
| `CONTACT_TO` | your real inbox | Plaintext |
| `CONTACT_FROM` | `CTM Tech Website <enquiries@your-domain>` | Plaintext |
| `TURNSTILE_SECRET` | `0x...` | **Secret** (optional) |

`CONTACT_FROM` must be the verified domain, not the visitor's address; the visitor goes in `reply_to`.

---

## 5. Turnstile

The widget is on `/contact/` (`src/pages/contact.html`). The Function only enforces Turnstile if
`TURNSTILE_SECRET` is set. The widget's hostname list must include every domain the form is used on
(add `<project>.pages.dev` to test on preview deployments).

The honeypot field is always active.

---

## 6. Testing

Local:
```bash
python build.py
npx wrangler pages dev dist
```
With a git-ignored `.dev.vars` in the repo root:
```
RESEND_API_KEY=re_...
CONTACT_TO=you@example.com
CONTACT_FROM=CTM Tech Website <enquiries@your-domain>
```

Checks before merging to `main`:

- Every page and the mobile menu work; `/sitemap.xml` and `/robots.txt` serve real files; an unknown URL shows the 404 page.
- Submit the form → email arrives, and replying goes to the visitor.
- Fill the hidden `website` field via devtools → success response, nothing sent.
- Submit with a blank message → friendly error.

Function logs: Pages → Deployments → **Functions** tab, or `npx wrangler pages deployment tail`.
