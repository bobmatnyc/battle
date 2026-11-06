# 38 — Scenario catalog and the scenario-entry format

**Date:** 2026-11-05. **Requirement:** the catalog must hold several scenarios, so that Concord North Bridge, Hougoumont, Pegasus Bridge and Hill 223 ([37](37-first-five-selection-register.md)) can later be added as data rather than as forks of the Little Round Top builder. This change adds no historical battle and changes no rule: new games still use `poc-8`.

## What changed (implemented)

- A scenario is one `ScenarioEntry` record (`apps/poc/battle/scenario_entry.py`). Little Round Top is the entry `LITTLE_ROUND_TOP` in `apps/poc/battle/scenario.py`; `scenario.create(rules)` keeps its old signature and builds from the entry.
- One builder, `build_state(entry, rules)`, makes the initial snapshot for any entry. For Little Round Top it reproduces every edition, `poc-1` to `poc-8`, byte for byte.
- `ScenarioRegistry` (`apps/poc/battle/adapters/rules.py`) is the catalog. `bootstrap.py` constructs it from `PLAYER_SCENARIOS` and injects it into the battle, commander and headless services. `LittleRoundTopCatalog` remains as a one-entry compatibility catalog.
- Player prompts take the setting line, each side's mission and the prompt version from the entry. Each side still sees only its own mission.
- `--scenario <id>` selects the scenario for headless runs and for new interactive games; `POST /api/new` accepts an optional `"scenario"` id. The default is `little-round-top`. Unknown ids are refused with the list of known ids, before any database is opened. Headless run metadata records `scenario_id` and `variant`.
- `GET /api/map` returns the map of the current game's scenario.

## Resolution

| Need | Key | Method |
|---|---|---|
| New game or headless run | Entry `id` | `resolve(scenario_id)`; `None` gives the catalog default |
| Saved game (prompts, map) | Snapshot `scenario` label | `for_state(state)`, through the entry's `labels` |

Saved snapshots gain no new field. A Little Round Top save from any edition carries one of the labels `little-round-top-v2` to `little-round-top-v8`, all owned by the Little Round Top entry. Replay needs no catalog, because it replays the recorded snapshots and actions.

## Entry format

| Field | Type | Meaning |
|---|---|---|
| `id` | str | Catalog id used by `--scenario` and `/api/new` |
| `title` | str | Human name |
| `variant` | str or None | Variant label, recorded in run metadata. Each variant is its own entry with its own `id` and labels |
| `rules` | str | Rules edition for new games; must be the current edition |
| `prompt_version` | str | Version recorded with every model decision |
| `prompt_setting` | str | Setting line in the shared prompt, e.g. `Little Round Top, 1863` |
| `labels` | edition → str | Snapshot `scenario` label per supported edition. A new scenario needs only the current edition |
| `location`, `date`, `start_time`, `time_basis` | str | Command-desk setting; `start_local` is `date` + `T` + `start_time`, local battlefield time |
| `seconds_per_turn` | int | Simulation step |
| `weather` | dict | Fixed initial condition (`season`, `conditions`) |
| `sides` | side id → `SideEntry` | Per side: `name`, `role`, `mission` (that side's prompt only), `charge` (staff adviser summary), `command_unit` (the detachment the controller is attached to), `headquarters` (rally point), `supply` (`SupplyEntry`: name, hex, ammunition, weapon class; optional) |
| `units` | tuple of `UnitEntry` | `id`, `side`, `name`, starting hex, and `overrides` applied to the default detachment (`scenario_entry.unit`) |
| `victory` | `VictoryEntry` | `kind`, `objective` hex, `defender`, `attacker`, `deadline_turns`, `radius`, `hold_turns` |
| `map` | `MapEntry` | `terrain` (callable returning the cell dict), `features` (`roads`, `buildings`, `works`), grid size, metres per hex, display size, source and source URL |
| `order_catalog` | tuple of template ids | Orders the scenario expects |
| `communications` | str | Command transport profile id |
| `voice_profile` | str | Dispatch voice for model prose |
| `tools_per_unit` | int | Entrenching tools per detachment (`poc-6` and later) |

The synthetic two-unit duel in `apps/poc/tests/scenario_fixtures.py` is a minimal complete example. It is a test fixture and is not in the player-facing catalog.

## What `poc-8` can run

`validate` refuses, at catalog construction, any entry the `poc-8` engine cannot run. Each limit below is a constant or literal in the rules, so lifting it is a rules change and needs a new edition with frozen `*_v8` modules and an old-save decision.

| Entry field | `poc-8` requires | Where the rules fix it |
|---|---|---|
| `sides` | Exactly `union`, `confederate` | `SIDES`, `engine.advance`, `runtime.apply` (player orders are Union), browser labels |
| side `role` | `union` defends, `confederate` attacks | `engine.advance` |
| `victory` | `hold-objective`, radius 1, 3 hold turns; deadline and objective free | `engine.advance` |
| `map` grid | 24 × 21 hexes, 50 m | `grid.COLS`, `grid.ROWS`, `grid.valid` |
| `seconds_per_turn` | 30 | Delay text in `engine.issue` |
| `order_catalog` | The full `poc-8` catalog | `orders.TEMPLATES`, `orders.validate` |
| `communications` | `civil-war-courier-v1` | `comms.PROFILE` |
| `voice_profile` | `civil-war-en-v1` | `presentation.VOICE_INSTRUCTION` |

Other `poc-8` limits that validation does not check: every unit is present at turn 0 (no arrival schedule); line of sight is fixed at 7 hexes with no darkness; `weapon_class` is a label used for resupply and identification, with one fire model for all; split and combine use 12 and 80 troops; outcome reasons and the map label in the browser name the Little Round Top summit.

## What each planned battle needs beyond data (proposal)

| Battle | Fits as data now | Still needs code or a new edition |
|---|---|---|
| Concord North Bridge | Terrain, roster, setting, missions, prompt version | Side ids and labels other than Union/Confederate; a 1775 voice and spoken-order profile; fire discipline (no first fire) and the reach of a spoken order; succession after an officer falls; a crossing-only river (terrain has costs, not impassable edges); smoothbore fire effects |
| Hougoumont north gate | Farm buildings as features, roster, setting, the two variants as separate entries | The `poc-9` gate state from [37 §2 Option A](37-first-five-selection-register.md#option-a--model-the-gate-proposal): openings on building edges, a *Close the gate* order (`common-orders-v4`), labour and push under contact, units cut off inside; a courtyard-possession victory instead of the summit model; a Napoleonic voice and command profile |
| Pegasus Bridge | Terrain, roster, date and a night local start time | Scheduled arrivals for separate glider landings; darkness limiting sight; alarm delivery; bridge state (intact or demolished); a seize-then-hold-for-relief victory in which the attacker must then defend; WWII radio and voice profiles; side ids other than Union/Confederate |
| Hill 223 (R1, R2 on L1) | Two variant entries sharing terrain L1; a 17-strong patrol through unit `overrides`; variant labels in run metadata | Machine-gun arcs, dead ground, local surrender and prisoner escort with conserved prisoner accounting; a reach-the-rear-and-return victory; formation limits below 12 troops; a WWI voice profile; terrain L2 waits for a readable source |

## Verification

`apps/poc/tests/test_scenario_catalog.py` pins the Little Round Top snapshots for all eight editions, the map document and both side prompts to SHA-256 digests taken at commit `503d541`. It also runs the duel fixture headless twice, replays it from storage alone, and checks prompt mission isolation, unknown-id refusal and entry validation.
