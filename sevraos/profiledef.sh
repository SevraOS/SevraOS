#!/usr/bin/env bash
# shellcheck disable=SC2034
iso_name="sevraos"
iso_label="SEVRAOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="Sevra Technologies <https://sevra.ai>"
iso_application="SevraOS Healthcare Platform"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="sevra"
buildmodes=('iso')
bootmodes=(
    'bios.syslinux'
    'uefi.systemd-boot'
)
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=(
    '-comp' 'zstd'
    '-Xcompression-level' '19'
)
bootstrap_tarball_compression=(
    'zstd'
    '-c'
    '-T0'
    '--auto-threads=logical'
    '--long'
    '-19'
)
file_permissions=(
    ["/etc/shadow"]="0:0:400"
    ["/root"]="0:0:750"
    ["/root/.automated_script.sh"]="0:0:755"
    ["/root/.gnupg"]="0:0:700"
    ["/usr/local/bin/choose-mirror"]="0:0:755"
    ["/usr/local/bin/Installation_guide"]="0:0:755"
    ["/usr/local/bin/livecd-sound"]="0:0:755"
    ["/usr/local/bin/sevra-installer"]="0:0:755"
    ["/usr/local/bin/sevra-start"]="0:0:755"
    ["/usr/local/bin/sevra-monitor"]="0:0:755"
    ["/usr/local/bin/sevra-recovery"]="0:0:755"
    ["/opt/sevra"]="0:0:755"
    ["/opt/sevra/bin"]="0:0:755"
    ["/opt/sevra/config"]="0:0:700"
    ["/opt/sevra/services"]="0:0:750"
    ["/opt/sevra/logs"]="0:0:750"
    ["/opt/sevra/patient-data"]="0:0:700"
    ["/opt/sevra/telemetry"]="0:0:700"
    ["/opt/sevra/helios"]="0:0:750"
    ["/opt/sevra/adapters"]="0:0:755"
    ["/opt/sevra/collectors"]="0:0:755"
    ["/opt/sevra/configs"]="0:0:700"
    ["/opt/sevra/storage"]="0:0:750"
    ["/opt/sevra/recovery"]="0:0:755"
    ["/opt/sevra/recovery/recovery.sh"]="0:0:755"
    ["/opt/sevra/recovery/diagnostics/system-info.sh"]="0:0:755"
    ["/opt/sevra/recovery/logs/collect-logs.sh"]="0:0:755"
    ["/opt/sevra/recovery/repair/disk-check.sh"]="0:0:755"
    ["/etc/sevra"]="0:0:700"
    ["/etc/systemd/system"]="0:0:755"
)
