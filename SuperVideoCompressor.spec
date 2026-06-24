# -*- mode: python ; coding: utf-8 -*-
"""Cấu hình đóng gói PyInstaller cho Super Video Compressor.

Build:  pyinstaller SuperVideoCompressor.spec --noconfirm

Gom đầy đủ dữ liệu của customtkinter (theme/asset), tkinterdnd2 (binary tkdnd
cho kéo-thả) và static_ffmpeg để bản .exe chạy độc lập, không cần cài Python.
"""
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for pkg in ("customtkinter", "tkinterdnd2", "static_ffmpeg"):
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="SuperVideoCompressor",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
