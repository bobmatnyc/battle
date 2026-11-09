# Doc 84 counterfactual scripts and outputs (bt-T27)

Evidence for [84-d37-model-vs-control.md](../84-d37-model-vs-control.md). The doc 84 author (bt-T25) wrote these as scratch files in `/tmp/t25`. They are archived here as written. No script contains a key or key label (grep for `sk-or-`, `OPENROUTER` and `label` found only the argument `player_provider='openrouter'`).

The scripts hard-code paths into the bt-T25 worktree (`.claude/worktrees/agent-a3710adf3b45ab492/apps/poc`) and into the git-ignored D37 artifacts. To re-run, change those two paths. No script calls a model or the network. The fake provider replays recorded orders by call number.

## Replay scripts

| Script | What it did | Doc 84 claim it backs | Command |
|---|---|---|---|
| `cf.py` | Replays the Little Round Top game 1 orders with one edit: `none`, `no-u1-move-t0`, `only-u1-move-t0`. | Section 2 replay table (no orders: confederate 28; without the U1 move: confederate 35; only the U1 move: confederate 25). | `python3 cf.py none no-u1-move-t0 only-u1-move-t0` |
| `cfa.py` | Replays game 1 of any entry with `recorded` or no orders. | Section 2 first row, and section 5 (Hougoumont, Pegasus, Hill 223 same winner and turn with no orders). | `python3 cfa.py <entry> recorded none` |
| `cfg.py` | Gergovia: swaps call 0 between games 1 and 2. | Section 3 replays (game 1 with game 2 call 0: roman 38; game 2 with game 1 call 0: roman 65; no orders: gallic 36). | `python3 cfg.py g1-recorded g2-recorded g1-with-g2-call0 g2-with-g1-call0 no-orders` |
| `cfc.py` | Concord: same swap between games 1 and 2. | Section 4 (game 1 with game 2 call 0: provincial 8; no orders: british 20). | `python3 cfc.py g1-recorded g2-recorded g1-with-g2-call0 g2-with-g1-call0 no-orders` |
| `empty.py` | Counts model calls with no orders and their cost. | Section 1 (52 of 88 decisions, $1.15). | `python3 empty.py` |
| `cost.py`, `runs.py` | Per-game decisions, tokens and cost from `runs.jsonl` and the game databases. | Section 1 table. | `python3 cost.py`; `python3 runs.py` |

## Inspection helpers (read-only queries on the game databases)

`grid.py` (hex distances to the summit), `ords.py` (order sent/delivered/expired events), `mv.py` (movement events in a turn range), `snap.py` (unit strength from snapshots), `ev.py` and `sumev.py` (event listings), `dec.py`, `dump.py`, `keys.py`, `obs.py` (decision payloads and observations). These back the `seq` and `idx` citations throughout doc 84.

## Control run

`runctl.sh` ran `make headless-poc SCENARIO=<id>` for the six scenarios. Output: `ctl-<scenario>.log`, the summary line of each control game (winner, turns, replay status). The control databases are binary and large. They are in the git-ignored archive, not in the repo.

## Binary archive (not in git)

`apps/poc/artifacts/d37-option-a-f1f4210/counterfactuals/` in the main checkout, with `MANIFEST.txt` (file, size, sha256). It holds `ctl-<scenario>.sqlite`, the six control databases. They were written to the system temp directory by `make headless-poc`, not to `/tmp/t25`, and were copied from there.
