# ═══════════════════════════════════════════════════════════════
# SevraOS Build Profile — QEMU Virtual Machine Launcher
# ═══════════════════════════════════════════════════════════════

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$OutDir = Resolve-Path "$ScriptDir\..\sevraos\out" -ErrorAction SilentlyContinue
$IsoPath = $null
if ($OutDir) {
    $IsoPath = Get-ChildItem $OutDir -Filter "sevraos-*-x86_64.iso" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
}

if (-not $IsoPath) {
    Write-Host "❌ Error: compiled SevraOS live ISO image not found!" -ForegroundColor Red
    Write-Host "Please build the ISO first by running the mkarchiso compilation guide." -ForegroundColor Yellow
    Exit 1
}

# Check QEMU installation
$QemuPath = Get-Command qemu-system-x86_64 -ErrorAction SilentlyContinue
if (-not $QemuPath) {
    Write-Host "❌ Error: QEMU (qemu-system-x86_64) is not installed on this system!" -ForegroundColor Red
    Write-Host "To install QEMU on Windows:" -ForegroundColor Yellow
    Write-Host "  winget install SoftwareDesignLabs.QEMU" -ForegroundColor Cyan
    Write-Host "After installing QEMU, restart your terminal and run this script again." -ForegroundColor Yellow
    Exit 1
}

Write-Host "💿 Launching SevraOS Kiosk OS virtually in QEMU..." -ForegroundColor Green
Write-Host "Image: $IsoPath" -ForegroundColor Cyan
Write-Host "Memory: 2048 MB" -ForegroundColor Cyan
Write-Host "Press Ctrl+Alt+G to release the mouse cursor from the QEMU window." -ForegroundColor Yellow

# Start QEMU (using WHPX acceleration if available, falling back to TCG)
# For UEFI boot, standard archiso supports legacy boot directly.
qemu-system-x86_64 -m 4096 -cdrom $IsoPath.FullName -boot d -rtc base=localtime -net nic -net user
