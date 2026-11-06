import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from battle import engine,grid,inference,runtime,scenario
from battle.storage import Store,Conflict
from battle.server import Application


def flat(s):
    for c in s['cells'].values(): c.update(elevation=100,terrain='open',move_cost=100,cover=10)
    return s

class GridTests(unittest.TestCase):
    def test_neighbors_reciprocal_and_distance(self):
        for r in range(grid.ROWS):
            for c in range(grid.COLS):
                for n in grid.neighbors([c,r]):
                    self.assertIn([c,r],grid.neighbors(n))
                    self.assertEqual(grid.distance([c,r],n),1)
    def test_path_is_contiguous_and_reaches_goal(self):
        s=scenario.create(rules='poc-2'); p=grid.path(s['cells'],[0,0],[23,20]);prev=[0,0]
        for nxt in p:
            self.assertEqual(grid.distance(prev,nxt),1);prev=nxt
        self.assertEqual(prev,[23,20])
    def test_ridge_blocks_line_of_sight(self):
        s=flat(scenario.create(rules='poc-2'));a=[3,3];b=[7,3]
        self.assertTrue(grid.visible(s['cells'],a,b))
        s['cells'][grid.key(grid.line(a,b)[2])]['elevation']=160
        self.assertFalse(grid.visible(s['cells'],a,b))
    def test_bounds_reject_boolean_and_float(self):
        for p in ([True,2],[2.0,2],[-1,2],[24,2],None,'4,4'):
            self.assertFalse(grid.valid(p))

class OrderTests(unittest.TestCase):
    def test_order_delayed_and_report_delayed_again(self):
        s=flat(scenario.create(rules='poc-2'));before=copy.deepcopy(s['units'][0]['pos'])
        o=engine.issue(s,'union',{'unit_id':'U1','stance':'move','destination':[11,10]})
        self.assertEqual(s['units'][0]['pos'],before)
        for _ in range(o['arrival_turn']):engine.advance(s)
        self.assertNotEqual(s['units'][0]['pos'],before)
        self.assertNotEqual(engine.view(s)['units'][0]['pos'],s['units'][0]['pos'])
        self.assertEqual(engine.view(s)['orders'][0]['status'],'awaiting_ack')
        engine.advance(s)
        self.assertEqual(engine.view(s)['orders'][0]['status'],'delivered')
    def test_wrong_side_order_denied(self):
        s=scenario.create(rules='poc-2')
        with self.assertRaises(engine.InvalidOrder):engine.issue(s,'union',{'unit_id':'C1','stance':'hold','destination':None})
    def test_invalid_order_has_no_effect(self):
        s=scenario.create(rules='poc-2');before=copy.deepcopy(s)
        with self.assertRaises(engine.InvalidOrder):engine.issue(s,'union',{'unit_id':'U1','stance':'move','destination':[99,0]})
        self.assertEqual(s,before)
    def test_newer_order_wins_when_older_arrives_late(self):
        s=scenario.create(rules='poc-2')
        a=engine.issue(s,'union',{'unit_id':'U1','stance':'move','destination':[0,0]})
        b=engine.issue(s,'union',{'unit_id':'U1','stance':'hold','destination':None})
        a['arrival_turn']=3;b['arrival_turn']=1
        for _ in range(3):engine.advance(s)
        self.assertEqual(a['status'],'superseded');self.assertEqual(s['units'][0]['order_version'],2)
        self.assertIsNone(s['units'][0]['target'])
    def test_collision_does_not_stack_units(self):
        s=flat(scenario.create(rules='poc-2'));s['units'][0]['pos']=[5,5];s['units'][1]['pos']=[7,5]
        for u in s['units'][:2]:u['target']=[6,5];u['move_credit']=300
        engine.advance(s)
        self.assertEqual(s['units'][0]['pos'],[5,5]);self.assertEqual(s['units'][1]['pos'],[7,5])

class CombatTests(unittest.TestCase):
    def duel(self):
        s=flat(scenario.create(rules='poc-2'));s['units']=[s['units'][0],s['units'][3]]
        s['units'][0]['pos']=[5,5];s['units'][1]['pos']=[7,5]
        for u in s['units']:u.update(morale=85,ammo=400,strength=20,initial=20)
        return s
    def test_fire_is_simultaneous(self):
        s=self.duel()
        for u in s['units']:u.update(strength=1,loss_credit=99)
        engine.advance(s)
        self.assertEqual([u['strength'] for u in s['units']],[0,0])
        self.assertEqual(s['winner'],'draw')
        self.assertEqual(len([e for e in s['events'] if e['kind']=='volley']),2)
    def test_no_ammunition_no_fire(self):
        s=self.duel()
        for u in s['units']:u['ammo']=0
        engine.advance(s)
        self.assertEqual([u['strength'] for u in s['units']],[20,20])
        self.assertFalse(any(e['kind']=='volley' for e in s['events']))
    def test_conservation_and_no_negative_resources(self):
        s=self.duel();engine.advance(s)
        for u in s['units']:
            casualties=sum(e['count'] for e in s['events'] if e['kind']=='casualties' and e['unit_id']==u['id'])
            spent=sum(e['rounds'] for e in s['events'] if e['kind']=='volley' and e['unit_id']==u['id'])
            self.assertEqual(20,u['strength']+casualties);self.assertEqual(400,u['ammo']+spent)
            self.assertGreaterEqual(u['ammo'],0)
    def test_order_independent_combat_results(self):
        a=self.duel();b=copy.deepcopy(a);b['units'].reverse()
        engine.advance(a);engine.advance(b)
        self.assertEqual({u['id']:u['strength'] for u in a['units']},{u['id']:u['strength'] for u in b['units']})
    def test_capture_requires_three_uncontested_turns(self):
        s=flat(scenario.create(rules='poc-2'))
        for i,u in enumerate(s['units']):u['pos']=[i,0] if u['side']=='union' else [11+i-3,15]
        for _ in range(2):engine.advance(s)
        self.assertEqual(s['status'],'active')
        engine.advance(s);self.assertEqual(s['winner'],'confederate')
    def test_no_orders_still_runs_autonomous_combat(self):
        s=self.duel();engine.advance(s)
        self.assertFalse(s['orders']);self.assertTrue(any(e['kind']=='volley' for e in s['events']))

class VisibilityTests(unittest.TestCase):
    def test_initial_view_contains_no_enemy_truth(self):
        s=scenario.create(rules='poc-2');v=engine.view(s)
        self.assertEqual(v['contacts'],[])
        self.assertTrue(all(u['side']=='union' for u in v['units']))
        self.assertNotIn('events',v);self.assertNotIn('decisions',v)
    def test_contacts_require_report_arrival(self):
        s=flat(scenario.create(rules='poc-2'));s['units'][0]['pos']=[5,5];s['units'][3]['pos']=[7,5]
        engine.advance(s);self.assertEqual(engine.view(s)['contacts'],[])
        engine.advance(s);self.assertTrue(engine.view(s)['contacts'])
        c=engine.view(s)['contacts'][0]
        self.assertNotIn('strength',c);self.assertNotIn('ammo',c)
        self.assertEqual(c['observed_turn'],1);self.assertEqual(c['received_turn'],2)
    def test_hidden_enemy_changes_do_not_change_agent_observation(self):
        a=scenario.create(rules='poc-2');b=copy.deepcopy(a)
        b['units'][3].update(pos=[0,0],strength=1)
        self.assertEqual(engine.view(a),engine.view(b))
    def test_contact_expires(self):
        s=scenario.create(rules='poc-2');s['contacts']['union']['C1']={'id':'C1','observed_turn':0,'pos':[2,2]}
        s['turn']=7;self.assertEqual(engine.view(s)['contacts'],[])

class AgentTests(unittest.TestCase):
    def test_timeout_falls_back_without_changing_state(self):
        s=scenario.create(rules='poc-2');before=copy.deepcopy(s)
        with patch('battle.inference.request_json',side_effect=TimeoutError):d=inference.decide(s)
        self.assertEqual(d['source'],'scripted');self.assertEqual(d['fallback_reason'],'TimeoutError')
        self.assertEqual(s,before)
    def test_illegal_model_orders_fall_back(self):
        s=scenario.create(rules='poc-2')
        with patch('battle.inference.request_json',return_value=({'orders':[{'unit_id':'U1','stance':'hold','destination':None}]},{})):
            d=inference.decide(s)
        self.assertEqual(d['source'],'scripted');self.assertTrue(all(o['unit_id'].startswith('C') for o in d['orders']))
    def test_model_cannot_set_casualties(self):
        s=scenario.create(rules='poc-2')
        with self.assertRaises(engine.InvalidOrder):inference.validated(s,'union',[{'unit_id':'U1','stance':'hold','destination':None,'casualties':50}])
    def test_duplicate_model_orders_rejected(self):
        s=scenario.create(rules='poc-2');o={'unit_id':'U1','stance':'hold','destination':None}
        with self.assertRaises(ValueError):inference.validated(s,'union',[o,o])
    def test_chat_proposals_do_not_execute(self):
        s=scenario.create(rules='poc-2');before=copy.deepcopy(s)
        with patch('battle.inference.request_json',return_value=({'text':'Hold.','orders':[{'unit_id':'U1','stance':'hold','destination':None}]},{})):
            d=inference.chat(s,'hold')
        self.assertEqual(len(d['orders']),1);self.assertEqual(s,before)

class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'battle.sqlite')
        self.s=scenario.create(rules='poc-2');self.gid=self.store.create(self.s)
    def tearDown(self):self.tmp.cleanup()
    def test_snapshot_and_event_commit(self):
        n=runtime.apply(self.s,{'type':'orders','orders':[{'unit_id':'U1','stance':'hold','destination':None}]})
        self.store.save(self.gid,n,0);self.assertEqual(self.store.load(self.gid),n)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM events').fetchone()[0],len(n['events']))
    def test_stale_revision_rejected(self):
        n=runtime.apply(self.s,{'type':'advance','decision':None});self.store.save(self.gid,n,0)
        with self.assertRaises(Conflict):self.store.save(self.gid,n,0)
        self.assertEqual(len(self.store.history(self.gid)),2)
    def test_event_failure_rolls_back_world_and_snapshot(self):
        with self.store.connect() as db:
            db.execute("CREATE TRIGGER fail_event BEFORE INSERT ON events BEGIN SELECT RAISE(ABORT,'injected'); END")
        n=runtime.apply(self.s,{'type':'advance','decision':None})
        with self.assertRaises(sqlite3.IntegrityError):self.store.save(self.gid,n,0)
        self.assertEqual(self.store.load(self.gid),self.s)
        self.assertEqual(len(self.store.history(self.gid)),1)
    def test_replay_uses_saved_decisions_without_inference(self):
        s=self.s
        for _ in range(5):
            d=inference.decide(s,mode='scripted') if s['turn']%3==0 else None
            n=runtime.apply(s,{'type':'advance','decision':d});self.store.save(self.gid,n,s['revision']);s=n
        with patch('battle.inference.request_json',side_effect=AssertionError('Replay called model')):
            self.assertEqual(runtime.verify_replay(self.store,self.gid)['status'],'identical')
    def test_chat_and_decision_commit_together(self):
        decision={'source':'scripted','text':'Hold the summit.','orders':[], 'request':'Status?','turn':0}
        n=runtime.apply(self.s,{'type':'chat','decision':decision})
        self.store.save(self.gid,n,0)
        self.assertEqual(len(self.store.messages(self.gid)),2)
        self.assertEqual(self.store.load(self.gid)['decisions'],[decision])
    def test_chat_storage_failure_rolls_back_decision(self):
        with self.store.connect() as db:
            db.execute("CREATE TRIGGER fail_message BEFORE INSERT ON messages BEGIN SELECT RAISE(ABORT,'injected'); END")
        decision={'source':'scripted','text':'Hold.','orders':[], 'request':'Status?','turn':0}
        n=runtime.apply(self.s,{'type':'chat','decision':decision})
        with self.assertRaises(sqlite3.IntegrityError):self.store.save(self.gid,n,0)
        self.assertEqual(self.store.load(self.gid),self.s)
        self.assertEqual(self.store.messages(self.gid),[])
    def test_server_rejects_stale_game(self):
        app=Application(Path(self.tmp.name)/'app.sqlite',offline=True)
        with self.assertRaises(Conflict):app.mutate('/api/advance',{'game_id':'wrong','revision':0})

if __name__=='__main__':unittest.main()
