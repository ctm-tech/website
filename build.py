"""Build the CTM Tech static site: src/pages/*.html fragments -> dist/ (Cloudflare Pages output)."""
import html, json, re, shutil
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
SRC, DIST = ROOT / "src", ROOT / "dist"
SITE = "https://ctm-tech.co.uk"
LASTMOD = "2026-09-23"

NAV = [
    ("it-support", "/it-support/", "IT Support"),
    ("ai", "/ai/", "AI &amp; Automation"),
    ("home-assistant", "/home-assistant/", "Home Assistant"),
    ("smart-home", "/#home", "Smart Home"),
    ("about", "/#about", "About"),
    ("contact", "/contact/", "Contact"),
]

LOGO_SVG = """<svg class="logo-mark" viewBox="0 0 28 28" fill="none" aria-hidden="true">
        <rect x="1" y="1" width="26" height="26" stroke="#2C3846"/>
        <path d="M7 20 L7 12 L14 7 L21 12 L21 20" stroke="#E2E8F0" stroke-width="1.4" fill="none"/>
        <circle cx="14" cy="15.5" r="2.6" fill="#F5A524"/>
        <path d="M10.6 12.6 A4.8 4.8 0 0 1 17.4 12.6" stroke="#F5A524" stroke-width="1.1" fill="none" opacity="0.55"/>
      </svg>"""


def parse(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--meta\n(.*?)\n-->\n", text, re.S)
    meta = {}
    for line in m.group(1).splitlines():
        if line.strip():
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta, text[m.end():]


def plain(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def crumb_items(meta):
    # "Label|/url >> Label|/url" (">>" because labels may contain "&amp;")
    return [("Home", "/")] + [tuple(c.strip().split("|")) for c in meta["crumbs"].split(">>")]


def faqs(body):
    out = []
    for q, a in re.findall(r"<details>\s*<summary>(.*?)</summary>(.*?)</details>", body, re.S):
        out.append({"@type": "Question", "name": plain(q),
                    "acceptedAnswer": {"@type": "Answer", "text": " ".join(plain(a).split())}})
    return out


def schema(meta, body, url):
    blocks = []
    if meta.get("home"):
        blocks.append({
            "@context": "https://schema.org", "@type": "ProfessionalService", "@id": SITE + "/#org",
            "name": "CTM Tech", "url": SITE + "/", "logo": SITE + "/favicon.svg", "foundingDate": "2016",
            "description": plain(meta["description"]),
            "areaServed": [{"@type": "AdministrativeArea", "name": "Hertfordshire"}] + [
                {"@type": "City", "name": t} for t in
                ["St Albans", "Watford", "Hemel Hempstead", "Stevenage", "Hertford", "Hatfield",
                 "Welwyn Garden City", "Harpenden", "Berkhamsted", "Bishop's Stortford", "Potters Bar", "Tring"]],
            "knowsAbout": ["IT support", "Office networking", "Cloud services", "Microsoft 365",
                           "Endpoint protection", "Microsoft 365 Copilot", "AI agents",
                           "Model Context Protocol", "Business process automation", "Power Automate",
                           "Home networking", "Home automation", "Home Assistant", "Control4 integration"],
            "priceRange": "££",
        })
    if meta.get("service"):
        blocks.append({
            "@context": "https://schema.org", "@type": "Service", "name": plain(meta["service"]),
            "serviceType": plain(meta.get("serviceType", meta["service"])), "url": url,
            "description": plain(meta["description"]),
            "provider": {"@type": "ProfessionalService", "@id": SITE + "/#org", "name": "CTM Tech", "url": SITE + "/"},
            "areaServed": {"@type": "AdministrativeArea", "name": "Hertfordshire"},
        })
    if meta.get("crumbs"):
        items = crumb_items(meta)
        blocks.append({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": plain(n), "item": SITE + u}
            for i, (n, u) in enumerate(items)]})
    q = faqs(body)
    if q:
        blocks.append({"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": q})
    return "\n".join(
        '<script type="application/ld+json">\n' + json.dumps(b, ensure_ascii=False, indent=1) + "\n</script>"
        for b in blocks)


def crumbs_html(meta):
    if not meta.get("crumbs"):
        return ""
    items = crumb_items(meta)
    parts = [f'<a href="{u}">{n}</a>' for n, u in items[:-1]] + [f'<span aria-current="page">{items[-1][0]}</span>']
    return '<nav class="crumbs" aria-label="Breadcrumb">' + "<span>/</span>".join(parts) + "</nav>"


def cta_band(meta):
    if meta.get("cta") == "none":
        return ""
    title = meta.get("cta_title", "Book a no-obligation review")
    text = meta.get("cta_text", "Tell us what's working and what isn't. We'll look at what you're running, show you where the gaps are and tell you what we'd do about them.")
    href = "/contact/" + ("?type=" + quote(html.unescape(meta["cta_type"])) if meta.get("cta_type") else "")
    return f"""
<section class="cta-band" aria-label="Get in touch">
  <div class="wrap cta-inner">
    <div>
      <h2>{title}</h2>
      <p>{text}</p>
      <div class="cta-facts">Reply within 1 business day &middot; Flexible, no lock-in &middot; Hertfordshire &amp; borders</div>
    </div>
    <div class="cta-actions">
      <a href="{href}" class="btn btn-primary">Get in touch</a>
    </div>
  </div>
</section>"""


def page(meta, body):
    path = meta["path"]
    url = SITE + path
    active = meta.get("nav", "")
    nav = "\n      ".join(
        f'<a href="{h}"' + (' aria-current="page"' if k == active else "") + f">{label}</a>" for k, h, label in NAV)
    robots = '<meta name="robots" content="noindex">\n' if meta.get("noindex") else ""
    canonical = "" if meta.get("noindex") else f'<link rel="canonical" href="{url}">\n'
    body = body.replace("{{CRUMBS}}", crumbs_html(meta))
    return f"""<!DOCTYPE html>
<html lang="en-GB">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{meta['title']}</title>
<meta name="description" content="{meta['description']}">
{robots}{canonical}<meta name="theme-color" content="#0A0D12">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">

<meta property="og:type" content="website">
<meta property="og:site_name" content="CTM Tech">
<meta property="og:locale" content="en_GB">
<meta property="og:title" content="{meta['title']}">
<meta property="og:description" content="{meta['description']}">
<meta property="og:url" content="{url}">
<meta name="twitter:card" content="summary">

<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Chivo:wght@400;600;700;900&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
<script>document.documentElement.classList.add('js')</script>
{schema(meta, body, url)}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>

<header class="site-nav">
  <div class="nav-inner">
    <a href="/" class="logo" aria-label="CTM Tech home">
      {LOGO_SVG}
      <span class="logo-text">CTM<i>.</i>Tech</span>
    </a>
    <nav class="links" id="navLinks" aria-label="Main">
      {nav}
    </nav>
    <div class="nav-cta">
      <a href="/contact/" class="btn btn-primary">Get in touch</a>
      <button class="menu-toggle" id="menuToggle" aria-label="Toggle menu" aria-expanded="false" aria-controls="navLinks">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6"><path d="M3 6h18M3 12h18M3 18h18"/></svg>
      </button>
    </div>
  </div>
</header>

<main id="main">
{body.strip()}
{cta_band(meta)}
</main>

<footer>
  <div class="wrap">
    <div class="foot-grid">
      <div class="foot-about">
        <a href="/" class="logo"><span class="logo-text">CTM<i>.</i>Tech</span></a>
        <p>Corporate-grade IT support, AI and smart home technology for Hertfordshire businesses and homes. Est. 2016.</p>
      </div>
      <div>
        <h2>Services</h2>
        <ul>
          <li><a href="/it-support/">IT support</a></li>
          <li><a href="/ai/">AI &amp; automation</a></li>
          <li><a href="/home-assistant/">Home Assistant</a></li>
          <li><a href="/home-assistant/#control4">Control4 integration</a></li>
          <li><a href="/#home">Smart home</a></li>
        </ul>
      </div>
      <div>
        <h2>Company</h2>
        <ul>
          <li><a href="/#about">About</a></li>
          <li><a href="/#sectors">Sectors we work in</a></li>
          <li><a href="/#faq">FAQ</a></li>
          <li><a href="/contact/">Contact</a></li>
          <li><a href="/privacy/">Privacy</a></li>
        </ul>
      </div>
    </div>
    <div class="foot-base">
      <span>&copy; 2026 CTM Tech &middot; Hertfordshire &middot; Est. 2016</span>
      <span>St Albans &middot; Watford &middot; Hemel Hempstead &middot; Stevenage &middot; Hertford &middot; Welwyn Garden City</span>
    </div>
  </div>
</footer>

<script src="/assets/site.js"></script>
</body>
</html>
"""


def main():
    if DIST.exists():
        shutil.rmtree(DIST)
    shutil.copytree(SRC / "assets", DIST / "assets")
    shutil.copy(SRC / "favicon.svg", DIST / "favicon.svg")
    urls = []
    for f in sorted((SRC / "pages").glob("*.html")):
        meta, body = parse(f)
        out = DIST / "404.html" if meta["path"] == "/404" else DIST / meta["path"].strip("/") / "index.html"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page(meta, body), encoding="utf-8")
        if not meta.get("noindex"):
            urls.append((meta["path"], meta.get("priority", "0.7")))
        print("built", out.relative_to(DIST))
    urls.sort(key=lambda u: (-float(u[1]), u[0]))
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{p}</loc><lastmod>{LASTMOD}</lastmod><priority>{pr}</priority></url>\n" for p, pr in urls)
        + "</urlset>\n", encoding="utf-8")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", encoding="utf-8")


if __name__ == "__main__":
    main()
