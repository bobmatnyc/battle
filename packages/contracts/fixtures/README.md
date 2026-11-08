# Contract fixtures

Recorded from the Python app at commit `c733662` by `python3 -I packages/contracts/fixtures/record.py` (run from the repository root). One offline Little Round Top game: one order body (a hold for U1 with `destination: null`, a hold for U3 with no `destination` key), one staff chat message, 12 clock intervals; responses read through `HttpApi`, no server. The game id is pinned to `f1c7f1c7f1c7f1c7`, so two runs write identical files. Each file and its request are listed in [docs/research/67](../../../docs/research/67-typescript-contracts.md#fixtures). Do not edit by hand; re-run the script and `npm test`.

`map.json` (`GET /api/map`, the same game) was added for the TypeScript desk; see [docs/research/70](../../../docs/research/70-ts-desk-slice-1.md).
