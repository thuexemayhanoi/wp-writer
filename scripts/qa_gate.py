#!/usr/bin/env python3
"""Per-article QA checkpoint: admit PASS while other articles require repair.

Writer hashes are independently admitted by Publisher intake on the state branch;
a writer may need a fresh QA run after a revision receipt is persisted. Never
weaken the submission-hash gate to resolve that normal asynchronous race.

The only green outcome is a COMPLETE fresh per-article report. Missing files,
stale source hashes, unsupported status, interrupted evaluation, or missing
repair queue FAIL the workflow. No WordPress credentials or article rewrites.
"""
import json
from pathlib import Path
import subprocess
import sys
from common import ROOT,digest

VALID={'PASS','FAIL','REVIEW'}

def validate_complete(root=ROOT):
    root=Path(root)
    drafts=sorted((root/'posts/drafts').glob('NT-*.md'))
    output=root/'data/qa'
    report_path=root/'reports/repair-queue.json'
    if not report_path.is_file():
        raise ValueError('QA did not produce complete fresh repair-queue checkpoint')
    repair=json.loads(report_path.read_text(encoding='utf-8'))
    if not isinstance(repair,list):
        raise ValueError('Repair queue must be a list')
    receipt={}
    for path in drafts:
        topic_id=path.stem
        file=output/(topic_id+'.json')
        if not file.is_file():
            raise ValueError('Missing QA checkpoint for '+topic_id)
        qa=json.loads(file.read_text(encoding='utf-8'))
        if qa.get('topic_id')!=topic_id:
            raise ValueError('QA topic identity mismatch: '+topic_id)
        if qa.get('source_sha256')!=digest(path.read_bytes()):
            raise ValueError('Stale or wrong QA source digest: '+topic_id)
        state=qa.get('status')
        if state not in VALID:
            raise ValueError('Invalid QA result: '+topic_id)
        if state=='PASS':
            if qa.get('errors') or qa.get('review'):
                raise ValueError('PASS has unaddressed errors/reviews: '+topic_id)
            if 'word_count' not in qa or 'gates' not in qa:
                raise ValueError('PASS missing quality gate evidence: '+topic_id)
        receipt[topic_id]=state
    expected={topic_id for topic_id,s in receipt.items() if s!='PASS'}
    found=[]
    for item in repair:
        if not isinstance(item,dict):
            raise ValueError('Repair ticket must be an object')
        ticket=item.get('topic_id')
        if ticket not in expected or item.get('status')!=receipt.get(ticket):
            raise ValueError('Repair queue inconsistent with QA receipts')
        found.append(ticket)
    if len(found)!=len(set(found)) or set(found)!=expected:
        raise ValueError('Incomplete or duplicate repair tickets')
    return {'qa_run':'COMPLETE','draft_count':len(drafts),
            'pass_count':sum(status=='PASS' for status in receipt.values()),
            'repair_count':len(expected),'repair_ids':sorted(expected),
            'publish_eligibility':'PER_ARTICLE_ONLY',
            'wordpress_posts_created':0}


def main():
    output=ROOT/'data/qa'
    output.mkdir(parents=True,exist_ok=True)
    repair_path=ROOT/'reports/repair-queue.json'
    # Do not accept stale artifacts from another commit or previous CI run. With the incremental sweep (config
    # qa-rules.incremental_sweep) only records that are hash-valid for the current draft, rules and topic row (or
    # frozen by a VERIFIED WordPress publication) survive; every other record is removed and evaluated afresh.
    from qa_incremental import enabled,plan
    incremental=enabled()
    keep=set()
    if incremental:
        p=plan();keep=set(p['frozen'])|set(p['cached'])
        print('QA_INCREMENTAL: frozen=%d cached=%d fresh=%d'%(len(p['frozen']),len(p['cached']),len(p['fresh'])))
    for path in output.glob('NT-*.json'):
        if path.stem not in keep:
            path.unlink()
    repair_path.unlink(missing_ok=True)
    cmd=[sys.executable,str(ROOT/'scripts/qa.py')]+(['--incremental'] if incremental else [])
    result=subprocess.run(cmd,cwd=ROOT,check=False)
    # QA returns 1 when at least one draft is FAIL/REVIEW, but Python
    # exceptions also return 1. Only a complete, hash-matched fresh checkpoint
    # is admissible; crashes can never be masked as article REPAIR.
    if result.returncode not in (0,1):
        raise SystemExit('QA infrastructure error '+str(result.returncode))
    receipt=validate_complete()
    message=json.dumps(receipt,ensure_ascii=False)
    print('QA_PIPELINE_COMPLETE: '+message)
    if result.returncode==1 and receipt['repair_count']==0:
        raise SystemExit('QA script failed without a valid repair reason')
    if result.returncode==0 and receipt['repair_count']:
        raise SystemExit('QA return code contradicts repair-queue contents')
    if 'GITHUB_STEP_SUMMARY' in __import__('os').environ:
        with open(__import__('os').environ['GITHUB_STEP_SUMMARY'],'a',encoding='utf-8') as f:
            f.write('## Writer QA readiness (independent articles)\n\n')
            f.write('**PASS:** '+str(receipt['pass_count'])+'; **REPAIR:** '+str(receipt['repair_count'])+
                    '; QA reports complete and hash checked.\n')
            f.write('Workflow SUCCESS means QA execution succeeded, NOT that every article passed. '
                    'Publisher independently applies live QA to each post before any WordPress write.\n')


if __name__=='__main__':
    main()
