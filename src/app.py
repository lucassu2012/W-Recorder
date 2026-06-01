"""W-Recorder 主应用（云化无 UI 版本）。

设计：
- 纯后台进程，无托盘 / 无 GUI
- 启动时检查 PID 文件，已在跑则直接退出（避免双启）
- 每 5 分钟采样活动窗口 / 每 15 分钟同步 Outlook 日历
- 每 5 分钟重新生成日报并 copy 到 OneDrive\\W-Recorder
- 主循环每秒检测 stop.flag 实现优雅停止
"""

from __future__ import annotations

import logging
import signal
import sys
import time
from datetime import datetime

from . import config, idle, lifecycle, outlook, report, storage, sync, tracker

log = logging.getLogger(__name__)


def _setup_logging() -> None:
    logfile = config.LOGS_DIR / "w_recorder.log"
    handlers: list[logging.Handler] = [
        logging.FileHandler(logfile, encoding="utf-8"),
    ]
    # 打包成 --noconsole EXE 时 stdout 可能是 None
    if sys.stdout is not None and sys.stdout.isatty():
        handlers.append(logging.StreamHandler(sys.stdout))
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


class WRecorderApp:
    def __init__(self) -> None:
        self._stop = False
        self._cloud = sync.resolve_cloud_target()

    # ---------- 核心动作 ----------
    def _sample_once(self) -> None:
        try:
            aw = tracker.get_active_window()
            idle_state, idle_secs = idle.is_idle(config.IDLE_THRESHOLD_SECONDS)
            storage.insert_activity_sample(
                sampled_at=datetime.now(),
                process_name=aw.process_name,
                process_path=aw.process_path,
                window_title=aw.window_title,
                category=aw.category,
                is_idle=idle_state,
                idle_seconds=idle_secs,
            )
            log.info(
                "采样: %s | %s | idle=%s(%ss)",
                aw.process_name,
                (aw.window_title or "")[:60],
                idle_state,
                idle_secs,
            )
        except Exception as exc:
            log.exception("采样失败：%s", exc)

    def _calendar_sync_once(self) -> int:
        try:
            items = outlook.fetch_calendar_items()
            count = storage.upsert_meetings(items)
            log.info("日历同步完成：%d 条", count)
            return count
        except Exception as exc:
            log.exception("日历同步失败：%s", exc)
            return 0

    def _refresh_report(self) -> None:
        """重新生成今日报告 + 推送到云。"""
        try:
            rep, md_path, html_path = report.generate_for_day()
            uploaded = sync.sync_files([md_path, html_path], self._cloud)
            sync.write_status(
                self._cloud,
                last_sample_at=(
                    storage.last_sample_at().isoformat(timespec="seconds")
                    if storage.last_sample_at() else None
                ),
                samples_today=rep.samples_count,
                active_minutes=rep.active_minutes,
                idle_minutes=rep.idle_minutes,
                meetings_today=len(rep.meetings),
                uploaded=[p.name for p in uploaded],
            )
            log.info(
                "报告已刷新并同步 %d 个文件（provider=%s）",
                len(uploaded), self._cloud.provider,
            )
        except Exception as exc:
            log.exception("刷新报告失败：%s", exc)

    # ---------- 信号 ----------
    def _install_signal_handlers(self) -> None:
        def _handler(signum, _frame):
            log.info("收到信号 %s，准备退出。", signum)
            self._stop = True
        try:
            signal.signal(signal.SIGINT, _handler)
            signal.signal(signal.SIGTERM, _handler)
        except Exception:
            # PyInstaller --noconsole 下某些信号可能不可装载，忽略即可
            pass

    # ---------- 主循环 ----------
    def run(self) -> int:
        # 单实例检查
        existing = lifecycle.read_running_pid()
        if existing is not None:
            log.warning("已有 W-Recorder 进程在运行（PID=%s），本次启动退出。", existing)
            return 2

        lifecycle.write_pid()
        self._install_signal_handlers()

        log.info("W-Recorder 启动 · PID=%s", lifecycle.PID_FILE.read_text())
        log.info(self._cloud.note)
        sync.write_intro_readme(self._cloud)

        # 启动时立刻做一次采样 / 同步 / 报告
        self._sample_once()
        self._calendar_sync_once()
        self._refresh_report()

        next_sample = time.monotonic() + config.SAMPLE_INTERVAL_SECONDS
        next_calendar = time.monotonic() + config.CALENDAR_SYNC_INTERVAL_SECONDS
        next_report = time.monotonic() + config.REPORT_REFRESH_INTERVAL_SECONDS

        try:
            while not self._stop:
                if lifecycle.consume_stop_flag():
                    log.info("检测到 stop.flag，准备退出。")
                    break

                now = time.monotonic()
                if now >= next_sample:
                    self._sample_once()
                    next_sample = now + config.SAMPLE_INTERVAL_SECONDS
                if now >= next_calendar:
                    self._calendar_sync_once()
                    next_calendar = now + config.CALENDAR_SYNC_INTERVAL_SECONDS
                if now >= next_report:
                    self._refresh_report()
                    next_report = now + config.REPORT_REFRESH_INTERVAL_SECONDS

                time.sleep(1.0)
        finally:
            try:
                # 退出前最后再 flush 一次报告，保证云端数据是最新的
                self._refresh_report()
            except Exception:
                pass
            lifecycle.clear_pid()
            log.info("W-Recorder 已退出。")
        return 0


def main() -> int:
    _setup_logging()
    log.info(
        "W-Recorder 启动 · 数据根=%s · 报告目录(预解析)=%s",
        config.DATA_ROOT, config.REPORTS_DIR,
    )
    return WRecorderApp().run()
