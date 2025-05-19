[中文](README_zh.md)

# Steam Game Migration Tool

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)  
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)  
[![Windows Only](https://img.shields.io/badge/platform-Windows-lightgrey)](https://www.microsoft.com/windows)

A simple Steam game migration tool supporting cross-disk/cross-file system operations, offering both precompiled binaries and Python source code versions.

## Features

- **Intelligent Library Detection** - Automatically scans Steam library locations from registry and config files
- **Dual-mode Operation** - Supports safe copy or direct move of game files
- **Real-time Progress Monitoring** - Visual transfer progress with remaining time estimation
- **Data Integrity Assurance** - Triple verification mechanism (file size, timestamp, content comparison)
- **Cross-file System Support** - Full compatibility with NTFS/FAT32/exFAT formats
- **Automatic Configuration Update** - Smart maintenance of Steam library config files

## Download

### Precompiled Version

Standalone executable compiled with Cython:

1. Visit [Release Page](https://github.com/Zucker-jex/SteamMigrator/releases) to download the latest version
2. Run `SteamMigrator.exe` directly after extraction

### Source Code Version

Requires Python 3.7+ environment:

```bash
pip install vdf rich
```

## Usage Guide

1. **Close Steam Client**
2. **Run the Program**

```bash
# EXE version
SteamMigrator.exe

# Source code version
python steam_migrator.py
```

3. Follow the prompts:
   - Select source game library
   - Choose target storage location
   - Select copy/move mode
   - Choose games to migrate

## Compiling to EXE

### Prerequisites

1. Install Cython: `pip install cython`
2. Install MinGW-w64 (check "Add to PATH" during installation)
3. Confirm Python installation path (example uses Python3.11)

### Compilation Steps

```bash
cython --embed -o steam_migrator.c steam_migrator.py
gcc steam_migrator.c -o SteamMigrator.exe -DMS_WIN64 -IC:\PythonPath\include -LC:\PythonPath\libs -lpython311 -municode
```

_Replacements:_

- `C:\PythonPath` with actual Python installation path
  - Typical path: `C:\Users\YourUsername\AppData\Local\Programs\Python\Python311`
- Ensure `python311.dll` exists in system PATH or the same directory as the EXE

## Notes

- Ensure target disk has sufficient space (recommended 10% free space)
- FAT32 file system doesn't support single files larger than 4GB
- NTFS format recommended for optimal compatibility
- Move operation will delete source files - perform test copy first
- EXE version may require manual antivirus whitelisting

## FAQ

**Q: Why admin privileges required?**  
A: Necessary for accessing registry and system-protected directories

**Q: Games won't launch after migration?**  
A: Restart Steam client and "Verify File Integrity" in game properties

**Q: Linux support?**  
A: Windows only

---

> Note: Backup critical data before operation. The developer is not responsible for data loss caused by improper operations.
