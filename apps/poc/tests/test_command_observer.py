import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from battle import comms,engine,engine_v2,grid,inference,runtime,scenario
from battle.storage import Store


def fixture():
    s=scenario.create()
    for c in s['cells'].values():c.update(elevation=100,terrain='open',move_cost=100,cover=10)
    positions={'U1':[2,2],'U2':[8,2],'U3':[2,4],'C1':[20,18],'C2':[22,18],'C3':[20,20]}
    for u in s['units']:
        u['pos']=positions[u['id']]
        s['friendly_reports'][u['side']][u['id']]=dict(copy.deepcopy(u),observed_turn=0,received_turn=0)
    comms.sync(s)
    return s


class CommandTests(unittest.TestCase):
    def test_player_attaches_to_real_existing_formation(self):
        s=fixture();c=engine.view(s)['command']
        self.assertEqual(c['unit_id'],'U2');self.assertEqual(c['pos'],[8,2])
        self.assertEqual(sum(u['strength'] for u in s['units']),240)
        self.assertEqual(c['profile']['methods'],['voice','courier'])

    def test_movement_carries_headquarters_and_changes_order_origin(self):
        s=fixture();u=engine.find_unit(s,'U2')
        engine.issue(s,'union',{'unit_id':'U2','stance':'move','destination':[9,2]})
        engine.advance(s)
        self.assertEqual(u['pos'],[9,2]);self.assertEqual(s['hq']['union'],[9,2])
        self.assertEqual(engine.view(s)['command']['pos'],[9,2])
        self.assertEqual(next(u for u in engine.view(s)['units'] if u['id']=='U2')['pos'],[9,2])
        order=engine.issue(s,'union',{'unit_id':'U1','stance':'hold','destination':None})
        self.assertEqual(order['transport']['origin'],[9,2])

    def test_own_detachment_uses_local_voice(self):
        s=fixture();o=engine.issue(s,'union',{'unit_id':'U2','stance':'hold','destination':None})
        self.assertEqual(o['transport']['method'],'voice');engine.advance(s)
        self.assertEqual(engine.view(s)['orders'][0]['status'],'delivered')

    def test_courier_order_then_physical_return_ack(self):
        s=fixture();o=engine.issue(s,'union',{'unit_id':'U1','stance':'hold','destination':None})
        self.assertEqual(o['arrival_turn'],3)
        for _ in range(2):engine.advance(s)
        self.assertEqual(o['status'],'en_route')
        engine.advance(s);self.assertEqual(o['status'],'delivered')
        for _ in range(2):
            self.assertEqual(engine.view(s)['orders'][0]['status'],'awaiting_ack');engine.advance(s)
        engine.advance(s)
        self.assertEqual(engine.view(s)['orders'][0]['status'],'delivered')

    def test_rough_terrain_increases_courier_travel(self):
        a=fixture();b=copy.deepcopy(a)
        for c in b['cells'].values():c['move_cost']=170
        order={'unit_id':'U1','stance':'hold','destination':None}
        self.assertGreater(engine.issue(b,'union',order)['arrival_turn'],engine.issue(a,'union',order)['arrival_turn'])

    def test_orders_use_last_reported_recipient_position(self):
        s=fixture();engine.find_unit(s,'U1')['pos']=[4,2]
        o=engine.issue(s,'union',{'unit_id':'U1','stance':'hold','destination':None})
        self.assertEqual(o['transport']['address'],[2,2])

    def test_moving_hq_adds_forwarding_travel_for_reports(self):
        s=fixture();engine.enqueue(s,'union','Dispatch from U1',sender='U1')
        packet=s['reports'][0]['transport'];u=engine.find_unit(s,'U2');u['pos']=[10,2]
        for turn in range(1,4):s['turn']=turn;engine.deliver_reports(s)
        self.assertFalse(s['dispatches']['union'])
        self.assertEqual(packet['forwardings'],1);self.assertEqual(packet['pos'],[8,2])
        s['turn']=4;engine.deliver_reports(s)
        self.assertEqual(s['dispatches']['union'][-1]['text'],'Dispatch from U1')
        self.assertEqual(s['dispatches']['union'][-1]['observed_turn'],0)
        self.assertEqual(s['dispatches']['union'][-1]['turn'],4)

    def test_report_transport_advances_once_per_interval(self):
        s=fixture();engine.enqueue(s,'union','Message',sender='U1');s['turn']=1
        engine.deliver_reports(s);first=copy.deepcopy(s['reports'])
        engine.deliver_reports(s);self.assertEqual(first,s['reports'])

    def test_disrupted_hq_cannot_order_but_subordinates_still_fight(self):
        s=fixture();engine.find_unit(s,'U2')['status']='routed'
        engine.find_unit(s,'C1')['pos']=[4,2]
        with self.assertRaises(engine.InvalidOrder):engine.issue(s,'union',{'unit_id':'U1','stance':'hold','destination':None})
        self.assertEqual(inference.decide(s,side='union',mode='scripted')['orders'],[])
        engine.advance(s)
        self.assertTrue(any(e['kind']=='volley' and e['unit_id']=='U1' for e in s['events']))
        self.assertFalse(engine.view(s)['command']['operational'])

    def test_routed_command_unit_falls_towards_rally_point(self):
        s=fixture();u=engine.find_unit(s,'U2');u['status']='routed';u['move_credit']=300
        before=list(u['pos']);engine.advance(s)
        self.assertNotEqual(u['pos'],before);self.assertEqual(u['target'],s['rally_points']['union'])

    def test_lost_command_blocks_receipt(self):
        s=fixture();engine.enqueue(s,'union','Cannot deliver',sender='U1')
        engine.find_unit(s,'U2').update(strength=0,status='lost')
        for turn in range(1,4):s['turn']=turn;engine.deliver_reports(s)
        self.assertFalse(s['dispatches']['union'])
        self.assertTrue(any(e['kind']=='report_undeliverable' for e in s['events']))

    def test_destroyed_remote_unit_does_not_send_ghost_status_reports(self):
        s=fixture();u=engine.find_unit(s,'U1');u.update(strength=0,status='lost')
        before=copy.deepcopy(s['friendly_reports']['union']['U1'])
        engine.advance(s)
        self.assertEqual(s['friendly_reports']['union']['U1'],before)
        self.assertFalse(any(r['transport']['origin']==u['pos'] for r in s['reports']))

    def test_command_local_sighting_arrives_without_distant_report(self):
        s=fixture();engine.find_unit(s,'C1')['pos']=[10,2]
        engine.advance(s);contacts=engine.view(s)['contacts']
        self.assertTrue(contacts)
        self.assertEqual(contacts[0]['observer_id'],'U2')
        self.assertEqual(contacts[0]['observed_turn'],contacts[0]['received_turn'])
        self.assertNotIn('strength',contacts[0])

    def test_distant_sighting_not_visible_before_courier(self):
        s=fixture();engine.find_unit(s,'U2')['pos']=[14,2]
        engine.find_unit(s,'C1')['pos']=[3,2]
        engine.advance(s);self.assertFalse(engine.view(s)['contacts'])

    def test_stale_friendly_report_cannot_replace_new_position(self):
        s=fixture();u=engine.find_unit(s,'U1');old=engine.summary(u)
        engine.enqueue(s,'union',None,old,kind='friendly')
        s['friendly_reports']['union']['U1'].update(pos=[6,2],observed_turn=2)
        for turn in range(1,4):s['turn']=turn;engine.deliver_reports(s)
        self.assertEqual(s['friendly_reports']['union']['U1']['pos'],[6,2])

    def test_courier_expiry_is_logged_without_invented_receipt(self):
        s=fixture();engine.enqueue(s,'union','Expired',sender='U1')
        s['turn']=21;engine.deliver_reports(s)
        self.assertFalse(s['dispatches']['union']);self.assertFalse(s['reports'])
        self.assertTrue(any(e['kind']=='communication_expired' for e in s['events']))


class GodObserverTests(unittest.TestCase):
    def test_explicit_god_view_shows_all_sides_and_events_without_mutation(self):
        s=fixture();engine.advance(s);before=copy.deepcopy(s)
        normal=engine.view(s);god=engine.god_view(s)
        self.assertEqual(len(normal['units']),3);self.assertEqual(len(god['units']),6)
        self.assertEqual(god['events'],s['events']);self.assertEqual(god['reports'],s['reports'])
        god['units'][0]['strength']=999;god['events'].clear()
        self.assertEqual(s,before)

    def test_observing_does_not_leak_into_twin_or_enemy(self):
        s=fixture();before={side:inference.observation_for(s,side) for side in scenario.SIDES}
        engine.god_view(s)
        for side in scenario.SIDES:
            after=inference.observation_for(s,side);self.assertEqual(before[side],after)
            self.assertNotIn('events',after);self.assertNotIn('reports',after);self.assertNotIn('commands',after)
            self.assertTrue(all(u['side']==side for u in after['units']))

    def test_new_rules_replay_and_resources_with_command_movement(self):
        s=fixture()
        with tempfile.TemporaryDirectory() as temp:
            store=Store(Path(temp)/'battle.sqlite');gid=store.create(s)
            actions=[{'type':'orders','orders':[{'unit_id':'U2','stance':'move','destination':[10,2]},
                                             {'unit_id':'U1','stance':'move','destination':[4,2]}]}]
            actions += [{'type':'advance','decision':None} for _ in range(8)]
            for action in actions:
                n=runtime.apply(s,action);store.save(gid,n,s['revision']);s=n
                engine.god_view(s)
            with patch('battle.inference.request_json',side_effect=AssertionError('Unexpected model call')):
                self.assertEqual(runtime.verify_replay(store,gid)['status'],'identical')
            for u in s['units']:
                self.assertEqual(u['initial'],u['strength']+sum(e['count'] for e in s['events'] if e['kind']=='casualties' and e['unit_id']==u['id']))

    def test_legacy_orders_transitions_and_views_stay_unchanged(self):
        a=scenario.create(rules='poc-2');b=copy.deepcopy(a)
        order={'unit_id':'U1','stance':'move','destination':[0,0]}
        engine.issue(a,'union',order);engine_v2.issue(b,'union',order)
        for _ in range(4):engine.advance(a);engine_v2.advance(b)
        self.assertEqual(a,b);self.assertEqual(engine.view(a),engine_v2.view(b))
        self.assertEqual(len(engine.god_view(a)['units']),6)


if __name__=='__main__':unittest.main()
