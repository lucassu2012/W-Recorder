"""W-Recorder 启动入口（云化无 UI 版本）。

用法：
  py w_recorder.py            前台运行（看日志）
  py w_recorder.py --stop     给已运行实例发送停止信号
  py w_recorder.py --where    打印报告写入位置 + 探测到的所有网盘（诊断用）

打包：见 build.bat / WRecorder.spec
"""

from __future__ import annotations

import sys


def _maybe_stop() -> bool:
    if "--stop" in sys.argv:
        from src import lifecycle
        existing = lifecycle.read_running_pid()
        if existing is None:
            print("没有正在运行的 W-Recorder 实例。")
            return True
        lifecycle.request_stop()
        print(f"已向 PID={existing} 发送停止信号。")
        return True
    return False


def _maybe_where() -> bool:
    if "--where" in sys.argv:
        from src import config, sync
        print("W-Recorder 报告位置诊断")
        print("=" * 40)
        detected = sync.detect_all()
        if detected:
            print("探测到的网盘客户端：")
            for _name, label, root in detected:
                print(f"  - {label}: {root}")
        else:
            print("未探测到任何网盘客户端。")
        print("-" * 40)
        target = sync.resolve_cloud_target()
        print(f"最终写入 provider：{target.provider}")
        print(f"报告目录：{target.folder}")
        print(f"是否云同步：{'是' if target.is_cloud else '否（仅本地）'}")
        print("-" * 40)
        print(f"原始数据库（始终本地）：{config.DB_PATH}")
        print(f"日志：{config.LOGS_DIR}")
        return True
    return False


def main() -> int:
    if _maybe_stop():
        return 0
    if _maybe_where():
        return 0
    from src.app import main as run
    return run()


if __name__ == "__main__":
    sys.exit(main() or 0)
