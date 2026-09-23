import re, json, pathlib
from html.parser import HTMLParser
d = pathlib.Path(__file__).parent / "dist"
VOID = {"meta", "link", "br", "img", "input", "hr", "source", "path", "rect", "circle", "animateMotion"}


class P(HTMLParser):
    def __init__(s):
        super().__init__(); s.stack = []; s.err = []; s.links = []; s.ids = set(); s.h1 = 0

    def handle_starttag(s, t, a):
        a = dict(a)
        if a.get("id"): s.ids.add(a["id"])
        if t == "h1": s.h1 += 1
        if t == "a" and a.get("href", "").startswith("/"): s.links.append(a["href"])
        if t not in VOID: s.stack.append((t, s.getpos()))

    def handle_endtag(s, t):
        if t in VOID: return
        if s.stack and s.stack[-1][0] == t: s.stack.pop()
        else: s.err.append(f"unexpected </{t}> at {s.getpos()} open={s.stack[-1] if s.stack else None}")


pages = {}
for f in sorted(d.rglob("*.html")):
    src = f.read_text(encoding="utf-8")
    p = P(); p.feed(src)
    if p.err or p.stack: print("HTML", f, p.err[:3], p.stack[-3:])
    for m in re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S): json.loads(m)
    title = re.search(r"<title>(.*?)</title>", src).group(1)
    desc = re.search(r'name="description" content="(.*?)"', src).group(1)
    words = len(re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style|svg)[\s\S]*?</\1>", "", src)).split())
    print(f"{str(f.relative_to(d)):38} h1={p.h1} words={words:5} title={len(title):3} desc={len(desc)}")
    pages[f.resolve()] = p
for f, p in pages.items():
    for l in p.links:
        path, _, frag = l.partition("#"); path = path.split("?")[0]
        if path.endswith(".svg"): continue
        target = (d / "index.html" if path in ("", "/") else d / path.strip("/") / "index.html").resolve()
        if target not in pages: print("BROKEN", f.name, l)
        elif frag and frag not in pages[target].ids: print("BAD ANCHOR", f, l)
print((d / "sitemap.xml").read_text())
