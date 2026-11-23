# unSpootify: instructions for Claude

**Read `PLAN.md` first, every session.** It is the plan of record.

## Staying on task
- Work only on the current phase in `PLAN.md`, in order. Don't start the next phase early.
- New ideas, feature requests, or "while we're here" fixes that aren't in the current phase go to the **Backlog** section of `PLAN.md`, then back to the task. Gently do the same when the owner drifts.
- Phases marked **CHECKPOINT** end with stopping and asking the owner to approve. Don't continue past one without a yes.
- Tagging (Phase 6) is a bonus. Do not build any of it before Phase 5 is done.
- Decisions in `PLAN.md` are settled. To change one, ask the owner, then update the table.
- Tick checkboxes as items land and update the **Status** line at the end of each session.

## Users
Four people; three are non-technical and can't debug. Every error the app shows must say what happened and what to do, in plain words. No terminal steps for end users, ever.

## Git
- Claude owns commits, pushes, PRs, and merges.
- One branch per phase or feature (`phase-0-skeleton`, `feat/force-format`, ...), PR into `main`, merge when the phase item is done and tests pass.
- Don't merge a CHECKPOINT phase until the owner approves.
- Never commit Soulseek credentials, `vendor/` binaries, or downloaded music. Commit `uv.lock`.

## Layout (target)
- `src/unspootify/`: Python backend (pipeline, settings, state, sockseek runner)
- `src/unspootify/ui/`: HTML/CSS/JS shown in the pywebview window. `base.css` = layout, `themes/*.css` = looks (contract in `themes/THEMING.md`). New UI must be styled in every look.
- `scripts/`: dev and build scripts (`fetch_sockseek.sh`, packaging)
- `vendor/`: bundled third-party binaries, gitignored
- `legacy/`: old Node web app, reference only, deleted at v1

## Dev
- Python 3.13, managed with `uv`. Run tests before every PR.
- Downloader is **sockseek** (formerly sldl). Fetch it with `scripts/fetch_sockseek.sh`; CLI reference: `vendor/sockseek/<platform>/sockseek --help` (and `--help <topic>`).
- Run the app: `uv run python -m unspootify` (add `--mockups` for the look check).
- Before handing any UI change to the owner, run `uv run python -m unspootify --smoke-test` (and with `--mockups`): it opens the real window, fails if any CSS/JS didn't load, and quits.
- pywebview serves pages over HTTP rooted at the page's own folder, so every HTML page lives directly in `src/unspootify/ui/` and never references `../`.
- Check UI visually with `uv run python scripts/screenshot_ui.py <page.html> <out.png> [query] [WxH]` (offscreen Qt WebEngine, same engine as the Linux app).
- Claude can't test macOS. Flag anything Mac-specific for a human test.
