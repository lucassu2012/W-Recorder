"""W-Recorder 全局配置（云化版本）。

设计要点：
- EXE 在任何位置运行时，数据 / 日志固定落到 %LOCALAPPDATA%\\W-Recorder
- 日报写入到 OneDrive\\W-Recorder（自动检测），缺省回落到本地
- 所有可调参数集中在这里，且可被同目录下 config.json 覆盖
"""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

log = logging.getLogger(__name__)

APP_NAME = "W-Recorder"


def _is_frozen() -> bool:
    """是否运行在 PyInstaller 打包后的 EXE 中。"""
    return getattr(sys, "frozen", False)


def _exe_dir() -> Path:
    """EXE / 脚本所在目录（用于查找同目录 config.json）。"""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def _local_appdata() -> Path:
    """%LOCALAPPDATA%；fallback 到 ~/.W-Recorder。"""
    base = os.environ.get("LOCALAPPDATA")
    if base and Path(base).is_dir():
        return Path(base) / APP_NAME
    return Path.home() / f".{APP_NAME}"


# ---------- 路径 ----------
# 数据 / 日志：固定落到 %LOCALAPPDATA%，跟随用户而非 EXE 位置
DATA_ROOT: Path = _local_appdata()
DATA_DIR: Path = DATA_ROOT / "data"
LOGS_DIR: Path = DATA_ROOT / "logs"
ASSETS_DIR: Path = DATA_ROOT / "assets"
RUNTIME_DIR: Path = DATA_ROOT / "runtime"
DB_PATH: Path = DATA_DIR / "w_recorder.db"

# 报告目录：先尝试 OneDrive，缺省回落到 DATA_ROOT/reports
# （真正解析在 sync.detect_reports_dir() 里做，这里给一个 fallback）
REPORTS_DIR: Path = DATA_ROOT / "reports"

for _p in (DATA_DIR, LOGS_DIR, ASSETS_DIR, RUNTIME_DIR, REPORTS_DIR):
    _p.mkdir(parents=True, exist_ok=True)

# ---------- 采集策略 ----------
SAMPLE_INTERVAL_SECONDS: int = 5 * 60
IDLE_THRESHOLD_SECONDS: int = 5 * 60
CALENDAR_SYNC_INTERVAL_SECONDS: int = 15 * 60

# 报告写入云盘 / 本地的间隔
REPORT_REFRESH_INTERVAL_SECONDS: int = 5 * 60

# ---------- 云同步 ----------
# CLOUD_TARGET 取值：
#   'auto'（推荐）—— 自动探测 OneDrive / 坚果云 / Dropbox / Google Drive / iCloud / Box
#   也可锁定具体网盘：'onedrive' 'nutstore' 'dropbox' 'googledrive' 'icloud' 'box'
#   'local' —— 完全不接网盘，仅写本地（本机浏览器查看）
CLOUD_TARGET: str = "auto"
CLOUD_SUBDIR: str = APP_NAME  # 在网盘根目录下创建的子文件夹名

# 手动指定任意"已被某网盘客户端同步的"目录（最高优先级，留空则走自动探测）。
# 例：坚果云自定义路径 "D:\\MySync"，或新版 Google Drive 虚拟盘 "G:\\My Drive"
CUSTOM_SYNC_DIR: str = ""

# ---------- 应用分类 ----------
APP_CATEGORIES: dict[str, str] = {
    # 通讯/会议
    "outlook.exe": "邮件/日历",
    "teams.exe": "会议",
    "ms-teams.exe": "会议",
    "zoom.exe": "会议",
    "wemeetapp.exe": "会议",
    "dingtalk.exe": "即时通讯",
    "wechat.exe": "即时通讯",
    "wework.exe": "即时通讯",
    "feishu.exe": "即时通讯",
    "lark.exe": "即时通讯",
    "slack.exe": "即时通讯",
    # 浏览器
    "chrome.exe": "浏览器",
    "msedge.exe": "浏览器",
    "firefox.exe": "浏览器",
    "brave.exe": "浏览器",
    # 文档/办公
    "winword.exe": "Office 文档",
    "excel.exe": "Office 文档",
    "powerpnt.exe": "Office 文档",
    "onenote.exe": "笔记",
    "notepad.exe": "记事/编辑",
    "notepad++.exe": "记事/编辑",
    "wpsoffice.exe": "Office 文档",
    "wps.exe": "Office 文档",
    "et.exe": "Office 文档",
    "wpp.exe": "Office 文档",
    "acrord32.exe": "PDF 阅读",
    "foxitreader.exe": "PDF 阅读",
    # 开发
    "code.exe": "开发/IDE",
    "devenv.exe": "开发/IDE",
    "pycharm64.exe": "开发/IDE",
    "idea64.exe": "开发/IDE",
    "clion64.exe": "开发/IDE",
    "windowsterminal.exe": "终端",
    "powershell.exe": "终端",
    "cmd.exe": "终端",
    "wt.exe": "终端",
    # 系统
    "explorer.exe": "文件资源管理器",
}

REPORT_TOP_N_APPS: int = 10


# ---------- 用户配置覆盖 ----------
def _load_user_config() -> None:
    """如果 EXE 同目录有 config.json，则覆盖部分配置。

    支持的键：CLOUD_TARGET, CLOUD_SUBDIR, SAMPLE_INTERVAL_SECONDS,
              IDLE_THRESHOLD_SECONDS, CALENDAR_SYNC_INTERVAL_SECONDS,
              REPORT_REFRESH_INTERVAL_SECONDS, REPORT_TOP_N_APPS,
              APP_CATEGORIES (字典 merge)
    """
    cfg_path = _exe_dir() / "config.json"
    if not cfg_path.is_file():
        return
    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            user = json.load(f)
    except Exception as exc:
        log.warning("config.json 解析失败：%s", exc)
        return

    g = globals()
    for k, v in user.items():
        if k == "APP_CATEGORIES" and isinstance(v, dict):
            g["APP_CATEGORIES"] = {**g["APP_CATEGORIES"], **v}
        elif k in g and not k.startswith("_"):
            g[k] = v
            log.info("覆盖配置：%s = %s", k, v)


_load_user_config()
