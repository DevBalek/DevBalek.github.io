# devbalek.github.io

Support and privacy pages for the apps, served by GitHub Pages.

## The HTML is generated — do not edit it

Every `index.html` under `compressive/`, and the root `index.html`, is written by
`build.py`. Edit `content/<lang>.json` (or the templates inside `build.py`), then:

    python3 build.py

and commit what changes. Editing the HTML directly works until the next build
overwrites it.

## Adding a language

Copy `content/en.json` to `content/<code>.json`, translate the values, and build.
The generator writes `compressive/<code>/`, and adds the language to every page's
switcher, `hreflang` set, and the browser-language redirect by itself.

English is the source language and is published without a path prefix, because
those URLs are already live and are the ones the app falls back to.

Two things have to move with a new language:

- `LegalLinks.translated` in the app (`Compressive/Views/Components.swift`) — the
  app picks the URL by language, and a code it lists but the site has not
  published is a 404 on the privacy policy.
- Nothing else. The site handles the rest.
