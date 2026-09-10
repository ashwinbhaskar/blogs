# How this site works

This site is a folder of posts and a script. There is no framework to upgrade and nothing to configure beyond
one small JSON file. I wrote it this way so that publishing a fix is the same motion as fixing a typo in code:
edit, check, push.

## The shape of it

Every post is a folder under `posts/` with a `post.json` next to the content. Prose posts are Markdown
(`index.md`); slide decks are self-contained HTML files (`index.html`) that carry their own data, diagrams and
a small slide engine. The build script reads the JSON files, renders the Markdown, copies the decks as they are,
and writes the home page, an RSS feed and a sitemap into `_site/`. GitHub Actions runs that script on every push
and publishes the result to GitHub Pages.

| Piece | What it is | Where |
|---|---|---|
| Site settings | name, tagline, base path, series | `site.json` |
| A post | metadata plus content | `posts/<slug>/` |
| Style language | colour and type tokens, components | `site/site.css` |
| Build | Markdown to HTML, home page, feed | `scripts/build.py` |
| Publish | build, check, deploy | `.github/workflows/deploy.yml` |

## The style language

Pages are light by default with a dark option in the header; the choice is remembered in the browser. Both
themes are the same twelve custom properties with different values, so a component never mentions a colour
directly. Body text is Inter, code is JetBrains Mono, and the accent is a mint green that the slide decks share.

Decks are always dark. A deck is meant to be shown on a projector or a shared screen, where a dark canvas keeps
the diagrams in front, and the matrices are drawn with colour ramps tuned for that background. Rather than
maintain two palettes for every diagram, the decks keep one.

## What a post can contain

Code blocks are highlighted when the fence names a language:

```python
import numpy as np

def softmax(z):
    z = z - z.max(axis=-1, keepdims=True)   # shift first, for stability
    e = np.exp(z)
    return e / e.sum(axis=-1, keepdims=True)
```

Inline code like `d_k` and short math written in plain text both read fine. Footnotes collect at the end of the
post[^1], and block quotes look like this:

> The score between a query and a key is a dot product. Everything else in the attention block is bookkeeping
> around that one number.

<div class="callout" markdown="1">
**Callouts** are a `div` with the class `callout`; Markdown keeps working inside. Use one for the sentence you
want a skimming reader to take away.
</div>

Images go in the post folder and are linked relatively, so a post stays self-contained and can be moved or
deleted as one unit.

## The checks

`python scripts/build.py --check` fails on a missing field in `post.json`, a broken internal link, a folder name
that is not a clean slug, or an em dash anywhere in the sources or the output. The same command runs in the
workflow, so a push that breaks the site does not publish.

[^1]: A footnote. The build uses Python-Markdown with the footnotes, tables, fenced code and attribute list extensions.
