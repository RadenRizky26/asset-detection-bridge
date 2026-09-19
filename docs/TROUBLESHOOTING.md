# TROUBLESHOOTING — Bridge

| Gejala | Penyebab umum | Solusi |
|--------|---------------|--------|
| `curl /health` → `autocad_connected: false` | AutoCAD belum buka / DWG belum open | Buka AutoCAD + DWG target. Tidak perlu restart bridge (probe tiap request). |
| `pip install -e` gagal | Python < 3.10 / pip tua / tanpa internet | `python --version` (≥3.10), `python -m pip install --upgrade pip setuptools` |
| `import win32com` / `pythoncom` error | Bukan Windows / pywin32 belum install | Wajib Windows. `pip install pywin32`, lalu `python Scripts/pywin32_postinstall.py -install` |
| Host dapat "Bridge HTTP 502/timeout" | Firewall blokir / beda subnet / bridge mati | Buka inbound TCP 8765 (Private). Test dari host: `curl http://<IP-BRIDGE>:8765/health`. Pastikan satu LAN/VPN. |
| Host dapat CORS error di browser | `CORS_ALLOW_ORIGINS` salah | `autocad-bridge/.env`: `CORS_ALLOW_ORIGINS=http://<IP-HOST>:3000`, restart bridge |
| Execute 0 inserted / banyak failed | Urutan titik kalibrasi salah | Di web ulangi step kalibrasi (BL → BR → TL). Cek residual via `/calibrate/compute` |
| `GetPoint` tidak merespons di AutoCAD | Fokus window / Utility sibuk | Klik window AutoCAD agar fokus, ulangi execute |
| `Save failed after retries` | DWG read-only / terkunci / path network putus | Save manual sekali di AutoCAD, cek permission file |
| Port 8765 sudah dipakai | Instance bridge ganda | Matikan instance lama (Task Manager → python/uvicorn) |
| Script `.ps1` ditolak PowerShell | ExecutionPolicy | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| AutoCAD tidak terdeteksi script | Install non-standar / versi lama | Warning saja — lanjut manual bila AutoCAD sebenarnya ada |

## Log

Uvicorn mencetak log ke console. Untuk file log:

```powershell
uvicorn bridge_main:app --host 0.0.0.0 --port 8765 --log-level info 2>&1 | Tee-Object bridge.log
```
