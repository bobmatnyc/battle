# battle

A historical command game: choose strategy, delegate intent to autonomous unit commanders, and react to delayed battlefield reports. Deterministic rules adjudicate effects; agents make bounded decisions from authorized knowledge. Technology spans land and sea warfare through WWII.

## Current workspace

| Path | Status |
|---|---|
| [apps/poc](apps/poc/README.md) | Playable Python/SQLite Little Round Top experiment, including UI, tests, assets and local data |
| [docs/research](docs/research/README.md) | Shared design, sources, implemented contracts and limitations |
| [Stack direction](docs/research/28-monorepo-and-stack-direction.md) | Proposed TypeScript/Next.js application and independent simulation worker |

The POC is an authored scenario based on a historical engagement, not a calibrated reconstruction. Its complete play guide, architecture and limitations are in [the POC README](apps/poc/README.md).

**Current deployment: keep the POC on the workstation.** Evo remains a future option; `make package-evo` only prepares a portable bundle. See the [Evo runbook and TypeScript decision](docs/research/31-evo-target-and-typescript.md).

## Local development

```sh
make poc                 # http://127.0.0.1:8874
make poc-offline         # scripted commanders, no inference calls
make test-poc            # Python components, UI smoke and map geometry
make smoke-poc           # isolated local HTTP smoke
make headless-poc        # scripted battle + exact replay; temporary database
make web                 # TypeScript desk on http://127.0.0.1:8875, relaying to the POC on 8874
make smoke-web           # real-browser click test of the TypeScript desk; isolated POC and ports
```

Python 3.11+ runs the POC without additional Python packages; Node is needed for the JavaScript checks. Pass server options with `make poc POC_ARGS="--port 8875"`. Direct commands run from `apps/poc/`, for example `python3 -m battle --offline`.

Saved battles live in `apps/poc/data/battle.sqlite`; server-only configuration is in ignored `apps/poc/.env.local`. Restart resumes the newest saved battle with its clock paused. Moving the POC does not reset or migrate battles. Shared research stays at the repository root.

## Proposed full stack

The workstation remains the current host. TypeScript for the web application and contracts is recommended; self-hosted Next.js or a later Vercel frontend are options. Keep the Python simulator independently runnable until a port proves replay equivalence.

The playable app is in `apps/poc/`. `apps/web` holds the first TypeScript desk slice (Little Round Top map, counters and a move order against the running POC; see [70](docs/research/70-ts-desk-slice-1.md)), and `packages/contracts` holds its wire contracts. Build handoff notes are local only (`docs/build-handoff.md`, not published).

[Design scale assessment](docs/research/30-design-scale-assessment.md): what the playable skirmish proves, what breaks at company and campaign scale, and which experiment to run next.
