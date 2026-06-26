"""Check which routes are registered on the API app."""
import sys
sys.path.insert(0, 'src')

from api.main import app

all_paths = []
for r in app.routes:
    rtype = type(r).__name__
    path = getattr(r, 'path', None)
    paths = getattr(r, 'paths', None)
    
    if path:
        all_paths.append((rtype, path))
    elif paths:
        for p in paths:
            all_paths.append((rtype, p))

print(f'Total route entries: {len(app.routes)}')
print(f'Total paths: {len(all_paths)}')
print()

phase2_paths = [(t, p) for t, p in all_paths if 'phase2' in p.lower()]
print(f'Phase2 paths ({len(phase2_paths)}):')
for t, p in sorted(phase2_paths, key=lambda x: x[1]):
    print(f'  [{t}] {p}')

print()
print('Routes by type:')
from collections import Counter
type_counts = Counter(type(r).__name__ for r in app.routes)
for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
    print(f'  {t}: {c}')
