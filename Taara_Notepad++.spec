# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('C:\\Users\\ADMIN\\Desktop\\Debugger_Tools\\Taara_Debugger\\project_view.py', '.'), ('C:\\Users\\ADMIN\\Desktop\\Debugger_Tools\\Taara_Debugger\\ctags_handler.py', '.'), ('C:\\Users\\ADMIN\\Desktop\\Debugger_Tools\\Taara_Debugger\\themes\\khaki.json', 'themes')],
    hiddenimports=[],
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
    name='Taara_Notepad++',
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
    icon=['C:\\Users\\ADMIN\\Desktop\\Debugger_Tools\\Taara_Debugger\\icons\\logoIcon.ico'],
)
