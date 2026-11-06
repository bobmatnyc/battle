# Working on the POC

Read the root `../../AGENTS.md`, this directory's `README.md`, and shared `../../docs/research/README.md`. Root gameplay, information, persistence, authorization and collaboration constraints apply here.

- Keep all experiment code, tests, static assets, scripts and local runtime files in this directory. Shared research belongs in `../../docs/research/`; update its index and source register for new design work.
- Run Python and JavaScript commands from this directory, or use the root Makefile. The Python module remains `battle`; do not change imports to include `apps.poc`.
- Resolve default data, static and configuration paths from the application location. Preserve ignored `data/`, `artifacts/` and owner-only `.env.local`; never print credentials. Temporary verification databases must not replace a user's battle.
- Wire dependencies in `battle/bootstrap.py`. Preserve interfaces in `battle/contracts.py`, service boundaries, authorized observations and atomic state/event/decision commits. The framework and browser never adjudicate combat.
- Freeze prior rules editions and preserve replay. A directory move or structural refactor does not justify a rules-version change or Reset.
- Run `python3 -m unittest discover -s tests -q`, the two JavaScript checks and relevant HTTP/headless checks for structural changes. Report runtime verification separately from source/test results.
- Future TypeScript packages are proposed in `../../docs/research/28-monorepo-and-stack-direction.md`; do not scaffold them as part of ordinary POC work. Keep this experiment independently runnable throughout migration.
