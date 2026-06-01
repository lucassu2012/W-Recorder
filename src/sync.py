"""云同步：自动探测多种网盘客户端，把日报写入其同步目录。

核心思路：
- "没有 OneDrive" 的用户往往有别的网盘（坚果云 / Dropbox / Google Drive / iCloud / Box），
  它们的工作方式和 OneDrive 一致——一个本地文件夹被客户端自动同步到云。
- 因此把探测从"只认 OneDrive"扩展成"认一串常见网盘"，零配置覆盖大多数人。
- 仍然提供 CUSTOM_SYNC_DIR（用户手动指定任意已同步目录）与本地兜底。

解析优先级（高 → 低）：
  1. config.CUSTOM_SYNC_DIR     用户手动指定（最高优先级）
  2. config.CLOUD_TARGET 指定的具体 provider（如 'dropbox'）
  3. 'auto'：依次探测 OneDrive → 坚果云 → Dropbox → Google Drive → iCloud → Box
  4. 本地 %LOCALAPPDATA%\\W-Recorder\\reports（永远可用兜底）
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import string
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from . import config

log = logging.getLogger(__name__)


@dataclass
class CloudTarget:
    folder: Path
    provider: str           # onedrive/nutstore/dropbox/googledrive/icloud/box/custom/local
    is_cloud: bool
    note: str


def _home() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home())))


def _first_writable(paths: list) -> Path | None:
    """返回第一个存在且可写的目录。"""
    for p in paths:
        if not p:
            continue
        try:
            pp = Path(p)
            if pp.is_dir() and os.access(pp, os.W_OK):
                return pp
        except OSError:
            continue
    return None


def _fixed_drive_letters() -> list[str]:
    """枚举本机"固定磁盘"盘符（跳过可移动 / 光驱，避免触发插盘提示）。"""
    try:
        import ctypes
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        DRIVE_FIXED = 3
        letters = []
        for i in range(26):
            if bitmask & (1 << i):
                letter = f"{string.ascii_uppercase[i]}:\\"
                if ctypes.windll.kernel32.GetDriveTypeW(letter) == DRIVE_FIXED:
                    letters.append(string.ascii_uppercase[i])
        return letters
    except Exception:
        return []


# ---------- 各网盘探测 ----------
def detect_onedrive_root() -> Path | None:
    home = _home()
    return _first_writable([
        os.environ.get("OneDriveCommercial"),
        os.environ.get("OneDriveConsumer"),
        os.environ.get("OneDrive"),
        home / "OneDrive",
        home / "OneDrive - Personal",
    ])


def detect_nutstore_root() -> Path | None:
    """坚果云：默认同步目录通常是 %USERPROFILE%\\Nutstore\\我的坚果云。"""
    home = _home()
    return _first_writable([
        home / "Nutstore" / "我的坚果云",
        home / "Nutstore",
        home / "我的坚果云",
    ])


def detect_dropbox_root() -> Path | None:
    """Dropbox：优先解析 info.json（最可靠），回落到默认路径。"""
    for env in ("APPDATA", "LOCALAPPDATA"):
        base = os.environ.get(env)
        if not base:
            continue
        info = Path(base) / "Dropbox" / "info.json"
        if info.is_file():
            try:
                data = json.loads(info.read_text(encoding="utf-8"))
                for key in ("personal", "business"):
                    node = data.get(key) or {}
                    p = node.get("path")
                    if p and Path(p).is_dir():
                        return Path(p)
            except Exception as exc:
                log.debug("解析 Dropbox info.json 失败：%s", exc)
    return _first_writable([_home() / "Dropbox"])


def detect_googledrive_root() -> Path | None:
    """Google Drive：旧版在 ~/Google Drive；新版 Drive for desktop 挂成虚拟盘 X:\\My Drive。"""
    home = _home()
    candidates = [
        home / "Google Drive" / "My Drive",
        home / "Google Drive",
    ]
    # 新版：扫描固定盘符下的 "My Drive"
    for letter in _fixed_drive_letters():
        candidates.append(Path(f"{letter}:\\My Drive"))
    return _first_writable(candidates)


def detect_icloud_root() -> Path | None:
    home = _home()
    return _first_writable([
        home / "iCloudDrive",
        home / "iCloud Drive",
    ])


def detect_box_root() -> Path | None:
    home = _home()
    return _first_writable([
        home / "Box",
        home / "Box Sync",
    ])


# provider 名 → 探测函数 + 中文显示名
_DETECTORS: dict[str, tuple] = {
    "onedrive":    (detect_onedrive_root,   "OneDrive"),
    "nutstore":    (detect_nutstore_root,   "坚果云"),
    "dropbox":     (detect_dropbox_root,    "Dropbox"),
    "googledrive": (detect_googledrive_root, "Google Drive"),
    "icloud":      (detect_icloud_root,     "iCloud Drive"),
    "box":         (detect_box_root,        "Box"),
}

# auto 模式探测顺序
_AUTO_CHAIN = ["onedrive", "nutstore", "dropbox", "googledrive", "icloud", "box"]


def detect_all() -> list[tuple[str, str, Path]]:
    """返回所有探测到的网盘 [(provider, 显示名, root), ...]，用于诊断 / --where。"""
    found = []
    for name in _AUTO_CHAIN:
        fn, label = _DETECTORS[name]
        root = fn()
        if root:
            found.append((name, label, root))
    return found


# ---------- 解析最终目标 ----------
def _make_cloud(provider: str, label: str, root: Path) -> CloudTarget:
    folder = root / config.CLOUD_SUBDIR
    folder.mkdir(parents=True, exist_ok=True)
    return CloudTarget(
        folder=folder,
        provider=provider,
        is_cloud=True,
        note=f"已识别 {label}，报告写入：{folder}",
    )


def _make_local() -> CloudTarget:
    folder = config.DATA_ROOT / "reports"
    folder.mkdir(parents=True, exist_ok=True)
    return CloudTarget(
        folder=folder,
        provider="local",
        is_cloud=False,
        note=(
            f"未检测到任何网盘，报告写入本地：{folder}\n"
            f"  本机可直接用浏览器打开其中的 HTML 查看。"
        ),
    )


def resolve_cloud_target() -> CloudTarget:
    """按优先级解析出最终写入目录。"""
    # 1. 自定义目录（最高优先级）
    custom = (getattr(config, "CUSTOM_SYNC_DIR", "") or "").strip()
    if custom:
        root = _first_writable([custom])
        if root:
            return _make_cloud("custom", f"自定义目录 {root}", root)
        log.warning("CUSTOM_SYNC_DIR=%s 不存在或不可写，继续自动探测。", custom)

    target = (config.CLOUD_TARGET or "auto").lower()

    # 2. 显式纯本地
    if target == "local":
        return _make_local()

    # 3. 指定了具体 provider：先试它，失败再走 auto 链
    if target in _DETECTORS:
        fn, label = _DETECTORS[target]
        root = fn()
        if root:
            return _make_cloud(target, label, root)
        log.warning("指定的 %s 未检测到，回退到自动探测。", label)

    # 4. auto：依次探测整条链
    for name in _AUTO_CHAIN:
        fn, label = _DETECTORS[name]
        root = fn()
        if root:
            return _make_cloud(name, label, root)

    # 5. 本地兜底
    log.warning("自动探测未发现任何网盘客户端，回落到本地。")
    return _make_local()


# ---------- 同步动作 ----------
def sync_file(src: Path, target: CloudTarget) -> Path | None:
    if not src.is_file():
        return None
    dst = target.folder / src.name
    try:
        shutil.copy2(src, dst)
        log.debug("已同步 %s -> %s", src.name, dst)
        return dst
    except Exception as exc:
        log.warning("同步 %s 失败：%s", src, exc)
        return None


def sync_files(paths: list[Path], target: CloudTarget) -> list[Path]:
    return [p for p in (sync_file(s, target) for s in paths) if p]


def write_status(target: CloudTarget, **fields) -> None:
    status = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "provider": target.provider,
        **fields,
    }
    try:
        (target.folder / "status.json").write_text(
            json.dumps(status, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        log.warning("写 status.json 失败：%s", exc)


def write_intro_readme(target: CloudTarget) -> None:
    readme = target.folder / "README.txt"
    if readme.exists():
        return
    where = "本网盘会自动同步到云" if target.is_cloud else "当前为本地目录（未接入网盘）"
    body = (
        "W-Recorder 自动生成的工作日报目录\n"
        "================================\n\n"
        f"存储位置：{where}\n"
        f"当前 provider：{target.provider}\n\n"
        "- YYYY-MM-DD.html : 每日日报（推荐用浏览器打开，含图表）\n"
        "- YYYY-MM-DD.md   : Markdown 版本，方便粘贴到周报\n"
        "- status.json     : 当前服务运行状态\n\n"
        "数据由本机 WRecorder.exe 后台采集，每 5 分钟一次窗口快照 + 每 15 分钟同步 Outlook 日历。\n"
        "停止采集：双击 stop.bat 或在任务管理器结束 WRecorder.exe。\n"
    )
    try:
        readme.write_text(body, encoding="utf-8")
    except Exception as exc:
        log.warning("写 README.txt 失败：%s", exc)
