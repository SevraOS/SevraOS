# Sevra Recovery Environment

The Sevra Recovery Environment provides tools and workflows for system diagnostics, repair, backup operations and recovery logging. It is integrated into the [SevraOS Build Profile](file:///c:/Users/ThePC/SevraOS/sevraos/README.md).

## 🛠️ Recovery Script Entrypoint

The main execution script is [recovery.sh](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/recovery.sh).

## 📁 Directory Structure

- 📊 **[diagnostics/](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/diagnostics/)**: Contains live diagnosis utilities such as [system-info.sh](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/diagnostics/system-info.sh).
- 🔧 **[repair/](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/repair/)**: Disk and partition repair tools such as [disk-check.sh](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/repair/disk-check.sh).
- 💾 **[backup/](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/backup/)**: Backup and restore operations storage.
- 📝 **[logs/](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/logs/)**: Live logger dumps and troubleshooting records compiled by [collect-logs.sh](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/logs/collect-logs.sh).

Future versions will include advanced automated recovery workflows and maintenance tooling.
