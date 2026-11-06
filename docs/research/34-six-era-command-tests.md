# Historical command tests across six eras

The requested coverage is one action in each era, in the order below. These comparison fixtures were selected for project review. The [illustrated PDF](../presentations/battle-six-eras.pdf) uses the same cases as the [machine-readable test matrix](../../apps/poc/experiments/six-era-cases.json). Sources checked November 5, 2026. The orders below translate historical accounts into playable intents. An opposing intent may be an inference, especially for Gergovia. Treat all six as evaluation material and keep outcomes out of controller inputs.

## What ran

Six shared-engine component checks passed on local poc-8. One fresh headless run of the authored Little Round Top demo used isolated SQLite storage and the default scripted policies. It produced a Union win, 80 Union and 82 Confederate troops remaining, 2,562 events, and exact replay across 63 revisions. This matches the earlier [design assessment](30-design-scale-assessment.md). The demo differs from the proposed Morrill fixture. None of the six sourced historical baselines has yet been calibrated or compared end to end.

To repeat the shared checks, run the following from the repository root. The command reads the case-specific test identifiers without giving evaluation data to a simulation controller.

~~~sh
cd apps/poc
PYTHONPATH=tests python3 -c 'import json, unittest; from pathlib import Path; cases=json.loads(Path("experiments/six-era-cases.json").read_text())["cases"]; suite=unittest.defaultTestLoader.loadTestsFromNames([case["shared_test"] for case in cases]); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())'
~~~

Use `make headless-poc` from the repository root for the separate Civil War demo and replay. Record the run identity, versions, side-specific observations, order issue and receipt, objective state, force changes and replay verification for each future comparison. Treat an unsupported event as a recorded model gap.

## American Civil War — Little Round Top

Gettysburg, Pennsylvania  /  July 2, 1863. Company B, 20th Maine, on the exposed Union flank. Confederate pressure comes from the neighboring Alabama infantry.

**Decision.** How far can a detached company range and still protect the line?

- Union: Screen the exposed flank. Take cover and use local judgment when the enemy passes.
- Confederate: Advance against the Union left. Withdraw when the position becomes untenable.

**Historical outcome.** The Union held the position. Morrill described firing from a stone wall as the Confederates fell back.

**What to compare.** Compare control of the high ground, the timing of flank fire and the cost to each side. Separate a matching outcome from a matching sequence.

**Missing or uncertain.** The demo models six equal starting detachments. Morrill’s actual company and its attached sharpshooters still need their own scenario data.

Shared component exercised: `test_services.ServiceTests.test_can_run_commands_clock_and_replay_with_injected_dependencies`.

Sources: [Morrill’s account • NPS landscape report, fig. 4.13](https://www.nps.gov/gett/getinvolved/upload/FinalCLR_LittleRoundTop_AllSections-508.pdf) · [Oates’s report • August 8, 1863](https://www.nps.gov/gett/learn/historyculture/official-report-of-colonel-william-c-oates.htm)

## American Revolutionary War — Concord’s North Bridge

Concord, Massachusetts  /  April 19, 1775. Captain Isaac Davis’s Acton minute company at the head of a larger provincial column, facing British light infantry at the crossing.

**Decision.** When may the front company open fire?

- Provincial: Advance to the bridge. Hold fire until fired upon, then return fire on Buttrick’s command.
- British: Guard the crossing. Fall back toward the main body if the position gives way.

**Historical outcome.** The regulars fired, the provincials returned fire, and the regulars withdrew. Davis was killed.

**What to compare.** Compare first-fire sequence, who heard the command, and who controlled the crossing after the exchange.

**Missing or uncertain.** Represent fire discipline, a spoken order’s reach and succession after an officer is hit. The precise source of the first British shot is uncertain.

Shared component exercised: `test_command_observer.CommandTests.test_own_detachment_uses_local_voice`.

Sources: [Minute Man NHP • The events of April 19](https://www.nps.gov/mima/learn/historyculture/april-19-1775.htm) · [National Park Service • Captain Isaac Davis](https://www.nps.gov/people/captain-isaac-davis.htm)

## Napoleonic Wars — The north gate at Hougoumont

Waterloo, present-day Belgium  /  June 18, 1815. Guards defending the farm and a French assault party. The gate fight was a small action within the wider garrison defence.

**Decision.** When is it worth closing the route that keeps the garrison supplied?

- Allied: Keep the supply entrance available. On a breach, close the leaves and hold the courtyard.
- French: Reach the entrance and pass men through before the defenders can shut it.

**Historical outcome.** A French party entered. The defenders shut the gate behind them and held the farm through the day.

**What to compare.** Compare gate state, entry by follow-on troops and possession of the courtyard. Vary the delay before closing.

**Missing or uncertain.** A building that adds cover cannot model a working gate. Track open, contested and barred states, with men already inside.

Shared component exercised: `test_features.FeatureTests.test_building_blocks_intermediate_sight_and_adds_cover`.

Sources: [National Army Museum • Defence of Hougoumont](https://www.nam.ac.uk/explore/battle-waterloo) · [Age of Revolution • Closing the gates](https://ageofrevolution.waterlooassociation.org.uk/200-object/closing-the-gates-at-hougoumont-1815/)

## World War II — Pegasus Bridge

Bénouville, Normandy  /  June 6, 1944. Major John Howard’s reinforced D Company, 2nd Ox and Bucks. The case follows the canal-bridge platoons of the wider two-bridge operation.

**Decision.** Can the first platoons seize the crossing intact before the defence can react?

- British: Land near the canal bridge, rush the crossing and hold it intact for relief.
- German: Guard the crossing, raise the alarm and organize resistance when the landing is detected.

**Historical outcome.** The British captured the canal bridge intact. The Orne river bridge was a separate objective.

**What to compare.** Record when each bank is secured, whether the bridge remains passable and when headquarters learns the outcome.

**Missing or uncertain.** Begin at touchdown. Model platoons arriving separately, darkness, alarm delivery and the physical state of the bridge.

Shared component exercised: `test_standing_analysis.StandingTests.test_remote_delivery_and_receipt_are_separate`.

Sources: [Airborne Assault Museum • Jim Wallwork’s account](https://paradata.org.uk/content/4663334) · [Airborne Assault Museum • Pegasus Bridge](https://paradata.org.uk/content/4663998)

## World War I — The ravine west of Hill 223

Châtel-Chéhéry, France  /  October 8, 1918. Company G, 328th U.S. Infantry. The maneuvering element is Sgt. Bernard Early’s 17-man patrol, nested in a company attack.

**Decision.** Can a small patrol turn a gun position that has stopped the main advance?

- American: Send a patrol around the flank to reach the machine guns from the rear.
- German: Keep the approach under fire. Respond locally when the patrol reaches the gun positions.

**Historical outcome.** The patrol suffered losses, captured German troops and brought prisoners back. The outcome depended on more than one man.

**What to compare.** Compare loss of effective gunfire and return of the patrol with prisoners. Keep disputed body counts out of the pass criteria.

**Missing or uncertain.** Model machine-gun arcs, dead ground, local surrender and the burden of escorting captives. The precise locations and counts are debated.

Shared component exercised: `test_recon_tactics.ReconTests.test_distance_cover_and_suppression_reduce_quality`.

Sources: [U.S. Army History • Field study of Hill 223](https://history.army.mil/Portals/143/Images/Publications/ArmyHistoryMag/pdf/20002009/AH50newOCR.pdf) · [U.S. Army History • The other sixteen](https://www.lineofdeparture.army.mil/Journals/Army-History/Archive/Spring-2026/Unraveling-the-Myth-of-Sergeant/)

## Romans in Gaul — The recall at Gergovia

Gaul, present-day France  /  52 BCE. Men of the Eighth Legion under centurions at the wall, against Gallic defenders. The comparison is a small sector of a much larger assault.

**Decision.** What does a forward detachment do when the recall fails to reach it?

- Roman: Attack the outer position, then halt and retire on the recall. Each group acts on the signals it receives.
- Gallic: Reinforce the threatened wall and gate. Drive back the isolated Romans.

**Historical outcome.** Caesar says some troops continued after he sounded the recall. Defenders repulsed the attack. His account gives the Roman commander's perspective.

**What to compare.** Compare which groups receive the recall, how far they advance and whether they can withdraw together.

**Missing or uncertain.** Model signal audibility over broken ground, formation cohesion and close combat. The engaged strength and Gallic orders are uncertain.

Shared component exercised: `test_command_observer.CommandTests.test_courier_order_then_physical_return_ack`.

Sources: [Caesar • The Gallic War, VII.45–51](https://penelope.uchicago.edu/Thayer/E/Roman/Texts/Caesar/Gallic_War/7D%2A.html) · [Latin and English • VII.47, the recall](https://lectito.app/caesar/gallic-war-7/47/)

## Larger test

[Cannae, 216 BCE](36-cannae-army-scale.md) adds a separate army-scale double envelopment to these six actions.
