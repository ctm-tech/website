# CTM Tech — site

Static site + one Cloudflare Pages Function for the contact form.

```
.
├── index.html              # the whole site: CSS, JS, SVG all inline
├── functions/
│   └── api/
│       └── contact.js      # POST /api/contact — validates, spam-checks, emails
└── README.md
```

No build step. No dependencies. Pages compiles `functions/` into a Worker on deploy.

---

## 1. Content to fill in first

Search the repo for `[[` — every placeholder is marked that way.

| Placeholder | Where | Notes |
|---|---|---|
| `[[YEAR]]` | hero sub-line, credentials strip, About, footer | Year CTM Tech was founded |
| `[[Project title]]` etc. | `#work` | Three case study cards. Keep the problem → approach → **measurable result** shape |
| `[[SECTOR]]` | `#work` | e.g. ACCOUNTANCY, LEGAL, MANUFACTURING |
| `[[TURNSTILE_SITE_KEY]]` | contact form | Only if you enable Turnstile (step 5) |
| `ctmtech.co.uk` | canonical, og:url, JSON-LD, `CONTACT_FROM` | Swap if the domain differs |

**Cyber Essentials**: there's a commented-out badge in `#about`. Leave it commented until you actually hold the certification. Every serious Herts MSP advertises it — worth getting, but not worth claiming early.

---

## 2. Deploy to Cloudflare Pages

1. Push this folder to a GitHub repo.
2. Cloudflare dashboard → **Workers & Pages** → **Create** → **Pages** → **Connect to Git**.
3. Build settings: **framework preset = None**, build command **empty**, output directory **`/`**.
4. Deploy. You'll get `ctm-tech.pages.dev`.
5. **Custom domains** → add `ctmtech.co.uk` and `www.ctmtech.co.uk`. Cert is automatic and free.

The form will return a 500 until step 3 is done — that's expected.

---

## 3. Email delivery (Resend)

1. Sign up at resend.com. Free tier covers 3,000 emails/month, far past what a marketing form needs.
2. **Domains** → add `ctmtech.co.uk`. Resend gives you DKIM and SPF records.
3. Add them in Cloudflare DNS. **Set those records to DNS-only (grey cloud), not proxied.**
4. Wait for verification (usually minutes).
5. **API Keys** → create one with **Sending access** only. Copy it now; it's shown once.

While you're in DNS, add a DMARC record. Start in monitor mode:

```
_dmarc.ctmtech.co.uk   TXT   "v=DMARC1; p=none; rua=mailto:you@ctmtech.co.uk"
```

Once you've confirmed nothing legitimate is failing, tighten `p=none` to `p=quarantine`. This is the same work you'd do for an M365 client — worth doing properly on your own domain first.

---

## 4. Environment variables

Pages → your project → **Settings** → **Environment variables**.

| Name | Value | Type |
|---|---|---|
| `RESEND_API_KEY` | `re_...` | **Secret** |
| `CONTACT_TO` | your real inbox | Plaintext |
| `CONTACT_FROM` | `CTM Tech Website <enquiries@ctmtech.co.uk>` | Plaintext |
| `TURNSTILE_SECRET` | `0x...` | **Secret** (optional — see step 5) |

**Add them to both Production and Preview**, or preview deploys will 500.

Redeploy after adding — env vars are bound at deploy time.

`CONTACT_FROM` must be the verified domain, **not** the visitor's address. The visitor goes in `reply_to` (the Function already does this). Getting that backwards is the classic way to fail DMARC and land in spam.

---

## 5. Turnstile (recommended before launch)

Free, first-party, mostly invisible. Public marketing forms get scraped and spammed within weeks.

1. Cloudflare dashboard → **Turnstile** → **Add widget**. Hostname `ctmtech.co.uk`. Widget mode **Managed**.
2. Copy the **site key** into `index.html` — uncomment the `.cf-turnstile` div and paste it in.
3. Uncomment the script tag on that same line, or add it before `</body>`:
   ```html
   <script src="https://challenges.cloudflare.com/turnstile/v0/api.js" async defer></script>
   ```
4. Copy the **secret key** into the `TURNSTILE_SECRET` env var.

The Function only enforces Turnstile if `TURNSTILE_SECRET` is set, so you can ship without it and add it later without touching the code.

The honeypot field is always active regardless — it catches the dumber bots for free.

---

## 6. Receiving mail on the domain

Cloudflare **Email Routing** will forward `enquiries@ctmtech.co.uk` to your real inbox for free, no mailbox required. Worth setting up so the address on your site actually receives replies, not just sends.

Note: Email Routing adds its own MX records. If you later move the domain to M365, those need replacing.

---

## 7. Testing

Local:
```bash
npx wrangler pages dev .
```
Then create a `.dev.vars` file (git-ignored — **do not commit it**):
```
RESEND_API_KEY=re_...
CONTACT_TO=you@example.com
CONTACT_FROM=CTM Tech Website <enquiries@ctmtech.co.uk>
```

Checks worth running before you point the domain at it:

- Submit the form → email arrives, and **hitting reply goes to the visitor**, not to yourself.
- Fill the hidden `website` field via devtools → should return success but send nothing.
- Submit with a blank message → friendly error, no crash.
- Send a test to a Gmail address, then check the headers show SPF, DKIM and DMARC all passing.
- Run the domain through mail-tester.com. Aim for 9+/10.

Function logs: Pages → Deployments → **Functions** tab, or `npx wrangler pages deployment tail`.

---

## Where this goes next

The single page is a fine starting point, but local competitors rank on **town × service** pages — "IT support Watford", "IT support St Albans", one URL each. When you're ready for that, split `index.html` into a template and generate the pages; the Function stays exactly as it is.

Other things worth doing before you push hard on lead gen:

- **Self-host the fonts.** Google Fonts is a CDN request on every page load; a German court has ruled against it under GDPR. Not settled UK law, but you're selling security and compliance — better not to be asked the question.
- **Privacy notice.** You're collecting names and emails via the form. A short page covering what you collect, why, and how long you keep it. Then link it from the form note.
- **Google Business Profile.** For local search this matters more than anything on the site itself.
