"""Period voice for display; canonical events and replay inputs stay untouched.

English is the only shipped locale. Stable message keys/arguments are a first
localization seam, not a claim that the entire POC is internationalized.
"""
from copy import deepcopy
import re

VOICE_PROFILE = 'civil-war-en-v1'
VOICE_INSTRUCTION = '''Write the human-readable text as a concise military dispatch
appropriate to the American Civil War in 1863. Address the player as General;
use restrained, readable period phrasing such as headquarters, detachment,
position, ammunition, runner, and orders. Avoid modern radio idioms such as
roger, copy that, over and out, and modern slang. Do not use caricatured dialect,
invent historical quotations, or obscure the meaning with theatrical archaism.
Keep every reported fact, uncertainty, map reference and delivery limitation intact.
Never invent a messenger, sighting or event merely for atmosphere. These voice
instructions apply only to prose, never to JSON keys, IDs or legal order values.
The current demo's output locale is English; localization is a product requirement.'''

# Hougoumont (docs/research/42): the same rules as the 1863 voice, set in 1815.
NAPOLEONIC_VOICE_PROFILE = 'napoleonic-en-v1'
NAPOLEONIC_VOICE_INSTRUCTION = '''Write the human-readable text as a concise military dispatch
appropriate to the Napoleonic Wars in 1815. Address the player as Colonel;
use restrained, readable period phrasing such as headquarters, detachment,
companies, position, cartridges, runner, and orders. Avoid modern radio idioms such as
roger, copy that, over and out, and modern slang. Do not use caricatured dialect,
invent historical quotations, or obscure the meaning with theatrical archaism.
Keep every reported fact, uncertainty, map reference and delivery limitation intact.
Never invent a messenger, sighting or event merely for atmosphere. These voice
instructions apply only to prose, never to JSON keys, IDs or legal order values.
The current demo's output locale is English; localization is a product requirement.'''

# Voice profile id -> prose instruction. A scenario entry names one of these.
VOICE_PROFILES = {VOICE_PROFILE: VOICE_INSTRUCTION, NAPOLEONIC_VOICE_PROFILE: NAPOLEONIC_VOICE_INSTRUCTION}

EN_DISPATCH = {
    'order.move.sent': 'To {unit}: Instructions to change position are on their way by runner. Delivery expected in {seconds} seconds.',
    'order.hold.sent': 'To {unit}: Instructions to hold position are on their way by runner. Delivery expected in {seconds} seconds.',
    'order.delivered': '{unit} to headquarters: Order {order} received.',
    'order.superseded': '{unit} to headquarters: Order {order} set aside in favour of later instructions.',
    'order.refused': '{unit} to headquarters: Unable to carry out order {order}.',
    'unit.arrived': '{unit} to headquarters: We have reached the appointed position.',
    'unit.routed': '{unit} to headquarters: The detachment is breaking. We are falling back toward headquarters.',
    'contact.reported': 'Enemy troops reported near map reference {column},{row}.',
}

# Adapter for existing poc-1 records. New canonical event envelopes should carry
# keys and typed arguments directly once a versioned event migration is approved.
PATTERNS = [
    (r'(?P<unit>\w+): (?P<stance>move|hold) order dispatched by runner\. Expected delivery in (?P<seconds>\d+) seconds\.', 'order.{stance}.sent'),
    (r'(?P<unit>\w+): order (?P<order>O\d+) (?P<status>delivered|superseded|refused)\.', 'order.{status}'),
    (r'(?P<unit>\w+): reached assigned position\.', 'unit.arrived'),
    (r'(?P<unit>\w+): formation breaking; withdrawing toward headquarters\.', 'unit.routed'),
    (r'Enemy formation reported near hex (?P<column>\d+),(?P<row>\d+)\.', 'contact.reported'),
]


def scenario_brief(entry, side):
    """Why: the command desk must show the current scenario's own text, and only
    the viewing side's mission.
    What: the display brief of ``entry`` for the player of ``side``: title, side
    names, that side's mission and outcome headlines, the objective's map text,
    the voice id. The opponent's mission is never included. Authored
    ``SideBrief``/``DeskBrief`` text is used when the entry has it; otherwise
    the text is derived from the entry's required fields.
    Test: `test_brief_carries_only_the_viewing_sides_mission`,
    `test_brief_is_derived_for_an_entry_without_authored_text`.
    """
    spec = entry.sides[side]
    foe = next(s for s in entry.sides if s != side)
    name = entry.victory.objective_name
    side_brief, desk = spec.brief, entry.desk
    ring = entry.victory.kind == 'hold-objective'
    return {
        'id': entry.id,
        'title': entry.title,
        'voice_profile': entry.voice_profile,
        'campaign': desk.campaign if desk else entry.location.upper(),
        'conditions': desk.conditions if desk else entry.weather.get('season', '').upper(),
        'side': {'id': side, 'name': spec.name},
        'opponent': {'id': foe, 'name': entry.sides[foe].name},
        'kicker': side_brief.kicker if side_brief else entry.title.upper(),
        'tagline': side_brief.tagline if side_brief else entry.prompt_setting,
        'subhead': side_brief.subhead if side_brief else
                   f'You command the {spec.name}. The computer commands the {entry.sides[foe].name}.',
        'mission': {'title': side_brief.mission_title if side_brief else 'Your mission',
                    'text': side_brief.mission_text if side_brief else spec.mission},
        'objective': {'place': desk.place if desk else name.capitalize(),
                      'label': desk.objective_label if desk else f'{name.upper()} OBJECTIVE',
                      'key': desk.objective_key if desk else name.upper(),
                      'ring': ring},
        'outcomes': {'win': side_brief.win if side_brief else 'Victory.',
                     'loss': side_brief.loss if side_brief else 'Defeat.',
                     'draw': desk.draw if desk else 'The battle ends in a draw.'},
    }


def present_view(observation, entry=None):
    """Voice id comes from the battle's scenario ``entry``; None (a saved game
    whose label no catalog knows) keeps the original 1863 voice."""
    result = deepcopy(observation)
    result['display_locale'] = 'en'
    result['voice_profile'] = entry.voice_profile if entry else VOICE_PROFILE
    for dispatch in result.get('dispatches', []):
        dispatch['display_text'] = dispatch['text'].replace(': dig_in order dispatched', ': dig in order dispatched')
        for pattern, key_pattern in PATTERNS:
            match = re.fullmatch(pattern, dispatch['text'])
            if not match:
                continue
            args = match.groupdict()
            key = key_pattern.format(**args)
            dispatch.update(message_key=key, message_args=args,
                            display_text=EN_DISPATCH[key].format(**args))
            break
    return result
