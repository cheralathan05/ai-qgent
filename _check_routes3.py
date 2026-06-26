"""Debug included routers."""
import sys
sys.path.insert(0, 'src')

from api.main import app

for i, r in enumerate(app.routes):
    if 'IncludedRouter' in type(r).__name__:
        print(f'[{i}] {type(r).__name__}')
        print(f'  dir: {[x for x in dir(r) if not x.startswith("_")]}')
        for attr in dir(r):
            if not attr.startswith('_'):
                try:
                    val = getattr(r, attr)
                    if callable(val):
                        continue
                    if isinstance(val, str):
                        print(f'  .{attr} = {val!r}')
                except Exception:
                    pass
        print()
