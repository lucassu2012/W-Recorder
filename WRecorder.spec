# PyInstaller 构建脚本：把 W-Recorder 打包成一个免安装的 EXE。
# 使用：build.bat（或手动 `py -m PyInstaller WRecorder.spec`）

# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Outlook COM 在 PyInstaller 下需要显式声明的隐式依赖
hiddenimports = [
    "win32com",
    "win32com.client",
    "win32com.gen_py",
    "win32timezone",
    "pythoncom",
    "pywintypes",
    "psutil",
]
hiddenimports += collect_submodules("win32com")

a = Analysis(
    ["w_recorder.py"],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # 云化版本不带 GUI / 托盘，显式排除以减小 EXE 体积
    excludes=[
        "tkinter",
        "pystray",
        "PIL",
        "src.gui",
        "src.tray",
        "matplotlib",
        "numpy",
        "pandas",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="WRecorder",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,                # 有 upx.exe 时会进一步压缩；没有则忽略
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # 后台无窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,               # 后续可塞一个 .ico
)
