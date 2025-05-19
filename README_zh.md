# Steam 游戏迁移工具

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Windows Only](https://img.shields.io/badge/platform-Windows-lightgrey)](https://www.microsoft.com/windows)

简单的 Steam 游戏迁移工具，支持跨磁盘/跨文件系统操作，提供预编译二进制版本和 Python 源码版本。

## 功能特性

- **智能库检测** - 自动扫描注册表和配置文件中的 Steam 库位置
- **双模式操作** - 支持安全复制或直接移动游戏文件
- **实时进度监控** - 可视化传输进度与剩余时间预测
- **数据完整性保障** - 三重校验机制(文件大小、时间戳、内容对比)
- **跨文件系统支持** - 完美兼容 NTFS/FAT32/exFAT 格式
- **自动配置更新** - 智能维护 Steam 库配置文件

## 获取方式

### 预编译版本

提供通过 Cython 编译的独立可执行文件：

1. 访问 [Release 页面](https://github.com/Zucker-jex/SteamMigrator/releases) 下载最新版本
2. 解压后直接运行 `SteamMigrator.exe`

### 源码版本

要求 Python 3.7+环境：

```bash
pip install vdf rich
```

## 使用指南

1. **关闭 Steam 客户端**
2. **运行程序**

```bash
# EXE版本
SteamMigrator.exe

# 源码版本
python steam_migrator.py
```

3. 按提示操作：
   - 选择源游戏库
   - 选择目标存储位置
   - 选择复制/移动模式
   - 选择要迁移的游戏

## 编译为 EXE 文件

### 准备工具

1. 安装 Cython：`pip install cython`
2. 安装 MinGW-w64 (勾选添加 PATH 环境变量)
3. 确认 Python 安装路径 (示例中使用 Python3.11)

### 编译步骤

```bash
cython --embed -o steam_migrator.c steam_migrator.py
gcc steam_migrator.c -o SteamMigrator.exe -DMS_WIN64 -IC:\Python路径\include -LC:\Python路径\libs -lpython311 -municode
```

_替换说明：_

- `C:\Python路径` 替换为实际 Python 安装路径
  - 典型路径：`C:\Users\你的用户名\AppData\Local\Programs\Python\Python311`
- 确保`python311.dll`存在于系统 PATH 或 exe 同级目录

## 注意事项

- 确保目标磁盘有充足空间（建议预留 10%冗余空间）
- FAT32 文件系统不支持超过 4GB 的单个文件
- 建议优先使用 NTFS 格式以获得最佳兼容性
- 移动操作会删除源文件，建议先进行测试性复制
- EXE 版本可能需要手动添加杀毒软件白名单

## 常见问题

**Q: 为什么需要管理员权限？**
A: 需要访问注册表和系统保护目录，普通权限可能导致操作失败

**Q: 迁移后游戏无法启动？**
A: 请重启 Steam 客户端并在游戏属性中执行"验证文件完整性"

**Q: 支持 Linux 系统吗？**
A: 仅支持 Windows 系统

---

> 注意：操作前建议备份重要数据。开发者不对因不当操作导致的数据丢失负责。
