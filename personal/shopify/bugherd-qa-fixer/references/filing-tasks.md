# Filing a BugHerd task an AI can actually fix

For whoever does QA. Written against a real client board of 90 tasks — every rule below exists because that board broke on it.

A fixer — human or AI — can only work from what the task carries. It cannot see your screen, cannot ask you a question without stopping the whole batch, and will not guess. **A task that can't be reproduced never gets fixed; it gets sent back as a question.** On the board this guide is written from, roughly two thirds of tasks would come back with a question before any work started.

---

## The 60-second checklist

Before you hit Add, the task must answer all six:

1. **Where** — pinned on the element, on the page where it happens.
2. **What's wrong** — what you see now.
3. **What's right** — what it should be instead. A value, a Figma frame, or a sentence.
4. **Which build** — live site, or the draft/preview theme (paste the link you used).
5. **What state** — logged in? which country/currency? which variant? mobile or desktop?
6. **One thing** — one defect per task.

If you can't pin it, use the template at the bottom.

---

## The rules, and why

### 1. Pin it. Always.

The pin is what gives the task its URL, viewport size, browser, screenshot, and the element you meant. Without it the task carries **nothing** — literally `url: null`.

> On the reference board, **23 of 90 tasks had no pin data at all.** Every one of them needs a round-trip before work can start. One of them already has the reply *"Where's the screenshot for this? Where exactly are you seeing the issue?"* sitting on it.

Can't pin it — the element only appears on hover, it's inside a modal, it's a whole-page problem? Pin the nearest stable thing and say so in words, or use the template below.

### 2. One defect per task.

Bundling costs you tracking. If a task says three things and two get fixed, the task can't be marked done and you can't tell which one is outstanding.

> Real example: *"this curved line has the wrong width. its too thin-- brands are not centered and get cutoff"* — that's three defects (line width, centering, cutoff) in one task. File three.

### 3. Say what "correct" looks like, not just that it's wrong.

This is the single biggest time sink. "Wrong" is not actionable; "wrong, should be X" is.

| ❌ as filed | ✅ what it needed |
|---|---|
| `fix length` | `This heading wraps to 3 lines — should be 2 max at this width.` |
| `should be 1 line` | `Subtitle wraps to 2 lines at 1920 wide. Should stay on 1 line.` |
| `this is too big` | `Icon renders ~64px, Figma has it at 40px.` |
| `wrong color also` | `Button background is light blue, Figma says #1B2A4A.` |
| `should be more on the left side` | `Text block sits centered; Figma has it left-aligned to the container edge.` |
| `pls check padding above` | `Gap above this section is ~120px, Figma has 64px.` |
| `these should be links` | `The three logos here aren't clickable. Each should link to its publisher.` |

You don't need a pixel value. "Should match Figma" is fine — **if** you link the frame (next rule).

### 4. "Doesn't match the design" → link the Figma frame, with the node-id.

This is the most common report type and the one that stalls most often. *"this isnt part of the design"*, *"not the design"*, *"diff products in figma"* — none of these can be actioned without seeing the design.

- Paste the **frame link with `?node-id=…`** in it — right-click the frame in Figma → Copy link to selection.
- A bare file link is not enough; it can't be resolved to the specific frame.
- Say which breakpoint the frame is (desktop / mobile).

### 5. Describe the element in words too.

The pin stores a CSS path that is specific to the exact theme you were looking at — it does **not** carry over to the draft theme where the fix gets made and checked.

> Median path length on the reference board: **390 characters**. Longest: **1016**. And **8 of 67 pins** landed *outside* the element they recorded.

So add three or four words: *"the 'As Seen On' logo strip"*, *"the price under the Add to Cart button"*. That survives everything.

### 6. Say which theme you were on.

**A URL does not record the theme.** `https://your-store.com/products/x` looks identical whether you're on the live theme or a preview. Two people can file byte-identical URLs about entirely different code.

- On the **live site** — say "live".
- On a **preview/draft link** — paste the link you clicked.
- Preview links expire: the shareable visitor preview dies after **2 days**, merchant previews after **30**. If you're reporting from a link you opened yesterday, it may already have dropped you back onto live without saying anything.

*(Developer note: this whole rule can be deleted permanently — see the last section.)*

### 7. State anything that isn't the default.

The fixer loads the page cold, logged out, in the default country, with an empty cart. If your bug needs more than that, it will not reproduce.

Say so if any of these applied: logged in · items in cart · a specific variant or swatch selected · a specific country/currency/language · a dropdown, modal, or accordion open · you scrolled or hovered first.

> Real example: *"tried a different location. prices still show as $"* on `/en-gb`. Good instinct — but it needs the country you switched **to** and what currency you expected.

### 8. Mobile bugs must be filed from mobile.

Pin from a real phone or a resized window. The task records your window width and that's the width the fix is checked at.

> The reference board has **zero** mobile reports across 90 tasks — 1920 or 1800 wide, every one. If mobile isn't being QA'd, mobile isn't being fixed.

### 9. Report the symptom, not the fix.

*"Make the padding 20px"* tells the fixer what you want typed, not what's broken. Often the real cause is somewhere else entirely and the requested change papers over it or breaks another page. Say what looks wrong and what it should look like; let the fix be diagnosed.

If you're confident about the cause, add it as a second line: *"(might be the same issue as #38?)"* — as a hint, not as the instruction.

### 10. Set a severity, and give it a short title.

> **90 of 90** tasks on the reference board had severity unset. That means the batch can't be ordered by importance and everything is treated the same.

Rough is fine: **critical** = blocks buying · **important** = visibly wrong on a key page · **normal** = default · **minor** = cosmetic, low traffic.

Titles were also empty on all 90. One short line — *"As Seen On logos not clickable"* — makes the board scannable.

### 11. Video for anything that moves.

Intermittent, animation, hover, scroll, carousel, or "it only happens sometimes" → record it. A still frame of a moving problem is not evidence.

---

## Template — when you can't pin

Paste this into the task description and fill it in:

```
Page:        <full URL, including any ?query>
Theme:       live  |  draft/preview (paste link)
Viewport:    <window width in px>  ·  desktop / mobile
State:       logged out / logged in · country · variant · anything opened first

What I see:      <the symptom>
What I expected: <the correct behaviour, or a Figma frame link with node-id>
Element:         <a few words naming it>
Steps:           1. … 2. … 3. …
```

---

## What comes back as a question

Expect a round-trip — not a fix — if the task:

- has no pin **and** no URL;
- says something is wrong without saying what right looks like;
- says "doesn't match the design" with no Figma frame link;
- bundles two or more separate problems;
- describes a state (logged in, a market, a selected variant) without naming it;
- is a mobile report filed from a desktop window;
- points at a third-party app's widget — those are fixed differently and need to be flagged as app issues, not theme issues.

None of these are the reporter's fault as such. They're just the categories where guessing is worse than asking.

---

## One-time developer setup (do this once, delete rule 6 forever)

BugHerd captures the page URL but not the theme. It can be made to capture the theme, by adding metadata to the BugHerd snippet in the theme:

```javascript
var BugHerdConfig = {
  metadata: {
    theme_id:   "{{ theme.id }}",
    theme_role: "{{ theme.role }}",
    template:   "{{ template }}"
  }
};
```

Every task then carries the theme it was filed against under **Additional Info** in the task detail. This turns "works for me" from an argument into a one-line check, and it's the single highest-value change available to this board.

> On the reference board, `metadata` was empty on **all 90** tasks — this is not installed yet.
