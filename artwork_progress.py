"""Report catalog completion without changing images or user data."""
import json
from pathlib import Path
from artwork_catalog import ART_ROOT, ROOT, anime_catalog


def report():
    catalog=anime_catalog()
    pending=[key for key,entry in catalog.items() if not (ART_ROOT/entry['file']).is_file()]
    result=dict(total=len(catalog),completed=len(catalog)-len(pending),pending=pending,
                catalog_verified=(ART_ROOT/'anime/READY').is_file(),
                cleanup_applied=json.loads((ROOT/'artifacts/artwork-cleanup.json').read_text()).get('applied',False)
                if (ROOT/'artifacts/artwork-cleanup.json').is_file() else False)
    (ROOT/'artifacts/artwork-progress.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    result=report()
    print(f"{result['completed']} / {result['total']} illustrations complete; {len(result['pending'])} remaining")
