---
name: spec-implement
description: Implement one .spec task from its brief, or a batch of briefs. Use when the user sends /implement <id>, /batch, or /investigate <id>, or asks to implement, build, or finish a task under .spec/tasks.
---

# Implement one task

Read and follow the procedure file before editing product code.

- `/implement <id>`: `implement.md` in this directory, or `../../pipeline/implement.md` in the kit.
- `/batch`, or a list of briefs: `batch.md` in this directory, or `../../pipeline/batch.md` in the kit. A list is not a reason to skip the spec, that id's tests, or the docs.
- `/investigate <id>`: `investigate.md` in this directory, or `../../pipeline/investigate.md` in the kit. Do not change product code.

The id is the folder name under `.spec/tasks/`. `/implement` stays on that one id. `/batch` is the only procedure that opens the next id, and only after the current id's spec, tests, and docs are done.

Run `.cursor/tools/verify-report.py --id <id>`. Read `.spec/tasks/<id>/verify-report.md` only. Do not paste test, style, smoke, or e2e output into the chat, the spec, or `verify.json`.
