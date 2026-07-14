# SevraOS Build Profile (Archiso)

This directory contains the custom build profile config for compiling the bootable **SevraOS** live Linux distribution. It utilizes the Arch Linux `archiso` framework. It represents the operating system base of the wider [Sevra Healthcare Operating Ecosystem](file:///c:/Users/ThePC/SevraOS/README.md).

## 🚀 Key Specifications

- **Kernel**: Real-Time kernel (`linux-rt`) optimized for ultra-low latency patient monitoring operations.
- **Desktop Environment**: KDE Plasma with SDDM display manager.
- **Autostart Kiosk UI**: SDDM is configured to automatically log in the `severa` user, launching the KDE desktop, which triggers Firefox in kiosk mode showing the patient terminal frontend.
- **Edge Telemetry Application**: Integrated [FastAPI Edge Backend](file:///c:/Users/ThePC/SevraOS/backend/README.md) served as a background systemd service.

## 📁 Completed OS Overlay Integrations

1. **Service Startup**: [sevra-backend.service](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/etc/systemd/system/sevra-backend.service) is enabled on boot to run the FastAPI telemetry backend.
2. **Kiosk Autologin**: [autologin.conf](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/etc/sddm.conf.d/autologin.conf) automatically signs in the `severa` user on boot.
3. **Session Start**: [sevra-start](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/usr/local/bin/sevra-start) script waits for FastAPI initialization and loads the frontend dashboard in fullscreen kiosk mode.
4. **Desktop Trigger**: [sevra-autostart.desktop](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/etc/xdg/autostart/sevra-autostart.desktop) launches the kiosk script on KDE session startup.

## 📁 Profile Directory Structure

```text
sevraos/
├── airootfs/            # Filesystem overlay copied to the live system root
│   ├── etc/             # Config files (sddm configurations, systemd services, hostnames)
│   ├── opt/sevra/       # Emplaced web client (frontend) and edge backend server
│   └── usr/local/bin/   # Live system command wrappers (sevra-start kiosk script)
├── efiboot/             # UEFI systemd-boot configuration settings
├── grub/                # GRUB bootloader configuration files
├── syslinux/            # BIOS bootloader configuration files
├── packages.x86_64      # Official packages list to install on the ISO image
├── bootstrap_packages   # Packages to compile the bootstrap image
├── pacman.conf          # Package manager database configurations
├── profiledef.sh        # Profile settings, ISO labels, and file permissions map
└── pkgs                 # Package listing overview
```

Relevant files:
- 📦 **Packages list**: [packages.x86_64](file:///c:/Users/ThePC/SevraOS/sevraos/packages.x86_64)
- ⚙️ **ISO Config**: [profiledef.sh](file:///c:/Users/ThePC/SevraOS/sevraos/profiledef.sh)
- 🖥️ **Embedded Backend**: [airootfs/opt/sevra/backend/](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/backend/README.md)
- 🎨 **Embedded Frontend**: [airootfs/opt/sevra/frontend/](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/frontend/README.md)
- 🛡️ **Recovery Tools**: [airootfs/opt/sevra/recovery/](file:///c:/Users/ThePC/SevraOS/sevraos/airootfs/opt/sevra/recovery/README.md)

## 🛠️ Compilation & ISO Build

To build the SevraOS live ISO image, you must have an active Arch Linux build system.

1. **Install the Archiso toolkit**:
   ```bash
   sudo pacman -S archiso
   ```
2. **Compile the ISO**:
   ```bash
   sudo mkarchiso -v -w ./work -o ./out ./
   ```

*Note: Build steps must be run as root to permit the tool to build mounting structures and set exact filesystem owners/permissions.*
