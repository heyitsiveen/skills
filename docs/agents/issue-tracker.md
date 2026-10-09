# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`.

## Conventions

- One feature per directory: `.scratch/<feature-slug>/`
- The spec is `.scratch/<feature-slug>/spec.md`
- Implementation issues are one file per ticket at `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numbered from `01` — never a single combined tickets file
- Triage state is recorded as a `Status:` line near the top of each issue file (see `triage-labels.md` for the role strings)
- Comments and conversation history append to the bottom of the file under a `## Comments` heading
- An orchestrator's run state is `.scratch/<feature-slug>/run-log.md` (see "When orchestrating a feature's tickets")

## When working in a git worktree

`.scratch/` is gitignored, so a git worktree has no copy of it. An agent working in a worktree reads and writes everything under `.scratch/` by the main checkout's absolute path, `<main checkout>/.scratch/<feature-slug>/…`. The main checkout is the first path `git worktree list` prints. A relative `.scratch/` path inside a worktree finds nothing, and a file written there is deleted with the worktree.

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/<feature-slug>/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## When an implementation ticket is done

Set its `Status:` line to `**Status:** done`, then append a dated note under `## Comments` saying what landed and where: the commits, the branch they landed on or were merged into, and anything that departs from the ticket, with who decided it.

```md
**<YYYY-MM-DD> — implemented.** <commits> on `<branch>`. <Departures, and who decided them.>
```

A later fact about the ticket, such as proof from real use or a follow-up, gets a dated note of its own below; earlier notes stay as written. `done` closes a ticket and is not a triage role.

## When orchestrating a feature's tickets

An orchestrator, a session that works through a feature's tickets by handing them to other agents, keeps its run state in `.scratch/<feature-slug>/run-log.md`: each decision made along the way, with who made it and when, and the notes a new session needs to resume, such as which tickets are done, which branch or worktree holds work in flight, and what comes next. It writes each entry as it happens rather than at the end, so the run state survives a lost session.

## Wayfinding operations

Used by `/wayfinder`. The **map** is a file with one **child** file per ticket.

- **Map**: `.scratch/<effort>/map.md` — the Notes / Decisions-so-far / Fog body.
- **Child ticket**: `.scratch/<effort>/issues/NN-<slug>.md`, numbered from `01`, with the question in the body. A `Type:` line records the ticket type (`research`/`prototype`/`grilling`/`task`); a `Status:` line records `claimed`/`resolved`.
- **Blocking**: a `Blocked by: NN, NN` line near the top. A ticket is unblocked when every file it lists is `resolved`.
- **Frontier**: scan `.scratch/<effort>/issues/` for files that are open, unblocked, and unclaimed; first by number wins.
- **Claim**: set `Status: claimed` and save before any work.
- **Resolve**: append the answer under an `## Answer` heading, set `Status: resolved`, then append a context pointer (gist + link) to the map's Decisions-so-far in `map.md`.
