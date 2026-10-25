# Free Download Organization Kit

A friendly, local-first home for all the free stuff you download — fonts,
printables, ebooks, audio packs — and a record of what each one's license
actually lets you do with it.

Think of it as a library card file for your Downloads folder. Every catalog
row answers three questions in plain English:

1. **Where does the file live?** (which folder, which zip)
2. **What license does it carry?** (with a link to the actual license page)
3. **What am I allowed to do with it?** (sell, edit, share — or hands off)

## What's in the kit

| File | What it is |
|---|---|
| `index.html` | The catalog page. Opens in any browser, no server or signup needed. |
| `data/freebies.csv` | **Your catalog data.** Edit this — it's the source of truth. |
| `data/freebies.json` | A machine-readable mirror of the CSV, kept in sync by `build.py`. |
| `docs/license-types.md` | Free licenses explained like a friend would (MIT, CC0, CC BY, OFL, "personal use only", marketplace terms...). |
| `rights-card.html` | A one-page printable rights card — the cheat-sheet version of the guide. |
| `templates/catalog-template.html` | The page template `build.py` fills with your rows. |
| `build.py` | The rebuild tool. Validates your data, syncs the JSON, regenerates `index.html`. |
| `tests/test_freebies.py` | Tests that check your data schema and that the page renders. |

## Quick start

Everything runs locally. You need Python 3 (any modern version) and a browser.

```bash
# 1. Open the catalog
open index.html           # macOS  (on Windows: start index.html)

# 2. Add your own freebies
open data/freebies.csv    # add one row per download

# 3. Rebuild the page and re-check the data
python3 build.py

# 4. Run the tests anytime
python3 -m unittest discover -s tests -v
```

Or use the handy shortcuts:

```bash
python3 build.py --check   # validate data only
python3 build.py --sync    # re-sync freebies.json from the CSV
```

## How to add a freebie

Add a row to `data/freebies.csv`. Every column matters — that's the point.

A row looks like this:

```csv
ex-font-display-serif,Playfair-Style Display Serif,font,https://fonts.google.com/,~/Downloads/fonts/display-serif/playfair.zip,OFL 1.1,https://openfontlicense.org/,commercial-ok,true,false,"Safe for book covers; may be embedded in PDFs."
```

Column cheat sheet:

| Column | Meaning |
|---|---|
| `id` | Short unique lowercase-dash name for the item. |
| `title` | Human name of the download. |
| `category` | One of: `font`, `printable`, `ebook`, `audio`, `other`. |
| `source_url` | Where you downloaded it from. |
| `download_location` | Where the file lives on *your* machine (e.g. `~/Downloads/...`). |
| `license_type` | The license name, as stated by the creator. |
| `license_url` | Link to the actual license/terms page. |
| `usage_rights` | One of four plain-English badges: `commercial-ok`, `share-and-adapt`, `personal-use-only`, or `check-me`. |
| `can_edit` | `true` if you may modify the work, else `false`. |
| `must_credit` | `true` if the license asks for a credit line. |
| `notes` | Anything future-you will want to know. |

If `build.py` catches a typo (bad category, missing URL, duplicate id), it
tells you the exact line number to fix.

## Usage-rights badges at a glance

- **commercial-ok** — safe for projects you sell (still skim the license page).
- **share-and-adapt** — Creative Commons-style sharing and remixing, usually with credit.
- **personal-use-only** — your own projects only; commercial use needs a purchase.
- **check-me** — rights unclear; read the license page before using it.

The full plain-English explanations live in [`docs/license-types.md`](docs/license-types.md),
and [`rights-card.html`](rights-card.html) prints the whole thing on one sheet.

## A tiny workflow that works

1. Download a font/pack/ebook.
2. Unzip it somewhere sensible (e.g. `~/Downloads/fonts/<name>/`).
3. Open the license page once. Copy the link.
4. Add one row to the CSV.
5. Run `python3 build.py`. Done — five seconds, no future guessing.

## Design notes

- **Local-first:** your data stays in this folder. No accounts, no tracking, no uploads. The page works from a plain `file://` open.
- **Plain English over legalese:** the badges and the license guide are written to be understood at a glance.
- **Fail loudly on bad data:** `build.py` and the tests catch schema mistakes immediately with line numbers.
- **Beginner friendly:** every column, command, and concept is explained in this README — no prior scripting required.

## Tests

The test suite validates the data schema (required fields, valid categories
and rights, URL formats, unique ids), CSV/JSON sync, and the rendered page
(every item listed, filter buttons, badge legend, hostile-HTML escaping):

```bash
python3 -m unittest discover -s tests -v
```

## Example data disclaimer

The starter rows in `data/freebies.csv` are **example entries** marked as such.
Swap them out with your own downloads — keep at least one item so the page
has something to render.

## Credits

Built and maintained by **Asdale Dynamics, LLC** — Dylan Asdale's company for
plain-English AI education, practical author tools, and local-first software.
Part of the same family as *The Massive AI Manual* and [dylanasdale.github.io](https://dylanasdale.github.io/).

Licensed under the MIT license — see [`LICENSE`](LICENSE).
