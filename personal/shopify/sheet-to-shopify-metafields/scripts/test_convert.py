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


B = "•"  # the bullet glyph real sheets use


class PlainTextCells(unittest.TestCase):
    """Most sheets carry no markup at all. Their structure is newlines and
    bullet glyphs, and running those through an HTML parser damages prose."""

    def test_prose_keeps_its_angle_brackets(self):
        out = convert.convert_cell("Size < 10cm and > 5cm", convert.RICH_TEXT)
        self.assertEqual(out["html"], "<p>Size &lt; 10cm and &gt; 5cm</p>")

    def test_prose_with_angle_brackets_is_one_paragraph_not_three(self):
        out = convert.convert_cell("Size < 10cm and > 5cm", convert.RICH_TEXT)
        self.assertEqual(out["html"].count("<p>"), 1)

    def test_tag_shaped_prose_naming_no_element_stays_text(self):
        out = convert.convert_cell("100% cotton <do not bleach>", convert.RICH_TEXT)
        self.assertEqual(out["html"], "<p>100% cotton &lt;do not bleach&gt;</p>")

    def test_a_real_html_element_still_stops_the_run(self):
        with self.assertRaises(convert.ConversionError):
            convert.convert_cell("a <span>b</span> c", convert.RICH_TEXT)

    def test_a_heading_line_then_bullets_becomes_paragraph_then_list(self):
        cell = f"Features\n{B} Top zipper\n{B} Fits standard credit cards"
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertEqual(
            out["html"],
            "<p>Features</p><ul><li>Top zipper</li>"
            "<li>Fits standard credit cards</li></ul>",
        )

    def test_a_blank_line_closes_the_list_so_groups_stay_separate(self):
        cell = f"Leather\n{B} Soft.\n\nHardware\n{B} Strong."
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertEqual(
            out["html"],
            "<p>Leather</p><ul><li>Soft.</li></ul>"
            "<p>Hardware</p><ul><li>Strong.</li></ul>",
        )

    def test_crlf_line_endings_are_normalised(self):
        cell = f"Leather\r\n{B} Soft.\r\n{B} Durable."
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertNotIn("\r", out["html"])
        self.assertEqual(out["html"].count("<li>"), 2)

    def test_trailing_blank_lines_make_no_empty_paragraphs(self):
        out = convert.convert_cell(f"Leather\n{B} Soft.\n\n\n", convert.RICH_TEXT)
        self.assertNotIn("<p></p>", out["html"])
        self.assertTrue(out["html"].endswith("</ul>"))

    def test_lines_with_no_bullets_become_separate_paragraphs(self):
        out = convert.convert_cell("First line.\nSecond line.", convert.RICH_TEXT)
        self.assertEqual(out["html"], "<p>First line.</p><p>Second line.</p>")

    def test_a_hyphen_bullet_is_a_bullet_but_a_hyphenated_word_is_not(self):
        out = convert.convert_cell("- One\n- Two", convert.RICH_TEXT)
        self.assertEqual(out["html"], "<ul><li>One</li><li>Two</li></ul>")
        prose = convert.convert_cell("high-quality leather", convert.RICH_TEXT)
        self.assertEqual(prose["html"], "<p>high-quality leather</p>")

    def test_the_cell_reports_which_path_it_took(self):
        self.assertEqual(
            convert.convert_cell("Plain.", convert.RICH_TEXT)["kind"], "text")
        self.assertEqual(
            convert.convert_cell(DETAILS_G2, convert.RICH_TEXT)["kind"], "markup")


class Hyperlinks(unittest.TestCase):
    """A sheet's hyperlinks exist only as cell formatting. The plain-text read
    drops every href; one real sheet carries 59 of them."""

    def test_a_link_run_inside_a_text_cell_keeps_its_href(self):
        cell = 'Protect it with <a href="https://x.com/p/balm">Super VII balm</a>.'
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertIn('<a href="https://x.com/p/balm">Super VII balm</a>',
                      out["html"])

    def test_a_link_inside_a_bullet_survives(self):
        cell = f'{B} Use <a href="https://x.com/b">the balm</a> monthly.'
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertIn("<li>Use <a href=", out["html"])

    def test_the_plain_twin_carries_the_anchor_text_only(self):
        cell = 'Protect it with <a href="https://x.com/p/balm">balm</a>.'
        out = convert.convert_cell(cell, convert.RICH_TEXT)
        self.assertEqual(out["plain"], "Protect it with balm.")


class ListValuesFromLines(unittest.TestCase):
    def test_a_bulleted_cell_becomes_one_value_per_line(self):
        out = convert.convert_list([f"{B} One\n{B} Two\n{B} Three"])
        self.assertEqual(out["values"], ["One", "Two", "Three"])

    def test_three_columns_still_become_three_values(self):
        out = convert.convert_list(["One", "Two", "Three"])
        self.assertEqual(out["values"], ["One", "Two", "Three"])

    def test_columns_and_lines_compose(self):
        out = convert.convert_list([f"{B} One\n{B} Two", "Three"])
        self.assertEqual(out["values"], ["One", "Two", "Three"])

    def test_blank_lines_produce_no_empty_values(self):
        out = convert.convert_list([f"{B} One\n\n\n{B} Two\n"])
        self.assertEqual(out["values"], ["One", "Two"])


class HandleFromUrl(unittest.TestCase):
    """One real sheet has no handle column at all — only a product URL."""

    MAP = {"handle_column": {"from_url": "Product URL"}}

    def test_the_last_path_segment_is_the_handle(self):
        row = {"Product URL": "https://shop.com/products/leather-bag"}
        self.assertEqual(convert.row_handle(row, self.MAP), "leather-bag")

    def test_a_query_string_and_trailing_slash_are_ignored(self):
        row = {"Product URL": "https://shop.com/products/leather-bag/?variant=1"}
        self.assertEqual(convert.row_handle(row, self.MAP), "leather-bag")

    def test_a_url_cell_carrying_link_formatting_still_yields_a_handle(self):
        # A URL cell often has link formatting, so the HTML read delivers it
        # as an anchor. Eight of 52 cells on a real sheet did, and the naive
        # last-path-segment gave every one of them the handle `a>`.
        row = {"Product URL":
               '<a href="https://shop.com/products/leather-bag">'
               'https://shop.com/products/leather-bag</a>'}
        self.assertEqual(convert.row_handle(row, self.MAP), "leather-bag")

    def test_the_href_is_preferred_over_the_anchor_text(self):
        row = {"Product URL":
               '<a href="https://shop.com/products/real-handle">click here</a>'}
        self.assertEqual(convert.row_handle(row, self.MAP), "real-handle")

    def test_a_plain_url_cell_is_unaffected(self):
        row = {"Product URL": "https://shop.com/products/leather-bag"}
        self.assertEqual(convert.row_handle(row, self.MAP), "leather-bag")

    def test_a_named_handle_column_still_works(self):
        self.assertEqual(
            convert.row_handle({"Handle": "blonde"}, {"handle_column": "Handle"}),
            "blonde")


class VisitingTheProductUrl(unittest.TestCase):
    """A handle derived from a URL is a guess. A renamed product keeps its old
    URL working and redirects, so the guess can be stale — it finds nothing, or
    finds the wrong product."""

    MAP = {
        "handle_column": {"from_url": "Product URL"},
        "targets": [{"key": "custom.details", "type": convert.RICH_TEXT,
                     "columns": ["Details"]}],
    }
    ROWS = [
        {"Product URL": "https://shop.com/products/old-name", "Details": "A."},
        {"Product URL": "https://shop.com/products/leather-bag", "Details": "B."},
        {"Product URL": "https://shop.com/products/old-name", "Details": "C."},
    ]

    def test_the_urls_to_visit_are_distinct_and_in_sheet_order(self):
        urls = convert.product_urls(self.ROWS, self.MAP)
        self.assertEqual(urls, ["https://shop.com/products/old-name",
                                "https://shop.com/products/leather-bag"])

    def test_without_a_visit_every_row_is_reported_unresolved(self):
        _, report = convert.convert_rows(self.ROWS, self.MAP)
        self.assertEqual(len(report["unresolved_urls"]), 3)
        self.assertEqual(report["unresolved_urls"][0]["derived"], "old-name")

    def test_the_visited_handle_wins_over_the_derived_one(self):
        resolved = {"https://shop.com/products/old-name":
                    {"handle": "new-name", "title": "The New Name"}}
        row = self.ROWS[0]
        self.assertEqual(convert.row_handle(row, self.MAP), "old-name")
        self.assertEqual(convert.row_handle(row, self.MAP, resolved), "new-name")

    def test_a_renamed_product_is_flagged_with_both_handles(self):
        resolved = {
            "https://shop.com/products/old-name":
                {"handle": "new-name", "title": "The New Name"},
            "https://shop.com/products/leather-bag":
                {"handle": "leather-bag", "title": "Leather Bag"},
        }
        _, report = convert.convert_rows(self.ROWS, self.MAP, resolved)
        self.assertEqual(report["unresolved_urls"], [])
        renamed = report["renamed_products"]
        self.assertEqual(len(renamed), 2)  # the same URL appears on two rows
        self.assertEqual(renamed[0]["derived"], "old-name")
        self.assertEqual(renamed[0]["actual"], "new-name")

    def test_an_unchanged_handle_is_not_flagged(self):
        resolved = {"https://shop.com/products/leather-bag":
                    {"handle": "leather-bag", "title": "Leather Bag"}}
        _, report = convert.convert_rows([self.ROWS[1]], self.MAP, resolved)
        self.assertEqual(report["renamed_products"], [])

    def test_the_exact_title_is_carried_for_searching_the_admin(self):
        resolved = {"https://shop.com/products/leather-bag":
                    {"handle": "leather-bag", "title": "Women's Leather Bag"}}
        _, report = convert.convert_rows([self.ROWS[1]], self.MAP, resolved)
        self.assertEqual(report["titles"]["leather-bag"], "Women's Leather Bag")

    def test_a_row_with_no_url_is_reported_rather_than_silently_skipped(self):
        _, report = convert.convert_rows([{"Product URL": "", "Details": "A."}],
                                         self.MAP, {})
        self.assertEqual(len(report["unresolved_urls"]), 1)
        self.assertIn("no product URL", report["unresolved_urls"][0]["reason"])

    def test_a_named_handle_column_needs_no_visiting_at_all(self):
        mapping = dict(self.MAP, handle_column="Handle")
        _, report = convert.convert_rows([{"Handle": "blonde", "Details": "A."}],
                                         mapping)
        self.assertNotIn("unresolved_urls", report)


class ClipboardHtmlRead(unittest.TestCase):
    HTML = (
        "<table><tr><th>Product Name</th><th>Materials</th></tr>"
        "<tr><td>Purse</td><td>Leather<br>"
        f"{B} Use <a href='https://x.com/balm'>balm</a><br>"
        f"{B} Keep dry</td></tr></table>"
    )

    def test_headers_and_rows_come_back(self):
        headers, rows = convert.parse_clipboard_html(self.HTML)
        self.assertEqual(headers, ["Product Name", "Materials"])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Product Name"], "Purse")

    def test_line_breaks_become_newlines(self):
        _, rows = convert.parse_clipboard_html(self.HTML)
        self.assertEqual(rows[0]["Materials"].count("\n"), 2)

    def test_the_href_survives_the_read(self):
        _, rows = convert.parse_clipboard_html(self.HTML)
        self.assertIn('href="https://x.com/balm"', rows[0]["Materials"])

    def test_the_cell_then_converts_with_its_link_intact(self):
        _, rows = convert.parse_clipboard_html(self.HTML)
        out = convert.convert_cell(rows[0]["Materials"], convert.RICH_TEXT)
        self.assertIn('<a href="https://x.com/balm">balm</a>', out["html"])
        self.assertEqual(out["html"].count("<li>"), 2)


class ColumnShapeReport(unittest.TestCase):
    MAP = {
        "handle_column": "Handle",
        "targets": [{"key": "custom.details", "type": convert.RICH_TEXT,
                     "columns": ["Details"]}],
    }

    def test_it_says_whether_a_column_is_text_or_markup(self):
        rows = [{"Handle": "a", "Details": f"Features\n{B} One"},
                {"Handle": "b", "Details": DETAILS_G2}]
        shapes = convert.column_shapes(rows, self.MAP)["Details"]
        self.assertEqual(shapes["text"], 1)
        self.assertEqual(shapes["markup"], 1)
        self.assertEqual(shapes["bulleted"], 1)
        self.assertEqual(shapes["multiline"], 1)

    def test_it_counts_cells_carrying_links(self):
        rows = [{"Handle": "a", "Details": 'Use <a href="https://x.com">it</a>'}]
        self.assertEqual(
            convert.column_shapes(rows, self.MAP)["Details"]["with_links"], 1)

    def test_tag_shaped_prose_is_flagged_not_failed(self):
        rows = [{"Handle": "a", "Details": "cotton <do not bleach>"}]
        shapes = convert.column_shapes(rows, self.MAP)["Details"]
        self.assertEqual(shapes["taglike_text"], ["<do not bleach>"])
        _, report = convert.convert_rows(rows, self.MAP)
        self.assertEqual(report["failures"], [])


class MatchingAgainstTheAdmin(unittest.TestCase):
    """The bulk editor is positional. The sheet's order and the admin's order
    have no reason to agree, so the handle is what ties a row to a product."""

    CONVERTED = [
        {"handle": "blonde", "key": "custom.details", "type": convert.RICH_TEXT},
        {"handle": "blonde", "key": "custom.materials", "type": convert.RICH_TEXT},
        {"handle": "caramel", "key": "custom.details", "type": convert.RICH_TEXT},
        {"handle": "pumpkin", "key": "custom.details", "type": convert.RICH_TEXT},
    ]
    # Admin order deliberately unlike the sheet's, with strangers interleaved.
    ADMIN = ["zebra-bag", "pumpkin", "aardvark", "blonde", "caramel", "yak"]

    def test_every_sheet_product_is_found_whatever_the_order(self):
        r = convert.match_admin(self.CONVERTED, self.ADMIN)
        self.assertEqual(r["sheet_handles"], 3)
        self.assertEqual(r["matched"], 3)
        self.assertEqual(r["missing_from_admin"], [])

    def test_it_says_plainly_that_the_orders_disagree(self):
        r = convert.match_admin(self.CONVERTED, self.ADMIN)
        self.assertFalse(r["orders_agree"])

    def test_rows_are_planned_by_admin_position_not_sheet_position(self):
        r = convert.match_admin(self.CONVERTED, self.ADMIN)
        positions = {w["handle"]: w["list_position"] for w in r["batches"][0]["write"]}
        self.assertEqual(positions, {"pumpkin": 2, "blonde": 4, "caramel": 5})

    def test_products_not_in_the_sheet_are_left_out_of_the_plan(self):
        r = convert.match_admin(self.CONVERTED, self.ADMIN)
        planned = {w["handle"] for w in r["batches"][0]["write"]}
        self.assertNotIn("zebra-bag", planned)
        self.assertNotIn("aardvark", planned)
        self.assertEqual(r["untouched_admin_products"], 3)

    def test_a_sheet_product_missing_from_the_admin_is_reported(self):
        r = convert.match_admin(self.CONVERTED, ["blonde", "caramel"])
        self.assertEqual(r["missing_from_admin"], ["pumpkin"])

    def test_each_row_carries_the_fields_it_needs(self):
        r = convert.match_admin(self.CONVERTED, self.ADMIN)
        blonde = [w for w in r["batches"][0]["write"] if w["handle"] == "blonde"][0]
        self.assertEqual(blonde["fields"],
                         ["custom.details", "custom.materials"])

    def test_the_plan_is_split_into_pages_of_fifty(self):
        admin = [f"p{i}" for i in range(120)]
        converted = [{"handle": "p3", "key": "k", "type": convert.RICH_TEXT},
                     {"handle": "p60", "key": "k", "type": convert.RICH_TEXT},
                     {"handle": "p119", "key": "k", "type": convert.RICH_TEXT}]
        r = convert.match_admin(converted, admin)
        self.assertEqual(r["pages_to_visit"], [1, 2, 3])
        by_page = {b["page"]: b["write"] for b in r["batches"]}
        self.assertEqual(by_page[1][0]["list_position"], 4)
        self.assertEqual(by_page[2][0]["list_position"], 11)
        self.assertEqual(by_page[3][0]["list_position"], 20)

    def test_orders_agree_when_they_really_do(self):
        converted = [{"handle": "a", "key": "k", "type": convert.RICH_TEXT},
                     {"handle": "b", "key": "k", "type": convert.RICH_TEXT}]
        r = convert.match_admin(converted, ["a", "b"])
        self.assertTrue(r["orders_agree"])


class MetaobjectTargets(unittest.TestCase):
    """Some copy does not live in the product metafield at all. The metafield
    points at an entry, and the text can be another hop beyond that."""

    # The real AJLD chain: product -> custom.product_tabs -> product_tabs entry
    # -> details -> product_details entry -> content.
    DETAILS = {
        "key": "custom.product_tabs", "type": convert.METAOBJECT,
        "columns": ["Details"],
        "path": [
            {"definition": "product_tabs", "field": "details"},
            {"definition": "product_details", "field": "content",
             "type": convert.RICH_TEXT},
        ],
    }
    QUOTE = {
        "key": "custom.testimonial", "type": convert.METAOBJECT,
        "columns": ["Testimonial"],
        "path": [{"definition": "testimonial", "field": "quote",
                  "type": convert.RICH_TEXT}],
    }
    MAP = {"handle_column": "Handle", "targets": [DETAILS, QUOTE]}

    def test_the_leaf_field_type_decides_the_conversion(self):
        self.assertEqual(convert.target_field_type(self.DETAILS),
                         convert.RICH_TEXT)

    def test_a_plain_target_still_uses_its_own_type(self):
        self.assertEqual(
            convert.target_field_type({"type": convert.LIST_TEXT}),
            convert.LIST_TEXT)

    def test_the_converted_value_carries_the_path_to_the_leaf(self):
        rows = [{"Handle": "bag", "Details": f"Features\n{B} Zip",
                 "Testimonial": "Lovely bag."}]
        converted, _ = convert.convert_rows(rows, self.MAP)
        details = [c for c in converted if c["key"] == "custom.product_tabs"][0]
        self.assertEqual(details["path"][-1]["definition"], "product_details")
        self.assertEqual(details["path"][-1]["field"], "content")
        self.assertEqual(details["html"],
                         "<p>Features</p><ul><li>Zip</li></ul>")

    def test_the_cost_is_counted_in_entry_saves(self):
        rows = [{"Handle": f"bag{i}", "Details": "A.", "Testimonial": "B."}
                for i in range(3)]
        _, report = convert.convert_rows(rows, self.MAP)
        # Two definitions per product, three products.
        self.assertEqual(report["metaobjects"]["entry_saves"], 6)
        self.assertEqual(report["metaobjects"]["by_definition"],
                         {"product_details": 3, "testimonial": 3})

    def test_a_plain_mapping_reports_no_metaobject_cost(self):
        _, report = convert.convert_rows(
            [{"Handle": "a", "Subheading": "x", "Bullet 1": "", "Bullet 2": "",
              "Bullet 3": "", "Details (HTML)": ""}], MAPPING)
        self.assertNotIn("metaobjects", report)


class MappingIsChecked(unittest.TestCase):
    def test_a_metaobject_target_with_no_path_is_refused(self):
        bad = {"targets": [{"key": "custom.testimonial",
                            "type": convert.METAOBJECT, "columns": ["T"]}]}
        problems = convert.check_mapping(bad)
        self.assertTrue(any("no path" in p for p in problems))

    def test_a_path_ending_without_a_type_is_refused(self):
        bad = {"targets": [{"key": "k", "type": convert.METAOBJECT,
                            "columns": ["T"],
                            "path": [{"definition": "d", "field": "f"}]}]}
        self.assertTrue(any("without a `type`" in p
                            for p in convert.check_mapping(bad)))

    def test_a_path_step_missing_its_field_is_refused(self):
        bad = {"targets": [{"key": "k", "type": convert.METAOBJECT,
                            "columns": ["T"],
                            "path": [{"definition": "d"},
                                     {"definition": "e", "field": "f",
                                      "type": convert.RICH_TEXT}]}]}
        self.assertTrue(any("step 1" in p for p in convert.check_mapping(bad)))

    def test_an_unwritable_type_is_refused_by_name(self):
        bad = {"targets": [{"key": "custom.colour", "type": "color",
                            "columns": ["Colour"]}]}
        problems = convert.check_mapping(bad)
        self.assertTrue(any("cannot write" in p for p in problems))

    def test_a_target_naming_no_columns_is_refused(self):
        bad = {"targets": [{"key": "k", "type": convert.RICH_TEXT}]}
        self.assertTrue(any("no columns" in p
                            for p in convert.check_mapping(bad)))

    def test_a_good_mapping_has_no_problems(self):
        self.assertEqual(convert.check_mapping(MetaobjectTargets.MAP), [])
        self.assertEqual(convert.check_mapping(MAPPING), [])


class SingleLineTargets(unittest.TestCase):
    def test_a_one_line_cell_becomes_plain_text_with_no_markup(self):
        out = convert.convert_cell("Best Seller", convert.SINGLE_TEXT)
        self.assertEqual(out["text"], "Best Seller")
        self.assertNotIn("html", out)

    def test_a_multi_line_cell_is_refused_rather_than_flattened(self):
        with self.assertRaises(convert.ConversionError) as ctx:
            convert.convert_cell("One\nTwo", convert.SINGLE_TEXT)
        self.assertIn("cannot hold 2 lines", str(ctx.exception))

    def test_multi_line_text_keeps_its_lines(self):
        out = convert.convert_cell("One\nTwo", convert.MULTI_TEXT)
        self.assertEqual(out["text"], "One\nTwo")

    def test_an_entity_is_decoded_for_a_plain_text_field(self):
        out = convert.convert_cell("Cotton &amp; linen", convert.SINGLE_TEXT)
        self.assertEqual(out["text"], "Cotton & linen")


class SplittingOneColumnIntoTwoFields(unittest.TestCase):
    """One sheet column can hold what the store keeps in two fields. The sheet
    cannot tell you that — only the store's structure can."""

    QUOTE = '"…not to mention the total quality of the workmanship." — Chris'

    TARGET = {
        "key": "custom.testimonial", "type": convert.METAOBJECT,
        "columns": ["Testimonial"],
        "path": [{"definition": "testimonial", "field": "quote",
                  "type": convert.RICH_TEXT}],
        "split": {"rule": "trailing-attribution", "parts": [
            {"field": "quote", "type": convert.RICH_TEXT},
            {"field": "author", "type": convert.SINGLE_TEXT},
        ]},
    }
    MAP = {"handle_column": "Handle", "targets": [TARGET]}

    def test_the_quote_keeps_its_quotation_marks_and_loses_the_name(self):
        quote, author = convert.split_attribution(self.QUOTE)
        self.assertTrue(quote.endswith('workmanship."'))
        self.assertNotIn("Chris", quote)

    def test_the_attribution_keeps_its_leading_space_and_dash(self):
        _, author = convert.split_attribution(self.QUOTE)
        self.assertEqual(author, " — Chris")

    def test_a_dash_inside_the_quotation_is_not_the_split_point(self):
        quote, author = convert.split_attribution(
            "A well-made bag — truly — every time. — Sam")
        self.assertEqual(author, " — Sam")
        self.assertIn("truly", quote)

    def test_no_dash_means_it_is_all_quotation(self):
        quote, author = convert.split_attribution("Just a lovely bag.")
        self.assertEqual(quote, "Just a lovely bag.")
        self.assertEqual(author, "")

    def test_one_cell_becomes_two_records_aimed_at_two_fields(self):
        rows = [{"Handle": "bag", "Testimonial": self.QUOTE}]
        converted, _ = convert.convert_rows(rows, self.MAP)
        self.assertEqual(len(converted), 2)
        by_field = {c["field"]: c for c in converted}
        self.assertEqual(sorted(by_field), ["author", "quote"])
        self.assertEqual(by_field["author"]["text"], "— Chris")
        self.assertIn("workmanship", by_field["quote"]["html"])

    def test_each_record_carries_its_own_destination_field(self):
        rows = [{"Handle": "bag", "Testimonial": self.QUOTE}]
        converted, _ = convert.convert_rows(rows, self.MAP)
        by_field = {c["field"]: c for c in converted}
        self.assertEqual(by_field["quote"]["path"][-1]["field"], "quote")
        self.assertEqual(by_field["author"]["path"][-1]["field"], "author")

    def test_both_fields_of_one_entry_are_still_one_entry_save(self):
        rows = [{"Handle": "bag", "Testimonial": self.QUOTE}]
        _, report = convert.convert_rows(rows, self.MAP)
        self.assertEqual(report["metaobjects"]["entry_saves"], 1)

    def test_a_cell_with_no_attribution_writes_only_the_quote(self):
        rows = [{"Handle": "bag", "Testimonial": "Just a lovely bag."}]
        converted, _ = convert.convert_rows(rows, self.MAP)
        self.assertEqual([c["field"] for c in converted], ["quote"])


class MappingCheckedAgainstTheStore(unittest.TestCase):
    """The real AJLD shape, as Pre-flight found it."""

    STRUCTURE = {
        "product_metafields": {
            "custom.badge": convert.SINGLE_TEXT,
            "custom.subheading": convert.RICH_TEXT,
            "custom.testimonial": convert.METAOBJECT,
        },
        "metaobjects": {
            "testimonial": {"fields": {
                "label": convert.SINGLE_TEXT,
                "quote": convert.RICH_TEXT,
                "author": convert.SINGLE_TEXT}},
        },
    }

    def test_the_real_split_mapping_passes(self):
        mapping = {"targets": [SplittingOneColumnIntoTwoFields.TARGET]}
        self.assertEqual(
            convert.check_mapping(mapping, self.STRUCTURE), [])

    def test_a_metafield_the_store_does_not_have_is_named(self):
        mapping = {"targets": [{"key": "custom.materials",
                                "type": convert.RICH_TEXT,
                                "columns": ["Materials"]}]}
        problems = convert.check_mapping(mapping, self.STRUCTURE)
        self.assertTrue(any("does not exist on the store" in p
                            for p in problems))

    def test_a_type_disagreement_is_named_with_both_types(self):
        mapping = {"targets": [{"key": "custom.badge",
                                "type": convert.RICH_TEXT,
                                "columns": ["Badge"]}]}
        problems = convert.check_mapping(mapping, self.STRUCTURE)
        self.assertTrue(any("is 'single_line_text_field' on the store" in p
                            for p in problems))

    def test_a_missing_metaobject_field_lists_the_ones_that_exist(self):
        mapping = {"targets": [{
            "key": "custom.testimonial", "type": convert.METAOBJECT,
            "columns": ["T"],
            "path": [{"definition": "testimonial", "field": "body",
                      "type": convert.RICH_TEXT}]}]}
        problems = convert.check_mapping(mapping, self.STRUCTURE)
        self.assertTrue(any("has no field 'body'" in p for p in problems))
        self.assertTrue(any("author, label, quote" in p for p in problems))

    def test_a_split_writing_a_field_that_does_not_exist_is_caught(self):
        target = dict(SplittingOneColumnIntoTwoFields.TARGET)
        target["split"] = {"rule": "trailing-attribution", "parts": [
            {"field": "quote", "type": convert.RICH_TEXT},
            {"field": "attribution", "type": convert.SINGLE_TEXT}]}
        problems = convert.check_mapping({"targets": [target]}, self.STRUCTURE)
        self.assertTrue(any("does not have" in p for p in problems))

    def test_an_unknown_metaobject_is_named(self):
        mapping = {"targets": [{
            "key": "custom.testimonial", "type": convert.METAOBJECT,
            "columns": ["T"],
            "path": [{"definition": "reviews", "field": "quote",
                      "type": convert.RICH_TEXT}]}]}
        self.assertTrue(any("metaobject 'reviews' does not exist" in p
                            for p in convert.check_mapping(mapping,
                                                           self.STRUCTURE)))

    def test_an_unknown_split_rule_is_refused(self):
        target = dict(SplittingOneColumnIntoTwoFields.TARGET)
        target["split"] = {"rule": "guess", "parts": [
            {"field": "quote", "type": convert.RICH_TEXT},
            {"field": "author", "type": convert.SINGLE_TEXT}]}
        self.assertTrue(any("unknown split rule" in p
                            for p in convert.check_mapping({"targets": [target]})))


class VerifyFirst(unittest.TestCase):
    """Read what is there, compare it to what the Run intends, change nothing.

    The `sheet is authoritative` policy overwrites the store's editorial
    styling. That is a decision, so it is reported before the write rather
    than discovered after it."""

    CONVERTED = [
        {"handle": "bag", "key": "custom.subheading",
         "html": "<p>A small purse.</p>"},
        {"handle": "bag", "key": "custom.product_tabs", "field": "content",
         "html": "<p>Features</p><ul><li>Top zipper</li></ul>",
         "path": [{"definition": "product_details", "field": "content"}]},
    ]

    def test_an_identical_value_is_already_correct_and_not_rewritten(self):
        current = [{"handle": "bag", "key": "custom.subheading",
                    "value": "<p>A small purse.</p>"}]
        out = convert.diff_run([self.CONVERTED[0]], current)
        self.assertEqual(out["summary"]["already correct"], 1)
        self.assertEqual(out["fields"][0]["status"], "already correct")

    def test_whitespace_alone_is_not_a_difference(self):
        current = [{"handle": "bag", "key": "custom.subheading",
                    "value": "<p>A small   purse.</p>\n"}]
        out = convert.diff_run([self.CONVERTED[0]], current)
        self.assertEqual(out["summary"]["already correct"], 1)

    def test_bold_the_store_has_and_the_sheet_does_not_is_reported(self):
        current = [{"handle": "bag", "key": "custom.product_tabs",
                    "field": "content",
                    "value": "<p><strong>Features</strong></p>"
                             "<ul><li>Top zip</li></ul>"}]
        out = convert.diff_run([self.CONVERTED[1]], current)
        self.assertEqual(out["fields"][0]["status"], "differs")
        self.assertIn("bold", out["fields"][0]["removes"])
        self.assertEqual(out["would_remove"]["bold"], 1)

    def test_links_the_store_has_and_the_sheet_does_not_are_counted(self):
        current = [{"handle": "bag", "key": "custom.subheading",
                    "value": '<p>A <a href="https://x.com">small</a> purse '
                             'from <a href="https://y.com">us</a>.</p>'}]
        out = convert.diff_run([self.CONVERTED[0]], current)
        self.assertIn("link(s)", " ".join(out["fields"][0]["removes"]))
        self.assertEqual(out["would_remove"]["link(s)"], 1)

    def test_styling_the_sheet_also_has_is_not_reported_as_removed(self):
        converted = [{"handle": "bag", "key": "custom.subheading",
                      "html": "<p>A <strong>small</strong> purse.</p>"}]
        current = [{"handle": "bag", "key": "custom.subheading",
                    "value": "<p>A <strong>tiny</strong> purse.</p>"}]
        out = convert.diff_run(converted, current)
        self.assertEqual(out["fields"][0]["status"], "differs")
        self.assertEqual(out["fields"][0]["removes"], [])

    def test_a_field_never_read_is_reported_rather_than_assumed_equal(self):
        out = convert.diff_run(self.CONVERTED, [])
        self.assertEqual(out["summary"]["not read"], 2)
        self.assertEqual(out["summary"]["already correct"], 0)

    def test_the_split_fields_are_compared_separately(self):
        converted = [
            {"handle": "bag", "key": "custom.testimonial", "field": "quote",
             "html": "<p>Lovely.</p>"},
            {"handle": "bag", "key": "custom.testimonial", "field": "author",
             "text": "— Chris"},
        ]
        current = [
            {"handle": "bag", "key": "custom.testimonial", "field": "quote",
             "value": "<p>Lovely.</p>"},
            {"handle": "bag", "key": "custom.testimonial", "field": "author",
             "value": "— Sam"},
        ]
        out = convert.diff_run(converted, current)
        self.assertEqual(out["summary"], {"already correct": 1, "differs": 1,
                                          "not read": 0})

    def test_list_values_compare_element_by_element(self):
        converted = [{"handle": "bag", "key": "custom.benefits",
                      "values": ["One", "Two"]}]
        same = [{"handle": "bag", "key": "custom.benefits",
                 "value": ["One ", "Two"]}]
        self.assertEqual(
            convert.diff_run(converted, same)["summary"]["already correct"], 1)


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
