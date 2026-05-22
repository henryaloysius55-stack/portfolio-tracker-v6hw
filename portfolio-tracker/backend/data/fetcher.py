INFO:     Shutting down
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [46]
==> Running 'uvicorn main:app --host 0.0.0.0 --port $PORT'
INFO:     Started server process [46]
INFO:     Waiting for application startup.
Menu
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
INFO:     68.46.46.130:0 - "OPTIONS /watchlist/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /ai-advisor/personas HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /transactions/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /holdings/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "GET /ai-advisor/personas HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "GET /transactions/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "GET /watchlist/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "GET /holdings/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /copy-trading/my-profile HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "GET /copy-trading/my-profile HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /copy-trading/profile HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "PATCH /copy-trading/profile HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /benchmark/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "GET /copy-trading/famous-investors HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "GET /benchmark/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /holdings/138 HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "DELETE /holdings/138 HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /ai-advisor/personas HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /holdings/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /transactions/ HTTP/1.1" 200 OK
INFO:     68.46.46.130:0 - "OPTIONS /watchlist/ HTTP/1.1" 200 OK
==> Deploying...
==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
==> No open ports detected, continuing to scan...
==> Docs on specifying a port: https://render.com/docs/web-services#port-binding
==> Running 'uvicorn main:app --host 0.0.0.0 --port $PORT'
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/bin/uvicorn", line 7, in <module>
    sys.exit(main())
             ~~~~^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 1524, in __call__
    return self.main(*args, **kwargs)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 1445, in main
    rv = self.invoke(ctx)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 1308, in invoke
    return ctx.invoke(self.callback, **ctx.params)
           ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/click/core.py", line 877, in invoke
    return callback(*args, **kwargs)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/main.py", line 441, in main
    run(
    ~~~^
        app,
        ^^^^
    ...<48 lines>...
        reset_contextvars=reset_contextvars,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/main.py", line 609, in run
    config.load_app()
    ~~~~~~~~~~~~~~~^^
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/config.py", line 415, in load_app
    return import_from_string(self.app)
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/importer.py", line 22, in import_from_string
    raise exc from None
  File "/opt/render/project/src/.venv/lib/python3.14/site-packages/uvicorn/importer.py", line 19, in import_from_string
    module = importlib.import_module(module_str)
  File "/opt/render/project/python/Python-3.14.3/lib/python3.14/importlib/__init__.py", line 88, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "<frozen importlib._bootstrap>", line 1398, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1371, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1342, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 938, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 759, in exec_module
  File "<frozen importlib._bootstrap>", line 491, in _call_with_frames_removed
  File "/opt/render/project/src/portfolio-tracker/backend/main.py", line 15, in <module>
    from routes.equitylens import router as equitylens_router
  File "/opt/render/project/src/portfolio-tracker/backend/routes/equitylens.py", line 2, in <module>
    from modules.screener import screen_ticker
  File "/opt/render/project/src/portfolio-tracker/backend/modules/screener.py", line 12, in <module>
    from data.fetcher import get_price_history
ModuleNotFoundError: No module named 'data'
==> Exited with status 1
==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
==> No open ports detected, continuing to scan...
==> Docs on specifying a port: https://render.com/docs/web-services#port-binding
==> Running 'uvicorn main:app --host 0.0.0.0 --port $PORT'
==> Running 'uvicorn main:app --host 0.0.0.0 --port $PORT'
