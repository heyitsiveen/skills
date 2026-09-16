# Verification reads the rendered storefront, not the Storefront API

A Run must prove its writes landed. The admin cannot show it: a metafield renders as a collapsed button whose preview truncates and flattens a list to one line, so reading 304 values there means opening 304 editors. Of the browser toolset, only injected JavaScript returns exact text — the page-text tool silently returned an unrelated article and missed every metafield, the accessibility tree truncates each node at 100 characters, and the element finder paraphrases rather than quotes.

A far cheaper route exists and was measured working. Every Shopify storefront publishes its own Storefront API token in the page source, for every visitor. A read-only GraphQL query returns the raw stored value byte-exact for all four fields and batches: one call covered 50 products and 200 values. The whole catalogue is about two calls, against 76 page loads — and because it reads the product record rather than a template, it is immune to which theme is published and to CDN staleness after a write.

It is nonetheless the Shopify Storefront API, and the brief excludes Shopify APIs. The constraint was stated five times, before and after this option was put to the developer with its cost advantage made explicit. It is a real constraint about what the skill is allowed to be, not an approximation of one, and a skill that honours a rule except where the rule is expensive does not honour it.

So verification loads each product page and reads the rendered text. This is sufficient for the question actually being asked — did the text land — because the theme adds no truncation, no ellipsis and no entity mangling, and the rendered text matches the stored text exactly.

## Consequences

Verification costs 76 page loads per Run. It happens once, at the end, and it is the last phase rather than a per-product step.

The rendered page proves text, not structure. Rebuilding a `rich_text_field` document from HTML has to infer bold and italic text nodes, link attributes and heading levels, and empty paragraphs vanish, so the rendered page is a check and never a source of truth for the Backup. On the first target catalogue no stored value uses bold, italic or links, so the gap is currently empty — on a client store whose values use them, a Browser mode Backup has to come from the editor, not the page.

A storefront check catches one class of failure an API read would hide: data written correctly that the theme never renders, because the template pulls something else. The preceding run hit exactly this — three of four fields rendered and the fourth did not. So the cheaper path was also the blinder one, and this consequence is a genuine gain rather than a consolation.

Reading a page requires injected JavaScript to return only a verdict, never the values. The tool caps its return at about 1000 characters and silently blocks payloads shaped like `key=value` or base64, so the comparison runs in the page and returns mismatching rows.
