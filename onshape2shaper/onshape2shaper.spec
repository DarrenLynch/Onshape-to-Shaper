# -*- mode: python ; coding: utf-8 -*-


block_cipher = None


a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['_tkinter', 'Tkinter', 'enchant', 'twisted'],
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
    name='onshape2shaper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(exe, Tree('/Users/darrenlynch/Documents/Shaper Origin/Onshape-to-Shaper/onshape2shaper'),
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=None,
    upx=True,
    name='onshape2shaper',
)
app = BUNDLE(
    coll,
    name='onshape2shaper.app',
    icon=None,
    bundle_identifier=None,
)
