@echo off
REM W-Recorder 打包脚本：产出 dist\WRecorder.exe（单文件，免安装）
cd /d "%~dp0"

echo [W-Recorder] 升级 pip ...
py -m pip install --upgrade pip

echo.
echo [W-Recorder] 安装运行时依赖 ...
py -m pip install -r requirements.txt

echo.
echo [W-Recorder] 安装 PyInstaller ...
py -m pip install pyinstaller

echo.
echo [W-Recorder] 清理上次产物 ...
if exist build rd /s /q build
if exist dist  rd /s /q dist

echo.
echo [W-Recorder] 开始打包（首次需要 1-2 分钟）...
py -m PyInstaller WRecorder.spec --noconfirm

if exist dist\WRecorder.exe (
    echo.
    echo ============================================
    echo  打包完成：dist\WRecorder.exe
    echo  把该 EXE 拷到任何 Windows 机器上双击即可运行。
    echo ============================================
) else (
    echo.
    echo [错误] 打包失败，检查上面的 PyInstaller 输出。
    exit /b 1
)

pause
