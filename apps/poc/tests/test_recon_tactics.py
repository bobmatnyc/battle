"""Tiny observation/control fixtures, independent of model responses and historical calibration."""
import copy
import tempfile
import unittest
from pathlib import Path
from battle import engine,grid,recon,tactics,scenario,runtime
from battle.storage import Store


def fixture():
    s=scenario.create(rules='poc-2');s['units']=[s['units'][0],s['units'][3]]
    s['units'][0]['pos']=[5,5];s['units'][1]['pos']=[7,5]
    for c in s['cells'].values():c.update(elevation=100,terrain='open',cover=10,move_cost=100)
    return s

class ReconTests(unittest.TestCase):
    def test_observations_narrow_ranges_and_identify_composition(self):
        s=fixture();samples=[]
        for t in range(1,13):
            s['turn']=t;samples.append(recon.scan(s)['U1'][0])
        widths=[c['strength_range'][1]-c['strength_range'][0] for c in samples]
        self.assertLess(widths[-1],widths[0])
        self.assertEqual(samples[0]['composition']['type'],'unidentified troops')
        self.assertEqual(samples[-1]['composition']['type'],'infantry')
        self.assertTrue(all(c['strength_range'][0]<=40<=c['strength_range'][1] for c in samples))
        self.assertTrue(all(c['strength_range'][0]<c['strength_range'][1] for c in samples))
    def test_scout_and_spy_better_at_same_exposure(self):
        estimates=[]
        for role in ('line','scout','spy'):
            s=fixture();s['units'][0].update(recon_role=role,recon_skill=recon.PROFILES[role]);s['turn']=1
            estimates.append(recon.scan(s)['U1'][0])
        self.assertLess(estimates[0]['quality'],estimates[1]['quality'])
        self.assertLess(estimates[1]['quality'],estimates[2]['quality'])
        self.assertLess(estimates[1]['strength_range'][1]-estimates[1]['strength_range'][0],estimates[0]['strength_range'][1]-estimates[0]['strength_range'][0])
        self.assertEqual(estimates[2]['report_delay'],3)
    def test_no_extra_exposure_for_repeated_scan_or_hidden_contact(self):
        s=fixture();s['turn']=1;a=recon.scan(s)['U1'][0];b=recon.scan(s)['U1'][0]
        self.assertEqual(a,b)
        s['units'][1]['pos']=[23,20];s['turn']=2
        self.assertEqual(recon.scan(s)['U1'],[])
        s['turn']=6;s['units'][1]['pos']=[7,5]
        self.assertEqual(recon.scan(s)['U1'][0]['exposure_intervals'],1)
    def test_distance_cover_and_suppression_reduce_quality(self):
        s=fixture();s['turn']=1;base=recon.scan(s)['U1'][0]['quality']
        s['units'][0]['suppression']=70
        self.assertLess(recon.scan(s)['U1'][0]['quality'],base)
        s['units'][0]['suppression']=0;s['units'][1]['pos']=[11,5]
        for t in range(2,15):s['turn']=t;c=recon.scan(s)['U1'][0]
        self.assertLessEqual(c['quality'],45)
        self.assertEqual(c['composition']['weapons'],'not established')
    def test_spy_asset_needs_position_and_delivery_without_suppressing_fast_warning(self):
        s=fixture();s['turn']=1;s['intel_assets']=[{'id':'I1','side':'union','pos':[5,5],'status':'observing','recon_role':'spy','recon_skill':95,'report_delay':3}]
        reports=[c for side,c in recon.reports(s,recon.scan(s)) if side=='union']
        self.assertEqual(sorted(c['report_delay'] for c in reports),[1,3])
        for c in reports:engine.enqueue(s,'union',None,c,kind='contact',delay=c['report_delay'])
        self.assertEqual(engine.view(s)['contacts'],[])
        s['turn']=2;engine.deliver_reports(s)
        self.assertEqual(engine.view(s)['contacts'][0]['observer_role'],'line')
        s['turn']=4;engine.deliver_reports(s)
        self.assertEqual(engine.view(s)['contacts'][0]['observer_role'],'spy')
        s['intel_assets'][0]['pos']=[23,20]
        self.assertEqual(recon.scan(s)['I1'],[])
    def test_older_spy_report_cannot_replace_newer_contact(self):
        s=fixture();s['turn']=1;old=recon.scan(s)['U1'][0]
        engine.enqueue(s,'union',None,old,kind='contact',delay=3)
        s['turn']=2;s['units'][1]['pos']=[8,5];new=recon.scan(s)['U1'][0]
        engine.enqueue(s,'union',None,new,kind='contact',delay=1)
        s['turn']=3;engine.deliver_reports(s);s['turn']=4;engine.deliver_reports(s)
        self.assertEqual(s['contacts']['union']['C1']['pos'],[8,5])
        self.assertEqual(s['contacts']['union']['C1']['observed_turn'],2)
    def test_slow_spy_enriches_identification_without_replacing_newer_strength(self):
        s=fixture();s['turn']=1;spy=recon.scan(s)['U1'][0]
        spy.update(quality=90,observer_role='spy',composition={'type':'infantry','weapons':'rifled muskets'})
        engine.enqueue(s,'union',None,spy,kind='contact',delay=3)
        s['turn']=2;s['units'][1]['pos']=[8,5];line=recon.scan(s)['U1'][0]
        engine.enqueue(s,'union',None,line,kind='contact',delay=1)
        s['turn']=3;engine.deliver_reports(s);s['turn']=4;engine.deliver_reports(s)
        contact=s['contacts']['union']['C1']
        self.assertEqual(contact['pos'],[8,5]);self.assertEqual(contact['strength_range'],line['strength_range'])
        self.assertEqual(contact['composition']['weapons'],'rifled muskets')
        self.assertEqual(contact['identification']['type']['observer_role'],'spy')
        self.assertEqual(contact['identification']['type']['observed_turn'],1)
    def test_poorer_sighting_retains_recent_identification(self):
        s=fixture();s['turn']=1;contact=recon.scan(s)['U1'][0]
        good=copy.deepcopy(contact);good.update(quality=60,composition={'type':'infantry','weapons':'long arms'})
        first,_=recon.merge_contact(None,good,1,2)
        second,_=recon.merge_contact(first,contact,2,3)
        self.assertEqual(second['composition']['type'],'infantry')
        self.assertEqual(second['strength_range'],contact['strength_range'])
        expired,_=recon.merge_contact(second,contact,9,10)
        self.assertEqual(expired['composition']['type'],'unidentified troops')
    def test_poorer_followup_reports_do_not_repeat_identification_loss(self):
        s=fixture();s['units'][1]['pos']=[11,5]
        good=recon.scan(s)['U1'][0];good.update(quality=80,confidence='high',composition={'type':'infantry','weapons':'rifled muskets'})
        known,_=recon.merge_contact(None,good,0,0);s['contacts']['union']['C1']=known
        for _ in range(3):engine.advance(s)
        texts=[d for d in s['dispatches']['union'] if d['kind']=='contact']+[r for r in s['reports'] if r['side']=='union' and r['kind']=='contact' and r['text']]
        self.assertEqual(len(texts),1)
        self.assertEqual(s['contacts']['union']['C1']['composition']['type'],'infantry')
    def test_no_enemy_inventory_exposed_in_contact(self):
        s=fixture();engine.advance(s);engine.advance(s)
        for c in engine.view(s)['contacts']:
            for key in ('strength','ammo','morale','skill','name','target'):self.assertNotIn(key,c)
            self.assertIn('strength_range',c)
    def test_sight_line_leaving_the_grid_at_an_edge_column_is_skipped(self):
        # Architect ruling 2026-11-07, option (c): off-grid points are open.
        s=fixture();cells=s['cells']
        cols={int(k.split(',')[0]) for k in cells};rows={int(k.split(',')[1]) for k in cells}
        for col in (min(cols),max(cols)):
            pairs=[([col,r1],[col,r2]) for r1 in rows for r2 in rows
                   if 1<grid.distance([col,r1],[col,r2])<=7
                   and any(grid.key(p) not in cells for p in grid.line([col,r1],[col,r2]))]
            self.assertTrue(pairs,f'no sight line leaves the grid at column {col}')
            for a,b in pairs:
                with self.subTest(col=col,a=a,b=b):
                    self.assertIs(grid.visible(cells,a,b),True)
                    self.assertTrue(recon.sees(s,{'pos':a},b))

class StandingPolicyTests(unittest.TestCase):
    def test_no_orders_defends_and_returns_fire(self):
        s=fixture();engine.advance(s)
        self.assertEqual(s['units'][0]['local_action'],'defend')
        self.assertTrue(any(e['kind']=='volley' and e['unit_id']=='U1' for e in s['events']))
        self.assertFalse(s['orders'])
        self.assertFalse(any(d['kind']=='reaction' for d in engine.view(s)['dispatches']))
        engine.advance(s)
        self.assertTrue(any(d['kind']=='reaction' for d in engine.view(s)['dispatches']))
    def test_low_ammunition_withdraws_without_waiting_for_rout(self):
        s=fixture();u=s['units'][0];u['ammo']=10;before=copy.deepcopy(u['pos']);engine.advance(s)
        self.assertEqual(u['local_action'],'withdraw');self.assertEqual(u['status'],'ready')
        self.assertGreater(grid.distance(u['pos'],s['units'][1]['pos']),grid.distance(before,s['units'][1]['pos']))
        self.assertTrue(any(e['kind']=='local_decision' and e['action']=='withdraw' for e in s['events']))
    def test_better_cover_preserves_mission(self):
        s=fixture();u=s['units'][0];u['target']=[12,5];u['stance']='move'
        s['cells']['4,5'].update(cover=46)
        engine.advance(s)
        self.assertEqual(u['local_action'],'take_cover');self.assertEqual(u['pos'],[4,5]);self.assertEqual(u['target'],[12,5])
    def test_no_targetable_contact_does_not_chase(self):
        s=fixture();s['units'][1]['pos']=[11,5];before=copy.deepcopy(s['units'][0]['pos']);engine.advance(s)
        self.assertEqual(s['units'][0]['local_action'],'observe');self.assertEqual(s['units'][0]['pos'],before)
    def test_hidden_enemy_changes_do_not_change_local_decision(self):
        a=fixture();a['units'][1]['pos']=[23,20];b=copy.deepcopy(a);b['units'][1].update(strength=400,morale=1,ammo=100000)
        first=tactics.decide(a,a['units'][0],recon.scan(a)['U1']);second=tactics.decide(b,b['units'][0],recon.scan(b)['U1'])
        self.assertEqual(first,second)
    def test_under_fire_without_located_enemy_does_not_invent_contact(self):
        s=fixture();u=s['units'][0];u.update(ammo=0,last_attacked_turn=0)
        s['turn']=1;s['units'][1]['pos']=[23,20]
        d=tactics.decide(s,u,[])
        self.assertEqual(d['action'],'withdraw');self.assertEqual(d['contacts'],[])
    def test_blocked_withdrawal_does_not_stack(self):
        s=fixture();u=s['units'][0];u['ammo']=1
        for i,p in enumerate(grid.neighbors(u['pos'])):
            if p==s['units'][1]['pos']:continue
            ally=scenario.unit('A'+str(i),'union','fixture',p);s['units'].append(ally)
        before=copy.deepcopy(u['pos']);engine.advance(s)
        self.assertEqual(u['local_action'],'withdraw');self.assertEqual(u['pos'],before)
    def test_withdrawal_cooldown_then_resumes_mission(self):
        s=fixture();u=s['units'][0];u.update(local_action='withdraw',withdraw_until=4,target=[10,0])
        s['units'][1]['pos']=[23,20];s['turn']=2
        self.assertEqual(tactics.decide(s,u,[])['action'],'withdraw')
        s['turn']=4
        self.assertEqual(tactics.decide(s,u,[])['action'],'continue')
        self.assertEqual(u['target'],[10,0])
    def test_enemy_ammo_and_morale_are_not_inputs_to_local_policy(self):
        a=fixture();b=copy.deepcopy(a);b['units'][1].update(ammo=0,morale=0)
        self.assertEqual(tactics.decide(a,a['units'][0],recon.scan(a)['U1']),tactics.decide(b,b['units'][0],recon.scan(b)['U1']))
    def test_legacy_rules_keep_original_transitions(self):
        from battle import engine_v1
        a=fixture();a['rules']='poc-1';b=copy.deepcopy(a)
        engine.advance(a);engine_v1.advance(b)
        self.assertEqual(a,b)
        self.assertFalse(any(e['kind']=='local_decision' for e in a['events']))
    def test_new_rules_replay_exactly(self):
        s=fixture()
        with tempfile.TemporaryDirectory() as temp:
            store=Store(Path(temp)/'test.sqlite');gid=store.create(s)
            for _ in range(5):
                n=runtime.apply(s,{'type':'advance','decision':None});store.save(gid,n,s['revision']);s=n
            self.assertEqual(runtime.verify_replay(store,gid)['status'],'identical')

if __name__=='__main__':unittest.main()
