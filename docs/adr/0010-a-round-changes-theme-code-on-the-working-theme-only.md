# A Round changes theme code on the Working theme only

`shopify-speed-tune` writes only to two unpublished themes it creates itself. Each Round's change is tested on the Working theme. The Control theme holds the kept Rounds and is measured against it. Specifically, the skill never:

- writes to the published theme
- pushes with `--live` or `--allow-live`
- pushes a branch that is connected to the published theme
- switches an app embed, app block or tracking tag on or off

Going live is a person's step, taken after the report. The skill measures what each app and tag costs and reports it. Code that an already-uninstalled app left behind counts as theme code, so it is in scope.

Each of these limits answers something that went wrong in the eight `/goal` runs this skill replaces:

- The published theme was the test bed. One store took a push to live on every try, and another shipped its first round to live with no preview.
- A change tested on a dev theme still broke keyboard focus in a live mobile menu.
- An agent ran `git push origin main` — a live deploy on a GitHub-connected store — before asking.
- One client's files were pushed onto another client's dev theme.
- The developer turned down app changes five times. Whether a merchant keeps an app is a business decision that a performance score cannot make.

## Consequences

The score clients see does not move until a person publishes. Rollback stays cheap: on a CLI-managed store the old theme stays in the theme library, and on a GitHub-connected store the change is one merge to revert.

A store whose cost is mostly apps reaches a low Ceiling and stops there. ADR 0009 is what makes that an honest result rather than a failure.

The first version leaves out deferring a third-party script until interaction, a chat widget for example, without ruling it out. Shopify accepts the technique as legitimate, but each app would need its own functional check.
