# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\main.py', 'D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\ctags_handler.py', 'D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\project_view.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\ARM-logo-vector-01.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\Electronics-icon-vector-01.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\function_list.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\new.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\open.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\open_proj.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\Power-icon-vector-02.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\project.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\save.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\show_all_char.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\sss.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\icons\\word-wrap.svg', 'icons'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\themes\\khaki.json', 'themes'), ('D:\\Git_Repository\\Debugger_Tools\\Taara_Debugger\\session.json', '.')],
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
    name='Taara_IDE.exe',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['icons\\logoIcon.ico'],
)
