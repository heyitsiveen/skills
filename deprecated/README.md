# Deprecated snapshots

Byte-identical copies of skills as they stood **before** a rewrite, kept so the
previous behaviour can be restored if the replacement misbehaves.

This is not a bucket. Nothing here is published: it is listed in none of the
three registries (`README.md`, `skills.sh.json`,
`.claude-plugin/marketplace.json`), no `heyitsiveen-skills-*` plugin covers it,
and `scripts/check.sh` skips it.

## Contents

| Snapshot | Superseded by | Taken at |
| --- | --- | --- |
| `shopify/figma-shopify-builder` | `personal/shopify/figma-shopify-builder` | `df052eb` (merge-base with `main`, last commit before the design-spec convention) |
| `shopify/figma-shopify-composer` | `personal/shopify/figma-shopify-composer` | `df052eb` |
| `shopify/shopify-app-restyle` | `personal/shopify/shopify-app-restyle` | `df052eb` |

All three were replaced by the design-spec convention — see
`docs/adr/0001-design-spec-replaces-pixel-diff.md`.

## Rolling one back

Copy the snapshot over its live counterpart, then re-run the checks:

```sh
rm -rf personal/shopify/<skill> && cp -R deprecated/shopify/<skill> personal/shopify/<skill>
./scripts/check.sh
```

`check.sh` will then fail on the retired-vocabulary and Phase 4 assertions —
that is expected for a rollback, and those assertions describe the convention
the snapshot predates.
