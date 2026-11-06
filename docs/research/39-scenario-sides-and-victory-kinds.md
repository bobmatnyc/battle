# 39 — Scenario-defined sides and victory kinds (`poc-9`)

**Date:** 2026-11-05. **Requirement:** the battles after Little Round Top need their own side ids and their own ways to win ([38](38-scenario-catalog.md), [37](37-first-five-selection-register.md)). Hougoumont, for example, has `allied` and `french` sides and a courtyard-possession victory. This change prepares that ground. It adds no historical scenario and no new victory rule.

## Rules-edition decision

New games use `poc-9`. Saved `poc-1` to `poc-8` games keep their editions and replay through frozen modules.

**Why a new edition.** The engine must read side ids, names, roles and the victory model from the battle, and replay must not need the catalog. The snapshot therefore stores three new fields, which changes the shape of stored state for new games. AGENTS.md requires a new edition for that. The change is not behaviour-neutral in general either: outcome reasons now take the side names and objective name from the scenario, and the capture rule reads its radius and hold time from the snapshot.

**What is frozen.** `battle/engine_v8.py` is the `poc-8` `engine.py` at commit `ed33325`, byte for byte apart from its module docstring. `engine.py` routes `poc-8` states to it, and through it to the earlier frozen engines. The other live modules (`orders`, `formations`, `features`, `recommendations`, `standing`, `recon`, `comms`, `tactics_v8`) behave identically for `poc-8` and `poc-9`: their only changes accept `poc-9` wherever they accepted `poc-8`, and `features.setup` reads the side ids from the snapshot it builds. They are shared, not copied. `runtime.apply` acts for the snapshot's player side, which is `union` for every edition before `poc-9`.

## What changed (implemented)

| Area | Before (`poc-8`) | Now (`poc-9`) |
|---|---|---|
| Side ids | `union`, `confederate` in the engine, runtime, headless runner, CLI and browser | From the entry; stored as `sides`, a list of `{id, name, role}` in entry order |
| Player side | Union, hard-coded in `runtime.apply` and the battle service | Entry `player_side` (default: first side); stored as `player_side` |
| Computer side | Confederate, the default side of `CommanderService.decide` | The one stored side other than `player_side` (`Simulation.computer_side`); `decide` takes `side` explicitly, and a poc-9 decision must name its side |
| Roles | Union defends, Confederate attacks | Each `SideEntry.role`, `defender` or `attacker` |
| Victory | One block in `engine.advance` | `battle/victory.py`: the entry names a kind in `victory.KINDS`; its parameters are stored as `victory` |
| Outcome reasons | Literal Union and summit text | Built from side names, `objective_name`, `hold_turns` and turn length. Little Round Top's text is unchanged |
| Scripted control | Union fills the ring, Confederate attacks by lanes | The same by role |

Side order is a list, not dict keys, because storage writes snapshots with sorted keys and side order decides the order of some events within an interval. An early draft kept a dict; Little Round Top replay then diverged at revision 9, because `confederate` sorts before `union`.

### Victory-kind interface

A kind is an object in `victory.KINDS` with three members:

- `problems(entry)` returns the reasons an entry cannot use the kind. The catalog refuses the entry at registration.
- `setup(entry)` returns the kind's parameters, stored in the snapshot as `victory`.
- `score(s)` runs at the end of every `poc-9` interval. It may update only the kind's own counters and returns `(winner, reason)`, with `winner` None while the battle goes on.

`hold-objective` is the only kind. It is the `poc-8` rule with its constants made parameters: `radius` (default 1), `hold_turns` (default 3) and `objective_name` (default `objective`; Little Round Top uses `summit`). It needs exactly two sides, one defender and one attacker. Adding a kind changes rule effects, so it needs the next edition.

## Little Round Top plays identically (verification)

- `make headless-poc` output at `ed33325` and on this branch, with the game id blanked and the temporary-directory line removed, is byte-identical (`cmp` exit 0). The summary prints no rules label.
- The same scripted plays (Union baseline, Confederate decision path, and an interactive game with orders, standing order, chat, split and a recommendation response) give final states equal to the `ed33325` states, once the three new fields are dropped and the `poc-9` / `little-round-top-v9` labels are read as `poc-8` / `-v8`.
- Saves written at `ed33325` replay `identical` on this branch through `engine_v8.py`.
- `tests/test_scenario_sides.py` pins the `ed33325` final-state digest of the scripted run. It checks that a `poc-8` game still reaches it and that a `poc-9` game reaches it after the same label mapping.

## Renamed sides (verification)

`tests/scenario_fixtures.py` derives `BLUE_GREY_DUEL` from the test duel with side ids `blue` and `grey`. It is a test fixture and not player-facing. It runs headless with either side as the player and replays `identical` from storage alone; the stored battle contains neither `union` nor `confederate`. Against the same duel under `union` and `confederate`, it ends with the same unit states, winner, reason and turn. Contact reports are sorted by side id (`recon.reports`), so the order of events within an interval can differ between the two.

## What Hougoumont still needs (proposal)

[37](37-first-five-selection-register.md#option-a--model-the-gate-proposal) proposed the gate for "`poc-9`". That number is now taken, so the gate needs `poc-10`, with `engine_v9.py` and any changed module frozen. Side ids `allied` and `french`, their names and roles are now entry data. Still code: gate state on building edges, the *Close the gate* order and its catalog version, labour and push under contact, units cut off inside, a courtyard-possession kind in `victory.KINDS` (the defender may need to hold rather than the attacker to take), browser labels for non-Union sides and a Napoleonic voice and command profile.

## Still fixed by the rules

Grid size, turn length, order catalog, communications profile and voice profile stay as in [38](38-scenario-catalog.md#what-poc-9-can-run). The browser's mission panel, summit marker and outcome headline remain Little Round Top copy; side colours and the "YOU" marker now follow the player side.
