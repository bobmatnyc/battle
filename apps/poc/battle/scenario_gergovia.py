"""Gergovia, 52 BCE: a catalog entry and its variants (poc-13).

Why: the sixth comparison (docs/research/34, 37 §1) asks what a forward
detachment does when the recall fails to reach it. Doc 57 plans the upper-slope
sector, from the midslope stone wall to the town wall, with the trumpet recall
and its failure; doc 60 supplies the rules (broadcast signal with reach and
block, exploit doctrine, recover-force victory, Roman profile and voice) and
doc 58 the declared rout threshold.
What: ``gergovia_entry`` builds one ``ScenarioEntry``; ``GERGOVIA_RECALL`` is
doc 57 §8's default (trumpet recall at interval 40, reach 8 hexes, a valley
block, Roman S1, Gallic G1), accepted with every other doc 57 §9 default by
the Dc0 ruling of 2026-11-07. ``VARIANTS`` holds doc 57 §8's named variants
that the engine can build, each with its question and source. The map is
authored and schematic. Every field's basis is in the entry's ``provenance``;
the runs are docs/research/62.
Test: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`,
`test_each_named_variant_differs_only_in_its_own_question`.
"""

from .grid import COLS, METRES_PER_HEX, ROWS, key
from .presentation import ROMAN_VOICE_PROFILE
from .scenario_broadcast import BroadcastEntry
from .scenario_command import ROMAN_COMMUNICATIONS, TACTICS_V11, CommandEntry, WeaponEntry
from .scenario_concord import Variant
from .scenario_entry import (
    ORDER_CATALOG, RULES_VERSION, FireEntry, MapEntry, ScenarioEntry, SideEntry, UnitEntry, VictoryEntry,
)

DC0 = "default per Dc0 ruling 2026-11-07"  # doc 57 §9: every open question takes the proposed default.
# Authored, schematic layout (doc 57 §2, §7). North is row 0: the town. The
# town wall is row 1, the stone wall row 19, 18 hexes below it (doc 57 §2:
# about 600 paces, "almost in the middle of the hill", inferred from VII.46).
# Row 20 is the lower slope. The valley between the Tenth and the other
# legions (VII.47) runs down columns 16-17; the Tenth stands east of it.
TOWN_WALL_ROW, STONE_WALL_ROW = 1, 19
VALLEY_COLS, VALLEY_TOP = (16, 17), 8
GATE = (11, 1)  # S60 VII.47, VII.50: the town gates; the hex is authored.
BELOW_GATE = (11, 2)  # The hex outside the gate: the ardour press ends here.
TENTH = (21, 19)  # Caesar with the Tenth on the lower, more level ground (VII.47, VII.51).
RALLY = (20, 19)  # The Tenth's line, the recall's destination and the recover-force rally hex.
RALLY_RADIUS = 2
LESSER_CAMP = (0, 20)  # Sextius at the lesser camp, off the map to the south-west (VII.49).
SEXTIUS_POST = (6, 19)  # The foot of the hill on the enemy's right (VII.49).
UNDER_WALL = {"GR": (9, 2), "GC": (13, 2)}  # VII.48: the returning Gauls gather beneath the wall.
PUSH_TO = (11, 18)  # VII.51: the Gauls drive down to the stone wall, then go back.
TURNS_PER_HOUR = 120  # 30-second intervals.
DEADLINE = 2 * TURNS_PER_HOUR  # Doc 57 §2: 120 minutes, authored; VII.48 says only a "long continuation".
RECALL_TURN = 40  # Doc 57 §8: the default recall at interval 40 (12:20); the time is not sourced.
RECALL_REACH = 8  # Doc 57 §8: 8 hexes (400 m), authored.
RETURN_TURN = 40  # The Gallic masses are ordered back as the recall sounds (VII.47-48 order; authored).
SEXTIUS_TURN = 60  # Doc 57 §8 sextius-cover: Sextius is ordered out at interval 60 (12:30), authored.
VOICE_REACH = 2  # A tribune's or legate's voice: 2 hexes (100 m), authored.
STRENGTH = 60  # Doc 57 §6: Eighth Legion century groups of 60, authored.
SHOCK, MISSILE = "shock infantry", "missile troops"
# Scripted controls (battle/gergovia_policy.py); ids live here so the entry needs no policy import.
ROMAN_POLICY = "scripted-gergovia-roman-v1"
ROMAN_NO_COVER_POLICY = "scripted-gergovia-roman-no-cover-v1"
ROMAN_RUNNER_POLICY = "scripted-gergovia-roman-runner-v1"
GALLIC_POLICY = "scripted-gergovia-gallic-v1"
GALLIC_DELAYS = (10, 20, 40)  # Doc 57 §8 gallic-delay: intervals added to RETURN_TURN.


def gallic_delay_policy(delay):
    return f"scripted-gergovia-gallic-delay-{delay}-v1"


VALLEY = tuple((c, r) for c in VALLEY_COLS for r in range(VALLEY_TOP, ROWS))


def _cell(c, r):
    """Town, town wall, camps, stone wall, lower slope and valley (doc 57 §7, authored)."""
    elevation = 80 - 2 * r  # A steady rise to the town; no contour map was obtained (doc 57 §7).
    if (c, r) in VALLEY:  # VII.47: "a very large valley"; depth, cost and cover authored.
        return {"elevation": elevation - 14, "terrain": "open", "move_cost": 140, "cover": 10, "area": "valley"}
    if r < TOWN_WALL_ROW:
        return {"elevation": elevation, "terrain": "open", "move_cost": 110, "cover": 30, "area": "oppidum"}
    if r == TOWN_WALL_ROW:  # The town wall, as terrain: the engine has no free-standing wall (doc 57 §10).
        gate = (c, r) == GATE
        return {"elevation": elevation, "terrain": "open", "move_cost": 150 if gate else 220, "cover": 40,
                "obstacle_height": 3, "area": "gate" if gate else "town-wall"}
    if r == STONE_WALL_ROW:  # VII.46: a six-foot wall of large stones, as terrain.
        return {"elevation": elevation, "terrain": "open", "move_cost": 160, "cover": 30, "obstacle_height": 2,
                "area": "stone-wall"}
    if r > STONE_WALL_ROW or c > VALLEY_COLS[1]:
        return {"elevation": elevation, "terrain": "open", "move_cost": 110, "cover": 10, "area": "lower-slope"}
    # VII.46: the upper hill "full of the camps of the Gauls, very close to one another".
    return {"elevation": elevation, "terrain": "open", "move_cost": 120, "cover": 20, "area": "gallic-camps"}


def terrain():
    cells = {}
    for r in range(ROWS):
        for c in range(COLS):
            cells[key([c, r])] = {"pos": [c, r], **_cell(c, r)}
    return cells


FEATURES = {"roads": (), "buildings": (), "works": ()}


def _men(n, weapon, **extra):
    return {"initial": n, "strength": n, "ammo": n * 20, "weapon_class": weapon, **extra}


FORWARD = ("R8a", "R8b", "R8c", "R8d", "R8f")
CENTURIES = FORWARD[:4]
# Doc 57 §3 S1: the forward groups, past the stone wall in the taken camps,
# pursue up the slope toward the gate (S60 VII.47: they pursued to the wall and
# gates); a group that hears the recall stops and obeys it, a group that does
# not hear it keeps pressing (docs/research/60 §2, recall_binding true). The
# pursuit is the battle's opening state (trigger "start"; 57 §2, the camps taken).
PURSUIT = {"trigger": "start", "press_to": list(BELOW_GATE), "recall_binding": True, "max_loss_pct": 50}
# Doc 57 §3 S2 (ardour): the same pursuit, but a heard recall is taken up only
# once the press stops (recall_binding false, docs/research/60 §2).
ARDOUR = {**PURSUIT, "recall_binding": False}


def roman_units(strength=STRENGTH, exploit=PURSUIT, officers=None):
    """The forward groups pursue toward the gate until recalled (S1);
    ``exploit`` ARDOUR and ``officers`` are the ardour and leaders-fall readings."""
    extra = {"exploit": dict(exploit)}
    if officers:
        extra["officers"] = officers

    def group(n, **more):
        return _men(n, SHOCK, **{k: (dict(v) if isinstance(v, dict) else v) for k, v in extra.items()}, **more)

    return (
        # VII.47, VII.51: the Tenth with Caesar, on level ground in reserve.
        UnitEntry("RX", "roman", "Tenth Legion · reserve with Caesar", TENTH, _men(80, SHOCK)),
        UnitEntry("R8a", "roman", "Eighth Legion · century group, east", (14, 17), group(strength)),
        UnitEntry("R8b", "roman", "Eighth Legion · century group, centre-east", (12, 17), group(strength)),
        UnitEntry("R8c", "roman", "Eighth Legion · century group, centre-west", (10, 17), group(strength)),
        UnitEntry("R8d", "roman", "Eighth Legion · century group, west", (8, 17), group(strength)),
        # VII.47: Centurion Lucius Fabius and three men of his company; below the 12-man default rout.
        UnitEntry("R8f", "roman", "Eighth Legion · Fabius and three men", (10, 16), group(4, rout_strength=0)),
        # VII.49, VII.51: Sextius's cohorts of the Thirteenth at the lesser camp.
        UnitEntry("R13", "roman", "Thirteenth Legion · Sextius's cohorts", LESSER_CAMP, _men(80, SHOCK)),
    )


def gallic_units(aedui=False):
    units = (
        # VII.46, VII.48: the town wall held; garrison and camp groups, strengths authored.
        UnitEntry("G1", "gallic", "Wall garrison, west", (7, 1), _men(60, MISSILE)),
        UnitEntry("G2", "gallic", "Wall garrison at the gate", GATE, _men(60, MISSILE)),
        UnitEntry("G3", "gallic", "Wall garrison, centre-east", (13, 1), _men(60, MISSILE)),
        UnitEntry("G4", "gallic", "Wall garrison, east", (15, 1), _men(60, MISSILE)),
        # VII.48: from the other part of the town, cavalry first; strengths authored.
        UnitEntry("GR", "gallic", "Returning force from the far side of the town", (2, 0), _men(120, SHOCK)),
        UnitEntry("GC", "gallic", "Returning cavalry", (3, 0), _men(40, SHOCK)),
    )
    if aedui:
        # VII.50: the Aedui on the exposed flank, taken for enemies. Doc 57 §10
        # workaround: a detachment on the Gallic side that holds fire.
        units += (UnitEntry("AE", "gallic", "Aedui detachment on the right, taken for enemies", (15, 14),
                            _men(60, SHOCK, fire_posture="hold_fire")),)
    return units


WEAPONS = {
    SHOCK: WeaponEntry(range_hexes=1, effect_pct=100,
                       basis="authored: hand-to-hand, the 'close fight' (S60 VII.50); the sources read name no "
                             "pilum or sword (doc 57 §6)"),
    MISSILE: WeaponEntry(range_hexes=3, effect_pct=70,
                         basis="authored: stones and javelins from the wall (S61 Dio 40.36.3); 150 m (doc 57 §6)"),
}
COMMAND = CommandEntry(succession={"roman": ("R13",)},
                       basis="authored: if the Tenth's command group falls, Sextius takes command; no source "
                             "names a successor; no Gallic successor is recorded")
FIRE = FireEntry(basis="authored: every group fires except the Aedui of aedui-misread, who hold fire (doc 57 "
                       "§10 workaround)")


def recall(reach=RECALL_REACH, block=VALLEY):
    return BroadcastEntry(
        id="recall", side="roman", kind="recall", reach=reach, stance="retreat", destination=RALLY,
        meaning="The trumpet sounds the retreat: fall back to the Tenth's line.", turn=RECALL_TURN,
        block_hexes=tuple(block),
        basis=f"sourced: Caesar sounds the retreat and the legions across 'a very large valley' do not hear it "
              f"(S60 VII.47); the interval {RECALL_TURN}, the {reach}-hex reach and the block hexes are authored "
              f"(doc 57 §8)")


ROMAN_MISSION = (
    "You are Caesar, with the Tenth Legion in reserve below the Gallic camps on the hill of Gergovia. The "
    "camps are taken by surprise, as you intended: success depended on a surprise, not on a battle. Your "
    "mission: bring the forward century groups back to the Tenth's line before the Gallic masses return, "
    "by the end of the second hour after noon.")
GALLIC_MISSION = (
    "You command the Gauls on the hill of Gergovia. The Romans have taken the camps below the town wall "
    "while your forces were drawn off to the far hill. Your mission: hold the town wall, bring the masses "
    "back from the far side of the town, and drive the Romans down the hill.")

PROVENANCE = {
    "location": "sourced: the hill of Gergovia, the upper slope between the midslope stone wall and the town "
                "wall (S60 VII.46); the site is Merdogne, renamed Gergovie in 1865 (S64, tertiary)",
    "date": "sourced: 52 BCE (the year of the campaign); Caesar gives no day, and VII.55 shows snow-melt in "
            "the Loire soon after (doc 57 §1); the date is the year alone, and the season 'spring' is inferred",
    "start_time": f"authored: 12:00 with the camps taken (doc 57 §2), on the sourced cue that Teutomarus 'had "
                  f"gone to rest at noon' when the camps were taken (S60 VII.46); {DC0} (doc 57 §9 q2)",
    "deadline": f"authored: 120 minutes, 240 intervals; VII.48 gives only a 'long continuation' (doc 57 §2); "
                f"{DC0} (doc 57 §9 q2)",
    "weather": "authored: daylight, fixed POC condition; no weather is read (doc 57 §6 observation)",
    "sides": "sourced: Caesar's legions against the Gauls under Vercingetorix (S60 VII.34-VII.51); no Gallic "
             "account survives (S64)",
    "player_side": f"authored: Caesar with the Tenth at the foot of the slope (S60 VII.47, VII.51); {DC0} "
                   "(doc 57 §9 q5)",
    "scope": f"authored: headless only, as Pegasus, Concord and Hill 223; {DC0} (doc 57 §9 q7)",
    "sources_pass": f"authored: no pull of the Latin text, Goldsworthy or the 1995-96 excavation report before "
                    f"the run; {DC0} (doc 57 §9 q8)",
    "sector": f"authored: four Eighth Legion century groups with Fabius's party, the Tenth and Sextius's "
              f"cohorts, not a cohort-sized sector (doc 57 §6); {DC0} (doc 57 §9 q1)",
    "map": f"authored: schematic, not surveyed; the upper-slope crop with the camps taken at the start; the "
           f"approach and the valley between the legions are a lower-slope edge and signal-block hexes (doc 57 "
           f"§2, §7); {DC0} (doc 57 §9 q2)",
    "map.crop": "inferred: 1,200 paces from the plain to the town wall (S60 VII.46), at a conventional 1.48 m "
                "a pace about 1.8 km, does not fit 24 by 21 hexes of 50 m; the stone wall 'almost in the middle' "
                "gives about 600 paces, 18 hexes (doc 57 §2)",
    "map.valley": "sourced: 'a very large valley' between the Tenth and the other legions (S60 VII.47); columns "
                  "16-17 below row 8, its depth, cost and cover are authored",
    "map.walls": "sourced: the town wall and gates (S60 VII.46, VII.47, VII.50) and a six-foot stone wall about "
                 "the middle of the hill (VII.46); both are terrain rows with cover and sight height, since the "
                 "engine has no free-standing wall (doc 57 §10 later); values authored",
    "roman.mission": f"sourced: take the camps by surprise, not fight a battle (S60 VII.45), with legates and "
                     f"tribunes to restrain the men (VII.45, VII.47); 'also the town' is not an intent; {DC0} "
                     f"(doc 57 §9 q4)",
    "gallic.mission": "inferred: hold the wall, return in growing numbers, drive the Romans down (S60 VII.48, "
                      "VII.51 as Caesar's description); no Gallic order is read (doc 57 §3)",
    "roman.command_unit": "sourced: the Tenth with Caesar, halted by the recall, in reserve on level ground (S60 "
                          "VII.47, VII.51); 80 men authored",
    "gallic.command_unit": "authored: the wall garrison at the gate; Vercingetorix's post is not given",
    "units.eighth": "sourced: the Eighth Legion at the wall (S60 VII.47, VII.50); four century groups of 60 are "
                    "authored (doc 57 §6); 46 centurions fell (VII.51), so more centuries fought than are modelled",
    "units.fabius": "sourced: Centurion Lucius Fabius and three men (S60 VII.47); rout_strength 0 is authored, so "
                    "the party does not rout at once under the 12-man default (docs/research/58)",
    "units.sextius": "sourced: Sextius's cohorts of the Thirteenth from the lesser camp (S60 VII.49, VII.51); 80 "
                     "men and the lesser-camp hex at the map's south-west corner are authored",
    "units.gallic": "authored: four wall groups of 60, a returning force of 120 and cavalry of 40 (doc 57 §6); "
                    "VII.48 gives the pattern, not the numbers; museum and Wikipedia totals are not used (S63, S64)",
    "units.placement": "reconstruction: the Eighth just past the stone wall in the taken camps (doc 57 §2), "
                       "west of the valley; the hexes are authored",
    "units.civilians": f"authored: the women on the wall (S60 VII.47, VII.48) are not modelled; {DC0} (doc 57 §9 "
                       f"q6)",
    "units.aedui": f"authored: the Aedui (S60 VII.45, VII.50) are left out of the default and appear only in "
                   f"aedui-misread; {DC0} (doc 57 §9 q6)",
    "signal": f"sourced: the trumpet recall (S60 VII.47), which the Tenth heard and the legions across the valley "
              f"did not; interval 40, reach 8 and the valley block are authored (doc 57 §8); {DC0} (doc 57 §9 q3: "
              f"signal failure and ardour are separate variants, neither the default truth)",
    "restraint": "reconstruction: Roman S1 (doc 57 §3): the forward groups pursue from the taken camps toward "
                 "the gate (S60 VII.47: they pursued to the wall and gates); a group that hears the recall stops and "
                 "falls back to the Tenth's line, where it holds; a group that does not hear it keeps pressing "
                 "(exploit, trigger start, press to the hex below the gate, recall_binding true, loss limit 50 per "
                 "cent; docs/research/60 §2); tribunes' voices are the command's 2-hex voice reach, used only "
                 "when an order is sent (recall-by-runner)",
    "victory": "authored: recover-force (doc 57 §5, docs/research/60 §3): half the forward force's starting "
               "strength within 2 hexes of the Tenth's line by the deadline; a 'force recovered' reading, not a "
               "historical result; 57 §5's limit_row condition is not in the kind",
    "losses_check": "sourced: 46 centurions and 'little less than seven hundred' men (S60 VII.51); an "
                    "order-of-magnitude check only, which S61 and S64 say may understate",
    "observation_range": "authored: the 7-hex daylight default; the walls block sight by obstacle height "
                         "(doc 57 §6)",
    "weapons": "authored: shock infantry 1 hex, missile troops 3 hexes, under tactics_v11 (doc 57 §6, "
               "docs/research/55); the cavalry use the shock class, as the table has no mounted class",
    "communications": "authored: roman-republic-signal-v1 with a 2-hex voice reach; trumpet (S60 VII.47), runner "
                      "for 'sends orders' (VII.49), voice for legates briefed in person (VII.45)",
    "voice_profile": "authored: republic-en-v1; no ancient text is quoted (docs/research/60 §4)",
    "officers": "authored: the engine's default 2 officers a group (a centurion and one other); leaders-fall "
                "gives each forward group 1, its centurion",
    "succession": "authored: Sextius succeeds the Tenth's command group; no source names one",
    "scripted": "reconstruction: scripted policies from S60 (Roman) and Caesar's description of the Gauls "
                "(Gallic G1) (battle/gergovia_policy.py)",
}


def gergovia_entry(variant=None, *, strength=STRENGTH, signal=None, exploit=PURSUIT, officers=None, aedui=False,
                   scripted=None, notes=None):
    """One Gergovia entry; ``variant`` None is the catalog default. The
    keywords change one question each; ``notes`` adds provenance."""
    suffix = "" if variant is None else f"-{variant}"
    return ScenarioEntry(
        id="gergovia-recall" + suffix,
        title="Gergovia" + ("" if variant is None else f" ({variant})"),
        variant=variant,
        rules=RULES_VERSION,
        prompt_version="gergovia-side-v1",
        prompt_setting="the upper slope of the hill of Gergovia, Gaul, 52 BCE",
        labels={RULES_VERSION: f"gergovia-recall{suffix}-v1"},
        location="Upper slope below the town wall · Gergovia, Arverni",
        date="52 BCE",
        start_time="12:00:00",
        time_basis=f"Scenario local time; authored: noon, when the camps were taken (S60 VII.46); no day is "
                   f"sourced; {DC0}",
        seconds_per_turn=30,
        weather={"season": "spring", "conditions": "daylight; fixed POC condition"},
        sides={
            "roman": SideEntry(name="Roman", role="attacker", command_unit="RX", headquarters=TENTH,
                               mission=ROMAN_MISSION, charge="bring the forward groups back to the Tenth's line"),
            "gallic": SideEntry(name="Gallic", role="defender", command_unit="G2", headquarters=GATE,
                                mission=GALLIC_MISSION, charge="hold the wall and drive the Romans down"),
        },
        player_side="roman",
        units=roman_units(strength, exploit, officers) + gallic_units(aedui),
        victory=VictoryEntry(kind="recover-force", objective=RALLY, deadline_turns=DEADLINE,
                             objective_name="the Tenth's line", recover_units=FORWARD, rally_hex=RALLY,
                             rally_radius=RALLY_RADIUS, recover_pct=50),
        map=MapEntry(terrain=terrain, features=FEATURES, cols=COLS, rows=ROWS, metres_per_hex=METRES_PER_HEX,
                     width=1080, height=840,
                     source=("Authored, schematic: the upper slope of Gergovia from the stone wall to the town "
                             "wall, the valley between the legions and the Tenth's lower slope "
                             "(docs/research/57, 62)."),
                     source_url=None),
        order_catalog=ORDER_CATALOG,
        communications=ROMAN_COMMUNICATIONS,
        voice_profile=ROMAN_VOICE_PROFILE,
        voice_reach=VOICE_REACH,
        broadcasts=(signal or recall(),),
        fire=FIRE,
        command=COMMAND,
        weapons=WEAPONS,
        tactics=TACTICS_V11,
        scripted=scripted or {"roman": ROMAN_POLICY, "gallic": GALLIC_POLICY},
        provenance={**PROVENANCE, **(notes or {})},
    )


GERGOVIA_RECALL = gergovia_entry()
# Doc 57 §8 names that are the default's own reading; each is its own entry so it validates and runs.
AS_DEFAULT = {
    "sextius-cover": ("doc 57 §8 sextius-cover / no-cover", "sourced: S60 VII.49; the interval is authored"),
    "strength-60": ("doc 57 §8 strength-sweep (40, 60, 80)", "authored"),
}


def _variants():
    table = (
        ("recall-audible", "doc 57 §8 recall-audible (control)", "every unit hears the signal: reach 45, no block",
         "sourced as the counterfactual: S60 VII.47, the Tenth heard it", dict(signal=recall(COLS + ROWS, ()))),
        ("recall-by-runner", "doc 57 §8 recall-by-runner",
         f"the recall also goes as a retreat order to each forward group at interval {RECALL_TURN}, by voice "
         "within 2 hexes, else by runner", "sourced: S60 VII.47, tribunes and legates",
         dict(scripted={"roman": ROMAN_RUNNER_POLICY, "gallic": GALLIC_POLICY})),
        ("ardour", "doc 57 §8 ardour", "the forward groups' pursuit to the gate does not stop for a heard "
         "recall; they take it up only when the press stops (exploit, recall_binding false)",
         "sourced as Caesar's account: S60 VII.47, VII.52; the mechanism is authored", dict(exploit=ARDOUR)),
        ("leaders-fall", "doc 57 §8 leaders-fall",
         "each forward group has one officer, its centurion; when he falls the group is leaderless and does not "
         "obey a recall", "inferred: S60 VII.47, VII.51 (46 centurions)", dict(officers=1)),
        ("no-cover", "doc 57 §8 sextius-cover / no-cover", "Sextius's cohorts are not ordered out",
         "sourced: S60 VII.49 (the counterfactual)",
         dict(scripted={"roman": ROMAN_NO_COVER_POLICY, "gallic": GALLIC_POLICY})),
        ("aedui-misread", "doc 57 §8 aedui-misread",
         "an Aedui detachment of 60 on the Roman right, placed on the Gallic side and holding fire, is read as "
         "hostile", "sourced: S60 VII.50; the mechanism is doc 57 §10's workaround", dict(aedui=True)),
    ) + tuple(
        (f"gallic-delay-{d}", "doc 57 §8 gallic-delay (10, 20, 40)",
         f"the Gallic masses are ordered back {d} intervals later, at interval {RETURN_TURN + d}",
         "authored: VII.48 gives the order, not the times",
         dict(scripted={"roman": ROMAN_POLICY, "gallic": gallic_delay_policy(d)})) for d in GALLIC_DELAYS
    ) + tuple(
        (f"strength-{n}", "doc 57 §8 strength-sweep (40, 60, 80)", f"each Eighth Legion century group has {n} men",
         "authored", dict(strength=n)) for n in (40, 80)
    ) + tuple((name, q, "the default's own reading, run under its own label", src, {})
              for name, (q, src) in AS_DEFAULT.items())
    return {name: Variant(question=q, reading=reading, source=src,
                          entry=gergovia_entry(name, notes={"variant": f"authored: {reading}"}, **kw))
            for name, q, reading, src, kw in table}


VARIANTS = _variants()
