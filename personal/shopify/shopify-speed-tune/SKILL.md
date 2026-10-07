---
name: shopify-speed-tune
description: Measure a client store's home, collection and product pages on an unpublished copy of its theme, with a program deciding every number. Run it from the store's theme repo with the store URL.
argument-hint: <store-url> [requested-score, default 80]
disable-model-invocation: true
---

# Shopify Speed Tune

Measure a client store's speed on two unpublished copies of its published theme, so customers never see a change and every figure is a real median. Run from the store's theme repo. Arguments: `$ARGUMENTS`: the store's public URL, then optionally a requested Performance score (default 80). Ask for the URL when it is missing.

The terms are the repo glossary's "Making a store faster" section. A **Sample** is one Lighthouse load of one page on one device. A **Measurement** is five Samples of the same page, device and theme, given as a median and a range. The **Working theme** and the **Control theme** are this invocation's two unpublished copies of the published theme.

## The decision program

A small program owns every number, every write to the store and every guard: `scripts/speed_tune.py` in this skill's base directory, `<skill>` below. Run it from the theme repo root:

    python3 <skill>/scripts/speed_tune.py <operation> [flags]

It prints one fact per line, each starting with a fixed tag: `START`, `PAGE`, `SAMPLE`, `MEASUREMENT`, `REPORT`, `FINISH`, `NOTE`, and `REFUSED` or `FAILED` when it stops. Those lines are the verdict: act on what they say, and quote them rather than paraphrase. `--help` after any operation lists its flags.

Each guardrail below protects something the developer relies on:

- **Customers see only what the developer publishes.** The program is the only thing that writes to the store, and it writes only to the two themes it created. Leave every `shopify theme` command to it, push no branch, publish nothing.
- **A refusal is an answer.** On `REFUSED` or `FAILED`, follow the step's instruction for that line, or stop and show the developer the line with its `NOTE`s. The ledger, the lock and the program stay as they are.
- **The preview cookie stays inside the program.** It fetches every preview itself; leave the workspace's `secrets/` folder unopened.
- **The developer's other work keeps running.** Stop a process only by a pid the program names, never by name, and leave the Shopify CLI logged in.

This version runs four steps: Preflight → Baseline → Report → Cleanup. It changes no theme code.

## 1. Preflight

Run `start --store <store-url>`, adding `--score <n>` when the developer gave one. Allow it 10 minutes.

It refuses, changing nothing, unless the store is the one this repo's `shopify.theme.toml` names, no other invocation is unfinished on this Mac, and the theme library has room for two more themes. Then it takes the machine lock, creates the branch `speed-tune/<invocation>`, duplicates the published theme into the Working theme and the Control theme, checks that both preview, downloads Chrome for Testing into a temp workspace and pins Lighthouse 13.5.0.

**Done when** the output ends with `START ready`.

- `REFUSED invocation-unfinished`: another invocation holds the lock. Show the developer the line. Only when they say it was abandoned, run `unlock --invocation <id>` with the id it names, then `start` again.
- `REFUSED no-theme-room`: ask the developer to free two theme slots, or rerun with `--theme-limit 100` if they say the store is on Shopify Plus. Deleting themes is the developer's call.
- Any other `REFUSED`: show it and stop. Nothing was created.
- `FAILED`: run `finish --discard`, which deletes whatever `start` created and releases the lock, then show the developer the failure.

## 2. Baseline

1. Run `pages`. It proposes the collection from the store's main navigation and the product from its best-selling order, and prints three `PAGE` lines. Tell the developer which pages this invocation measures.
2. Take the six baseline Measurements on the Control theme, one call each, in this order:

       sample --page home --device mobile
       sample --page home --device desktop
       sample --page collection --device mobile
       sample --page collection --device desktop
       sample --page product --device mobile
       sample --page product --device desktop

   Each call takes Samples until its Measurement holds five, about a minute per Sample, and ends with a `MEASUREMENT` line: each metric's median with its range in brackets. Allow each call 10 minutes. A call cut off by the timeout, or ending in `FAILED samples-rejected`, resumes when the same command runs again, since recorded Samples stay. When one call fails twice, or stops on any other line, stop measuring and go on to Report, which marks what is missing.

**Done when** `status` prints six `MEASUREMENT … n=5` lines.

## 3. Report

Run `report`. It writes the baseline report to `.agent/shopify-speed-tune/<invocation>/report.md` in the theme repo: each page's median and range on mobile and desktop for Performance score, LCP, TBT, CLS, FCP, Speed Index and accessibility score, plus the Lighthouse and Chrome versions that took every Sample.

**Done when** the `REPORT` line names the file. Show the developer its Baseline table.

## 4. Cleanup

Run `finish`. It deletes the Control theme, keeps the Working theme, puts the repo back on the branch it started from while keeping `speed-tune/<invocation>`, restores Chrome for Testing's preferences, removes the temp workspace with Chrome in it, and releases the lock. Run it after a stop in any step too: whatever exists, it cleans up.

**Done when** the output ends with `FINISH done`. Tell the developer what stays: the Working theme from the `FINISH working-theme kept` line, and the branch.

## Files

Everything the invocation keeps is in `.agent/shopify-speed-tune/<invocation>/` in the theme repo, kept out of git through `.git/info/exclude`: `ledger.json`, the program's record of the invocation; `samples/`, each Sample's Lighthouse report with the cookie and screenshots removed; and `report.md`. Chrome, the pnpm store and the cookie files live in a temp workspace that `finish` deletes. The machine lock is `~/Library/Caches/shopify-speed-tune.lock`.
