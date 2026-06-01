@echo off
REM 把 WRecorder 加入开机启动（用户级，无需管理员）
REM 通过写注册表 HKCU\...\Run 实现
cd /d "%~dp0"

set "TARGET="
if exist "dist\WRecorder.exe" set "TARGET=%CD%\dist\WRecorder.exe"
if not defined TARGET if exist "WRecorder.exe" set "TARGET=%CD%\WRecorder.exe"

if not defined TARGET (
    echo 未找到 WRecorder.exe。请先运行 build.bat 完成打包。
    pause
    exit /b 1
)

reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "W-Recorder" /t REG_SZ /d "\"%TARGET%\"" /f >nul
if errorlevel 1 (
    echo 写注册表失败。
    pause
    exit /b 1
)

echo ============================================
echo  已加入开机启动：%TARGET%
echo  如需取消，运行 uninstall_autostart.bat
echo ============================================
pause
