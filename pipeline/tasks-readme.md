# Tasks

Add one folder per task: `.spec/tasks/<id>/brief.md`.

Use the brief shape from the spec kit (`pipeline/brief.md`): goal, constraints, out of scope, and done when. Set **Kind** to `feature`, `bugfix`, or `investigation`.

`/implement <id>` implements one brief. `/batch` implements several, in order. Both write `spec.md` before code.

When `verify.json` has `"exit": 0`, the brief, the spec, and the subtasks are `done`. Spec IDE lists a brief under Open only while it has no such receipt. A finished brief left at `open` is still hidden once the receipt exists.

An investigation writes the finding in `spec.md` and does not change product code.
