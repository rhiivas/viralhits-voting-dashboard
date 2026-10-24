#!/usr/bin/env python3
"""Convert historical vote snapshots to the shared dashboard schema."""
import csv,sys
from pathlib import Path
OUT=Path('docs/viral_hits_standings.csv')
FIELDS=['timestamp_utc','rank','nominee','percentage','change_pp','rank_change','gap_to_leader_pp']
if len(sys.argv)!=2: raise SystemExit('Usage: python migrate_history.py path/to/old.csv')
with open(sys.argv[1],newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
by_time={}
for r in rows:
    try:
        entry={'timestamp_utc':r['timestamp_utc'],'rank':int(r['rank']),'nominee':r['nominee'],'percentage':float(r['percentage'])}
        by_time.setdefault(entry['timestamp_utc'],[]).append(entry)
    except (ValueError,KeyError,TypeError): continue
OUT.parent.mkdir(exist_ok=True)
previous={}
with OUT.open('w',newline='',encoding='utf-8-sig') as f:
    writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader()
    for stamp,items in sorted(by_time.items()):
        leader=max(x['percentage'] for x in items)
        for x in items:
            old=previous.get(x['nominee'])
            writer.writerow({**x,'change_pp':round(x['percentage']-old['percentage'],2) if old else '', 'rank_change':old['rank']-x['rank'] if old else '', 'gap_to_leader_pp':round(leader-x['percentage'],2)})
            previous[x['nominee']]=x
print(f'Converted {sum(map(len,by_time.values()))} rows into {OUT}')
