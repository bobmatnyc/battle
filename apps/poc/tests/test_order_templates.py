import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from battle import comms,engine,engine_v4,inference,orders,runtime,scenario
from battle.storage import Store
from test_formations import fixture


def issue(s,stance,uid='U2',destination=None):
    return engine.issue(s,'union',{'unit_id':uid,'stance':stance,'destination':destination})

def supply_fixture():
    s=fixture();u=engine.find_unit(s,'U2');u.update(ammo=100,fatigue=30)
    s['supply_sites'][0].update(pos=[4,2],ammo=250)
    return s,u,s['supply_sites'][0]

class OrderTemplateTests(unittest.TestCase):
    def test_shared_catalog_is_versioned_and_restricted_for_old_games(self):
        s=fixture();ids=[t['id'] for t in engine.view(s)['order_templates']]
        self.assertEqual(ids,['hold','move','rest','retreat','resupply','recon','dig_in','hold_fire','open_fire'])
        self.assertEqual(ids,inference.observation_for(s,'union')['order_contract']['stances'])
        self.assertEqual(inference.observation_for(scenario.create(rules='poc-4'),'union')['order_contract']['stances'],['hold','move'])
        self.assertTrue(all(t['message_key'] and t['version'] for t in orders.catalog(s)))

    def test_invalid_templates_destinations_and_enemy_orders_are_atomic(self):
        for stance,destination,uid in [('attack',None,'U2'),('rest',[0,0],'U2'),('retreat',None,'U2'),('recon',[24,0],'U2'),('resupply',[1,1],'U2'),('rest',None,'C1')]:
            s=fixture();before=copy.deepcopy(s)
            with self.assertRaises(ValueError):issue(s,stance,uid,destination)
            self.assertEqual(s,before)

    def test_rest_begins_after_delivery_and_changes_only_condition(self):
        s=fixture();u=engine.find_unit(s,'U2');u['fatigue']=12;u['strength']=30
        issue(s,'rest');self.assertEqual(u['stance'],'hold')
        engine.advance(s);self.assertEqual(u['fatigue'],6);self.assertEqual(u['stance'],'rest')
        engine.advance(s);self.assertEqual(u['fatigue'],0);self.assertEqual(u['stance'],'hold')
        self.assertEqual((u['strength'],u['ammo']),(30,1600))
        self.assertEqual(u['mission_result']['status'],'completed')
        self.assertEqual(len([e for e in s['events'] if e['kind']=='unit_rested']),2)

    def test_incoming_fire_blocks_rest_and_recovery_resumes_after_clearance(self):
        s=fixture();u=engine.find_unit(s,'U2');u['fatigue']=30
        enemy=engine.find_unit(s,'C1');enemy['pos']=[5,2]
        issue(s,'rest');engine.advance(s)
        self.assertEqual(u['fatigue'],30);self.assertEqual(u['mission_result']['status'],'blocked')
        enemy['pos']=[20,18]
        for _ in range(3):engine.advance(s)
        self.assertLess(u['fatigue'],30)
        self.assertTrue(any(e['kind']=='mission_blocked' for e in s['events']))

    def test_retreat_moves_on_contact_where_move_order_would_defend(self):
        s=fixture();u=engine.find_unit(s,'U2');engine.find_unit(s,'C1')['pos']=[5,2]
        issue(s,'retreat',destination=[0,2]);engine.advance(s)
        self.assertNotEqual(u['pos'],[3,2]);self.assertEqual(u['status'],'ready')
        self.assertEqual(u['stance'],'retreat');self.assertEqual(u['local_action'],'fall_back')
        self.assertGreaterEqual(comms.grid.distance(u['pos'],[5,2]),2)
        self.assertEqual(u['target'],[0,2])

    def test_retreat_same_position_completes_and_is_not_a_rout(self):
        s=fixture();u=engine.find_unit(s,'U2');issue(s,'retreat',destination=u['pos'])
        engine.advance(s)
        self.assertEqual(u['mission_result']['status'],'completed');self.assertEqual(u['status'],'ready')

    def test_recon_arrival_retains_cautious_mission_and_does_not_grant_skill(self):
        s=fixture();u=engine.find_unit(s,'U2');issue(s,'recon',destination=[4,2]);engine.advance(s)
        self.assertEqual(u['pos'],[4,2]);self.assertEqual(u['stance'],'recon');self.assertEqual(u['recon_skill'],35)
        engine.find_unit(s,'C1')['pos']=[6,2];engine.advance(s)
        self.assertEqual(u['local_action'],'fall_back');self.assertGreater(comms.grid.distance(u['pos'],[6,2]),2)
        self.assertEqual(u['target'],[4,2])

    def test_resupply_is_rate_limited_conserved_and_exhaustible(self):
        s,u,d=supply_fixture();issue(s,'resupply');self.assertEqual(u['ammo'],100)
        engine.advance(s);self.assertEqual((u['ammo'],d['ammo']),(300,50))
        engine.advance(s);self.assertEqual((u['ammo'],d['ammo']),(350,0))
        engine.advance(s);self.assertEqual((u['ammo'],d['ammo']),(350,0))
        self.assertEqual(u['mission_result']['status'],'failed');self.assertEqual(u['stance'],'hold')
        self.assertEqual(sum(e['rounds'] for e in s['events'] if e['kind']=='ammunition_transferred'),250)

    def test_resupply_capacity_and_repeated_requests_cannot_create_rounds(self):
        s,u,d=supply_fixture();u['ammo']=1590;d['ammo']=100
        for _ in range(3):issue(s,'resupply');engine.advance(s)
        self.assertEqual((u['ammo'],d['ammo']),(1600,90))
        self.assertEqual(u['mission_result']['status'],'completed')

    def test_contact_prevents_loading_even_during_arrival_interval(self):
        s,u,d=supply_fixture();u['ammo']=1000;engine.find_unit(s,'C1')['pos']=[6,2]
        issue(s,'resupply');engine.advance(s)
        self.assertEqual(d['ammo'],250)
        self.assertFalse(any(e['kind']=='ammunition_transferred' for e in s['events']))
        self.assertLess(u['ammo'],1000)  # Self-defense still consumes ammunition.

    def test_supply_stock_is_not_a_remote_or_enemy_oracle(self):
        s,u,d=supply_fixture();d['ammo']=0
        v=engine.view(s);self.assertEqual(len(v['supply_sites']),1)
        self.assertNotIn('ammo',v['supply_sites'][0])
        self.assertNotIn('ammo',inference.observation_for(s,'union')['supply_sites'][0])
        issue(s,'resupply')  # Depletion is discovered locally, not at dispatch validation.
        self.assertEqual(s['orders'][0]['status'],'en_route')
        self.assertEqual(engine.god_view(s)['supply_sites'][0]['ammo'],0)

    def test_distant_unit_must_travel_before_loading(self):
        s,u,d=supply_fixture();d['pos']=[10,2];issue(s,'resupply')
        engine.advance(s);self.assertEqual(u['ammo'],100);self.assertEqual(d['ammo'],250)
        for _ in range(10):engine.advance(s)
        self.assertEqual(d['ammo'],0);self.assertLessEqual(comms.grid.distance(u['pos'],d['pos']),1)

    def test_completion_waits_for_report_to_headquarters(self):
        s=fixture();u=engine.find_unit(s,'U1');u['fatigue']=6
        issue(s,'rest',uid='U1');engine.advance(s)
        self.assertEqual(u['mission_result']['status'],'completed')
        self.assertNotIn('mission_result',next(x for x in engine.view(s)['units'] if x['id']=='U1'))
        engine.advance(s)
        self.assertEqual(next(x for x in engine.view(s)['units'] if x['id']=='U1')['mission_result']['status'],'completed')

    def test_new_order_supersedes_rest_through_normal_delivery(self):
        s=fixture();u=engine.find_unit(s,'U2');u['fatigue']=90
        issue(s,'rest');engine.advance(s);issue(s,'move',destination=[4,2]);engine.advance(s)
        self.assertEqual(u['pos'],[3,2])  # Tired formation must accumulate movement credit.
        self.assertEqual(u['stance'],'move');self.assertTrue(any(e['kind']=='mission_superseded' for e in s['events']))

    def test_loading_persistence_failure_rolls_back_stock_and_unit(self):
        s,u,d=supply_fixture();issue(s,'resupply')
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'rollback.sqlite');gid=store.create(s)
            with store.connect() as db:db.execute("CREATE TRIGGER fail_load BEFORE INSERT ON events WHEN NEW.kind='ammunition_transferred' BEGIN SELECT RAISE(ABORT,'injected'); END")
            n=runtime.apply(s,{'type':'advance','decision':None})
            with self.assertRaises(sqlite3.IntegrityError):store.save(gid,n,s['revision'])
            self.assertEqual(store.load(gid),s)

    def test_new_missions_replay_without_fresh_inference(self):
        s,u,d=supply_fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'orders.sqlite');gid=store.create(s)
            for stance in ('resupply','rest','retreat','recon'):
                actions=[{'type':'orders','orders':[{'unit_id':'U2','stance':stance,'destination':[4,2] if stance in ('retreat','recon') else None}]}]+[{'type':'advance','decision':None} for _ in range(3)]
                for action in actions:
                    n=runtime.apply(s,action);store.save(gid,n,s['revision']);s=n
            self.assertEqual(runtime.verify_replay(store,gid)['status'],'identical')

    def test_frozen_poc4_retains_exact_transitions_and_reorganization(self):
        a=scenario.create(rules='poc-4');b=copy.deepcopy(a)
        for state,eng in ((a,engine),(b,engine_v4)):
            eng.issue(state,'union',{'unit_id':'U2','stance':'hold','destination':None})
            for _ in range(4):eng.advance(state)
        self.assertEqual(a,b);self.assertEqual(engine.view(a),engine_v4.view(b))
        with self.assertRaises(ValueError):issue(a,'rest')

if __name__=='__main__':unittest.main()
