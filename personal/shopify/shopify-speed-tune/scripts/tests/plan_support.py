"""Shared set-up for the tests of the plan stop: an invocation whose three pages
carry their five baseline mobile Samples, recorded from the real reports."""

import json

from support import Sandbox, hook, report

PAGES = ("home", "collection", "product")
COLLECTION = "/collections/example-collection"
PRODUCT = "/products/example-product"


def baseline_reports(page):
    return [report("%s-mobile-%d" % (page, i)) for i in range(1, 6)]


def ceiling_reports(page):
    """The page's five real Ceiling Samples, taken with the probe its baseline builds."""
    return [report("%s-ceiling-%d" % (page, i)) for i in range(1, 6)]


def record(box, op, page, reports, *extra):
    args = [op, "--page", page] + (["--device", "mobile"] if op == "sample" else [])
    for path in reports:
        args += ["--report", path]
    result = box.run(*args, *extra)
    box.test.assertEqual(result.code, 0, result)
    return result


def measured(test, *start_args, theme_files=None, pre_commit=None):
    """A started invocation with the three pages set and their baseline mobile
    Measurements complete. `theme_files` ({path: text or bytes}) are committed to
    the client repo before the invocation starts, and `pre_commit` becomes its
    pre-commit hook."""
    box = Sandbox(test)
    if theme_files:
        for path, text in theme_files.items():
            target = box.repo / path
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(text, bytes):
                target.write_bytes(text)
            else:
                target.write_text(text)
        box.git(box.repo, "add", "-A")
        box.git(box.repo, "commit", "-q", "-m", "theme files")
    if pre_commit:
        hook(box.repo, pre_commit)
    box.start(*start_args)
    pages = box.run("pages", "--collection", COLLECTION, "--product", PRODUCT)
    test.assertEqual(pages.code, 0, pages)
    for page in PAGES:
        record(box, "sample", page, baseline_reports(page))
    return box


def diagnosed(test, *start_args, theme_files=None, pre_commit=None):
    """`measured`, plus each page's Ceiling and a `diagnose`: ready for a plan."""
    box = measured(test, *start_args, theme_files=theme_files, pre_commit=pre_commit)
    for page in PAGES:
        record(box, "ceiling", page, ceiling_reports(page))
    result = box.run("diagnose")
    test.assertEqual(result.code, 0, result)
    return box


def write_items(box, items):
    path = box.root / "plan-items.json"
    path.write_text(json.dumps(items))
    return path


# Stand-in Golden theme files: each carries exactly the lines a known-defect rule
# keys on, in the defective form or the fixed form the client stores shipped.

def schema(name, version):
    return json.dumps([{"name": "theme_info", "theme_name": name, "theme_version": version}])


STATIC_CSS = "".join(".btn--%d { padding: 12px 24px; border-radius: 4px; }\n" % i for i in range(60))

DEFECTIVE = {
    "config/settings_schema.json": schema("Golden", "3.0"),
    "snippets/responsive-image.liquid": """{%- liquid
  assign lazy_loading = lazy_loading | default: true
  if lazy_loading
    assign initial_src = image | image_url: width: 20
  endif
-%}
{%- capture srcset -%}
  {%- for size in image_sizes -%}
    {{- image | image_url: width: size }} {{ size }}w
    {%- unless forloop.last %}, {% endunless -%}
  {%- endfor -%}
{%- endcapture -%}
{%- liquid
  assign srcset_clean = srcset | strip | split: ',' | join: ', '
  assign srcset_clean_length = srcset_clean | size | minus: 1
  assign srcset_final = srcset_clean | slice: 0, srcset_clean_length
-%}
<img class="responsive-image lazyload" src="{{ initial_src }}" data-src="{{ image | image_url: width: 1200 }}" data-srcset="{{ srcset_final }}" loading="lazy">
""",
    "blocks/media.liquid": "{% render 'responsive-image', image: block.settings.image %}\n",
    "snippets/button.liquid": "{%- style -%}\n" + STATIC_CSS + "{%- endstyle -%}\n<a class=\"btn\">{{ label }}</a>\n",
}

FIXED = {
    "config/settings_schema.json": schema("Golden", "3.0"),
    "snippets/responsive-image.liquid": """{%- liquid
  assign lazy_loading = lazy_loading | default: true, allow_false: true
  if lazy_loading
    assign initial_src = image | image_url: width: 20
  endif
-%}
{%- capture srcset -%}
  {%- for size in image_sizes -%}
    {{- image | image_url: width: size }} {{ size }}w
    {%- unless forloop.last %}, {% endunless -%}
  {%- endfor -%}
{%- endcapture -%}
{%- assign srcset_final = srcset | strip -%}
{%- comment -%}
  The old copy, kept for reference:
  {%- comment -%} it sliced the srcset {%- endcomment -%}
  assign lazy_loading = lazy_loading | default: true
  assign srcset_final = srcset_clean | slice: 0, srcset_clean_length
{%- endcomment -%}
<img class="responsive-image" src="{{ image | image_url: width: 800 }}" srcset="{{ srcset_final }}" loading="eager">
""",
    "blocks/media.liquid": ("{% render 'responsive-image', image: block.settings.image, "
                            "lazy_loading: image_lazy, fetchpriority: image_priority %}\n"),
    "snippets/button.liquid": ("{% stylesheet %}\n" + STATIC_CSS + "{% endstylesheet %}\n"
                               "<a class=\"btn\">{{ label }}</a>\n"),
}
