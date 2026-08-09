#!/usr/bin/env python3
"""Builds the static site from one set of templates and one JSON file per language.

    python3 build.py

Everything under `compressive/` and the root `index.html` is GENERATED — edit
`content/<lang>.json` or the templates in this file, never the HTML. This is the
same arrangement the app itself uses for `Localizable.xcstrings`, and for the
same reason: two copies of a sentence in two languages drift, one source does
not.

Adding a language is one file: copy `content/en.json` to `content/<code>.json`,
translate the values, and run this. The generator picks up every JSON in
`content/`, writes `<code>/` under each app, and adds the language to every
page's switcher and `hreflang` set by itself.

English is the canonical language and is written without a prefix, because those
URLs are already published and sit in the app's `LegalLinks`.
"""

import json
import pathlib
import shutil

ROOT = pathlib.Path(__file__).parent
CONTENT = ROOT / "content"
SOURCE_LANG = "en"

# ---------------------------------------------------------------- templates


def esc(s):
    """The content files hold text, not markup — everything is escaped. The one
    exception is `raw`-marked strings, which a few sentences need for a link."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def head(title, description, depth, lang, page, langs):
    """`depth` is how many levels down from the site root this page sits, which
    is the only thing the stylesheet href depends on. `page` is None for a page
    that has no translations — the hub — and such a page must not advertise
    `hreflang` alternates, since the addresses it would name are not
    translations of itself."""
    up = "../" * depth
    alts = ""
    if page is not None:
        alts = "\n".join(
            '<link rel="alternate" hreflang="{code}" href="{href}">'.format(
                code=code, href=page_url(code, page, absolute=True))
            for code in langs
        )
        alts += '\n<link rel="alternate" hreflang="x-default" href="{}">\n'.format(
            page_url(SOURCE_LANG, page, absolute=True))
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
{alts}<link rel="stylesheet" href="{up}style.css">
</head>
<body>
<div class="wrap">
"""


FOOT = """
</div>
</body>
</html>
"""

# Web visitors who arrive from the App Store get no language hint from anywhere,
# so this is the one place the site has to guess. It only ever runs on the
# canonical English page, only ever hops once (the translated pages carry no
# script), and stands down the moment the visitor states a preference — the
# switcher links carry `?hl=`. Customers who arrive from the app never reach it:
# the app knows its own language and links straight to the right page.
REDIRECT = """<script>
(function () {
  try {
    if (location.search.indexOf('hl=') !== -1) return;
    if (sessionStorage.getItem('hl')) return;
    var published = %s;
    var preferred = navigator.languages || [navigator.language || ''];
    for (var i = 0; i < preferred.length; i++) {
      var code = String(preferred[i]).toLowerCase().split('-')[0];
      if (code === '%s') return;
      if (published.indexOf(code) !== -1) {
        location.replace('%s' + code + '/%s');
        return;
      }
    }
  } catch (e) {}
})();
</script>
"""


def page_url(lang, page, absolute=False):
    """`page` is "" for the app's own page or "privacy/"."""
    base = "https://devbalek.github.io" if absolute else ""
    prefix = "" if lang == SOURCE_LANG else lang + "/"
    return f"{base}/compressive/{prefix}{page}"


def masthead(data, lang, page, langs):
    """Wordmark plus the language switcher. Each switcher link carries `?hl=`,
    which is what tells the redirect above that the visitor has chosen.

    The wordmark is an absolute address rather than a count of `../`: from the
    Turkish policy the relative walk lands on `/compressive/`, which is the
    *English* page, and a reader who clicked the app's own name would silently
    change language."""
    items = []
    for code in langs:
        label = LANG_LABELS.get(code, code.upper())
        href = page_url(code, page) + "?hl=" + code
        current = ' aria-current="page"' if code == lang else ""
        items.append(f'      <a href="{href}"{current}>{label}</a>')
    links = "\n".join(items)
    return f"""  <div class="masthead">
    <a class="wordmark" href="{page_url(lang, '')}">{esc(data['app_name'])}</a>
    <nav class="langs" aria-label="Language">
{links}
    </nav>
  </div>
"""


LANG_LABELS = {"en": "EN", "tr": "TR"}


# ------------------------------------------------------------------ blocks


def render_blocks(blocks):
    """The privacy policy is a list of typed blocks so a translation mirrors the
    structure instead of restating the markup."""
    out = []
    for b in blocks:
        kind = b["type"]
        if kind == "p":
            out.append(f"    <p>{inline(b['text'])}</p>")
        elif kind == "h2":
            out.append(f"    <h2>{esc(b['text'])}</h2>")
        elif kind == "ul":
            items = "\n".join(f"      <li>{inline(i)}</li>" for i in b["items"])
            out.append(f"    <ul>\n{items}\n    </ul>")
        elif kind == "card":
            rows = "\n".join(
                f"        <dt>{esc(d['term'])}</dt>\n"
                f"        <dd>{inline(d['detail'])}</dd>"
                for d in b["items"]
            )
            out.append(f'    <div class="card">\n      <dl>\n{rows}\n      </dl>\n    </div>')
        elif kind == "claim":
            out.append(f'    <p class="claim">{inline(b["text"])}</p>')
        else:
            raise SystemExit(f"unknown block type: {kind}")
    return "\n\n".join(out)


def inline(text):
    """Content is escaped text, with two markers kept deliberately small:
    `**bold**` and `[label](href)`. Anything richer belongs in a block type."""
    import re
    s = esc(text)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"__([^_]+)__", r"<em>\1</em>", s)
    return s


# ------------------------------------------------------------------- pages


def build_support(data, lang, langs):
    s = data["support"]
    depth = 1 if lang == SOURCE_LANG else 2
    html = head(s["title"], s["description"], depth, lang, "", langs)
    if lang == SOURCE_LANG:
        others = [c for c in langs if c != SOURCE_LANG]
        html += REDIRECT % (json.dumps(others), SOURCE_LANG, "/compressive/", "")
    html += masthead(data, lang, "", langs)

    m = s["meter"]
    faq = "\n".join(
        f"""      <div>
        <h3>{esc(item['q'])}</h3>
        <p>{inline(item['a'])}</p>
      </div>"""
        for item in s["faq"]
    )

    html += f"""
  <div class="hero">
    <p class="eyebrow">{esc(s['eyebrow'])}</p>
    <h1>{esc(s['h1'])}</h1>
    <p class="lede">{inline(s['lede'])}</p>

    <div class="meter">
      <div class="meter-row">
        <div class="meter-label">
          <span>{esc(m['before_label'])}</span>
          <b class="num">{esc(m['before_size'])}</b>
        </div>
        <div class="track">
          <div class="fill picture" style="--w:{m['ratio']}"></div>
          <div class="fill padding" style="--from:{m['ratio']}; --w:100%"></div>
        </div>
      </div>

      <div class="meter-row">
        <div class="meter-label">
          <span>{esc(m['after_label'])}</span>
          <b class="num">{esc(m['after_size'])}</b>
        </div>
        <div class="track">
          <div class="fill picture" style="--w:{m['ratio']}"></div>
        </div>
      </div>

      <div class="legend">
        <span><i class="k-picture"></i> {esc(m['key_picture'])}</span>
        <span><i class="k-padding"></i> {esc(m['key_padding'])}</span>
      </div>

      <p class="verdict">{inline(m['verdict'])}</p>
    </div>
  </div>

  <section>
    <h2>{esc(s['support_h2'])}</h2>
    <p class="narrow">{inline(s['support_body'])}</p>
    <p class="narrow small">{inline(s['support_hint'])}</p>
  </section>

  <section>
    <h2>{esc(s['faq_h2'])}</h2>
    <div class="faq narrow">
{faq}
    </div>
  </section>

{footer(data, lang, "", langs)}"""
    return html + FOOT


def build_privacy(data, lang, langs):
    p = data["privacy"]
    depth = 2 if lang == SOURCE_LANG else 3
    html = head(p["title"], p["description"], depth, lang, "privacy/", langs)
    if lang == SOURCE_LANG:
        others = [c for c in langs if c != SOURCE_LANG]
        html += REDIRECT % (json.dumps(others), SOURCE_LANG, "/compressive/", "privacy/")
    html += masthead(data, lang, "privacy/", langs)

    html += f"""
  <div class="hero">
    <p class="eyebrow">{esc(p['updated'])}</p>
    <h1>{esc(p['h1'])}</h1>
    <p class="lede">{esc(p['lede'])}</p>
  </div>

  <div class="prose">

{render_blocks(p['blocks'])}

  </div>

{footer(data, lang, "privacy/", langs)}"""
    return html + FOOT


def footer(data, lang, page, langs):
    f = data["footer"]
    if page == "privacy/":
        near = f'<a href="{page_url(lang, "")}">{esc(f["support"])}</a>'
    else:
        near = f'<a href="{page_url(lang, "privacy/")}">{esc(f["privacy"])}</a>'
    return f"""  <footer>
    <span>{esc(f['copyright'])}</span>
    {near}
    <a href="{esc(f['terms_href'])}">{esc(f['terms'])}</a>
    <span class="spacer"><a href="/">{esc(f['all_apps'])}</a></span>
  </footer>
"""


def build_hub(data, langs):
    h = data["hub"]
    html = head(h["title"], h["description"], 0, SOURCE_LANG, None, langs)
    html += f"""
  <div class="hero">
    <h1>{esc(h['h1'])}</h1>
    <p class="lede">{esc(h['lede'])}</p>
  </div>

  <section>
    <a class="app" href="compressive/">
      <h3>{esc(data['app_name'])}</h3>
      <p class="small">{esc(h['app_blurb'])}</p>
      <span class="small">{esc(h['app_cta'])}</span>
    </a>
  </section>
"""
    return html + FOOT


# -------------------------------------------------------------------- main


def main():
    files = sorted(CONTENT.glob("*.json"))
    if not files:
        raise SystemExit("no content/*.json found")
    content = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in files}
    if SOURCE_LANG not in content:
        raise SystemExit(f"content/{SOURCE_LANG}.json is the source and must exist")

    # Source language first in every switcher; the rest alphabetical.
    langs = [SOURCE_LANG] + sorted(c for c in content if c != SOURCE_LANG)

    # Every translation has to answer the same keys as the source, or a missing
    # sentence ships as a KeyError at build time rather than as a blank on a
    # published privacy policy.
    for code in langs[1:]:
        check_shape(content[SOURCE_LANG], content[code], code)

    app = ROOT / "compressive"
    if app.exists():
        shutil.rmtree(app)

    written = []
    for code in langs:
        data = content[code]
        sub = app if code == SOURCE_LANG else app / code
        (sub / "privacy").mkdir(parents=True, exist_ok=True)
        (sub / "index.html").write_text(build_support(data, code, langs), encoding="utf-8")
        (sub / "privacy" / "index.html").write_text(build_privacy(data, code, langs), encoding="utf-8")
        written += [str((sub / "index.html").relative_to(ROOT)),
                    str((sub / "privacy" / "index.html").relative_to(ROOT))]

    (ROOT / "index.html").write_text(build_hub(content[SOURCE_LANG], langs), encoding="utf-8")
    written.append("index.html")

    print(f"languages: {', '.join(langs)}")
    for w in sorted(written):
        print("  ", w)


def check_shape(src, other, code, path=""):
    if isinstance(src, dict):
        for k, v in src.items():
            if k not in other:
                raise SystemExit(f"content/{code}.json is missing {path}{k}")
            check_shape(v, other[k], code, f"{path}{k}.")
    elif isinstance(src, list) and src and isinstance(src[0], dict):
        if len(src) != len(other):
            raise SystemExit(
                f"content/{code}.json: {path.rstrip('.')} has {len(other)} items, "
                f"source has {len(src)}")
        for i, item in enumerate(src):
            check_shape(item, other[i], code, f"{path}{i}.")


if __name__ == "__main__":
    main()
