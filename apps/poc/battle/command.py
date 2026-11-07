"""poc-13 part B command rules: officers, succession and spoken-order reach.

Why: at Concord an officer's fall, and who heard an order, shaped the
exchange (docs/research/43, R3 and R4). What: pure functions of the snapshot
that ``engine`` calls. Each reads only snapshot data that part B adds
(``command_rules``, a profile ``voice_reach``, a ``fire_rules.release_by``
of ``command``), so a battle without it plays exactly as before. Design and
limits: docs/research/47; command fire release: docs/research/50.
"""
from copy import deepcopy
from . import comms,grid


def voice_reach(s,side):
    """Hexes a spoken order carries from ``side``'s command detachment; 0
    for profiles without one (only the detachment itself hears its orders).
    docs/research/59: a reach the entry declared, stored with the commander, wins."""
    c=s['commanders'][side]
    return c['voice_reach'] if 'voice_reach' in c else comms.PROFILES[c['communications']].get('voice_reach',0)


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


def radio_range(s,side):
    """Hexes ``side``'s radio reaches from its command detachment; 0 for
    profiles without radio (docs/research/53: only ``wwii-1944-radio-v1``)."""
    return comms.PROFILES[s['commanders'][side]['communications']].get('radio_range',0)


def radioed(s,side,commander,pos):
    """Why: a 1944 company commander reaches platoons beyond earshot by radio.
    What: True when the profile has a radio and ``pos`` (headquarters' known
    position of the recipient, or a reporting unit's own) lies within its
    range of ``commander``. ``comms.progress`` checks the true distance.
    Test: `test_order_within_radio_range_goes_by_radio_and_arrives_next_interval`,
    `test_reports_from_units_within_radio_range_travel_by_radio`."""
    reach=radio_range(s,side)
    return bool(reach) and grid.distance(commander['pos'],pos)<=reach


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
    `test_side_with_no_successor_falls_back_to_standing_orders`,
    `test_both_commands_falling_in_one_interval_replay_identically`,
    `test_reports_on_their_way_to_the_fallen_command_go_to_the_successor`."""
    if 'command_rules' not in s:return
    # poc-13B review: scenario side order, never dict-key order, which a Store
    # load sorts; otherwise two vacancies in one interval replay out of order.
    for side in (x['id'] for x in s['sides']):
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
    docs/research/53: a radio packet beyond ``radio_range`` of its sender goes
    on by runner in the same way (``radio_out_of_range``).
    Test: `test_unit_out_of_earshot_at_delivery_gets_the_word_by_runner`,
    `test_unit_out_of_radio_range_at_delivery_gets_the_word_by_runner`."""
    if packet['method'] not in ('voice','radio') or 'speaker_id' not in packet or target is None:return False
    radio=packet['method']=='radio'
    speaker=next((u for u in s['units'] if u['id']==packet['speaker_id']),None)
    origin=speaker['pos'] if speaker else packet['pos']
    reach=packet['radio_range'] if radio else packet['voice_reach']
    if speaker and speaker['strength']>0 and grid.distance(origin,target['pos'])<=reach:return False
    packet.update(method='courier',pos=list(origin),address=list(target['pos']),credit=0)
    emit(s,'radio_out_of_range' if radio else 'voice_out_of_reach',packet=deepcopy(packet))
    return True


def release(s,triggered,emit,enqueue,message,check,previous=False):
    """Why: a scenario may delegate to a side's command the conditional intent
    "open fire once fired upon" (at Concord, standing for Buttrick's order,
    S47; docs/research/50). It is an order headquarters gives on what it
    knows, not an automatic attribution. What: under ``fire_rules.release_by``
    ``command``, for every side (delegation is scenario-wide), ``triggered``
    are the hold-fire units meeting the unchanged release condition, in the
    previous interval (``previous``) or this one. The chain is: losses, the
    command perceives them, speaks, the order is delivered, the posture is
    set, the unit fires. The operational command gives a spoken ``open_fire``
    order, sent and delivered this interval (an authored timing below the
    decision cadence), to each triggered unit (``release_scope`` ``hit``)
    or to every hold-fire unit (``earshot``) that it may order: see
    ``_may_release``. Returns the ids it opened; none under ``unit``. Every
    unit it does not open keeps its own release (Barrett's rule).
    Test: `test_hit_scope_releases_only_the_unit_that_meets_the_release_condition`,
    `test_earshot_scope_releases_the_unit_and_every_hold_fire_unit_in_voice_reach`,
    `test_unit_out_of_voice_reach_keeps_its_own_release`,
    `test_newer_voice_hold_fire_delivered_after_the_losses_is_not_overridden`,
    `test_pending_runner_hold_fire_is_not_overridden_or_superseded`,
    `test_recipient_is_chosen_by_the_position_headquarters_knows`,
    `test_release_meets_the_refusals_of_a_normal_order`."""
    if s['fire_rules'].get('release_by','unit')!='command':return set()
    opened=set()
    earshot=s['fire_rules'].get('release_scope','hit')=='earshot'
    # The losses the command acts on: last interval's fired-upon event, or this interval's, still to come.
    kind='unit_under_fire' if s['fire_rules']['warning_shots_release'] else 'casualties'
    since={u['id']:(max(e['seq'] for e in s['events'] if e['turn']==s['turn']-1 and e['kind']==kind
                        and e.get('unit_id')==u['id']) if previous else len(s['events'])+1) for u in triggered}
    for side in (x['id'] for x in s['sides']):
        if not comms.operational(s,side):continue
        commander=comms.command_unit(s,side)
        heard=[u for u in triggered if u['side']==side and _may_release(s,side,commander,u,since[u['id']],check)]
        if not heard:continue
        first=min(since[u['id']] for u in heard)
        targets=heard if not earshot else [u for u in sorted(s['units'],key=lambda x:x['id'])
                                           if u['side']==side and _may_release(s,side,commander,u,first,check)]
        for u in sorted(targets,key=lambda x:x['id']):
            _spoken_open_fire(s,side,commander,u,voice_reach(s,side),emit,enqueue,message)
            opened.add(u['id'])
    return opened


def _may_release(s,side,commander,u,since,check):
    """Whether the command may give ``u`` the release now: a hold-fire unit
    truly able to take it (as delivery checks) that headquarters may order
    (``check``, ``engine.validate_order``, except for the command unit,
    whose own state headquarters knows), within voice reach of the
    commander both as headquarters knows its position (``spoken``) and in
    fact, and with no ``hold_fire`` to it pending or delivered after the
    losses at event ``since``: the newer hold_fire wins."""
    if u.get('fire_posture')!='hold_fire' or u['strength']<=0 or u['status'] in ('routed','lost','merged') or u.get('leaderless'):
        return False
    reach=voice_reach(s,side)
    if u['id']!=commander['id']:
        try:check(s,side,{'unit_id':u['id'],'destination':None,'stance':'open_fire'})
        except Exception:return False  # engine.InvalidOrder; command cannot import engine.
        known=s['friendly_reports'][side][u['id']]['pos']
        if not spoken(s,side,commander,u,known) or grid.distance(commander['pos'],u['pos'])>reach:return False
    delivered={e['order_id']:e['seq'] for e in s['events'] if e['kind']=='order_delivered'}
    return not any(o['unit_id']==u['id'] and o['stance']=='hold_fire'
                   and (o['status']=='en_route' or (o['status']=='delivered' and delivered.get(o['id'],0)>since))
                   for o in s['orders'])


def _spoken_open_fire(s,side,commander,u,reach,emit,enqueue,message):
    """One ``open_fire`` order from ``commander`` to ``u``, given and taken
    this interval; recorded and acknowledged as ``engine.issue`` orders are."""
    version=max([o['version'] for o in s['orders'] if o['unit_id']==u['id']]+[u['order_version']])+1
    oid=f'O{len(s["orders"])+1}'
    packet=comms.envelope(s,commander['pos'],u['id'],u['pos'],'voice')
    packet.update(id=oid,pos=list(u['pos']),status='arrived',ready_turn=s['turn'],
                  last_progress_turn=s['turn'],expected_turn=s['turn'])
    if u['id']!=commander['id']:packet.update(speaker_id=commander['id'],voice_reach=reach)
    s['orders'].append({'id':oid,'side':side,'unit_id':u['id'],'destination':None,'stance':'open_fire',
                        'source':'command_release','version':version,'sent_turn':s['turn'],
                        'arrival_turn':s['turn'],'status':'delivered','transport':packet})
    emit(s,'order_sent',order_id=oid,side=side,unit_id=u['id'],destination=None,version=version,
         arrival_turn=s['turn'],transport=deepcopy(packet))
    u.update(fire_posture='open_fire',fire_posture_version=version)
    emit(s,'fire_posture_set',unit_id=u['id'],order_id=oid,fire_posture='open_fire')
    emit(s,'order_delivered',order_id=oid,unit_id=u['id'],version=version)
    message(s,side,f'{u["id"]}: open_fire order given by voice under fire.',kind='order')
    enqueue(s,side,f'{u["id"]}: order {oid} delivered.',data={'order_id':oid,'status':'delivered'},
            kind='ack',sender=u['id'])
