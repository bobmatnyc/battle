# 59 — Surrender and captives, gun facing, raid-and-return, 1918 communications

**Date:** 2026-11-06. **Requirement:** the remaining Hill 223 engine must-haves of [56](56-hill-223-scenario-plan.md) §10 (gaps 2, 3, 5 and 6); gaps 1 and 4 shipped in [58](58-small-unit-rout-and-open-assault.md). This doc covers engine work and test fixtures only. No Hill 223 entry is added, and no player, timing, strength or variant is chosen: those wait on the owner. No existing entry declares any key or field below.

Labels follow [52](52-pegasus-bridge-scenario-plan.md): **sourced**, **inferred**, **reconstruction**, **authored**. Every value in this doc and its tests is authored. A future entry supplies its own values and labels them.

## 1. Surrender and captives (`surrender`; `battle/captives.py`)

- **Rule.** A unit override `surrender` holds four fields: `reach` (1 to 7 hexes), `odds_pct` (1 to 1000), `support_reach` (0 to 7) and `rear_only` (a boolean). At each interval, before local decisions, a live declaring unit yields when:
  - *believed enemy* ≥ `odds_pct` % of (*own strength* + *support*), where
  - *believed enemy* is the sum of the high ends of the strength estimates (`recon.estimate`) of the enemies the unit sees within `reach`. With `rear_only`, only enemies outside the unit's declared arc (§2) count.
  - *support* is the strength of the effective friendly units it sees within `support_reach`.
- **Simultaneity.** All decisions in an interval are taken from one state before any is applied, so id order cannot matter. A unit that loses support when a neighbour yields decides again at the next interval.
- **Effect.** The nearest counted enemy (lowest id on a tie) becomes the holder. The yielding unit's whole strength becomes one record in `s['captives']`: `id`, `count`, `from_unit`, `from_side`, `holder_id`, `holder_side`, `turn`, `status` `held`. The unit is `lost`, strength 0, with `surrendered: true`. The holder's `captives` field carries the count. Event `unit_surrendered`.
- **Reporting.** The holder sends `"<holder>: <n> prisoners taken from <unit>."` to its headquarters by the ordinary report transport (kind `captives`). Its friendly report also carries `captives`. Headquarters learns of the captives only when a report arrives. The yielding side is not told. The God view shows the whole account.
- **Escape.** When the holder routs or is lost, its captives go free (`status` `escaped`, `escaped_turn`, event `captives_escaped`). They leave the account and do not become a unit again.
- **Conservation.** At every interval, the yielding unit's strength plus the captives taken from it equals its strength before it yielded. Captives are never created.
- **Observer basis.** The decision reads only the unit's own sightings (`recon.scan`, which applies `recon.sees`) and the friends it sees. `test_an_enemy_the_unit_cannot_observe_does_not_change_the_decision` builds two states that differ only in an 80-man party within reach but beyond a 1-hex sight. Both states give no surrender, and the same party, once seen, causes it. A trial mutation that read every true enemy turned six tests red. The friends' strengths are read from truth, because a unit sees its neighbours directly. That is an authored simplification.
- **Mapping to doc 56.** G1 (yield on perceived envelopment) is a wide `reach` with `rear_only`. G2 (yield only under direct threat) is `reach` 1. Both are **inferred** readings of S57 and S40. The high-end estimate stands for S57's "supposing … a large American force". This is **authored**: no source gives a threshold.

## 2. Gun facing and reorientation delay (`facing`, `arc`, `reorient_turns`; `battle/facing.py`)

- **Rule.** A unit that declares all three keys fires only at enemies whose bearing from it lies inside its arc. `facing` is whole degrees clockwise from map north (up the map), 0 to 359. `arc` is the full width, 1 to 359. `reorient_turns` is 0 or more.
- **Turning.** Every interval, after movement and before fire, each live, unrouted facing unit is checked (`facing.progress`), whatever its fire posture. If it sees enemies within reach and none inside its arc, it starts to turn toward the nearest one (`gun_reorienting`, with `ready_turn`). It fires at nothing until `ready_turn`. Then the bearing becomes its new facing (`gun_reoriented`). With a delay of 0 it turns and fires in the same interval. After the turn, the old front is outside the arc.
- **Hold fire.** Turning never fires and never changes `fire_posture`, so a `hold_fire` gun still opens fire only under the [46](46-poc13-river-and-fire-discipline.md) and [50](50-concord-command-fire-release.md) release rules. A held gun turns while it holds. Once released after its delay has passed, it fires at once into its new front (`test_a_held_gun_turns_while_holding_its_fire`, `test_a_held_gun_released_after_the_delay_fires_at_once`, `test_a_held_gun_does_not_fire_before_release`). Before the fix round on `aa93b44`, turning started only inside a volley, so a held gun gave a rear party `reorient_turns` free intervals after release.
- **Observer basis.** `engine.in_reach` passes only enemies the unit sees within reach, to both the turn and the volley. `test_an_enemy_the_gun_cannot_see_does_not_start_a_turn` holds the facing when the rear party is beyond sight.
- **Unchanged.** Without the keys, `facing.targets` returns every enemy and `engine.volley` fires as before. Local tactics (`tactics_v10`, `tactics_v11`) ignore facing.
- **Source need.** S40: the guns were "masked and the muzzles pointed down into the valley", and the gunners were "rapidly turning them around". The delay value is **authored** (doc 56 variant `gun-turn-delay`: 1, 2, 4).

## 3. Victory kind `raid-and-return` (`battle/victory.py`)

- **Fields** (`VictoryEntry`): `raiders` (attacker unit ids), `return_hex`, `return_radius`, exactly one of `return_strength` (men) or `return_pct` (per cent of the raiders' starting strength, rounded up), and `min_captives` (None means captives are not counted; a value is refused unless some unit of a side other than the attacker declares `surrender`, since only a yielding unit makes captives, bt-T02). The kind reuses `objective`, `radius`, `hold_turns`, `objective_name` and `deadline_turns`.
- **Rule.** The raid is made when an effective raider has stood within `radius` of the objective for `hold_turns` consecutive intervals (`raided_turn`). The attacker wins at a later interval when two things hold. The effective raiders within `return_radius` of `return_hex` must number at least the needed men. With `min_captives` set, they must also hold at least that many `held` captives. The defender wins when no raider is effective, or at the deadline.
- **Scope.** Other kinds refuse every raid field. `raid-and-return` refuses `relief_turn` and `more_objectives`.
- **Truth and view.** The score reads true positions, strengths and the captive account, as the other kinds do. `s['victory']` is in no side's view (`test_nothing_of_the_raid_state_reaches_either_view`). A mutation that put it in the view turned that test red.
- **Not included.** Doc 56 §5(b), "no effective gun group fires", is not part of the kind. It can be scored as a metric.

## 4. 1918 communications and voice

- **Profile `wwi-1918-voice-runner-v1`** (`comms.WWI`). Voice and runner at the 1863 courier rates, with no radio. The profile has no reach of its own. An entry that names it must declare `ScenarioEntry.voice_reach` (an integer of 0 or more). `build_state` writes the value to each side's `s['commanders']` record, and `command.voice_reach` reads it first. Every other profile refuses `voice_reach`. The prompt's transport line states the declared reach. Doc 56 proposes reach 1. That value is **authored** and belongs to the entry.
- **Voice `wwi-1918-en-v1`** (`presentation`). Plain American infantry wording for the AEF in France in 1918. It states that word goes by voice or runner. It adds display-only order words and a prisoners line (`captives.taken`). The stored dispatch text, events and replay inputs are unchanged. All wording is **authored** and quotes no historical message. The address is "Sir", because the player's rank (doc 56 open question 1) is not chosen.

## 5. Rules edition and gating

The work stays in `poc-13`, as in 53, 55 and 58. Every rule reads a unit key, victory kind or entry field that only a new entry writes, and no saved `poc-13` game holds one. `build_state` refuses `surrender` and the facing keys before `poc-13` (`scenario_units.declares`), and refuses the 1918 profile there too (`scenario_command.declares`). From the fix round on `aa93b44`, `scenario_units.declares` also refuses the `seize-and-hold` and `raid-and-return` victory kinds before `poc-13`. Before, an entry with a `poc-12` label built a `poc-12` snapshot naming either kind, which `engine_v12` then scored (`test_an_edition_before_poc_13_refuses_the_poc_13_victory_kinds`). A unit that declares `surrender` or a facing, or that holds captives, neither splits nor combines (`formations`), as in 58. The victory kind inventory test gains the new kind, as for earlier kinds. No pinned digest was edited. The Little Round Top, Hougoumont, Concord and Pegasus headless runs and replays are unchanged: union 60 turns, 2573 events; allied 60, 2350; provincial 8, 569; german 5, 306; all replays `identical`.

## 6. Tests

All tests were written first and run red (import or field errors before each module existed):

- `apps/poc/tests/test_gun_facing.py`
- `apps/poc/tests/test_surrender.py`
- `apps/poc/tests/test_raid_and_return.py`
- `apps/poc/tests/test_wwi_comms.py`

The fixtures are the synthetic 1944 flat-ground entries of `test_pegasus_engine`. Mutation checks also ran:

- Stubbing `facing.targets` turned three facing tests red.
- Reading enemy truth in `captives._yields` turned six surrender tests red.
- Applying surrender decisions one at a time turned `test_decisions_in_one_interval_are_taken_together` red.
- Exposing `s['victory']` in the view turned the view test red.

## 7. Limits

- A whole unit yields. There is no partial surrender, no guard detail, and no slowing of a unit that holds captives. Prisoners are not a fire shield (doc 56 "later": the `shield` variant).
- A surrendered unit never reports its own fate. Its headquarters sees only that it stops reporting.
- Captives that escape leave the account. They do not rejoin their side.
- Facing affects fire only, not observation or tactics. A routed unit does not turn.
- Bearings come from rounded floating-point angles between hex centres. They are deterministic on one platform, and arc edges are inclusive.
- `voice_reach` is one value for every side of the entry.
- No Hill 223 entry, scripted control or variant exists. Its values, player side and timings remain owner decisions (doc 56 §9).
