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


def present_view(observation):
    result = deepcopy(observation)
    result['display_locale'] = 'en'
    result['voice_profile'] = VOICE_PROFILE
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
