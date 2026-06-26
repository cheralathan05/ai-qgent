"""Check included router contents."""
import sys
sys.path.insert(0, 'src')

from api.main import app

for i, r in enumerate(app.routes):
    if 'IncludedRouter' in type(r).__name__:
        candidates = r.effective_candidates()
        print(f'[{i}] {len(candidates)} effective candidates')
        first = candidates[0]
        print(f'  Sample attrs: {[x for x in dir(first) if not x.startswith("_")]}')
        for c in candidates[:5]:
            path = getattr(c, 'path', getattr(c, 'url_path', ''))
            method = getattr(c, 'method', getattr(c, 'methods', ''))
            print(f'  {method} {path}')
        if len(candidates) > 5:
            print(f'  ... and {len(candidates)-5} more')
        print()
