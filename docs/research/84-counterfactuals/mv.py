import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
lo=int(sys.argv[2]); hi=int(sys.argv[3])
for s,t,k,p in c.execute("select seq,turn,kind,payload from events where turn between ? and ? and kind in ('unit_moved','order_sent','order_delivered','volley','casualties','mission_completed','movement_blocked','unit_routed','battle_ended','local_decision') order by seq",(lo,hi)):
    d=json.loads(p)
    if k=='unit_moved': print(s,'t%d'%t,'moved',d['unit_id'],d['origin'],'->',d['destination'])
    elif k=='order_sent': print(s,'t%d'%t,'sent',d['order_id'],d['side'],d['transport']['recipient_id'],d.get('destination'),'arr',d.get('arrival_turn'))
    elif k=='order_delivered': print(s,'t%d'%t,'deliv',d['order_id'],d['unit_id'])
    elif k=='local_decision':
        if d['action'] not in('continue','hold'): print(s,'t%d'%t,'local',d['unit_id'],d['action'],d['reason'][:60])
    elif k=='volley': print(s,'t%d'%t,'volley',{x:d[x] for x in d if x in('unit_id','target_id','shooter_id','side','target')})
    else: print(s,'t%d'%t,k,d.get('unit_id',''),d.get('count',''),d.get('remaining',''),d.get('reason',''))
