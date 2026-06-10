# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 빌드 설정"""

import sys
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

block_cipher = None
root = Path(SPECPATH)

datas = [
    (str(root / "app.py"), "."),
    (str(root / "naver_ad_report"), "naver_ad_report"),
    (str(root / ".streamlit"), ".streamlit"),
    (str(root / "data"), "data"),
] + copy_metadata("streamlit")

hiddenimports = [
    "streamlit",
    "streamlit.web.cli",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "pandas",
    "openpyxl",
    "altair",
    "numpy",
    "pyarrow",
    "tornado",
    "watchdog",
    "naver_ad_report",
    "naver_ad_report.parser",
    "naver_ad_report.report_generator",
    "naver_ad_report.storage",
    "naver_ad_report.metrics",
    "naver_ad_report.report_data",
    "naver_ad_report.config",
]

a = Analysis(
    ["launcher.py"],
    pathex=[str(root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="네이버광고리포트",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="네이버광고리포트",
)
