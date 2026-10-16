import json
from common import WP
from taxonomy_sync import by_key,resolve
if __name__=='__main__':
    live=WP().all('wp/v2/categories',hide_empty='false')
    for key,item in by_key().items():
        if item['existing_or_planned']=='existing' and key!='uncategorized':print(json.dumps({'key':key,'term_id':resolve(key,by_key(),live)}))
