import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from battle import comms,engine,engine_v3,formations,inference,runtime,scenario
from battle.storage import Store

def fixture():
    s=scenario.create()
    for c in s['cells'].values():
        c.update(elevation=100,terrain='open',move_cost=100,cover=10)
        for key in ('road_neighbors','building','obstacle_height'):c.pop(key,None)
    positions={'U1':[2,2],'U2':[3,2],'U3':[2,5],'C1':[20,18],'C2':[22,18],'C3':[20,20]}
    for u in s['units']:
        u['pos']=positions[u['id']]
        s['friendly_reports'][u['side']][u['id']]=dict(copy.deepcopy(u),observed_turn=0,received_turn=0)
    comms.sync(s)
    return s

SPLIT={'kind':'split','unit_id':'U1','count':20,'destination':[1,2]}

class FormationTests(unittest.TestCase):
    def test_split_delivers_then_takes_two_intervals_and_conserves_resources(self):
        s=fixture();a=engine.find_unit(s,'U1');a.update(ammo=999,initial=43,loss_credit=73)
        formations.request(s,'union',SPLIT)
        for _ in range(2):engine.advance(s);self.assertEqual(len(s['units']),6)
        engine.advance(s);b=engine.find_unit(s,'UD1')
        self.assertEqual([a['strength'],b['strength']],[20,20])
        self.assertEqual(a['ammo']+b['ammo'],999);self.assertEqual(a['initial']+b['initial'],43)
        self.assertEqual(a['loss_credit']+b['loss_credit'],73)
        self.assertEqual(b['pos'],[1,2]);self.assertEqual(s['formation_ops'][0]['status'],'completed')
        self.assertTrue(any(e['kind']=='unit_split' for e in s['events']))

    def test_split_children_preserve_training_and_do_not_duplicate_headquarters(self):
        s=fixture();formations.request(s,'union',{**SPLIT,'unit_id':'U2','destination':[4,2]})
        for _ in range(3):engine.advance(s)
        a=engine.find_unit(s,'U2');b=engine.find_unit(s,'UD1')
        for field in formations.PROFILE:self.assertEqual(a[field],b[field])
        self.assertEqual(s['commanders']['union']['unit_id'],'U2')
        self.assertEqual(sum(u['strength'] for u in s['units']),240)

    def test_unsafe_counts_rejected_without_changes(self):
        for n in (True,20.5,0,11,29,100):
            s=fixture();before=copy.deepcopy(s)
            with self.assertRaises(ValueError):formations.request(s,'union',{**SPLIT,'count':n})
            self.assertEqual(s,before)

    def test_remote_enemy_self_and_hq_partner_rejected(self):
        for instruction in (
            {**SPLIT,'unit_id':'C1'},
            {**SPLIT,'destination':[0,0]},
            {'kind':'combine','unit_id':'U1','partner_id':'U1'},
            {'kind':'combine','unit_id':'U1','partner_id':'U2'},
            {'kind':'combine','unit_id':'U2','partner_id':'U3'}):
            s=fixture();before=copy.deepcopy(s)
            with self.assertRaises(ValueError):formations.request(s,'union',instruction)
            self.assertEqual(s,before)

    def test_combine_preserves_aggregate_totals_and_retires_partner(self):
        s=fixture();a=engine.find_unit(s,'U2');b=engine.find_unit(s,'U1')
        a.update(morale=70,fatigue=25,ammo=901);b.update(morale=55,fatigue=50,ammo=777)
        formations.request(s,'union',{'kind':'combine','unit_id':'U2','partner_id':'U1'})
        for _ in range(3):engine.advance(s)
        self.assertEqual(a['strength'],80);self.assertEqual(a['ammo'],1678)
        self.assertEqual(b['status'],'merged');self.assertEqual(b['strength'],0);self.assertEqual(b['ammo'],0)
        self.assertEqual(len(s['retired_units']),1)
        self.assertLessEqual(a['morale'],58);self.assertGreaterEqual(a['fatigue'],44)
        self.assertEqual(sum(u['strength'] for u in s['units']),240)
        self.assertEqual(len(engine.god_view(s)['units']),5)
        self.assertNotIn('U1',[u['id'] for u in engine.view(s)['units']])

    def test_orders_to_retired_id_are_rejected_after_report(self):
        s=fixture();formations.request(s,'union',{'kind':'combine','unit_id':'U2','partner_id':'U1'})
        for _ in range(3):engine.advance(s)
        with self.assertRaises(engine.InvalidOrder):engine.issue(s,'union',{'unit_id':'U1','stance':'hold','destination':None})

    def test_hidden_occupancy_is_adjudicated_on_delivery_not_api_validation(self):
        s=fixture();engine.find_unit(s,'C1')['pos']=[1,2]
        formations.request(s,'union',SPLIT)
        self.assertEqual(s['formation_ops'][0]['status'],'awaiting_orders')
        engine.advance(s)
        self.assertEqual(s['formation_ops'][0]['status'],'refused');self.assertEqual(len(s['units']),6)

    def test_low_remaining_strength_refuses_without_creating_troops(self):
        s=fixture();formations.request(s,'union',SPLIT);engine.find_unit(s,'U1')['strength']=25
        for _ in range(3):engine.advance(s)
        self.assertEqual(s['formation_ops'][0]['status'],'refused')
        self.assertEqual(engine.find_unit(s,'U1')['strength'],25)

    def test_incoming_fire_interrupts_regrouping(self):
        s=fixture();formations.request(s,'union',SPLIT);engine.advance(s)
        engine.find_unit(s,'U1')['last_attacked_turn']=s['turn'];engine.advance(s)
        self.assertEqual(s['formation_ops'][0]['status'],'refused');self.assertEqual(len(s['units']),6)

    def test_newer_order_cancels_pending_formation_instruction(self):
        s=fixture();formations.request(s,'union',SPLIT)
        engine.issue(s,'union',{'unit_id':'U1','stance':'move','destination':[1,1]})
        engine.advance(s)
        self.assertEqual(s['formation_ops'][0]['status'],'refused');self.assertEqual(len(s['units']),6)

    def test_capacity_and_profile_mismatch_are_rejected(self):
        for field,value in (('strength',41),('skill',99),('weapon_class','different arms')):
            s=fixture();s['friendly_reports']['union']['U1'][field]=value
            with self.assertRaises(ValueError):formations.request(s,'union',{'kind':'combine','unit_id':'U2','partner_id':'U1'})
            self.assertFalse(s['orders'])

    def test_failure_to_persist_split_rolls_back_all_units_and_lineage(self):
        s=fixture();formations.request(s,'union',SPLIT)
        for _ in range(2):engine.advance(s)
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'rollback.sqlite');gid=store.create(s)
            with store.connect() as db:
                db.execute("CREATE TRIGGER fail_split BEFORE INSERT ON events WHEN NEW.kind='unit_split' BEGIN SELECT RAISE(ABORT,'injected'); END")
            n=runtime.apply(s,{'type':'advance','decision':None})
            with self.assertRaises(sqlite3.IntegrityError):store.save(gid,n,s['revision'])
            self.assertEqual(store.load(gid),s)
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM units WHERE game_id=?',(gid,)).fetchone()[0],6)

    def test_repeated_combine_cannot_duplicate_resources(self):
        s=fixture();request={'kind':'combine','unit_id':'U2','partner_id':'U1'}
        formations.request(s,'union',request);formations.request(s,'union',request)
        for _ in range(4):engine.advance(s)
        self.assertEqual([o['status'] for o in s['formation_ops']],['refused','completed'])
        self.assertEqual(sum(u['strength'] for u in s['units']),240)
        self.assertEqual(sum(u['ammo'] for u in s['units']),9600)

    def test_command_knowledge_waits_for_formation_report(self):
        s=fixture();formations.request(s,'union',SPLIT)
        for _ in range(3):engine.advance(s)
        self.assertEqual(engine.view(s)['formation_ops'][0]['status'],'awaiting_report')
        self.assertNotIn('UD1',[u['id'] for u in engine.view(s)['units']])
        engine.advance(s)
        self.assertEqual(engine.view(s)['formation_ops'][0]['status'],'completed')
        self.assertIn('UD1',[u['id'] for u in engine.view(s)['units']])

    def test_legacy_rules_do_not_allow_reorganization(self):
        s=scenario.create(rules='poc-3')
        with self.assertRaises(ValueError):formations.request(s,'union',SPLIT)

    def test_frozen_poc3_transitions_are_unchanged(self):
        a=scenario.create(rules='poc-3');b=copy.deepcopy(a)
        order={'unit_id':'U1','stance':'move','destination':[0,0]}
        engine.issue(a,'union',order);engine_v3.issue(b,'union',order)
        for _ in range(4):engine.advance(a);engine_v3.advance(b)
        self.assertEqual(a,b);self.assertEqual(engine.view(a),engine_v3.view(b))

    def test_replay_split_and_combine_with_receipts_and_lineage(self):
        s=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'formation.sqlite');gid=store.create(s)
            actions=[{'type':'formation','instruction':SPLIT}]+[{'type':'advance','decision':None} for _ in range(5)]
            actions += [{'type':'formation','instruction':{'kind':'combine','unit_id':'U1','partner_id':'UD1'}}]+[{'type':'advance','decision':None} for _ in range(8)]
            for action in actions:
                n=runtime.apply(s,action);store.save(gid,n,s['revision']);s=n
            self.assertEqual([o['status'] for o in s['formation_ops']],['completed','completed'])
            self.assertEqual(sum(u['strength'] for u in s['units']),240)
            self.assertEqual(runtime.verify_replay(store,gid)['status'],'identical')
            self.assertLessEqual(len(inference.decide(s,mode='scripted')['orders']),3)

if __name__=='__main__':unittest.main()
