# pdf-markup-core

Pure-Python core library for the **PDF Markup → AutoCAD DWG** workflow.
Ported from `markup_v4.0.py`. Zero AutoCAD/COM dependency — safe to use
from the Next.js backend (via the bridge service) and from tests.

## Modules

| Module | Contents |
|--------|----------|
| `geometry` | distance/angle helpers, 3-point affine matrix, point/vector transforms |
| `pdf_extract` | FreeText annotation extraction, drawing-frame auto-detection, pt→mm conversion |
| `pdf_render` | Render a PDF page to base64 PNG (for the web calibration canvas) |
| `pdf_generate` | Generate a markup PDF with FreeText annotations from confirmed assets |
| `cloud` | Revision-cloud vertex generation (used by the bridge when inserting in DWG) |
| `schemas` | Pydantic models shared between the web API and the bridge service |
| `calibrate` | Calibration helpers (mm conversion, matrix computation, validation) |

## Install (editable, for local dev)

```bash
pip install -e ".[dev]"
```

Used by `autocad-bridge` (same machine or any host — pure Python, no AutoCAD needed).

## Test

```bash
pytest
```

## Used from

- `autocad-bridge` — PDF extract/generate/render, calibration math, cloud vertices.
- Next.js web app — indirectly via bridge HTTP API only (never import Python from Node).
- Full workflow guide: `DWG-EXPORT.md` (repo root).

