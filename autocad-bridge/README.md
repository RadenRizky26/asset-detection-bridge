# AutoCAD Bridge Service

FastAPI service that exposes **local AutoCAD COM automation** to the
Asset-Detection Next.js web app. Windows-only (requires AutoCAD + pywin32).

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health + AutoCAD connection state |
| POST | `/autocad/connect` | Verify AutoCAD + active document |
| GET | `/autocad/text-entities` | List TEXT/MTEXT entities in active DWG (for the reference-text dropdown) |
| POST | `/calibrate/execute` | Run full PDF-markup → DWG insert job (background) |
| GET | `/jobs/{job_id}` | Poll job status |
| POST | `/jobs/{job_id}/cancel` | Request cancellation |

## Run (Windows, AutoCAD open with target DWG)

```bat
pip install -e ../lib/pdf-markup-core
pip install -e .
set AUTOCAD_BRIDGE_PORT=8765
uvicorn bridge_main:app --host 127.0.0.1 --port 8765
```

Or use `start-bridge.bat` at the repo root (also started by `npm run dev:all`).

## Configuration

All settings via environment variables (see `src/config.py`):

- `AUTOCAD_BRIDGE_PORT` (default 8765)
- `AUTOCAD_COM_RETRY_COUNT` / `AUTOCAD_COM_RETRY_DELAY`
- `DEFAULT_IMPORT_LAYER`, `DEFAULT_REV_CLOUD_LAYER` (+ colors)
- `REV_CLOUD_MARGIN_FACTOR`, `REV_CLOUD_ARC_FACTOR`, `CREATE_REV_CLOUD`
- `IGNORE_TEXT_CONTAINS` (comma-separated), `TAG_NUDGE_X/Y`, `TEXT_HEIGHT_FACTOR`
- `CORS_ALLOW_ORIGINS` (comma-separated, default `http://localhost:3000`)
