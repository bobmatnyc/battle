# Contract fixtures

Recorded from the Python app at commit `c733662` by `python3 -I packages/contracts/fixtures/record.py` (run from the repository root). One offline Little Round Top game: one order body (a hold for U1 with `destination: null`, a hold for U3 with no `destination` key), one staff chat message, 12 clock intervals; responses read through `HttpApi`, no server. The game id is pinned to `f1c7f1c7f1c7f1c7`, so two runs write identical files. Each file and its request are listed in [docs/research/67](../../../docs/research/67-typescript-contracts.md#fixtures). Do not edit by hand; re-run the script and `npm test`.

`map.json` (`GET /api/map`, the same game) was added for the TypeScript desk; see [docs/research/70](../../../docs/research/70-ts-desk-slice-1.md).

`scenarios.json` (`GET /api/scenarios`, the player-facing catalog) was added for desk slice 2; see [docs/research/71](../../../docs/research/71-ts-desk-slice-2.md). Re-recording rewrote no other fixture.

`map-features.json` (desk slice 3, [docs/research/73](../../../docs/research/73-ts-desk-slice-3.md)) holds each catalog entry's opening commander `map_features` (the projection `/api/state` serves, read the way `apps/poc/scripts/check_map_features.mjs` reads it), with the map's `metres_per_hex` and its bridge crossing cells. Re-recording rewrote no other fixture.

`standing-request.json`, `formation-request-split.json`, `formation-request-combine.json` and `state-commander-commands.json` (desk slice 4b, [docs/research/81 §12](../../../docs/research/81-ts-desk-slice-4-scope.md)) come from a second Little Round Top game with the same pinned id: U1 is sent Preserve the force, headquarters U2 detaches 20 troops to its first free neighbour, the detachment UD1 is combined back into U2 once the split is reported, and the clock runs until the combine and the standing order are reported (revision 9). The three request files are the bodies the POC accepted. Re-recording rewrote no other fixture.

`replay-commander-pegasus.json` (desk slice 4a, [docs/research/81](../../../docs/research/81-ts-desk-slice-4-scope.md)) is the British commander replay (`GET /api/replay`) of a headless Pegasus Bridge run at the first revision holding a delivered codeword (Ham, revision 13). The catalog entry blows its bridge before Ham can be sent, so the run uses the headless-only `guard-only+relief-1h` entry, scripted on both sides. Re-recording rewrote no other fixture.
