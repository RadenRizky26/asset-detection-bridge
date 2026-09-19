# ARCHITECTURE — Cara Kerja Bridge

```
HOST (pemilik web app)                         BRIDGE (mesin ini, +AutoCAD)
┌──────────────────────────────┐               ┌─────────────────────────────┐
│ Next.js :3000                │               │ FastAPI :8765               │
│  /dwg-export UI              │    HTTP       │  bridge_main.py             │
│  /api/dwg-export/*           │ ────────────► │  markup_executor.py         │
│  PostgreSQL + Redis          │  REST/JSON    │  autocad_client.py (COM)    │
└──────────────────────────────┘               └──────────────┬──────────────┘
                                                              │ pywin32 COM
                                                              ▼
                                                     AutoCAD aktif + DWG open
```

## Alur Satu Job Execute

1. Host kirim `POST /calibrate/execute` berisi:
   `pdf_base64` (markup PDF) + `pdf_frame_points_mm` (3 titik kalibrasi web, mm)
   + `reference_text` (handle/height/style dari dropdown).
2. Bridge jalan di **background thread** (HTTP langsung return `job_id`).
3. Bridge extract FreeText dari PDF (`pdf-markup-core.extract_pdf_annotations`).
   PDF generate-an tidak punya frame vector → dipakai manual fallback dari titik web.
4. Matrix affine dihitung (`affine_from_3_points`, PDF-mm → unit DWG).
5. Titik frame DWG:
   - **Default:** prompt 3 klik langsung di AutoCAD (`Utility.GetPoint` ×3, OSNAP endpoint).
   - **Preset:** bila host mengirim `dwg_frame_points` (`/execute-with-preset`), tanpa klik.
6. Tiap annotasi: transform posisi → `ModelSpace.AddText` (layer import, style reference)
   → opsional revision cloud (closed LWPolyline + bulge) di layer cloud.
7. `doc.Save()` + `ZoomExtents`. Host polling `GET /jobs/{id}` untuk progress.

## Batasan Desain

- **COM single-thread**: semua akses AutoCAD di-serialize satu lock global.
- **Satu insert berat per waktu** dianjurkan; job paralel akan antri di lock.
- **Windows only**: `pywin32` tidak ada di Linux/Mac — jangan coba container Linux.
- **MVP satu halaman** (`pdf_page_index`, default 0), revisi cloud hanya di DWG.
- `lib/pdf-markup-core/` **dilarang** import `win32com`/`pythoncom` (aturan repo utama) —
  semua COM hanya di `autocad_client.py` + `markup_executor.py`.
