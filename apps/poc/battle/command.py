"""poc-13 part B command rules: officers, succession and spoken-order reach.

Why: at Concord an officer's fall, and who heard an order, shaped the
exchange (docs/research/43, R3 and R4). What: pure functions of the snapshot
that ``engine`` calls. Each reads only snapshot data that part B adds
(``command_rules``, a profile ``voice_reach``), so a battle without it plays
exactly as before. Design and limits: docs/research/47.
"""
from copy import deepcopy
from . import comms,grid


def voice_reach(s,side):
    """Hexes a spoken order carries from ``side``'s command detachment; 0
    for profiles without one (only the detachment itself hears its orders)."""
    return comms.PROFILES[s['commanders'][side]['communications']].get('voice_reach',0)


def spoken(s,side,commander,recipient,known):
    """Why: a spoken order reaches only units within earshot.
    What: True when the order to ``recipient`` goes by voice: it is the
    command detachment, or headquarters' known position ``known`` lies within
    the profile's voice reach of the commander. The choice reads
    headquarters' knowledge only; ``comms.progress`` checks the true distance.
    Test: `test_order_within_voice_reach_is_spoken_and_delivered_next_interval`,
    `test_order_beyond_voice_reach_goes_by_runner_and_the_unit_keeps_its_last_order`."""
    if recipient['id']==commander['id']:return True
    reach=voice_reach(s,side)
    return bool(reach) and grid.distance(commander['pos'],known)<=reach


def officer_losses(s,u,losses,emit,enqueue):
    """Why: when an officer falls, command must pass on rather than freeze.
    What: with ``command_rules``, adds ``losses`` to ``u``'s count; each
    ``officer_step`` losses one officer falls (``officer_down``) and the next
    takes command. The last one leaves ``u`` leaderless (``unit_leaderless``):
    it keeps its order, refuses new ones and loses morale once. Each fall is
    reported to headquarters by the unit.
    Test: `test_next_officer_takes_command_and_the_unit_keeps_its_order`,
    `test_unit_with_no_officer_left_keeps_its_last_order_and_refuses_new_ones`."""
    if 'command_rules' not in s or 'officers' not in u or not losses or u.get('leaderless'):return
    u['officer_losses']+=losses
    while u['officers']>0 and u['officer_losses']>=u['officer_step']:
        u['officer_losses']-=u['officer_step'];u['officers']-=1
        emit(s,'officer_down',unit_id=u['id'],officers_left=u['officers'])
        if u['officers']:
            enqueue(s,u['side'],f'{u["id"]}: an officer is down; the next officer takes command.',kind='command',sender=u['id'])
            continue
        u['leaderless']=True;u['morale']=max(0,u['morale']-s['command_rules']['leaderless_morale'])
        emit(s,'unit_leaderless',unit_id=u['id'])
        enqueue(s,u['side'],f'{u["id"]}: no officer remains; the detachment keeps its last orders.',kind='command',sender=u['id'])


def _restaff(u):
    u.update(officer_step=max(1,u['initial']//(u['officers']+1)),officer_losses=0)
    if u['officers']:u.pop('leaderless',None)
    else:u['leaderless']=True


def split_officers(a,child,n):
    """Why: a split must not create officers. What: when ``a`` carries
    ``officers``, the detachment of ``n`` takes its share, rounded down, and
    ``a`` keeps the rest; a part with none is leaderless. Call before
    ``a['strength']`` drops. Test: `test_split_apportions_officers_and_combine_adds_them`."""
    if 'officers' not in a:return
    child['officers']=a['officers']*n//a['strength'];a['officers']-=child['officers']
    _restaff(a);_restaff(child)


def combine_officers(a,b):
    """Combining adds ``b``'s officers to ``a`` (poc-13B); see ``split_officers``."""
    if 'officers' not in a:return
    a['officers']+=b.get('officers',0);_restaff(a)


def _successor(s,side):
    units={u['id']:u for u in s['units']}
    for uid in s['command_rules']['succession'].get(side,()):
        u=units.get(uid)
        if u and u['strength']>0 and u['status'] not in ('lost','routed','merged') and not u.get('leaderless'):
            return u
    return None


def succession(s,emit,message):
    """Why: a fallen command detachment must hand command to a defined successor.
    What: with ``command_rules``, for each side whose command detachment is
    not operational (lost, routed or leaderless): opens a vacancy of
    ``succession_delay`` intervals (``command_vacant``); when it ends, the
    first operational unit of the side's ``succession`` list takes command
    (``command_succeeded``) and reports in transit to the old detachment are
    re-addressed to it. With no such unit, ``command_lost``: the side keeps
    no working command and its units continue under standing orders.
    Test: `test_side_command_passes_to_the_named_successor_after_the_delay`,
    `test_side_with_no_successor_falls_back_to_standing_orders`."""
    if 'command_rules' not in s:return
    for side in s['commanders']:
        vacancy=s['command_vacancy'].get(side)
        if comms.operational(s,side):
            s['command_vacancy'].pop(side,None);continue
        old=s['commanders'][side]['unit_id']
        if vacancy is None:
            vacancy=s['command_vacancy'][side]={'unit_id':old,'until_turn':s['turn']+s['command_rules']['succession_delay']}
            emit(s,'command_vacant',side=side,unit_id=old,until_turn=vacancy['until_turn'])
        if vacancy.get('lost') or s['turn']<vacancy['until_turn']:continue
        heir=_successor(s,side)
        if heir is None:
            vacancy['lost']=True;emit(s,'command_lost',side=side,unit_id=old);continue
        s['commanders'][side]['unit_id']=heir['id'];s['hq'][side]=list(heir['pos'])
        s['command_vacancy'].pop(side,None)
        for report in s['reports']:
            t=report['transport']
            if report['side']==side and t['recipient_id']==old and t['status']=='en_route':
                t.update(recipient_id=heir['id'],address=list(heir['pos']),method='courier',credit=0,forwardings=t['forwardings']+1)
        emit(s,'command_succeeded',side=side,from_unit=old,to_unit=heir['id'])
        message(s,side,f'Command passes to {heir["id"]}; orders now go out from its position.',kind='command')


def relay(s,packet,target,emit):
    """Why: a unit that leaves earshot before a spoken order reaches it must
    still get the word, later. What: for a voice packet with a ``speaker_id``
    (part B only), True when ``target`` is beyond the reach of the speaker's
    detachment; the packet then becomes a runner from the speaker's position
    (``voice_out_of_reach``). Packets without ``speaker_id`` are untouched.
    Test: `test_unit_out_of_earshot_at_delivery_gets_the_word_by_runner`."""
    if packet['method']!='voice' or 'speaker_id' not in packet or target is None:return False
    speaker=next((u for u in s['units'] if u['id']==packet['speaker_id']),None)
    origin=speaker['pos'] if speaker else packet['pos']
    if speaker and speaker['strength']>0 and grid.distance(origin,target['pos'])<=packet['voice_reach']:return False
    packet.update(method='courier',pos=list(origin),address=list(target['pos']),credit=0)
    emit(s,'voice_out_of_reach',packet=deepcopy(packet))
    return True
