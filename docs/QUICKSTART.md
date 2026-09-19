# QUICKSTART — Setup 5 Menit (Mesin Bridge / Teman)

Repo ini untuk **mesin yang punya AutoCAD**. Web app jalan di mesin **host** milik rekan Anda.
Anda hanya menjalankan bridge service + membuka DWG target.

## 1. Prasyarat

- [ ] Windows 10/11
- [ ] AutoCAD 2018+ terinstall
- [ ] Python 3.10+ terinstall (**centang "Add python.exe to PATH"**)
- [ ] Satu jaringan (LAN/VPN) dengan mesin host
- [ ] Tahu **IP mesin host** (tanya ke pemilik host, misal `192.168.1.30`)

## 2. Clone

```powershell
git clone <repo-url> asset-detection-bridge
cd asset-detection-bridge
```

(Tanpa git? Download ZIP dari halaman Releases → extract.)

## 3. Setup Otomatis (PowerShell Administrator)

```powershell
.\scripts\setup-bridge.ps1 -HostIP 192.168.1.30
```

Ganti `192.168.1.30` dengan IP host yang sebenarnya.

Script melakukan:
1. Detect IP LAN mesin ini
2. Buka firewall port **8765** (Private)
3. Cek AutoCAD via registry (semua versi)
4. `pip install -e lib/pdf-markup-core` + `pip install -e autocad-bridge`
5. Tulis `autocad-bridge/.env` (CORS mengarah ke host)
6. **BERHENTI dan minta Anda membuka DWG target di AutoCAD** → tekan Enter setelah open
7. Start `uvicorn bridge_main:app --host 0.0.0.0 --port 8765`

## 4. Verifikasi

```powershell
curl http://localhost:8765/health
```

Harus kembali (contoh):

```json
{"status":"ok","autocad_connected":true,"active_doc":"Plant-A.dwg"}
```

- `autocad_connected: false` → buka AutoCAD + DWG target, service auto-retry tiap request
  (tidak perlu restart bridge).

## 5. Pakai

1. Buka browser: `http://<IP-HOST>:3000/dwg-export`
2. Buat job → generate PDF → kalibrasi 3 titik → pilih reference text → **Execute**
3. Saat diminta, **klik 3 titik frame langsung di AutoCAD** (kiri-bawah → kanan-bawah → kiri-atas)
4. Tunggu status COMPLETED — DWG tersave otomatis.

## Kalau PowerShell Menolak Script

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Lalu ulangi step 3.
