# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec для FinFocus — onedir mode, portable."""

import os
from PyInstaller.utils.hooks import (
    collect_submodules,
    collect_data_files,
)

block_cipher = None

# Hidden imports: Dash/Plotly/dbc динамически подгружают модули
hiddenimports = [
    # Plotly validators (огромное дерево, importlib dynamic)
    *collect_submodules("plotly"),
    # Dash components
    *collect_submodules("dash"),
    *collect_submodules("dash_bootstrap_components"),
    # Flask internals
    "flask.json.provider",
    # SQLAlchemy dialects
    "sqlalchemy.dialects.sqlite",
    # Other
    "pkg_resources",
    "importlib.metadata",
]

# Data files: JS/JSON/CSS ресурсы Dash и Plotly
datas = [
    # App assets (CSS, JS)
    ("app/assets", "app/assets"),
    # Plotly JS bundle
    *collect_data_files("plotly"),
    # Dash renderer JS
    *collect_data_files("dash"),
    *collect_data_files("dash_bootstrap_components"),
    *collect_data_files("dash_core_components"),
    *collect_data_files("dash_html_components"),
    *collect_data_files("dash_table"),
]

a = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "alembic",
        "tkinter",
        "unittest",
        "pytest",
        "test",
    ],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # onedir mode
    name="FinFocus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # console для отладки; False для release
    icon=None,  # TODO: добавить иконку
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="FinFocus",
)
