"""Historical setting with authored, uncalibrated POC terrain and detachments."""
import math
from .grid import COLS, ROWS, center, key

SIDES = ('union','confederate')
RULES_VERSION = 'poc-8'

def terrain():
    cells = {}
    for r in range(ROWS):
        for c in range(COLS):
            p=[c,r]; x,y=center(p)
            hill = 40*math.exp(-((x-530)**2/170**2+(y-600)**2/230**2))
            spur = 15*math.exp(-((x-540)**2/120**2+(y-390)**2/140**2))
            woods = y > 530 and 250 < x < 740
            rocks = 420 < x < 630 and 490 < y < 670
            kind = 'rocky' if rocks else 'woods' if woods else 'open'
            cells[key(p)]={'pos':p,'elevation':round(145+hill+spur), 'terrain':kind,
                           'move_cost':{'open':100,'woods':145,'rocky':170}[kind],
                           'cover':{'open':10,'woods':32,'rocky':46}[kind]}
    return cells

def unit(uid,side,name,pos):
    return {'id':uid,'side':side,'name':name,'pos':pos,'initial':40,'strength':40,
            'ammo':1600,'morale':85,'suppression':0,'fatigue':0,'status':'ready',
            'target':None,'stance':'hold','move_credit':0,'loss_credit':0,
            'order_version':0,'skill':70,'unit_type':'infantry','weapon_class':'rifled muskets',
            'recon_role':'line','recon_skill':35,'local_action':'hold','local_reason':'Awaiting contact; hold position.',
            'tactical_target':None,'last_attacked_turn':-99,'withdraw_until':0}

def create(rules=RULES_VERSION):
    units = [unit('U1','union','20th Maine · A',[11,14]),
             unit('U2','union','20th Maine · B',[13,15]),
             unit('U3','union','20th Maine · C',[10,13]),
             unit('C1','confederate','15th Alabama · A',[5,20]),
             unit('C2','confederate','15th Alabama · B',[9,20]),
             unit('C3','confederate','47th Alabama · A',[3,17])]
    # Authored reconnaissance assignments; not claims about the historical regiments.
    for u in (units[2],units[5]):u.update(recon_role='scout',recon_skill=80)
    s={'rules':rules,'scenario':'little-round-top-v2','turn':0,'revision':0,
       'status':'active','winner':None,'reason':None,'objective':[11,15],
       'recon_memory':{},'intel_assets':[],'capture':0,'max_turns':60,'seconds_per_turn':30,'units':units,
       'cells':terrain(),'orders':[],'reports':[], 'contacts':{x:{} for x in SIDES},
       'friendly_reports':{side:{u['id']:dict(u,observed_turn=0,received_turn=0)
                            for u in units if u['side']==side} for side in SIDES},
       'dispatches':{x:[] for x in SIDES},'events':[], 'decisions':[],
       'weather':{'season':'summer','conditions':'dry, clear (fixed POC condition)'},
       'hq':{'union':[14,8],'confederate':[4,20]}}
    if rules in ('poc-3','poc-4','poc-5','poc-6','poc-7','poc-8'):
        s['scenario']='little-round-top-v3'
        s['rally_points']={side:list(pos) for side,pos in s['hq'].items()}
        # Staff are attached to existing aggregate detachments, not extra soldiers.
        s['commanders']={side:{'controller_id':side+'-commander','unit_id':uid,
                               'communications':'civil-war-courier-v1'}
                         for side,uid in (('union','U2'),('confederate','C2'))}
        s['hq']={side:next(list(u['pos']) for u in units if u['id']==c['unit_id'])
                 for side,c in s['commanders'].items()}
        s['acknowledgements']={side:{} for side in SIDES}
    if rules in ('poc-4','poc-5','poc-6','poc-7','poc-8'):
        s.update(scenario='little-round-top-v4',formation_ops=[],formation_notices={},retired_units=[])
    if rules in ('poc-5','poc-6','poc-7','poc-8'):
        s['scenario']='little-round-top-v5'
        s['supply_sites']=[{'id':side+'-ammunition','side':side,'name':name,
                            'pos':pos,'ammo':2400,'weapon_class':'rifled muskets'}
                           for side,name,pos in [('union','Union ammunition point',[14,8]),
                                                 ('confederate','Confederate ammunition point',[4,20])]]
    if rules in ('poc-6','poc-7','poc-8'):
        from . import features
        s['scenario']='little-round-top-v6'
        for u in units:u['tools']=20
        features.setup(s)
        for side in SIDES:
            for u in units:
                if u['side']==side:s['friendly_reports'][side][u['id']]['tools']=u['tools']
    if rules=='poc-7':s.update(scenario='little-round-top-v7',recommendations=[])
    if rules=='poc-8':
        s.update(scenario='little-round-top-v8',recommendations=[],standing_orders=[])
        for u in units:
            u.update(standing_profile='balanced',standing_version=0)
            s['friendly_reports'][u['side']][u['id']].update(standing_profile='balanced',standing_version=0)
    return s
