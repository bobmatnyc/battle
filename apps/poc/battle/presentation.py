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

# poc-13B: the 1775 voice (docs/research/47), on the same rules as the others.
COLONIAL_VOICE_PROFILE = 'colonial-1775-en-v1'
COLONIAL_VOICE_INSTRUCTION = '''Write the human-readable text as a concise military report
appropriate to the American Revolution in 1775. Address the player as Colonel;
use restrained, readable period phrasing such as companies, the column, the ground,
powder and ball, the regulars, word passed, runner, and orders. Avoid modern radio
idioms such as roger, copy that, over and out, and modern slang. Do not use caricatured
dialect, invent historical quotations, or obscure the meaning with theatrical archaism.
Keep every reported fact, uncertainty, map reference and delivery limitation intact.
Never invent a messenger, sighting or event merely for atmosphere. These voice
instructions apply only to prose, never to JSON keys, IDs or legal order values.
The current demo's output locale is English; localization is a product requirement.'''

# docs/research/53: the 1944 British voice. The address is the company
# commander's rank, Major (S51 is "the first report by Major Howard"); the
# register is authored and quotes no historical message.
WWII_VOICE_PROFILE = 'wwii-1944-en-v1'
WWII_VOICE_INSTRUCTION = '''Write the human-readable text as a concise British Army report
appropriate to the Second World War in June 1944. Address the player as Major, the
company commander; never as General. Use restrained, readable period phrasing such as
platoon, section, company headquarters, the bridge, wireless, runner, ammunition, and orders.
Avoid modern idioms such as copy that, ten-four, affirmative, and modern slang. Do not use
caricatured dialect, invent historical quotations, or obscure the meaning with theatrical archaism.
Keep every reported fact, uncertainty, map reference and delivery limitation intact.
Never invent a messenger, sighting or event merely for atmosphere. These voice
instructions apply only to prose, never to JSON keys, IDs or legal order values.
The current demo's output locale is English; localization is a product requirement.'''

# docs/research/59: the American 1918 voice. Authored register; it quotes no
# historical message. The address is "Sir" because the player's rank is not
# yet chosen (docs/research/56, open question 1).
WWI_VOICE_PROFILE = 'wwi-1918-en-v1'
WWI_VOICE_INSTRUCTION = '''Write the human-readable text as a concise American Army report
appropriate to the American Expeditionary Forces in France in 1918. Address the player as Sir;
never as General. Use plain, readable infantry phrasing such as sergeant, corporal, squad, platoon,
company, the line, the post, runner, prisoners, ammunition, and orders. There is no radio or field
telephone at this echelon: word goes by voice or by runner. Avoid modern idioms such as copy that,
roger, ten-four, affirmative, and modern slang. Do not use caricatured dialect, invent historical
quotations, or obscure the meaning with theatrical archaism.
Keep every reported fact, uncertainty, map reference and delivery limitation intact.
Never invent a messenger, sighting or event merely for atmosphere. These voice
instructions apply only to prose, never to JSON keys, IDs or legal order values.
The current demo's output locale is English; localization is a product requirement.'''

# docs/research/60: the Roman voice, Caesar's army in Gaul in 52 BCE. Authored
# register in the manner of a Latin field report put into plain English; it
# quotes no ancient text. The address "Imperator" is authored (docs/research/57 §6).
ROMAN_VOICE_PROFILE = 'republic-en-v1'
ROMAN_VOICE_INSTRUCTION = '''Write the human-readable text as a concise report to Caesar
appropriate to a Roman army of the late Republic in Gaul in 52 BCE. Address the player as Imperator;
never as General. Use plain, readable phrasing in the register of a Latin field report put into
English, such as legion, cohort, century, legate, tribune, centurion, the standards, the trumpet,
the camp, the rampart, missiles, runner, and orders. Word goes by trumpet signal, by voice or by
runner; there is no radio, telegraph or written relay. Avoid modern idioms such as copy that,
roger, ten-four, affirmative, and modern slang. Do not use caricatured dialect, Latin tags the
reader must translate, invented historical quotations, or theatrical archaism.
Keep every reported fact, uncertainty, map reference and delivery limitation intact.
Never invent a messenger, sighting or event merely for atmosphere. These voice
instructions apply only to prose, never to JSON keys, IDs or legal order values.
The current demo's output locale is English; localization is a product requirement.'''

# Voice profile id -> prose instruction. A scenario entry names one of these.
VOICE_PROFILES = {VOICE_PROFILE: VOICE_INSTRUCTION, NAPOLEONIC_VOICE_PROFILE: NAPOLEONIC_VOICE_INSTRUCTION,
                  COLONIAL_VOICE_PROFILE: COLONIAL_VOICE_INSTRUCTION, WWII_VOICE_PROFILE: WWII_VOICE_INSTRUCTION,
                  WWI_VOICE_PROFILE: WWI_VOICE_INSTRUCTION, ROMAN_VOICE_PROFILE: ROMAN_VOICE_INSTRUCTION}

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

# poc-13B: 1775 order text (docs/research/47). Display only: the stored
# dispatch text, events and replay inputs are unchanged. The words name each
# order template in period phrasing; they quote no historical order.
COLONIAL_ORDER_WORDS = {
    'hold': 'Stand fast', 'move': 'Shift your ground', 'rest': 'Rest the men',
    'retreat': 'Fall back', 'resupply': 'Draw powder and ball', 'recon': 'Scout the ground',
    'dig_in': 'Throw up a breastwork', 'close_gate': 'Shut the gate',
    'hold_fire': 'Hold your fire unless fired upon', 'open_fire': 'Open fire',
}
COLONIAL_PATTERNS = [
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by voice\. (?P<estimate>.*)', 'order.spoken'),
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by runner\. (?P<estimate>.*)', 'order.carried'),
]
COLONIAL_DISPATCH = {
    'order.spoken': 'To {unit}: {words}. Given by word of mouth. {estimate}',
    'order.carried': 'To {unit}: {words}. A runner carries the word. {estimate}',
    'order.delivered': '{unit} to the Colonel: Your order {order} is received.',
    'order.superseded': '{unit} to the Colonel: Order {order} is set aside for later word.',
    'order.refused': '{unit} to the Colonel: We cannot carry out order {order}.',
    'unit.arrived': '{unit} to the Colonel: We are come to the ground appointed.',
    'unit.routed': '{unit} to the Colonel: The company is giving way and falls back.',
}
# docs/research/53: 1944 British order text, display only like the 1775 text.
# Authored phrasing; it quotes no historical order. "Wireless" is the British
# word for radio in 1944.
WWII_ORDER_WORDS = {
    'hold': 'Hold your position', 'move': 'Move to the new position', 'rest': 'Rest the men',
    'retreat': 'Withdraw', 'resupply': 'Draw ammunition', 'recon': 'Patrol forward',
    'dig_in': 'Dig in', 'close_gate': 'Close the gate',
    'hold_fire': 'Hold your fire unless fired upon', 'open_fire': 'Open fire',
}
WWII_PATTERNS = [
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by voice\. (?P<estimate>.*)', 'order.spoken'),
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by radio\. (?P<estimate>.*)', 'order.radioed'),
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by runner\. (?P<estimate>.*)', 'order.carried'),
]
WWII_DISPATCH = {
    'order.spoken': 'To {unit}: {words}. Given by word of mouth. {estimate}',
    'order.radioed': 'To {unit}: {words}. Sent by wireless. {estimate}',
    'order.carried': 'To {unit}: {words}. Sent by runner. {estimate}',
    'order.delivered': '{unit} to company headquarters: Order {order} received, sir.',
    'order.superseded': '{unit} to company headquarters: Order {order} set aside for later orders.',
    'order.refused': '{unit} to company headquarters: Unable to carry out order {order}.',
    'unit.arrived': '{unit} to company headquarters: In position.',
    'unit.routed': '{unit} to company headquarters: We are being pushed back and are falling back.',
}
# docs/research/59: American 1918 order text, display only like the 1944 text.
# Authored phrasing; it quotes no historical order.
WWI_ORDER_WORDS = {
    'hold': 'Hold where you are', 'move': 'Move up to the new position', 'rest': 'Rest the men',
    'retreat': 'Fall back', 'resupply': 'Draw ammunition', 'recon': 'Patrol ahead',
    'dig_in': 'Dig in', 'close_gate': 'Close the gate',
    'hold_fire': 'Hold your fire unless fired upon', 'open_fire': 'Open fire',
}
WWI_PATTERNS = [
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by voice\. (?P<estimate>.*)', 'order.spoken'),
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by runner\. (?P<estimate>.*)', 'order.carried'),
    (r'(?P<unit>\w+): (?P<count>\d+) prisoners taken from (?P<source>\w+)\.', 'captives.taken'),
]
WWI_DISPATCH = {
    'order.spoken': 'To {unit}: {words}. Passed by word of mouth. {estimate}',
    'order.carried': 'To {unit}: {words}. Sent by runner. {estimate}',
    'order.delivered': '{unit} to headquarters: Order {order} received, sir.',
    'order.superseded': '{unit} to headquarters: Order {order} set aside for later orders.',
    'order.refused': '{unit} to headquarters: Unable to carry out order {order}.',
    'unit.arrived': '{unit} to headquarters: In position.',
    'unit.routed': '{unit} to headquarters: We are being driven back and are falling back.',
    'captives.taken': '{unit} to headquarters: We have taken {count} prisoners from {source}.',
}
# docs/research/60: Roman order text, display only like the 1918 text. Authored
# phrasing; it quotes no ancient order.
ROMAN_ORDER_WORDS = {
    'hold': 'Stand your ground', 'move': 'Advance to the place appointed', 'rest': 'Rest the men',
    'retreat': 'Withdraw', 'resupply': 'Draw fresh missiles', 'recon': 'Scout the ground',
    'dig_in': 'Entrench', 'close_gate': 'Close the gate',
    'hold_fire': 'Hold your missiles unless attacked', 'open_fire': 'Loose missiles',
}
ROMAN_PATTERNS = [
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by voice\. (?P<estimate>.*)', 'order.spoken'),
    (r'(?P<unit>\w+): (?P<stance>\w+) order dispatched by runner\. (?P<estimate>.*)', 'order.carried'),
    (r'(?P<unit>\w+): signal (?P<signal>[\w-]+) sounded\. (?P<meaning>.*)', 'signal.sounded'),
]
ROMAN_DISPATCH = {
    'order.spoken': 'To {unit}: {words}. Given by word of mouth. {estimate}',
    'order.carried': 'To {unit}: {words}. A runner carries the word. {estimate}',
    'order.delivered': '{unit} to Caesar: Your order {order} is received.',
    'order.superseded': '{unit} to Caesar: Order {order} is set aside for later orders.',
    'order.refused': '{unit} to Caesar: We cannot carry out order {order}.',
    'unit.arrived': '{unit} to Caesar: We stand at the place appointed.',
    'unit.routed': '{unit} to Caesar: The men are giving way and fall back.',
    'signal.sounded': 'The trumpets sound from {unit}: {meaning}',
}
# Voice id -> (patterns tried first, dispatch text, order words).
VOICE_DISPATCH = {COLONIAL_VOICE_PROFILE: (COLONIAL_PATTERNS, COLONIAL_DISPATCH, COLONIAL_ORDER_WORDS),
                  WWII_VOICE_PROFILE: (WWII_PATTERNS, WWII_DISPATCH, WWII_ORDER_WORDS),
                  WWI_VOICE_PROFILE: (WWI_PATTERNS, WWI_DISPATCH, WWI_ORDER_WORDS),
                  ROMAN_VOICE_PROFILE: (ROMAN_PATTERNS, ROMAN_DISPATCH, ROMAN_ORDER_WORDS)}

# Text of a scripted decision record, by voice; other voices keep the 1863 line.
SCRIPTED_TEXT = 'General, we shall proceed according to our standing orders.'
SCRIPTED_TEXTS = {COLONIAL_VOICE_PROFILE: 'Colonel, the companies will proceed according to their standing orders.',
                  WWII_VOICE_PROFILE: 'Major, the platoons will carry on under their standing orders.',
                  WWI_VOICE_PROFILE: 'Sir, the men will carry on under their standing orders.',
                  ROMAN_VOICE_PROFILE: 'Imperator, the cohorts will carry on under their standing orders.'}


# poc-13B review: how staff address the player, by voice. Standing-order,
# recommendation and staff-assessment text is stored as "General, ..."; a voice
# listed here shows it with its own title. Other voices add no display field.
# docs/research/53: the 1944 player commands a company, as a Major (S51).
VOICE_ADDRESS = {COLONIAL_VOICE_PROFILE: 'Colonel', WWII_VOICE_PROFILE: 'Major', WWI_VOICE_PROFILE: 'Sir',
                 ROMAN_VOICE_PROFILE: 'Imperator'}
# docs/research/75 (slice 1 review): how the scripted staff answer says orders travel, by
# voice, matching each voice's communications profile (comms.PROFILES): 1775 voice within
# earshot, else runner; 1944 wireless, voice and runner; 1918 voice close by, else runner.
# Voices not listed (1863, 1815) keep the runner-only line, unchanged.
STAFF_ORDERS = 'Send your instructions by runner; '
STAFF_ORDERS_BY_VOICE = {
    COLONIAL_VOICE_PROFILE: 'Give your orders by word of mouth to the companies within earshot, '
                            'or send them by runner; ',
    WWII_VOICE_PROFILE: 'Send your orders by wireless, by word of mouth close by, or by runner; ',
    WWI_VOICE_PROFILE: 'Pass your orders by word of mouth close by, or send them by runner; ',
}


def staff_orders_text(voice_profile):
    """The scripted staff answer's line on how orders travel, in ``voice_profile``.
    Test: `test_the_closing_follows_each_voice_and_its_transport`."""
    return STAFF_ORDERS_BY_VOICE.get(voice_profile, STAFF_ORDERS)


def _address(text, title):
    return title + text[len('General'):] if text.startswith('General, ') else text


def present_analysis(analysis, entry=None):
    """The staff assessment for display: in a voice with its own address
    (``VOICE_ADDRESS``) each recommendation gains ``display_reason``.
    Test: `test_1775_standing_and_recommendation_text_does_not_say_general`."""
    title = VOICE_ADDRESS.get(entry.voice_profile if entry else VOICE_PROFILE)
    if title:
        for row in analysis.get('units', []):
            row['recommendation']['display_reason'] = _address(row['recommendation']['reason'], title)
    return analysis


def scripted_text(voice_profile):
    """The scripted decision's text in ``voice_profile`` (poc-13B: 1775 has its own)."""
    return SCRIPTED_TEXTS.get(voice_profile, SCRIPTED_TEXT)


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
    """Why: dispatches must read in the scenario's period voice.
    What: ``observation`` with display text per dispatch. The voice id comes
    from the battle's scenario ``entry``; None (a saved game whose label no
    catalog knows) keeps the original 1863 voice. A voice in
    ``VOICE_DISPATCH`` tries its own patterns first and overrides the text.
    Test: `test_1775_order_text_is_in_the_period_voice`."""
    result = deepcopy(observation)
    result['display_locale'] = 'en'
    result['voice_profile'] = voice = entry.voice_profile if entry else VOICE_PROFILE
    patterns, table, words = VOICE_DISPATCH.get(voice, ((), {}, {}))
    texts = {**EN_DISPATCH, **table}
    for dispatch in result.get('dispatches', []):
        dispatch['display_text'] = dispatch['text'].replace(': dig_in order dispatched', ': dig in order dispatched')
        for pattern, key_pattern in (*patterns, *PATTERNS):
            match = re.fullmatch(pattern, dispatch['text'])
            if not match:
                continue
            args = match.groupdict()
            key = key_pattern.format(**args)
            shown = dict(args, words=words.get(args.get('stance'), args.get('stance', '')))
            dispatch.update(message_key=key, message_args=args,
                            display_text=texts[key].format(**shown))
            break
    title = VOICE_ADDRESS.get(voice)
    if title:  # poc-13B review: no "General" in the 1775 voice.
        for dispatch in result.get('dispatches', []):
            dispatch['display_text'] = _address(dispatch['display_text'], title)
        for r in result.get('recommendations', []):
            r['display_text'] = _address(r['text'], title)
    if 'analysis' in result:
        present_analysis(result['analysis'], entry)
    return result
