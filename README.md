# Ashwin's notes

Source for [ashwinbhaskar.github.io/blogs](https://ashwinbhaskar.github.io/blogs/): a static site built by one
Python script and published by GitHub Actions. Posts are either Markdown articles or self-contained HTML slide decks,
and both share one style language (`site/site.css` for pages, the deck starter for slides).

## Everyday process

```bash
make new T="Why softmax?" TAGS=llm         # 1. scaffold posts/why-softmax/ (post.json + index.md)
$EDITOR posts/why-softmax/index.md          # 2. write
make serve                                  # 3. preview at http://localhost:8000/blogs/
make check                                  # 4. what CI runs: metadata, links, no em dashes
git add -A && git commit -m "Why softmax" && git push   # 5. live a minute later
```

Fixes follow the same path: edit, `make check`, push. Every push to `main` rebuilds and redeploys the whole site;
pull requests run the checks without deploying.

A slide deck instead of an article:

```bash
make new T="Part 2: The MLP block" K=deck S="LLM internals" P=2 TAGS=llm,transformers
```

That copies `templates/deck-starter.html` into `posts/llm-internals-part-2-the-mlp-block/index.html`: a
five-slide deck showing the fragment, diagram and divider conventions, running on the same engine as Part 1.
Everything a deck needs is in its own folder (data, images, scripts), and the build copies the folder as-is.

## Layout

```
site.json                 name, tagline, author, GitHub user, base path, series descriptions
posts/<slug>/post.json    one per post: title, date, summary, kind, tags, series, updated, draft
posts/<slug>/index.md     an article (kind "article"), or
posts/<slug>/index.html   a deck (kind "deck"), plus any assets next to it
templates/                base page, home, article, post card, 404, deck starter
site/                     site.css (tokens + components), site.js (theme toggle, tag filter), favicon.svg
scripts/build.py          renders _site/ (feed.xml and sitemap.xml included); --check validates
scripts/serve.py          local preview under the base path, like GitHub Pages
scripts/new-post.py       scaffolds a post (what `make new` calls)
.github/workflows/        deploy.yml: build, check, publish to Pages
_site/                    build output, ignored by git
```

`post.json` in full:

```json
{
  "title": "Inside an autoregressive LLM, Part 1: The attention block",
  "date": "2026-09-10",
  "summary": "One or two sentences for the home page and the feed.",
  "kind": "deck",
  "tags": ["llm", "transformers", "attention"],
  "series": {"name": "LLM internals", "part": 1},
  "updated": "2026-09-12",
  "draft": false
}
```

`title`, `date`, `summary` and `kind` are required. A `series` entry groups posts on the home page and adds
previous/next links between parts; `part` orders them, an optional `label` replaces the "Part n" wording
(the LLM series uses `"part": 0, "label": "Introduction"`), and an optional `title` is the short form shown in
the series card ("The attention block" rather than the full post title). Parts that are not written yet can be
listed as `planned` under that series in `site.json`. `draft: true` keeps a post out of the build (and therefore off the site) while it is being written.
Posts are ordered by `date`, newest first; folder names must be lowercase words joined by hyphens.

## Changing things

The site name, tagline and description are in `site.json`; change them there and every page follows on the next
build. Colours, fonts and spacing are CSS custom properties at the top of `site/site.css`, one block for light and
one for dark; components below them only use the tokens. The nav and footer are in `templates/base.html`.
Slides keep their own dark palette on purpose: the starter carries it, and Part 1 is the reference for anything
the starter does not show.

Writing in Markdown: fenced code blocks are highlighted (name the language), tables, footnotes and block quotes
work, `<div class="callout" markdown="1">` makes a callout box, and images go in the post folder and are linked
relatively. Deep links into a deck work as `.../posts/<slug>/#/16` (slide 16) or `#/16/2` (with two build steps
already revealed).

## First-time setup

```bash
make deps                                   # pip install markdown pygments
```

In the GitHub repository, once: **Settings > Pages > Build and deployment > Source: GitHub Actions**. The first
push to `main` after that publishes the site. If the base path or GitHub user ever changes, update `base`, `url`,
`github` and `repo` in `site.json` and push.

## Conventions

No em dashes anywhere (the check fails the build). One word per thing across the LLM series: a *layer* is the
unit repeated N times, its halves are the attention *block* and the MLP *block*, *weights* only ever means the
attention weights, the W matrices are *matrices* or *learned numbers*. Announce a step before asking why it is done.
