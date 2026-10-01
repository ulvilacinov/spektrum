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

# A click into a classic console window starts "QuickEdit" selection, which pauses every
# write to the window and so freezes the server at its next log line. Turn it off for this
# window only.
function Disable-QuickEdit {
  try {
    Add-Type -Namespace Spektrum -Name ConsoleMode -MemberDefinition @'
[DllImport("kernel32.dll")] public static extern IntPtr GetStdHandle(int handle);
[DllImport("kernel32.dll")] public static extern bool GetConsoleMode(IntPtr handle, out uint mode);
[DllImport("kernel32.dll")] public static extern bool SetConsoleMode(IntPtr handle, uint mode);
'@
    $inputHandle = [Spektrum.ConsoleMode]::GetStdHandle(-10)  # STD_INPUT_HANDLE
    $mode = [uint32]0
    if ([Spektrum.ConsoleMode]::GetConsoleMode($inputHandle, [ref]$mode)) {
      # Clear ENABLE_QUICK_EDIT_MODE (0x40); ENABLE_EXTENDED_FLAGS (0x80) makes it stick.
      [void][Spektrum.ConsoleMode]::SetConsoleMode($inputHandle, ($mode -band (-bnot 0x40)) -bor 0x80)
    }
  } catch {
    # Not a classic console (e.g. redirected output): nothing to do.
  }
}
Disable-QuickEdit

if (-not (Test-Path (Join-Path $backend '.env'))) {
  throw 'backend\.env bulunamadı. backend\.env.example dosyasını backend\.env olarak kopyalayın.'
}
# SECRET_KEY encrypts the users' AI API keys: generated once into backend\.env (never
# committed). Changing it later would make the saved keys unreadable.
Push-Location $backend
try {
  Invoke-Step 'SECRET_KEY kontrol ediliyor' { & (Join-Path $venv 'python.exe') -m app.cli ensure-secret-key }
} finally { Pop-Location }

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
  # Not fatal: only prints how to create an account or set a missing password.
  & (Join-Path $venv 'python.exe') -m app.cli check
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
  & (Join-Path $venv 'uvicorn.exe') app.main:app --host $Listen --port $Port --timeout-graceful-shutdown 5
} finally { Pop-Location }
