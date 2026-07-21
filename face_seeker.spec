# -*- mode: python ; coding: utf-8 -*-

"""
face_seeker.spec - PyInstaller Specification File for Face Seeker.
Bundles Face Seeker into a 100% offline standalone Windows executable.
Includes OpenCV ONNX models, CustomTkinter assets, dependencies, and path resolution.
"""

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

project_dir = os.path.abspath(os.path.dirname(SPEC)) if 'SPEC' in locals() else os.path.abspath('.')

datas = [
    (os.path.join(project_dir, 'models'), 'models'),
    (os.path.join(project_dir, 'assets'), 'assets'),
]

if os.path.exists(os.path.join(project_dir, 'alia.jpg')):
    datas.append((os.path.join(project_dir, 'alia.jpg'), '.'))

datas += collect_data_files('customtkinter')

hiddenimports = [
    'customtkinter',
    'darkdetect',
    'cv2',
    'onnxruntime',
    'PIL',
    'PIL.Image',
    'PIL.ImageTk',
    'PIL.ImageDraw',
    'numpy',
    'face_engine',
    'ui',
    'pdf_exporter',
    'fpdf',
    'csv',
    'queue',
    'threading',
]
hiddenimports += collect_submodules('customtkinter')

excludes = [
    'torch',
    'torchvision',
    'transformers',
    'sympy',
    'scipy',
    'pandas',
    'matplotlib',
    'notebook',
    'jinja2',
    'fastapi',
    'streamlit',
    'altair',
    'pyarrow',
    'weasyprint',
    'IPython',
    'brotli'
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
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None
)
