# First five selections and their source register

**Date:** 2026-11-06 (UTC). **Requirement:** the user's sequence item 4 in the build handoff (local, not published) asks for the first five battle selections, each with separate order and outcome sources. Item 3 asks for comparisons against scripted historical controls across the six eras, plus a separate army-scale Cannae. **Correction applied:** an earlier pass dropped Hougoumont (no gate state in the engine) and Hill 223 (disputed account), and counted Cannae as a company action. The Architect ruled that both eras stay and that Cannae is a separate army-scale case. This register follows that ruling.

This document keeps four kinds of statement apart. Each section heading says which kind it holds:

- **Requirement** — what the user or the Architect asked for.
- **Observation** — what a cited source says, with the date it was read.
- **Proposal** — an original design suggestion. Nothing here is implemented.
- **Open question** — listed at the end for the user.

Cases, fixtures and art already exist in [the six-era matrix](../../apps/poc/experiments/six-era-cases.json), [34 — six-era command tests](34-six-era-command-tests.md), [36 — Cannae](36-cannae-army-scale.md) and the [battle gallery](battle-gallery/README.md). This register adds no new case and swaps in no unrelated action.

## 1. Selections (proposal)

| # | Era | Company-scale action | Nested element |
|---|---|---|---|
| 1 | American Civil War | Little Round Top, 2 July 1863 | Company B, 20th Maine, on the detached flank |
| 2 | American Revolutionary War | Concord's North Bridge, 19 April 1775 | Acton minute company at the head of the provincial column |
| 3 | Napoleonic Wars | The north gate at Hougoumont, 18 June 1815 | The gate party inside the farm, within the Guards garrison |
| 4 | World War II | Pegasus Bridge, 6 June 1944 | The canal-bridge platoons of D Company, 2nd Ox and Bucks |
| 5 | World War I | The ravine west of Hill 223, 8 October 1918 | The 17-man patrol from Company G, 328th Infantry |
| next | Romans in Gaul | The recall at Gergovia, 52 BCE | Men of the Eighth Legion at the wall |
| separate | Second Punic War (army scale) | Cannae, 216 BCE | Center, wings and cavalry commands |

**Why Gergovia waits (proposal).** Item 4 asks for separate order and outcome sources. Gergovia is the only company-scale case where one surviving narrative supplies both. Caesar's *Gallic War* VII.45–51 gives the Roman orders, the recall and the repulse. No Gallic account survives, so the Gallic intent is wholly inferred ([34](34-six-era-command-tests.md#romans-in-gaul--the-recall-at-gergovia)). The other five each have at least one outcome source written by someone other than the author of the order source. Gergovia is not dropped. Its fixture, shared component test and art stay in place, and it is the sixth comparison to run. The two cases with engine or source problems, Hougoumont and Hill 223, stay in the first five because the Architect ruled that neither an engine gap nor a source dispute removes an era.

**Cannae** is the army-scale case. It is listed in the register below for completeness and is not one of the five.

## 2. Napoleonic — Hougoumont

### What the sources say (observation)

Read 2026-11-06 unless noted.

- Age of Revolution, *Closing the Gates at Hougoumont, 1815*: the north gate was left open for friendly traffic. It was not shut properly when the French attacked, and about 30 French soldiers got in. The page names Corporal James Graham among the men who closed it and Lt-Col James Macdonell as commander. It ties the closing to the start of the attack at about 11:30. It cites no primary source.
- Age of Revolution, *Lock of the Gate of Hougoumont* (Guards Museum object): names Macdonell, Wyndham, Ensigns Hervy and Gooch (spelling as on the page) and men of the 2nd Battalion Coldstream Guards as the men who shut the gate, and Sous-Lieutenant Legros as leader of the French party. It cites no primary source and attributes the line about the battle turning on the gates to Wellington without a reference.
- Age of Revolution, *Battle Instructions written by the Duke of Wellington* (Apsley House, English Heritage): a note written during the battle to Macdonell about the fire in the château. It tells him to keep men where the fire has not reached and to hold the garden walls if the buildings fall in. It is a recorded Allied order to the garrison, but it concerns the fire, not the gate.
- Wellington's dispatch to Bathurst, 19 June 1815 (Wikisource transcription, citing *London Gazette Extraordinary* no. 17028, 22 June 1815, pp. 1213–1215, and Gurwood 1838, pp. 478–484): Hougoumont was held by a detachment of Byng's Guards brigade, first under Macdonell and then under Colonel Home, and was held all day. The dispatch does not mention a gate.
- National Army Museum, *Battle of Waterloo*: the north gate was open for resupply; a small French group got in; the defenders shut the gates and killed them. It summarises Napoleon's intent for Hougoumont as a diversion. It cites no source.
- Gareth Glover Collection, *Private Matthew Clay at Quatre-Bras and Waterloo*: Clay's narrative was published at Bedford in 1853 (reprint Ken Trotman, 2006, ISBN 1905074255). Glover argues that later writers misquoted Clay and that two separate French break-ins were merged into the single "closing of the gates". The narrative itself was not read.

**Gaps (observation).** No French order for the gate party was found. No source read gives the gate's construction, a bar or beam, the time it took to shut, or the size of the closing party beyond the named individuals. The time of the incident is uncertain: the dispatch dates the first attacks from about ten, and one secondary page puts the closing at about 11:30.

### Option A — model the gate (proposal)

Extend the `poc-6` feature model in [24 — map features and Dig in](24-map-features-and-digging-in.md). Today a building is one aggregate hex with cover, a movement cost and an obstacle height. Doors are explicitly out of scope there.

1. **Opening on a building.** A building feature gets a list of openings. Each opening sits on one hex edge between the building hex and an outside hex. Its state is one of `open`, `closing`, `closed`, `barred` or `forced`. The state belongs to the ground, like fieldworks, and survives any change of occupant.
2. **Movement and sight.** `open` and `forced` let troops and couriers cross that edge at the building's entry cost. `closed` and `barred` make the edge impassable. The building's other edges stay impassable for entry if the scenario declares the compound walled. A closed gate blocks sight through the opening; the walls already block it.
3. **Close action.** A new order template, *Close the gate*, goes through the normal authority, voice or courier delivery and acknowledgement. A unit inside the building hex performs it. A standing order of the kind in [26](26-standing-orders-and-troop-analysis.md), "close the gate on a breach", lets the local commander act without a courier. That matches the Allied intent in the fixture.
4. **Labour and time.** Closing needs a number of labour units; barring needs more. Work per interval is `min(men assigned, cap)`, as Dig in uses `min(strength, tools × 2, remaining)`. The numbers are authored POC values, labelled as such, because no source gives them.
5. **Contact interruption.** Dig in stops on any contact within five hexes. A gate is closed *because* of contact, so the rule differs. Closing proceeds under fire. It cannot complete while an enemy unit is in the gateway itself. An enemy unit on the outside hex pushes back: compare men pushing on each side and add the difference to or subtract it from the labour. The attacker can force a `closed` gate back to `forced` with labour; a `barred` gate needs much more, or cannot be forced in the POC.
6. **Men already inside.** Enemy troops who crossed before the gate shut stay in the building hex as a separate unit. Their route out and their courier route are cut. They fight, surrender or are destroyed under existing close-combat rules. The comparison records how many crossed and what happened to them.
7. **Knowledge.** Gate state is a feature observation. Each side learns a change only through local sight or a delivered report. Inference sees the reported state, never the current one. God Mode shows the current state.
8. **Events.** A `gate_state` event links unit, order version, labour, pushers on each side, and the units on each side of the edge when the state changed.

**Rules-edition implication (proposal).** This changes movement, sight and the order catalog, so it needs a new edition. Following the project's pattern, new battles would use `poc-9`. The current `engine.py`, `orders.py` (`common-orders-v3`), `features.py` and any other changed module would be frozen as `*_v8.py` so that `poc-8` saves replay exactly. The order catalog would become `common-orders-v4`. Old saves are not migrated. The snapshot schema gains the openings list, which older editions ignore.

**Scenario variants (proposal).** Vary the delay before closing, and run a second variant with two separate break-ins, following Glover's reading of Clay. Keep the number of French who entered out of the pass criteria; compare gate state, entry by follow-on troops and possession of the courtyard.

### Option B — a replacement action (proposal)

The nearest Napoleonic company-scale candidate in the same battle is La Haye Sainte, defended by Major Georg Baring's 2nd Light Battalion, King's German Legion. A search on 2026-11-06 found Baring's narrative cited through Beamish's *History of the King's German Legion*, vol. 2, but no text of it was read; it is **unverified**. The action is battalion-scale (about 400 men in secondary accounts found by search, unverified), and it also turns on buildings, gates and ammunition. It would need the same building work plus resupply. It does not avoid the engine gap and has weaker sources in hand.

### Recommendation

**Keep Hougoumont and build Option A.** The gate is the decision the fixture asks about. The proposal extends an existing model rather than adding a new subsystem. The case has art, a fixture and three independent institutional descriptions of the outcome. La Haye Sainte would need the same mechanism and has no verified source in the repo.

## 3. World War I — Hill 223

### The source dispute (observation)

Read 2026-11-06 unless noted.

- **York's diary.** Excerpts are printed in Sam K. Cowan, *Sergeant York and His People* (Funk & Wagnalls, copyright 1922; Grosset & Dunlap printing; Project Gutenberg eBook #19117). The diary says the order came to take Hills 223 and 240 on the 8th. It says the barrage did not arrive, that 17 men went round the left flank, that Germans surrendered, that the German guns turned and killed 6 and wounded 3, and that York brought 132 prisoners to his major's post. It credits York with the shooting and with the German officer's surrender.
- **Affidavits of the other survivors.** Cowan prints excerpts from four affidavits (Privates Donohue, Sacina, Beardsley and Wills). He says the affidavits were made by the patrol's survivors and are among the records of Lt-Col G. Edward Buxton Jr., the 82nd Division's official historian. In the printed excerpts the men describe guarding prisoners and say they did not or could not fire. Cowan presents the affidavits as confirming York's role. The full affidavits were not read.
- **"The other sixteen."** James P. Gregory Jr., *Unraveling the Myth of Sgt. Alvin York: The Other Sixteen* (Texas A&M University Press, 2023; ISBN 9781648430763; Project MUSE listing read). The publisher's summary says the patrol was led by acting Sgt Bernard Early, captured more than 80 Germans before an unseen machine gun killed six men, and that the other survivors later sought recognition and met "improper investigations" and cover-ups. Its appendices include a 1932 Buxton letter and a 1941 letter from six survivors to *The Boston Globe*. The book itself was not read.
- **Official citation.** York's Medal of Honor citation was **not read from an official source**. Search results give the action near Châtel-Chéhéry on 8 October 1918 with Company G, 328th Infantry, and give conflicting award dates (20 March 1919 versus War Department General Orders No. 59, 3 May 1919). Status: unverified.
- **Site location.** An MTSU release of 8 December 2006 (Newswise) reports that geographer Tom Nolan and historian Michael Birdwell used GIS, historic French and German maps, maps annotated by Buxton and Danforth, the 1919 affidavits and 1929 Buxton correspondence to target a metal-detector survey. It reports over 1,400 artifacts, including a "328 Infantry G" collar disk. A CBN report reposted by History News Network (25 March 2007) says Lt-Col Douglas Mastriano disputed the site and claimed proof of a different location. Mastriano's own 2007 report on battledetective.com could not be read (unreadable PDF). His later book was found only in search results and is **unverified**.
- **Repo-recorded Army History sources.** [34](34-six-era-command-tests.md#world-war-i--the-ravine-west-of-hill-223) cites a "Field study of Hill 223" (history.army.mil, *Army History* no. 50) and "The other sixteen" (lineofdeparture.army.mil, Spring 2026), checked 2026-11-05. Both returned HTTP 403 on 2026-11-06 (about 02:13 UTC). A web search found no *Army History* Spring 2026 article under that title; the title matches Gregory's 2023 book. Resolved in the fixture and in 34: "The other sixteen" now cites the Project MUSE listing of Gregory (2023), S41 (HTTP 200, 2026-11-06 UTC). "Field study of Hill 223" has no verified replacement: a mirror of *Army History* no. 50 (ky.ng.mil) also returned HTTP 403, so the citation stays marked "link dead (HTTP 403, 2026-11-06); unverified". Its contents are **not re-verified** here.

**What the accounts share.** The diary, the printed affidavit excerpts and Gregory's summary agree that a group of about 17 went round the flank, took prisoners at a German post, lost 6 killed and 3 wounded to machine-gun fire, and came back with prisoners. They disagree on who did what, on prisoner counts (the diary gives "about 80 or 90" at the surrender and 132 at the end; Gregory's summary says more than 80), and later on where it happened.

### Option A — competing reconstructions (proposal)

Model the action as one scenario with labelled variants. Each variant discloses its assumptions in the evaluation file, never in the controller briefs.

| Variant | Basis | Assumption disclosed |
|---|---|---|
| R1 York-centred | Diary, citation (unverified), Cowan | Most suppressive fire on the gun line comes from one rifleman; the rest guard prisoners. |
| R2 Patrol-wide | Affidavit excerpts, Gregory's summary | Prisoners act as a shield; the guards' presence and the German officer's decision end the fire; credit is shared. |
| L1 MTSU site | Nolan and Birdwell, 2006 | Terrain from the MTSU survey area. |
| L2 Mastriano site | Mastriano's claim (location not verified here) | Terrain from the alternative site; held until a readable source gives it. |

Run R1 and R2 on L1 first; add L2 when a source for it is read. **Pass criteria stay the same across variants** and use only what the accounts share: the patrol reaches the rear of the gun position; it takes a large group of prisoners; it loses about a third of its men to fire from the gun line; it returns with prisoners. Body counts and prisoner totals are recorded and never scored. A result that only one variant reproduces is reported as variant-specific.

Model gaps (from [34](34-six-era-command-tests.md)): machine-gun arcs, dead ground, local surrender and the cost of escorting prisoners.

### Option B — a replacement action (proposal)

No WWI company-scale replacement was verified in this pass. None is proposed, because an unsourced substitute would be worse than a disputed case with disclosed variants.

### Recommendation

**Keep Hill 223 with Option A.** The dispute is about attribution, counts and location. The facts the comparison needs are shared by every account read. Variants turn the dispute into a test: a model that only reproduces the outcome under one reading tells us something.

## 4. Register (observation, with labelled reconstruction)

Abbreviations: **REC** — reconstructed intent, with its basis. **SHARED** — one source, or one author, serves as both order and outcome source. Sources are those in [34](34-six-era-command-tests.md) (checked 2026-11-05) unless dated 2026-11-06.

| Case | Order source(s) per side | Outcome source(s) | Reconstructed intent (REC) | Order and outcome independent? | Missing independent sources | In the repo / model gap |
|---|---|---|---|---|---|---|
| Little Round Top | **Union:** Morrill's account (NPS landscape report, fig. 4.13), recounting Chamberlain's instruction. **Confederate:** Oates's report, 8 Aug 1863 (Law's order to wheel, which Oates did not obey; his own withdrawal order; re-read 2026-11-06). | Morrill's account; Oates's report. | REC: Union "screen the flank, use local judgment"; Confederate "advance on the Union left, withdraw when untenable" — paraphrased from the two accounts. | SHARED per side: each author gives his own side's order and the outcome. The two sides are independent of each other. | Chamberlain's official report; a 15th or 47th Alabama company-level account. Not read. | Fixture, art, shared service test; authored Little Round Top demo scenario (not the Morrill fixture). Gap: Morrill's company and attached sharpshooters as scenario data. |
| Concord North Bridge | **British:** Gage's orders to Smith, as quoted by NPS (re-read 2026-11-06); manuscript at the Clements Library (**unverified**, HTTP 403). **Provincial:** Barrett's no-first-fire instruction and Buttrick's order to fire, as reported by NPS. | NPS *April 19, 1775* (depositions, Barker, Foster, Smith's report cited); NPS *Captain Isaac Davis*. | REC: British "guard the crossing, fall back if it gives way" — inferred from Laurie's position, not an order to him. Provincial intent follows Barrett's recorded instruction. | Partly. The British order is an independent document. The provincial order and the outcome reach us through the same NPS synthesis: SHARED. | The depositions and Barker's diary themselves; Laurie's own account. Not read. | Fixture, art, local-voice test. Gap: fire discipline, reach of a spoken order, succession after an officer falls. |
| Hougoumont north gate | **Allied:** Wellington's battle note to Macdonell (Apsley House, via Age of Revolution; about the fire, not the gate). **French:** none for the gate party; NAM summarises Napoleon's diversion intent without a source. | Wellington's dispatch, 19 June 1815; Age of Revolution gate and lock pages; NAM. | REC: Allied "keep the supply entrance open, close on a breach"; French "pass men through before it shuts" — inferred from the outcome pages. | Primary layer SHARED (Wellington wrote the order and the dispatch). The secondary outcome pages are separate but uncited. | Any French order or account (Legros's party, Reille, Jérôme); Clay's 1853 narrative (not read); Siborne's *Waterloo Letters* (not read). | Fixture, art, building-cover test. Gap: gate state (proposal in §2). |
| Pegasus Bridge | **British:** Howard's coup-de-main report and a report on Operation Tonga are listed as attachments on the Paradata page; their text was not read. **German:** none found. | Paradata *Pegasus Bridge*; Wallwork's account (Paradata). | REC: British "seize the canal bridge intact and hold for relief"; German "guard, raise the alarm, resist" — the German intent is inferred. | Partly. If the Howard report is read, it is an order source from a different author than the outcome pages. Wallwork's account is an independent participant witness. | Howard's operation order text; any German garrison record. | Fixture, art, remote-delivery test. Gap: separate glider arrivals, darkness, alarm delivery, bridge state. |
| Hill 223 | **American:** York's diary ("order came to take Hill 223 and 240"; 17 went round the left flank), via Cowan 1922. Who ordered the patrol out is not in the material read. **German:** none read. | York's diary; four affidavit excerpts (Cowan 1922); Gregory 2023 (summary only); citation (**unverified**). | REC: American "turn the gun position from the flank"; German "hold the approach under fire, respond locally" — the German intent is inferred. | Diary SHARED for order and outcome. Affidavits are separate witnesses, but read only through Cowan and collected by the division historian; not fully independent. | The order that sent the patrol; German regimental accounts; the full affidavits; an official citation text; readable site reports from both teams. | Fixture, art, recon-quality test. Gap: MG arcs, dead ground, local surrender, prisoner escort; variants in §3. |
| Gergovia (next) | **Roman:** Caesar, *Gallic War* VII.45–51. **Gallic:** none. | Caesar, VII.47–51. | REC: Gallic "reinforce the wall, drive back the isolated Romans" — wholly inferred. | SHARED: one author for order and outcome. | Any non-Caesarian account; a Gallic source does not exist. | Fixture, art, courier-acknowledgement test. Gap: signal audibility, cohesion, close combat. |
| Cannae (army scale) | **Both sides:** no orders survive. Dispositions narrated by Polybius III.113–117 and Livy XXII.45–50. | Polybius; Livy. | REC: Carthaginian "yielding centre, inward-turning wings, cavalry to the rear"; Roman "press the centre" — reconstructed from the narratives ([36](36-cannae-army-scale.md)). | SHARED: the same narratives give dispositions and outcome. Livy is not independent of the Polybian tradition ([gallery note](battle-gallery/cannae.md)). | Any surviving order, Carthaginian account or staff record. | Four synthetic escape-route tests, art and manifest. Gap: army hierarchy, capacity-limited movement, command delays, historical replay. |

## 5. Sources newly read for this register

Access date for every entry: **2026-11-06 (UTC)**. Recorded in [09 — sources](09-sources.md#first-five-selection-register--2026-11-06).

Verified (page read):

- Sam K. Cowan, *Sergeant York and His People*, Funk & Wagnalls, copyright 1922; Grosset & Dunlap printing. [Project Gutenberg #19117 text](https://www.gutenberg.org/files/19117/19117.txt), released 25 Aug 2006.
- James P. Gregory Jr., *Unraveling the Myth of Sgt. Alvin York: The Other Sixteen*, Texas A&M University Press, 2023. [Project MUSE listing](https://muse.jhu.edu/book/125322) (summary and contents only).
- MTSU via Newswise, 8 Dec 2006. [Researchers use scientific detection and historic evidence to uncover Sgt. York's battle site](https://www.newswise.com/articles/researchers-utilize-scientific-detection-historic-evidence-to-uncover-sgt-yorks-battle-site).
- CBN report reposted by History News Network, 25 Mar 2007. [Army officer: Sgt. York battle site located](https://www.hnn.us/article/37526).
- Wellington to Bathurst, 19 June 1815. [Wikisource transcription](https://en.wikisource.org/wiki/Wellingon%27s_Waterloo_dispatch_to_Lord_Bathurst,_19_June_1815), citing *London Gazette Extraordinary* 17028 and Gurwood 1838.
- Age of Revolution, [Battle Instructions written by the Duke of Wellington](https://ageofrevolution.waterlooassociation.org.uk/200-object/battle-instructions-written-by-duke/) (Apsley House).
- Age of Revolution, [Lock of the Gate of Hougoumont](https://ageofrevolution.waterlooassociation.org.uk/200-object/lock-of-the-gate-of-hougoumont/) (Guards Museum).
- Gareth Glover Collection, [Private Matthew Clay at Quatre-Bras and Waterloo](https://garethglovercollection.com/?p=130).
- Re-read: Age of Revolution *Closing the Gates*, NAM *Battle of Waterloo*, NPS *April 19, 1775*, NPS Oates report, Paradata *Pegasus Bridge*.

Unverified (found in search or blocked; nothing here rests on them):

- York's Medal of Honor citation, official text.
- Gage's orders to Smith, Clements Library manuscript (HTTP 403).
- Mastriano's 2007 report (unreadable PDF) and his later book.
- Baring's La Haye Sainte narrative in Beamish, vol. 2.
- Clay's 1853 narrative text; Siborne, *Waterloo Letters* (1891).
- The two *Army History* items in [34](34-six-era-command-tests.md) (HTTP 403 on re-read).

## 6. Open questions for the user

1. Is Gergovia the right era to hold back, given that its only source is Caesar? The alternative is to hold back Pegasus Bridge, whose German side has no order source either.
2. Should the Hougoumont gate mechanism go into a `poc-9` edition now, or should the comparison first run on `poc-8` and report the gate as a recorded model gap?
3. For Hill 223, may the evaluator score variant R1 and R2 separately and report both, rather than choose one?
4. Do you want the full affidavits, the official citation and both site reports obtained before the Hill 223 comparison runs? Some may need library or archive access.
5. Resolved 2026-11-06 (Architect-approved): "The other sixteen" is replaced by S41. Gap remaining: no readable public copy of "Field study of Hill 223" was found, so that citation is marked dead and unverified.
6. Should the authored gate labour and push numbers be fixed in advance, or treated as sensitivity parameters in the tuning step?
