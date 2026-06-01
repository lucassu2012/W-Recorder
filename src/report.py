"""每日报告生成：聚合活动样本 + 会议 → HTML / Markdown 双格式。"""

from __future__ import annotations

import html
import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from . import config, storage


_MINUTES_PER_SAMPLE = max(1, config.SAMPLE_INTERVAL_SECONDS // 60)


@dataclass
class DailyReport:
    day: date
    total_minutes: int
    active_minutes: int
    idle_minutes: int
    samples_count: int
    by_app: list[tuple[str, int]]
    by_category: list[tuple[str, int]]
    timeline: list[dict]
    meetings: list[dict]
    generated_at: datetime


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {k: row[k] for k in row.keys()}


def _category_of(process_name: str, raw_category: str | None) -> str:
    if raw_category:
        return raw_category
    if process_name in (None, "", "unknown"):
        return "未识别"
    return "其它应用"


def build_report(day: date | None = None) -> DailyReport:
    if day is None:
        day = date.today()

    samples = storage.fetch_samples_for_day(day)
    meetings = [_row_to_dict(m) for m in storage.fetch_meetings_for_day(day)]

    samples_count = len(samples)
    total_minutes = samples_count * _MINUTES_PER_SAMPLE
    idle_minutes = sum(_MINUTES_PER_SAMPLE for s in samples if s["is_idle"])
    active_minutes = total_minutes - idle_minutes

    app_counter: Counter[str] = Counter()
    cat_counter: Counter[str] = Counter()
    for s in samples:
        if s["is_idle"]:
            continue
        name = s["process_name"] or "unknown"
        app_counter[name] += _MINUTES_PER_SAMPLE
        cat_counter[_category_of(name, s["category"])] += _MINUTES_PER_SAMPLE

    by_app = app_counter.most_common(config.REPORT_TOP_N_APPS)
    by_category = sorted(cat_counter.items(), key=lambda kv: -kv[1])

    timeline = []
    for s in samples:
        ts = datetime.fromisoformat(s["sampled_at"])
        timeline.append({
            "time": ts.strftime("%H:%M"),
            "process_name": s["process_name"],
            "window_title": s["window_title"] or "",
            "category": _category_of(s["process_name"], s["category"]),
            "is_idle": bool(s["is_idle"]),
            "idle_seconds": int(s["idle_seconds"]),
        })

    return DailyReport(
        day=day,
        total_minutes=total_minutes,
        active_minutes=active_minutes,
        idle_minutes=idle_minutes,
        samples_count=samples_count,
        by_app=by_app,
        by_category=by_category,
        timeline=timeline,
        meetings=meetings,
        generated_at=datetime.now(),
    )


def _format_duration(minutes: int) -> str:
    h, m = divmod(minutes, 60)
    if h and m:
        return f"{h}h{m}m"
    if h:
        return f"{h}h"
    return f"{m}m"


def render_markdown(rep: DailyReport) -> str:
    lines: list[str] = []
    lines.append(f"# W-Recorder 日报 · {rep.day.isoformat()}")
    lines.append("")
    lines.append(f"_生成时间：{rep.generated_at:%Y-%m-%d %H:%M:%S}_")
    lines.append("")
    lines.append("## 概览")
    lines.append("")
    lines.append(f"- 采集次数：{rep.samples_count}")
    lines.append(f"- 在线时长：{_format_duration(rep.total_minutes)}")
    lines.append(f"- 实际工作：{_format_duration(rep.active_minutes)}")
    lines.append(f"- 空闲时长：{_format_duration(rep.idle_minutes)}")
    lines.append("")

    lines.append("## 今日会议 / 日历")
    lines.append("")
    if not rep.meetings:
        lines.append("_今日无日历项_")
    else:
        for m in rep.meetings:
            s = datetime.fromisoformat(m["start_at"]).strftime("%H:%M")
            e = datetime.fromisoformat(m["end_at"]).strftime("%H:%M")
            loc = f"  ·  📍 {m['location']}" if m.get("location") else ""
            org = f"  ·  组织者 {m['organizer']}" if m.get("organizer") else ""
            lines.append(f"- **{s}–{e}**  {m['subject']}{loc}{org}")
    lines.append("")

    lines.append("## 应用 Top")
    lines.append("")
    lines.append("| 应用 | 时长 |")
    lines.append("|------|------|")
    for name, minutes in rep.by_app:
        lines.append(f"| {name} | {_format_duration(minutes)} |")
    lines.append("")

    lines.append("## 类别分布")
    lines.append("")
    lines.append("| 类别 | 时长 |")
    lines.append("|------|------|")
    for cat, minutes in rep.by_category:
        lines.append(f"| {cat} | {_format_duration(minutes)} |")
    lines.append("")

    lines.append("## 时间线")
    lines.append("")
    if not rep.timeline:
        lines.append("_今日无采集样本_")
    else:
        for item in rep.timeline:
            tag = "💤 idle" if item["is_idle"] else item["category"]
            title = item["window_title"][:80] if item["window_title"] else ""
            lines.append(
                f"- `{item['time']}`  **{item['process_name']}**  "
                f"_{tag}_  {title}"
            )
    lines.append("")
    return "\n".join(lines)


_HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<title>W-Recorder 日报 · {day}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: -apple-system, "Segoe UI", "PingFang SC", "Microsoft Yahei", sans-serif;
         max-width: 960px; margin: 24px auto; padding: 0 16px; line-height: 1.55; }}
  h1 {{ margin-bottom: 0; }}
  .meta {{ color: #888; margin-bottom: 24px; }}
  .cards {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 16px 0 28px; }}
  .card {{ border: 1px solid #ddd; border-radius: 10px; padding: 14px; }}
  .card h3 {{ margin: 0 0 6px; font-size: 13px; color: #777; font-weight: 500; }}
  .card .v {{ font-size: 22px; font-weight: 600; }}
  table {{ border-collapse: collapse; width: 100%; margin: 8px 0 24px; }}
  th, td {{ text-align: left; padding: 8px 10px; border-bottom: 1px solid #eee; }}
  th {{ background: #fafafa; font-weight: 600; font-size: 13px; }}
  .bar {{ height: 8px; background: #4f90ff; border-radius: 4px; }}
  .timeline {{ font-family: ui-monospace, "Cascadia Mono", Consolas, monospace; font-size: 13px; }}
  .timeline tr.idle td {{ color: #999; }}
  .pill {{ display: inline-block; padding: 1px 8px; border-radius: 999px;
          background: #eef2ff; color: #3b4cca; font-size: 12px; margin-right: 6px; }}
  .pill.idle {{ background: #f1f1f1; color: #777; }}
  .meeting {{ padding: 8px 10px; border-left: 3px solid #ffaa00;
              background: #fff8e8; margin-bottom: 6px; border-radius: 4px; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background: #1b1d21; color: #ddd; }}
    .card, table th {{ background: #25282d; border-color: #333; }}
    th, td {{ border-color: #333; }}
    .pill {{ background: #2a3358; color: #b9c4ff; }}
    .meeting {{ background: #3a3122; border-color: #c69035; }}
  }}
</style>
</head>
<body>
<h1>W-Recorder 日报 · {day}</h1>
<div class="meta">生成时间：{generated_at}</div>

<div class="cards">
  <div class="card"><h3>采集次数</h3><div class="v">{samples_count}</div></div>
  <div class="card"><h3>在线时长</h3><div class="v">{total_dur}</div></div>
  <div class="card"><h3>实际工作</h3><div class="v">{active_dur}</div></div>
  <div class="card"><h3>空闲时长</h3><div class="v">{idle_dur}</div></div>
</div>

<h2>今日会议 / 日历</h2>
{meetings_html}

<h2>应用 Top</h2>
<table>
  <thead><tr><th>应用</th><th>时长</th><th style="width:40%">占比</th></tr></thead>
  <tbody>{apps_rows}</tbody>
</table>

<h2>类别分布</h2>
<table>
  <thead><tr><th>类别</th><th>时长</th><th style="width:40%">占比</th></tr></thead>
  <tbody>{cats_rows}</tbody>
</table>

<h2>时间线</h2>
<table class="timeline">
  <thead><tr><th style="width:64px">时间</th><th style="width:140px">应用</th>
            <th style="width:120px">类别</th><th>窗口标题</th></tr></thead>
  <tbody>{timeline_rows}</tbody>
</table>

</body>
</html>
"""


def _bar_cell(value: int, max_value: int) -> str:
    if max_value <= 0:
        return ""
    pct = max(2, int(value * 100 / max_value))
    return f'<div class="bar" style="width:{pct}%"></div>'


def render_html(rep: DailyReport) -> str:
    if rep.meetings:
        meetings_html = "".join(
            (
                '<div class="meeting"><b>{s}–{e}</b> &nbsp; {subject}'
                "{loc}{org}</div>"
            ).format(
                s=datetime.fromisoformat(m["start_at"]).strftime("%H:%M"),
                e=datetime.fromisoformat(m["end_at"]).strftime("%H:%M"),
                subject=html.escape(m["subject"] or "(无主题)"),
                loc=(f" &nbsp; 📍 {html.escape(m['location'])}" if m.get("location") else ""),
                org=(f" &nbsp; 👤 {html.escape(m['organizer'])}" if m.get("organizer") else ""),
            )
            for m in rep.meetings
        )
    else:
        meetings_html = '<p style="color:#888">今日无日历项</p>'

    max_app = max((v for _, v in rep.by_app), default=0)
    apps_rows = "".join(
        f"<tr><td>{html.escape(name)}</td>"
        f"<td>{_format_duration(minutes)}</td>"
        f"<td>{_bar_cell(minutes, max_app)}</td></tr>"
        for name, minutes in rep.by_app
    )

    max_cat = max((v for _, v in rep.by_category), default=0)
    cats_rows = "".join(
        f"<tr><td>{html.escape(cat)}</td>"
        f"<td>{_format_duration(minutes)}</td>"
        f"<td>{_bar_cell(minutes, max_cat)}</td></tr>"
        for cat, minutes in rep.by_category
    )

    if rep.timeline:
        timeline_rows = "".join(
            (
                '<tr class="{cls}"><td>{t}</td><td>{p}</td>'
                '<td><span class="pill {idle}">{cat}</span></td><td>{title}</td></tr>'
            ).format(
                cls="idle" if it["is_idle"] else "",
                t=it["time"],
                p=html.escape(it["process_name"] or "unknown"),
                idle="idle" if it["is_idle"] else "",
                cat=html.escape("💤 idle" if it["is_idle"] else it["category"]),
                title=html.escape((it["window_title"] or "")[:120]),
            )
            for it in rep.timeline
        )
    else:
        timeline_rows = '<tr><td colspan="4" style="color:#888">今日无采集样本</td></tr>'

    return _HTML_TEMPLATE.format(
        day=rep.day.isoformat(),
        generated_at=rep.generated_at.strftime("%Y-%m-%d %H:%M:%S"),
        samples_count=rep.samples_count,
        total_dur=_format_duration(rep.total_minutes),
        active_dur=_format_duration(rep.active_minutes),
        idle_dur=_format_duration(rep.idle_minutes),
        meetings_html=meetings_html,
        apps_rows=apps_rows or '<tr><td colspan="3" style="color:#888">暂无数据</td></tr>',
        cats_rows=cats_rows or '<tr><td colspan="3" style="color:#888">暂无数据</td></tr>',
        timeline_rows=timeline_rows,
    )


def write_report_files(rep: DailyReport, out_dir: Path | None = None) -> tuple[Path, Path]:
    out_dir = out_dir or config.REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path = out_dir / f"{rep.day.isoformat()}.md"
    html_path = out_dir / f"{rep.day.isoformat()}.html"
    md_path.write_text(render_markdown(rep), encoding="utf-8")
    html_path.write_text(render_html(rep), encoding="utf-8")
    return md_path, html_path


def generate_for_day(day: date | None = None) -> tuple[DailyReport, Path, Path]:
    rep = build_report(day)
    md_path, html_path = write_report_files(rep)
    return rep, md_path, html_path
