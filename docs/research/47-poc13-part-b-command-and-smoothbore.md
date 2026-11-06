# 47 — Succession, spoken-order reach and smoothbore fire (`poc-13`, part B)

**Date:** 2026-11-06. **Requirement:** the remaining rule prerequisites of the Concord North Bridge scenario ([43](43-concord-scenario-spec.md), R3 to R5 and the 1775 voice of row 6), plus the review items carried from part A ([46](46-poc13-river-and-fire-discipline.md)). (1) When an officer falls, command passes to a defined successor; a unit with none follows a defined fallback. (2) An order reaches only units inside a voice range of the issuing officer; others get it later by a defined relay and keep their last order until then. (3) Musket fire for 1775 uses smoothbore range and accuracy values. (4) Prompts and order text for 1775 use a period voice. Part B adds no Concord catalog entry.

## Rules-edition decision

Part B stays in `poc-13`. No engine is frozen and no edition is added.

**Why.** [43 §4](43-concord-scenario-spec.md) plans one edition for R1 to R5, and [46](46-poc13-river-and-fire-discipline.md) is labelled part A of it. The edition rule is that a published edition replays identically. Part B keeps that: every new rule reads snapshot data that no `poc-13` game saved before part B can hold.

- Succession and officers read `command_rules`; smoothbore fire reads `weapon_rules`. `build_state` writes them only for an entry that declares `command` or `weapons`. No catalog entry does, and `build_state` at `e165371` never wrote either key.
- Voice reach reads `voice_reach` from the communications profile. Only the new profile `colonial-1775-voice-v1` has one; no earlier save names it.
- The shared modules (`comms`, `formations`, `engine.summary`, `engine.report_refusal`) change only behind those keys or behind fields they create (`speaker_id` on a packet, `officers` and `leaderless` on a unit).
- `build_state` refuses an entry with part B data in an edition before `poc-13`.

**Proof.** `tests/test_poc13b.py` pins seven digests taken at `e165371`, before part B: the scripted `poc-13` Little Round Top run (Union, turn 60); a `poc-13` Little Round Top save advanced 10 and then 30 intervals through `BattleService` (Confederates, turn 28); a `poc-13` Hougoumont save advanced 40 intervals (French, turn 29); the `poc-13` north-gate arrangement (turn 12); the courtyard stall (4 intervals); the corridor contest (24 intervals); and the part A hold-fire duel (12 intervals). All match on this branch. The six `poc-12` digests of [46](46-poc13-river-and-fire-discipline.md) still match. Changing the suppression recovery in `engine.py` from 8 to 9 makes the first `poc-13` digest fail, so the pin can detect a change.

**What did change for `poc-13` games.** Prompt text only, which replay never reads: the model prompt of every scenario now lists `hold_fire` and `open_fire` among the orders with a null destination. Little Round Top's prompt is `lrt-side-v3` and Hougoumont's `hougoumont-side-v2`; v3 is v2 with that one clause changed (checked byte for byte in `test_little_round_top_prompt_is_byte_identical_to_lrt_side_v3`). Model decision telemetry now records `rules` and `order_catalog` beside `prompt_version`.

## Rules (implemented)

| Area | Rule |
|---|---|
| (1) Officers | With `command_rules`, each unit starts with `officers` (entry default 2; a unit override replaces it). Its `officer_step` is `initial // (officers + 1)`. Each time its losses since the last fall reach `officer_step`, one officer falls (`officer_down`). If one remains, the next officer takes command: the unit keeps its order, stance and posture and takes new orders as before. The unit reports the fall to headquarters. |
| (1) No successor in a unit | When the last officer falls the unit becomes `leaderless` (`unit_leaderless`) and loses `leaderless_morale` (10) morale once. It keeps its last order and its standing orders, still fires and still takes cover or withdraws by itself. A delivered order is `refused`. Headquarters learns it from the unit's report; a reported leaderless unit is not orderable (`reported_leaderless`). |
| (1) Side succession | A side's command detachment that is lost, routed or leaderless opens a vacancy (`command_vacant`) of `succession_delay` intervals (1). Orders are refused during it, as before. When it ends, command passes to the first unit in the side's `succession` list that has strength, is not lost, routed, merged or leaderless (`command_succeeded`). Reports on their way to the old detachment are re-addressed to the new one by runner. |
| (1) No successor for a side | With no such unit, `command_lost`: the side keeps the fallen detachment as its command, which is not operational, so no new orders go out and its units continue under standing orders. This is the behaviour of every earlier edition. |
| (1) Split and combine | A split gives the detachment its share of officers, rounded down; the parent keeps the rest. A part with none is leaderless. A combine adds the officers. |
| (1) Registration | `validate` refuses a succession list that names an unknown side, a unit of another side, the side's own command unit or a unit twice, and negative or non-integer counts, including a unit override `officers`. |
| (2) Voice reach | The profile `colonial-1775-voice-v1` has `voice_reach` 2 hexes (100 m). `engine.issue` sends an order by voice when headquarters' known position of the unit is within that reach of the command detachment, else by runner, as before. A voice order is due the next interval. Profiles without a reach speak only to the command detachment itself, as before. |
| (2) Out of earshot | On delivery, `comms.progress` measures the true distance from the speaking detachment to the unit. Beyond the reach, or if the speaker has fallen, the order goes on by runner from the speaker's position (`voice_out_of_reach`) at the courier rates. Until it arrives the unit keeps its last order. |
| (3) Smoothbore fire | An entry may give a weapon table (`weapons`, stored as `weapon_rules`) keyed by `weapon_class`. A class in it fires only to `range_hexes`. Its exposure term is `(range_hexes + 1 - d) * 7 // range_hexes` in place of `8 - d`, so it starts at the rifle baseline's 7 at 1 hex and falls faster. The effect is then scaled by `effect_pct / 100`. Classes not in the table keep the baseline. `SMOOTHBORE_1775` is range 2, effect 60. |
| (3) Registration | Each weapon needs an integer `range_hexes` of 1 to 5, an integer `effect_pct` of 1 to 100 and a `basis`. |
| (4) Voice | `colonial-1775-en-v1` is a prose instruction for the American Revolution in 1775, addressed to the Colonel, on the same rules as the 1863 and 1815 voices. A prompt for a voice-reach profile says that orders reach units within the reach by voice and others by runner. |
| (4) Order text | For the 1775 voice, `present_view` shows dispatched orders in period phrasing ("To B2: Stand fast. Given by word of mouth.", "A runner carries the word.") and the receipt, refusal, arrival and rout lines addressed to the Colonel. Scripted decisions read "Colonel, the companies will proceed according to their standing orders." Stored dispatch text and events are unchanged. |
| Carried LOW | `dry_run` refuses water, with or without a crossing, on any hex of a building's compound or on either side of an opening. |

## Values, sources and assumptions

No source in this repository gives a smoothbore range or hit rate, the reach of a shouted order, or how often an officer falls ([43](43-concord-scenario-spec.md), R5: "No source read gives smoothbore range or rate of fire; all are authored"). Every value below is therefore an assumption or an authored parameter, and each is labelled in code.

| Value | Where | Status |
|---|---|---|
| Smoothbore `range_hexes` 2 (100 m) | `scenario_command.SMOOTHBORE_1775` | **Assumption.** Within the 2 to 3 hexes proposed in 43 R5; not sourced. `basis` begins `assumption:`. |
| Smoothbore `effect_pct` 60 | `scenario_command.SMOOTHBORE_1775` | **Assumption.** Within the 50 to 100 proposed in 43 R5; not sourced. |
| Exposure fall-off `(range + 1 - d) * 7 // range` | `engine.volley` | **Authored**, from 43 R5's design. The baseline `8 - d` is itself a synthetic coefficient. |
| `voice_reach` 2 hexes | `comms.COLONIAL` | **Assumption.** Within the 1 to 3 hexes proposed in 43 R4; not a measured earshot. |
| `officers` 2, `officer_step` formula | `CommandEntry` | **Authored**, from 43 R3's design. It stands in for a hit; it does not model who fell. Davis's death (S48) is not reproduced by it. |
| `succession_delay` 1, `leaderless_morale` 10 | `CommandEntry` | **Authored** sensitivity parameters. |
| 1775 voice text | `presentation` | **Authored.** It quotes no historical order; the Barrett and Buttrick orders (S47) are not used as text. |

## Design choices

- **(1) Two levels.** A unit's officers decide whether it can still take orders; the side's succession list decides who commands. 43 R3 proposed both. A command detachment that loses its last officer is leaderless and so not operational, which opens the side's vacancy: one rule serves both cases.
- **(1) Fallback that does not freeze.** A leaderless unit refuses new orders but keeps acting under its last order and standing orders. This follows the existing rule for a disrupted command: subordinates continue under standing behaviour and never wait for a player action.
- **(1) No `leaderless_turns` gap.** 43 R3 proposed a gap during which a unit with a successor accepts no order. It is left out: the brief asks that the unit not freeze, and the order still travels by voice or runner, which is a delay of its own.
- **(2) Choice on knowledge, delivery on truth.** Headquarters chooses voice from the position it knows, so the dispatch text never reveals the true position. Whether the word is heard depends on where the unit really is, and the relay is the defined rule when it is not.
- **(2) Reports are not shouted.** Reports to headquarters still go by voice only from the command detachment itself. A unit within earshot reporting by voice would change report timing in every 1775 battle and was not asked for.
- **(3) A table keyed by class.** `weapon_class` was a label (Hougoumont's "smoothbore muskets" used the rifle model, [42](42-hougoumont-scenario.md)). Hougoumont has no weapon table, so it keeps that model. An 1815 table would be a scenario change, to be decided separately.
- **(4) Display-only voice.** As in [42](42-hougoumont-scenario.md), the voice changes prose and display text, never stored dispatches, events or legal order values.

## Probes before the fix

`tests/test_poc13b.py`, run with the entry data plumbing only (the `CommandEntry`, `WeaponEntry` and profile records, their registration checks, and the voice constant): 13 failures and 5 errors in 20 tests.

- (1) No `officer_down` after 14 losses; no `leaderless` field; no `command_vacant` or `command_lost` when the command detachment routed.
- (2) An order to a unit 2 hexes from the commander went by `courier`, not `voice`.
- (3) A smoothbore unit fired at 3 hexes; at 2 hexes its exposure was 200, the same as the rifle.
- (4) The 1775 prompt had no voice-reach sentence; 1775 order text used the 1863 keys; scripted text began "General".
- Carried: the prompt lacked `hold_fire/open_fire` in the null list; versions were `lrt-side-v2` and `hougoumont-side-v1`; telemetry had no `rules` (`KeyError`); water in a gateway, outside hex or compound was accepted.
- Passing before and after, as they should: an out-of-reach order goes by runner; courier profiles speak only to the command detachment; posture orders replay identically; registration of bad command data (the checks are in the plumbing); the `poc-13` part A digests.

## Outcome changes

None for any existing game. The headless runs on this branch: Little Round Top, Union at turn 60; Hougoumont, Allied at turn 60; both replay `identical`, as in [46](46-poc13-river-and-fire-discipline.md). Model runs are not comparable across the prompt change: compare `prompt_version`, `rules` and `order_catalog` in the decision records.

## Tests

`apps/poc/tests/test_poc13b.py`: the next officer takes command and the unit keeps its order; a unit with no officer keeps its last order and refuses new ones; side command passes to the named successor after the delay; a side with no successor falls back to standing orders; a split apportions officers; registration refuses bad command data; an order within reach is spoken and arrives the next interval; an order beyond reach goes by runner while the unit keeps its order; a unit out of earshot at delivery gets the word by runner; courier profiles speak only to the command detachment; smoothbore range, exposure (72 against the rifle's 240 at 2 hexes) and value labels; the 1775 prompt, order text and scripted text; the fire orders in the null list and the new prompt versions; telemetry records the edition and catalog; posture orders replay identically through `verify_replay`; water in a compound or gateway is refused; the seven `e165371` digests.

## Limits

- No Concord entry exists yet, so none of these rules runs in a catalog scenario.
- Officers are a count, not people. The rule cannot say who fell, and a single early volley cannot kill an officer before losses reach the step.
- Voice reach ignores noise, smoke and suppression (43 R4's `din_penalty` is not implemented).
- A holding unit's release reach (43 R2 `release_reach`) is not tied to the voice reach.
- The weapon table changes fire only. Tactical choices still use the 5-hex fire range of the standing profiles when they judge threats.
