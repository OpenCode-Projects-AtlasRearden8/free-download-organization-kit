"""Tests for the Free Download Organization Kit.

Run with:  python3 -m unittest discover -s tests -v
(or just:  make test )

Validates:
  1. Data schema — every CSV/JSON item has required fields with valid values.
  2. Data sync — freebies.json mirrors freebies.csv item for item.
  3. Page rendering — build.py produces an index.html that contains every
     item, the filter buttons, the legend, and no leftover placeholders.
  4. Housekeeping — LICENSE text, README credit, no secrets in data files.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import tempfile
import unittest
from html import escape  # noqa: F401  (kept for future HTML assertions)
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import build  # noqa: E402

CSV_PATH = ROOT / "data" / "freebies.csv"
JSON_PATH = ROOT / "data" / "freebies.json"
TEMPLATE_PATH = ROOT / "templates" / "catalog-template.html"
README_PATH = ROOT / "README.md"
LICENSE_PATH = ROOT / "LICENSE"
RIGHTS_CARD_PATH = ROOT / "rights-card.html"
SORTED_VALID_CATEGORIES = sorted(build.VALID_CATEGORIES)
SORTED_VALID_RIGHTS = sorted(build.VALID_RIGHTS)


class SchemaTests(unittest.TestCase):
    """The CSV data must pass the full validation rules."""

    @classmethod
    def setUpClass(cls):
        cls.items = build.load_items(CSV_PATH)

    def test_load_succeeds(self):
        self.assertGreaterEqual(len(self.items), 5, "starter example entries missing")

    def test_categories_are_valid(self):
        for item in self.items:
            self.assertIn(item["category"], build.VALID_CATEGORIES,
                          f"{item['id']}: bad category")

    def test_usage_rights_are_valid(self):
        for item in self.items:
            self.assertIn(item["usage_rights"], build.VALID_RIGHTS,
                          f"{item['id']}: bad usage_rights")

    def test_yes_no_fields_are_boolean_words(self):
        for item in self.items:
            for field in ("can_edit", "must_credit"):
                self.assertIn(item[field], ("true", "false"),
                              f"{item['id']}: {field} must be true/false")

    def test_urls_look_like_urls(self):
        for item in self.items:
            for field in ("source_url", "license_url"):
                self.assertRegex(item[field], r"^https?://\S+$",
                                 f"{item['id']}: {field} is not a URL")

    def test_unique_ids_in_snake_dash_format(self):
        ids = [item["id"] for item in self.items]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids in CSV")
        for item_id in ids:
            self.assertRegex(item_id, r"^[a-z0-9][a-z0-9-]*$")

    def test_download_locations_are_local_paths_or_plausible(self):
        for item in self.items:
            loc = item["download_location"]
            self.assertTrue(loc, f"{item['id']}: empty download_location")


class JsonSyncTests(unittest.TestCase):
    """freebies.json should mirror the CSV exactly (plus the description key)."""

    @classmethod
    def setUpClass(cls):
        cls.csv_items = build.load_items(CSV_PATH)
        raw = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        cls.json_items = raw["items"]

    def test_same_length(self):
        self.assertEqual(len(self.csv_items), len(self.json_items))

    def test_items_match_by_id(self):
        csv_by_id = {i["id"]: i for i in self.csv_items}
        json_by_id = {i["id"]: i for i in self.json_items}
        self.assertEqual(csv_by_id["ex-font-display-serif"]["title"],
                         json_by_id["ex-font-display-serif"]["title"])
        self.assertEqual(set(csv_by_id), set(json_by_id))

    def test_sync_produces_identical_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_json = Path(tmp) / "freebies.json"
            build.json_sync(self.csv_items, tmp_json)
            synced = json.loads(tmp_json.read_text(encoding="utf-8"))
        self.assertEqual(synced["items"], self.json_items)


class RenderingTests(unittest.TestCase):
    """build.py must render an index.html that actually shows the catalog."""

    @classmethod
    def setUpClass(cls):
        cls.items = build.load_items(CSV_PATH)
        with tempfile.TemporaryDirectory() as tmp:
            cls.out_html = build.build(cls.items, Path(tmp) / "index.html")
        cls.subprocess_ok = True

    def _run_build(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "build.py"), *args],
            capture_output=True, text=True, cwd=ROOT,
        )

    def test_template_placeholders_all_filled(self):
        self.assertNotRegex(self.out_html, r"\{\{[A-Z_]+\}\}")

    def test_every_item_title_renders(self):
        for item in self.items:
            self.assertIn(escape(item["title"]), self.out_html,
                          f"title missing from rendered page: {item['title']}")
            self.assertIn(item["download_location"], self.out_html)
            self.assertIn(item["license_type"], self.out_html)

    def test_every_item_has_a_row_with_category_marker(self):
        for item in self.items:
            self.assertIn(f'data-category="{item["category"]}"', self.out_html)

    def test_filter_buttons_render_with_counts(self):
        categories = sorted({i["category"] for i in self.items})
        for cat in categories:
            self.assertRegex(self.out_html,
                             rf"data-filter=\"{cat}\">[^<]*\((\d+)\)")

    def test_page_has_usage_rights_legend(self):
        for badge in build.VALID_RIGHTS:
            self.assertIn(f">{badge}</span>", self.out_html)

    def test_page_structure_is_sane(self):
        self.assertIn("<!DOCTYPE html", self.out_html)
        self.assertIn('<table id="catalog"', self.out_html)
        self.assertIn("data-no-signup=\"true\"", self.out_html)

    def test_escapes_hostile_data(self):
        hostile = {
            **self.items[0],
            "title": "<script>alert(1)</script>",
            "notes": '"quoted" & <tag>',
        }
        row = build.render_row(hostile)
        self.assertNotIn("<script>", row)
        self.assertIn("&lt;script&gt;", row)
        self.assertIn("&quot;quoted&quot; &amp; &lt;tag&gt;", row)

    def test_cli_build_and_check_succeed_against_real_data(self):
        result = self._run_build("--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_project_index_html_matches_template_output(self):
        committed = (ROOT / "index.html").read_text(encoding="utf-8")
        freshly_rendered_rows = re.findall(r"<tr data-category.*?</tr>",
                                           self.out_html, re.S)
        for row in freshly_rendered_rows:
            self.assertIn(row, committed)


class FailureModeTests(unittest.TestCase):
    """Bad data must be rejected with a clear message, not crash the build."""

    def _write_and_load(self, csv_text: str) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.csv"
            bad.write_text(csv_text, encoding="utf-8")
            with self.assertRaises(build.DataError):
                build.load_items(bad)

    def test_missing_required_column_rejected(self):
        text = ("id,title,category\n"
                "a,Some title,font\n")
        self._write_and_load(text)

    def test_empty_required_field_rejected(self):
        text = ("id,title,category,source_url,download_location,license_type,"
                "license_url,usage_rights,can_edit,must_credit,notes\n"
                "a,,font,https://x.com/,~/x,OFL,https://x.com/,commercial-ok,"
                "true,false,n\n")
        self._write_and_load(text)

    def test_bad_category_rejected(self):
        text = ("id,title,category,source_url,download_location,license_type,"
                "license_url,usage_rights,can_edit,must_credit,notes\n"
                "a,Title,flyingthing,https://x.com/,~/x,OFL,https://x.com/,"
                "commercial-ok,true,false,n\n")
        self._write_and_load(text)

    def test_duplicate_ids_rejected(self):
        header = ("id,title,category,source_url,download_location,license_type,"
                  "license_url,usage_rights,can_edit,must_credit,notes\n")
        row1 = "dup,T1,font,https://x.com/,~/x,OFL,https://x.com/,commercial-ok,true,false,n\n"
        row2 = "dup,T2,font,https://x.com/,~/y,OFL,https://x.com/,commercial-ok,true,false,n\n"
        self._write_and_load(header + row1 + row2)

    def test_non_url_license_link_rejected(self):
        text = ("id,title,category,source_url,download_location,license_type,"
                "license_url,usage_rights,can_edit,must_credit,notes\n"
                "a,T,font,https://x.com/,~/x,OFL,not-a-url,commercial-ok,"
                "true,false,n\n")
        self._write_and_load(text)


class HousekeepingTests(unittest.TestCase):
    """Project hygiene: license, README credit, no secrets in data files."""

    def test_license_exists_with_correct_copyright_line(self):
        text = LICENSE_PATH.read_text(encoding="utf-8")
        self.assertIn("MIT License", text)
        self.assertIn("Copyright (c) 2026 Asdale Dynamics, LLC", text)

    def test_readme_credits_asdale_dynamics(self):
        text = README_PATH.read_text(encoding="utf-8")
        self.assertIn("Asdale Dynamics, LLC", text)

    def test_data_files_contain_no_secrets(self):
        secret_pattern = re.compile(
            r"(api[_-]?key|secret|password|passwd|token\s*=|Bearer\s|sk-)",
            re.I,
        )
        for path in (CSV_PATH, JSON_PATH):
            text = path.read_text(encoding="utf-8")
            match = secret_pattern.search(text)
            self.assertIsNone(match, f"possible secret in {path.name}: {match!r}")

    def test_rights_card_is_printable_and_linked_from_catalog(self):
        text = RIGHTS_CARD_PATH.read_text(encoding="utf-8")
        self.assertIn("@media print", text)
        self.assertIn("window.print", text)
        catalog = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("rights-card.html", catalog)

    def test_license_guide_exists_and_images_paths_resolve(self):
        guide = (ROOT / "docs" / "license-types.md").read_text(encoding="utf-8")
        self.assertIn("OFL", guide)
        self.assertIn("CC BY", guide)


if __name__ == "__main__":
    unittest.main()
