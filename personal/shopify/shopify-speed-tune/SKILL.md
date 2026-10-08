---
name: shopify-speed-tune
description: Measure a client store's home, collection and product pages on unpublished copies of its theme, find what theme work can reach on each, stop once for the developer to approve a plan, then test each planned change against an unchanged copy and keep only clear wins, with a program deciding every number. Run it from the store's theme repo with the store URL.
argument-hint: <store-url> [requested-score, default 80]
disable-model-invocation: true
---

# Shopify Speed Tune

Measure a client store's speed on two unpublished copies of its published theme, so customers never see a change and every figure is a real median, plan the theme changes worth making, then make them one at a time and keep the ones that win. Run from the store's theme repo. Arguments: `$ARGUMENTS`: the store's public URL, then optionally a requested Performance score (default 80). Ask for the URL when it is missing.

The terms are the repo glossary's "Making a store faster" section. A **Sample** is one Lighthouse load of one page on one device. A **Measurement** is five Samples of the same page, device and theme, given as a median and a range. The **Working theme** and the **Control theme** are this invocation's two unpublished copies of the published theme. A page's **Ceiling** is its mobile score with the theme's optional requests blocked: the most theme work can reach while apps and tags stay. Its **target** is the lower of the requested score and that Ceiling. A **Round** applies one plan item to the Working theme, measures it against the Control theme in pairs, then keeps or removes it.

## The decision program

A small program owns every number, every write to the store and every guard: `scripts/speed_tune.py` in this skill's base directory, `<skill>` below. Run it from the theme repo root:

    python3 <skill>/scripts/speed_tune.py <operation> [flags]

It prints one fact per line, each starting with a fixed tag: `START`, `PAGE`, `SAMPLE`, `MEASUREMENT`, `CEILING`, `SMOKE`, `FINDING`, `DEFECT`, `COST`, `PLAN`, `PSI`, `ROUND`, `CHANGE`, `PUSH`, `PAIR`, `PAIRS`, `VERDICT`, `TARGET`, `NEXT`, `STOP`, `WARN`, `REPORT`, `FINISH`, `NOTE`, and `REFUSED` or `FAILED` when it stops. Those lines are the verdict: act on what they say, and quote them rather than paraphrase. `--help` after any operation lists its flags.

Each guardrail below protects something the developer relies on:

- **Customers see only what the developer publishes.** The program is the only thing that writes to the store, and it writes only to the two themes it created. Leave every `shopify theme` command to it, push no branch, publish nothing.
- **The program keeps the history.** You edit theme files; the program pushes them, commits each kept Round once and puts back each removed one. Leave committing, stashing and switching branches to it, so the branch holds exactly the kept Rounds.
- **One stop.** Step 3's plan is the only place the skill waits for the developer. Everything they decide (the pages, the plan, their PageSpeed scores) goes into that one message; every other step runs on.
- **A refusal is an answer.** On `REFUSED` or `FAILED`, follow the step's instruction for that line, or stop and show the developer the line with its `NOTE`s. The ledger, the lock and the program stay as they are.
- **The preview cookie stays inside the program.** It fetches each theme's cookie itself and gives it only to its own test Chrome, for the store's host alone. An unpublished theme's page loads from its own URL plus `?pb=0`, which keeps Shopify's preview bar out without the redirect `preview_theme_id` would add to every load.
- **The developer's other work keeps running.** Leave stopping processes to the program, which stops only the Chrome and the `caffeinate` it started, and leave the Shopify CLI logged in.

It runs six steps: Preflight → Baseline → Plan → Rounds → Report → Cleanup.

## 1. Preflight

Run `start --store <store-url>`, adding `--score <n>` when the developer gave one. Allow it 10 minutes.

It refuses, changing nothing, unless the store is the one this repo's `shopify.theme.toml` names, no other invocation is unfinished on this Mac, the theme library has room for two more themes, and the repo's pre-commit hook passes on the unchanged repo, run the way `git commit` runs it: every kept Round is committed through that hook. Then it takes the machine lock, keeps the Mac from idle sleep until `finish` (a `caffeinate -i` it stops by pid), creates the branch `speed-tune/<invocation>`, duplicates the published theme into the Working theme and the Control theme, checks that both preview, downloads Chrome for Testing into a temp workspace, pins Lighthouse 13.5.0 and installs puppeteer-core beside them.

**Done when** the output ends with `START ready`. Its `START hook=` line says how keep commits run: `passed`, through the hook; `absent`, with no hook; `bypass-approved`, with `--no-verify`.

- `REFUSED invocation-unfinished`: another invocation holds the lock. Show the developer the line. Only when they say it was abandoned, run `unlock --invocation <id>` with the id it names, then `start` again.
- `REFUSED no-theme-room`: ask the developer to free two theme slots, or rerun with `--theme-limit 100` if they say the store is on Shopify Plus. Deleting themes is the developer's call.
- `REFUSED pre-commit-fails`: the hook already fails before any change, so it would refuse every keep. Show the developer the line, which names the hook, its exit code and the end of its output, and ask whether they will fix what it reports (commit the fix, then `start` again) or approve committing this invocation's kept Rounds with `--no-verify`. Pass `--no-verify-approved` only when the developer has explicitly approved that in this conversation for this invocation, never on your own judgment.
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

Allow each call 10 minutes. A call cut off by the timeout, or ending in `FAILED samples-rejected`, resumes when the same command runs again, since recorded Samples stay. When one call fails twice, or stops on any other line, stop measuring and go to step 5, Report, which marks what is missing: the plan needs every page's baseline and Ceiling.

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
   - Every item changes theme code only, and treats every visitor alike. Apps, app embeds and tags stay as the merchant set them, and `config/settings_data.json` stays untouched. A Round refuses a change to that file or one that detects Lighthouse, the device or the platform, and its smoke check catches a lost app block.

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

## 4. Rounds

After approval the Rounds run without the developer until a `STOP` line. Each Round puts one plan item on the Working theme while the Control theme holds every change kept so far, smoke-checks the two, measures them in pairs, and lets the program keep or remove the change. Work Round after Round:

1. **Open.** Run `round`. **Done when** it prints `ROUND <n> opened item=<id>` with that item's `PLAN item` line. When the Rounds are over it prints a `TARGET` line per page and a `STOP` line instead: go to step 5, Report. On `REFUSED`, stop and show the developer.
2. **Apply.** Make the change the `PLAN item` line describes, in the theme files, and nothing beyond it. It stays uncommitted until its verdict. Write it so the theme treats every visitor alike:
   - theme files only, with `config/settings_data.json` left as the merchant set it
   - apps, app embeds, app blocks and tags left as they are
   - no code that reads the user agent, `navigator.platform` or `navigator.webdriver`, and no theme file that names Lighthouse, PageSpeed or a test device, comments included: `push` refuses the change. Vendored libraries get no exception: a change that adds, updates or moves one that reads the user agent, such as a slider bundle, is refused like the theme's own code, so leave it as it is, or delete it when the item removes it
   - files the repo's `.shopifyignore` matches left alone: the CLI skips them without a word, so `push` refuses them
   - template JSON only when the item needs it; the program flags each template JSON change for the report

   With `START hook=passed`, run the formatter and checks the hook runs on the files you changed: the keep commit runs that hook, and a change it refuses is removed. With `bypass-approved`, the keep commit skips the hook; run its formatter on the files you changed. **Done when** the change is in the tree, and with `hook=passed` those checks pass.
3. **Push.** Run `push`. **Done when** it prints `PUSH working theme=<id> paths=<n> ok`; its `CHANGE` lines list the change, `template-json` marking each template JSON file.
   - `REFUSED settings-file`, `detection`, `outside-theme`, `odd-path` or `shopifyignore`: take that part out of the change and push again. When the item cannot be made without it, run `verdict --remove`.
   - `FAILED push-errors`: the store refused the change, so the Round failed; its `NOTE`s name each file's error. Go to **Decide**.
   - `FAILED push-failed`: run `push` once more; when it fails again, stop and show the developer.
   - Any other `REFUSED`: stop and show the developer. Nothing was written.
4. **Check.** Run `smoke`, allowing it 10 minutes. It comes before the pairs: it warms the store's cache with the changed files, and it catches a broken change before 15 minutes of pairs. **Done when** it prints `SMOKE round-<n> result`. On `result fail`, go to **Decide**, which removes the Round without pairs. When it ends in `FAILED` twice, run `verdict --remove`.
5. **Measure.** Run `pairs`, allowing it 10 minutes, until it prints `PAIRS <n> complete`. It takes five pairs on each page, each a Control theme Sample then a Working theme Sample, with a `PAIR` line per pair; a call stops between pairs after about six minutes and the next carries on. When two calls in a row end in `FAILED samples-rejected`, run `verdict --remove`.
6. **Decide.** Run `verdict`. It prints each page's `PAIRS` line and the `SMOKE` result, then `VERDICT <n> keep item=<id> won=<pages>` or `VERDICT <n> remove item=<id> reasons=<reasons>`, and carries it out: a kept change becomes one commit and is pushed to the Control theme; a removed one leaves the working tree and the Working theme at the last commit. A Round whose smoke check failed is removed with no `PAIRS` lines, on `smoke-regression` or `new-error`. It ends with a `TARGET` line per page, then `NEXT item=<id>`, or `STOP targets-reached` or `STOP plan-exhausted`. On `FAILED`, run `verdict` again, which carries on where it stopped; when it fails twice, stop and show the developer.

After a `NEXT` line, open the next Round.

**Done when** a `STOP` line names why the Rounds ended: `targets-reached`, every page's kept median at or above its target, or `plan-exhausted`, no unused plan item left.

## 5. Report

1. When the Rounds ended on a `STOP` line, measure desktop once more on the Working theme, which now holds every kept Round, one call each: `final --page home`, then `collection`, then `product`. Allow each call 10 minutes. Each ends with a `MEASUREMENT final … n=5` line; a call cut off, or ending in `FAILED samples-rejected`, resumes when the same command runs again. When the invocation stopped before its Rounds, the Working theme still matches the baseline: go straight to `report`.
2. Run `report`. It writes `.agent/shopify-speed-tune/<invocation>/report.md` from the ledger: a part for the team, then the detail log behind it. It prints a `REPORT page` line per page, a `REPORT setup` line naming how this store goes live (`github-connected`, `cli-managed` or `not-recognised`), and `REPORT file <path>` last.
   - `REFUSED round-open`: end the Round with `verdict`, or `verdict --remove`, then run `report` again.
   - A `NOTE` naming a final desktop Measurement still short: take it with the `final` command the note gives, then run `report` again.
3. For each `REPORT missed <page> unexplained` line, write that page's reason and proposed next plan to `.agent/shopify-speed-tune/<invocation>/missed.json`, as [references/missed-targets.md](references/missed-targets.md) describes, and run `report --missed <file>`.

**Done when** `report` ends with `REPORT file <path>` and prints no `REPORT missed … unexplained` line. Show the developer the report's Outcome, What changed, Performance by page, and Going live and going back sections, with every `WARN` line `report` printed, and give them the file's path: its part for the team is theirs to send.

## 6. Cleanup

Run `finish`, after the report or after a stop in any step: whatever the invocation created, it cleans up. It deletes the Control theme, keeps the Working theme, puts the repo back on the branch it started from while keeping `speed-tune/<invocation>`, restores Chrome for Testing's preferences, stops any Chrome a cut-off call left running, removes the temp workspace (Chrome, the smoke checker's puppeteer-core, the pnpm store), stops the `caffeinate` it held, marks the invocation finished and releases the lock. Then it reads back what it leaves, with a `FINISH verified` line each for the theme library, the repo and the machine. It switches branches only when that loses nothing: uncommitted changes, or a switch git refuses, leave the repo on `speed-tune/<invocation>`, and a `NOTE` says why. While a Round is open it refuses, so the Working theme it keeps holds kept Rounds only: end the Round with `verdict`, or `verdict --remove`, first.

- `FAILED cleanup-incomplete`: its `NOTE`s name what is left, and the invocation stays open. A process still running from the workspace is one the program did not start as its Chrome, so it leaves it running: show the developer its pid and command, and run `finish` again once they have stopped it. Anything else: run `finish` again; when it stops there twice, show the developer the line.

**Done when** the output ends with `FINISH done`. Tell the developer what stays: the Working theme from the `FINISH working-theme kept` line, the branch with one commit per kept Round, and the report.

## Files

Everything the invocation keeps is in `.agent/shopify-speed-tune/<invocation>/` in the theme repo, kept out of git through `.git/info/exclude`: `ledger.json`, the program's record of the invocation; `samples/`, each Sample's Lighthouse report without its screenshots; `plan-items.json` and `missed.json`, your drafts; `plan.md`, the plan as the developer approved it; and `report.md`, the part for the team and the detail log. Each kept Round is one commit on the branch `speed-tune/<invocation>`. Chrome, puppeteer-core and the pnpm store live in a temp workspace that `finish` deletes. The machine lock is `~/Library/Caches/shopify-speed-tune.lock`.
