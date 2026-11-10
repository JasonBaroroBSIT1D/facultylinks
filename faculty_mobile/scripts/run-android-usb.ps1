# Physical Android over USB (no Wi‑Fi to PC needed).
# Requires: USB debugging on, Flask on PC port 5000 (python run.py in backend).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Get-Command adb -ErrorAction SilentlyContinue)) {
  Write-Error "adb not found. Install Android platform-tools or use Android Studio SDK."
}

$dev = adb devices | Select-String "device$"
if (-not $dev) {
  Write-Error "No Android device attached. Enable USB debugging and approve the PC."
}

adb reverse tcp:5000 tcp:5000
Write-Host "adb reverse: phone 127.0.0.1:5000 -> PC :5000"

flutter run --no-enable-impeller --dart-define-from-file=config/dart_defines.local.json @args
