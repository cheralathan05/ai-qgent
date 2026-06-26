"""Check included routers."""
import sys
sys.path.insert(0, 'src')

from api.main import app

for r in app.routes:
    if 'IncludedRouter' in type(r).__name__:
        prefix = getattr(r, 'prefix', 'N/A')
        router = getattr(r, 'router', None)
        if router:
            route_paths = []
            for sr in router.routes:
                p = getattr(sr, 'path', None) or list(getattr(sr, 'paths', []))[0] if hasattr(sr, 'paths') else None
                if p:
                    route_paths.append(prefix + p)
            print(f'Router prefix={prefix}: {len(route_paths)} routes')
            for rp in sorted(route_paths)[:5]:
                print(f'  {rp}')
            if len(route_paths) > 5:
                print(f'  ... and {len(route_paths)-5} more')
        else:
            print(f'Router prefix={prefix}: no router attr')
