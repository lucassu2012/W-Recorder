"""活动窗口采集（前台窗口标题 + 进程名 + 可执行路径）。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from . import config

log = logging.getLogger(__name__)

try:
    import win32gui  # type: ignore
    import win32process  # type: ignore
    import psutil  # type: ignore
    _HAVE_WIN32 = True
except Exception as exc:  # pragma: no cover
    log.warning("无法加载 pywin32/psutil：%s。tracker 将退化为占位实现。", exc)
    _HAVE_WIN32 = False


@dataclass(frozen=True)
class ActiveWindow:
    process_name: str
    process_path: str | None
    window_title: str | None
    category: str | None


def _categorize(process_name: str) -> str | None:
    return config.APP_CATEGORIES.get(process_name.lower())


def get_active_window() -> ActiveWindow:
    if not _HAVE_WIN32:
        return ActiveWindow("unknown", None, None, None)
    try:
        hwnd = win32gui.GetForegroundWindow()
        if not hwnd:
            return ActiveWindow("unknown", None, None, None)
        title = win32gui.GetWindowText(hwnd) or None
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if not pid:
            return ActiveWindow("unknown", None, title, None)
        try:
            proc = psutil.Process(pid)
            name = proc.name() or "unknown"
            try:
                path = proc.exe()
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                path = None
        except psutil.NoSuchProcess:
            return ActiveWindow("unknown", None, title, None)
        return ActiveWindow(name, path, title, _categorize(name))
    except Exception as exc:  # pragma: no cover
        log.exception("获取前台窗口失败：%s", exc)
        return ActiveWindow("unknown", None, None, None)
