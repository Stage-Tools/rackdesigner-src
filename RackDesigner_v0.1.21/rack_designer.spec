# -*- mode: python ; coding: utf-8 -*-
# Rack Designer
# Copyright (C) 2026 Riccardo Nessi
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


from PyInstaller.utils.hooks import collect_all

block_cipher = None

# PyMuPDF (imported as `fitz`, used by app.pdf_export.export_rack_png() to
# rasterize PDF -> PNG) is a known PyInstaller gotcha: its compiled
# extensions (_mupdf.pyd, _extra.pyd) and mupdfcpp64.dll aren't reliably
# picked up by static import analysis alone, since pymupdf/__init__.py loads
# them dynamically rather than via a plain top-level `import`. collect_all()
# is the standard fix (equivalent to `pyinstaller --collect-all pymupdf`) --
# collected for both `pymupdf` (the real package) and `fitz` (the thin
# `from pymupdf import *` compatibility shim actually imported in code),
# since `fitz` ships its own small datas set on top of what `pymupdf`
# resolves to. Not yet exercised by a real build this session -- see
# task.md #65.
_pymupdf_datas, _pymupdf_binaries, _pymupdf_hidden = collect_all('pymupdf')
_fitz_datas, _fitz_binaries, _fitz_hidden = collect_all('fitz')

# Drop PyMuPDF's C/C++ development headers and import libraries (.h/.lib under
# mupdf-devel/): build-time material only, never used at runtime.
def _no_devel(items):
    return [i for i in items if 'mupdf-devel' not in (str(i[0]) + str(i[1])).replace(chr(92), '/')]

_pymupdf_datas = _no_devel(_pymupdf_datas)
_pymupdf_binaries = _no_devel(_pymupdf_binaries)
_fitz_datas = _no_devel(_fitz_datas)
_fitz_binaries = _no_devel(_fitz_binaries)

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        *_pymupdf_binaries,
        *_fitz_binaries,
    ],
    datas=[
        *_pymupdf_datas,
        *_fitz_datas,
    ],
    hiddenimports=[
        'reportlab.graphics',
        'reportlab.platypus',
        'reportlab.lib.pagesizes',
        'reportlab.lib.units',
        'reportlab.lib.styles',
        'reportlab.lib.colors',
        'reportlab.platypus.flowables',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
        'PIL.ImageFont',
        *_pymupdf_hidden,
        *_fitz_hidden,
    ],
    hookspath=[],
    hooksconfig={
        'PyQt6': {
            'binaries': True,
        }
    },
    runtime_hooks=[],
    excludes=[
        'PySide6',
        'shiboken6',
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
        'cv2',
        'test',
        'unittest',
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
    # Not derived from app.APP_VERSION (app/__init__.py) — this is build
    # tooling, not Python app code, so it can't import that constant.
    # Bump this by hand on every version change; it won't follow APP_VERSION
    # automatically.
    name='RackDesigner_v0.1.21',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.ico',
)
