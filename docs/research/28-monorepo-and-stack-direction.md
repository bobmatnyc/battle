# Monorepo layout and proposed full stack

Date: 2026-11-05. **Implemented:** isolate the existing POC under `apps/poc/`. **User preference:** likely Vercel/TypeScript/Next.js for the full application, with recommendations requested. **Proposal:** the future layout and production architecture below; no production stack or hosting has been provisioned.

**Later target decision:** [Evo is the first deployment target](31-evo-target-and-typescript.md); the Vercel discussion below is an optional future topology.

## Current layout

```text
apps/poc/
  battle/           Python domain, services, contracts and adapters
  static/           buildless UI, MapLibre and map assets
  tests/            component and adapter contracts
  scripts/          HTTP/UI/geometry checks
  data/             ignored SQLite saves
  artifacts/        ignored local verification artifacts
  .env.local        ignored server credential, owner-only permissions
  README.md
  AGENTS.md
docs/research/      shared product/design/source records
Makefile           root launch and verification shortcuts
README.md
AGENTS.md
```

Existing Python imports and HTTP routes remain unchanged. Application-relative path resolution makes configuration, assets and default storage independent of shell location. Direct CLI commands run from `apps/poc/`; the root Makefile performs that change of directory. Earlier implementation notes use paths relative to the POC unless explicitly described as repository paths. Research links remain rooted in this shared notebook.

The saved database and credential move with the POC, without recreation. Existing frozen rules still load and replay; no Reset is required. Each `make headless-poc` run creates a separate temporary directory and prints its path. No Git repository was initialized by this reorganization.

## Recommendation

**Use TypeScript/Next.js on Vercel for the full command application, retaining an independently runnable simulation worker.** This follows the user's preference and keeps the service boundaries already established in [27](27-service-architecture-and-dependency-injection.md). Start with a small number of processes; service-oriented design does not require a fleet of microservices.

| Proposed location | Responsibility |
|---|---|
| `apps/web/` | Next.js command desk, map, dispatches, player messaging, authentication and authorized command/query endpoints |
| `apps/sim-worker/` | Battle scheduling, tick ownership, bounded commander calls and atomic commits |
| `packages/contracts/` | Versioned commands, observations, events, codecs and runtime validation; no secret-bearing server dependencies |
| `packages/sim-core/` | Pure deterministic transitions, grid, engagement, communications and observer projections |
| `packages/application/` | Command/query/replay use cases and dependency interfaces |
| `packages/adapters/` | Store, inference, clock and transport implementations, kept server-only where appropriate |
| `apps/poc/` | Independently runnable Python behavioral reference |

These are proposed paths, not created packages. Choose workspace tooling when TypeScript implementation starts; a build orchestrator is optional until there are enough packages to benefit from it.

Next.js distinguishes server-rendered components from client components for interactive/browser behavior. Keep the map and live controls on the client, with credentials and authoritative command handling on the server. The simulation core should have no React, Next.js, browser, network or database dependency. [Next.js component boundaries](https://nextjs.org/docs/app/getting-started/server-and-client-components).

Vercel supports selecting a monorepo subdirectory as a project's root. `apps/web/` would be that root; build dependency declarations must include shared packages. Vercel documents workspace-aware skipping of unaffected projects, with requirements that should be revisited once the actual package graph exists. [Vercel monorepos](https://vercel.com/docs/monorepos).

## Worker and realtime hosting

Do not tie a battle's lifetime to a page request, browser tab or WebSocket connection. This is an architectural recommendation based on durable simulation requirements, rather than a claim that Vercel cannot host workers.

Current Vercel documentation offers container-based **Daemons** in public beta. They run continuous processes, restart after failure and currently run only in production environments, not preview deployments. This makes them a plausible future host for the worker, with a portable container on another host as an alternative. Availability, quotas, cost and interruption behavior still need an actual deployment evaluation. [Daemons](https://vercel.com/docs/daemons).

Vercel distinguishes continuous workers, queued jobs and durable workflows. Its worker guidance calls for external durable state, graceful shutdown and repeated-delivery safety. Use that separation for tick processing versus optional long-running background analysis; do not assume a workflow scheduler supplies tactical clock semantics. Local daemon storage is ephemeral. [Background worker guidance](https://vercel.com/docs/background-workers).

Functions have bounded invocation durations. Current documentation lists 300 seconds for Hobby, 800 seconds generally available on Pro/Enterprise, and a per-function 1,800-second beta maximum for supported runtimes. These are deployment limits, not simulation-time limits. [Function duration](https://vercel.com/docs/functions/configuring-functions/duration).

Vercel now documents native WebSocket support. Connections end at the function duration limit; reconnects can reach another instance. Therefore realtime delivery needs reconnection, resubscription and recovery from a durable observation cursor. Keep durable shared state outside connection memory. Polling remains sufficient while testing low-frequency command-map updates. [WebSockets](https://vercel.com/docs/functions/websockets).

## Authority, persistence and multiplayer

The following are proposed contracts, not implemented production capabilities:

1. One authoritative tick owner per battle, with a renewable lease and fencing token; compare-and-swap revision checks remain mandatory after ownership changes.
2. Idempotent command identifiers, explicit expected revision and side/role authorization. Persist accepted commands before reporting acceptance. A worker crash must not lose them or apply them twice.
3. Commit state, essential events, accepted decisions and an outbox record atomically. Publish authorized projections after commit; failed publication retries cannot rerun combat.
4. Pause/speed/reset authority is a scenario policy. Reset creates a new battle and retains the archive. Playback never advances the live battle or requests new inference.
5. Realtime feeds expose only recipient-authorized observations and dispatches. God Mode requires explicit host/scenario permission. A UI toggle cannot confer that permission in multiplayer.
6. Simulated courier/radio delay remains part of deterministic rules, separate from real network latency. A fast WebSocket must not deliver a battlefield report before its in-world arrival.

SQLite remains the POC authority. The earlier graph-database direction remains open for the full system: select a product only after testing transactional state/event commits, relationship queries, historical replay, concurrency and operating cost against representative scenarios. Do not introduce both an authoritative graph and authoritative relational snapshot with uncoordinated writes. Any secondary graph projection must be explicitly reconstructible and non-authoritative unless the architecture decision changes. No new database recommendation is treated as approved selection here.

## Migration and verification gates

Keep Python until a TypeScript component proves equivalence, rather than rewriting the working demo to establish folder structure. Export tiny versioned fixtures covering units, grid, communications, observations, engagements, lifecycle and events. Compare serialized inputs, ordered effects and resulting states across runtimes. Specify numeric precision, rounding, integer bounds and stable iteration order; superficially identical Python/JavaScript arithmetic is insufficient evidence of equivalence.

Preserve frozen Python editions for old saves. New TypeScript rules may receive a distinct rules ID; never claim cross-runtime replay of an old edition without exact fixture and full-battle evidence. Run deterministic component tests separately from model evaluations and historical calibration.

Evo remains the first intended full testing environment. Verify its identity, resources and provider access before execution. Exercise restart recovery, duplicate jobs, stale owners, disconnect/resume, persistence failures and observer isolation there before choosing deployment. No Evo run or production deployment is claimed in this document.

## Sources and uncertainty

All software sources above are official, accessed 2026-11-05. Vercel beta features and limits are time-sensitive and must be rechecked before provisioning. The layout, authority contracts and migration plan are original design recommendations; these sources establish platform capabilities, not suitability or measured performance for this game. Historical terrain and combat calibration are unchanged by this work.

## Relocation verification — 2026-11-05

- `make test-poc`: 180 Python tests, UI regression checks and map geometry checks passed from the new directory.
- `make smoke-poc`: isolated HTTP checks passed, including observer isolation, commands, clock, replay and static/secret boundaries.
- `make headless-poc`: game `92b7b807478d4117` completed 60 turns with 2,562 events; all 63 replay snapshots were identical.
- SQLite integrity check returned `ok`; all three existing saved battles replayed identically.
- The main server was restarted from `apps/poc/` at port 8874. HTTP readback confirmed game `1dc13035e2844411`, rules `poc-3`, turn 4, revision 4, paused, unchanged from before the move. Its referenced local UI assets returned HTTP 200.
- Local Markdown targets resolve and `.env.local` retains mode 0600. No live inference was invoked for these checks. No rules, combat coefficients or saved-game schema changed.

These are local execution results. They do not establish Evo readiness, historical calibration or deployed multiplayer behavior.
