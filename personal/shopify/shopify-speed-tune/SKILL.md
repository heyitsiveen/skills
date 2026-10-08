---
name: shopify-speed-tune
description: Measure a client store's home, collection and product pages on unpublished copies of its theme, find what theme work can reach on each, and stop once for the developer to approve a plan, with a program deciding every number. Run it from the store's theme repo with the store URL.
argument-hint: <store-url> [requested-score, default 80]
disable-model-invocation: true
---

# Shopify Speed Tune

Measure a client store's speed on two unpublished copies of its published theme, so customers never see a change and every figure is a real median, then plan the theme changes worth making. Run from the store's theme repo. Arguments: `$ARGUMENTS`: the store's public URL, then optionally a requested Performance score (default 80). Ask for the URL when it is missing.

The terms are the repo glossary's "Making a store faster" section. A **Sample** is one Lighthouse load of one page on one device. A **Measurement** is five Samples of the same page, device and theme, given as a median and a range. The **Working theme** and the **Control theme** are this invocation's two unpublished copies of the published theme. A page's **Ceiling** is its mobile score with the theme's optional requests blocked: the most theme work can reach while apps and tags stay. Its **target** is the lower of the requested score and that Ceiling.

## The decision program

A small program owns every number, every write to the store and every guard: `scripts/speed_tune.py` in this skill's base directory, `<skill>` below. Run it from the theme repo root:

    python3 <skill>/scripts/speed_tune.py <operation> [flags]

It prints one fact per line, each starting with a fixed tag: `START`, `PAGE`, `SAMPLE`, `MEASUREMENT`, `CEILING`, `SMOKE`, `FINDING`, `DEFECT`, `COST`, `PLAN`, `PSI`, `WARN`, `REPORT`, `FINISH`, `NOTE`, and `REFUSED` or `FAILED` when it stops. Those lines are the verdict: act on what they say, and quote them rather than paraphrase. `--help` after any operation lists its flags.

Each guardrail below protects something the developer relies on:

- **Customers see only what the developer publishes.** The program is the only thing that writes to the store, and it writes only to the two themes it created. Leave every `shopify theme` command to it, push no branch, publish nothing.
- **One stop.** Step 3's plan is the only place the skill waits for the developer. Everything they decide (the pages, the plan, their PageSpeed scores) goes into that one message; every other step runs on.
- **A refusal is an answer.** On `REFUSED` or `FAILED`, follow the step's instruction for that line, or stop and show the developer the line with its `NOTE`s. The ledger, the lock and the program stay as they are.
- **The preview cookie stays inside the program.** It fetches each theme's cookie itself and gives it only to its own test Chrome, for the store's host alone. An unpublished theme's page loads from its own URL plus `?pb=0`, which keeps Shopify's preview bar out without the redirect `preview_theme_id` would add to every load.
- **The developer's other work keeps running.** Leave stopping processes to the program, which kills only the Chrome it started, and leave the Shopify CLI logged in.

This version runs five steps: Preflight → Baseline → Plan → Report → Cleanup. It changes no theme code: the approved plan is recorded for the Rounds a later version runs.

## 1. Preflight

Run `start --store <store-url>`, adding `--score <n>` when the developer gave one. Allow it 10 minutes.

It refuses, changing nothing, unless the store is the one this repo's `shopify.theme.toml` names, no other invocation is unfinished on this Mac, and the theme library has room for two more themes. Then it takes the machine lock, creates the branch `speed-tune/<invocation>`, duplicates the published theme into the Working theme and the Control theme, checks that both preview, downloads Chrome for Testing into a temp workspace, pins Lighthouse 13.5.0 and installs puppeteer-core beside them.

**Done when** the output ends with `START ready`.

- `REFUSED invocation-unfinished`: another invocation holds the lock. Show the developer the line. Only when they say it was abandoned, run `unlock --invocation <id>` with the id it names, then `start` again.
- `REFUSED no-theme-room`: ask the developer to free two theme slots, or rerun with `--theme-limit 100` if they say the store is on Shopify Plus. Deleting themes is the developer's call.
- Any other `REFUSED`: show it and stop. Nothing was created.
- `FAILED`: run `finish --discard`, which deletes whatever `start` created and releases the lock, then show the developer the failure.

## 2. Baseline

1. Run `pages`. It proposes the collection from the store's main navigation and the product from its best-selling order, and prints three `PAGE` lines. The developer confirms them at the plan stop.
2. Take the six baseline Measurements on the Control theme, one call each, in this order:

       sample --page home --device mobile
       sample --page home --device desktop
       sample --page collection --device mobile
       sample --page collection --device desktop
       sample --page product --device mobile
       sample --page product --device desktop

   Each call takes Samples until its Measurement holds five, about a minute per Sample, and ends with a `MEASUREMENT` line: each metric's median with its range in brackets.
3. Measure each page's Ceiling, one call each: `ceiling --page home`, then `collection`, then `product`. Each call builds the page's probe from its five baseline mobile Samples and prints it: a `CEILING <page> block <pattern>` line per pattern (theme scripts, theme fonts, and each theme image) and a `CEILING <page> protect` line for the LCP image, which no pattern touches. It then takes five mobile Samples with those patterns blocked and ends with `CEILING <page> ceiling=<n> requested=<n> target=<n>`. A `NOTE` saying the largest paint moved, or that the Ceiling is not above the baseline, belongs in the plan you show the developer.

Allow each call 10 minutes. A call cut off by the timeout, or ending in `FAILED samples-rejected`, resumes when the same command runs again, since recorded Samples stay. When one call fails twice, or stops on any other line, stop measuring and go to step 4, Report, which marks what is missing: the plan needs every page's baseline and Ceiling.

4. Run `smoke`, allowing it 10 minutes. The smoke checker loads each page on both themes as a phone and does what a shopper does: opens and closes the header menu by keyboard, changes the product's variant, adds it to the cart and watches the cart count rise. It also lists the app blocks, console errors and Liquid errors. The program holds the Working theme to whatever already works on the Control theme and ends with a `SMOKE baseline result` line. Both themes are still copies of the published theme, so `pass` is expected; a `fail` means the check is unsteady on this store, and its `SMOKE` lines belong in the plan you show the developer. On `FAILED`, run `smoke` once more; when it fails again, put that line in the plan instead and go on.

**Done when** `status` prints six `MEASUREMENT baseline … n=5` lines, three `CEILING … target=` lines and a `SMOKE baseline result` line.

## 3. Plan

1. Run `diagnose`. It reads the baseline Samples already taken and prints, per page, `FINDING` lines (the LCP element and its breakdown, the render-blocking requests, the layout shifts, the long tasks, each request named by its owner), then a `DEFECT` line per known Golden theme defect, then the `COST` table of every app and tag.
2. Trace each finding the theme owns to its cause in the theme code: the LCP element's section and snippet, the theme's render-blocking stylesheets, the theme scripts and the page's own HTML in the long tasks, the elements that shift. Read the repo's `AGENTS.md` and `.agent/THEME-CAPABILITIES.md` when present. When any `DEFECT … found` line prints, plan from [references/known-defects.md](references/known-defects.md). Check every item against [references/regressions.md](references/regressions.md).
3. Write the plan items as a JSON list to `.agent/shopify-speed-tune/<invocation>/plan-items.json`. Each item is one change a Round can test alone:

       {"change": "…", "pages": ["home", "collection"], "cause": "…", "effect": "…", "defects": ["D2"]}

   - `cause` names the finding or defect the change answers; `effect` is the expected gain, with "unmeasured" when no evidence backs it.
   - `defects` lists the known defects an item fixes, following each entry's proven fix. The program puts those items first.
   - Order the rest by expected effect, largest first.
   - Every item changes theme code only. Apps, app embeds and tags stay as the merchant set them, `config/settings_data.json` stays untouched, and nothing may detect Lighthouse, the device or the platform: the Rounds refuse all three.

   Run `plan --items <file>`. It refuses an item missing its change, pages, cause or effect, or one naming a defect `diagnose` did not find; fix the file and run it again. A `NOTE` naming a found defect no item fixes needs an item, or your reason in the message to the developer.
4. Stop. Show the developer the Pages, Apps and tags, and Plan sections of `plan.md` (the `PLAN file` line names it) and every Ceiling `NOTE`, then ask in this one message for:
   - their approval, or the changes they want, a different collection or product page included
   - their PageSpeed mobile score for each of the three pages, as they would screenshot it for the team
5. Apply the answer, then show the result again when anything changed: it is still the same stop.
   - A changed page: `pages --collection <path>` or `--product <path>`, then that page's two baseline Measurements and its Ceiling, `diagnose`, and `plan --items` again.
   - Changed items: edit the file and run `plan --items` again.
   - The scores: `psi --home <n> --collection <n> --product <n>`. Relay every `WARN psi-gap` line: the PageSpeed screenshot taken after going live may not match this skill's report.
6. When the developer approves, run `plan --approve`.

**Done when** the output ends with `PLAN approved items=<n> at <time>` and the developer's three PageSpeed scores are recorded.

## 4. Report

Run `report`. It writes the baseline report to `.agent/shopify-speed-tune/<invocation>/report.md` in the theme repo: each page's median and range on mobile and desktop for Performance score, LCP, TBT, CLS, FCP, Speed Index and accessibility score, plus the Lighthouse and Chrome versions that took every Sample.

**Done when** the `REPORT` line names the file. Show the developer its Baseline table.

## 5. Cleanup

Run `finish`. It deletes the Control theme, keeps the Working theme, puts the repo back on the branch it started from while keeping `speed-tune/<invocation>`, restores Chrome for Testing's preferences, removes the temp workspace with Chrome and puppeteer-core in it, and releases the lock. Run it after a stop in any step too: whatever exists, it cleans up.

**Done when** the output ends with `FINISH done`. Tell the developer what stays: the Working theme from the `FINISH working-theme kept` line, and the branch.

## Files

Everything the invocation keeps is in `.agent/shopify-speed-tune/<invocation>/` in the theme repo, kept out of git through `.git/info/exclude`: `ledger.json`, the program's record of the invocation; `samples/`, each Sample's Lighthouse report without its screenshots; `plan-items.json`, your draft; `plan.md`, the plan as the developer approved it; and `report.md`. Chrome, puppeteer-core and the pnpm store live in a temp workspace that `finish` deletes. The machine lock is `~/Library/Caches/shopify-speed-tune.lock`.
