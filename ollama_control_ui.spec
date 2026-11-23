# -*- mode: python ; coding: utf-8 -*-
# Spec PyInstaller pentru Ollama Control.
#
# Se foloseste build onedir (`COLLECT`), nu onefile: pornirea este mult mai
# rapida, iar distributia in pachete (.deb) si AppImage este mai simpla.


a = Analysis(
    ['ollama_control.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('icon.png', '.'),
        ('ui_uptime.png', '.'),
        ('ui_status.png', '.'),
        ('ui_model.png', '.'),
        ('ui_version.png', '.'),
        ('ui_copy.png', '.'),
    ],
    hiddenimports=['PIL', 'PIL._tkinter_finder'],
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
    [],
    exclude_binaries=True,
    name='ollama_control',
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

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ollama_control',
)
