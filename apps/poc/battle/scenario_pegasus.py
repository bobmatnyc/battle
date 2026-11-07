"""Pegasus Bridge, 6 June 1944: a catalog entry and its variants (poc-13).

Why: the third of the first five selections (docs/research/37) asks whether
the glider platoons seize the canal bridge intact before the defence reacts
and hold it until relieved; doc 52 plans it and doc 53 supplies the 1944
rules (bridge state, company radio, codewords, night sight, one weapon range).
What: ``pegasus_entry`` builds one ``ScenarioEntry``; ``PEGASUS_BRIDGE`` is
the Architect-approved default (canal bridge only, demolish on contact,
relief about 3 hours after landing, S51). ``VARIANTS`` holds doc 52's named
alternatives and ``RANGE_SENSITIVITY`` the 1- and 3-hex weapon ranges, each
with its question and source. The map is authored, not surveyed. Every
field's basis is in the entry's ``provenance``; the runs are docs/research/54.
Test: `test_entry_registers_in_the_headless_catalog_after_a_dry_run`,
`test_each_named_variant_differs_in_its_own_question`.
"""

from dataclasses import replace

from .grid import COLS, METRES_PER_HEX, ROWS, key
from .presentation import WWII_VOICE_PROFILE
from .scenario_command import WeaponEntry
from .scenario_concord import Variant
from .scenario_entry import (
    ORDER_CATALOG, RULES_VERSION, MapEntry, ScenarioEntry, SideEntry, UnitEntry, VictoryEntry,
)
from .scenario_wwii import RADIO_COMMUNICATIONS, BridgeEntry, DemolitionEntry, SignalEntry

# Authored layout, not surveyed (doc 52 §7). North is row 0. Each waterway
# steps one column west below its bridge, so each bridge's radius-1 ring has
# two hexes on each bank (the balanced ring of docs/research/49).
CANAL_COL, ORNE_COL = 9, 19
CANAL, ORNE = (9, 10), (19, 10)  # Ten hexes apart: about 500 m (S54).
CANAL_WEST, CANAL_WEST_N, CANAL_EAST = (8, 10), (8, 9), (10, 10)
ORNE_WEST, ORNE_EAST = (18, 10), (20, 10)
WEAPON = "1944 small arms"  # The only class: one range for every unit (doc 52 §8 row 6).
TURNS_PER_HOUR = 120  # 30-second intervals.
RELIEF_TURN = 3 * TURNS_PER_HOUR  # S51: relief "reached us 3 hours after our landing".
NO_RELIEF_DEADLINE = 4 * TURNS_PER_HOUR  # Authored: one hour past the recorded relief.
# Scripted controls (battle/pegasus_policy.py); ids live here so the entry needs no policy import.
BRITISH_POLICY = "scripted-pegasus-coup-de-main-v1"
GUARD_POLICY = "scripted-pegasus-guard-v1"
EARLY_ALARM_POLICY = "scripted-pegasus-guard-early-alarm-v1"


def _water_col(base, r):
    return base if r <= CANAL[1] else base - 1


def terrain():
    cells = {}
    for r in range(ROWS):
        canal, orne = _water_col(CANAL_COL, r), _water_col(ORNE_COL, r)
        for c in range(COLS):
            cell = {"pos": [c, r], "elevation": 10, "terrain": "open", "move_cost": 100, "cover": 10,
                    "area": "benouville-bank" if c < canal else "ranville-bank" if c > orne else "between"}
            if canal + 3 <= c <= orne - 3 and r != CANAL[1]:
                cell.update(terrain="marsh", move_cost=160, cover=15, area="marsh")  # S54: marshy strip.
            if c in (canal, orne):
                water = "caen-canal" if c == canal else "river-orne"
                cell.update(elevation=8, terrain="water", water=True, cover=0, area=water)
                if (c, r) in (CANAL, ORNE):
                    cell.update(crossing="bridge", move_cost=100,
                                area="canal-bridge" if (c, r) == CANAL else "orne-bridge")
            cells[key([c, r])] = cell
    return cells


def _work(fid, name, pos, cover):
    return {"id": fid, "kind": "fortification", "name": name, "pos": list(pos), "cover": cover,
            "progress": 100, "effort": 400, "required": 400, "updated_turn": 0}


# Roads stop at each end of a bridge, so a bridge hex keeps its own cost.
FEATURES = {
    "roads": (
        {"id": "benouville-road", "kind": "road", "name": "Road from Bénouville to the canal bridge",
         "points": [[0, 10], list(CANAL_WEST)]},
        {"id": "bridges-road", "kind": "road", "name": "Road between the bridges",
         "points": [list(CANAL_EAST), list(ORNE_WEST)]},
        {"id": "ranville-road", "kind": "road", "name": "Road from the Orne bridge to Ranville",
         "points": [list(ORNE_EAST), [23, 10]]},
    ),
    "buildings": (),
    # S54 lists these defences; their hexes and cover values are authored.
    "works": (
        _work("west-mg-posts", "Machine-gun emplacements, west bank", CANAL_WEST, 50),
        _work("west-trenches", "Trench system, west bank", CANAL_WEST_N, 40),
        _work("east-mg-post", "Machine gun and anti-tank gun, east bank", CANAL_EAST, 50),
        _work("orne-pillbox", "Pillbox, east bank of the Orne", ORNE_EAST, 60),
    ),
}


def _men(n):
    return {"initial": n, "strength": n, "ammo": n * 40, "weapon_class": WEAPON}


HQ = UnitEntry("DHQ", "british", "D Company headquarters · Howard", (10, 13), _men(15))
CANAL_PLATOONS = (  # S51 p. 1 para 3; S52 sheets 1-2 (gliders 91, 92, 93).
    UnitEntry("D25", "british", "25 Platoon · Brotheridge", (9, 11), _men(30)),
    # D2 review: the only platoon a source puts sappers with (S52 sheet 2, No. 92).
    UnitEntry("D24", "british", "24 Platoon · Wood, with Capt Neilson RE", (10, 11),
              {**_men(30), "clears_charges": True}),
    UnitEntry("B14", "british", "14 Platoon (B Company) · Smith", (10, 12), _men(30)),
)
ORNE_PLATOONS = (  # S51 p. 1 para 3; S52 sheet 3 (gliders 96 and 95).
    UnitEntry("B17", "british", "17 Platoon (B Company) · Fox", (17, 9), _men(30)),
    UnitEntry("D23", "british", "23 Platoon · Sweeney, landed to the north", (17, 1), _men(30)),
)
CANAL_GUARD = (  # S54: 50 men of the 736th Grenadier Regiment; the split is authored.
    UnitEntry("G1", "german", "Bridge guard · machine-gun posts, west bank", CANAL_WEST, _men(14)),
    UnitEntry("G2", "german", "Bridge guard · machine gun and anti-tank gun, east bank", CANAL_EAST, _men(12)),
    UnitEntry("G3", "german", "Bridge guard · trench post, west bank", CANAL_WEST_N, _men(12)),
)
ORNE_GUARD = (UnitEntry("G4", "german", "Bridge guard · Orne pillbox", ORNE_EAST, _men(12)),)
RESERVE = (  # S54 times; the groups, hexes and strengths are authored.
    UnitEntry("GHQ", "german", "Guard command post (stands in for the alarm chain)", (0, 16), _men(15)),
    UnitEntry("R1", "german", "Counter-attack group from the west (21st Panzer; not modelled as armour)",
              (0, 10), _men(30)),
    UnitEntry("R2", "german", "Infantry and self-propelled-gun group from the south", (3, 20), _men(60)),
)

SINGLE_RANGE = 2
SMALL_ARMS = WeaponEntry(
    range_hexes=SINGLE_RANGE, effect_pct=100,
    basis="assumption: one authored night range of 100 m (2 hexes) for every weapon, at the rifle-baseline "
          "effect; rifle, machine gun, PIAT and anti-tank gun are not modelled apart (docs/research/52 §8 row 6)")
NIGHT_RANGE = 2  # doc 52 §8 row 1: an assumption, no source gives night sight in hexes.
ON_CONTACT = DemolitionEntry(
    side="german", trigger="contact", delay=4, reach=1, removal_turns=2,
    basis="inferred: the guard's orders to blow the bridges if capture threatened (S54, secondary); the "
          "2-minute delay from first sight to firing, the 1-hex firing reach and the 1-minute clearing by "
          "sappers on the bridge are authored, no source gives them")
HAM = SignalEntry("Ham", "Canal bridge taken intact.", "british", "canal-bridge",
                  basis="sourced, secondary: Ham meant the canal bridge was taken (S54); the trigger is authored")
JAM = SignalEntry("Jam", "River bridge taken intact.", "british", "orne-bridge",
                  basis="sourced, secondary: Jam meant the river bridge was taken (S54); the trigger is authored")


def _bridge(bid, name, pos, demolition):
    return BridgeEntry(bid, name, pos, state="charges", demolition=demolition,
                       basis="inferred: wired with charges (S54, secondary; S51 p. 1 para 3: sappers "
                             "'cut wires and removed charges')")


BRITISH_MISSION = (
    "You command D Company, 2nd Ox and Bucks, landed by glider beside the Caen Canal bridge at Bénouville. "
    "Your mission: seize the bridge intact and hold the ground within one hex of it until relieved by "
    "7th Parachute Battalion. Report the bridge taken with the codeword Ham.")
GERMAN_MISSION = (
    "You command the guard on the Caen Canal bridge and the reserve that answers its alarm. Your mission: "
    "keep the bridge out of enemy hands; if capture threatens, fire the charges.")

PROVENANCE = {
    "location": "sourced: the Caen Canal bridge at Bénouville and the Orne bridge at Ranville (S51 p. 1 para 2)",
    "date": "sourced: 6 June 1944 (S51, S52)",
    "start_time": "sourced: 00:25, the first glider down (S51 p. 1 para 3); S53 says 'just after midnight'",
    "weather": "sourced: a cloudy night (S52 sheet 2); a fixed POC condition",
    "sides": "sourced: D Company and attached B Company platoons, 2nd Ox and Bucks, against the bridge "
             "guard of the 736th Grenadier Regiment (S51, S52, S54)",
    "player_side": "authored: the fixture asks whether the platoons seize the crossing (docs/research/52 §2)",
    "scope": "authored: the canal bridge only (Architect default, doc 52 §2); the Orne bridge is in the "
             "both-bridges and orne-platoons variants",
    "british.mission": "sourced: seize the bridge intact and hold until relieved (S51 p. 1 paras 2-3; S52 "
                       "sheet 1 §2; S54); the codeword clause is S54, secondary",
    "german.mission": "inferred: guard the bridges and blow them if capture threatens (S54, secondary, no "
                      "primary cited); no order to the guard was read (doc 52 §1)",
    "british.command_unit": "reconstruction: the company commander landed with 25 Pln (S51 p. 1 para 3); a "
                            "separate headquarters detachment of authored strength stands in for his party "
                            "so the codeword travels from the bridge to him",
    "german.command_unit": "authored: a command post stands in for the 716th Division and 736th Regiment "
                           "chain that passed the alarm (S54, S55); Schmidt was away (S54)",
    "units.british": "sourced: platoons 25, 24 and 14 at the canal bridge, 17 and 23 at the Orne bridge, "
                     "Capt Neilson RE with 24 (S51 p. 1 para 3, S52 sheets 2-3); strengths of 30 are "
                     "authored (doc 52 §6)",
    "units.german": "sourced: about 50 men in all (S51 p. 1 para 2, S54); the split into posts of 14, 12, "
                    "12 at the canal bridge and 12 at the Orne bridge is authored",
    "units.reserve": "sourced: secondary, armour from the west near 02:00, infantry and self-propelled guns "
                     "from the south near 03:00 (S54; S51 'within an hour'); the two groups, their hexes "
                     "and strengths of 30 and 60 are authored and are not modelled as armour",
    "units.sappers": "sourced: only 24 Pln declares clears_charges: glider No. 92 carried 24 Pln and Capt "
                     "Neilson RE (S52 sheet 2), and sappers 'cut wires and removed charges' at the canal "
                     "bridge (S51 p. 1 para 3); S51 and S52 name no sappers with the other platoons, so none "
                     "is declared. The clearing time is authored; the sappers' behaviour is not validated",
    "units.placement":"reconstruction: the platoons start where they touched down (doc 52 §8 row 2): 25 "
                       "within 80 ft of the bridge (S51), 24 and 14 within 50 yards (S51 p. 1 para 2); "
                       "the landing order is not modelled",
    "map": "authored: illustrative layout, not surveyed; no map sheet was read (doc 52 §7)",
    "map.banks": "reconstruction: the gliders landed in field X east of the canal and attacked west; the "
                 "German posts stand on both banks (S54); each ring has two hexes a bank (authored)",
    "map.defences": "sourced: machine-gun emplacements and trenches on the west bank, a machine gun and an "
                    "anti-tank gun on the east bank (S54); their hexes and cover are authored; the pillbox "
                    "'to the north' is not placed (bank unknown)",
    "bridge": "inferred: the canal bridge is wired with charges (S54, secondary)",
    "demolition": "inferred: demolish on contact (Architect default, doc 52 §10 question 2); the trigger, "
                  "the 2-minute delay, the firing reach and the clearing time are authored "
                  "(docs/research/54)",
    "alarm": "inferred: the guard's alarm (S54: a flare; S52 sheet 2: a flare seen before landing) reaches "
             "the reserve by the scripted German control (battle/pegasus_policy.py)",
    "relief": "sourced: relief reached the company about 3 hours after landing (S51 p. 1 para 3); modelled "
              "as the seize-and-hold relief turn, not as arriving units",
    "victory": "authored: seize-and-hold, radius 1, 2 intervals to seize, held to the relief turn "
               "(doc 52 §5); the historical outcome, both bridges taken intact, is sourced (S51, S52 sheet 4)",
    "observation_range": "authored: a night sight of 2 hexes for every unit, an assumption (doc 52 §8 row 1)",
    "weapons": "authored: one 2-hex range for every unit (doc 52 §8 row 6); run at 1, 2 and 3 hexes",
    "communications": "authored: wwii-1944-radio-v1, radio 10 hexes, voice 2 (assumptions, docs/research/53)",
    "voice_profile": "authored: the 1944 British voice; no historical message is quoted",
    "signals": "sourced: secondary, Ham (S54); the trigger is authored and counts only the enemies within the "
               "holder's radius that the holder sees (docs/research/54)",
    "scripted": "reconstruction: scripted policies from S51 and S52 (British) and inferred German intent "
                "(battle/pegasus_policy.py)",
}


def pegasus_entry(variant=None, *, british=CANAL_PLATOONS, german=CANAL_GUARD, objectives=(CANAL,),
                  bridges=None, signals=(HAM,), relief_turn=RELIEF_TURN, deadline=RELIEF_TURN,
                  scripted=None, weapons=None, notes=None):
    """One Pegasus entry; ``variant`` None is the catalog default. The
    keywords change one question each; ``notes`` adds provenance."""
    suffix = "" if variant is None else f"-{variant}"
    bridges = bridges if bridges is not None else (_bridge("canal-bridge", "Caen Canal bridge", CANAL, ON_CONTACT),)
    name = {(CANAL,): "canal bridge", (ORNE,): "Orne bridge"}.get(tuple(objectives), "canal and Orne bridges")

    return ScenarioEntry(
        id="pegasus-bridge" + suffix,
        title="Pegasus Bridge" + ("" if variant is None else f" ({variant})"),
        variant=variant,
        rules=RULES_VERSION,
        prompt_version="pegasus-side-v1",
        prompt_setting="the Caen Canal bridge at Bénouville, June 1944",
        labels={RULES_VERSION: f"pegasus-bridge{suffix}-v1"},
        location="Caen Canal bridge · Bénouville, Normandy",
        date="1944-06-06",
        start_time="00:25:00",
        time_basis="Scenario local time; sourced: the first glider landed at 00:25 (S51 p. 1 para 3)",
        seconds_per_turn=30,
        weather={"season": "summer", "conditions": "night, cloudy (S52 sheet 2); fixed POC condition"},
        sides={
            "british": SideEntry(
                name="British", role="attacker", command_unit="DHQ", headquarters=(12, 17),
                mission=BRITISH_MISSION, charge="seize the canal bridge intact and hold it until relieved"),
            "german": SideEntry(
                name="German", role="defender", command_unit="GHQ", headquarters=(0, 15),
                mission=GERMAN_MISSION, charge="hold the canal bridge or blow it"),
        },
        player_side="british",
        units=(HQ,) + tuple(british) + tuple(german) + RESERVE,
        victory=VictoryEntry(kind="seize-and-hold", objective=objectives[0], deadline_turns=deadline,
                             radius=1, hold_turns=2, objective_name=name,
                             more_objectives=tuple(objectives[1:]), relief_turn=relief_turn),
        map=MapEntry(terrain=terrain, features=FEATURES, cols=COLS, rows=ROWS,
                     metres_per_hex=METRES_PER_HEX, width=1080, height=840,
                     source=("Authored, not surveyed: an illustrative Caen Canal, Orne and the marsh between "
                             "(docs/research/52, 54)."),
                     source_url=None),
        order_catalog=ORDER_CATALOG,
        communications=RADIO_COMMUNICATIONS,
        voice_profile=WWII_VOICE_PROFILE,
        weapons=weapons or {WEAPON: SMALL_ARMS},
        bridges=bridges,
        signals=signals,
        observation_range=NIGHT_RANGE,
        scripted=scripted or {"british": BRITISH_POLICY, "german": GUARD_POLICY},
        provenance={**PROVENANCE, **(notes or {})},
    )


PEGASUS_BRIDGE = pegasus_entry()


def _variants():

    canal = _bridge("canal-bridge", "Caen Canal bridge", CANAL, ON_CONTACT)
    orne = _bridge("orne-bridge", "Orne bridge", ORNE, ON_CONTACT)
    table = (
        ("both-bridges", "doc 52 §10 question 1 (scope), variant B",
         "the Orne bridge is a second objective: platoons 17 and 23, the Orne guard and the Jam codeword",
         "S51 p. 1 paras 2-3: two bridges; S52 sheet 3; Jam: S54, secondary",
         dict(british=CANAL_PLATOONS + ORNE_PLATOONS, german=CANAL_GUARD + ORNE_GUARD,
              objectives=(CANAL, ORNE), bridges=(canal, orne), signals=(HAM, JAM))),
        ("orne-platoons", "doc 52 §10 question 1 (scope), variant C",
         "the Orne bridge alone, with platoons 17 and 23 and the Orne guard; the canal bridge is plain terrain",
         "S51 p. 1 para 3; S52 sheet 3 (No. 96 'took it with little opposition'); Jam: S54, secondary",
         dict(british=ORNE_PLATOONS, german=ORNE_GUARD, objectives=(ORNE,), bridges=(orne,), signals=(JAM,))),
        ("guard-only", "doc 52 §10 question 2 (German intent)",
         "the guard holds and never fires the charges",
         "inferred: S54's demolition order is secondary with no primary cited",
         dict(bridges=(replace(canal, demolition=None),))),
        ("demolish-on-crossing", "doc 52 §10 question 2 (German intent)",
         "the guard fires the charges once a British unit is on the bridge, not at first sight",
         "inferred: S54 'if they were in danger of capture'; the trigger is authored",
         dict(bridges=(replace(canal, demolition=replace(ON_CONTACT, trigger="crossing")),))),
        ("relief-1h", "doc 52 §10 question 4 (relief timing)",
         f"relief at {TURNS_PER_HOUR} intervals (01:25), the expected time",
         "inferred: S51 p. 1 para 3, relief came '2 hours later than expected' at 3 hours",
         dict(relief_turn=TURNS_PER_HOUR)),
        ("no-relief", "doc 52 §10 question 4 (relief timing)",
         f"no relief: the bridge must be held to an authored deadline of {NO_RELIEF_DEADLINE} intervals (04:25)",
         "authored: the deadline is one hour past S51's relief, so the 03:00 attack (S54) plays out",
         dict(relief_turn=None, deadline=NO_RELIEF_DEADLINE)),
        ("early-alarm", "doc 52 §9 S3 (G2 early alarm)",
         "the reserve is ordered forward at touchdown plus one minute, not near the S54 times",
         "reconstruction: doc 52 §3 G2, a sensitivity of the alarm, no source",
         dict(scripted={"british": BRITISH_POLICY, "german": EARLY_ALARM_POLICY})),
    )
    return {name: Variant(question=q, reading=reading, source=src,
                          entry=pegasus_entry(name, notes={"variant": f"authored: {reading}"}, **kw))
            for name, q, reading, src, kw in table}


def _ranges():
    out = {}
    for hexes in (1, 3):
        name = f"range-{hexes}"
        weapon = replace(SMALL_ARMS, range_hexes=hexes,
                         basis=f"assumption: sensitivity, one {hexes}-hex range for every weapon (doc 52 §8 row 6)")
        out[name] = Variant(
            question="doc 52 §9 S5 (weapon range sensitivity)",
            reading=f"sensitivity: one weapon range of {hexes} hexes instead of {SINGLE_RANGE}",
            source="authored: no source gives a night range in hexes",
            entry=pegasus_entry(name, weapons={WEAPON: weapon},
                                notes={"sensitivity": f"authored: sensitivity: weapon range {hexes} hexes"}))
    return out


VARIANTS = _variants()
RANGE_SENSITIVITY = _ranges()


def _relabel(entry, name, note, **changes):
    ident = f"pegasus-bridge-{name}"
    return replace(entry, id=ident, title=f"Pegasus Bridge ({name})", variant=name,
                   labels={RULES_VERSION: f"{ident}-v1"},
                   provenance={**entry.provenance, "sensitivity": f"authored: sensitivity: {note}"}, **changes)


def _crossed():
    """docs/research/54: the default demolition ends every run at turn 5, so the
    relief, alarm and range questions are also run with the guard-only bridge,
    and the demolition delay is swept. Sensitivity runs only, in no catalog."""
    guard = VARIANTS["guard-only"].entry.bridges
    out = {}
    for base in ("range-1", "range-3", "relief-1h", "no-relief", "early-alarm"):
        source = (RANGE_SENSITIVITY | VARIANTS)[base]
        out[f"guard-only+{base}"] = Variant(
            question=f"{source.question}, crossed with guard-only",
            reading=f"sensitivity: {source.reading}, and the guard never fires the charges",
            source=source.source,
            entry=_relabel(source.entry, f"guard-only+{base}", f"{base} with no demolition", bridges=guard))
    canal = PEGASUS_BRIDGE.bridges[0]
    for delay in (8, 9, 10, 11, 12, 13, 14, 15, 16, 32):  # D2 review: bracket the measured boundary.
        name = f"delay-{delay}"
        bridge = replace(canal, demolition=replace(ON_CONTACT, delay=delay))
        out[name] = Variant(
            question="docs/research/54 (does the demolition delay decide the race)",
            reading=f"sensitivity: the guard fires {delay} intervals after first sight, not {ON_CONTACT.delay}",
            source="authored: no source gives the delay",
            entry=_relabel(PEGASUS_BRIDGE, name, f"demolition delay {delay} intervals", bridges=(bridge,)))
    return out


CROSSED_SENSITIVITY = _crossed()
