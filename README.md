# W-Recorder（云化免安装版）

Windows 桌面工作内容自动记录工具。**单文件 EXE 免安装**，后台静默运行，
自动把每日日报同步到你**已有的任意网盘**，任何设备都能看。

## 一句话特性

- 📦 **单文件 EXE，免安装**：~20MB，双击即跑，无需装 Python / pywin32 / 任何依赖
- 🕒 每 5 分钟采样前台窗口（应用 + 标题），每 15 分钟同步 Outlook 日历
- 💤 5 分钟无键鼠输入自动判定空闲，不计入工作时间
- ☁️ 日报（HTML + Markdown）**自动探测网盘**：OneDrive / 坚果云 / Dropbox / Google Drive / iCloud / Box
- 📱 手机 / 平板 / 其他 PC 打开对应网盘即可查看
- 🪂 **没有任何网盘也能用**：自动回落本地，本机浏览器直接看
- 🔒 完全本地采集，**不调任何第三方 API**，零账号、零授权
- 🚫 单实例锁，PID 文件优雅停止

## 快速上手（最终用户）

### 1. 拿到 EXE

如果你拿到的是 `WRecorder.exe`：跳到第 2 步。

如果你拿到的是源码：在源码目录运行 `build.bat`（首次需 1–2 分钟），完成后
`dist\WRecorder.exe` 即是最终产物。

### 2. 双击运行

把 `WRecorder.exe` 拷到任意目录（建议 `D:\Tools\WRecorder\` 或类似），
**双击启动**。无窗口、无托盘——它就在后台跑了。

首次运行后，会在你**已有的网盘**根目录下自动出现 `W-Recorder/` 文件夹：

```
<你的网盘>\W-Recorder\
├── README.txt          说明文件
├── status.json         当前运行状态（每 5 分钟更新）
├── 2026-06-01.html     今日日报（推荐浏览器打开）
└── 2026-06-01.md       今日日报（Markdown，方便贴周报）
```

**不确定写到哪了？** 运行 `WRecorder.exe --where`（或 `py w_recorder.py --where`），
会打印探测到的所有网盘 + 最终写入位置。

### 3. 查看日报

- **本机**：直接双击 `W-Recorder\` 目录里的 HTML
- **手机**：装对应网盘 App（OneDrive / 坚果云 / Dropbox…），进到 `W-Recorder/` 看 HTML
- **其他 PC**：登录对应网盘网页版查看

### 4. 停止 / 开机自启

| 操作 | 方法 |
|---|---|
| 启动 | 双击 `WRecorder.exe`，或运行 `start.bat` |
| 停止 | 双击 `stop.bat`（优雅停止，5 秒兜底 taskkill） |
| 开机自启 | 双击 `install_autostart.bat`（写入 `HKCU\…\Run`） |
| 取消自启 | 双击 `uninstall_autostart.bat` |

## 目录结构

打包后只需要分发以下 5 个文件：

```
WRecorder/
├── WRecorder.exe            主程序（PyInstaller 单文件）
├── start.bat                启动
├── stop.bat                 停止
├── install_autostart.bat    加入开机启动
├── uninstall_autostart.bat  取消开机启动
└── config.sample.json       可选配置示例（如需自定义间隔 / 分类）
```

运行时数据落到：

```
%LOCALAPPDATA%\W-Recorder\
├── data\w_recorder.db       SQLite 原始数据（永远在本地）
├── logs\w_recorder.log      运行日志
├── runtime\wrecorder.pid    PID 文件
└── reports\                 本地报告（OneDrive 缺失时的 fallback）

%OneDrive%\W-Recorder\
├── YYYY-MM-DD.html / .md    日报
├── status.json
└── README.txt
```

## 报告存到哪？（网盘探测与兜底）

W-Recorder 不绑定 OneDrive。启动时按下面的**优先级阶梯**自动决定报告写入位置：

```
1. config.json 里的 CUSTOM_SYNC_DIR   你手动指定的任意已同步目录（最高优先级）
2. CLOUD_TARGET 指定的具体网盘          如 "dropbox"
3. auto 自动探测（默认）               OneDrive → 坚果云 → Dropbox → Google Drive → iCloud → Box
4. 本地兜底                           %LOCALAPPDATA%\W-Recorder\reports（本机浏览器直接看）
```

| 你的情况 | 怎么办 |
|---|---|
| 有 OneDrive / 坚果云 / Dropbox / Google Drive / iCloud / Box | **什么都不用做**，自动识别 |
| 有其它网盘（企业盘映射成本地文件夹等） | config.json 填 `"CUSTOM_SYNC_DIR": "你的同步目录"` |
| 新版 Google Drive（虚拟盘 G:） | config.json 填 `"CUSTOM_SYNC_DIR": "G:\\My Drive"` |
| 啥网盘都没有 | 自动落本地，双击 `%LOCALAPPDATA%\W-Recorder\reports` 里的 HTML 查看 |
| 想完全离线、绝不写网盘 | config.json 填 `"CLOUD_TARGET": "local"` |

**验证写到哪了**：`WRecorder.exe --where` 一条命令打印探测结果 + 最终位置。

## 自定义配置

把 `config.sample.json` 复制为 `config.json`，放到 `WRecorder.exe` 同目录。
所有键可省略，仅写你想覆盖的：

```json
{
  "CLOUD_TARGET": "auto",
  "CUSTOM_SYNC_DIR": "",
  "SAMPLE_INTERVAL_SECONDS": 300,
  "IDLE_THRESHOLD_SECONDS": 300,
  "CALENDAR_SYNC_INTERVAL_SECONDS": 900,
  "CLOUD_SUBDIR": "Work-Logs",
  "APP_CATEGORIES": {
    "myapp.exe": "自定义业务系统"
  }
}
```

改完重启 EXE 即生效。

## 开发模式（不打包，直接跑 Python）

```bat
py -m pip install -r requirements.txt
py w_recorder.py            REM 前台运行
py w_recorder.py --stop     REM 给已运行实例发停止信号
```

## 项目结构（源码）

```
W_Recorder/
├── w_recorder.py            入口
├── WRecorder.spec           PyInstaller 配置
├── build.bat                打包脚本
├── requirements.txt
├── config.sample.json
├── start.bat / stop.bat / install_autostart.bat / uninstall_autostart.bat
└── src/
    ├── config.py            全局配置 + config.json 覆盖逻辑
    ├── storage.py           SQLite（activity_samples + meetings）
    ├── tracker.py           前台窗口采集（win32gui + psutil）
    ├── idle.py              空闲检测（GetLastInputInfo）
    ├── outlook.py           Outlook COM 日历读取
    ├── report.py            HTML + Markdown 日报渲染
    ├── sync.py              多网盘自动探测 + 文件同步
    ├── lifecycle.py         PID 文件 + 单实例 + stop.flag
    └── app.py               主调度（采样 / 同步 / 报告刷新）
```

## 常见问题

| 现象 | 排查 |
|---|---|
| 双击 EXE 没反应 | 这是预期：它是后台进程，无 UI。查 `%LOCALAPPDATA%\W-Recorder\logs\w_recorder.log` |
| 不知道报告写到哪 | 运行 `WRecorder.exe --where`，打印探测到的网盘 + 最终写入位置 |
| 网盘里没出现 W-Recorder 文件夹 | `--where` 看 `provider`；为 `local` 说明没探测到任何网盘。确认网盘客户端已登录且 sync 正常，或用 `CUSTOM_SYNC_DIR` 手动指定 |
| 有网盘但没被识别 | config.json 填 `"CUSTOM_SYNC_DIR": "网盘的本地同步目录"` 即可 |
| 日报里都是 `unknown` | 极少见，pywin32 拿不到前台窗口；通常是被某些全屏游戏 / UAC 抢焦点期间 |
| 日历同步 0 条 | 本机需安装 Outlook **桌面客户端**并已登录账户。仅网页版 Outlook 不支持 |
| 想从一台机器迁移数据 | 拷 `%LOCALAPPDATA%\W-Recorder\data\w_recorder.db` 到新机同位置即可 |

## 设计取舍

为什么不做"完全云端"：活动窗口监控必须在本地 OS 层调用 Win32 API，
云端无法访问你 PC 的前台窗口。所以采用了"**本地极轻代理 + 云端报告**"
架构——本地只有一个 EXE，没有安装步骤，所有可视化数据放云端。

为什么走"网盘文件夹"而非各家云 API（Microsoft Graph / Google Drive API…）：
- 网盘客户端是文件级同步，**零配置零授权**——它把云目录映射成本地文件夹，
  W-Recorder 只管往文件夹里写，同步交给网盘客户端
- 云 API 普遍需要应用注册 + OAuth flow，对个人用户太重
- 一套写文件的逻辑同时兼容 6 种主流网盘 + 自定义目录 + 纯本地，覆盖面最广
- 后续如需多人协作 / 主动推送，可在 `sync.py` 里加 Notion / 飞书 / WebDAV provider

## 隐私

- 所有原始数据仅写入本地 SQLite，**不会上传**
- 写入网盘目录的只有渲染好的日报（HTML / Markdown）+ 状态文件，由你自己的网盘账号同步
- 如需完全离线：`config.json` 设 `"CLOUD_TARGET": "local"`，绝不写任何网盘
- 清空数据：删 `%LOCALAPPDATA%\W-Recorder\` 目录即可
