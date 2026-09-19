# API — Bridge Service (`http://<IP-BRIDGE>:8765`)

Base URL dikonfigurasi di host sebagai `AUTOCAD_BRIDGE_URL`. Semua body JSON.

## `GET /health`

```json
{"status":"ok","autocad_connected":true,"active_doc":"Plant-A.dwg","detail":null}
```

## `POST /autocad/connect`

Verifikasi AutoCAD + dokumen aktif.

```json
{"success":true,"doc_name":"Plant-A.dwg","layers":["0","PDF_TAG_IMPORT"],"detail":null}
```

## `GET /autocad/text-entities?layer=&limit=200`

Daftar TEXT/MTEXT di ModelSpace (sumber dropdown reference text di web).

```json
{"entities":[{"handle":"2A1","object_name":"AcDbText","text":"P-101","height":2.5,
"style":"Standard","insertion_x":10.0,"insertion_y":20.0}],"doc_name":"Plant-A.dwg"}
```

## `POST /calibrate/execute`

Job penuh (klik 3 titik DWG **interaktif** di AutoCAD). Return langsung `job_id`.

```json
{
  "pdf_base64": "<markup pdf base64>",
  "pdf_page_index": 0,
  "pdf_frame_points_mm": {"p1":{"x":0,"y":0},"p2":{"x":800,"y":0},"p3":{"x":0,"y":550}},
  "reference_text": {"handle":"2A1","height":2.5,"style":"Standard"},
  "create_rev_clouds": true,
  "import_layer": "PDF_TAG_IMPORT", "import_layer_color": 5,
  "rev_cloud_layer": "PDF_REV_CLOUD", "rev_cloud_color": 1,
  "tag_nudge_x": 0.0, "tag_nudge_y": 0.0,
  "target_space": "ModelSpace"
}
```

→ `{"job_id":"a1b2c3d4e5f6","status":"RUNNING"}`

## `POST /calibrate/execute-with-preset?dwg_p1=x,y&dwg_p2=x,y&dwg_p3=x,y`

Sama, tapi titik DWG dari preset tersimpan → **tanpa klik** di AutoCAD.

## `GET /jobs/{job_id}`

```json
{"job_id":"a1b2c3d4e5f6","status":"COMPLETED",
 "inserted_count":42,"failed_count":1,"doc_name":"Plant-A.dwg","error_detail":null}
```

Status: `PENDING | RUNNING | COMPLETED | FAILED | CANCELLED`.

## `POST /jobs/{job_id}/cancel`

→ `{"cancelled":true}`

## `POST /pdf/info` — `{"pdf_base64":"..."}`

Ukuran halaman PDF: `{page_count, pages:[{index,width_pt,height_pt,width_mm,height_mm,rotation}]}`.

## `POST /pdf/generate`

```json
{"assets":[{"asset_tag":"P-101","asset_type":"Pump","bbox_x":100,"bbox_y":200,
"bbox_w":150,"bbox_h":60,"pid_page":1}],
 "page_width_mm":841.0,"page_height_mm":594.0,"font_size_pt":6.0,"title":"..."}
```

→ `{"pdf_base64":"...","size_bytes":12345}`

## `POST /pdf/render` — `{"pdf_base64":"...","page_index":0,"scale":1.5}`

→ `{png_base64,width_px,height_px,render_scale,page_width_pt,page_height_pt,rotation,page_count}`

## `POST /calibrate/compute` — `{"pdf_points_mm":[[x,y]×3],"dwg_points":[[x,y]×3]}`

→ `{calibration:{...matrix...}, quality:{residuals,max_residual,frame sizes}}`.
`max_residual` besar = kemungkinan urutan klik salah.
