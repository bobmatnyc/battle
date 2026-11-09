import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
side=sys.argv[2]
sent={}
for s,t,k,p in c.execute("select seq,turn,kind,payload from events where kind in ('order_sent','order_delivered','order_expired','order_refused','mission_started','mission_superseded','mission_completed','mission_failed','exploit_stopped','unit_routed','signal_sounded') order by seq"):
    d=json.loads(p)
    if k=='order_sent':
        if d['side']!=side: continue
        tr=d['transport']; sent[d['order_id']]=1
        print(s,'t%d'%t,'SENT',d['order_id'],'to',tr['recipient_id'],'dest',d.get('destination'),'arrive',d.get('arrival_turn'),tr.get('method'))
    elif k=='order_delivered':
        if d['order_id'] in sent: print(s,'t%d'%t,'DELIVERED',d['order_id'],d['unit_id'])
    elif k=='order_expired':
        if d['order_id'] in sent: print(s,'t%d'%t,'EXPIRED',d['order_id'])
    elif k in('mission_started','mission_superseded','mission_completed','mission_failed'):
        if d.get('unit_id','')[:1]==side[0].upper() or d.get('unit_id','')[:1]=='R' and side=='roman':
            print(s,'t%d'%t,k,d.get('unit_id'),d.get('template',''),d.get('reason','')[:60])
    else:
        print(s,'t%d'%t,k,d.get('unit_id',''),d.get('reason',''))
