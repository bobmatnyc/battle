# 79 — Cannae: why the b5a8c9f batch shows five odd results

**Date:** 2026-11-08. **Task:** bt-T15. **Basis:** the ar-T7a handoff remainder; the five open observations of [77](77-cannae-ride-fix.md) §6.1. **Approval:** Architect GO 16:17Z, time-boxed: step 1 local and read-only, step 2 at most 2 EVO runs. No EVO run was needed. Repo main `3f54974`.

No engine, policy or scenario change. No model, no spend. This is a diagnosis of data already recorded; what to change is for the owner (section 7).

## 1. Method

BatchStore keeps only the start and end snapshots, so per-interval positions are not stored. They rebuild exactly from the start snapshot plus every `unit_moved` destination and every `casualties.remaining`.

Scoring the rebuilt state with the repo's `enclosure()` reproduces every stored `victory.record` row: 14 runs × 160 intervals = 2,240 rows, 0 mismatches. The d829763 default also gives 0 mismatches. Rebuilt end positions and strengths match the end snapshot. The 14 b5a8c9f databases still match `cannae-ride-b5a8c9f/SHA256SUMS-all` (14 of 14). Every database was opened read-only.

Evidence: `apps/poc/artifacts/cannae-diag-3f54974/` (`MANIFEST.txt` lists each script and its output).

## 2. Observation 1: the peak passes the share, the deadline shows 0

**The pocket is Roman heavy units that pressed to the Carthaginian rear edge, row 0.** The Roman exits are on row 20 (`scenario_cannae.py:42`). The exploit target is `PRESS_ROW` (`scenario_cannae.py:44,121-122`); `exploit_stopped` is reached by L1 at 34, L2 37, L5 40 and so on to L4 at 68.

Walls around the pocket:

- the river (column 23) and the map edge;
- the unbroken Carthaginian line, rows 3 to 6;
- routed Carthaginian units sitting at their rally hex (16, 0) (`engine.py:379`; `rally_points` is `CARTHAGINIAN_HQ` (16, 0), `scenario_cannae.py:43`);
- their zone of control.

Routed units count as walls because `_live` excludes only lost or merged units (`victory_encircle.py:135-136,220`). At t53 NU1 (routed) is at (16, 0), HC2 (routed) at (16, 1) and AF2 at (12, 1).

The exits are never cut: open exits 3 and narrowest gap 3 or more at every interval in all 14 runs.

**Why the pocket opens.** Default, by turn: pocket units, then the single change that re-closes it if reverted.

| Turn | Pocket units | Change |
|---|---|---|
| 57 | 14 to 13 | A1 (routed 56) rout move |
| 61 | 13 to 12 | A6 (routed 55) rout move |
| 62 | 12 to 7 | AF2 (routed 57) moves (12, 1) to (13, 2), freeing A2, A3, L2, L3, L4 |
| 66 | | NU1 destroyed |
| 69 | | A5 (routed 65) rout move |
| 94 | | AF2 destroyed |
| 116 | 6 to 0 | HC3 (routed 38, at (16, 1)) destroyed |

The routed blockers are shot down by the enclosed Romans and do not fire back: HC3 on 109 to 116 by L4 and L5; AF2 on 88 to 94 by A3, L3 and L4; NU1 on 60 to 66 by L3.

The other five runs follow the same pattern. In cavalry-delayed-20 and -40 the pocket releases when C1 (99) and HC1 (112 and 119) are lost. The d829763 pocket has the same geometry and opens when AF2 (102) and AF1 (117) are lost.

**Not Carthaginian policy.** There is one transient opening, at t33, when HC1 and HC3 ride; L6 is enclosed again at 34. The charge at 60 is never a cause.

**Not an unrouted Roman breakout.** Every Roman unit that left the pocket on its own move had routed, except A4 at 97, which was shaken.

**The share is held for long stretches.** Intervals where enclosed plus lost men reach 28,400:

| Run | Intervals | Longest run |
|---|---|---|
| default | 53 | 51 consecutive (43 to 93) |
| deserters | 62 | 51 consecutive (43 to 93) |
| cavalry-delayed-10 | 35 | 24 |
| cavalry-delayed-20 | 36 | 19 |
| cavalry-delayed-40 | 34 | 20 |
| one-wing-fixed-af1 | 9 | 5 |

The rule scores enclosure only at interval 160 (`victory_encircle.py:238-244`; rule in [63](63-cannae-scenario-plan.md) line 166), so none of this counts.

## 3. Observation 2: `zoc-0` plays the default battle

`zoc-0` is the same battle as default: 63,124 events in each, 0 differing rows, the same event-stream sha256 prefix `29364be2`, identical start and end states. The d829763 pair is also identical (69,079 events, 0 differing).

`zoc` is read only by the measure (`victory_encircle.py:210,221`); `s['victory']` is in neither side's view. Rescoring the `zoc-0` database at zoc 1 reproduces default's record. The 0@1 in the batch table is the measure at zoc 0, not a different battle.

At zoc 0 only occupied hexes block (the `_blocked` loop runs zero times, `victory_encircle.py:35-41`). The Carthaginian line has one-hex gaps. At t53 all 14 units enclosed at zoc 1 have zoc-0 paths to an exit through columns 13, 17 or 20, rows 3 to 6.

## 4. Observation 3: `aemilius-commands` loses its command at interval 20

The variant sets `command="EQ"` (`scenario_cannae.py:363-364`). A routed command unit makes the side non-operational (`comms.py:45-48`), and `_roman` then returns no orders (`cannae_policy.py:158-159`).

EQ routs at t20. The heavy advance is due at the first decision at or after turn 20 (`cannae_policy.py:163`), which is t21 in default. By then the Romans send only V1 to V4, at 12 and 15: 4 orders against 20 in default. All 16 heavy units end on their start hexes and nothing is enclosed.

Roman losses of 1,836 are heavy 684 (all from the horse), velites 567 and cavalry 585. In d829763 EQ never routed and the advance went out at 21 to 36 (7,439 losses).

EQ routs earlier in this run than in default (20 against 29). The first divergence is t14. Velite orders carried from EQ's hex (21, 11) arrive at 15 to 17 instead of 13 to 15. At t14 EQ's withdrawal reports "No safer adjacent ground" and it takes an HC1 rear volley. Morale fails at 15; it withdraws to (20, 9), then (20, 8) into frontal fire from C1 and C2, and routs at 20.

Which hex was unavailable at t14 is an inference: `local_decision` does not log withdrawal candidates. It does not change the explanation.

## 5. Observation 4: only HC1 rides in the cavalry-delayed runs

HC2 routs at 28 and HC3 at 37 in all three runs, before the delayed rides at 42, 51 and 72. Rides go only to `_able` units (`cannae_policy.py:108-110,227-228`).

The delay's hold goes to HC1 only (`cannae_policy.py:224`, sent at 30). The idle HC3 is routed at (18, 8) by L6 and L7.

A charge needs a horse unit within 1 hex of its ride hex (`cannae_policy.py:230-236`):

- `-10`: HC1 routs at 45, at (15, 6), before it arrives.
- `-20`: HC1 rides from about (18, 4), never leaves rows 2 to 6, and routs at 71.
- `-40`: HC1 reaches (11, 13) at 79 and charges at 84.

In default the ride at 30 catches HC1 and HC3 (HC2 had already routed). HC3 routs on the way at 38.

## 6. Observation 5: Roman losses are higher than in doc 68

The only Cannae-affecting change from d829763 to b5a8c9f is `cannae_policy.py`. The first divergence is t9, after the t3 pursuit. Firer shares below are approximate: each casualty event is split over that interval's volleys by exposure.

**Default: +2,837 (6,525 to 9,362).**

- Horse fire +1,281 (130 to 1,411): 948 before the ride, 372 from ride to charge, 92 after.
- AF and C fire +1,504. Roman heavy fire shifts to the horse and light troops (4,626 and 3,078 men, against 53 and 509). Only 2,903 men fall to C (6,884 before) and 6,044 to AF (10,000 before).
- No C unit routs (d829763: C8 at 45, C7 at 49, AF1 at 71), so C keeps firing, and C's fire on Roman heavy rises from 1,682 to 3,105.
- Light troops +53.

**Other runs.** The horse term is +944 to +1,429 in 13 of the 14 runs; `roman-reserve` is the exception at +195, because its d829763 horse fire was already 910. Post-charge horse fire is 150 men or fewer. `roman-horse-holds` is +38: horse +958, AF/C -814, light troops -107. `aemilius-commands` is -5,603 (no advance, section 4).

## 7. Owner questions

Options only. No recommendation, nothing built.

**Q1. When is enclosure scored?**

- (a) At the deadline only (now).
- (b) At the peak, at any interval.
- (c) Sustained for N consecutive intervals (default held 51).

**Q2. Does a routed, non-firing unit count as a wall?**

- (a) Yes (now, `victory_encircle.py:220`).
- (b) No: drop INEFFECTIVE enemies from the blockers.

**Q3. Is a Roman unit at the Carthaginian map edge enclosed or broken through?**

- (a) Enclosed (now).
- (b) Count only units cut off behind the Roman line.
- (c) Treat the row-0 edge as an exit.

**Q4. `aemilius-commands` tests losing command when EQ routs.**

- (a) Keep it.
- (b) Add command succession.
- (c) Put the command detachment on a non-fighting unit.

**Q5. `cavalry-delayed`.**

- (a) Hold HC1 only (now).
- (b) Hold all three.

## 8. Review notes

Pending PM.
