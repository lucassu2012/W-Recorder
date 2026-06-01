@echo off
REM W-Recorder 优雅停止：通过 --stop 参数让正在运行的实例自己退出
cd /d "%~dp0"

if exist "dist\WRecorder.exe" (
    "dist\WRecorder.exe" --stop
    goto :verify
)
if exist "WRecorder.exe" (
    "WRecorder.exe" --stop
    goto :verify
)

py w_recorder.py --stop

:verify
echo.
echo 等待进程退出 ...
timeout /t 5 >nul

REM 兜底：5 秒后仍存活则强制杀
tasklist /FI "IMAGENAME eq WRecorder.exe" 2>nul | findstr /I "WRecorder.exe" >nul
if not errorlevel 1 (
    echo 仍在运行，执行强制结束 ...
    taskkill /F /IM WRecorder.exe >nul 2>&1
)
echo W-Recorder 已停止。
