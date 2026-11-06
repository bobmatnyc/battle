import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from battle import comms,engine,inference,recommendations,runtime,scenario
from battle.storage import Store
from test_formations import fixture


def advance(s,n=1):
    for _ in range(n):engine.advance(s)


def advice(s,uid='U2'):
    return next(r for r in s['recommendations'] if r['unit_id']==uid)

class RecommendationTests(unittest.TestCase):
    def test_local_advice_arrives_without_changing_mission(self):
        s=fixture();advance(s,2);r=advice(s)
        self.assertEqual(r['proposal']['stance'],'dig_in');self.assertEqual(r['status'],'delivered')
        self.assertEqual(engine.find_unit(s,'U2')['stance'],'hold');self.assertEqual(s['orders'],[])
        self.assertIn(r,engine.view(s)['recommendations'])
        self.assertTrue(any(e['kind']=='recommendation_received' for e in s['events']))

    def test_remote_recommendation_travels_before_becoming_visible(self):
        s=fixture();engine.find_unit(s,'U2')['pos']=[8,2];comms.sync(s);advance(s,2)
        r=advice(s,'U1');self.assertEqual(r['status'],'en_route')
        self.assertNotIn(r['id'],[x['id'] for x in engine.view(s)['recommendations']])
        self.assertNotIn(r['id'],[x['id'] for x in inference.observation_for(s,'union')['recommendations']])
        self.assertIn(r['id'],[x['id'] for x in engine.god_view(s)['recommendations']])
        while 'received_turn' not in r:advance(s)
        self.assertGreater(r['received_turn'],r['created_turn'])

    def test_hq_disruption_prevents_delivery(self):
        s=fixture();engine.find_unit(s,'U2')['pos']=[8,2];comms.sync(s);advance(s,2)
        r=advice(s,'U1');engine.find_unit(s,'U2')['status']='routed'
        advance(s,5)
        self.assertNotIn('received_turn',r)
        self.assertNotIn(r['id'],[x['id'] for x in engine.view(s)['recommendations']])

    def test_accept_dispatches_through_transport_not_instant_execution(self):
        s=fixture();advance(s,2);r=advice(s)
        recommendations.respond(s,'union',r['id'],'accept')
        self.assertEqual(r['status'],'accepted');self.assertEqual(s['orders'][-1]['status'],'en_route')
        self.assertEqual(engine.find_unit(s,'U2')['stance'],'hold')
        advance(s);self.assertEqual(engine.find_unit(s,'U2')['stance'],'dig_in')
        self.assertEqual(s['orders'][-1]['source'],'commander-recommendation')

    def test_repeat_accept_is_rejected_without_second_order(self):
        s=fixture();advance(s,2);r=advice(s);recommendations.respond(s,'union',r['id'],'accept')
        before=copy.deepcopy(s)
        with self.assertRaises(ValueError):recommendations.respond(s,'union',r['id'],'accept')
        self.assertEqual(s,before)

    def test_dismiss_leaves_standing_orders_and_cooldown(self):
        s=fixture();advance(s,2);r=advice(s);recommendations.respond(s,'union',r['id'],'dismiss');advance(s,5)
        self.assertEqual(engine.find_unit(s,'U2')['stance'],'hold');self.assertEqual(s['orders'],[])
        self.assertEqual(len([x for x in s['recommendations'] if x['unit_id']=='U2']),1)

    def test_expired_advice_has_no_actionable_flag_and_is_logged(self):
        s=fixture();advance(s,2);r=advice(s);advance(s,recommendations.LIFETIME)
        self.assertEqual(r['status'],'expired')
        with self.assertRaises(ValueError):recommendations.respond(s,'union',r['id'],'accept')
        self.assertTrue(any(e['kind']=='recommendation_expired' and e['recommendation_id']==r['id'] for e in s['events']))
        recommendations.respond(s,'union',r['id'],'dismiss')

    def test_new_manual_orders_supersede_advice_immediately_at_hq(self):
        s=fixture();advance(s,2);r=advice(s)
        engine.issue(s,'union',{'unit_id':'U2','stance':'hold','destination':None})
        self.assertEqual(next(x for x in engine.view(s)['recommendations'] if x['id']==r['id'])['status'],'superseded')
        with self.assertRaises(ValueError):recommendations.respond(s,'union',r['id'],'accept')

    def test_local_commander_does_not_know_undelivered_new_orders(self):
        s=fixture();engine.find_unit(s,'U2')['pos']=[8,2];comms.sync(s)
        engine.issue(s,'union',{'unit_id':'U1','stance':'rest','destination':None})
        advance(s,2)
        self.assertEqual(engine.find_unit(s,'U1')['stance'],'hold')
        self.assertEqual(advice(s,'U1')['proposal']['stance'],'dig_in')

    def test_undelivered_or_other_side_advice_cannot_be_accepted(self):
        s=fixture();engine.find_unit(s,'U2')['pos']=[8,2];comms.sync(s);advance(s,2)
        for rid in (advice(s,'U1')['id'],advice(s,'C2')['id'],'unknown'):
            before=copy.deepcopy(s)
            with self.assertRaises(ValueError):recommendations.respond(s,'union',rid,'accept')
            self.assertEqual(s,before)

    def test_recommendations_use_own_condition_and_local_contact(self):
        s=fixture();u=engine.find_unit(s,'U2')
        u['ammo']=100;self.assertEqual(recommendations.propose(s,u,[])['proposal']['stance'],'resupply')
        u.update(ammo=1600,fatigue=60);self.assertEqual(recommendations.propose(s,u,[])['proposal']['stance'],'rest')
        u.update(local_action='withdraw');r=recommendations.propose(s,u,[])
        self.assertEqual(r['proposal']['stance'],'retreat');self.assertEqual(r['proposal']['destination'],s['rally_points']['union'])
        u.update(local_action='hold',fatigue=0);s['turn']=2
        hidden=copy.deepcopy(s);engine.find_unit(hidden,'C1').update(pos=[3,3],ammo=1,morale=1)
        self.assertEqual(recommendations.propose(s,u,[]),recommendations.propose(hidden,u,[]))
        self.assertIsNone(recommendations.propose(s,u,[{'id':'C1','pos':[3,3]}]))

    def test_destroyed_or_routed_commanders_send_no_advice(self):
        s=fixture();engine.find_unit(s,'U1')['status']='routed';advance(s,2)
        self.assertFalse(any(r['unit_id']=='U1' for r in s['recommendations']))

    def test_accept_save_failure_rolls_back_order_and_response(self):
        s=fixture();advance(s,2);r=advice(s)
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'rollback.sqlite');gid=store.create(s)
            with store.connect() as db:db.execute("CREATE TRIGGER fail_advice BEFORE INSERT ON events WHEN NEW.kind='recommendation_accepted' BEGIN SELECT RAISE(ABORT,'injected'); END")
            n=runtime.apply(s,{'type':'recommendation','recommendation_id':r['id'],'response':'accept'})
            with self.assertRaises(sqlite3.IntegrityError):store.save(gid,n,s['revision'])
            self.assertEqual(store.load(gid),s)

    def test_generate_deliver_accept_and_dismiss_replay_exactly(self):
        s=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'replay.sqlite');gid=store.create(s)
            def commit(a):
                nonlocal s
                n=runtime.apply(s,a);store.save(gid,n,s['revision']);s=n
            for _ in range(4):commit({'type':'advance','decision':None})
            commit({'type':'recommendation','recommendation_id':advice(s)['id'],'response':'accept'})
            commit({'type':'recommendation','recommendation_id':advice(s,'U1')['id'],'response':'dismiss'})
            for _ in range(4):commit({'type':'advance','decision':None})
            self.assertEqual(runtime.verify_replay(store,gid)['status'],'identical')

    def test_previous_rules_reject_new_response_and_have_no_advice(self):
        s=scenario.create(rules='poc-6');advance(s,3)
        self.assertNotIn('recommendations',engine.view(s))
        with self.assertRaises(ValueError):recommendations.respond(s,'union','A1','accept')

if __name__=='__main__':unittest.main()
