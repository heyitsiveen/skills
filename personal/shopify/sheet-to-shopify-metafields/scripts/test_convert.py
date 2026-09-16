#!/usr/bin/env python3
"""
test_convert.py — Tests for the sheet-to-shopify-metafields converter.

Run from anywhere:   python3 -m unittest discover -s <this directory>
Or from here:        python3 -m unittest test_convert -v

Stdlib `unittest`. Nothing to install.

These test the converter through its public operations only — a source cell in,
a Converted value out. Nothing reaches into how the parse is structured. The
fixtures are real cells from the first target catalogue, not invented ones:
invented fixtures would not have found Welding and will not find its successor.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import convert  # noqa: E402

# Real cells. G2 and J2 are verbatim from the Source sheet; the expected HTML
# for G2 is byte-identical to what the live store already stores and the live
# theme already renders.
DETAILS_G2 = (
    "<dl><dt>Best for</dt><dd>Espresso</dd>"
    "<dt>Origins</dt><dd>Central America and Africa</dd></dl>"
)
DETAILS_G2_HTML = (
    "<ul><li>Best for: Espresso</li>"
    "<li>Origins: Central America and Africa</li></ul>"
)
BREW_PARAGRAPH = "<p>Grind fresh right before you brew.</p>"

MAPPING = {
    "handle_column": "Handle",
    "targets": [
        {"key": "custom.revamp_short_description", "type": convert.RICH_TEXT,
         "columns": ["Subheading"]},
        {"key": "custom.product_benefits", "type": convert.LIST_TEXT,
         "columns": ["Bullet 1", "Bullet 2", "Bullet 3"]},
        {"key": "custom.revamp_details", "type": convert.RICH_TEXT,
         "columns": ["Details (HTML)"]},
    ],
}


class DefinitionLists(unittest.TestCase):
    def test_becomes_one_list_with_one_item_per_pair(self):
        out = convert.convert_cell(DETAILS_G2, convert.RICH_TEXT)
        self.assertEqual(out["html"], DETAILS_G2_HTML)

    def test_four_pairs_produce_four_items(self):
        cell = "<dl>" + "".join(
            "<dt>T%d</dt><dd>V%d</dd>" % (i, i) for i in range(4)
        ) + "</dl>"
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertEqual(out["html"].count("<li>"), 4)
        self.assertEqual(out["html"].count("<ul>"), 1)

    def test_term_already_ending_in_a_colon_does_not_get_a_second(self):
        cell = "<dl><dt>Best for:</dt><dd>Espresso</dd></dl>"
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertIn("<li>Best for: Espresso</li>", out["html"])
        self.assertNotIn("::", out["html"])

    def test_plain_twin_is_one_line_per_item(self):
        out = convert.convert_cell(DETAILS_G2, convert.RICH_TEXT)
        self.assertEqual(
            out["plain"],
            "Best for: Espresso\nOrigins: Central America and Africa",
        )


class Paragraphs(unittest.TestCase):
    def test_single_paragraph_cell_stays_one_paragraph(self):
        out = convert.convert_cell(BREW_PARAGRAPH, convert.RICH_TEXT)
        self.assertEqual(out["html"], "<p>Grind fresh right before you brew.</p>")

    def test_bare_text_with_no_tags_becomes_a_paragraph(self):
        out = convert.convert_cell("Just a sentence.", convert.RICH_TEXT)
        self.assertEqual(out["html"], "<p>Just a sentence.</p>")


class Entities(unittest.TestCase):
    def test_hand_escaped_entity_survives_without_doubling(self):
        # Row 58 of the Source sheet carries the literal five characters &amp;
        cell = "<dl><dt>Origins</dt><dd>Brazil &amp; Peru</dd></dl>"
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertIn("Brazil &amp; Peru", out["html"])
        self.assertNotIn("&amp;amp;", out["html"])

    def test_plain_twin_carries_the_decoded_character(self):
        cell = "<p>Brazil &amp; Peru</p>"
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertEqual(out["plain"], "Brazil & Peru")


class InlineEmphasis(unittest.TestCase):
    def test_emphasis_inside_a_pair_is_preserved(self):
        cell = "<dl><dt>Best for</dt><dd>A <strong>sweet</strong> espresso</dd></dl>"
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertIn("<strong>sweet</strong>", out["html"])

    def test_italic_is_preserved(self):
        out = convert.convert_cell("<p>A <em>sweet</em> cup</p>", convert.RICH_TEXT)
        self.assertIn("<em>sweet</em>", out["html"])

    def test_a_link_keeps_its_href(self):
        out = convert.convert_cell(
            '<p>See <a href="https://example.com">this</a></p>', convert.RICH_TEXT
        )
        self.assertIn('<a href="https://example.com">this</a>', out["html"])


class RefusesToGuess(unittest.TestCase):
    def test_a_dt_with_no_matching_dd_is_reported(self):
        cell = "<dl><dt>Best for</dt><dd>Espresso</dd><dt>Origins</dt></dl>"
        with self.assertRaises(convert.ConversionError) as ctx:
            convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertIn("<dt>", str(ctx.exception))

    def test_a_dd_with_no_preceding_dt_is_reported(self):
        with self.assertRaises(convert.ConversionError):
            convert.convert_cell("<dl><dd>Espresso</dd></dl>", convert.RICH_TEXT)

    def test_an_unsupported_tag_stops_rather_than_being_dropped(self):
        cell = "<table><tr><td>Best for</td></tr></table>"
        with self.assertRaises(convert.ConversionError) as ctx:
            convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertIn("table", str(ctx.exception))

    def test_the_failure_names_every_unsupported_tag(self):
        with self.assertRaises(convert.ConversionError) as ctx:
            convert.convert_cell("<p>a<br><span>b</span></p>", convert.RICH_TEXT)
        msg = str(ctx.exception)
        self.assertIn("br", msg)
        self.assertIn("span", msg)


class EmptyCells(unittest.TestCase):
    def test_an_empty_cell_converts_to_nothing_at_all(self):
        self.assertIsNone(convert.convert_cell("", convert.RICH_TEXT))
        self.assertIsNone(convert.convert_cell("   ", convert.RICH_TEXT))

    def test_an_empty_cell_is_a_skip_not_an_empty_value(self):
        rows = [{"Handle": "blonde", "Subheading": "", "Bullet 1": "One",
                 "Bullet 2": "", "Bullet 3": "", "Details (HTML)": DETAILS_G2}]
        converted, report = convert.convert_rows(rows, MAPPING)
        keys = [c["key"] for c in converted]
        self.assertNotIn("custom.revamp_short_description", keys)
        self.assertEqual(len(report["skipped"]), 1)
        self.assertEqual(report["skipped"][0]["key"],
                         "custom.revamp_short_description")


class ListMetafields(unittest.TestCase):
    def test_three_columns_become_three_ordered_values(self):
        out = convert.convert_list(["One", "Two", "Three"])
        self.assertEqual(out["values"], ["One", "Two", "Three"])

    def test_an_empty_column_drops_out_and_order_holds(self):
        out = convert.convert_list(["One", "", "Three"])
        self.assertEqual(out["values"], ["One", "Three"])

    def test_all_empty_columns_convert_to_nothing(self):
        self.assertIsNone(convert.convert_list(["", "  ", ""]))

    def test_list_values_are_plain_text_not_html(self):
        out = convert.convert_list(["Sweet blend &amp; more"])
        self.assertEqual(out["values"], ["Sweet blend & more"])


class TsvParsing(unittest.TestCase):
    def test_a_quoted_cell_containing_a_tab_stays_one_cell(self):
        text = 'Handle\tSubheading\nblonde\t"holds\ta tab"\n'
        headers, rows = convert.parse_tsv(text)
        self.assertEqual(headers, ["Handle", "Subheading"])
        self.assertEqual(rows[0]["Subheading"], "holds\ta tab")

    def test_a_quoted_cell_containing_a_newline_stays_one_cell(self):
        text = 'Handle\tSubheading\nblonde\t"line one\nline two"\n'
        headers, rows = convert.parse_tsv(text)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Subheading"], "line one\nline two")

    def test_blank_lines_are_not_rows(self):
        text = "Handle\tSubheading\nblonde\tA\n\n\ncinnabun\tB\n"
        _, rows = convert.parse_tsv(text)
        self.assertEqual(len(rows), 2)

    def test_headers_keep_their_exact_spelling(self):
        text = "Handle\tDetails (HTML)\nblonde\tx\n"
        headers, _ = convert.parse_tsv(text)
        self.assertEqual(headers, ["Handle", "Details (HTML)"])


class PreFlightReporting(unittest.TestCase):
    def _rows(self):
        return [
            {"Handle": "blonde", "Subheading": "A", "Bullet 1": "One",
             "Bullet 2": "Two", "Bullet 3": "Three", "Details (HTML)": DETAILS_G2},
            {"Handle": "blonde", "Subheading": "B", "Bullet 1": "One",
             "Bullet 2": "Two", "Bullet 3": "Three", "Details (HTML)": DETAILS_G2},
        ]

    def test_duplicate_handles_are_reported(self):
        _, report = convert.convert_rows(self._rows(), MAPPING)
        self.assertIn("blonde", report["duplicate_handles"])
        self.assertEqual(report["duplicate_handles"]["blonde"], [2, 3])

    def test_identical_values_are_grouped(self):
        converted, report = convert.convert_rows(self._rows(), MAPPING)
        details = [g for g in report["groups"].values()
                   if g["key"] == "custom.revamp_details"]
        self.assertEqual(len(details), 1)
        self.assertEqual(sorted(details[0]["handles"]), ["blonde", "blonde"])

    def test_a_failing_cell_does_not_stop_the_other_cells_being_reported(self):
        rows = [{"Handle": "blonde", "Subheading": "A", "Bullet 1": "One",
                 "Bullet 2": "", "Bullet 3": "",
                 "Details (HTML)": "<table><tr><td>x</td></tr></table>"}]
        converted, report = convert.convert_rows(rows, MAPPING)
        self.assertEqual(len(report["failures"]), 1)
        self.assertEqual(report["failures"][0]["key"], "custom.revamp_details")
        self.assertIn("custom.revamp_short_description",
                      [c["key"] for c in converted])

    def test_tag_inventory_names_unsupported_tags(self):
        rows = [{"Handle": "blonde", "Subheading": "", "Bullet 1": "",
                 "Bullet 2": "", "Bullet 3": "",
                 "Details (HTML)": "<dl><dt>A</dt><dd>B<br></dd></dl>"}]
        tags = convert.tag_inventory(rows, MAPPING)
        self.assertIn("dl", tags["counts"])
        self.assertEqual(tags["unsupported"], ["br"])

    def test_sheet_row_numbers_start_at_two(self):
        rows = [{"Handle": "blonde", "Subheading": "A", "Bullet 1": "",
                 "Bullet 2": "", "Bullet 3": "", "Details (HTML)": ""}]
        converted, _ = convert.convert_rows(rows, MAPPING)
        self.assertEqual(converted[0]["row"], 2)


class BackupRoundTrip(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.path = os.path.join(self.dir, "backup.json")

    def test_values_written_come_back_unchanged(self):
        entries = [
            {"handle": "blonde", "key": "custom.revamp_details",
             "type": convert.RICH_TEXT, "value": DETAILS_G2_HTML},
            {"handle": "cinnabun", "key": "custom.product_benefits",
             "type": convert.LIST_TEXT, "value": ["One", "Two", "Three"]},
        ]
        convert.backup_write(self.path, "example-store", entries)
        back = convert.backup_read(self.path)
        self.assertEqual(back["entries"], entries)
        self.assertEqual(back["store"], "example-store")

    def test_absent_stays_absent_and_lands_in_the_delete_set(self):
        entries = [
            {"handle": "blonde", "key": "custom.revamp_details",
             "type": convert.RICH_TEXT, "value": None},
            {"handle": "cinnabun", "key": "custom.revamp_details",
             "type": convert.RICH_TEXT, "value": "<p>x</p>"},
        ]
        convert.backup_write(self.path, "example-store", entries)
        back = convert.backup_read(self.path)
        self.assertEqual(len(back["delete"]), 1)
        self.assertEqual(back["delete"][0]["handle"], "blonde")
        self.assertEqual(len(back["restore"]), 1)
        self.assertIsNone(back["delete"][0]["value"])

    def test_an_absent_value_is_never_turned_into_an_empty_string(self):
        entries = [{"handle": "blonde", "key": "k", "type": convert.RICH_TEXT,
                    "value": None}]
        convert.backup_write(self.path, "s", entries)
        with open(self.path, encoding="utf-8") as f:
            raw = json.load(f)
        self.assertIsNone(raw["entries"][0]["value"])

    def test_an_unrecognised_version_is_refused(self):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump({"version": 99, "entries": []}, f)
        with self.assertRaises(convert.ConversionError):
            convert.backup_read(self.path)


class TheWeldingGuard(unittest.TestCase):
    """The failure the whole module exists to prevent: a definition list whose
    terms end up glued to their values with no separator."""

    def test_every_term_is_separated_from_its_value(self):
        out = convert.convert_cell(DETAILS_G2, convert.RICH_TEXT)
        self.assertNotIn("Best forEspresso", out["html"])
        self.assertNotIn("Best forEspresso", out["plain"])

    def test_a_multi_pair_cell_never_runs_two_pairs_together(self):
        out = convert.convert_cell(DETAILS_G2, convert.RICH_TEXT)
        self.assertNotIn("EspressoOrigins", out["html"])
        self.assertEqual(len(out["plain"].split("\n")), 2)


if __name__ == "__main__":
    unittest.main()
