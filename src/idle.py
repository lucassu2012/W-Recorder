"""空闲检测：调用 user32.GetLastInputInfo 获取自上次键鼠输入以来的毫秒数。"""

from __future__ import annotations

import ctypes
import logging
from ctypes import wintypes

log = logging.getLogger(__name__)


class _LASTINPUTINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]


def get_idle_seconds() -> int:
    try:
        info = _LASTINPUTINFO()
        info.cbSize = ctypes.sizeof(_LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
            return 0
        tick = ctypes.windll.kernel32.GetTickCount()
        return max(0, tick - info.dwTime) // 1000
    except Exception as exc:  # pragma: no cover
        log.warning("空闲检测失败：%s", exc)
        return 0


def is_idle(threshold_seconds: int) -> tuple[bool, int]:
    elapsed = get_idle_seconds()
    return elapsed >= threshold_seconds, elapsed
