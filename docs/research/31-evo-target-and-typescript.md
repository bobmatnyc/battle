# Evo deployment target and TypeScript portability

**Current operating decision:** keep the running POC on this workstation for the current build. The following is the earlier Evo decision and a future-target runbook.

**Earlier decision, 2026-11-05:** Evo is the first deployment and integration-test target for battle. The workstation is a development client. This supersedes the hosting preference in [28](28-monorepo-and-stack-direction.md); Vercel remains an optional later web host. The language of the authoritative engine remains Python for the POC. This decision does not establish a live Evo deployment.

## How to deliver today's POC

Run `make package-evo` from the repository root. It produces `apps/poc/artifacts/evo/battle-poc.zip` containing Python sources and public UI/map assets including the renderer license. It omits local databases, environment files, artifacts and dependencies installed on the workstation. Local development still uses `make poc`.

For the first Evo run:

1. Confirm the destination account/OS, Python 3.11+ with sqlite3, writable persistent storage and an unused loopback port. A workstation SSH alias named `evo` exists; that alone does not verify the remote runtime. Node is unnecessary to run the current POC.
2. Transfer the ZIP to the confirmed Evo account, unpack into a fresh release directory (e.g. `python3 -m zipfile -e battle-poc.zip release-001`), and enter that directory. Use Evo's Python executable if it is named differently.
3. Run `python3 -m battle --headless --db ../probe.sqlite` against a disposable database. Record rules, outcome and exact replay. Then run `python3 -m battle --offline --port 8876 --db ../battle.sqlite` for interactive use. Keep that live database outside the release directory across upgrades. The offline session needs no credential.
4. From the workstation, forward the same port: `ssh -N -L 127.0.0.1:8876:127.0.0.1:8876 evo`. Open `http://127.0.0.1:8876`. Using the same local/remote port satisfies the existing Host/Origin checks; 8876 also avoids the development server on 8874. The simulation and storage run on Evo. This path is for a trusted single player, not public multiplayer.
5. Confirm the UI opens, issue an order in the disposable battle, verify report delivery, then restart against the same database and check that the clock is paused and replay matches. Inference is a separate check using server-side credentials explicitly configured on Evo. No key or existing game is transferred implicitly.

The bundle is a foreground evaluation release. A production supervisor, public ingress, multi-user authorization and database migration are separate decisions.

## Would TypeScript limit deployment options?

**Little loss of hosting choice if we compile to JavaScript; a real change in runtime requirements if we port the server.** For browser-only TypeScript, build once and ship the JavaScript with the existing assets; Evo can continue to serve it with Python. A TypeScript server/worker normally means pinning a supported Node runtime (or packaging it in a container), a lockfile and a build step. A native SQLite driver or another native dependency must support the target OS/CPU; the workstation's node_modules is not a release artifact. Verify Evo's platform before selecting one.

Next.js officially supports self-hosting as a full Node server or container. Static export has limited features: it can serve the command desk if paired with a separate API, but cannot itself own an active battle, persist orders or keep provider keys private on the server. Hosted functions can handle requests; keep the battle clock, SQLite writer and authoritative simulation in a restartable worker with durable storage. A later Vercel frontend can use that same API, provided a suitably authenticated route to Evo or its successor exists. A private SSH tunnel is not production connectivity between hosts.

**Recommended sequence:** use TypeScript for new shared wire contracts and command-desk code, with runtime validation of JSON at both ends. Retain the Python engine through the [company-command experiment](30-design-scale-assessment.md). Only port a simulation component after identical accepted inputs produce matching ordered events and snapshots for the supported edition. Pay attention to integer division, rounding, stable tie order and serialization. A purely structural port offers no remedy for repeated snapshots or player workload. Platform-specific queues, storage and inference belong behind existing interfaces so changing host does not change combat rules.

**Sources (official, accessed 2026-11-05):** [TypeScript handbook](https://www.typescriptlang.org/docs/handbook/typescript-from-scratch.html), [Next.js deployment options and feature support](https://nextjs.org/docs/app/getting-started/deploying), [Node support policy](https://nodejs.org/en/about/previous-releases). These establish software capabilities, not availability on Evo. Packaging, topology and migration order are project choices.
