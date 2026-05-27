#!/usr/bin/env python3
"""Generate hotspot report for 2026-05-27"""
import json, os

db_path = '/workspace/005-News/hotspot_event_db_v2.json'
media_path = '/workspace/005-News/media_ranking_2026.json'
out_dir = '/workspace/005-News/2026-05-27'
os.makedirs(out_dir, exist_ok=True)

with open(db_path, 'r', encoding='utf-8') as f:
    db = json.load(f)
with open(media_path, 'r', encoding='utf-8') as f:
    mdb = json.load(f)

today = '2026-05-27'
# 今日新增：last_seen == today (最近出现日期)
te = [e for e in db if e.get('last_seen') == today]
all_events = db
entities = set(e.get('entity_id', '') for e in all_events if e.get('entity_id'))
long_events = [e for e in all_events if (e.get('persistence') or 0) >= 3]
top20 = sorted(all_events, key=lambda x: (x.get('appearances', 0), x.get('last_seen', '')), reverse=True)[:20]

cn = mdb.get('cn_top100', [])
top20media = cn[:20]

print(f'TODAY={today} ADDEVENTS={len(te)} TOTAL={len(all_events)} ENTITIES={len(entities)} LONG={len(long_events)}')
print('===TOP20===')
for i, e in enumerate(top20, 1):
    r = e.get('repr', {})
    print(f"{i}|[app={e.get('appearances',0)} pers={e.get('persistence',0)}] {r.get('title','no-title')[:60]}")
print('===TOP20MEDIA===')
for i, row in enumerate(top20media, 1):
    print(f"{i}. {row.get('name','')} rank={row.get('rank','')}")