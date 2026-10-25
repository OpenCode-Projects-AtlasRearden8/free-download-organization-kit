#!/usr/bin/env python3
"""Build the Freebie Shelf catalog page from data/freebies.csv.

Local-first, no dependencies. Python 3 standard library only.

Commands:
    python3 build.py            rebuild index.html and sync data/freebies.json
    python3 build.py --sync     only sync freebies.json from freebies.csv
    python3 build.py --check    validate data without writing files (for CI/tests)

The CSV file (data/freebies.csv) is the source of truth.
"""

from __future__ import annotations

import argparse
import csv
import datetime
import json
import re
import sys
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CSV_PATH = ROOT / "data" / "freebies.csv"
JSON_PATH = ROOT / "data" / "freebies.json"
TEMPLATE_PATH = ROOT / "templates" / "catalog-template.html"
OUTPUT_PATH = ROOT / "index.html"

REQUIRED_FIELDS = [
    "id", "title", "category", "source_url", "download_location",
    "license_type", "license_url", "usage_rights", "can_edit",
    "must_credit", "notes",
]
VALID_CATEGORIES = ["font", "printable", "ebook", "audio", "other"]
VALID_RIGHTS = [
    "commercial-ok", "share-and-adapt", "personal-use-only", "check-me",
]
YES_NO = {"true": True, "false": False}

PLACEHOLDER_RE = re.compile(r"\{\{[A-Z_]+\}\}")


class DataError(Exception):
    """Raised when catalog data fails validation."""


def load_items(csv_path: Path = CSV_PATH) -> list[dict]:
    """Read the catalog CSV and return validated item dicts."""
    items = []
    with csv_path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fieldnames = reader.fieldnames or []
        missing_cols = [f for f in REQUIRED_FIELDS if f not in fieldnames]
        if missing_cols:
            raise DataError(f"CSV is missing required columns: {', '.join(missing_cols)}")
        seen_ids: set[str] = set()
        for lineno, row in enumerate(reader, start=2):
            item = {k: (row.get(k) or "").strip() for k in REQUIRED_FIELDS}
            errors = validate_item(item, lineno)
            if errors:
                raise DataError(
                    f"{csv_path.name} line {lineno}: " + "; ".join(errors)
                )
            if item["id"] in seen_ids:
                raise DataError(
                    f"{csv_path.name} line {lineno}: duplicate id '{item['id']}'"
                )
            seen_ids.add(item["id"])
            items.append(item)
    if not items:
        raise DataError(f"{csv_path.name} has no data rows")
    return items


def validate_item(item: dict, lineno: int) -> list[str]:
    errors = []
    for field in REQUIRED_FIELDS:
        if not item.get(field):
            errors.append(f"missing/empty field '{field}'")
    if item.get("id") and not re.fullmatch(r"[a-z0-9][a-z0-9-]*", item["id"]):
        errors.append(
            f"id '{item['id']}' must use lowercase letters, digits, and dashes"
        )
    if item.get("category") and item["category"] not in VALID_CATEGORIES:
        errors.append(
            f"category '{item['category']}' not in {VALID_CATEGORIES}"
        )
    if item.get("usage_rights") and item["usage_rights"] not in VALID_RIGHTS:
        errors.append(
            f"usage_rights '{item['usage_rights']}' not in {VALID_RIGHTS}"
        )
    for field in ("can_edit", "must_credit"):
        if field in item and item[field].lower() not in YES_NO:
            errors.append(f"{field} must be 'true' or 'false', got '{item[field]}'")
    for field in ("source_url", "license_url"):
        url = item.get(field, "")
        if url and not re.match(r"^https?://\S+$", url):
            errors.append(f"{field} must start with http:// or https:// ({url})")
    return errors


def json_sync(items: list[dict], json_path: Path = JSON_PATH) -> None:
    """Write freebies.json so it mirrors the CSV (minus the example comment)."""
    payload = {"_description": "Mirror of data/freebies.csv, kept in sync by build.py.", "items": items}
    json_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def render_row(item: dict) -> str:
    rights = item["usage_rights"]
    badge_kind = {
        "commercial-ok": "ok",
        "share-and-adapt": "share",
        "personal-use-only": "personal",
        "check-me": "unknown",
    }[rights]
    rights_badge = (
        f'<span class="badge badge-{badge_kind}">{escape(rights)}</span>'
    )
    extras = []
    if item["must_credit"] == "True" or item["must_credit"] == "true":
        extras.append("credit required")
    if item["can_edit"] == "True" or item["can_edit"] == "true":
        extras.append("edits allowed")
    extras_txt = ""
    if extras:
        extras_txt = '<span class="notes">✔ ' + ", ".join(extras) + "</span>"
    return (
        "<tr data-category=\"{cat}\">"
        "<td class=\"freebie-title\">{title}<span class=\"notes\">{notes}</span></td>"
        "<td>{cat}</td>"
        "<td><a href=\"{src}\" rel=\"noopener\">{src_short}</a></td>"
        "<td class=\"path\">{loc}</td>"
        "<td class=\"license-cell\"><a href=\"{lic}\" rel=\"noopener\">{lic_name}</a>{extras}</td>"
        "<td>{badge}</td>"
        "</tr>"
    ).format(
        cat=escape(item["category"]),
        title=escape(item["title"]),
        notes=escape(item["notes"]),
        src=escape(item["source_url"], quote=True),
        src_short=escape(_host(item["source_url"])),
        loc=escape(item["download_location"]),
        lic=escape(item["license_url"], quote=True),
        lic_name=escape(item["license_type"]),
        extras=extras_txt,
        badge=rights_badge,
    )


def _host(url: str) -> str:
    match = re.match(r"^https?://([^/?#]+)", url)
    return match.group(1) if match else url


def build(items: list[dict], out_path: Path = OUTPUT_PATH) -> str:
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rows = "\n".join("  " + render_row(item) for item in items)
    categories = []
    for item in items:
        if item["category"] not in categories:
            categories.append(item["category"])
    cat_buttons = "\n  ".join(
        f'<button class="chip" data-filter="{escape(c)}">{escape(c.title())}'
        f' ({_count(items, c)})</button>'
        for c in categories
    )
    html = template.replace("{{ROWS}}", rows)
    html = html.replace("{{CATEGORY_BUTTONS}}", cat_buttons)
    html = html.replace("{{TOTAL}}", str(len(items)))
    html = html.replace("{{CATEGORIES}}", str(len(categories)))
    html = html.replace("{{GENERATED}}", datetime.date.today().isoformat())
    left = PLACEHOLDER_RE.findall(html)
    if left:
        raise DataError(f"unfilled template placeholders: {', '.join(left)}")
    out_path.write_text(html, encoding="utf-8")
    return html


def _count(items: list[dict], category: str) -> int:
    return sum(1 for i in items if i["category"] == category)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sync", action="store_true", help="only sync freebies.json from CSV")
    parser.add_argument("--check", action="store_true", help="validate data, write nothing")
    args = parser.parse_args(argv)
    try:
        items = load_items()
        if args.check:
            print(f"OK: {len(items)} valid items in {CSV_PATH.name}")
            return 0
        json_sync(items)
        if args.sync:
            print(f"Synced {len(items)} items to {JSON_PATH.name}")
            return 0
        build(items)
        print(f"Built {OUTPUT_PATH.name} from {len(items)} items. Open it in any browser.")
        return 0
    except (DataError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
