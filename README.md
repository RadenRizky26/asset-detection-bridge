# AutoCAD Bridge — Client/Colleague Edition

Jalankan **PDF Markup → AutoCAD DWG** insert langsung ke AutoCAD yang sedang terbuka
di mesin Windows ini. Web app (Next.js) jalan di mesin **host**; repo ini hanya berisi
yang dibutuhkan sisi bridge: core Python murni + FastAPI bridge service + setup script.

> Teman/rekan **tidak perlu** clone repo utama (`Asset-Detection`). Cukup repo kecil ini.

---

## Prasyarat

| Item | Keterangan |
|------|------------|
| OS | Windows 10/11 |
| AutoCAD | 2018+ terinstall (semua versi — auto-detect via registry) |
| Python | 3.10+ (centang **Add python.exe to PATH** saat install) |
| Jaringan | Satu LAN/VPN dengan mesin host |

---

## Quick Start (5 menit)

```powershell
# 1. Clone (atau extract ZIP release)
git clone <repo-url> asset-detection-bridge
cd asset-detection-bridge

# 2. PowerShell sebagai Administrator, ganti IP dengan IP mesin host:
.\scripts\setup-bridge.ps1 -HostIP 192.168.1.30
```

Script otomatis: detect IP LAN → buka firewall 8765 → cek AutoCAD →
`pip install` kedua package → tulis `.env` (CORS ke host) →
**minta buka DWG target di AutoCAD** → start bridge di `0.0.0.0:8765`.

Alternatif manual: `start-bridge.bat` (pastikan AutoCAD + DWG sudah open).

## Verifikasi

```powershell
curl http://localhost:8765/health
# → {"status":"ok","autocad_connected":true,"active_doc":"Plant-A.dwg"}
```

Lalu buka di browser: `http://<IP-HOST>:3000/dwg-export` → jalankan wizard
(generate → kalibrasi → reference → execute).

---

## Isi Repo

```
asset-detection-bridge/
├── lib/pdf-markup-core/      Pure Python: geometri, PDF extract/generate/render,
│                             revision-cloud, skema Pydantic, kalibrasi. TANPA AutoCAD.
├── autocad-bridge/           FastAPI + pywin32 (Windows only). COM ke AutoCAD aktif.
├── scripts/setup-bridge.ps1  Setup otomatis (Admin PowerShell).
├── start-bridge.bat          Starter manual.
└── docs/                     QUICKSTART, ARCHITECTURE, TROUBLESHOOTING, API.
```

Dokumentasi lengkap: `docs/QUICKSTART.md`.

## Catatan Penting

- Bridge insert ke **dokumen AKTIF** di AutoCAD — pastikan DWG target yang sedang open.
- Tanpa preset DWG: saat execute, klik 3 titik frame (BL → BR → TL) langsung di AutoCAD.
- Satu job insert per bridge dalam satu waktu (COM di-serialize + lock).
- Butuh detail endpoint? Lihat `docs/API.md`.
