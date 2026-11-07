"""Cannae, 216 BCE: a catalog entry and its variants at army scale (poc-13).

Why: the user's sequence item 3 asks for a separate army-scale Cannae beside
the company-scale comparisons (docs/research/36, 37 §1). Doc 63 plans it and
the D86 ruling (Bob 2026-11-07 13:10Z) accepts its defaults: scale option A,
the designed yield (C1), scripted orders for each sector, sources pulled in
parallel. Docs/research/68 states the entry and its deviations.
What: ``cannae_entry`` builds one ``ScenarioEntry``; ``CANNAE_ENVELOPMENT``
is doc 63 §8's default (``cannae-envelopment``): 200 m hexes, 180 s
intervals, 41 units, C1 against R1, the ``encircle`` victory. ``VARIANTS``
holds the doc 63 §8 variants the engine can build. The map is authored and
schematic, with no compass bearing and no site registration (doc 63 §7).
Every field's basis is in the entry's ``provenance``.
Test: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`,
`test_entry_takes_every_doc_63_default`,
`test_each_named_variant_differs_only_in_its_own_question`.
"""

from .grid import COLS, ROWS, key
from .presentation import ROMAN_VOICE_PROFILE
from .scenario_army import ArmyEntry
from .scenario_command import CARTHAGE_216_COMMUNICATIONS, ROMAN_216_COMMUNICATIONS, TACTICS_V11, WeaponEntry
from .scenario_concord import Variant
from .scenario_entry import (
    ORDER_CATALOG, RULES_VERSION, FireEntry, MapEntry, ScenarioEntry, SideEntry, UnitEntry, VictoryEntry,
)

D86 = "D86 (Bob 2026-11-07 13:10Z): doc 63 defaults"
METRES_PER_HEX, SECONDS_PER_TURN = 200, 180  # Doc 63 §2.2 option A, §8 rows 1-2.
TURNS_PER_HOUR = 3600 // SECONDS_PER_TURN
DEADLINE = 8 * TURNS_PER_HOUR  # Doc 63 §2, §8 row 5: 08:00 to 16:00, 160 intervals.
# Authored layout (doc 63 §6-7). Row 0 is the Carthaginian map edge, row 20 the
# Roman. The Romans face up the map (bearing 0), the Carthaginians down (180);
# the river covers the Roman right and the Carthaginian left (S65 III.113).
RIVER_COL = 23
LANE_COLS = (21, 22)  # Doc 63 §8 row 11: the 2-hex lane by the river (S66 XXII.47).
BLOCK_COLS = tuple(range(13, 21))  # Doc 63 §8 row 8: 8 wide.
AFRICAN_ROW, CENTRE_ROW, CRESCENT_ROW, LIGHT_ROW = 6, 7, 8, 9
VELITES_ROW, LEGION_ROW, ALA_ROW = 10, 11, 12
# Doc 63 §5, §8 row 25: three exits on the Roman edge for the smaller camp,
# the larger camp and Cannae village (S66 XXII.49); positions authored.
EXITS = {"smaller-camp": (22, 20), "larger-camp": (16, 20), "cannae-village": (6, 20)}
ROMAN_HQ, CARTHAGINIAN_HQ = EXITS["larger-camp"], (16, 0)  # Rally points; authored.
PRESS_ROW = 0  # The Carthaginian rear row the Roman press aims at (doc 63 §8 row 21): the map edge.
LANE_END = (21, 16)  # The horse by the river charges down the lane past the Roman right; authored.
RIDE = {"HC1": (11, 13), "HC2": (12, 14), "HC3": (10, 14)}  # Behind the Roman left wing; authored.
RESERVE = {"A7": (21, 16), "A8": (22, 16)}  # Doc 63 §3 R2: two alae on the lane to the smaller camp.
LIGHT_TURN = 10  # The light troops fall back at 08:30; authored (S65 III.115 gives no time).
ADVANCE_WAIT = 10  # Intervals after LIGHT_TURN the heavy advance waits for the light troops at most.
DESERTER_TURN = 60  # Doc 63 §8 deserters: the scripted interval (11:00); authored.
CAVALRY_DELAYS = (10, 20, 40)  # Doc 63 §8 cavalry-delayed.
VOICE_REACH = 1  # Doc 63 §8 row 15.
SIGNAL_REACH = 6  # Doc 63 §8 row 17: recorded; the battle signal falls before the start (docs/research/68 §3).
HEAVY_INFANTRY, LIGHT_INFANTRY = "heavy infantry", "light infantry"
HEAVY_CAVALRY, LIGHT_CAVALRY = "heavy cavalry", "light cavalry"
CAVALRY_RATE = 3  # Doc 63 §8 row 13.
# Scripted controls (battle/cannae_policy.py); ids live here so the entry needs no policy import.
ROMAN_POLICY = "scripted-cannae-roman-v1"
ROMAN_RESERVE_POLICY = "scripted-cannae-roman-reserve-v1"
CARTHAGINIAN_POLICY = "scripted-cannae-carthaginian-v1"
DESERTERS_POLICY = "scripted-cannae-carthaginian-deserters-v1"


def cavalry_delay_policy(delay):
    return f"scripted-cannae-carthaginian-cavalry-delay-{delay}-v1"


LEGIONS = tuple(f"L{i}" for i in range(1, 9))
ALAE = tuple(f"A{i}" for i in range(1, 9))
HEAVY = LEGIONS + ALAE
VELITES = tuple(f"V{i}" for i in range(1, 5))
CENTRE = tuple(f"C{i}" for i in range(1, 9))
CRESCENT = ("C3", "C4", "C5", "C6")  # Doc 63 §8 row 9.
AFRICANS = ("AF1", "AF2")
LIGHT_TROOPS = ("LT1", "LT2", "LT3")
HASDRUBAL = ("HC1", "HC2", "HC3")
NUMIDIANS = ("NU1", "NU2")


def _cell(c, r):
    """Flat, treeless open plain (S65 III.110.2) with the river on one side column (doc 63 §7)."""
    if c == RIVER_COL:  # The Aufidus, impassable here; both armies crossed before the start (S65 III.113).
        return {"elevation": 0, "terrain": "water", "water": True, "move_cost": 100, "cover": 0, "area": "aufidus"}
    area = "river-lane" if c in LANE_COLS else "plain"
    return {"elevation": 0, "terrain": "open", "move_cost": 100, "cover": 0, "area": area}


def terrain():
    return {key([c, r]): {"pos": [c, r], **_cell(c, r)} for r in range(ROWS) for c in range(COLS)}


FEATURES = {"roads": (), "buildings": (), "works": ()}


def _men(n, weapon, unit_type, ammo_per_man, **extra):
    return {"initial": n, "strength": n, "ammo": n * ammo_per_man, "weapon_class": weapon, "unit_type": unit_type,
            **extra}


def _heavy(n, **extra):
    return _men(n, HEAVY_INFANTRY, "infantry", 2, **extra)  # Shock: ammunition is never spent (doc 63 gap 3).


def _light(n, **extra):
    return _men(n, LIGHT_INFANTRY, "infantry", 3, **extra)


def _horse(n, weapon=HEAVY_CAVALRY, **extra):
    return _men(n, weapon, "cavalry", 2 if weapon == HEAVY_CAVALRY else 3, move_rate=CAVALRY_RATE, **extra)


def _moving(hex_):
    """An order given before the start: the unit moves to ``hex_`` from interval 1."""
    return {"stance": "move", "target": list(hex_),
            "mission_result": {"template": "move", "status": "active", "order_version": 0, "started_turn": 0,
                               "updated_turn": 0, "reason": "Instructions received."}}


# Doc 63 §3 R1: the heavy infantry presses on toward the Carthaginian rear row once
# its advance order is carried out, whatever its contacts (exploit, docs/research/60 §2).
def press(col):
    return {"trigger": "arrival", "press_to": [col, PRESS_ROW], "recall_binding": False, "max_loss_pct": 50}


YIELD = {"limit": 3, "rear_step": -1}  # Doc 63 §3 C1, §8 row 18: up to 3 hexes toward the Carthaginian rear.


def wheel(front_row=AFRICAN_ROW):
    return {"reach": 2, "front_row": front_row, "rear_step": -1}  # Doc 63 §8 row 19.


EQ_HEX, SC1_HEX, SC2_HEX = (21, LEGION_ROW), (12, LEGION_ROW), (11, LEGION_ROW)


def roman_units(*, horse=1, dust=False, wide=False, reserve=False):
    """Doc 63 §6 roster and deployment; ``horse`` multiplies the cavalry
    (roman-horse-holds), ``dust`` gives 3-hex sight, ``wide`` the 16-wide
    block, ``reserve`` R2's two alae on the lane."""
    sight = {"observation_range": 3} if dust else {}
    cols = tuple(range(5, 21)) if wide else BLOCK_COLS
    units = []
    for i, uid in enumerate(LEGIONS):
        col, row = (cols[2 * i], LEGION_ROW) if wide else (cols[i], LEGION_ROW)
        units.append(UnitEntry(uid, "roman", f"Legion {i + 1}", (col, row), _heavy(3550, exploit=press(col), **sight)))
    for i, uid in enumerate(ALAE):
        col, row = (cols[2 * i + 1], LEGION_ROW) if wide else (cols[i], ALA_ROW)
        if reserve and uid in RESERVE:
            col, row = RESERVE[uid]
            units.append(UnitEntry(uid, "roman", f"Allied ala {i + 1} · reserve", (col, row), _heavy(3550, **sight)))
            continue
        units.append(UnitEntry(uid, "roman", f"Allied ala {i + 1}", (col, row), _heavy(3550, exploit=press(col), **sight)))
    velites = (7, 11, 15, 19) if wide else (13, 15, 17, 19)
    for i, uid in enumerate(VELITES):
        units.append(UnitEntry(uid, "roman", f"Light infantry {i + 1}", (velites[i], VELITES_ROW), _light(3500, **sight)))
    left = ((4, LEGION_ROW), (3, LEGION_ROW)) if wide else (SC1_HEX, SC2_HEX)
    units += [
        UnitEntry("EQ", "roman", "Citizen cavalry · Aemilius Paullus", EQ_HEX, _horse(1600 * horse, **sight)),
        UnitEntry("SC1", "roman", "Allied cavalry · Terentius Varro", left[0], _horse(2400 * horse, **sight)),
        UnitEntry("SC2", "roman", "Allied cavalry", left[1], _horse(2400 * horse, **sight)),
    ]
    return tuple(units)


def carthaginian_units(*, design=True, wheels=AFRICANS, deserters=False):
    """Doc 63 §6 roster and deployment; ``design`` False is C2 (no yield),
    ``wheels`` the Africans that keep the wheel, ``deserters`` adds Livy's 500."""
    units = [
        UnitEntry("AF1", "carthaginian", "Africans · left shoulder", (BLOCK_COLS[-1], AFRICAN_ROW),
                  _heavy(5000, **({"wheel": wheel()} if "AF1" in wheels else {}))),
        UnitEntry("AF2", "carthaginian", "Africans · right shoulder", (BLOCK_COLS[0], AFRICAN_ROW),
                  _heavy(5000, **({"wheel": wheel()} if "AF2" in wheels else {}))),
    ]
    for i, uid in enumerate(CENTRE):  # C1 by the river, C8 on the open flank; Spaniards and Celts alternate.
        col = BLOCK_COLS[-1 - i]
        row = CRESCENT_ROW if uid in CRESCENT else CENTRE_ROW
        name = ("Spanish" if i % 2 == 0 else "Celtic") + " foot" + (" · Hannibal and Mago" if uid == "C4" else "")
        units.append(UnitEntry(uid, "carthaginian", name, (col, row), _heavy(2750, **({"yield": dict(YIELD)} if design else {}))))
    for uid, col in zip(LIGHT_TROOPS, (18, 16, 14)):
        units.append(UnitEntry(uid, "carthaginian", "Slingers and spearmen", (col, LIGHT_ROW), _light(2670)))
    for uid, hex_ in zip(HASDRUBAL, ((21, CENTRE_ROW), (22, CENTRE_ROW), (22, AFRICAN_ROW))):
        units.append(UnitEntry(uid, "carthaginian", "Spanish and Celtic horse · Hasdrubal", hex_,
                               _horse(2170, press_assault=True, **_moving(LANE_END))))
    for uid, hex_, foe in zip(NUMIDIANS, ((12, CENTRE_ROW), (11, CENTRE_ROW)), (SC1_HEX, SC2_HEX)):
        units.append(UnitEntry(uid, "carthaginian", "Numidian horse", hex_, _horse(1750, LIGHT_CAVALRY, **_moving(foe))))
    if deserters:  # S66 XXII.48: about 500 Numidians feign desertion and are sent to the Roman rear.
        units.append(UnitEntry("ND", "carthaginian", "Numidian false deserters", (16, 16),
                               _horse(500, LIGHT_CAVALRY, fire_posture="hold_fire")))
    return tuple(units)


WEAPONS = {
    HEAVY_INFANTRY: WeaponEntry(range_hexes=1, effect_pct=100,
                                basis="authored: close fighting (S65 III.115); doc 63 §6, §8 row 12"),
    LIGHT_INFANTRY: WeaponEntry(range_hexes=1, effect_pct=40,
                                basis="authored: slings and javelins (S65 III.113, S66 XXII.46); doc 63 §8 row 12"),
    HEAVY_CAVALRY: WeaponEntry(range_hexes=1, effect_pct=100,
                               basis="authored: dismounted fighting by the river (S65 III.115); doc 63 §6"),
    LIGHT_CAVALRY: WeaponEntry(range_hexes=1, effect_pct=40,
                               basis="authored: the Numidians' way of fighting (S65 III.116); doc 63 §6"),
}
# D86 (Bob 2026-11-07 13:10Z): doc 63 defaults. Doc 63 gap 3 and §8 row 26 leave the
# loss and morale scaling to implementation: 13 per cent of a unit fights in a volley
# (a 200 m front of a block about 35 deep, a few ranks engaged), so two equal heavy
# units lose about 1 per cent an interval and a frontal fight lasts hours; morale
# falls 2 points per per cent lost, so a unit that loses about 29 per cent routs
# frontally; a flank blow costs 1.5 times, a rear blow 2 times, in men and again in
# morale (gap 4). Basis: the authored target "the day takes hours" (doc 63 gap 3).
ARMY = ArmyEntry(engaged_pct=13, morale_per_pct=2, flank_pct=150, rear_pct=200,
                 shock_classes=(HEAVY_INFANTRY, HEAVY_CAVALRY), fronts={"roman": 0, "carthaginian": 180},
                 basis="authored: D86 default for doc 63 gap 3, 4 and §8 row 26; calibrated so that a frontal "
                       "fight between equal heavy units lasts hours, not measured")
FIRE = FireEntry(basis="authored: every unit fires; only the deserters of doc 63 §8 deserters hold fire")

ROMAN_MISSION = (
    "You are the consul Terentius Varro, with the allied cavalry on the left. The Senate has decided to give "
    "battle. Your mission: break the Carthaginian centre by the weight of the legions before the day ends, and "
    "do not let the army be enclosed.")
CARTHAGINIAN_MISSION = (
    "You command the Carthaginian army on the open plain by the river, where cavalry decide. Your mission: "
    "hold the Roman legions in the centre while the horse wins the flanks, and enclose the Roman army before "
    "the day ends.")

PROVENANCE = {
    "location": "sourced: the plain of the Aufidus near Cannae (S65 III.107, III.110); the site is not established, "
                "with at least eight proposals and no archaeology of the battle (S67 p. 7; S68 pp. 88-89; S69)",
    "date": "sourced: 2 August 216 BCE, Roman calendar (S70, tertiary; the primary was not read, doc 63 §1)",
    "start_time": f"authored: 08:00 at the first light-infantry contact, on the cue 'just after sunrise' (S65 "
                  f"III.113) and 'as soon as it grew light' (S66 XXII.46); doc 63 §8 row 4; {D86}",
    "deadline": f"authored: 16:00, 160 intervals of 180 s; the sources give only 'the remainder of the day' (S66 "
                f"XXII.51) and 'till close on night' (S66 XXII.59); doc 63 §8 row 5; {D86}",
    "weather": "authored: daylight, fixed condition; Livy's wind and dust enter only as the dust variant (doc 63 §7)",
    "scale": f"authored: option A, 200 m hexes and 180 s intervals on the 24 by 21 grid, one unit per legion or "
             f"ala (doc 63 §2.2, §8 rows 1-3); {D86}",
    "sides": "sourced: the Roman army under the consuls against Hannibal's army (S65 III.113-117, S66 XXII.45-49); "
             "no Carthaginian account survives (doc 37)",
    "player_side": f"sourced: the command, Terentius Varro, consul on the day (S65 III.113, S66 XXII.45), with the allied "
                   f"cavalry on the left (S65 III.114); the player choice is authored (doc 63 §8 row 27); {D86}",
    "scope": f"authored: headless only, as Pegasus, Hill 223 and Gergovia (doc 63 §9 q12); {D86}",
    "sources_pass": f"authored: Daly, Goldsworthy, Walbank, Lazenby and Polybius VI are pulled in parallel, not "
                    f"before the run (doc 63 §9 q11); every strength stays as doc 63 §6 sets it; {D86}",
    "hierarchy": f"authored: no sector commanders (doc 63 gap 5 deferred); the scripted controls issue each "
                 f"sector's orders from the one command detachment per side (doc 63 §9 q10); {D86}",
    "map": "authored: schematic open plain, no compass bearing and no site registration, since the sources "
           "disagree on facing (S65 III.113 south, S66 XXII.46 north, S70 east); doc 63 §7",
    "map.river": "sourced: the river covers the Roman right and the Carthaginian left (S65 III.113, S66 XXII.45-47); "
                 "an impassable side column, authored",
    "map.lane": "sourced: 'no room for maneuvering, the river on the one side and the infantry on the other' (S66 "
                "XXII.47); 2 hexes wide (doc 63 §8 row 11), authored",
    "map.exits": "inferred: the smaller camp, the larger camp and Cannae village as the fugitives' destinations "
                 "(S66 XXII.49); positions on the Roman edge authored (doc 63 §8 row 25)",
    "roman.mission": "sourced: give battle and decide the issue (S65 III.107.7, III.108.1); break the centre by "
                     "weight (S65 III.113; S67 p. 23)",
    "carthaginian.mission": "sourced: as Hannibal's speech and Polybius's judgment, ground for cavalry (S65 III.111), "
                            "the Romans caught 'as Hannibal had designed' (S65 III.115), disputed (S70 citing Healy)",
    "roman.command_unit": "sourced: Varro with the allied cavalry on the left (S65 III.114, S66 XXII.45)",
    "carthaginian.command_unit": "sourced: Hannibal with Mago in the centre (S65 III.114, III.116.1); C4 authored",
    "units.roman": "authored: on S67 p. 22, 16 heavy units of 3,550 (eight legions, S65 III.107.9; allied infantry "
                   "equal, III.107.12), 4 light units of 3,500, citizen horse 1,600 and allied horse 2 by 2,400 "
                   "(S67 p. 23); doc 63 §8 row 6",
    "units.carthaginian": "authored: on S65 III.114 and S67 pp. 24-25, Africans 2 by 5,000, Spanish and Celtic foot 8 "
                          "by 2,750, light troops 3 by 2,670, Hasdrubal's horse 3 by 2,170, Numidians 2 by 1,750; "
                          "the contingent split is authored (doc 63 §8 row 7)",
    "units.placement": "authored: on the sourced order (S65 III.113): the Roman block 8 wide and 2 deep, legions in "
                       "front; light troops one row ahead; cavalry on each flank; the crescent C3-C6 one hex ahead; "
                       "the Africans one hex behind each end of the centre (S67 p. 24); 3 hexes between the Roman "
                       "front row and the crescent (doc 63 §8 rows 8-10)",
    "units.off_map": "authored: the Roman camp force and the Carthaginian camp guard (S65 III.117) are off the map "
                     "(doc 63 §9 q8)",
    "army": f"authored: 13 per cent of a unit engaged in a volley, morale 2 points per per cent lost, flank 150 "
            f"and rear 200 per cent; doc 63 gap 3, 4 and §8 row 26 leave the values to implementation; {D86}",
    "movement": "authored: infantry 1 hex an interval (4 km/h), cavalry 3 (doc 63 §8 row 13)",
    "observation_range": "authored: 7 hexes (1.4 km), the engine cap (doc 63 §8 row 14)",
    "weapons": "authored: every class range 1; heavy 100, light 40 (doc 63 §6, §8 row 12), under tactics_v11",
    "communications": "authored: roman-216-v1 and carthage-216-v1, voice 1 hex, a mounted messenger at the engine "
                      "rates, 2 open hexes an interval and expiry 20 (doc 63 §8 rows 15-16)",
    "signal": f"sourced: Varro shows the signal for battle before he crosses (S66 XXII.45), before the 08:00 "
              f"start; its 6-hex reach (doc 63 §8 row 17) is recorded, and no signal sounds in the run; {D86}",
    "voice_profile": "authored: republic-en-v1 for the Roman side (docs/research/60 §4)",
    "doctrine.yield": "reconstruction: Carthaginian C1, the centre yields up to 3 hexes when pressed without "
                      "routing (doc 63 §3, §8 row 18; S67 p. 24 'likely' a fighting withdrawal)",
    "doctrine.wheel": "reconstruction: C1, the Africans wheel inward when a Roman unit stands past their front "
                      "row within 2 hexes (doc 63 §8 row 19; S65 III.115 'the situation itself indicating')",
    "doctrine.press": "reconstruction: R1, the heavy infantry presses toward the Carthaginian rear row once the "
                      "light troops have cleared, recall_binding false, loss limit 50 (doc 63 §8 row 21; S65 III.115)",
    "victory": "authored: encircle, zoc 1, 50 per cent enclosed or lost, a 5-of-8 centre break (doc 63 §5, §8 rows "
               "22-24); a reading of route geometry, not a historical result",
    "losses_check": "sourced: about 70,000 dead and 10,000 captured (S65 III.117) against 47,200 dead (S66 "
                    "XXII.49) and S67 p. 25; an order-of-magnitude check only",
    "scripted": "reconstruction: scripted controls from S65 and S66 (battle/cannae_policy.py)",
}


def cannae_entry(variant=None, *, design=True, wheels=AFRICANS, horse=1, dust=False, wide=False, reserve=False,
                 deserters=False, zoc=1, command="SC1", scripted=None, notes=None):
    """One Cannae entry; ``variant`` None is the catalog default. The
    keywords change one question each; ``notes`` adds provenance."""
    suffix = "" if variant is None else f"-{variant}"
    return ScenarioEntry(
        id="cannae-envelopment" + suffix,
        title="Cannae" + ("" if variant is None else f" ({variant})"),
        variant=variant,
        rules=RULES_VERSION,
        prompt_version="cannae-side-v1",
        prompt_setting="the plain of the Aufidus near Cannae, Apulia, 216 BCE",
        labels={RULES_VERSION: f"cannae-envelopment{suffix}-v1"},
        location="The plain by the Aufidus · Cannae, Apulia",
        date="216 BCE",
        start_time="08:00:00",
        time_basis=f"Scenario local time; authored: 08:00 at the first light-infantry contact; {D86}",
        seconds_per_turn=SECONDS_PER_TURN,
        weather={"season": "summer", "conditions": "daylight; fixed POC condition"},
        sides={
            "roman": SideEntry(name="Roman", role="attacker", command_unit=command, headquarters=ROMAN_HQ,
                               mission=ROMAN_MISSION, charge="break the centre without being enclosed"),
            "carthaginian": SideEntry(name="Carthaginian", role="defender", command_unit="C4",
                                      headquarters=CARTHAGINIAN_HQ, mission=CARTHAGINIAN_MISSION,
                                      charge="hold the centre and enclose the Roman army",
                                      communications=CARTHAGE_216_COMMUNICATIONS),
        },
        player_side="roman",
        units=roman_units(horse=horse, dust=dust, wide=wide, reserve=reserve)
        + carthaginian_units(design=design, wheels=wheels, deserters=deserters),
        victory=VictoryEntry(kind="encircle", objective=ROMAN_HQ, deadline_turns=DEADLINE,
                             objective_name="the larger camp", exits=tuple(EXITS.values()),
                             pocket_units=HEAVY,
                             centre_units=CENTRE, zoc=zoc, min_enclosed_pct=50, centre_break=5),
        map=MapEntry(terrain=terrain, features=FEATURES, cols=COLS, rows=ROWS, metres_per_hex=METRES_PER_HEX,
                     width=1080, height=840,
                     source="Authored, schematic: an open plain with the river on the Roman right (docs/research/63, 68).",
                     source_url=None),
        order_catalog=ORDER_CATALOG,
        communications=ROMAN_216_COMMUNICATIONS,
        voice_profile=ROMAN_VOICE_PROFILE,
        voice_reach=VOICE_REACH,
        fire=FIRE,
        weapons=WEAPONS,
        tactics=TACTICS_V11,
        army=ARMY,
        scripted=scripted or {"roman": ROMAN_POLICY, "carthaginian": CARTHAGINIAN_POLICY},
        provenance={**PROVENANCE, **(notes or {})},
    )


CANNAE_ENVELOPMENT = cannae_entry()


def _variants():
    table = (
        ("no-design", "doc 63 §8 no-design (C2)", "the centre has no yield doctrine; it holds or breaks under the "
         "ordinary rules; the Africans keep the wheel", "disputed design: S65 III.115; S70 citing Healy",
         dict(design=False)),
    ) + tuple(
        (f"cavalry-delayed-{d}", "doc 63 §8 cavalry-delayed (10, 20, 40)",
         f"Hasdrubal's horse waits {d} intervals after its trigger before it rides", "doc 36; authored",
         dict(scripted={"roman": ROMAN_POLICY, "carthaginian": cavalry_delay_policy(d)})) for d in CAVALRY_DELAYS
    ) + tuple(
        (f"one-wing-fixed-{uid.lower()}", "doc 63 §8 one-wing-fixed", f"{uid} has no wheel trigger", "doc 36",
         dict(wheels=tuple(a for a in AFRICANS if a != uid))) for uid in AFRICANS
    ) + (
        ("roman-reserve", "doc 63 §8 roman-reserve (R2)", "A7 and A8 start held on the river lane toward the "
         "smaller camp, with a hold order, and get no advance order", "doc 36; no source",
         dict(reserve=True, scripted={"roman": ROMAN_RESERVE_POLICY, "carthaginian": CARTHAGINIAN_POLICY})),
        ("aemilius-commands", "doc 63 §8 aemilius-commands", "the command detachment and the player are with "
         "Aemilius at EQ, the citizen cavalry on the right", "S67 p. 23", dict(command="EQ")),
        ("roman-horse-holds", "doc 63 §8 roman-horse-holds", "the Roman cavalry's strength is doubled",
         "authored; S67 p. 26 on timing", dict(horse=2)),
        ("dust", "doc 63 §8 dust", "every Roman unit sees 3 hexes", "S66 XXII.46", dict(dust=True)),
        ("deserters", "doc 63 §8 deserters", f"500 Numidians start in the Roman rear holding fire and attack at "
         f"interval {DESERTER_TURN}", "S66 XXII.48; not in S65",
         dict(deserters=True, scripted={"roman": ROMAN_POLICY, "carthaginian": DESERTERS_POLICY})),
        ("wide-front", "doc 63 §8 wide-front", "the Roman block is 16 wide and 1 deep", "authored control on S65 "
         "III.113", dict(wide=True)),
        ("zoc-0", "doc 63 §8 zoc-0", "only occupied hexes block an exit path", "authored; tests S67 p. 25",
         dict(zoc=0)),
    )
    return {name: Variant(question=q, reading=reading, source=src,
                          entry=cannae_entry(name, notes={"variant": f"authored: {reading}"}, **kw))
            for name, q, reading, src, kw in table}


VARIANTS = _variants()
