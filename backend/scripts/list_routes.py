from fastapi_server import app

routes = sorted(app.routes, key=lambda r: r.path)
for r in routes:
    methods = getattr(r, 'methods', None)
    print(f"{r.path} {methods}")
