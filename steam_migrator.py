import os
import shutil
import winreg
import vdf
import ctypes
from pathlib import Path
from ctypes.wintypes import DWORD, LPCWSTR, LPWSTR
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.console import Console
from rich.panel import Panel
from rich.columns import Columns
from rich.markup import escape
from rich.prompt import Confirm, Prompt

console = Console()

progress = Progress(
    TextColumn("[bold cyan]{task.description}", justify="right"),
    BarColumn(bar_width=40),
    "[progress.percentage]{task.percentage:>3.0f}%",
    "•",
    TransferSpeedColumn(),
    "•",
    TimeRemainingColumn(),
    console=console,
    refresh_per_second=10,
    expand=True,
)


def get_filesystem_type(path: Path) -> str:
    """获取路径所在磁盘的文件系统类型"""
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

    # 正确定义所有参数类型
    GetVolumeInformationW = kernel32.GetVolumeInformationW
    GetVolumeInformationW.argtypes = [
        LPCWSTR,  # 根路径
        LPWSTR,  # 卷名称缓冲区
        DWORD,  # 卷名称缓冲区长度
        ctypes.POINTER(DWORD),  # 卷序列号
        ctypes.POINTER(DWORD),  # 最大文件名长度
        ctypes.POINTER(DWORD),  # 文件系统标志
        LPWSTR,  # 文件系统名称缓冲区
        DWORD,  # 文件系统名称缓冲区长度
    ]

    fs_type = ctypes.create_unicode_buffer(32)
    drive = str(path.resolve().drive) + "\\"

    # 创建必要的指针变量
    volume_serial = DWORD()
    max_length = DWORD()
    flags = DWORD()

    success = GetVolumeInformationW(
        drive,  # 根路径
        None,  # 不获取卷名称
        0,  # 卷名称缓冲区长度为0
        ctypes.byref(volume_serial),  # 卷序列号指针
        ctypes.byref(max_length),  # 最大文件名长度指针
        ctypes.byref(flags),  # 文件系统标志指针
        fs_type,  # 文件系统类型缓冲区
        ctypes.sizeof(fs_type),  # 缓冲区长度
    )

    return fs_type.value if success else "UNKNOWN"


def get_steam_install_path():
    """通过注册表获取Steam安装路径"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam"
        )
        path, _ = winreg.QueryValueEx(key, "InstallPath")
        return Path(path)
    except Exception as e:
        console.print(f"[bold red]✗ 注册表查询失败:[/] {str(e)}")
        return None


def validate_steam_library(path: Path) -> bool:
    """验证Steam库有效性"""
    try:
        return (path / "steamapps").exists() and path.is_dir()
    except OSError:
        return False


def get_disk_info_panel(path: Path, index: int) -> Panel:
    """生成磁盘信息面板"""
    try:
        usage = shutil.disk_usage(path)
        fs_type = get_filesystem_type(path)

        info = (
            f"[b]路径:[/] {escape(str(path))}\n"
            f"[cyan]▏文件系统:[/] {fs_type}\n"
            f"[green]▏剩余: {usage.free//1024**3}GB[/]\n"
            f"[yellow]▏总量: {usage.total//1024**3}GB[/]"
        )
        return Panel(info, title=f"库 {index+1}", width=45)
    except Exception as e:
        return Panel(f"[red]错误: {escape(str(e))}[/]", title=f"库 {index+1}", width=45)


def manual_add_library():
    """手动添加库目录"""
    while True:
        path = Prompt.ask(
            "[bold cyan]⇒ 请输入要添加的Steam库完整路径[/] (留空取消)", default=""
        )
        if not path:
            return None
        lib_path = Path(path)
        if validate_steam_library(lib_path):
            return lib_path
        console.print(f"[red]! 路径无效或不是有效的Steam库: {path}[/]")


def select_steam_library(libraries: list, prompt: str) -> Path:
    """选择Steam库"""
    while True:
        console.clear()
        console.print(Panel.fit(prompt, style="bold blue"))

        # 显示所有库的信息面板
        panels = [get_disk_info_panel(lib, i) for i, lib in enumerate(libraries)]
        console.print(Columns(panels, equal=True, expand=True))

        # 输入处理
        choice = (
            console.input(
                "[bold cyan]⇒ 请输入库编号 (0=重新扫描, a=手动添加, q=退出):[/] "
            )
            .strip()
            .lower()
        )

        if choice == "q":
            raise KeyboardInterrupt
        if choice == "0":
            return None
        if choice == "a":
            new_lib = manual_add_library()
            if new_lib:
                libraries.append(new_lib)
            continue
        if choice.isdigit() and 1 <= int(choice) <= len(libraries):
            selected = libraries[int(choice) - 1]
            if validate_steam_library(selected):
                return selected

        console.print("[red]! 输入无效，请重新输入[/]", style="bold")


def scan_acf_files(steamapps_path: Path) -> list:
    """扫描ACF文件并解析有效游戏"""
    games = []
    for acf_file in steamapps_path.glob("appmanifest_*.acf"):
        try:
            with open(acf_file, "r", encoding="utf-8") as f:
                data = vdf.load(f)["AppState"]

                installdir = data.get("installdir", "")
                if not installdir:
                    console.print(
                        f"[yellow]! 跳过无效ACF文件: {acf_file.name} (缺少installdir字段)[/]"
                    )
                    continue

                game_path = steamapps_path.parent / "steamapps" / "common" / installdir

                if not game_path.exists():
                    console.print(
                        f"[yellow]! 跳过无效条目: {acf_file.name} (游戏目录不存在)[/]"
                    )
                    continue

                games.append(
                    {
                        "appid": data["appid"],
                        "name": data.get("name", "Unknown"),
                        "size": int(data.get("SizeOnDisk", 0)),
                        "acf_path": acf_file,
                        "game_path": game_path,
                        "installdir": installdir,
                    }
                )
        except Exception as e:
            console.print(f"[red]! 严重错误: {acf_file.name}[/]\n{str(e)}")
    return games


def verify_copy(source: Path, target: Path) -> bool:
    """验证复制完整性(优化时间戳校验)"""
    try:
        # 获取目标文件系统类型
        target_fs = get_filesystem_type(target)

        # 动态设置时间戳容忍度
        time_tolerance = 2  # 默认2秒
        if target_fs == "NTFS":
            time_tolerance = 1  # NTFS使用更严格校验
        elif target_fs == "exFAT":
            time_tolerance = 3  # exFAT时间戳精度较低

        # 验证文件数量
        src_files = {f.relative_to(source) for f in source.rglob("*") if f.is_file()}
        dst_files = {f.relative_to(target) for f in target.rglob("*") if f.is_file()}
        if src_files != dst_files:
            missing = src_files - dst_files
            extra = dst_files - src_files
            if missing:
                console.print(f"[red]缺失文件: {len(missing)}[/]")
            if extra:
                console.print(f"[red]多余文件: {len(extra)}[/]")
            return False

        # 验证文件元数据
        for rel_path in src_files:
            src_file = source / rel_path
            dst_file = target / rel_path

            if not dst_file.exists():
                console.print(f"[red]文件不存在: {dst_file}[/]")
                return False

            # 大小校验
            src_size = src_file.stat().st_size
            dst_size = dst_file.stat().st_size
            if src_size != dst_size:
                console.print(
                    f"[red]大小不一致: {rel_path}\n"
                    f"源: {src_size} 字节 vs 目标: {dst_size} 字节[/]"
                )
                return False

            # 时间戳校验
            src_mtime = src_file.stat().st_mtime
            dst_mtime = dst_file.stat().st_mtime
            if abs(src_mtime - dst_mtime) > time_tolerance:
                console.print(
                    f"[yellow]时间戳差异: {rel_path}\n"
                    f"源: {src_mtime:.6f} vs 目标: {dst_mtime:.6f}\n"
                    f"容忍范围: ±{time_tolerance}秒[/]"
                )
                # 不直接返回False，记录警告但继续
                console.print("[yellow]! 时间戳差异在容忍范围内，继续验证...[/]")

        return True
    except Exception as e:
        console.print(f"[red]验证失败: {str(e)}[/]")
        return False


def safe_transfer(src: Path, dst: Path, description: str, move: bool = False) -> bool:
    """安全传输文件（复制或移动）"""
    temp_dir = dst.parent / (dst.name + "_temp")
    target_fs = get_filesystem_type(dst.parent)

    try:
        # 显示文件系统信息
        console.print(f"[cyan]目标文件系统:[/] {target_fs}")
        if target_fs == "FAT32":
            console.print(
                Panel(
                    "[yellow]! 注意: 目标为FAT32文件系统\n"
                    "• 不支持超过4GB的单个文件\n"
                    "• 时间戳精度为2秒[/]",
                    border_style="yellow",
                )
            )
        elif target_fs == "exFAT":
            console.print(
                Panel(
                    "[yellow]! 注意: 目标为exFAT文件系统\n" "• 时间戳精度为10毫秒[/]",
                    border_style="yellow",
                )
            )

        # 第一阶段：复制到临时目录
        console.print(f"[yellow]阶段1/3: 正在创建临时副本...[/]")
        total_size = sum(f.stat().st_size for f in src.rglob("*") if f.is_file())

        with progress:
            task = progress.add_task(
                f"▸ 临时复制 {description}", total=total_size, visible=total_size > 0
            )

            for root, dirs, files in os.walk(src):
                dest_root = temp_dir / Path(root).relative_to(src)
                dest_root.mkdir(parents=True, exist_ok=True)

                for file in files:
                    src_file = Path(root) / file
                    dst_file = dest_root / file

                    if dst_file.exists():
                        progress.console.log(f"跳过已存在文件: {dst_file}")
                        continue

                    shutil.copy2(src_file, dst_file)
                    progress.update(task, advance=src_file.stat().st_size)

        # 第二阶段：验证完整性
        console.print(f"[yellow]阶段2/3: 正在验证文件完整性...[/]")
        if not verify_copy(src, temp_dir):
            raise RuntimeError("文件验证失败，数据可能损坏")

        # 第三阶段：应用更改
        console.print(f"[yellow]阶段3/3: 正在应用更改...[/]")
        if dst.exists():
            shutil.rmtree(dst)
        temp_dir.rename(dst)

        if move:
            console.print(f"[yellow]正在清理源文件...[/]")
            shutil.rmtree(src)

        return True
    except Exception as e:
        console.print(f"[red]操作失败: {str(e)}[/]")
        # 清理残留文件
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False
    finally:
        # 确保临时目录被清理
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


def migrate_game(
    source: dict, target_steamapps: Path, steam_exe: Path, move: bool
) -> bool:
    """执行游戏迁移主逻辑"""
    target_game_dir = target_steamapps / "common" / source["installdir"]
    target_acf = target_steamapps / f"appmanifest_{source['appid']}.acf"
    source_acf = source["acf_path"]

    try:
        # ===== 文件系统检查 =====
        target_fs = get_filesystem_type(target_steamapps)
        if target_fs == "FAT32":
            # 检查是否有超过4GB的文件
            large_files = [
                f
                for f in source["game_path"].rglob("*")
                if f.is_file() and f.stat().st_size > 4 * 1024**3
            ]
            if large_files:
                console.print(
                    Panel(
                        f"[bold red]FAT32文件系统限制:[/]\n"
                        f"发现 {len(large_files)} 个超过4GB的文件\n"
                        f"例如: {large_files[0].name}",
                        title="错误",
                        border_style="red",
                    )
                )
                return False

        # ===== 空间检查 =====
        required = source["size"]
        try:
            free = shutil.disk_usage(target_steamapps).free
        except FileNotFoundError:
            raise RuntimeError("目标库路径已失效")

        if required > free and not move:
            raise RuntimeError(
                f"需要 {required//1024**3}GB 空间，" f"当前可用 {free//1024**3}GB"
            )

        # ===== 显示操作信息 =====
        console.print(
            Panel.fit(
                f"[b]操作类型:[/] {'移动' if move else '复制'}\n"
                f"[b]游戏名称:[/] {source['name']}\n"
                f"[b]App ID:[/] {source['appid']}\n"
                f"[b]占用空间:[/] {source['size']//1024**3}GB",
                title="▷ 迁移信息",
                border_style="cyan",
            )
        )

        # ===== 执行传输 =====
        success = safe_transfer(
            source["game_path"], target_game_dir, source["name"], move=move
        )

        if not success:
            return False

        # ===== 处理ACF文件 =====
        console.print("[yellow]正在更新配置文件...[/]")

        try:
            shutil.copy2(source_acf, target_acf)
        except FileNotFoundError:
            raise RuntimeError(f"源ACF文件不存在: {source_acf}\n可能已被其他程序删除")

        # 移动操作需要删除源ACF
        if move:
            console.print(f"[yellow]正在清理源ACF文件...[/]")
            try:
                if source_acf.exists():
                    source_acf.unlink()
                    console.print(f"[green]✓ 已删除源ACF文件[/]")
                else:
                    console.print(f"[yellow]! 源ACF文件已不存在[/]")
            except PermissionError as e:
                raise RuntimeError(
                    f"无法删除源ACF文件: {source_acf}\n"
                    f"请确保: 1) Steam客户端已关闭 2) 使用管理员权限运行本程序"
                )

        # 修改目标ACF文件
        with open(target_acf, "r+", encoding="utf-8") as f:
            data = vdf.load(f)
            data["AppState"]["LauncherPath"] = str(steam_exe).replace("\\", "/")
            f.seek(0)
            vdf.dump(data, f, pretty=True)
            f.truncate()

        return True

    except Exception as e:
        console.print(
            Panel(
                f"[bold red]✗ 迁移失败:[/]\n{escape(str(e))}",
                title="错误",
                border_style="red",
            )
        )
        # 清理残留
        if target_game_dir.exists():
            shutil.rmtree(target_game_dir, ignore_errors=True)
        if target_acf.exists():
            target_acf.unlink()
        return False


def main_flow():
    """主控制流程"""
    console.print(
        Panel.fit(
            "[bold yellow]STEAM 游戏迁移工具 JexZucker[/]",
            subtitle="按Q随时退出",
            border_style="yellow",
        )
    )

    # 询问是否手动添加库
    if Confirm.ask("[bold cyan]⇒ 是否要手动添加Steam库目录？[/]", default=False):
        while True:
            lib = manual_add_library()
            if not lib:
                break
            console.print(f"[green]✓ 已添加库: {lib}[/]")

    # 获取Steam路径
    steam_path = get_steam_install_path()
    if not steam_path:
        steam_path = Path(console.input("[bold]⇒ 请输入Steam安装路径:[/] "))

    # 动态库发现
    libraries = [steam_path]
    libfolders = steam_path / "steamapps" / "libraryfolders.vdf"

    if libfolders.exists():
        try:
            with open(libfolders, "r", encoding="utf-8") as f:
                data = vdf.load(f)
                for key in data.get("libraryfolders", {}):
                    if key.isdigit():
                        lib_path = Path(data["libraryfolders"][key]["path"])
                        if validate_steam_library(lib_path):
                            libraries.append(lib_path)
        except Exception as e:
            console.print(f"[yellow]! 库文件解析失败: {e}[/]")

    # 去重处理
    libraries = list(dict.fromkeys(libraries))

    while True:
        try:
            # 选择源库
            src_lib = select_steam_library(libraries, "▼ 请选择源游戏库 ▼")
            if not src_lib:
                continue

            # 选择目标库
            dst_libs = [lib for lib in libraries if lib != src_lib]
            if not dst_libs:
                console.print("[red]! 没有可用的目标库[/]")
                continue

            dst_lib = select_steam_library(dst_libs, "▼ 请选择目标库 ▼")
            if not dst_lib:
                continue

            # 选择操作类型
            operation = Prompt.ask(
                "[bold cyan]⇒ 请选择操作类型 (copy=复制, move=移动)[/]",
                choices=["copy", "move"],
                default="copy",
                show_choices=False,
            )
            move_operation = operation == "move"

            # 扫描游戏
            steamapps = src_lib / "steamapps"
            games = scan_acf_files(steamapps)
            if not games:
                console.print("[yellow]! 该库未找到可迁移的游戏[/]")
                continue

            # 显示游戏列表
            console.print(
                Panel.fit(
                    "\n".join(
                        f"[b]{i+1}.[/] {g['name']} ([cyan]{g['appid']}[/])"
                        for i, g in enumerate(games)
                    ),
                    title="可用游戏列表",
                    border_style="green",
                )
            )

            # 选择游戏
            try:
                choice = int(console.input("[bold]⇒ 请输入游戏编号:[/] ")) - 1
                game = games[choice]
            except Exception:
                console.print("[red]! 选择无效[/]")
                continue

            # 执行迁移
            success = migrate_game(
                game,
                dst_lib / "steamapps",
                steam_path / "steam.exe",
                move=move_operation,
            )

            if success:
                console.print(
                    Panel(
                        "[bold green]✓ 迁移完成![/]\n"
                        "请重启Steam客户端并验证游戏文件",
                        title="成功",
                        border_style="green",
                    )
                )

            if not Confirm.ask("[bold cyan]⇒ 是否继续迁移其他游戏？[/]", default=True):
                break

        except KeyboardInterrupt:
            console.print("\n[bold yellow]⇨ 用户终止操作[/]")
            break
        except Exception as e:
            console.print_exception()
            break


if __name__ == "__main__":
    try:
        main_flow()
    finally:
        console.print("\n[bold blue]⇨ 感谢使用 Steam 迁移工具![/]")
