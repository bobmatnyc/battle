# 63 — Cannae: scenario plan and sources

**Date:** 2026-11-07 (UTC). **This is a plan, not a run.** It builds no entry, runs no simulation, changes no code and no fixture. It follows the shape of [52](52-pegasus-bridge-scenario-plan.md), [56](56-hill-223-scenario-plan.md) and [57](57-gergovia-scenario-plan.md).

**Requirement.** The user's sequence item 3 asks for a separate army-scale Cannae beside the six company-scale comparisons. The Architect ruled that Cannae is a separate army-scale case, not a company action ([37](37-first-five-selection-register.md) §1). [36](36-cannae-army-scale.md) sets the test: a center, wings and cavalry commands, an army-to-sector-to-formation hierarchy, scale-appropriate durations and distances, escape-lane throughput, and a model that allows a failed pincer. Its four route tests ([`test_escape_routes.py`](../../apps/poc/experiments/cannae/test_escape_routes.py)) check geometry on synthetic ground only.

Labels: **sourced** (S-id and locator), **inferred** (a reading from sourced facts), **reconstruction**, **authored**, as in 52. Sources are in [09 — sources](09-sources.md#cannae-source-pass--2026-11-07), S65 to S70. Access date 2026-11-07.

## 1. Findings on the sources

**Polybius is the earliest surviving narrative (S65).** Paton's Loeb translation (Thayer's transcription) was read for III.107 to III.117. Locators are book III chapter and, where Thayer marks it, section. Samuels dates the Cannae section to the 150s BCE, "some sixty years after the battle" (S67 p. 7), and notes that Polybius's friend and benefactor Scipio Aemilianus was Aemilius Paullus's grandson (p. 23).

| Point | What S65 says |
|---|---|
| Roman forces | Eight legions "of about five thousand men" each, allied infantry equal in number, allied cavalry three times the Roman (107.9–107.12); the army in line "about eighty thousand foot and rather more than six thousand horse" (113) |
| Camps | Romans camp about fifty stadia from the enemy (110.1); Aemilius camps two-thirds of the army on the Aufidus and fortifies a smaller position on the farther bank, east of the ford (110.8–110.11) |
| Ground | "Flat and treeless" (110.2); Hannibal tells his men the ground favours cavalry (111) |
| The day before | Numidians cut off the water-bearers of the lesser camp (112) |
| Roman deployment | Terentius in command; just after sunrise he crosses the river, forms the line "facing south"; Roman cavalry on the right by the river; maniples "closer together than was formerly the usage", depth "many times" the front; allied horse on the left; light troops in front (113) |
| Carthaginian deployment | Slingers and pikemen in front; Spanish and Celtic horse on the left by the river; half the Africans; Spanish and Celtic foot; the other half of the Africans; Numidian horse on the right. He then advances the central companies of Spaniards and Celts to form a crescent, "his object being to employ the Africans as a reserve" (113) |
| Carthaginian forces | Cavalry about ten thousand; infantry including the Celts "did not much exceed forty thousand"; Africans armed with captured Roman arms; Spaniards and Celts in alternate companies (114) |
| Commanders | Roman right Aemilius, left Terentius, centre the previous year's consuls Atilius and Servilius; Carthaginian left Hasdrubal, right Hanno, centre Hannibal with Mago (114) |
| Cavalry by the river | The Spanish and Celtic horse meet the Roman cavalry; no wheeling, "they dismounted and fought man to man"; the Romans are cut down along the river (115) |
| Centre | The Spaniards and Celts give way "borne down by the weight of the legions"; the Romans crowd "from the wings to the centre", press so far that the Africans are on both flanks (115) |
| Africans | They face inward and charge the flanks, "the situation itself indicating to them how to act"; the Romans "no longer kept their compact formation but turned singly or in companies" (115) |
| Hasdrubal | Having cut up the Roman horse by the river, he rides to the Numidians; the allied horse flee; he leaves the pursuit to the Numidians and charges the legions' rear "at various points all at once" (116.5 onward) |
| Aemilius and Hannibal | Aemilius rides to the centre and fights; Hannibal is in the centre from the start (116.1) |
| End | The Romans "as long as they could turn and present a front on every side" held out, then were "huddled in and surrounded" and killed (116) |
| Losses | Of 6,000 cavalry, 70 escape with Terentius and about 300 allied horse; about 10,000 infantry captured "not in the actual battle"; perhaps 3,000 escape; about 70,000 dead. Hannibal loses about 4,000 Celts, 1,500 Spaniards and Africans, 200 cavalry (117) |
| The camp force | Aemilius left 10,000 foot in camp with orders to assault the Carthaginian camp during the battle; Hannibal's guard held, Hannibal came to its aid, 2,000 were killed and the rest captured (117.7 onward) |

**Livy is later and agrees in outline (S66).** Canon Roberts's 1905 translation (Wikisource) was read for XXII.40 to XXII.52 and XXII.59.

| Point | What S66 says |
|---|---|
| Camps | Servilius commands the smaller camp, nearer Hannibal, with one legion and 2,000 allies; Atilius is sent back to Rome (40). Two camps at Cannae; the smaller across the river (44) |
| Command | Varro, on his day, "exhibited the signal for battle" and crossed; Paulus followed "bound to support it" (45). Varro on the left, Paulus on the right (45) |
| Deployment | Roman cavalry on the right by the river, allied cavalry on the extreme left, javelin men in front (45). Balearics and light infantry first; Gaulish and Spanish horse on the left by the bank; Numidians on the right; Gauls and Spaniards in the middle, Africans at either end (46) |
| Orientation and weather | "The Romans faced the north, the Carthaginians the South"; the Vulturnus wind "blew great clouds of dust into their faces, making it impossible for them to see in front of them" (46). The camp was placed with its back to the wind (43) |
| Forces | 40,000 Carthaginian infantry, 10,000 cavalry; Hasdrubal on the left, **Maharbal** on the right (46) |
| Cavalry by the river | "No room for maneuvering, the river on the one side and the infantry on the other"; riders drag each other from their horses; "a struggle of infantry, fierce but short" (47) |
| Centre and wings | The Romans "echeloned their front" and bore down the thin advanced centre; the front became level, then "concave and crescent-shaped, the Africans at either end forming the horns"; the Romans were "enfiladed by the two wings, which extended and closed round them in the rear" (47) |
| False deserters | About 500 Numidians feign desertion, are sent to the rear, and later attack the Roman rear with picked-up shields (48). Hasdrubal sends Numidians after the fugitives and the Spanish and Gaulish horse to aid the Africans (48) |
| Paulus | Wounded by a sling bullet at the start; fights with a compact body; his cavalry dismount (49) |
| Escape | 7,000 to the smaller camp, 10,000 to the larger, about 2,000 to the village of Cannae (surrounded by Carthalo's cavalry); Varro with about 50 horse to Venusia (49) |
| Losses | 45,500 infantry and 2,700 cavalry killed; 29 military tribunes; 3,000 infantry and 1,500 cavalry taken in the battle (49) |
| After | 600 under Sempronius Tuditanus break out of the smaller camp at night "rather than to any concerted plan" (50); Hannibal's officers urge rest "for the remainder of the day" (51); the prisoners' spokesman says they fought "till close on night" (59) |

**Conflicts between S65 and S66, kept as disclosed conflicts.**
- Facing: Polybius has the Romans facing south (113, 114); Livy has them facing north (46). Modern accounts summarised on Wikipedia (S70) put the Romans facing east. The plan does not assign a compass bearing (§7).
- Carthaginian right wing: Hanno (S65 114) or Maharbal (S66 46).
- Servilius: in the centre (S65 114) or in command of the smaller camp (S66 40).
- Losses: about 70,000 dead and 10,000 captured off the field (S65 117) against 47,200 dead and 4,500 captured in the battle (S66 49).
- End of the day: rest "for the remainder of the day" (S66 51) against fighting "till close on night" (S66 59). Neither gives a clock hour.
- Livy's false deserters (48) have no counterpart in Polybius.

**Modern scholarship read (S67, S68).**
- Samuels, "The Reality of Cannae", *Militärgeschichtliche Mitteilungen* 47 (1990), read in full from a hosted scan. He argues that there is "no archaeological or documentary evidence for the battle" (p. 7); that the Roman army had some 57,000 heavy infantry, 14,000 skirmishers and 6,400 cavalry (p. 22); that Aemilius, on the right "position of honour", may have been in command that day (p. 23); that the Roman infantry stood "a little over thirty men deep, giving a frontage for the whole infantry line of about one mile" (p. 23); that the cavalry split was 1,600 citizen horse on the right and 4,800 allied on the left against 6,500 heavy horse and 3,500 Numidians (pp. 23–24); that the Africans stood in column and the Celts and Spaniards were "likely to have received orders to conduct a fighting withdrawal" (p. 24, labelled by him as likely); and that the traditional account of the slaughter "does not ring true", in part because the Carthaginian cavalry "would have been too few in number to seal the rear" (p. 25). His figures are his own reconstructions from Polybius; the plan labels them secondary.
- Ball, *Collecting the Field* (PhD thesis, Liverpool, 2016), pp. 88–89 and 107: no conclusive location; citing Daly (2002, pp. 32–35), "at least eight locations have been proposed" from the narrative and the suggested course of the river (fig. 4). Ball cites Polybius 110.2 for "treeless" (p. 87 table).

**Place (S69, S70).**
- The Italian Ministry of Culture page for the Canne della Battaglia museum and park (S69, read through a summarising fetch) says the site "stands on the hills that dominate the valley of the Ofanto river" and that "no archaeological documentation has yet been found regarding the battle". It gives no distances.
- Wikipedia (S70, tertiary, read as wikitext): the date 2 August 216 BCE (Roman calendar; the primary for the date was not read); citing Daly, Carthaginian infantry of about 8,000 Libyans, 16,000 Gauls (8,000 left in camp) and 8,000 Iberians, with 1,000–2,000 Balearic slingers and 6,000 javelin men; Hasdrubal with 6,000–7,000 horse and Hanno with 3,000–4,000 Numidians (citing Goldsworthy 2001, pp. 108, 112); a view that the crescent may have been natural curvature rather than design (citing Healy 1994, p. 84). None of these books was read.

**What was not found.** Any order text from either side; any Carthaginian account (doc 37: none survives); a clock time other than "just after sunrise" and "as soon as it grew light"; frontages or distances between the lines; the strength of each Carthaginian contingent from a primary source; the battlefield's location (S67, S68, S69); Appian's account; Polybius VI on the manipular legion; the date's primary source (Gellius or Macrobius); and the modern monographs: Daly 2002, Goldsworthy 2001, Healy 1994, Lazenby 1978, Walbank's *Commentary on Polybius* I (1957), Delbrück, Kromayer and Veith. A Daly PDF linked from Wikipedia is an unlicensed copy and was not opened.

## 2. Scenario frame (proposal)

- **Action.** The whole field engagement on the day, from the light-infantry screens to the closing of the pocket or its failure. Fixture `cannae`: "Center, wings and cavalry commands" (doc 37 §1). Decision: whether local decisions produce an encirclement and whether the Roman command can see and prevent it (doc 36).
- **Sides.** `roman` (attacker; the Romans crossed to give battle, S65 113, S66 45) and `carthaginian` (defender). Default player: `roman`, the consul in command (Terentius Varro, S65 113, S66 45), whose command detachment is with the allied cavalry on the left (S65 114, S66 45). Computer: `carthaginian`. All units are autonomous under AGENTS; the player changes intent only by a delivered order or signal. Headless first, both sides under scripted controls.
- **Map.** Abstract open plain with the river along the Roman right and the Carthaginian left (both sources agree on which flank the river covers: S65 113, S66 45–47). No compass bearing, no site registration (§7).
- **Start.** 08:00, at the first light-infantry contact. Sourced cue: deployment "just after sunrise" (S65 113), "as soon as it grew light" (S66 46). The hour is authored. **Deadline:** 16:00, 8 hours. Authored; the sources give only "the remainder of the day" (S66 51) and "till close on night" (S66 59).

### 2.1 What the engine can and cannot express at army scale

The engine was built for companies: units of tens of men on 50 m hexes in 30 s intervals. Read in `apps/poc/battle/`; nothing was run.

| Engine fact | Where | At army scale |
|---|---|---|
| Grid 24 by 21 hexes of 50 m (1.2 km by 1.05 km) | `grid.py:5-6` | Too small for a 1.6 km infantry line (S67 p. 23) plus cavalry wings. The entry validator refuses any other shape or hex size (`scenario_entry.py:321-323`) |
| An interval is 30 s | `scenario_entry.py:25`; delay text `engine.py:116` | An 8-hour day is 960 intervals; no entry can declare another length |
| One unit per hex, no swaps or stacking; contested hexes rotate | `engine.py:343`, `engine.py:363-364`, `engine.contest` (`engine.py:186-214`) | Usable: a deep Roman block that cannot pass through itself is the crowding of S65 115. Throughput through a gap is a count of whole units, not men |
| Move credit 45 to 115 per interval against a cost of 100 per open hex, the same for every unit | `engine.py:350`; `grid.cost` (`grid.py:33-36`) | About one hex an interval. Cavalry cannot move faster than infantry |
| A volley fires `min(ammo, strength)` rounds and spends that much ammunition | `engine.py:246` | A shock unit of 3,500 men empties its stock in a few intervals and then never fights again (`engine.py:381`) |
| Morale falls by 4 per man lost | `engine.py:403` | A unit of thousands loses all morale on its first exchange. The 12-man rout floor (`engine.py:408`) never applies |
| Fire hits the nearest visible enemy from any side; only units that declare a gun `facing` have an arc | `engine.volley` (`engine.py:237-255`); `facing.py:1-16` | No flank or rear effect. An African charge into a flank equals a frontal one |
| One command detachment per side; every order goes from it to a unit | `command.voice_reach` (`command.py:14-19`); `comms.command_unit` (`comms.py:34-36`) | No wing or centre commander, so no army-to-sector-to-formation hierarchy (doc 36) |
| Runner cost 200 per interval (2 open hexes), packets expire after 20 intervals | `comms.py:10-11` | Usable as a mounted messenger only if the hex and interval change together (§2.2) |
| A trumpet `broadcast` with reach and block hexes | `broadcast.hears` (`broadcast.py:15-28`); profile `comms.py:30-31` | Usable for a Roman battle signal (S66 45) |
| `exploit` doctrine: press toward `press_to` after a start or arrival trigger, `recall_binding` | `standing.exploit` (`standing.py:90-146`) | Usable for the Roman press (S65 115 "pursuing them furiously"). No trigger on "an enemy has passed my flank" |
| Withdraw: one hex away from threats, held 3 intervals | `engine.py:335`; `tactics_v11.decide` (`tactics_v11.py:118-127`) | No bounded, ordered yield that keeps contact |
| Per-unit `observation_range`, capped at 7 hexes | `recon.py:32`; `grid.visible` (`grid.py:88-90`) | Usable for Livy's dust (S66 46) |
| Surrender with a conserved captive account | `captives.py:1-12` | A whole unit yields at once; usable later for prisoners |
| Victory kinds `hold-objective`, `hold-compound`, `seize-and-hold`, `raid-and-return`, `recover-force` | `victory.py:512` | None scores an enclosure |
| Combine refuses more than 80 troops | `formations.py:6`, `formations_v5.py:6` | Split and combine would have to stay off |

### 2.2 Scale options (authored)

The default holds the grid at 24 by 21, so only the hex size and the interval change. Its arithmetic rests on S67: 16 heavy units of about 3,550 men on 8 hexes of 200 m give a 1.6 km front about 35 men deep, Samuels's "a little over thirty men deep" and "about one mile" (p. 23).

| Option | Hex | Interval | Map | Unit | Units | Fit |
|---|---|---|---|---|---|---|
| **A (default)** | 200 m | 180 s | 4.8 km by 4.2 km | One legion or one allied *ala* (S65 107.9–107.13); Carthaginian contingents of 1,700–5,000 | 41 | One hex an interval is 4 km/h on foot; cavalry at 3 hexes is 12 km/h. 8 hours is 160 intervals |
| B | 150 m | 120 s | 3.6 km by 3.15 km | As A | 41 | Tighter flanks; the Roman block is 10.7 hexes wide if placed at S67's frontage, so it does not divide evenly; 240 intervals |
| C | 100 m | 60 s | needs a 48 by 42 grid | Half-legion (hastati and principes, or triarii and velites) | about 80 | Needs a variable grid size, not only a hex size; 480 intervals |
| D | 50 m sector crop | 30 s | the current grid | Maniple groups | about 30 | Runs on today's engine shape, but shows one flank, not an envelopment; doc 36 rules this out as the case |

A, B and C all need gap 1 (§10). Only D fits today's validator, and it cannot answer doc 36's question.

## 3. Intent registers

### Roman (sourced, through hostile or later narrators)

| Item | Statement | Label |
|---|---|---|
| Object | Give battle; the Senate decided "to give the enemy battle" and sent Aemilius "with orders to decide the issue" | Sourced: S65 107.7, 108.1 |
| Method | Break the centre by weight: maniples closer together, depth "many times" the front | Sourced: S65 113; S67 p. 23 (a deliberate choice, his inference) |
| Flanks | Cavalry on both wings; the river covers the right | Sourced: S65 113, S66 45 |
| Signal | The commander shows the signal for battle | Sourced: S66 45 |
| Camp force | 10,000 foot to storm the Carthaginian camp during the battle | Sourced: S65 117.7 onward. Off map (§8) |
| Who commanded | Varro (S65 113, S66 45), or Aemilius on the right (S67 p. 23) | Disclosed conflict; variant |
| Reserve and retreat lane | None in either source | Doc 36 asks for it as a second run, not as history |

### Carthaginian (no Carthaginian source; all through Polybius and Livy)

| Item | Statement | Label |
|---|---|---|
| Choice of ground | Fight on open ground where cavalry decide | Sourced as Hannibal's speech: S65 111; S66 44 |
| Centre | Advance the central Spanish and Celtic companies in a crescent and begin the action with them | Sourced: S65 113 |
| Africans | Held as a reserve on the shoulders | Sourced: S65 113; in column (S67 p. 24, his reading) |
| Design | The Romans caught "as Hannibal had designed" | Sourced as Polybius's judgment: S65 115. Disputed (S70, citing Healy) |
| Africans' turn | On the situation, not on an order: "the situation itself indicating to them how to act" | Sourced: S65 115. A local trigger |
| Cavalry | Hasdrubal's own decision to leave the pursuit and charge the rear | Sourced: S65 116 ("appears to have acted with great skill and prudence") |
| Yield | A fighting withdrawal ordered beforehand | Inferred: S67 p. 24 calls it likely; Polybius says the centre was "borne down" (115) |

### Reconstruction (authored)

- **Carthaginian C1 (default):** centre units yield up to 3 hexes when pressed, without routing; Africans wheel inward when a Roman unit stands past their front row within 2 hexes; Hasdrubal's horse, once the Roman right cavalry is routed or lost, rides behind the Roman line to the Numidian wing, then charges the rear; Numidians skirmish and pin.
- **Carthaginian C2 (no design):** the centre has no yield doctrine; it holds or breaks under the ordinary rules. The Africans keep the wheel trigger. This is the failed-pincer test doc 36 asks for.
- **Roman R1 (default):** heavy infantry `exploit` toward the Carthaginian rear row once the light troops have cleared, `recall_binding` false; cavalry hold their wings; the light troops screen then fall back through the intervals (approximated as moving to the rear rows).
- **Roman R2 (reserve):** two allied *alae* held at the rear as a reserve with a hold order on the lane to the smaller camp exit.

## 4. Order of events

No source gives clock times. The sequence is S65's; the spacing is not sourced.

| Step | Event | Source |
|---|---|---|
| 1 | Numidians cut the lesser camp's water party | S65 112; S66 45 |
| 2 | Varro shows the signal, crosses and forms line; the lesser camp's troops join | S65 113; S66 45 |
| 3 | Hannibal crosses at two places, forms line, advances the crescent | S65 113; S66 46 |
| 4 | Light troops skirmish, neither side gaining | S65 115; S66 47 |
| 5 | Spanish and Celtic horse defeat the Roman horse by the river | S65 115; S66 47 |
| 6 | The heavy infantry meet; the centre is pressed back; the Romans crowd inward | S65 115; S66 47 |
| 7 | The Romans pass the Africans, who turn inward on both flanks | S65 115; S66 47 |
| 8 | Hasdrubal rides to the Numidian wing; the allied horse flee; the Numidians pursue | S65 116; S66 48 (Livy's version differs) |
| 9 | Hasdrubal charges the Roman rear at several points | S65 116 |
| 10 | Aemilius falls in the centre; the Romans are surrounded and cut down | S65 116; S66 49 |
| 11 | Fugitives to the two camps and to Cannae village; Varro to Venusia | S66 49; S65 116 |
| 12 | The camp force is beaten at the Carthaginian camp | S65 117 (off map) |

## 5. Victory condition (proposal)

Doc 36 asks for a verdict on movement and route capacity, not on which army wins, and for a model that allows a failed pincer. No existing kind scores an enclosure (`victory.py:512`).

- **Proposed kind `encircle` (authored).** Each interval, a Roman unit counts as **enclosed** when no path runs from its hex to any declared exit hex, with hexes held by a Carthaginian unit, and hexes within `zoc` of one, treated as blocked. This is the geometry of `test_escape_routes.py`, run on the live state. The defender (Carthaginian) wins at the deadline when enclosed, lost or surrendered strength reaches `min_enclosed_pct` of the Roman heavy infantry's starting strength. The attacker (Roman) wins at once if `centre_break` of the Carthaginian centre units are routed or lost before that; otherwise it wins at the deadline. The Roman win reads "army not enclosed" or "centre broken", not a historical result.
- **Exits.** Three exit hexes on the Roman side of the map, standing in for the destinations Livy names: the smaller camp, the larger camp and Cannae village (S66 49). The mapping is inferred; the positions are authored.
- **Recorded every interval, not scored** (doc 36's list): each sector's frontage in hexes; facing as the bearing to the nearest enemy; morale as the stand-in for cohesion; the number of open exit paths and the narrowest hex count on them (passage capacity); each signal and messenger receipt; the interval each cavalry unit leaves its first fight; units and men reaching an exit (throughput); enclosed units and men. The interval the last route closes on the ground and the interval either headquarters first has a delivered report of it are two separate records. Groups outside the pocket are counted apart. Losses are compared with S65 117, S66 49 and S67 p. 25 by order of magnitude only.

## 6. Units, weapons, communications

**Roster (proposal; strengths authored on sourced totals).** Totals: Roman 56,800 heavy, 14,000 light, 6,400 horse (S67 p. 22, reconstructed from S65 107 and 113); Carthaginian 40,000 foot and 10,000 horse (S65 114, S66 46). The Carthaginian split by contingent is authored; the figures on S70 rest on Daly and Goldsworthy, which were not read.

| Unit | Side | Count × strength | Provenance |
|---|---|---|---|
| `L1`–`L8` legions | roman | 8 × 3,550 | Structure sourced: eight legions (S65 107.9). Heavy share authored from S67 p. 22 |
| `A1`–`A8` allied *alae* | roman | 8 × 3,550 | Structure sourced: allied infantry equal to the legions (S65 107.12) |
| `V1`–`V4` light infantry | roman | 4 × 3,500 | S67 p. 22 total; split authored |
| `EQ` citizen cavalry, right by the river | roman | 1 × 1,600 | S67 p. 23; S65 113 for the position |
| `SC1`, `SC2` allied cavalry, left; `SC1` is the command detachment (Varro) | roman | 2 × 2,400 | S67 p. 23; S65 114 for Terentius on the left |
| `AF1`, `AF2` Africans, left and right shoulders | carthaginian | 2 × 5,000 | Authored. S65 113: half on each side |
| `C1`–`C8` Spanish and Celtic foot, alternating; `C4` is the command detachment (Hannibal and Mago) | carthaginian | 8 × 2,750 | Authored. S65 114 for alternate companies; S67 p. 25 "about 25,000" for this body; S65 114 and 116 for Hannibal |
| `LT1`–`LT3` slingers and spearmen | carthaginian | 3 × 2,670 | Authored to make 40,000 foot; S65 113, S66 46 |
| `HC1`–`HC3` Spanish and Celtic horse (Hasdrubal) | carthaginian | 3 × 2,170 | S67 p. 24 (6,500); S65 113 for the river flank |
| `NU1`, `NU2` Numidians (Hanno or Maharbal) | carthaginian | 2 × 1,750 | S67 p. 24 (3,500) |

That is 23 Roman and 18 Carthaginian units. The Roman camp force (10,000, S65 117) and the Carthaginian camp guard are off the map.

**Deployment (authored on sourced order).** Roman heavy infantry as a block 8 hexes wide and 2 deep, legions in front and *alae* behind, standing for depth "many times" the front (S65 113); light troops one row ahead; cavalry on each flank. Carthaginian centre `C3`–`C6` one hex ahead of `C1`, `C2`, `C7`, `C8` (the crescent, S65 113); Africans in column one hex behind each end of the centre (S67 p. 24); light troops one row ahead; Hasdrubal's horse between the centre and the river; Numidians on the open flank. Lines 3 hexes (600 m) apart.

**Weapons (authored; at 200 m every class has range 1).**

| Class | Used by | Range | Effect | Ammunition | Basis |
|---|---|---|---|---|---|
| `heavy infantry` | L, A, AF, C | 1 | 100 | none (gap 3) | Close fighting (S65 115). The Africans' captured Roman arms (S65 114) give them no separate class |
| `light infantry` | V, LT | 1 | 40 | yes | Slings and javelins (S65 113, S66 46, S66 49) |
| `heavy cavalry` | EQ, SC, HC | 1 | 100 | none | S65 115: dismounted fighting by the river |
| `light cavalry` | NU | 1 | 40 | yes | S65 116: the Numidians' "peculiar mode of fighting", drawing off and attacking from all sides |

One range for every class, so `tactics_v10` would serve; the entry should still select `tactics_v11` ([55](55-tactics-v11-threat-range.md)) so that later variants can add a range.

**Movement (authored).** Infantry one hex an interval (today's credit, `engine.py:350`). Cavalry 3 hexes an interval (gap 2). Numidians 3.

**Observation.** 7 hexes (1.4 km), the `grid.visible` cap. Variant `dust`: Roman units 3 hexes (S66 46).

**Command and communications.** Profiles `roman-216-v1` and `carthage-216-v1`, authored. Both have voice within 1 hex and a mounted messenger at today's runner cost (200 an interval, which is 2 open hexes, 8 km/h at option A; packets expire after 20 intervals, 1 hour). The Roman profile adds the trumpet `broadcast` for the battle signal (S66 45; reach authored at 6 hexes). No Carthaginian signal is sourced. Sector commanders (gap 5): Roman right Aemilius with `EQ`, centre Servilius and Atilius with `L4`, left Varro with `SC1` (S65 114; S66 40 puts Servilius in the lesser camp); Carthaginian left Hasdrubal with `HC1`, centre Hannibal with `C4`, right Hanno with `NU1` (S65 114; Maharbal in S66 46). Voice `republic-en-v1` (doc 60) for the Roman side; a Carthaginian voice is not proposed, since the computer side has no voice.

## 7. Terrain, with sources

| Feature | Fact | Source |
|---|---|---|
| Plain | Flat and treeless; ground for cavalry | S65 110.2, 111; S66 44 |
| River | The Aufidus covers the Roman right and the Carthaginian left; the cavalry by it has no room to manoeuvre | S65 113; S66 45, 47 |
| Crossings | Both armies cross the river to form; Hannibal at two places | S65 113; S66 45–46 |
| Camps | Two Roman camps on opposite banks; the smaller east of the ford | S65 110.8–110.11; S66 44 |
| Cannae | A razed town with a citadel commanding the district; an unfortified village after the battle | S65 107.2–107.5; S66 49 |
| Dust and wind | Wind against the Romans, dust in their faces | S66 43, 46. Polybius: neither side troubled by the sun (114) |
| Location | Not established; at least eight proposals; no archaeology of the battle | S67 p. 7; S68 pp. 88–89 (citing Daly 2002, pp. 32–35); S69 |

**Map (authored).** 24 by 21 hexes of 200 m, open ground, elevation 0, with an impassable river along one side column. Passable cells only between the river and the Roman right cavalry, 2 hexes wide, standing for "no room" (S66 47). Exits on the Roman map edge as in §5. Because the sources disagree on facing (S65 113 south, S66 46 north, S70 east) and the site is unknown, the map carries no compass bearing and no registration; wind and dust enter only as the `dust` variant.

## 8. Proposed defaults and named variants

**Every authored value in the default.**

| # | Value | Default | Basis |
|---|---|---|---|
| 1 | Hex size | 200 m | Authored; S67 p. 23 frontage |
| 2 | Interval | 180 s | Authored; one hex at 4 km/h |
| 3 | Grid | 24 by 21 (unchanged) | Engine shape |
| 4 | Start | 08:00 | Authored; S65 113 "just after sunrise" |
| 5 | Deadline | 16:00 (160 intervals) | Authored |
| 6 | Roman unit strengths | 16 × 3,550, 4 × 3,500, 1,600, 2 × 2,400 | Authored on S67 p. 22 |
| 7 | Carthaginian unit strengths | 2 × 5,000, 8 × 2,750, 3 × 2,670, 3 × 2,170, 2 × 1,750 | Authored on S65 114, S67 pp. 24–25 |
| 8 | Roman block | 8 wide, 2 deep, legions in front | Authored; S65 113 |
| 9 | Crescent offset | 1 hex for C3–C6 | Authored; S65 113 |
| 10 | Line spacing | 3 hexes | Authored |
| 11 | River lane | 2 hexes | Authored; S66 47 |
| 12 | Weapon effects | 100 heavy, 40 light | Authored |
| 13 | Cavalry speed | 3 hexes an interval | Authored |
| 14 | Observation | 7 hexes | Engine cap |
| 15 | Voice reach | 1 hex | Authored |
| 16 | Messenger | 2 hexes an interval, expiry 20 | Engine rates, accepted |
| 17 | Battle signal reach | 6 hexes | Authored |
| 18 | Yield limit (C1) | 3 hexes | Authored; S67 p. 24 |
| 19 | Wheel trigger (C1) | a Roman unit past the African's front row within 2 hexes | Authored; S65 115 |
| 20 | Hasdrubal's trigger (C1) | the Roman right cavalry routed or lost | Authored; S65 116 |
| 21 | Roman press (R1) | `exploit` to the Carthaginian rear row, `recall_binding` false, `max_loss_pct` 50 | Authored; S65 115 |
| 22 | Victory `zoc` | 1 | Authored |
| 23 | `min_enclosed_pct` | 50 | Authored |
| 24 | `centre_break` | 5 of 8 centre units | Authored |
| 25 | Exit hexes | 3, on the Roman edge | Inferred from S66 49; positions authored |
| 26 | Morale and loss scaling | per gap 3, values to be set at implementation | Authored |
| 27 | Player | Roman, Varro at `SC1` | Sourced command (S65 113); choice authored |

**Named variants.**

| Name | What it changes | Label |
|---|---|---|
| **Default `cannae-envelopment`** | §2 to §7; C1 against R1 | Authored on sourced anchors |
| `no-design` | C2: no yield doctrine | Disputed design (S65 115; S70 citing Healy) |
| `cavalry-delayed` | Hasdrubal's trigger plus 10, 20, 40 intervals | Doc 36 |
| `one-wing-fixed` | `AF1` (then `AF2`) has no wheel trigger | Doc 36 |
| `roman-reserve` | R2: two *alae* held with a retreat lane | Doc 36; no source |
| `aemilius-commands` | Command detachment and player at `EQ` | S67 p. 23 |
| `roman-horse-holds` | Roman cavalry strength doubled | Authored; S67 p. 26 on timing |
| `dust` | Roman observation 3 hexes | S66 46 |
| `deserters` | 500 Numidians start in the Roman rear and attack at a scripted interval | S66 48; not in S65 |
| `wide-front` | Roman block 16 wide, 1 deep | Authored control on S65 113 |
| `zoc-0` | Only occupied hexes block an exit path | Authored; tests S67 p. 25's claim that the cavalry could not seal the rear |
| `scale-b` | Option B: 150 m, 120 s | Authored |

## 9. Open questions for the owner

1. **Scale.** Accept option A (200 m hexes, 180 s intervals, the 24 by 21 grid, one unit per legion or *ala*)? Or B (150 m, 120 s), or C (100 m, 60 s, a larger grid)?
2. **Whole field.** Model the whole engagement on one map (proposed), not a sector? Doc 36 asks for the envelopment, which a sector cannot show.
3. **Orientation.** Leave the compass out and keep only "river on the Roman right", since Polybius, Livy and modern accounts disagree?
4. **Player and commander.** Roman player as Varro (Polybius, Livy), with Aemilius in command as a variant (Samuels)? Or a Carthaginian player?
5. **The yield.** Default to a designed yield (C1, Polybius's "as Hannibal had designed"), with no design (C2) as the variant? Or the reverse?
6. **Numbers.** Use Samuels's reconstructed splits (1,600 and 4,800 Roman horse; 6,500 and 3,500 Carthaginian) and an authored Carthaginian infantry split, until Daly or Goldsworthy is read?
7. **Livy-only events.** Keep the false deserters (S66 48) out of the default?
8. **Off-map forces.** Leave the Roman camp force and the Carthaginian camp guard (S65 117) off the map?
9. **Victory.** Accept `encircle` with `zoc` 1, 50 per cent enclosed and a 5-of-8 centre break, with losses recorded only as a magnitude check?
10. **Hierarchy before the first run.** Build sector commanders (gap 5, size L) before a first run, or run first with scripted controls issuing each sector's orders and add the hierarchy after?
11. **Sources.** Pull Daly 2002, Goldsworthy 2001, Walbank's *Commentary* I, Lazenby 1978 and Polybius VI before a run?
12. **Headless only?** Same as Pegasus, Hill 223 and Gergovia?

## 10. Engine gaps

Engine facts were read in `apps/poc/battle/`; none was run. **Must-have** = the first entry cannot ask doc 36's question without it. **Later** = a variant or refinement. Size: S under a day, M one to three days, L more.

**Must-have**

| # | Gap | Where | Size | Note |
|---|---|---|---|---|
| 1 | **Declared scale.** The entry must declare `metres_per_hex` and `seconds_per_turn`. Today the validator refuses anything but 24 by 21 by 50 m (`scenario_entry.py:321-323`), the interval is a constant (`scenario_entry.py:25`), and delay text multiplies by 30 (`engine.py:116`) | `grid.py:6`, `scenario_entry.py`, `engine.py`, presentation and replay text | M | Grid size stays fixed (option A); every 50 m and 30 s reader takes the entry's value; existing digests unchanged |
| 2 | **Per-unit speed.** Every unit earns the same move credit (`engine.py:350`) | `engine.py`, `scenario_units.KEYS` (`scenario_units.py:21`) | S | A `move_rate` unit key; cavalry 3 hexes |
| 3 | **Army-scale losses and morale.** Morale falls 4 per man lost (`engine.py:403`); a volley spends ammunition equal to strength (`engine.py:246`) and a unit with none stops firing (`engine.py:381`); damage scales with absolute strength (`engine.py:249`) | `engine.py` | M | Morale loss as a share of strength; a no-ammunition shock class; a per-interval loss rate calibrated so the day takes hours, set as an authored target and labelled |
| 4 | **Flank and rear.** Fire and losses take no account of the attacker's bearing (`engine.py:237-255`); only declared guns have a facing (`facing.py:1-16`) | `engine.py`, `facing.py` | M | A facing for every unit of a declaring entry (front set by its last movement or order), and a flank or rear multiplier on losses and morale. The core of S65 115–116 |
| 5 | **Sector commanders.** One command detachment per side (`command.py:14-19`, `comms.py:34-36`) | `command.py`, `comms.py`, `orders.py`, the entry schema | L | A sector command with a commander unit, member units and its own view; army orders reach it by messenger; it issues orders to its units from its own delivered reports. Doc 36's hierarchy |
| 6 | **Conditional local doctrines.** `exploit` triggers only on `start` or `arrival` (`standing.py:90-91`); withdraw is a 3-interval step (`engine.py:335`, `tactics_v11.py:118-127`) | `standing.py`, `tactics_v11.py` | M | `wheel` (turn on an observed enemy past the flank, S65 115) and `yield` (step back up to N hexes under pressure without routing, S67 p. 24), each read from the unit's own sightings |
| 7 | **Enclosure measure and `encircle` kind** (§5) | `victory.py`, analysis records | M | Reuse `grid.path` with blocked hexes as `test_escape_routes.py` does; record ground and headquarters times separately |
| 8 | **Profiles** `roman-216-v1` and `carthage-216-v1` | `comms.py`, `scenario_entry.COMMUNICATIONS` (`scenario_entry.py:33-35`) | S | Data; voice 1, messenger rates, Roman trumpet |
| 9 | **Run time at 41 units.** Sightings loop over all units (`recon.py:37`, `recon.py:66`); nothing over about 20 units has been run (doc 57 §10) | measurement only | S | Time 160 intervals with 41 units before any feature work |

**Later**

- Throughput by men, not units: one unit per hex with no swaps (`engine.py:363-364`) makes a gap pass whole units; a gap's capacity in men an interval would need partial movement.
- Routed units with no path stay put: a routed unit heads for its rally point (`engine.py:347`) and stands if every route is blocked; a pocketed unit should fight, yield or try a breakout.
- Surrender in the pocket and the prisoner counts (`captives.py`; S66 49).
- Splitting a deep block into its front and rear lines; split and combine refuse more than 80 (`formations.py:6`).
- Officer losses at this scale (29 tribunes, S66 49; `command.officer_losses`).
- The Roman camp assault and the camp guard (S65 117), and the night breakout (S66 50).
- Livy's false deserters as a scripted arrival in the Roman rear (S66 48).
- Dismounted cavalry fighting (S65 115, S66 49) beyond a shared class.
- A variable grid size for option C.
- Scripted controls in a `cannae_policy.py` beside `gergovia_policy.py`, with source locators on each order.

## 11. Sources used in this pass

S65 to S70 in [09 — sources](09-sources.md#cannae-source-pass--2026-11-07). Access date 2026-11-07 (UTC). Doc 36 and the battle-gallery note cited Polybius and Livy by link without S-ids; this pass gives them S65 and S66.
