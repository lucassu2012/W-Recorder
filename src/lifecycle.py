"""进程生命周期：PID 文件、单实例保护、停止信号文件。

为什么不用 Windows Mutex：
- mutex 需要额外依赖且和 PyInstaller --onefile 配合时有 corner case
- 一个简单的 PID + 进程存活检测 + stop.flag 文件足够覆盖 99% 场景
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from . import config

log = logging.getLogger(__name__)

PID_FILE: Path = config.RUNTIME_DIR / "wrecorder.pid"
STOP_FLAG: Path = config.RUNTIME_DIR / "stop.flag"


# ---------- PID ----------
def _pid_alive(pid: int) -> bool:
    """检测 pid 是否还在跑。psutil 优先；缺失则用 os.kill(0)。"""
    if pid <= 0:
        return False
    try:
        import psutil  # type: ignore
        return psutil.pid_exists(pid)
    except Exception:
        pass
    try:
        # Windows / Unix 都接受 signal 0 做存在性测试
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_running_pid() -> int | None:
    """如果 pid 文件指向一个仍然存活的进程，返回该 pid，否则 None。"""
    if not PID_FILE.is_file():
        return None
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (ValueError, OSError):
        return None
    return pid if _pid_alive(pid) else None


def write_pid() -> None:
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")


def clear_pid() -> None:
    try:
        if PID_FILE.is_file():
            PID_FILE.unlink()
    except OSError as exc:
        log.warning("清理 PID 失败：%s", exc)


# ---------- stop flag ----------
def request_stop() -> None:
    """由 stop.bat 调用：放一个 flag 文件让主循环看到。"""
    STOP_FLAG.parent.mkdir(parents=True, exist_ok=True)
    STOP_FLAG.write_text(str(time.time()), encoding="utf-8")


def consume_stop_flag() -> bool:
    """主循环每秒检查一次；存在则视为收到停止请求并清理。"""
    if STOP_FLAG.is_file():
        try:
            STOP_FLAG.unlink()
        except OSError:
            pass
        return True
    return False
