import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
d=json.loads(c.execute('select payload from decisions where decision_index=?',(int(sys.argv[2]),)).fetchone()[0])
o=d['observation']
print(list(o.keys()))
for k in o:
    v=json.dumps(o[k])
    if k not in('known_terrain','map_features','units_terrain'): print(k,v[:int(sys.argv[3])])
    else: print(k,len(v))
print({k:v for k,v in d.items() if k not in('observation','text','usage','orders','proposed_orders')})
