#!/usr/bin/env bash
set -euo pipefail

pacman -Sy --noconfirm archiso

rm -rf /tmp/sevraos-profile /tmp/sevraos-work
mkdir -p /tmp/sevraos-profile
cp -a \
    /build/sevraos/airootfs \
    /build/sevraos/efiboot \
    /build/sevraos/grub \
    /build/sevraos/syslinux \
    /build/sevraos/bootstrap_packages \
    /build/sevraos/packages.x86_64 \
    /build/sevraos/pacman.conf \
    /build/sevraos/pkgs \
    /build/sevraos/profiledef.sh \
    /tmp/sevraos-profile/

cd /tmp/sevraos-profile/airootfs/etc/systemd/system
find . -type f \( -path "./*.wants/*" -o -path "./*.requires/*" \) |
while read -r file; do
    target="$(cat "$file")"
    case "$target" in
        ../*|/usr/*)
            rm -f "$file"
            ln -s "$target" "$file"
            ;;
    esac
done

mkarchiso -v -w /tmp/sevraos-work -o /out /tmp/sevraos-profile
