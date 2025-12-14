#!/bin/sh
exec python -m uvicorn  --host 0.0.0.0 --port 8010 app.main:app --reload