#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════
# SevraOS Build Profile — QEMU Virtual Machine Launcher
# ═══════════════════════════════════════════════════════════════
set -euo pipefail

CDPATH="" cd -- "$(dirname -- "$0")/.."

ISO_PATH="$(find sevraos/out -maxdepth 1 -type f -name 'sevraos-*-x86_64.iso' -printf '%T@ %p\n' 2>/dev/null | sort -nr | awk 'NR == 1 {print $2}')"

if [ -z "${ISO_PATH}" ] || [ ! -f "$ISO_PATH" ]; then
    echo -e "\033[0;31m❌ Error: compiled SevraOS live ISO image not found!\033[0m"
    echo -e "\033[0;33mPlease build the ISO first by running the mkarchiso compilation guide.\033[0m"
    exit 1
fi

if ! command -v qemu-system-x86_64 > /dev/null; then
    echo -e "\033[0;31m❌ Error: QEMU (qemu-system-x86_64) is not installed on this system!\033[0m"
    echo -e "\033[0;33mTo install QEMU:\033[0m"
    echo -e "  Ubuntu/Debian:  sudo apt install qemu-system-x86 qemu-utils"
    echo -e "  Arch Linux:     sudo pacman -S qemu-desktop"
    echo -e "  macOS:          brew install qemu"
    exit 1
fi

echo -e "\033[0;32m💿 Launching SevraOS Kiosk OS virtually in QEMU...\033[0m"
echo -e "\033[0;36mImage: $ISO_PATH\033[0m"

# Launch QEMU with KVM acceleration on Linux if available, or HVF on macOS, otherwise TCG
ACCEL="tcg"
if [ "$(uname)" = "Linux" ] && [ -e /dev/kvm ]; then
    ACCEL="kvm"
elif [ "$(uname)" = "Darwin" ]; then
    ACCEL="hvf"
fi

qemu-system-x86_64 -m 4096 -accel "$ACCEL" -cdrom "$ISO_PATH" -boot d -rtc base=localtime -net nic -net user
