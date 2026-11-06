# 50 — Concord North Bridge: command fire release

**Date:** 2026-11-06. **Requirement:** [48 §7 item 1](48-concord-historical-orders-run.md#7-gaps-and-divergences) found that the front company released its own fire, while in the record Buttrick's order released it (S47). The owner's sequence (build handoff, step 3) asks for no fitting to known winners, held-out and sensitivity checks, and before and after results. [49](49-concord-geometry-sensitivity.md) supplies the held-out geometry cases. This document records the diagnosis, the gated engine change, the before and after runs over seven cases, and a verdict against S47.

Simulated values quote `python3 scripts/concord_fire_release.py` and `python3 scripts/concord_timeline.py` (from `apps/poc`) at commit `fb36c84`. Every run uses scripted policies only.

**Revision.** The first version (commit `a377ff8`) made the command's order open every hold-fire company in earshot by default. Its verdict found that this extra release has no source. The default now opens only the company that met the release condition (`release_scope` `hit`). The earshot reading is kept as the labelled sensitivity variant `sensitivity-earshot-release`. The a377ff8 default and its pins now belong to that variant.

## 1. Diagnosis

Line numbers are at `f250220`, before this change, and were re-checked against the source.

1. **Turn 4.** B1's first volley costs P1 no casualties, so P1 keeps holding. Under `hold_fire`, only a `casualties` event counts as being fired upon, because `warning_shots_release` is off (`engine.py:207`, `scenario_entry.py:184`).
2. **Turn 5.** The second volley takes P1's loss credit past 100. The same-interval release (`engine.py:357-360`) then fires P1 back, and `volley` marks it `returning_fire` (`engine.py:234`).
3. **The scripted side cannot act first.** It is consulted only when `turn % 3 == 0` (`services/headless.py:147`, `services/battle.py:58`), a cadence shared by every scenario. Its trigger is `strength < initial` (`concord_policy.py:92`). A voice order is ready one interval after it is sent (`comms.py:53`, `comms.py:60`; `engine.py:97-98` sets the expected turn). The policy's `open_fire` went at turn 6 and took effect at turn 7, so a scripted order can never be the first release.
4. **Information is not the cause.** `engine.view` gives the command unit P1 its true state (`engine.py:433-436`). Headquarters knew of P1's loss at turn 5.
5. **The release-on-losses rule is sourced.** It is Barrett's "unless first fired upon" (S47). Removing it would move the run further from the record.
6. **The gap.** The model had no path for a commander standing in the front company to release fire inside an interval.

## 2. The change and its layer

The change is an engine mechanic in the fire step, gated by scenario data. It changes no parameter, policy, prompt or rules edition.

- **Keys.** `FireEntry.release_by`, `unit` (default) or `command`, and `FireEntry.release_scope`, `hit` (default) or `earshot`. `build_state` writes either key into `fire_rules` only when it is not the default (`scenario_entry.OMITTED`). Every earlier `poc-13` snapshot and digest, including Little Round Top, Hougoumont and the Concord v1 runs, is therefore unchanged. `scenario_checks.fire_problems` refuses any other value of either key at registration.
- **Mechanic.** `command.release` is called from `engine.advance` only under `command`. It acts when a hold-fire unit meets the existing release condition (casualties in the previous interval, or losses in this one), and its side's command unit is operational and is that unit or within voice reach of it. The command then gives a spoken `open_fire` order:
  - under `hit`, only to that unit;
  - under `earshot`, also to every other hold-fire unit of the side within voice reach that accepts orders.

  Each order is recorded in `s['orders']` with `source` `command_release`, sent and delivered in the same interval, and acknowledged like any delivered order. `fire_posture_set` comes before the volley, so the volley is no longer `returning_fire`. A triggered unit out of reach keeps its own release.
- **Concord entries.** `concord_entry` declares `release_by` `command` with the default `hit` scope. The doc 43 variants and the doc 49 sensitivity variants, built through `geometry_entry`, inherit it. The entries are labelled `-v2` (`concord-north-bridge-v2`).
- **The earshot sensitivity.** `concord_sensitivity.earshot(entry)` returns any v2 Concord entry with `release_scope` `earshot`, an id suffixed `-sensitivity-earshot-release` and an `authored: sensitivity:` provenance note. `RELEASE_SENSITIVITY["sensitivity-earshot-release"]` is the named variant of the baseline. It is in no catalog.
- **The v1 entry.** `scenario_concord.before` rebuilds the v1 form of any Concord entry: the old fire rules, the `-v1` label and the old provenance. `CONCORD_NORTH_BRIDGE_BEFORE` keeps the old pinned digests. `CONCORD_NORTH_BRIDGE_V1` is the same entry under the id `concord-north-bridge-v1`. It is in the headless catalog and not in `PLAYER_SCENARIOS`, so a saved `concord-north-bridge-v1` game resolves through `for_state`.
- **Policies.** `concord_policy` is unchanged, so the `rebind` guard of doc 49 still covers it.

### Assumptions

Each is in the entry's provenance under `fire.release_by*` and `fire.release_scope`.

| Assumption | Label and source |
|---|---|
| Buttrick's order released the fire, after the British volley in which Davis and Hosmer fell | Sourced: S47 |
| The command rides with P1, the Acton company | Reconstruction: Buttrick and Davis at the head (S47, S48), as `provincial.command_unit` |
| The order takes effect in the interval of the volley that triggers it | Reconstruction |
| The order opens only the company that met the release condition, the one Buttrick stood in | Reconstruction: S47 does not say which other companies heard it |
| The command reaches a company within the 1775 voice reach of 2 hexes | Authored: the doc 47 assumption; no new number |
| The trigger is unchanged: casualties in a hold-fire unit; warning shots release no one | Authored, as the existing `fire` provenance |
| A company out of earshot keeps Barrett's own-release rule | Sourced: S47, "Do not fire unless first fired upon" |
| *Sensitivity only:* the order opens every hold-fire company in earshot | Authored, `sensitivity:`; no source |

## 3. The runs

Seven cases: the baseline, the three doc 43 variants and the three doc 49 sensitivity variants. Each case runs three times, each headless in its own database:

- **before:** `before(entry)`, each company releasing itself.
- **after:** the v2 entry, command release with `hit` scope. This is (a), the change of who releases P1.
- **earshot:** `earshot(entry)`, the unsourced sensitivity. Its difference from "after" is (b), the extra release.

All 21 replays report `identical`. Clock times are the scenario's 09:25:00 start plus 30 seconds a turn.

**Check against the first version.** The "after" rows equal the a377ff8 script's "attribution only" rows, which patched `command.release`. The "earshot" rows equal its "after" rows, for every case and field. The baseline earshot run also reproduces the a377ff8 run and timeline digests once its id, label and `release_scope` key are mapped back (`test_earshot_variant_reproduces_the_a377ff8_run`).

**Historical sequence** uses the event checks of doc 49 §4, with one redefinition and one addition:

- **Redefinition.** "Provincials fire only after provincial losses": the first provincial volley comes after the first British volley, in or after the interval of the first provincial casualty. Doc 49 also required the volley to be `returning_fire`, which a command release removes by design.
- **Addition.** "An order releases the first provincial fire".

### Before and after (the default)

| Case | Winner, end turn | (a) P1 released by, turn | First provincial volley | Losses, British / provincial | Historical sequence |
|---|---|---|---|---|---|
| baseline | provincial 8 → provincial 8 | itself (`returning_fire`) 5 → order O8, 5 | turn 5, 09:27:30, P1 → same | 3/96, 1/400 → same | holds → holds; the order check no → yes |
| `british-west-bank` | provincial 20 → provincial 20 | itself 3 → order O7, 3 | turn 3, 09:26:30, P1 → same | 73/96, 9/400 → 70/96, 10/400 | holds → holds; no → yes |
| `planks-lifted` | provincial 8 → provincial 8 | itself 5 → order O8, 5 | turn 5, 09:27:30, P1 → same | 3/96, 1/400 → same | holds → holds; no → yes |
| `two-companies` | provincial 8 → provincial 8 | itself 5 → order O7, 5 | turn 5, 09:27:30, P1 → same | 3/90, 2/400 → same | holds → holds; no → yes |
| `sensitivity-odd-row-bridge` | british 20 → british 20 | itself 4 → order O8, 4 | turn 4, 09:27:00, P1 → same | 10/96, 9/400 → same | breaks (no hold) → breaks; no → yes |
| `sensitivity-balanced-ring` | provincial 8 → provincial 8 | itself 5 → order O8, 5 | turn 5, 09:27:30, P1 → same | 1/96, 1/400 → same | holds → holds; no → yes |
| `sensitivity-balanced-ring-full` | provincial 9 → provincial 9 | itself 4 → order O8, 4 | turn 4, 09:27:00, P1 → same | 6/96, 3/400 → same | holds → holds; no → yes |

In six of seven cases the after run equals the before run in winner, end turn and losses. P1 releases in the same interval and fires the same volley; only the event record changes. The exception is `british-west-bank`. There, P1 already has its order at the turn 3 decision, so the policy's three-order cap sends P3's order at turn 3 by runner instead of at turn 6 by voice. P3 releases at turn 8 instead of 7. Losses move from 73/96, 9/400 to 70/96, 10/400; the winner and end turn are unchanged.

### (b) The earshot sensitivity, shown alone

"Own release" is the turn the unit first releases in the after run, by the policy's order. "Extra volleys" are the unit's volleys before that turn.

| Case | Units the earshot order opens early (opened → own release) | Extra volleys | After → earshot: winner, end turn; losses British / provincial |
|---|---|---|---|
| baseline | P2 (5 → 7), P3 (5 → 7) | P2 1 (turn 6), P3 0 | provincial 8 → 10; 3/96, 1/400 → 20/96, 2/400 |
| `british-west-bank` | P2 (3 → 4), P3 (3 → 8) | P2 0, P3 3 (turns 5 to 7) | provincial 20 → 18; 70/96, 10/400 → 70/96, 7/400 |
| `planks-lifted` | P2 (5 → 7), P3 (5 → 7) | P2 1, P3 0 | provincial 8 → 10; 3/96, 1/400 → 20/96, 2/400 |
| `two-companies` | P2 (5 → 7), P3 (5 → 7) | P2 1, P3 0 | provincial 8 → 10; 3/90, 2/400 → 20/90, 3/400 |
| `sensitivity-odd-row-bridge` | P2 (4 → 7); P3 out of reach | P2 1 (turn 5) | british 20 → 20; 10/96, 9/400 → 12/96, 9/400 |
| `sensitivity-balanced-ring` | P2 (5 → 7), P3 (5 → 7) | P2 1, P3 0 | provincial 8 → 9; 1/96, 1/400 → 6/96, 2/400 |
| `sensitivity-balanced-ring-full` | P2 (4 → 7); P3 out of reach | P2 1 | provincial 9 → 11; 6/96, 3/400 → 17/96, 4/400 |

**How the earshot release moves the baseline.** P2's one early volley at turn 6 (120 rounds) raises B1's suppression from 11 to 41. At turn 7, with P3's volley, it reaches 100. B1 decides to withdraw at turn 7, as in the after run, but stays at (13, 10). It is shot down from 29 to 12 men, routes at turn 9 and leaves the ring at turn 10. In the after run it leaves the ring at turn 7 at suppression 33 and never routes. The same pattern appears in `planks-lifted` and `two-companies` (B1 routes at turn 9) and in `sensitivity-balanced-ring-full` (routes at turn 10). In `sensitivity-balanced-ring` B1 leaves at turn 8, one turn late, without routing. These B1 positions and suppression values come from a trace of each run's states, taken at `a377ff8`, whose runs these reproduce. They are not printed by `scripts/concord_fire_release.py`.

## 4. Verdict

**The default carries only the sourced part, and it is a fidelity gain in the event record.** In every case the first provincial fire is now a delivered order from the command in P1's company, in the interval of the British volley that caused the losses. S47 says this: Buttrick's order released the fire after that volley. The battle itself is unchanged in six of seven cases: same winner, end turn and losses as before. In `british-west-bank` the winner and end turn are unchanged and losses move by 3 British and 1 provincial, through the policy's order cap. For P1 the change is a relabelling with no effect on the outcome, so it cannot have been fitted to the known winner.

**The earshot release stays a recorded, unsourced sensitivity.** Against the default it:

- raises British losses in six of seven cases (baseline 3 to 20 of 96), and leaves them at 70 of 96 in `british-west-bank`;
- changes provincial losses by at most 3 men and changes no winner (the odd-row British hold survives it);
- on the east-bank layouts delays the provincial hold by 1 or 2 turns, because the suppressed British company stays in the ring; in `british-west-bank` it brings the hold 2 turns earlier (20 to 18);
- turns B1's orderly withdrawal into a rout in four of six provincial wins. S47 records that the British withdrew toward the town. It does not say they were broken.

S47 says Buttrick's order released the fire. It does not say which companies heard it, or that the detachments behind Acton fired. The earshot reading therefore favours the provincial side in losses, moves the British withdrawal away from the record, and rests on the authored 2-hex reach. It is kept as `sensitivity-earshot-release` for comparison only, not as tuning toward the record.

## 5. Saved v1 games

The 2026-11-06 baseline archive (`apps/poc/artifacts/concord-baseline-2026-11-06`, made at `d6f1748`, read-only) was opened from temporary copies:

- **`concord-entry.db`.** The game `e56e2cfb5bda4345` has the label `concord-north-bridge-v1` and resolves through `for_state` to `concord-north-bridge-v1`. It is a provincial win at turn 8, and its replay is `identical`.
- **The three variant DBs** (`planks-lifted`, `two-companies`, `british-west-bank`). Their v1 labels do not resolve through `for_state`, and did not at `d6f1748` either: the doc 43 variants were never in a catalog. Their replays are `identical`, since replay reads only the database.

Each archive file's sha256 was the same before and after.

## 6. Tests

`apps/poc/tests/test_concord_fire_release.py` (no test asserts a winner):

- under `hit` scope, the command releases only the unit that met the release condition, by a spoken order sent and delivered that interval, and the scope is not written to the snapshot;
- under `earshot`, it also releases every hold-fire unit in voice reach, posture set before the volley;
- the earshot release from losses in the previous interval;
- a unit out of reach keeps its own release;
- `release_by` `unit` equals the default and is not written to the snapshot;
- an unknown `release_by` or `release_scope` is refused at registration;
- the Concord baseline's first provincial release is a delivered `open_fire` order from the command, not `returning_fire`, and the command releases only P1;
- `sensitivity-earshot-release` is labelled `sensitivity:`, unsourced, in no catalog, and releases P1 to P3;
- a `concord-north-bridge-v1` game built from the headless catalog saves, resolves through `for_state` and replays `identical`;
- every Concord variant inherits `command` and its `before` form validates with the v1 label.

`apps/poc/tests/test_concord_sensitivity.py`:

- `CONCORD_NORTH_BRIDGE_BEFORE` keeps the doc 49 run digest (`BEFORE_RUN_SHA256`);
- the v2 baseline (hit scope) has new pins (`AFTER_RUN_SHA256`, `AFTER_TIMELINE_SHA256`);
- the earshot variant keeps the a377ff8 pins (`EARSHOT_RUN_SHA256`, `EARSHOT_TIMELINE_SHA256`), after the id and key mapping;
- each timeline is identical under `PYTHONHASHSEED` 1 and 2.

The `poc-12` and `poc-13` Little Round Top, Hougoumont and fixture digests are unchanged.

**Probes run before each change:**

- **First round, against `f250220`.** The synthetic tests raised `TypeError: FireEntry.__init__() got an unexpected keyword argument 'release_by'`, including the error-arm test. The Concord probe failed with `'returning_fire' unexpectedly found in {... 'turn': 5, 'unit_id': 'P1'}`.
- **Second round, against `41681f0`.**
  - The `release_scope` tests, including its error arm, raised `TypeError: ... unexpected keyword argument 'release_scope'`.
  - The hit-scope test failed with `[('B1', 'delivered', 1), ('B2', 'delivered', 1)] != [('B2', 'delivered', 1)]`.
  - The Concord probe failed with `['P1', 'P2', 'P3'] != ['P1']`.
  - The earshot variant test raised `ImportError` on `RELEASE_SENSITIVITY`.
  - The v1 test raised `UnknownScenario: Unknown scenario 'concord-north-bridge-v1'`.
