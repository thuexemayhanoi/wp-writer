#!/usr/bin/env python3
"""Test REAL GitHub Actions WordPress credentials against a safe existing draft.

Never creates/publishes a campaign article. The dedicated isolated factory
acceptance draft is used only after verifying its slug + status.
"""
import json
import os
from pathlib import Path
from common import WP, SITE, now
from publisher import seo_adapter_check

DRAFT_ID=3870
DRAFT_SLUG='wp-writer-factory-acceptance-20261016'
SEO_TITLE='[KIỂM THỬ] SEO REST của GitHub Publisher — không xuất bản'
SEO_DESC=('Bản nháp thử ghi và đọc lại Yoast REST SEO title, description và '
          'canonical trước khi cho phép xuất bản tự động.')


def check(client):
    post=client.get('wp/v2/posts/'+str(DRAFT_ID)+'?context=edit')
    if (post.get('id')!=DRAFT_ID or post.get('status')!='draft'
            or post.get('slug')!=DRAFT_SLUG):
        raise ValueError('Factory draft identity mismatch; no WordPress writes allowed')
    if not seo_adapter_check(client):
        raise ValueError('Yoast registered SEO fields or default canonical parity missing')
    # Restricted to TWO SEO meta fields, on the exact isolated factory draft.
    client.request('wp/v2/posts/'+str(DRAFT_ID),
                   {'meta':{'_yoast_wpseo_title':SEO_TITLE,
                            '_yoast_wpseo_metadesc':SEO_DESC}})
    after=client.get('wp/v2/posts/'+str(DRAFT_ID)+'?context=edit')
    meta=after.get('meta',{})
    if (after.get('status')!='draft' or after.get('slug')!=DRAFT_SLUG
            or meta.get('_yoast_wpseo_title')!=SEO_TITLE
            or meta.get('_yoast_wpseo_metadesc')!=SEO_DESC):
        raise ValueError('Yoast REST readback failed; do NOT activate production')
    return {'at':now(),'status':'PASS','site':SITE,'draft_id':DRAFT_ID,
        'draft_status':'draft','seo_title_readback':True,
        'seo_description_readback':True,'canonical_mode':'Yoast automatic permalink',
        'sample_default_canonical_checked':True,
        'wordpress_campaign_posts_published':0}


def main():
    report=check(WP(authenticated=True))
    print('WP_SEO_ADAPTER_REST_VERIFIED: '+json.dumps(report,ensure_ascii=False))
    dest=os.environ.get('SEO_ADAPTER_REPORT')
    if dest:
        path=Path(dest).resolve()
        if path.is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError('Report must not overwrite tracked repository files')
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    main()
