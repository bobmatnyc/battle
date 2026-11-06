import copy
import sqlite3
import tempfile
import unittest
from pathlib import Path
from battle import analysis,comms,engine,formations,runtime,scenario,standing,tactics_v8
from battle.storage import Store
from test_formations import fixture


def send(s,uid='U2',profile='cautious'):
    return standing.issue(s,'union',{'unit_id':uid,'profile_id':profile})

def step(s,n=1):
    for _ in range(n):engine.advance(s)

class StandingTests(unittest.TestCase):
    def test_prebattle_dispatch_waits_for_clock_and_preserves_mission(self):
        s=fixture();u=engine.find_unit(s,'U2')
        engine.issue(s,'union',{'unit_id':'U2','stance':'move','destination':[12,2]})
        o=send(s);self.assertEqual(u['standing_profile'],'balanced');self.assertEqual(s['turn'],0)
        step(s)
        self.assertEqual(u['standing_profile'],'cautious');self.assertEqual(u['target'],[12,2]);self.assertEqual(u['stance'],'move')
        self.assertEqual(o['status'],'delivered');self.assertEqual(u['order_version'],1)

    def test_remote_delivery_and_receipt_are_separate(self):
        s=fixture();engine.find_unit(s,'U1')['pos']=[12,2]
        s['friendly_reports']['union']['U1']['pos']=[12,2]
        o=send(s,'U1');step(s)
        self.assertEqual(engine.find_unit(s,'U1')['standing_profile'],'balanced')
        while o['status']=='en_route':step(s)
        self.assertEqual(engine.find_unit(s,'U1')['standing_profile'],'cautious')
        self.assertEqual(standing.visible(s,'union')[0]['status'],'awaiting_ack')
        while standing.visible(s,'union')[0]['status']=='awaiting_ack':step(s)
        self.assertEqual(standing.visible(s,'union')[0]['status'],'delivered')

    def test_policy_versions_do_not_cancel_mission_versions(self):
        s=fixture();send(s,profile='firm');send(s,profile='screen')
        engine.issue(s,'union',{'unit_id':'U2','stance':'dig_in','destination':None});step(s)
        u=engine.find_unit(s,'U2');self.assertEqual((u['standing_profile'],u['standing_version']),('screen',2))
        self.assertEqual((u['stance'],u['order_version']),('dig_in',1))
        engine.issue(s,'union',{'unit_id':'U2','stance':'rest','destination':None});step(s)
        self.assertEqual(u['standing_profile'],'screen')

    def test_late_old_policy_cannot_overwrite_newer_delivery(self):
        s=fixture();old=send(s,profile='cautious');new=send(s,profile='firm')
        old['transport']['ready_turn']=3;step(s,3)
        self.assertEqual(engine.find_unit(s,'U2')['standing_profile'],'firm');self.assertEqual(old['status'],'superseded')

    def test_contact_doctrines_change_judgment_but_never_prevent_rout(self):
        s=fixture();u=engine.find_unit(s,'U1');u.update(morale=50)
        contacts=[{'id':'C1','pos':[5,2],'strength_range':[30,50],'quality':60}]
        u['standing_profile']='cautious';self.assertEqual(tactics_v8.decide(s,u,contacts)['action'],'withdraw')
        u['standing_profile']='firm';self.assertEqual(tactics_v8.decide(s,u,contacts)['action'],'defend')
        u['status']='routed';self.assertEqual(tactics_v8.decide(s,u,contacts)['action'],'route')

    def test_screen_fire_range_is_adjudicated_by_engine(self):
        s=fixture();u=engine.find_unit(s,'U1');u['standing_profile']='screen'
        engine.find_unit(s,'C1')['pos']=[6,2]
        step(s)
        self.assertFalse(any(e['kind']=='volley' and e['unit_id']=='U1' for e in s['events']))
        # Balanced doctrine engages the same visible target.
        s=fixture();engine.find_unit(s,'C1')['pos']=[6,2];step(s)
        self.assertTrue(any(e['kind']=='volley' and e['unit_id']=='U1' for e in s['events']))

    def test_validation_and_disrupted_command(self):
        s=fixture()
        for instruction in ({'unit_id':'C1','profile_id':'firm'},{'unit_id':'U2','profile_id':'invulnerable'},{'unit_id':'U2','profile_id':'firm','morale':100}):
            before=copy.deepcopy(s)
            with self.assertRaises(ValueError):standing.issue(s,'union',instruction)
            self.assertEqual(s,before)
        engine.find_unit(s,'U2')['status']='routed'
        with self.assertRaises(ValueError):send(s)

    def test_refusal_uses_condition_at_arrival(self):
        s=fixture();o=send(s,'U1');engine.find_unit(s,'U1')['status']='routed';step(s)
        self.assertEqual(o['status'],'refused');self.assertEqual(engine.find_unit(s,'U1')['standing_profile'],'balanced')

    def test_both_sides_can_use_same_doctrine_contract(self):
        s=fixture();standing.issue(s,'confederate',{'unit_id':'C2','profile_id':'firm'});step(s)
        self.assertEqual(engine.find_unit(s,'C2')['standing_profile'],'firm')
        self.assertEqual(standing.visible(s,'union'),[])

    def test_split_inherits_doctrine_combine_preserves_survivor(self):
        s=fixture();send(s,profile='firm');step(s)
        formations.request(s,'union',{'kind':'split','unit_id':'U2','count':20,'destination':[4,2]});step(s,3)
        child=engine.find_unit(s,'UD1');self.assertEqual((child['standing_profile'],child['standing_version']),('firm',0))
        send(s,'UD1','cautious');step(s,2)
        formations.request(s,'union',{'kind':'combine','unit_id':'U2','partner_id':'UD1'});step(s,3)
        self.assertEqual(engine.find_unit(s,'U2')['standing_profile'],'firm')
        self.assertEqual(child['status'],'merged')

    def test_save_failure_rolls_back_and_replay_is_exact(self):
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'standing.sqlite');s=fixture();gid=store.create(s)
            action={'type':'standing','instruction':{'unit_id':'U2','profile_id':'firm'}}
            with store.connect() as db:db.execute("CREATE TRIGGER fail_standing BEFORE INSERT ON events WHEN NEW.kind='standing_order_sent' BEGIN SELECT RAISE(ABORT,'injected'); END")
            updated=runtime.apply(s,action)
            with self.assertRaises(sqlite3.IntegrityError):store.save(gid,updated,s['revision'])
            self.assertEqual(store.load(gid),s)
            with store.connect() as db:db.execute('DROP TRIGGER fail_standing')
            for a in [action]+[{'type':'advance','decision':None}]*4:
                n=runtime.apply(s,a);store.save(gid,n,s['revision']);s=n
            self.assertEqual(runtime.verify_replay(store,gid)['status'],'identical')

    def test_seventh_edition_remains_frozen(self):
        from battle import engine_v7
        s=scenario.create('poc-7');expected=copy.deepcopy(s)
        step(s,4)
        for _ in range(4):engine_v7.advance(expected)
        self.assertEqual(s,expected)
        self.assertNotIn('standing_orders',s)
        with self.assertRaises(ValueError):send(s)

class AssessmentTests(unittest.TestCase):
    def test_prebattle_assessment_read_only_and_recommendations(self):
        s=fixture();before=copy.deepcopy(s);a=analysis.assess(engine.view(s))
        self.assertEqual(s,before);self.assertEqual(a['turn'],0);self.assertEqual(a['summary']['reported_strength'],120)
        self.assertEqual(next(u for u in a['units'] if u['id']=='U3')['recommendation']['profile_id'],'screen')
        u=engine.find_unit(s,'U2');u['fatigue']=65
        a=analysis.assess(engine.view(s));self.assertEqual(next(u for u in a['units'] if u['id']=='U2')['recommendation']['profile_id'],'cautious')

    def test_analysis_cannot_see_undelivered_friendly_or_enemy_truth(self):
        s=fixture();before=analysis.assess(engine.view(s))
        engine.find_unit(s,'U1').update(strength=1,ammo=0,fatigue=100)
        engine.find_unit(s,'C1').update(strength=1,pos=[3,3],ammo=0)
        self.assertEqual(before,analysis.assess(engine.view(s)))
        with self.assertRaises(ValueError):analysis.assess(engine.god_view(s))

    def test_report_age_and_pending_doctrine_are_explicit(self):
        s=fixture();send(s,'U1');s['turn']=3
        a=analysis.assess(engine.view(s));u=next(u for u in a['units'] if u['id']=='U1')
        self.assertEqual(u['age_seconds'],90);self.assertEqual(u['standing_profile'],'balanced')
        self.assertEqual(u['pending_standing'][0]['status'],'awaiting_ack')
        self.assertIn('90 seconds',u['concerns'][-1])
        self.assertEqual(next(u for u in a['units'] if u['id']=='U2')['age_seconds'],0)

    def test_legacy_and_completed_battles_can_be_assessed(self):
        for version in ('poc-1','poc-3','poc-7','poc-8'):
            s=scenario.create(version);s['status']='complete'
            a=analysis.assess(engine.view(s));self.assertEqual(a['summary']['reported_strength'],120)

if __name__=='__main__':unittest.main()
