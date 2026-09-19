<#
.SYNOPSIS
    Setup otomatis mesin BRIDGE (Windows + AutoCAD) untuk akses LAN.
.DESCRIPTION
    - Auto-detect IP LAN (DHCP-friendly)
    - Buka firewall port 8765 (Private)
    - Cek AutoCAD terinstall (universal, semua versi via registry)
    - Install pdf-markup-core + autocad-bridge (pip editable)
    - Generate autocad-bridge/.env (CORS ke host)
    - Alert: DWG target harus sudah open di AutoCAD
    - Start bridge service bind 0.0.0.0:8765
    Dijalankan dari repo root sebagai Administrator.
.PARAMETER HostIP
    WAJIB. IP LAN mesin host (dari output setup-host.ps1).
.EXAMPLE
    .\scripts\setup-bridge.ps1 -HostIP 192.168.1.30
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$HostIP
)

$ErrorActionPreference = "Stop"

# ── 0. Admin check ──────────────────────────────────────────────────────────
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "Jalankan script ini sebagai Administrator (klik kanan > Run as Administrator)." -ForegroundColor Red
    exit 1
}

function Step($msg) { Write-Host "`n== $msg ==" -ForegroundColor Cyan }

# ── 1. Repo root check ──────────────────────────────────────────────────────
$repoRoot = Split-Path -Parent $PSScriptRoot
if (-not (Test-Path (Join-Path $repoRoot "autocad-bridge"))) {
    Write-Host "Folder autocad-bridge tidak ditemukan. Jalankan dari repo root." -ForegroundColor Red
    exit 1
}
Set-Location $repoRoot

# ── 2. Auto-detect LAN IP (DHCP) ────────────────────────────────────────────
Step "Detect IP LAN"
$ip = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
    Where-Object {
        $_.IPAddress -notmatch '^(127\.|169\.254\.)' -and
        $_.PrefixOrigin -ne "WellKnown" -and
        $_.AddressState -eq "Preferred"
    } |
    Sort-Object { if ($_.InterfaceAlias -like "*Ethernet*") { 0 } else { 1 } } |
    Select-Object -First 1 -ExpandProperty IPAddress

if (-not $ip) {
    Write-Host "Gagal detect IP LAN. Pastikan terhubung ke jaringan." -ForegroundColor Red
    exit 1
}
Write-Host "IP LAN mesin ini (bridge): $ip" -ForegroundColor Green
Write-Host "IP LAN mesin host        : $HostIP" -ForegroundColor Green

# ── 3. Firewall (idempotent) ────────────────────────────────────────────────
Step "Firewall (port 8765)"
$ruleName = "Asset-Detection AutoCAD Bridge (8765)"
if (Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue) {
    Write-Host "  [OK] Rule '$ruleName' sudah ada" -ForegroundColor DarkGray
} else {
    New-NetFirewallRule -DisplayName $ruleName -Direction Inbound `
        -LocalPort 8765 -Protocol TCP -Action Allow -Profile Private | Out-Null
    Write-Host "  [+] Rule '$ruleName' dibuat" -ForegroundColor Green
}

# ── 4. Cek AutoCAD (universal — semua versi via registry) ───────────────────
Step "Cek AutoCAD"
$acadKeys = @(
    "HKLM:\SOFTWARE\Autodesk\AutoCAD",
    "HKLM:\SOFTWARE\WOW6432Node\Autodesk\AutoCAD"
)
$found = @()
foreach ($k in $acadKeys) {
    if (Test-Path $k) {
        Get-ChildItem $k -ErrorAction SilentlyContinue | ForEach-Object {
            Get-ChildItem $_.PSPath -ErrorAction SilentlyContinue | ForEach-Object {
                $found += "$($_.PSChildName)"
            }
        }
    }
}
if ($found.Count -gt 0) {
    Write-Host "  [OK] AutoCAD terdeteksi: $($found -join ', ')" -ForegroundColor Green
} else {
    Write-Host "  [!] AutoCAD TIDAK terdeteksi di registry." -ForegroundColor Yellow
    Write-Host "      Bridge butuh AutoCAD terinstall. Lanjut anyway? (Enter=lanjut, Ctrl+C=batal)" -ForegroundColor Yellow
    Read-Host "      Tekan Enter untuk lanjut"
}

# ── 5. Python check ─────────────────────────────────────────────────────────
Step "Cek Python"
try {
    $pyVer = python --version 2>&1
    Write-Host "  [OK] $pyVer" -ForegroundColor DarkGray
} catch {
    Write-Host "  Python tidak ditemukan di PATH. Install Python 3.10+ dari python.org" -ForegroundColor Red
    Write-Host "  (centang 'Add python.exe to PATH' saat install), lalu jalankan script ini lagi." -ForegroundColor Red
    exit 1
}

# ── 6. Install Python packages ──────────────────────────────────────────────
Step "Install Python packages"
$coreDir = Join-Path $repoRoot "lib\pdf-markup-core"
$bridgeDir = Join-Path $repoRoot "autocad-bridge"
Write-Host "  Installing pdf-markup-core..."
pip install -e $coreDir
Write-Host "  Installing autocad-bridge..."
pip install -e $bridgeDir

# ── 7. autocad-bridge/.env (CORS ke host) ───────────────────────────────────
Step "Konfigurasi bridge (.env)"
$envFile = Join-Path $bridgeDir ".env"
$envExample = Join-Path $bridgeDir ".env.example"
$envMap = @{}
if (Test-Path $envExample) {
    Get-Content $envExample | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $k, $v = $_.Split('=', 2)
        $envMap[$k.Trim()] = $v.Trim()
    }
}
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^\s*#' -or $_ -notmatch '=') { return }
        $k, $v = $_.Split('=', 2)
        if ($k.Trim() -ne "CORS_ALLOW_ORIGINS") { $envMap[$k.Trim()] = $v.Trim() }
    }
}
$envMap["CORS_ALLOW_ORIGINS"] = "http://${HostIP}:3000"
$envMap["AUTOCAD_BRIDGE_PORT"] = "8765"
($envMap.Keys | Sort-Object | ForEach-Object { "$_=$($envMap[$_])" }) |
    Set-Content $envFile -Encoding UTF8
Write-Host "  [OK] .env ditulis (CORS=http://${HostIP}:3000)" -ForegroundColor Green

# ── 8. Cek port 8765 ────────────────────────────────────────────────────────
$inUse = Get-NetTCPConnection -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
if ($inUse) {
    Write-Host ""
    Write-Host "Port 8765 sudah dipakai (PID $($inUse.OwningProcess)). Matikan dulu proses tersebut." -ForegroundColor Red
    exit 1
}

# ── 9. Alert DWG ────────────────────────────────────────────────────────────
Step "DWG Target"
Write-Host ""
Write-Host "  +==============================================================+" -ForegroundColor Yellow
Write-Host "  |  BUKA AUTOCAD + FILE DWG TARGET SEKARANG SEBELUM LANJUT!      |" -ForegroundColor Yellow
Write-Host "  |  Bridge insert langsung ke dokumen AKTIF di AutoCAD.          |" -ForegroundColor Yellow
Write-Host "  +==============================================================+" -ForegroundColor Yellow
Write-Host ""
Read-Host "  Tekan Enter setelah DWG target sudah terbuka di AutoCAD"

# ── 10. Start bridge ────────────────────────────────────────────────────────
Step "Start bridge (0.0.0.0:8765)"
Write-Host ""
Write-Host "  Health check dari host: http://${ip}:8765/health" -ForegroundColor Green
Write-Host "  Sampaikan IP ini ke host untuk AUTOCAD_BRIDGE_URL." -ForegroundColor Green
Write-Host "  Tekan Ctrl+C untuk berhenti." -ForegroundColor Yellow
Write-Host ""
Set-Location (Join-Path $bridgeDir "src")
uvicorn bridge_main:app --host 0.0.0.0 --port 8765
