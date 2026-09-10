#!/usr/bin/env python3
"""Scaffold a new post.

    python scripts/new-post.py "Why softmax?"                               # a Markdown article
    python scripts/new-post.py "Part 2: The MLP block" --kind deck \\
        --series "LLM internals" --part 2 --tags llm,transformers          # a slide deck
    python scripts/new-post.py "Notes on git rebase" --tags git --slug git-rebase --date 2026-10-01

Creates posts/<slug>/post.json plus index.md (article) or index.html (deck, from templates/deck-starter.html).
The slug is derived from the title unless --slug is given; a series deck gets the series name folded in
so parts sort together (llm-internals-part2-the-mlp-block). Edit post.json any time: the build reads it fresh.
"""
import argparse, datetime, json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SITE = json.loads((ROOT / "site.json").read_text())


def slugify(s):
    s = re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)


def main():
    ap = argparse.ArgumentParser(description="Scaffold a new post under posts/.")
    ap.add_argument("title")
    ap.add_argument("--kind", choices=["article", "deck"], default="article")
    ap.add_argument("--tags", default="", help="comma separated, e.g. llm,transformers")
    ap.add_argument("--series", help='series name, e.g. "LLM internals"')
    ap.add_argument("--part", type=int, help="part number inside the series")
    ap.add_argument("--date", default=datetime.date.today().isoformat(), help="YYYY-MM-DD (default: today)")
    ap.add_argument("--slug", help="folder name under posts/ (default: from the title)")
    ap.add_argument("--summary", default="One or two sentences shown on the home page and in the feed.")
    ap.add_argument("--draft", action="store_true", help="create it as a draft (built locally, left out of the site)")
    a = ap.parse_args()

    if (a.series is None) != (a.part is None):
        sys.exit("--series and --part go together")
    slug = a.slug or slugify((f"{a.series} " if a.series else "") + a.title)
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        sys.exit(f"bad slug {slug!r}: lowercase words joined by hyphens")
    d = ROOT / "posts" / slug
    if d.exists():
        sys.exit(f"{d.relative_to(ROOT)} already exists")
    datetime.date.fromisoformat(a.date)

    meta = {"title": a.title, "date": a.date, "summary": a.summary, "kind": a.kind,
            "tags": [t.strip() for t in a.tags.split(",") if t.strip()]}
    if a.series:
        meta["series"] = {"name": a.series, "part": a.part}
    if a.draft:
        meta["draft"] = True
    d.mkdir(parents=True)
    (d / "post.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    if a.kind == "article":
        (d / "index.md").write_text(ARTICLE.format(title=a.title))
        made = "index.md"
    else:
        text = (ROOT / "templates" / "deck-starter.html").read_text()
        kicker = f"{a.series} · Part {a.part}" if a.series else SITE["name"]
        for k, v in {"title": a.title, "description": a.summary, "kicker": kicker, "author": SITE["author"],
                     "site_name": SITE["name"]}.items():
            text = text.replace("{{" + k + "}}", v.replace("<", "&lt;"))
        (d / "index.html").write_text(text)
        made = "index.html"
    print(f"created posts/{slug}/  (post.json, {made})")
    print(f"next:  edit posts/{slug}/{made}   then   make check   and   make serve")


ARTICLE = """# {title}

Write the post here in Markdown. The heading above is for editors and GitHub previews only: the page
takes its title, date, summary and tags from post.json, so keep the two in step.

## What works

Fenced code with a language name is syntax highlighted:

```python
def softmax(z):
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()
```

Tables, footnotes[^1], block quotes and images all work. Put images in this folder and link them
relatively: `![A caption](figure.png)`.

> A note in a block quote.

A callout: wrap a paragraph in a div with the class `callout`.

<div class="callout" markdown="1">
Anything that deserves a box goes here. Markdown still works inside.
</div>

[^1]: Footnotes collect at the end of the post.
"""

if __name__ == "__main__":
    main()
