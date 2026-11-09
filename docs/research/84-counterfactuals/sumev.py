import json,sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
skip={'report_received','report_sent','local_decision','communication_forwarded','contact_observed','order_sent','order_delivered','mission_started','mission_active','mission_superseded','mission_completed','mission_blocked','unit_under_fire','volley','casualties','unit_moved','turn_completed','fieldworks_progress','recommendation_created','recommendation_expired','recommendation_received','recommendation_superseded','report_merged','movement_blocked'}
print({k:n for k,n in c.execute('select kind,count(*) from events group by 1')})
for s,t,k,p in c.execute('select seq,turn,kind,payload from events order by seq'):
    if k in skip: continue
    print(s,'t%d'%t,k,p[:int(sys.argv[2]) if len(sys.argv)>2 else 300])
