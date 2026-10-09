# `shopify-speed-tune` refuses to start while the repo's pre-commit hook fails, unless the developer approves skipping it for that invocation

`shopify-speed-tune` commits each kept Round once, on the branch it creates for the invocation, and the commit goes through the client repo's own pre-commit hook. The skill's spec took that commit for granted. Its keep path is "one commit", and none of the checks it lists before the skill creates anything looks at the hook.

Client repos built on the Golden theme run a pre-commit hook that formats the staged files, then runs `shopify theme check --fail-level=info` over the whole theme. Because it checks the whole theme and fails even at info level, one offense anywhere fails every commit, and these repos carry plenty: on one store, the unchanged repo failed with hundreds. Every keep commit would be refused and no Round could be kept, so an invocation would measure for hours and keep nothing. In the `/goal` sessions this skill replaces, hooks that were broken or failed on old offenses ended in `--no-verify` commits in three sessions of eight, one of them made without asking again.

So `start` runs the repo's pre-commit hook the way `git commit` would, on the unchanged repo, before it creates any theme, branch or lock. A hook that fails refuses the invocation with `REFUSED pre-commit-fails`, naming the hook, its exit code and how its output ended. The developer then fixes what the hook reports and starts again, or approves committing this invocation's kept Rounds with `--no-verify`. Only that explicit approval, given for this invocation, lets the agent pass `--no-verify-approved`, and it covers this invocation alone: the next one checks the hook again. Like the spec's own refusals at the start, this one comes before anything exists, so once an invocation is under way the plan is still its only stop. The developer decided this on 2026-10-08.

## Considered options

- **Always obey the hook.** On a repo whose hook already fails, every keep is refused: hours of pairs, and nothing kept.
- **Skip the hook automatically when it already fails.** The formatter and checks the repo's owners put in the hook are skipped without anyone deciding so.
- **Ask at the plan stop.** The plan would stay the only place the developer decides anything. But the hook's failure is known before anything exists, and by the plan stop the invocation has made two themes and a branch and taken its baseline Measurements, all of it wasted if the developer would rather fix the hook first.

## Consequences

On a store whose hook already fails, the skill refuses to start until the hook passes or the developer approves.

The report says when kept Rounds skipped the hook. Its detail log names the hook's state, `passed`, `absent` or `bypass-approved`, and when the kept Rounds were committed with `--no-verify`, the part for the team quotes how the hook's output ended, so whoever goes live knows the hook never checked those commits. With the skip approved, the agent still runs the hook's formatter on the files each Round changes.

With a hook that passes, every keep commit runs it, and a Round whose keep commit the hook refuses is removed like any other.
