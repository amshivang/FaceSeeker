# -*- mode: python ; coding: utf-8 -*-

"""
face_seeker.spec - PyInstaller Specification File for Face Seeker.
Bundles Face Seeker into a 100% offline standalone Windows executable.
Includes OpenCV ONNX models, Flask/PyWebView assets, dependencies, and path resolution.
"""

import os
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None

# Project root directory
project_dir = os.path.abspath(os.path.dirname(SPEC)) if 'SPEC' in locals() else os.path.abspath('.')

datas = [
    (os.path.join(project_dir, 'models'), 'models'),
    (os.path.join(project_dir, 'templates'), 'templates'),
    (os.path.join(project_dir, 'static'), 'static'),
    (os.path.join(project_dir, 'assets', 'icon.ico'), 'assets'),
]

# Explicitly list hidden imports for lazy-loaded dependencies
hiddenimports = [
    'cv2',
    'numpy',
    'face_engine',
    'app',
    'csv',
    'io',
    'queue',
    'threading',
    'flask',
    'werkzeug',
    'jinja2',
    'webbrowser',
    'webview',
]
hiddenimports += collect_submodules('webview')

# Exclude heavy unused libraries to produce a fast & lightweight build
excludes = [
    'torch',
    'torchvision',
    'transformers',
    'sympy',
    'scipy',
    'pandas',
    'matplotlib',
    'notebook',
    'fastapi',
    'streamlit',
    'altair',
    'pyarrow',
    'weasyprint',
    'IPython',
    'brotli',
    'tkinter',
    'customtkinter',
]

a = Analysis(
    ['main.py'],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FaceSeeker',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False, # Hide console since PyWebView provides a native window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(project_dir, 'assets', 'icon.ico')
)
