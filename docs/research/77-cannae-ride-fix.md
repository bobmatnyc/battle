# 77 — Cannae: the horse pursues the Roman right cavalry (D34)

**Date:** 2026-11-08. **Task:** bt-T12. **Ruling:** D34 (Bob, relayed 14:22Z), Cannae ride fix option (i) of [68](68-cannae-scenario-entry.md) §9: "Horse pursues EQ while it is in view and unrouted (policy only; keeps your Dd8 Q5 view rule)." Code head `4a766e7`, base `65775a1`.

## 1. The problem

In every run of [68](68-cannae-scenario-entry.md) §6.1 Hasdrubal's ride never fired (§6.2 c). The ride waits for the Roman right cavalry EQ to be reported routed or to drop out of the Carthaginian view (Dd8 q5). The horse's opening order, a charge down the river lane to (21, 16), rode past EQ after a few volleys, so EQ was never routed and never left the view.

## 2. What changed

| Area | Change | File |
|---|---|---|
| Pursuit | Before the ride, while a contact of EQ is in the Carthaginian view and not routed, each able horse unit (HC1, HC2, HC3) is sent a `move` to EQ's reported hex. The order is sent again only when that hex changes. The view is the delivered contact list, the same input as the Dd8 q5 trigger, which is unchanged (`_horse_gone`) | `apps/poc/battle/cannae_policy.py` (`_quarry`, `_last_move`, `_pursue`, `_carthaginian`) |
| Fallback | When EQ routs or leaves the view, the existing ride and charge follow. Two existing guards would have misread a pursuit, so they changed with it: the ride order is built outside `_once`, whose one-order-per-stance check would refuse a ride `move` after a pursuit `move`; and the charge is a move off the ride hex sent at or after the ride (`_ride_turn`, `_rear_sent`), so a pursuit is not taken for the charge. With no pursuit sent, both produce the same orders as before | `apps/poc/battle/cannae_policy.py` |
| Order table | `CARTHAGINIAN_ORDERS` gains `pursue`, with its source (S65 III.116) and a `reconstruction:` label citing D34 | `apps/poc/battle/cannae_policy.py` |
| Runs script | `cannae_runs.py` reports `pursue` (per horse unit, the turns of moves off the ride hex before the ride) and counts the charge from the ride on | `apps/poc/scripts/cannae_runs.py` |
| Not changed | Engine rules (movement, combat, morale, sight, victory), the Dd8 q5 view rule, the Cannae entry data, every other scenario and its policy | — |

**Assumption.** Once the ride is sent, the pursuit ends for good: EQ coming back into view does not turn the horse round. The ruling governs the horse before the ride. The ride and charge sequence then runs unchanged.

## 3. Checks

| Test | Covers |
|---|---|
| `test_the_horse_pursues_the_roman_right_cavalry_while_it_is_in_view_and_unrouted` (new, `apps/poc/tests/test_cannae.py`) | In view and unrouted: a pursuit order per horse unit to EQ's hex, not repeated for the same hex, and sent again when the hex changes. Out of view: no pursuit; before interval 8 no horse order, after it the ride, after a pursuit too. Routed: no pursuit; the ride. After a pursuit and the ride, the charge follows the arrival. EQ seen again after the ride: no horse order |
| `test_hasdrubal_rides_only_after_the_roman_right_cavalry_leaves_the_view` (changed) | At interval 30 with EQ in view it now asserts no *ride* order, because the horse is sent a pursuit there |

**Red first.** The new test against the `65775a1` policy: 1 of 7 fails, at the in-view assertion, `[] != [{'unit_id': 'HC1', 'stance': 'move', ...}]` (`red/red-first.log`).

**Each condition can fail** (`mutations/`, one `apps/poc/battle/cannae_policy.py` change each, run by `scripts/mutate.py`): 5 of 5 turn the Cannae policy tests red.

| Mutation | Condition | Red test |
|---|---|---|
| m1-view | Out of view, pursue EQ's deployment hex | the new test, the ride test and the cavalry-delay test |
| m2-routed | A routed EQ is pursued | the new test (the ride after a rout) and the ride test |
| m3-pursuit | No pursuit (the `65775a1` behaviour) | the new test (the in-view assertion) |
| m4-charge | A pursuit counted as the charge | the new test (the charge after a pursuit) |
| m5-once-per-hex | The pursuit re-sent every decision | the new test (no repeat for the same hex) |

## 4. Gates, digests and evidence

All under the git-ignored `apps/poc/artifacts/cannae-ride-4a766e7/` in the main checkout. `MANIFEST.txt` lists every file and each gate's exit code. Each log starts with its command and ends with `EXIT=`.

| Gate | Result |
|---|---|
| `make test-poc` | `Ran 766 tests … OK` (765 at the base, plus the new test), then `smoke_ui.mjs`, map geometry, map features, route and sight; exit 0 |
| `make headless-poc` | Little Round Top: winner union, 60 turns, 2,573 events, replay `identical` (63 revisions), as in [76](76-objective-ring-and-order-wording.md) §3 |
| `make smoke-poc` | exit 0 |
| `npm test` | not run: nothing under `packages/` or `apps/web` changed (`diff-stat-web-contracts.log` is empty) |

**Digest comparison against `65775a1`** (`scripts/run_digests.sh`, with doc 74's `digests.py` copied unchanged), on `git archive` exports of both trees: every headless catalog entry, timings dropped, and desk play of the five player scenarios to the end (`run-digests.log`, `digests/`).

| Compared | Result |
|---|---|
| Desk play of Little Round Top, Hougoumont, Concord, Pegasus Bridge, Hill 223 | `cmp` exit 0 |
| Headless catalog, the 7 non-Cannae entries | `cmp` exit 0 |
| Headless catalog, `cannae-envelopment` | differs, as expected |

| `cannae-envelopment` | opening | view | played | headless | final | replay |
|---|---|---|---|---|---|---|
| base `65775a1` | `4f5f2b720e9364f2` | `b4eda1711ab85c22` | `d5a28690385984d0` | `b65c17431a09acfa` | `ad67df2539052379` | identical |
| head `4a766e7` | `4f5f2b720e9364f2` | `b4eda1711ab85c22` | `d5a28690385984d0` | `2e0e230c5dafa262` | `938378fb696ae077` | identical |

The opening, view and generic-play digests do not change: the entry data is the same, and the generic play loop does not use the Cannae policy. The headless run and its final state change because the policy now sends the pursuit.

## 5. Local measurement

One headless run of the default `cannae-envelopment`, scripted on both sides, no model, on the Mac at `4a766e7` (`measure/ride-measure.log`, `scripts/ride_measure.py`; rout turns from `scripts/routs.py`, `measure/routs.log`): 173.9 s wall, 1.80 GB peak RSS, replay `identical`.

**The horse rides.** The pursuit orders go to all three horse units at interval 3, to EQ's hex (21, 11), and again at 15, when EQ is reported at (20, 10). Horse and EQ exchange volleys on intervals 1, 3–4, 7, 9, 11–12, 19–20 and 24–29: 29 volleys, 14 involving HC1, 11 HC2 and 4 HC3. EQ loses 430 men and routs at interval 29. The ride goes at 30 to HC1 and HC3. HC2 is not sent it: it routed at 28. HC3 routs at 38. HC1 charges at 60, to (13, 13). EQ leaves by an exit at 35 with 1,170 of 1,600 men.

| Field | Head `4a766e7` (local) | Default in [68](68-cannae-scenario-entry.md) §6.1 (EVO, `d829763`) |
|---|---|---|
| Winner, end | Roman, 160 (16:00:00) | Roman, 160 (16:00:00) |
| Enclosed / lost at the deadline | 0 / 8,178 | 0 / 5,700 |
| Peak enclosed (men, turn, units) | 44,616, 53, 14 | 26,465, 56, 8 |
| Closed turn; known closed (Carth. / Roman) | 31; 25 / 33 | 36; 25 / 33 |
| Ride; charge | HC1 and HC3 at 30; HC1 at 60 | never; never |
| Exited | EQ 35 1,170 | L1 62 2,634 |
| Losses (Carth.; Roman) | 21,260/50,020; 9,362/77,200 | 21,699/50,020; 6,525/77,200 |
| Routed | A1, A5, A6, AF2, EQ, HC2, HC3, L1, LT2, NU1, NU2 | not in the §6.1 table |
| Lost units | AF2, HC2, HC3, LT2, NU1, NU2 | not in the §6.1 table |
| Events | 63,124 | 69,079 |

Enclosure peaks at 44,616 men at interval 53, above the 28,400 share, but it is 0 at the deadline, so the Romans still win at 16:00. HC2 and HC3 end lost at (16, 1), by the Carthaginian rally point. HC1 ends at (16, 10) with 1,490 of 2,170 men.

This is a smoke on one machine, not the EVO measurement.

## 6. EVO run

One measured run at `aa8789f`, scripted on both sides, no model, no spend. Command, from `apps/poc` under `/usr/bin/time -v`: `python3 scripts/cannae_runs.py --only default --dir <run>/runs`. It ran 2026-11-08 14:42:36Z to 14:48:07Z and exited 0.

| Field | Result |
|---|---|
| Pursue (HC1 to HC3) | 3 and 15 |
| Ride | HC1 30, HC3 30, HC2 none (routed 28) |
| Charge | HC1 60 |
| Routed | includes EQ, HC2, HC3 |
| `cavalry_fight` first/left | EQ 1/2, HC1 1/2, HC2 3/5, HC3 7/8 |
| Peak enclosed | 44,616 men (14 units) at 53 |
| Winner | Roman at 160 (0 enclosed, 8,178 lost, 28,400 required) |
| Losses (Carth.; Roman) | 21,260/50,020; 9,362/77,200 |
| Events | 63,124 |
| Replay | identical |
| Wall; max RSS; Python | 5:30.67; 411,860 kB; 3.14.4 |

The run matches the Mac run in every printed field. `cannae_runs.py` does not print the headless digests, so they were not compared.

Evidence: EVO run dir `bt12-aa8789f` and `apps/poc/artifacts/cannae-ride-4a766e7/evo/` (`MANIFEST.txt`; sqlite sha256 `36a9f1be`...`b7e5`).

The ride now fires, but the outcome is still a Roman win. The 14-run batch waits for the Architect.

## 7. Review notes

**code-critic on `aa8789f`: APPROVE.** No blocking findings. LOW findings, recorded, not scheduled:

- F1: no mutation log covers the ride-built-outside-`_once` guard or the `not rode` pursuit guard (suggested m6 and m7). The new test catches both by reading.
- F2: no unit test of the `scripts/cannae_runs.py` `summarise` pursue/charge split. Only the measured run checks it.

Notes:

1. With no pursuit sent the orders match `65775a1`. `_quarry` is truthy only when EQ is in the contact list and not routed. `_horse_gone` is true only when EQ is routed or absent after interval 7. They are never both true, so a pursuing decision is one where the base sent no horse order. The ride outside `_once` checks the same `_able` units in the same order and truncates as before. `_rear_sent` from `_ride_turn` matches the old set because a charge needs `rode`.
2. Neither changed guard can send a second ride or charge. Both ride branches need `not rode`, and `charged` turns true at the first move off the ride hex at or after the first ride turn.
3. The pursuit reads only the Carthaginian side's view (`engine.view(s, side)` contacts, no older than `CONTACT_MAX_AGE`), never a god-view position. This is the same input as `_horse_gone`.
4. "In view" is the side's contact list (headquarters' view), as in the kept Dd8 Q5 rule, not a per-horse sight check. Section 2 describes this.
5. A contact up to 6 intervals old counts as in view, so the horse may sit on EQ's last reported hex until it ages out; the ride then fires. If EQ stayed in view unrouted all game, the ride would never fire. The ruling allows this.
6. In the cavalry-delayed variants the delay counts from the first `hold`. A pursuit can replace the hold, and once EQ is gone the ride can go at once. This happens only in runs with a pursuit. The ruling allows it.
7. If EQ were reported on a horse unit's own `RIDE` hex, the pursuit would read as the ride. EQ starts at columns 20 to 21 and the `RIDE` hexes are at 10 to 12, so this is unlikely.
8. Only `cannae-envelopment` is digest-compared. The deserters and cavalry-delayed variants rest on note 1 and their passing tests.
9. The pursuit stops for good once the ride is sent (`not rode`; the new test's last assertion).
10. The pursuit is re-sent only on a hex change (m5). A truncated pursuit re-sends at the next decision.
11. Doc 77 matches the code and the local run (63,124 events, 173.9 s, 1.80 GB peak RSS; 766 tests OK; digests as recorded).
12. No `/Users/` paths in the diff. `# D34:` marks every change site; helpers `_last_move` and `_ride_turn` are untagged.
13. The red-first log proves only the first in-view assertion. The other conditions rest on mutations m1 to m5.

None blocks (Completion Standard fix bar); recorded, not scheduled.
