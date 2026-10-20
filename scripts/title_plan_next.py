#!/usr/bin/env python3
"""Read-only next-title selector; never claims writer lease or publishes."""
import argparse
import json
from pathlib import Path
from slug_policy import suggested_slug
ROOT=Path(__file__).resolve().parents[1]
PLAN=ROOT/'editorial'/'title-plan-1482'/'plan.json'
def main():
    p=argparse.ArgumentParser()
    p.add_argument('--limit',type=int,default=3)
    p.add_argument('--term',type=int,default=None)
    args=p.parse_args()
    if not 1<=args.limit<=10:raise ValueError('Select 1..10 at most')
    data=json.loads(PLAN.read_text(encoding='utf-8'))
    rows=[r for r in data['rows'] if r['status']=='PLANNED' and
          (args.term is None or r['category_id']==args.term)]
    # Existing Topic IDs are not assignable twice. Read the latest live topic
    # registry first; plan.json alone cannot prove a title is still unused.
    used=set()
    path=ROOT/'data/topics.jsonl'
    if path.exists():
        for line in path.read_text(encoding='utf-8').splitlines():
            if not line.strip():continue
            obj=json.loads(line)
            if obj.get('title_plan_id'):used.add(obj['title_plan_id'])
    rows=[r for r in rows if r['plan_id'] not in used]
    print(json.dumps({'count':len(rows),'next':[
       {**{k:r[k] for k in ('plan_id','title','category_id',
              'category_name','parent','taxonomy_key','intent',
              'research_query','sources_min','sources_max')},
        'title_plan_id':r['plan_id'],
        'suggested_slug':suggested_slug(r['title']),
        'suggested_canonical_target':'https://thuexemaynguyentu.com/'+suggested_slug(r['title'])+'/'}
       for r in rows[:args.limit]],
       'note':'Research 1-4 real sources; Research QA and Writer lease required before Publisher.'},
       ensure_ascii=False,indent=2))
if __name__=='__main__':main()
