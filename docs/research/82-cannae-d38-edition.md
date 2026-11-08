# 82 — Cannae: the cannae-d38 rules edition (D38)

**Date:** 2026-11-08. **Task:** bt-T19. **Ruling:** D38 (Bob, 2026-11-08 17:41Z), on the five owner questions of [79](79-cannae-observations-diagnosis.md) §7. **Base:** main `d4e3ac7`. **Branch:** `bt-t19-d38-cannae-edition`.

No model, no spend, no EVO run. The PM has local-ops run one measured EVO run per change afterwards (section 7).

## 1. The rules as adopted

| Question | D38 ruling | Commit |
|---|---|---|
| Q1 | Score a sustained encirclement: the enclosure counts once held for 20 consecutive intervals, not only at the deadline. | `5689adb` |
| Q2 | A routed, non-firing (INEFFECTIVE) unit no longer counts as a wall or blocker. | `44c1979` |
| Q3 | A Roman unit that reaches the Carthaginian rear (row-0) map edge has broken through, not been enclosed. | `d295f6a` |
| Q4 | Keep `aemilius-commands` as is. | no change |
| Q5 | The cavalry-delayed variant holds all three horse units, not HC1 only. | `3629656` |

The commits follow the asked order, Q2, Q3, Q1, Q5. No dependency forced another order. Each commit is cumulative.

## 2. The edition

**Edition id:** `cannae-d38`.

An entry opts in through `VictoryEntry.edition`. `Encircle.setup` then writes `edition` (and Q3's `broke_through` record) into `s['victory']`. Every D38 rule tests that key. A snapshot without it scores exactly as before, so every game recorded before this edition replays under the old rules.

Q5 is a scripted-control change, so it ships as new control ids: `scripted-cannae-carthaginian-cavalry-delay-{10,20,40}-v2`. The v1 ids stay registered. A replay re-applies the recorded orders and never re-runs a control, so the control version cannot move an old replay.

Every Cannae entry opts in: the default and all 13 variants. Their snapshot label becomes `-v2` (for example `cannae-envelopment-v2`), and their provenance gains a `victory.edition` line. `cannae_entry(..., edition=None)` still builds the old-edition entry, with the `-v1` label. Its opening snapshot is byte-identical to `d4e3ac7` (`test_the_old_edition_entry_builds_the_d4e3ac7_opening`).

**Why not `poc-14`.** A new `poc-14` would touch every `rules in (...)` check in the engine for a change that only the Cannae entries use. The repo already ships opt-in rules inside `poc-13` this way: `tactics_v11` ([55](55-tactics-v11-threat-range.md) §3), and the `seize-and-hold`, `raid-and-return`, `recover-force` and `encircle` kinds (`victory.py` module doc). An entry that names the feature writes it into the snapshot, and only that snapshot is scored by it.

No non-Cannae scenario changed. The `edition` field is refused on every other victory kind (`test_an_unknown_edition_and_the_field_on_another_kind_are_refused`).

## 3. Readings and deviations

Each rule needed one or more readings in code. Each takes the reading closest to doc 79 §7's option text.

1. **Q2, "routed, non-firing (INEFFECTIVE)".** INEFFECTIVE is `victory.INEFFECTIVE`: routed, lost and merged. Lost and merged units were already no wall (`_live`), so the change drops routed defenders from the blockers (`_wall`). The same rule applies to the headquarters' reading (`known_closed_turn`, recorded only): an attacker's contact reported `routed` is no wall there either.
2. **Q3 follows option (c), "treat the row-0 edge as an exit", and adds one clause.** Under the edition, every hex of row 0 is an exit for the enclosure measure (`_measure`). Option (c) alone still encloses a unit that stands on row 0 when its own hex and all its neighbours lie in a Carthaginian zone of control. The adopted text says such a unit "has broken through", so a pocket unit on row 0 is never enclosed. This clause is a deviation from the bare option text.
3. **Q3 changes two recorded columns.** `record`'s open exits and narrowest passage now count the row-0 exits too, so default reads 26 and 22 where it read 3 and 3. `exited` still lists only the three camp exits.
4. **Q3 records, but does not score, the breakthrough.** `broke_through` holds each pocket unit's first interval and men on row 0. A breakthrough neither ends the battle nor wins it; the ruling says only "not enclosed".
5. **Q1, "interval".** One interval is one scoring call, 180 s of battle, one `record` row. The 20 rows must be consecutive turns.
6. **Q1, "held".** Held means enclosed men plus lost men reach the share (28,400). That is the quantity the deadline test reads, and the one doc 79 §2 tabulates. The enclosure is the Q2 and Q3 measure.
7. **Q1, "counts".** The defender wins at once at the 20th consecutive interval, as the centre break wins at once. The other reading, a defender win recorded at the deadline, is not built. With the share held, the centre break cannot win (Dd8, `BREAK_ONLY_BELOW_SHARE`), so the two rules never compete.
8. **Q5, "holds all three".** The v2 controls send the hold to every able horse unit (HC1, HC2, HC3). A hold that the three-orders-a-decision cap leaves out is sent at a later decision within the delay. The delay counts from the first hold. A routed horse unit is not able and gets no hold, as before.
9. **`scripts/cannae_runs.py`** now prints `edition` and `broke_through`, so an EVO row shows the edition it ran under.

## 4. Files changed

| File | Change | Commits |
|---|---|---|
| `apps/poc/battle/victory_encircle.py` | `D38`, `EDITIONS`, `REAR_EDGE_ROW`, `SUSTAIN_INTERVALS`; `_wall` (Q2), `_measure` (Q3), `_sustained` (Q1); edition check in `problems`; opt-in keys in `setup` | Q2, Q3, Q1 |
| `apps/poc/battle/scenario_entry.py` | `VictoryEntry.edition` | Q2 |
| `apps/poc/battle/scenario_cannae.py` | `cannae_entry(edition=D38)`, the `-v2` label, the provenance line; `cavalry_delay_policy(delay, version)`; the variants use v2 | Q2, Q3, Q1, Q5 |
| `apps/poc/battle/cannae_policy.py` | `_carthaginian(hold_all=...)`; v1 and v2 delay controls registered | Q5 |
| `apps/poc/scripts/cannae_runs.py` | prints `edition` and `broke_through` | Q3 |
| `apps/poc/tests/test_cannae_d38.py` | new: edition, Q2, Q3, Q1, Q5 tests (11) | all |
| `apps/poc/tests/test_cannae.py` | the `-v2` label, the v2 delay id, the runs-script row | Q2, Q3, Q5 |

Code: +333 / −32 lines (`git diff --stat d4e3ac7 3629656`).

## 5. Checks per commit

Gates ran in the worktree, in the foreground, each with its own exit code. `make test-poc` is the Python suite followed by the four JavaScript checks. The TS desk was not run: nothing under `apps/web` or `packages/` changed, and no TS desk code reads a Cannae view (its only Cannae data is the map-features fixture, which this edition does not touch).

| Commit | `make test-poc` | `make headless-poc` | `make smoke-poc` |
|---|---|---|---|
| base `d4e3ac7` | Python suite only: `Ran 797 tests … OK` | — | — |
| Q2 `44c1979` | `Ran 802 tests … OK`, exit 0 | exit 0 | exit 0 |
| Q3 `d295f6a` | `Ran 804 tests … OK`, exit 0 | exit 0 | exit 0 |
| Q1 `5689adb` | `Ran 806 tests … OK`, exit 0 | exit 0 | exit 0 |
| Q5 `3629656` | `Ran 808 tests … OK`, exit 0 | exit 0 | exit 0 |

The first Q2 suite run, before the commit, failed four CLI tests: `scenario_cannae` imported `victory_encircle` and closed an import cycle through `victory`. The edition id is now spelt in `scenario_cannae` as well, and `test_every_cannae_entry_opts_into_the_d38_edition` checks it equals `victory_encircle.D38`.

`make headless-poc` printed the same Little Round Top line at every commit: winner union, 60 turns, 2,573 events, replay `identical` (63 revisions).

**Red first.** Each commit's new tests ran against the previous commit's tree (a `git archive` export) and failed there:

| Commit | Red run on | Result |
|---|---|---|
| Q2 | `d4e3ac7` | the module fails to import: `cannot import name 'D38'` (the edition does not exist) |
| Q3 | `44c1979` | 2 of 7 fail: `1 != 0` (L1 on row 0 enclosed; L1 with a path to row 0 enclosed) |
| Q1 | `d295f6a` | 2 of 9 fail: `(None, None) != ('carthaginian', 'The Roman army was enclosed for 20 consecutive intervals…')` |
| Q5 | `5689adb` | 4 of 11 fail (one per delay, and the late-hold test): only HC1 is held |

The Q2 red is an import failure, not an assertion. Mutation q2-m1 below shows the Q2 assertion itself turns red.

**Mutations** (`python3 -B`, one change to a copy of the tree, the named tests run):

| Mutation | Change | Red tests |
|---|---|---|
| q2-m1 | `_wall` ignores the edition: a routed unit is a wall again | `test_q2_a_routed_defender_is_no_longer_a_wall` |
| q3-m1 | no row-0 exits | `test_q3_a_path_to_the_rear_edge_is_a_way_out` |
| q3-m2 | a unit on row 0 can be enclosed | `test_q3_a_unit_on_the_rear_edge_has_broken_through` |
| q1-m1 | any 20 held intervals, not consecutive | `test_q1_a_break_in_the_share_starts_the_count_again` |
| q1-m2 | 19 intervals | both Q1 tests |
| q5-m1 | v2 holds HC1 only | both Q5 tests (3 subtests and the late hold) |
| q5-m2 | v1 holds all three | `test_a_cavalry_delay_holds_the_ride_for_its_intervals` (v1 unchanged) |
| q5-m3 | no later hold for a unit the cap left out | `test_q5_a_hold_left_out_is_sent_later_and_the_delay_counts_from_the_first` |

**Digests against `d4e3ac7`.** Doc 74's `digests.py`, copied unchanged from `fords-labels-29cfd3e`, ran on a `git archive` export of each commit and of the base, as doc 76's `run_digests.sh` does: every headless catalog entry (timings dropped) and desk play of the five player scenarios to the end.

| Commit | Desk play, 5 scenarios | Headless catalog, 7 non-Cannae entries | `cannae-envelopment` |
|---|---|---|---|
| Q2 `44c1979` | `cmp` exit 0 | `cmp` exit 0 | differs, as expected |
| Q3 `d295f6a` | `cmp` exit 0 | `cmp` exit 0 | differs, as expected |
| Q1 `5689adb` | `cmp` exit 0 | `cmp` exit 0 | differs, as expected |
| Q5 `3629656` | `cmp` exit 0 | `cmp` exit 0 | differs, as expected |

| `cannae-envelopment` | opening | view | played | headless | final |
|---|---|---|---|---|---|
| base `d4e3ac7` | `4f5f2b720e9364f2` | `b4eda1711ab85c22` | `d5a28690385984d0` | `2e0e230c5dafa262` | `938378fb696ae077` |
| Q2 `44c1979` | `3f005ecaf841a3ae` | `b4eda1711ab85c22` | `25684372e41e7eda` | `067346b51867f18f` | `553a6f73533fbfbb` |
| Q3, Q1, Q5 | `204438410fe31f3a` | `b4eda1711ab85c22` | `c9615b8a349c1534` | `067346b51867f18f` | `7201bdc7856c6021` |

The headless digest moves only because the label is `-v2`: winner, turns, events and strengths are the same battle. Q1 leaves the Q3 digests unchanged, because the share is never held in default after Q2 and Q3 (section 6). Q5 leaves them unchanged too: the default uses no delay control.

**Old Cannae replays.** The default and `cavalry-delayed-20` games recorded by `d4e3ac7` (labels `-v1`, no `edition` key) replay `identical` (169 revisions, 160 turns) under each of the four commits. The check can fail: with Q2 applied whatever the edition, the default replay diverges at revision 33.

## 6. Local results per commit

One local game per commit, scripted on both sides, no model, on the Mac, through `cannae_runs.run` (the EVO script's own path). Share: 28,400 men (enclosed plus lost).

| Run | Winner, end | Peak enclosed men@turn (units) | Intervals at the share | Longest run at the share | Broke through | Wall; max RSS |
|---|---|---|---|---|---|---|
| default, base `d4e3ac7` | Roman, 160 | 44,616@53 (14) | 53 | 51 (43 to 93) | — | 154.5 s |
| default, Q2 `44c1979` | Roman, 160 | 44,616@53 (14) | 14 | 14 (43 to 56) | — | 156.1 s; 1.45 GB |
| default, Q3 `d295f6a` | Roman, 160 | 6,901@32 (2) | 0 | 0 | 9 units, L1 first at 33 | 158.0 s; 1.52 GB |
| default, Q1 `5689adb` | Roman, 160 | 6,901@32 (2) | 0 | 0 | 9 units, L1 first at 33 | 199.9 s; 1.69 GB |
| cavalry-delayed-20, base `d4e3ac7` | Roman, 160 | 32,490@46 (10) | 36 | 19 | — | 162.8 s |
| cavalry-delayed-20, Q1 `5689adb` | Roman, 160 | 6,938@32 (2) | 0 | 0 | 8 units | 157.8 s; 1.47 GB |
| cavalry-delayed-20, Q5 `3629656` | Roman, 160 | 6,938@32 (2) | 0 | 0 | 8 units | 158.0 s; 1.55 GB |

Every run's replay is `identical`. Roman losses are 9,362 in every default run and 8,536 in every cavalry-delayed-20 run. Q2, Q3 and Q1 change scoring only, so the battle itself is the same.

**Q2.** Peak enclosure is unchanged, because the routed Carthaginians at (16, 0) and (16, 1) are not what closes the pocket at 53. The share now holds 14 intervals, not 53: the pocket opens once the walls around it rout.

**Q3.** The pocket of doc 79 §2 is gone. Nine heavy units reach row 0, L1 first at 33 with 3,397 men, and none of them counts as enclosed. The largest enclosure left is 6,901 men at 32, before the press reaches the edge.

**Q1.** No change in default. After Q2 the longest run at the share is 14 intervals, and after Q3 it is 0, so 20 consecutive intervals never occur. Inference from the base record: under the old walls and the old edge, default held the share from 43 to 93, so Q1 alone would have given the Carthaginians the battle at interval 62.

**Q5.** The hold at 30 now goes to HC1 and HC3; HC2 had routed at 28 and is not able. HC3's hold arrives at 32, but HC3 still routs at 37, before the ride at 51. The ride again goes to HC1 alone, and it does not charge. The battle gains 10 events (60,337 against 60,327); losses and the outcome are unchanged.

## 7. EVO run per commit

One measured run per change, scripted on both sides, no model, no spend. Method: doc 77 §6.1. Export the commit with `git archive`, run under `/usr/bin/time -v`, keep the database, then read the share runs and breakthroughs from it. The load guard of doc 77 §6.1 applies (wait while the 15-minute load is above 28 or MemAvailable is below 10 GB).

`REPO` is local-ops' clone of `bobmatnyc/battle` with the branch fetched. Each block runs from a fresh empty directory. The archive sha256 values are from `git archive <sha> | shasum -a 256` on the Mac; a different git version may produce a different tarball, so treat a mismatch as a note, not a failure.

| Change | Commit | Run | Archive sha256 |
|---|---|---|---|
| Q2 | `44c1979255f9d624a37b2474ab53c89dc84952ec` | `default` | `a7926a395e48503f0093a67cbb55858c45df864af8019d9b29e33f73767501e3` |
| Q3 | `d295f6a5dcc3a4d78174363a4de423f1ec620c6a` | `default` | `10cbdd4649adb4befb3e729204cc9cf0d52674a86fbfef39895e5216b8e866ef` |
| Q1 | `5689adbd0f315f7c844375f315149318866536b6` | `default` | `a538db2c3a5fce96687b704f67411f56aa2ab8a3c35e1093ef46d21ba9136e25` |
| Q5 | `36296569c350b955e4d04530085035ee8a6dfc5e` | `cavalry-delayed-20` | `004c6fcb0ccca46128ce07be573f29a30962f465aeea97d8e12fc12958574a73` |

The command, with `SHA`, `RUN` and `DIR` set per row (`DIR` is `bt19-q2-44c1979`, `bt19-q3-d295f6a`, `bt19-q1-5689adb` or `bt19-q5-3629656`):

```sh
mkdir -p "$DIR/src" "$DIR/runs"
git -C "$REPO" archive "$SHA" > "$DIR/src.tar"
shasum -a 256 "$DIR/src.tar" > "$DIR/src.sha256"
tar -x -C "$DIR/src" -f "$DIR/src.tar"
cd "$DIR/src/apps/poc"
/usr/bin/time -v -o "../../../time-$RUN.txt" python3 scripts/cannae_runs.py --only "$RUN" --dir ../../../runs \
  > "../../../$RUN.jsonl" 2> "../../../$RUN.err"; echo "EXIT=$?" >> "../../../$RUN.err"
python3 -c 'import itertools,json,sqlite3,sys; s=json.loads(sqlite3.connect(sys.argv[1]).execute("select state from games").fetchone()[0]); v=s["victory"]; n=v["enclosed_needed"]; runs=[len(list(g)) for k,g in itertools.groupby(v["record"], key=lambda r: r[2]+r[3]>=n) if k]; print(json.dumps({"edition": v.get("edition"), "winner": s["winner"], "turn": s["turn"], "share_intervals": sum(runs), "longest_share_run": max(runs, default=0), "broke_through": v.get("broke_through"), "horse_holds": sorted([o["unit_id"], o["sent_turn"]] for o in s["orders"] if o["stance"] == "hold" and o["unit_id"] in ("HC1", "HC2", "HC3"))}))' \
  "../../../runs/cannae-$RUN.sqlite" > "../../../$RUN-share.json"
```

The last step reads only the stored final state, so it needs no battle code. Expected, from section 6:

| Change | Expected fields (`$RUN.jsonl`, then `$RUN-share.json`) |
|---|---|
| Q2 | winner `roman`, turn 160, peak 44,616@53, 63,124 events; `share_intervals` 14, `longest_share_run` 14 |
| Q3 | winner `roman`, turn 160, peak 6,901@32; `broke_through` 9 units, L1 `[33, 3397]`; `share_intervals` 0 |
| Q1 | as Q3: Q1 does not fire in default |
| Q5 | winner `roman`, turn 160; ride HC1 51, no charge; 60,337 events; `horse_holds` `[["HC1", 30], ["HC3", 30]]` |

## 8. Evidence

Git-ignored, under `apps/poc/artifacts/cannae-d38/` in the task worktree, copied to the same path in the main checkout. `MANIFEST.txt` lists every file. The scratch scripts are in `scripts/`: `tree_digests.sh`, `compare.sh`, `digest_commit.sh`, `red.sh`, `mutate.py`, `local.sh`, `local_run.py`, `replay_old.py`, `replay_commit.sh`, `replay_mutation.py`, `db_stats.py`, `horse.py`. Gate logs are `q2-*.log` to `q5-*.log`; red runs are in `red/`, mutations in `mutations/`, local games in `local-*/` and `runs-base/`, digests in `digests-*/`.

## 9. EVO results

`local-ops` ran the four §7 blocks on EVO, one run per change, from 19:30:17Z to 19:52:42Z. The runs used the scripted policy only, with no model and no spend. Each archive sha256 matched §7 on the Mac and on EVO. Every run exited 0 and replayed `identical`.

| Change | Commit | Run | Winner, turn | Peak enclosed | Share intervals / longest | Breakthroughs (first interval) | Horse holds | Events | Wall |
|---|---|---|---|---|---|---|---|---|---|
| Q2 | `44c1979` | default | roman, 160 | 44,616@53 | 14 / 14 | none | none | 63,124 | 5:53 |
| Q3 | `d295f6a` | default | roman, 160 | 6,901@32 | 0 / 0 | 9: L1 33, L2 36, L5 39, L6 41, L8 42, A1 46, L7 46, L3 48, L4 67 | none | 63,124 | 5:39 |
| Q1 | `5689adb` | default | roman, 160 | 6,901@32 | 0 / 0 | same 9 as Q3 | none | 63,124 | 5:25 |
| Q5 | `3629656` | cavalry-delayed-20 | roman, 160 | 6,938@32 | 0 / 0 | 8: L1 33, L2 36, L5 39, L8 44, A1 45, L7 47, L3 48, L4 100 | HC1 30, HC3 30 | 60,337 | 5:26 |

Every value matches the local results in §6 and §7. Q1 equals Q3 in every field because Q1 does not fire in default. Max RSS was about 410 MB. Evidence: `apps/poc/artifacts/cannae-d38/evo/<sha>/` in the task worktree (git-ignored), and `evo-linux:/home/masa/bt19/`.

**Outcome for the owner.** Under the four changes the default game is still a Roman win at turn 160. After Q2 the Carthaginians hold the share for at most 14 consecutive intervals, so Q1's 20-interval rule never fires. After Q3 nine Roman units break through on the rear edge, and the peak enclosure falls from 44,616 to 6,901 men.

## Review notes

code-critic at `030e776`: **APPROVE**, no CRITICAL or HIGH. The critic ran the 25 Cannae tests (pass). It stopped the full suite at its 120 s limit; the builder's per-commit `make test-poc` runs are in §5. It confirmed in code that:

- Every D38 branch tests `edition == D38`, so a snapshot without the key scores as before.
- v1 cavalry-delay ids behave as before.
- Q1 re-derives the run from the last 20 record rows, so a break resets it and nothing double-counts.
- An unknown edition is refused at registration.

It did not re-run the digest, replay or mutation checks. Credential scan: see the PR.

Three LOW notes, not fixed (below the fix bar):

- `victory_encircle.py:253`: a persisted snapshot with an unknown edition string would score under the old rules without notice. Registration blocks it today. Raising in `score` on an unknown edition would close it.
- `scenario_cannae.py:295` duplicates the `"cannae-d38"` string to avoid an import cycle that predates this branch. A test pins the two together. §3's wording that the cycle is fixed overstates it: the change keeps the cycle from growing, and a lazy import in `victory.py` would remove it.
- `cannae_policy.py:225-229`: in v2 the ride delay counts from the first hold sent. A unit whose hold the three-order cap delays is held for less than the delay. This is documented and tested.
