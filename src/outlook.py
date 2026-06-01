"""Outlook 日历集成（本地 COM）。

要求本机已装 Outlook 桌面客户端并已登录。失败时静默返回空列表。
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Iterable

log = logging.getLogger(__name__)

try:
    import pythoncom  # type: ignore
    import win32com.client  # type: ignore
    _HAVE_COM = True
except Exception as exc:  # pragma: no cover
    log.warning("pywin32 (COM) 未就绪：%s。Outlook 集成将不可用。", exc)
    _HAVE_COM = False

_OL_FOLDER_CALENDAR = 9


def _to_python_datetime(value) -> datetime:
    if isinstance(value, datetime):
        return value
    if hasattr(value, "year"):
        return datetime(
            value.year, value.month, value.day,
            value.hour, value.minute, value.second,
        )
    return value


def _isoformat(dt: datetime) -> str:
    return dt.replace(microsecond=0).isoformat(sep=" ")


def fetch_calendar_items(
    target_day: date | None = None,
    days: int = 1,
) -> list[dict]:
    if not _HAVE_COM:
        return []

    if target_day is None:
        target_day = date.today()
    start = datetime.combine(target_day, datetime.min.time())
    end = start + timedelta(days=days)

    items: list[dict] = []
    pythoncom.CoInitialize()
    try:
        outlook = win32com.client.Dispatch("Outlook.Application")
        namespace = outlook.GetNamespace("MAPI")
        cal = namespace.GetDefaultFolder(_OL_FOLDER_CALENDAR).Items
        cal.IncludeRecurrences = True
        cal.Sort("[Start]")

        # Outlook Restrict 用 12 小时 + AM/PM
        fmt = "%m/%d/%Y %I:%M %p"
        restriction = (
            f"[Start] >= '{start.strftime(fmt)}' AND "
            f"[Start] < '{end.strftime(fmt)}'"
        )
        restricted = cal.Restrict(restriction)

        for entry in restricted:
            try:
                start_at = _to_python_datetime(entry.Start)
                end_at = _to_python_datetime(entry.End)
                body = (entry.Body or "")[:500] if hasattr(entry, "Body") else ""
                items.append({
                    "entry_id": getattr(entry, "EntryID", None),
                    "subject": getattr(entry, "Subject", "(无主题)"),
                    "start_at": _isoformat(start_at),
                    "end_at": _isoformat(end_at),
                    "organizer": getattr(entry, "Organizer", None),
                    "location": getattr(entry, "Location", None) or None,
                    "is_meeting": bool(getattr(entry, "MeetingStatus", 0)),
                    "body_preview": body or None,
                })
            except Exception as exc:
                log.warning("解析日历项失败：%s", exc)
    except Exception as exc:
        log.warning("访问 Outlook 失败：%s", exc)
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    return items


def summarize(items: Iterable[dict]) -> str:
    items = list(items)
    if not items:
        return "今日无日历项"
    return f"今日 {len(items)} 个日历项 / 会议"
