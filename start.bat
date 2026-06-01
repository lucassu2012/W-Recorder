@echo off
REM W-Recorder 启动：优先使用打包后的 EXE，找不到则用 py 源码运行
cd /d "%~dp0"

if exist "dist\WRecorder.exe" (
    start "" "dist\WRecorder.exe"
    echo W-Recorder 已启动（dist\WRecorder.exe）。
    echo 报告写入：检测到的 OneDrive\W-Recorder 或 %%LOCALAPPDATA%%\W-Recorder\reports
    timeout /t 3 >nul
    exit /b 0
)

if exist "WRecorder.exe" (
    start "" "WRecorder.exe"
    echo W-Recorder 已启动（WRecorder.exe）。
    timeout /t 3 >nul
    exit /b 0
)

REM 源码模式（开发用）
echo 未找到 EXE，使用源码模式启动 ...
start "" /min py w_recorder.py
timeout /t 3 >nul
