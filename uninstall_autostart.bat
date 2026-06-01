@echo off
REM 取消开机自启
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "W-Recorder" /f >nul 2>&1
if errorlevel 1 (
    echo 未发现开机启动项（或已删除）。
) else (
    echo 已取消 W-Recorder 开机启动。
)
pause
