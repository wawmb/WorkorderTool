# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec - WorkorderTool"""
import os
from PyInstaller.utils.hooks import collect_submodules

try:
    _spec_dir = os.path.dirname(os.path.abspath(SPEC))
except NameError:
    _spec_dir = os.getcwd()

hiddenimports = ['requests', 'urllib3']
hiddenimports += collect_submodules('requests')
hiddenimports += collect_submodules('urllib3')


a = Analysis(
    ['workorder_app.py'],
    pathex=[],
    binaries=[],
    datas=[('config.ini', '.'), ('app_icon.ico', '.')],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WorkorderTool',
    icon=os.path.join(_spec_dir, 'app_icon.ico'),
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
