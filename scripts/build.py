#!/usr/bin/env python3
"""Build the site into _site/ from site.json, templates/ and posts/*/post.json.

    python scripts/build.py            build
    python scripts/build.py --check    build, then validate links, metadata and typography (exit 1 on failure)

Each post is a folder under posts/ with a post.json:
    {"title": "...", "date": "YYYY-MM-DD", "summary": "...", "kind": "article" | "deck",
     "tags": ["..."], "series": {"name": "...", "part": 1, "label": "optional, e.g. Introduction", "title": "optional short title for the series card"},
     "updated": "YYYY-MM-DD", "draft": false}
An article has an index.md next to it (Markdown, converted here). A deck has a self-contained index.html,
copied as-is together with everything else in its folder.
"""
import json, re, shutil, sys, html, datetime, pathlib, urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text())
OUT = ROOT / "_site"
TPL = ROOT / "templates"
BASE = SITE["base"].rstrip("/")
KIND_LABEL = {"article": "Article", "deck": "Slides"}
REQUIRED = ["title", "date", "summary", "kind"]
problems = []


def tpl(name, **kw):
    text = (TPL / name).read_text()
    for k, v in kw.items():
        text = text.replace("{{" + k + "}}", str(v))
    left = re.findall(r"{{(\w+)}}", text)
    if left:
        problems.append(f"template {name}: unfilled placeholders {sorted(set(left))}")
    return text


def esc(s):
    return html.escape(str(s), quote=True)


def pretty(date):
    d = datetime.date.fromisoformat(date)
    return f"{d.day} {d.strftime('%B %Y')}"


def page(title, description, content, canonical, og_type="website", home=False):
    return tpl("base.html", title=esc(title), description=esc(description), canonical=canonical,
               base=BASE, site_name=esc(SITE["name"]), author=esc(SITE["author"]), github=SITE["github"],
               repo=SITE["repo"], year=datetime.date.today().year, content=content, og_type=og_type,
               nav_home_current=' aria-current="page"' if home else "")


def part_label(s):
    """How a series entry is shown: "Part 3", or its own label ("Introduction")."""
    return s.get("label") or f"Part {s['part']}"


def chips(tags):
    return "".join(f'<a class="chip" href="{BASE}/#tag={urllib.parse.quote(t)}">{esc(t)}</a>' for t in tags)


# ---------------------------------------------------------------- posts
def load_posts():
    posts = []
    for d in sorted((ROOT / "posts").iterdir()):
        meta_path = d / "post.json"
        if not d.is_dir() or not meta_path.exists():
            continue
        try:
            m = json.loads(meta_path.read_text())
        except json.JSONDecodeError as e:
            problems.append(f"{meta_path}: invalid JSON ({e})"); continue
        before = len(problems)
        for k in REQUIRED:
            if k not in m:
                problems.append(f"{meta_path}: missing '{k}'")
        if m.get("kind") not in KIND_LABEL:
            problems.append(f"{meta_path}: kind must be one of {list(KIND_LABEL)}")
        for k in ("date", "updated"):
            if k in m:
                try:
                    datetime.date.fromisoformat(str(m[k]))
                except ValueError:
                    problems.append(f"{meta_path}: {k} must be YYYY-MM-DD")
        if m.get("kind") == "article" and not (d / "index.md").exists():
            problems.append(f"{d}: article without index.md")
        if m.get("kind") == "deck" and not (d / "index.html").exists():
            problems.append(f"{d}: deck without index.html")
        s = m.get("series")
        if s is not None and not (isinstance(s, dict) and isinstance(s.get("name"), str) and isinstance(s.get("part"), int)):
            problems.append(f'{meta_path}: series must look like {{"name": "...", "part": 1}}')
        if not isinstance(m.get("tags", []), list):
            problems.append(f"{meta_path}: tags must be a list of strings")
        if len(problems) > before:
            continue
        m["slug"] = d.name
        m["dir"] = d
        m["href"] = f"{BASE}/posts/{d.name}/"
        m.setdefault("tags", [])
        if m.get("draft"):
            continue
        posts.append(m)
    # newest first; on the same day, series order (introduction before part 1)
    posts.sort(key=lambda p: (p["date"], -p.get("series", {}).get("part", 0), p["slug"]), reverse=True)
    return posts


def render_markdown(text):
    import markdown
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "attr_list", "md_in_html", "footnotes", "codehilite"],
                           extension_configs={"codehilite": {"css_class": "hl", "guess_lang": False},
                                              "toc": {"permalink": False}})
    return md.convert(text)


def series_nav(post, posts):
    s = post.get("series")
    if not s:
        return ""
    same = sorted([p for p in posts if p.get("series", {}).get("name") == s["name"]], key=lambda p: p["series"]["part"])
    idx = [p["slug"] for p in same].index(post["slug"])
    prev_ = same[idx - 1] if idx > 0 else None
    next_ = same[idx + 1] if idx + 1 < len(same) else None
    parts = []
    if prev_:
        parts.append(f'<a href="{prev_["href"]}"><span class="label">Previous in {esc(s["name"])}</span><span>{esc(prev_["title"])}</span></a>')
    if next_:
        parts.append(f'<a class="next" href="{next_["href"]}"><span class="label">Next in {esc(s["name"])}</span><span>{esc(next_["title"])}</span></a>')
    return f'<nav class="series-nav wrap wrap--narrow" aria-label="Series">{"".join(parts)}</nav>' if parts else ""


def build_article(post, posts):
    text = (post["dir"] / "index.md").read_text()
    text = re.sub(r"\A\s*#(?!#)[^\n]*\n", "", text)   # a leading "# Title" is for editors; the page heading comes from post.json
    body = render_markdown(text)
    s = post.get("series")
    kicker = f'<p class="kicker">{esc(s["name"])} · {esc(part_label(s))}</p>' if s else ""
    updated = f'<span>updated <time datetime="{post["updated"]}">{pretty(post["updated"])}</time></span>' if post.get("updated") else ""
    content = tpl("article.html", kicker=kicker, title=esc(post["title"]), summary=esc(post["summary"]), date=post["date"],
                  date_pretty=pretty(post["date"]), updated=updated, tag_chips=chips(post["tags"]), body=body,
                  series_nav=series_nav(post, posts))
    return page(f'{post["title"]} · {SITE["name"]}', post["summary"], content, f'{SITE["url"]}/posts/{post["slug"]}/', "article")


def copy_post_assets(post, dest):
    for item in post["dir"].iterdir():
        if item.name in ("index.md", "post.json") or item.name.startswith("."):
            continue
        if item.is_dir():
            shutil.copytree(item, dest / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dest / item.name)


# ---------------------------------------------------------------- home
def series_section(posts):
    defs = dict(SITE.get("series", {}))
    for p in posts:
        if p.get("series"):
            defs.setdefault(p["series"]["name"], {})
    if not defs:
        return ""
    cards = []
    for name, info in defs.items():
        members = sorted([p for p in posts if p.get("series", {}).get("name") == name], key=lambda p: p["series"]["part"])
        # inside the card the series name is already given, so a short title ("The attention block") reads better than the full one
        items = [f'<li><span class="part">{esc(part_label(p["series"]))}</span><a href="{p["href"]}">{esc(p["series"].get("title") or p["title"])}</a></li>' for p in members]
        n = max([p["series"]["part"] for p in members], default=0)
        for planned in info.get("planned", []):
            m = re.match(r"^Part\s+(\d+):\s*(.*)$", planned)   # "Part 2: The MLP block" keeps its number; a bare title continues the count
            n = int(m.group(1)) if m else n + 1
            label = m.group(2) if m else planned
            items.append(f'<li><span class="part">Part {n}</span><span class="planned">{esc(label)}</span></li>')
        if not items:
            continue
        desc = f'<p>{esc(info["description"])}</p>' if info.get("description") else ""
        cards.append(f'<div class="series-card"><h3>{esc(name)}</h3>{desc}<ol>{"".join(items)}</ol></div>')
    return f'<section class="section wrap"><h2>Series</h2><div class="series">{"".join(cards)}</div></section>' if cards else ""


def build_home(posts):
    counts = {}
    for p in posts:
        for t in p["tags"]:
            counts[t] = counts.get(t, 0) + 1
    tags = sorted(counts, key=lambda t: (-counts[t], t))
    filters = ('<div class="filters" role="group" aria-label="Filter by tag">' +
               "".join(f'<button class="chip" type="button" data-tag="{esc(t)}" aria-pressed="false">{esc(t)}<span class="count">{counts[t]}</span></button>' for t in tags) +
               "</div>") if tags else ""
    cards = []
    for p in posts:
        s = p.get("series")
        series_label = f'<span>{esc(s["name"])} · {esc(part_label(s))}</span>' if s else ""
        cards.append(tpl("post-card.html", tags_attr=esc(" ".join(p["tags"])), href=p["href"], title=esc(p["title"]),
                         kind_label=KIND_LABEL[p["kind"]], summary=esc(p["summary"]), date=p["date"],
                         date_pretty=pretty(p["date"]), series_label=series_label, tag_chips=chips(p["tags"])))
    content = tpl("index.html", site_name=esc(SITE["name"]), tagline=esc(SITE["tagline"]), series_section=series_section(posts),
                  filters=filters, post_cards="\n".join(cards) or '    <li class="empty">No posts yet.</li>')
    return page(SITE["name"], SITE["description"], content, SITE["url"] + "/", home=True)


def build_feed(posts):
    items = []
    for p in posts:
        d = datetime.datetime.fromisoformat(p["date"]).replace(tzinfo=datetime.timezone.utc)
        items.append(f"<item><title>{esc(p['title'])}</title><link>{SITE['url']}/posts/{p['slug']}/</link>"
                     f"<guid>{SITE['url']}/posts/{p['slug']}/</guid><pubDate>{d.strftime('%a, %d %b %Y 00:00:00 +0000')}</pubDate>"
                     f"<description>{esc(p['summary'])}</description></item>")
    return (f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>{esc(SITE["name"])}</title>'
            f'<link>{SITE["url"]}/</link><description>{esc(SITE["description"])}</description>{"".join(items)}</channel></rss>')


def build_sitemap(posts):
    urls = [f'{SITE["url"]}/'] + [f'{SITE["url"]}/posts/{p["slug"]}/' for p in posts]
    return ('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
            "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")


# ---------------------------------------------------------------- checks
def check(posts):
    # typography: no em dashes anywhere in sources or output
    for path in list((ROOT / "posts").rglob("*")) + list(OUT.rglob("*")) + list(TPL.rglob("*")):
        if path.is_file() and path.suffix in (".md", ".html", ".json", ".svg", ".xml"):
            if "\u2014" in path.read_text(errors="ignore"):   # an em dash
                problems.append(f"{path.relative_to(ROOT)}: contains an em dash")
    # links: every internal href/src must resolve inside _site
    for html_file in OUT.rglob("*.html"):
        text = html_file.read_text(errors="ignore")
        for attr, target in re.findall(r'\b(href|src)="([^"]+)"', text):
            t = target.split("#")[0].split("?")[0]
            if not t or t.startswith(("http://", "https://", "mailto:", "data:", "javascript:")):
                continue
            if t.startswith("/"):
                if not t.startswith(BASE + "/") and t != BASE:
                    problems.append(f"{html_file.relative_to(OUT)}: absolute link outside the base path: {target}"); continue
                fs = OUT / t[len(BASE) + 1:]
            else:
                fs = (html_file.parent / t).resolve()
            if fs.is_dir():
                fs = fs / "index.html"
            if not fs.exists():
                problems.append(f"{html_file.relative_to(OUT)}: broken link {target}")
    slugs = [p["slug"] for p in posts]
    for s in slugs:
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s):
            problems.append(f"posts/{s}: folder name should be lowercase words joined by hyphens")


# ---------------------------------------------------------------- main
def main():
    do_check = "--check" in sys.argv
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    posts = load_posts()
    for p in posts:
        dest = OUT / "posts" / p["slug"]
        dest.mkdir(parents=True)
        copy_post_assets(p, dest)
        if p["kind"] == "article":
            (dest / "index.html").write_text(build_article(p, posts))
    (OUT / "index.html").write_text(build_home(posts))
    (OUT / "404.html").write_text(page(f'Not found · {SITE["name"]}', SITE["description"], tpl("404.html", base=BASE), SITE["url"] + "/404.html"))
    (OUT / "feed.xml").write_text(build_feed(posts))
    (OUT / "sitemap.xml").write_text(build_sitemap(posts))
    shutil.copytree(ROOT / "site", OUT / "site", dirs_exist_ok=True)
    (OUT / ".nojekyll").write_text("")
    print(f"built {len(posts)} post(s) into _site/ (base path {BASE or '/'})")
    for p in posts:
        print(f"  {p['date']}  {KIND_LABEL[p['kind']]:8}  {p['slug']}")
    if do_check:
        check(posts)
    if problems:
        print("\nPROBLEMS:")
        for pr in problems:
            print("  -", pr)
        sys.exit(1)
    if do_check:
        print("checks passed: metadata, links, no em dashes")


if __name__ == "__main__":
    main()
