import copy
import tempfile
import sqlite3
import unittest
from pathlib import Path
from battle import engine,features,grid,inference,orders,runtime,scenario,formations
from battle.storage import Store
from test_formations import fixture


def dig(s,uid='U2'):
    engine.issue(s,'union',{'unit_id':uid,'stance':'dig_in','destination':None})

def works(s,pos):
    return next((f for f in s['map_features'] if f['kind']=='fortification' and f['pos']==pos),None)

class FeatureTests(unittest.TestCase):
    def test_briefed_features_and_road_edges_match_physics(self):
        s=scenario.create();v=engine.view(s)
        self.assertEqual({f['kind'] for f in v['map_features']},{'road','building','fortification'})
        road=next(f for f in s['map_features'] if f['kind']=='road')
        a,b=road['hexes'][:2]
        self.assertEqual(grid.distance(a,b),1)
        uphill=max(0,s['cells'][grid.key(b)]['elevation']-s['cells'][grid.key(a)]['elevation'])*3
        self.assertEqual(grid.cost(s['cells'],a,b),70+uphill)
        self.assertEqual(grid.cost(s['cells'],b,a),70+max(0,-uphill))
        self.assertEqual(works(s,[11,13])['cover'],60)

    def test_road_route_matches_dijkstra_cost(self):
        import heapq
        s=scenario.create();a=[2,2];b=[22,10];cells=s['cells']
        pending=[(0,tuple(a))];dist={tuple(a):0}
        while pending:
            spent,p=heapq.heappop(pending)
            if p==tuple(b):break
            if spent!=dist[p]:continue
            for n in grid.neighbors(p):
                cost=spent+grid.cost(cells,p,n);nt=tuple(n)
                if cost<dist.get(nt,float('inf')):dist[nt]=cost;heapq.heappush(pending,(cost,nt))
        route=grid.path(cells,a,b)
        self.assertEqual(sum(grid.cost(cells,p,q) for p,q in zip([a]+route,route)),dist[tuple(b)])

    def test_building_blocks_intermediate_sight_and_adds_cover(self):
        s=fixture();a=[2,3];b=[6,3];middle=grid.line(a,b)[2]
        self.assertTrue(grid.visible(s['cells'],a,b))
        s['cells'][grid.key(middle)]['obstacle_height']=8
        self.assertFalse(grid.visible(s['cells'],a,b))
        real=scenario.create();self.assertEqual(real['cells']['7,3']['cover'],45)
        self.assertEqual(real['cells']['7,3']['move_cost'],140)

    def test_dig_requires_delivery_time_labor_and_fatigue(self):
        s=fixture();u=engine.find_unit(s,'U2');dig(s)
        self.assertIsNone(works(s,u['pos']))
        engine.advance(s);w=works(s,u['pos'])
        self.assertEqual(w['progress'],10);self.assertEqual(u['fatigue'],2)
        self.assertEqual(s['cells'][grid.key(u['pos'])]['cover'],13)
        for _ in range(9):engine.advance(s)
        self.assertEqual(w['progress'],100);self.assertEqual(w['cover'],40)
        self.assertEqual(u['mission_result']['status'],'completed');self.assertEqual(u['stance'],'hold')
        self.assertEqual((u['tools'],u['strength'],u['ammo']),(20,40,1600))
        self.assertEqual(len([e for e in s['events'] if e['kind']=='fieldworks_progress']),10)

    def test_fire_suspends_work_then_work_resumes(self):
        s=fixture();u=engine.find_unit(s,'U2');dig(s);engine.advance(s);w=works(s,u['pos']);before=w['effort']
        e=engine.find_unit(s,'C1');e['pos']=[6,2];engine.advance(s)
        self.assertEqual(w['effort'],before);self.assertEqual(u['mission_result']['status'],'blocked')
        e['pos']=[20,18]
        for _ in range(3):engine.advance(s)
        self.assertGreater(w['effort'],before)

    def test_tools_rock_and_exhaustion_limit_construction(self):
        s=fixture();u=engine.find_unit(s,'U2');u['tools']=5;s['cells']['3,2']['terrain']='rocky'
        dig(s);engine.advance(s);w=works(s,u['pos'])
        self.assertEqual(w['required'],800);self.assertEqual(w['effort'],10)
        u['fatigue']=80;engine.advance(s);self.assertEqual(w['effort'],10)
        self.assertEqual(u['mission_result']['status'],'blocked')

    def test_unsuitable_ground_or_missing_tools_fail_locally(self):
        for field,value in [('building','barn'),('road_neighbors',[[4,2]]),('tools',0)]:
            s=fixture();u=engine.find_unit(s,'U2')
            if field=='tools':u[field]=value
            else:s['cells']['3,2'][field]=value
            dig(s);engine.advance(s)
            self.assertIsNone(works(s,u['pos']));self.assertEqual(u['mission_result']['status'],'failed')

    def test_abandoned_work_stays_at_site_and_can_be_resumed(self):
        s=fixture();u=engine.find_unit(s,'U2');dig(s);engine.advance(s);w=works(s,[3,2]);before=w['effort']
        engine.issue(s,'union',{'unit_id':'U2','stance':'move','destination':[4,2]});engine.advance(s)
        self.assertEqual(w['effort'],before);self.assertEqual(w['pos'],[3,2]);self.assertEqual(u['pos'],[4,2])
        self.assertEqual(s['cells']['4,2']['cover'],10)
        engine.issue(s,'union',{'unit_id':'U2','stance':'move','destination':[3,2]});engine.advance(s)
        dig(s);engine.advance(s);self.assertEqual(w['effort'],before+40)

    def test_completed_works_do_not_stack_cover(self):
        s=fixture();dig(s)
        for _ in range(10):engine.advance(s)
        dig(s);engine.advance(s)
        self.assertEqual(works(s,[3,2])['cover'],40);self.assertEqual(len([f for f in s['map_features'] if f.get('pos')==[3,2]]),1)

    def test_remote_construction_requires_reports_and_does_not_leak_to_inference(self):
        s=fixture();engine.find_unit(s,'U2')['pos']=[8,2]
        from battle import comms
        comms.sync(s);dig(s,'U1')
        while not works(s,[2,2]):engine.advance(s)
        observed_turn=s['turn']
        self.assertIsNotNone(works(s,[2,2]))
        self.assertFalse(any(f['id']=='works-2,2' for f in engine.view(s)['map_features']))
        self.assertFalse(any(f['id']=='works-2,2' for f in engine.view(s,'confederate')['map_features']))
        known=inference.observation_for(s,'union')['known_terrain']
        self.assertEqual(next(c['cover'] for c in known if c['pos']==[2,2]),s['briefing_cells']['2,2']['cover'])
        self.assertTrue(any(f['id']=='works-2,2' for f in engine.god_view(s)['map_features']))
        while not any(f['id']=='works-2,2' for f in engine.view(s)['map_features']):engine.advance(s)
        f=next(f for f in engine.view(s)['map_features'] if f['id']=='works-2,2')
        self.assertLess(f['progress'],works(s,[2,2])['progress']);self.assertEqual(f['observed_turn'],observed_turn)

    def test_stale_feature_report_cannot_replace_newer(self):
        s=fixture();f={'id':'test','kind':'fortification','progress':50}
        for turn,progress in [(5,50),(3,20)]:features.receive(s,{'side':'union','observed_turn':turn,'data':{'features':[{**f,'progress':progress}]}})
        self.assertEqual(s['feature_reports']['union']['test']['progress'],50)

    def test_cover_reduces_recorded_fire_effect(self):
        exposures=[]
        for cover in (10,40):
            s=fixture();engine.find_unit(s,'C1')['pos']=[6,2];s['cells']['3,2']['cover']=cover
            engine.advance(s)
            exposures.append(next(e['exposure'] for e in s['events'] if e['kind']=='volley' and e['unit_id']=='C1' and e['target_id']=='U2'))
        self.assertLess(exposures[1],exposures[0])

    def test_split_combine_conserves_tools(self):
        s=fixture();formations.request(s,'union',{'kind':'split','unit_id':'U2','count':20,'destination':[4,2]})
        for _ in range(3):engine.advance(s)
        self.assertEqual(sum(u['tools'] for u in s['units']),120)
        formations.request(s,'union',{'kind':'combine','unit_id':'U2','partner_id':'UD1'})
        for _ in range(3):engine.advance(s)
        self.assertEqual(engine.find_unit(s,'UD1')['tools'],0);self.assertEqual(sum(u['tools'] for u in s['units']),120)

    def test_persistence_failure_cannot_partially_build(self):
        s=fixture();dig(s)
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'rollback.sqlite');gid=store.create(s)
            with store.connect() as db:db.execute("CREATE TRIGGER fail_work BEFORE INSERT ON events WHEN NEW.kind='fieldworks_progress' BEGIN SELECT RAISE(ABORT,'injected'); END")
            n=runtime.apply(s,{'type':'advance','decision':None})
            with self.assertRaises(sqlite3.IntegrityError):store.save(gid,n,s['revision'])
            self.assertEqual(store.load(gid),s)

    def test_dig_replays_exactly_and_old_catalog_excludes_it(self):
        s=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            store=Store(Path(tmp)/'replay.sqlite');gid=store.create(s)
            actions=[{'type':'orders','orders':[{'unit_id':'U2','stance':'dig_in','destination':None}]}]+[{'type':'advance','decision':None} for _ in range(12)]
            for a in actions:
                n=runtime.apply(s,a);store.save(gid,n,s['revision']);s=n
            self.assertEqual(runtime.verify_replay(store,gid)['status'],'identical')
        old=scenario.create(rules='poc-5')
        self.assertNotIn('dig_in',[t['id'] for t in orders.catalog(old)])
        with self.assertRaises(ValueError):dig(old)

if __name__=='__main__':unittest.main()
