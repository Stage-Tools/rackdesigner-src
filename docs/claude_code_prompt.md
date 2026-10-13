
You are working on RackDesigner, a PyQt6 desktop app. Before doing anything
else, read these files in the `docs/` folder (project root/docs/), in this
order:

1. `docs/project.md` — what the app is, stack, scope
2. `docs/folder_structure.md` — real folder/file layout (verify it still
   matches disk; correct it if not, and note the correction)
3. `docs/design.md` — architecture, data model, known architectural gaps
4. `docs/status.md` — current version, known bugs, what's verified vs not
5. `docs/task.md` — task list with status; this is what you are here to
   work on
6. `docs/changelog.md` — recent history; `Changelog.txt` (project root,
   not in `docs/`) is the older archived log, read only if you need
   historical context

Ground rules:

- **`docs/` on disk is the canonical, live version — you write directly to
  it.** After each session, the project owner reports your summary back to
  the orchestrating chat, where decisions for the next session get made.
  You don't need to reconcile with any separate copy elsewhere.
- **Do not implement anything not explicitly listed as approved in
  `docs/task.md` for this session.** If you find additional bugs, design
  issues, or ambiguities while working, add them to `docs/task.md` under
  Backlog (or a new subsection) and report them back — do not fix or
  refactor opportunistically.
- If a task's fix direction is marked "pending confirmation" or a bug's
  root cause is marked "hypothesis", investigate/reproduce first and report
  findings before writing the fix, unless the task explicitly says to
  proceed.
- After completing (or partially completing) any task: update
  `docs/task.md` (status), `docs/changelog.md` (new dated entry, following
  the template at the bottom of that file), and `docs/status.md` if the
  change affects what's known/working/broken. Update `docs/design.md` if it
  changes architecture, and `docs/folder_structure.md` if it changes file
  layout.
- Keep changes scoped to what was asked. If a fix requires touching a file
  or area not mentioned in the task, say so before proceeding rather than
  expanding scope silently.
- End the session with a short summary: what changed, which files, which
  doc files were updated, and what's left open in `task.md`.
