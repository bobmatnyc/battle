"""Hill 223, 8 October 1918: a catalog entry and its variants (poc-13).

Why: the fourth of the first five selections (docs/research/37) asks whether
Acting Sgt Early's 17-man patrol, sent to silence the guns that pinned Company
G, reaches their rear, takes the surrender of the group it meets and comes
back with prisoners through the guns that turn on it. Doc 56 plans it; docs
58 and 59 supply the rules (declared rout threshold, assault in open ground,
surrender and captives, gun facing, raid-and-return, 1918 voice and runner).
What: ``hill223_entry`` builds one ``ScenarioEntry``; ``HILL_223_PATROL`` is
doc 56 §8's default (deadline 10:30, observation 3, valley 500 yd = 10 hexes,
German G1, American S1), accepted with every other doc 56 §9 default by the
Dc0 ruling of 2026-11-07. ``VARIANTS`` holds doc 56 §8's named variants, each
with its question and source. The map is authored and schematic. Every
field's basis is in the entry's ``provenance``; the runs are docs/research/61.
Test: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`,
`test_each_named_variant_differs_only_in_its_own_question`.
"""

from dataclasses import replace

from .grid import COLS, METRES_PER_HEX, ROWS, key
from .presentation import WWI_VOICE_PROFILE
from .scenario_command import TACTICS_V11, WWI_COMMUNICATIONS, CommandEntry, WeaponEntry
from .scenario_concord import Variant
from .scenario_entry import (
    ORDER_CATALOG, RULES_VERSION, DeskBrief, FireEntry, MapEntry, ScenarioEntry, SideBrief, SideEntry, UnitEntry,
    VictoryEntry,
)

DC0 = "default per Dc0 ruling 2026-11-07"  # doc 56 §9: every open question takes the proposed default.
# Authored, schematic layout (doc 56 §7). North is row 0. The German hill
# fills columns 0-4 (the ravine on its west side, the crest, the east face);
# the valley follows it; Hill 223 is the rest of the map.
GERMAN_HILL_COLS = 5
VALLEY_HEXES = 10  # S57 p. 59: 500 yd of open valley; 10 hexes of 50 m (doc 56 §7).
SHACK = (0, 11)  # S40: the "little shack", the German battalion commander's post, in the ravine.
PATROL_START = (4, 18)  # Doc 56 §2: the patrol at the east crest, entering the woods.
PATROL_TARGET = (0, 12)  # The ravine beside the shack: the rear of the gun position.
TURNS_PER_HOUR = 120  # 30-second intervals.
DEADLINE = 3 * TURNS_PER_HOUR + 90  # 06:45 to 10:30, the counter-attack hour (S57 p. 60).
FACING = 45  # The guns are laid north-east, down the valley toward the American attack (authored).
ARC = 120
GUN_TURN = 1  # Intervals to turn a gun group (S40 "rapidly"; authored); doc 56 §8 gun-turn-delay.
OBSERVATION = 3  # Doc 56 §6: daylight in dense woods and thicket.
VOICE_REACH = 1  # Doc 56 §6: thicket and fire.
RIFLES, MGS = "rifles and pistols", "machine guns"
# Scripted controls (battle/hill223_policy.py); ids live here so the entry needs no policy import.
AMERICAN_POLICY = "scripted-hill-223-company-g-v1"
REINFORCE_POLICY = "scripted-hill-223-company-reinforces-v1"
GERMAN_POLICY = "scripted-hill-223-german-v1"


def hill_223_col(valley=VALLEY_HEXES):
    """The first column of Hill 223: the valley's east edge."""
    return GERMAN_HILL_COLS + valley


def post(valley=VALLEY_HEXES):
    """The hex the patrol returns to, beside the Company G post (AHQ)."""
    return (hill_223_col(valley), 10)


def _german_cell(c, r):
    """Ravine (col 0), west slope, crest, east face (doc 56 §7, authored)."""
    elevation = (22, 30, 38, 36, 30)[c]
    if c == 0 and 6 <= r <= 16:  # S57 p. 60: the "wooded ravine on the west side".
        return {"elevation": elevation, "terrain": "woods", "move_cost": 145, "cover": 32, "area": "ravine"}
    if c >= 3 and r >= 12:  # S57 p. 60: "heavy woods on the east crest", where the patrol passed.
        return {"elevation": elevation, "terrain": "woods", "move_cost": 145, "cover": 32, "area": "east-crest-woods"}
    # S40: dense undergrowth on the slopes; cover and cost are authored.
    return {"elevation": elevation, "terrain": "open", "move_cost": 120, "cover": 20, "area": "german-hill"}


def terrain_for(valley):
    def terrain():
        cells = {}
        east = hill_223_col(valley)
        for r in range(ROWS):
            for c in range(COLS):
                if c < GERMAN_HILL_COLS:
                    cell = _german_cell(c, r)
                elif c < east:  # S57 p. 59: open valley.
                    cell = {"elevation": 10, "terrain": "open", "move_cost": 100, "cover": 5, "area": "valley"}
                else:
                    cell = {"elevation": 30, "terrain": "open", "move_cost": 110, "cover": 15, "area": "hill-223"}
                cells[key([c, r])] = {"pos": [c, r], **cell}
        cells[key(list(SHACK))]["area"] = "shack"
        return cells
    return terrain


FEATURES = {
    "roads": (),
    "buildings": (),
    # S40: an old trench on the hillside on the route; its hex and cover are authored.
    "works": ({"id": "old-trench", "kind": "fortification", "name": "Old trench on the hillside", "pos": [3, 16],
               "cover": 30, "progress": 100, "effort": 400, "required": 400, "updated_turn": 0},),
}


def _men(n, weapon, **extra):
    return {"initial": n, "strength": n, "ammo": n * 40, "weapon_class": weapon, **extra}


def _guns(n, turn=GUN_TURN):
    # S40: guns "masked and the muzzles pointed down into the valley".
    return _men(n, MGS, facing=FACING, arc=ARC, reorient_turns=turn)


# Doc 59 §1: G1 is a wide reach that counts only enemies in the rear arc; G2 is reach 1.
SURRENDER_G1 = {"reach": OBSERVATION, "odds_pct": 50, "support_reach": 1, "rear_only": True}
SURRENDER_G2 = {"reach": 1, "odds_pct": 50, "support_reach": 1, "rear_only": False}


def german_units(surrender=SURRENDER_G1, gun_turn=GUN_TURN):
    return (
        # S57 p. 60: about 75 round the battalion commander "receiving final instructions".
        UnitEntry("D1", "german", "Battalion command group at the shack", SHACK,
                  _men(75, RIFLES, facing=FACING, arc=ARC, reorient_turns=GUN_TURN, fire_posture="hold_fire",
                       surrender=dict(surrender))),
        UnitEntry("D2", "german", "Gun and rifle group, west slope", (1, 10), _guns(40, gun_turn)),
        UnitEntry("D3", "german", "Gun detachments, north and northeast slopes", (3, 4), _guns(30, gun_turn)),
        UnitEntry("D4", "german", "Guns laid on the valley", (4, 8), _guns(60, gun_turn)),
    )


def american_units(valley=VALLEY_HEXES):
    east = hill_223_col(valley)
    patrol = _men(17, RIFLES, officers=4, rout_strength=4, press_assault=True, fire_posture="hold_fire",
                  stance="move", target=list(PATROL_TARGET),
                  # The order given at departure, before the start (doc 56 §6: intent is set then).
                  mission_result={"template": "move", "status": "active", "order_version": 0, "started_turn": 0,
                                  "updated_turn": 0, "reason": "Instructions received."},
                  # D7b ruling 2026-11-07: the return resumes after a local withdrawal clears.
                  exploit={"trigger": "arrival", "press_to": list(post(valley)), "recall_binding": True,
                           "max_loss_pct": 100, "resume_after_withdrawal": True})
    return (
        # rout_strength 0: a 6-man post would rout at once under the 12-man default (docs/research/58).
        UnitEntry("AHQ", "american", "Company G post", (east, 9), _men(6, RIFLES, rout_strength=0)),
        UnitEntry("A1", "american", "Patrol · Acting Sgt Early, left support platoon", PATROL_START, patrol),
        UnitEntry("A2", "american", "Company G line, left", (east, 3), _men(40, RIFLES)),
        UnitEntry("A3", "american", "Company G line, right", (east, 5), _men(40, RIFLES)),
    )


WEAPONS = {
    RIFLES: WeaponEntry(range_hexes=3, effect_pct=67,
                        basis="authored: 150 m at two-thirds of the machine-gun effect (doc 56 §6 gives 100 against "
                              "150; the engine caps effect at 100, so both are scaled); S40 names rifle and .45 "
                              "Colt automatic, no range read"),
    MGS: WeaponEntry(range_hexes=5, effect_pct=100,
                     basis="authored: the engine's 5-hex fire cap (250 m); real reach exceeds the map, so the case "
                           "tests facing, surprise and surrender, not reach (doc 56 §6, §9 q5)"),
}
COMMAND = CommandEntry(succession={"american": ("A2", "A3")},
                       basis="authored: the patrol's 4 NCOs give an officer step of 17 // 5 = 3 losses (doc 56 §6); "
                             "other units keep the default 2; no German successor is recorded (S57 p. 61)")
FIRE = FireEntry(basis="authored: every group fires except the patrol and the command group, which hold fire "
                       "(doc 56 §6; S40 diary, S57 p. 60)")

AMERICAN_MISSION = (
    "You command Company G, 328th Infantry, on Hill 223. Machine guns on the hill across the valley pin the "
    "company. A patrol of 17 under Acting Sergeant Early has gone round by the woods to silence them. Your "
    "mission: the patrol reaches the rear of the gun position and comes back to the company post with "
    "prisoners before the German counter-attack hour, 10:30.")
GERMAN_MISSION = (
    "You command the battalion on the hill southwest of Hill 223. Your mission: hold the hill with the guns "
    "laid on the valley and keep any American party from returning before your counter-attack at 10:30.")

PROVENANCE = {
    "location": "sourced: the hill southwest across the valley from Hill 223, north of Châtel-Chéhéry (S57 "
                "p. 51-52, 59-60)",
    "date": "sourced: 8 October 1918 (S57 p. 58; S40)",
    "start_time": f"authored: 06:45, after the 06:00 or 06:10 jump-off (S57 p. 58; S40 diary); {DC0} (doc 56 "
                  "§9 q4)",
    "deadline": f"sourced: the hour of the German counter-attack set for 10:30 (S57 p. 60); as the battle's end it "
                f"is authored; {DC0} (doc 56 §9 q4)",
    "weather": "sourced: mist clearing to a cloudless sky (S40 narrative); a fixed POC condition",
    "sides": "sourced: Company G, 2nd Bn, 328th Infantry, against a German battalion; the German unit is a "
             f"disclosed conflict (S57 '45th Reserve Division'; S58 1st Bn 120th Landwehr); {DC0} (doc 56 §9 q7)",
    "player_side": f"authored: the Company G commander, who reaches the patrol only by runner; {DC0} (doc 56 §9 q1)",
    "scope": f"authored: headless only at first, as Pegasus and Concord; {DC0} (doc 56 §9 q6); a player "
             "scenario since docs/research/75, with the German side on its scripted control (bt-D08 default)",
    "credit": f"authored: no individual is modelled; doc 37's R1 and R2 are the mechanism variants of doc 56 §8; "
              f"{DC0} (doc 56 §9 q2)",
    "american.mission": "sourced: encircle the hill and silence the guns (S57 p. 60; S40 diary), then bring the "
                        "prisoners back (S57 p. 61-62)",
    "german.mission": "sourced: a counter-attack against the American left at 10:30 (S57 p. 60); hold the hill "
                      "until then is inferred",
    "american.command_unit": "authored: a 6-man Company G post on Hill 223 that does not rout by head count "
                             "(rout_strength 0); no strength is sourced",
    "german.command_unit": "inferred: the battalion commander stood with the group at the shack (S57 p. 60; S40)",
    "units.patrol": "sourced: 17 men, 4 NCOs and 13 privates, from the left support platoon of Company G (S57 "
                    "p. 60; S40); one aggregate detachment (doc 56 §6); rout below 4 men is authored",
    "units.company_line": "authored: two 40-man parts of the Company G line and a 6-man post; held, not modelled "
                          "as an attack (doc 56 §2, §6)",
    "units.german": "sourced: an estimate of about 75 round the commander (S57 p. 60); the gun groups of 40, 30 "
                    "and 60 are authored (doc 56 §6); 205 in all, under S57's 250 and above the 132 captured",
    "units.placement": "reconstruction: the patrol at the east crest entering the woods (S57 p. 60); the gun "
                       "groups on the west, north and northeast slopes and the valley face (S57 p. 60-61); "
                       "the hexes are authored",
    "map": f"authored: schematic, not surveyed; terrain readings L1 and L2 collapse to one map; {DC0} (doc 56 "
           "§9 q3, §7)",
    "map.valley": "sourced: a conflict, 200-300 yd (S40), 500 yd (S57 p. 59), about a mile (S58); the default is "
                  "S57's 500 yd, 10 hexes (doc 56 §7)",
    "map.ravine": "sourced: the wooded ravine on the west side and heavy woods on the east crest (S57 p. 60); "
                  "elevations, costs and cover are authored",
    "victory": "authored: raid-and-return (doc 56 §5, docs/research/59 §3): stand within 1 hex of the shack for "
               "1 interval, then a quarter of the patrol (5 men) within 1 hex of the post holding at least 1 "
               "captive by 10:30; no count is scored against S57 or the diary (doc 37)",
    "observation_range": "authored: 3 hexes for every unit, the valley included (doc 56 §6; the engine has no "
                         "per-terrain sight range)",
    "weapons": f"authored: rifles and pistols 3 hexes, machine guns 5 hexes, under tactics_v11 (doc 56 §6); "
               f"{DC0} (doc 56 §9 q5)",
    "communications": "authored: wwi-1918-voice-runner-v1, voice reach 1 (doc 56 §6); S57 p. 57-58 records only "
                      "a runner",
    "voice_profile": "authored: the 1918 American voice; no historical message is quoted (docs/research/59 §4)",
    "facing": "sourced: the posture, guns masked and aimed down the valley, then turned (S40; S57 p. 60); the "
              "north-east bearing, the 120-degree arc and the 1-interval turn are authored",
    "surrender": "inferred: G1, the command group yields on a party in its rear it believes strong (S57 p. 60, "
                 "'supposing' a large American force); reach 3, odds 50 per cent and support within 1 hex are "
                 "authored (docs/research/59 §1)",
    "fire_discipline": "sourced: the patrol held fire on a group offering to yield (S40 diary, 'told us not to "
                       "shoot') and returns fire when struck (docs/research/46); the command group's hold is "
                       "inferred from S57 p. 60 ('receiving final instructions')",
    "press_assault": "reconstruction: the patrol keeps to its route on contact, as it did (S57 p. 60); "
                     "docs/research/58 §2",
    "return": "reconstruction: on reaching the rear the patrol presses back to the company post (exploit "
              "doctrine, docs/research/60 §2, trigger arrival); S57 p. 61-62 and S40 record the return; the "
              "engine takes the shortest path, not the approach route; the return resumes after a local "
              "withdrawal clears (resume_after_withdrawal), per D7b ruling 2026-11-07",
    "officers": "authored: 4 for the patrol's 4 NCOs (S57 p. 60), so three fall in 9 losses, as S57 p. 61 "
                "records (doc 56 §6)",
    "shield": "authored: prisoners are not a fire shield; the engine has none (doc 56 §10 later; "
              "docs/research/59 §7)",
    "scripted": "reconstruction: scripted policies from S57 and S40 (American) and inferred German intent "
                "(battle/hill223_policy.py)",
    # docs/research/75: the command-desk text (``AMERICAN_BRIEF``, ``DESK``). Display only.
    "desk.campaign": "sourced: 8 October 1918 (S57 p. 58; S40) at Châtel-Chéhéry (S57 p. 51-52), in the Argonne "
                     "(S58, secondary)",
    "desk.place": "sourced: the little shack (S40) where the battalion commander stood with his group (S57 p. 60); "
                  "its hex is authored",
    "desk.conditions": "sourced: mist clearing to a cloudless sky (S40 narrative); authored: a fixed POC condition",
    "brief.american.headings": "authored: kicker, tagline and mission title are desk headings, not quotations; the "
                               "tagline echoes S57 p. 60, 'silence the enemy guns'",
    "brief.american.subhead": "sourced: Company G, 2nd Bn, 328th Infantry, on Hill 223, and a German battalion on "
                              "the hill southwest across the valley (S57 p. 58-60); the German unit is a disclosed "
                              "conflict (S57; S58), so the brief names none; authored: that the computer commands "
                              f"the Germans; the player as the Company G commander is the {DC0} (doc 56 §9 q1)",
    "brief.american.mission_text": "sourced: the guns on the hill southwest across the valley impede G Company (S57 "
                                   "p. 59-60); four NCOs and thirteen privates under Acting Sergeant Early sent to "
                                   "encircle the hill and silence the guns, by the woods on the east crest (S57 p. "
                                   "60); the 10:30 counter-attack in the captured orders (S57 p. 60); the return "
                                   "with prisoners (S57 p. 61-62); reconstruction: the command post at the shack in "
                                   "the ravine (S40; S57 p. 60); authored: word only by runner (voice reach 1, doc "
                                   "56 §6), one hex, 5 men (a quarter of 17), one prisoner and 10:30 as the battle's "
                                   "end restate the entry's victory (doc 56 §5; docs/research/61 §3)",
    "brief.american.win": "sourced: the patrol brought its prisoners to the battalion post (S57 p. 61-62); the "
                          "wording is authored",
    "brief.american.loss": "authored: the outcome the record does not show; no source",
}
# docs/research/75: the Company G commander's desk text, in the entry's 1918 register. The
# German side has no brief: the desk shows a side's brief only to that side's player.
AMERICAN_BRIEF = SideBrief(
    kicker="HILL 223", tagline="Silence the guns.",
    subhead="You command Company G, 328th Infantry, on Hill 223. The computer commands the German battalion on "
            "the hill across the valley.",
    mission_title="Bring the patrol back",
    mission_text=("Machine guns on the hill southwest across the valley pin the company. Acting Sergeant Early's "
                  "patrol of 17 has gone round by the woods to reach the rear of the guns and silence them. It is "
                  "out of earshot: word reaches it only by runner. The patrol must stand within one hex of the "
                  "German command post at the shack in the ravine, then bring at least 5 men and one prisoner back "
                  "within one hex of the company post before the German counter-attack hour, **10:30**."),
    win="The patrol is back with prisoners.", loss="The patrol has not come back with prisoners.")
DESK = DeskBrief(campaign="ARGONNE · 8 OCTOBER 1918", place="Command post at the shack",
                 objective_label="PATROL OBJECTIVE", objective_key="SHACK",
                 conditions="AUTUMN · MIST, THEN CLEAR · FIXED POC CONDITION", draw="The battle ends in a draw.")


def hill223_entry(variant=None, *, valley=VALLEY_HEXES, surrender=SURRENDER_G1, gun_turn=GUN_TURN,
                  observation=OBSERVATION, scripted=None, notes=None):
    """One Hill 223 entry; ``variant`` None is the catalog default. The
    keywords change one question each; ``notes`` adds provenance."""
    suffix = "" if variant is None else f"-{variant}"
    return ScenarioEntry(
        id="hill-223-patrol" + suffix,
        title="Hill 223" + ("" if variant is None else f" ({variant})"),
        variant=variant,
        rules=RULES_VERSION,
        prompt_version="hill-223-side-v1",
        prompt_setting="the hill southwest of Hill 223, Châtel-Chéhéry, October 1918",
        labels={RULES_VERSION: f"hill-223-patrol{suffix}-v1"},
        location="Hill southwest of Hill 223 · Châtel-Chéhéry, Argonne",
        date="1918-10-08",
        start_time="06:45:00",
        time_basis=f"Scenario local time; authored: 06:45, after the 06:00 jump-off (S57 p. 58); {DC0}",
        seconds_per_turn=30,
        weather={"season": "autumn", "conditions": "mist clearing to a cloudless sky (S40); fixed POC condition"},
        sides={
            "american": SideEntry(
                name="American", role="attacker", command_unit="AHQ", headquarters=(hill_223_col(valley), 9),
                mission=AMERICAN_MISSION, charge="bring the patrol back from the guns' rear with prisoners",
                brief=AMERICAN_BRIEF if variant is None else None),
            "german": SideEntry(
                name="German", role="defender", command_unit="D1", headquarters=SHACK,
                mission=GERMAN_MISSION, charge="hold the hill until the 10:30 counter-attack"),
        },
        player_side="american",
        units=american_units(valley) + german_units(surrender, gun_turn),
        victory=VictoryEntry(kind="raid-and-return", objective=SHACK, deadline_turns=DEADLINE, radius=1,
                             hold_turns=1, objective_name="German command post", raiders=("A1",),
                             return_hex=post(valley), return_radius=1, return_pct=25, min_captives=1),
        map=MapEntry(terrain=terrain_for(valley), features=FEATURES, cols=COLS, rows=ROWS,
                     metres_per_hex=METRES_PER_HEX, width=1080, height=840,
                     source=("Authored, schematic: the German hill with its ravine and east-crest woods, the valley "
                             "and the west edge of Hill 223 (docs/research/56, 61)."),
                     source_url=None),
        order_catalog=ORDER_CATALOG,
        communications=WWI_COMMUNICATIONS,
        voice_profile=WWI_VOICE_PROFILE,
        voice_reach=VOICE_REACH,
        fire=FIRE,
        command=COMMAND,
        weapons=WEAPONS,
        tactics=TACTICS_V11,
        observation_range=observation,
        scripted=scripted or {"american": AMERICAN_POLICY, "german": GERMAN_POLICY},
        desk=DESK if variant is None else None,
        provenance={**PROVENANCE, **(notes or {})},
    )


# docs/research/75 (default ruling bt-D08): on the command desk the German battalion plays its
# scripted control (G1: posture, facing and surrender are entry data), as in headless runs.
HILL_223_PATROL = replace(hill223_entry(), desk_scripted_opponent=True)
REINFORCE_TURN = 60  # company-reinforces: 07:15, half an hour in (authored).
# Doc 56 §8 names that are the default's own reading; each is its own entry so it validates and runs.
AS_DEFAULT = {
    "surrender-on-surprise": ("doc 56 §8 (who ended the fire: G1)", "inferred: S57 p. 60"),
    "gun-turn-delay-1": ("doc 56 §8 gun-turn-delay (1, 2, 4 turns)", "authored: S40 says only 'rapidly'"),
    "no-shield": ("doc 56 §8 shield (prisoners as a fire shield)",
                  "sourced as a claim: S40 affidavits, S57 'careful shooting'; the engine has no shield"),
}


def _variants():
    table = (
        ("valley-narrow", "doc 56 §8 valley width (sourced conflict)", "the valley is 5 hexes (250 m) wide",
         "S40: 'only from two to three hundred yards wide'", dict(valley=5)),
        ("valley-wide", "doc 56 §8 valley width (sourced conflict)",
         "the valley is 18 hexes (900 m) wide; Hill 223 keeps only the map's east column",
         "S58: 'about one mile wide', capped by the 24-column map", dict(valley=18)),
        ("surrender-on-threat", "doc 56 §8 (who ended the fire: G2)",
         "the command group yields only to a party adjacent to it, on any side",
         "inferred: S40 diary, the major yields when York threatens him", dict(surrender=SURRENDER_G2)),
        ("gun-turn-delay-2", "doc 56 §8 gun-turn-delay (1, 2, 4 turns)",
         "a gun group takes 2 intervals (1 minute) to turn", "authored: S40 says only 'rapidly'", dict(gun_turn=2)),
        ("gun-turn-delay-4", "doc 56 §8 gun-turn-delay (1, 2, 4 turns)",
         "a gun group takes 4 intervals (2 minutes) to turn", "authored: S40 says only 'rapidly'", dict(gun_turn=4)),
        ("observation-2", "doc 56 §8 observation sensitivity", "every unit sees 2 hexes",
         "authored: S40 affidavits, the men 'could not see' each other", dict(observation=2)),
        ("observation-4", "doc 56 §8 observation sensitivity", "every unit sees 4 hexes",
         "authored: S40 affidavits, the men 'could not see' each other", dict(observation=4)),
        ("company-reinforces", "doc 56 §8 company-reinforces",
         f"Company G sends its right part (A3) after the patrol at interval {REINFORCE_TURN} (07:15)",
         "authored: no source", dict(scripted={"american": REINFORCE_POLICY, "german": GERMAN_POLICY})),
    ) + tuple((name, q, "the default's own reading, run under its own label", src, {})
              for name, (q, src) in AS_DEFAULT.items())
    return {name: Variant(question=q, reading=reading, source=src,
                          entry=hill223_entry(name, notes={"variant": f"authored: {reading}"}, **kw))
            for name, q, reading, src, kw in table}


VARIANTS = _variants()
