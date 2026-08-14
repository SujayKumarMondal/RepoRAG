from fastapi_server import app

search_path = "/api/v1/graph/{repository_id}/symbol/{symbol}"
found = []
for r in app.routes:
    if r.path == search_path:
        found.append((r.path, getattr(r, 'methods', None), type(r).__name__))

print('Search path:', search_path)
if not found:
    print('Route not found in app.routes')
    # list closest matches
    candidates = [r.path for r in app.routes if r.path.startswith('/api/v1/graph')]
    print('Graph-related routes (sample):')
    for c in sorted(candidates):
        print('  ', c)
else:
    print('Found route(s):')
    for p, methods, kind in found:
        print('  ', p, methods, kind)
