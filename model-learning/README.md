# Model learning

Material for teaching agents how we work. It is reference material, not part of service onboarding. `/onboard` and `/refresh` do not copy it into a repository.

Layout:
- `<language>/spec-writing-rules.md`: rules for writing specs in that language, derived from our own specs.
- `<language>/examples/<ticket>-<slug>/`: one worked example. `brief.md` is the input, `spec.md` is the spec we wrote, `analysis.md` maps one to the other and lists what review of the implementation found.

Available now: `java/`.

To teach an agent, give it the rules file and one or more examples, then ask it to write a spec for a new brief. The spec template is `../pipeline/spec-template.md`. The agent writes a spec only when the person asks for it.

Add an example after each spec the team approves. Update the rules file with what the new example shows.
