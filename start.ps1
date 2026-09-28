<#
.SYNOPSIS
  Uygulamayı bu bilgisayarda tek komutla başlatır: PostgreSQL, migration'lar, frontend build'i
  ve backend (arayüz + API aynı adreste).

.EXAMPLE
  .\start.ps1                # http://localhost:8000 (Tailscale cihazlarından da erişilebilir)
  .\start.ps1 -SkipBuild     # frontend'i yeniden derlemeden başlat
  .\start.ps1 -Listen 127.0.0.1   # yalnızca bu bilgisayardan erişim
#>
param(
  [int]$Port = 8000,
  [string]$Listen = '0.0.0.0',
  [switch]$SkipBuild
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$backend = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$venv = Join-Path $backend '.venv\Scripts'

function Invoke-Step([string]$title, [scriptblock]$command) {
  Write-Host "==> $title" -ForegroundColor Cyan
  & $command
  if ($LASTEXITCODE -ne 0) { throw "$title başarısız oldu (çıkış kodu $LASTEXITCODE)." }
}

if (-not (Test-Path (Join-Path $backend '.env'))) {
  throw 'backend\.env bulunamadı. backend\.env.example dosyasını kopyalayıp GEMINI_API_KEY girin.'
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
  throw "Port $Port kullanımda. Çalışan eski sunucuyu kapatın ya da -Port ile başka bir port seçin."
}

# Docker Desktop may still be starting (e.g. when this runs at login).
Write-Host '==> Docker bekleniyor' -ForegroundColor Cyan
$deadline = (Get-Date).AddMinutes(3)
while ($true) {
  docker info *> $null
  if ($LASTEXITCODE -eq 0) { break }
  if ((Get-Date) -gt $deadline) { throw 'Docker çalışmıyor. Docker Desktop açık mı?' }
  Start-Sleep -Seconds 3
}

Push-Location $backend
try {
  Invoke-Step 'PostgreSQL başlatılıyor' { docker compose up -d --wait postgres }
  Invoke-Step 'Veritabanı güncelleniyor' { & (Join-Path $venv 'alembic.exe') upgrade head }
} finally { Pop-Location }

if (-not $SkipBuild) {
  Push-Location $frontend
  try {
    if (-not (Test-Path 'node_modules')) { Invoke-Step 'Frontend paketleri kuruluyor' { npm ci } }
    Invoke-Step 'Frontend derleniyor' { npm run build }
  } finally { Pop-Location }
}

$env:FRONTEND_DIST_DIR = Join-Path $frontend 'dist'
$env:ENVIRONMENT = 'production'
$env:DEBUG = 'false'

Write-Host ''
Write-Host "Hazır: http://localhost:$Port" -ForegroundColor Green
Write-Host 'Durdurmak için Ctrl+C.'
Write-Host ''

Push-Location $backend
try {
  & (Join-Path $venv 'uvicorn.exe') app.main:app --host $Listen --port $Port
} finally { Pop-Location }
