# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for animeiat-cli.

Environment variables (set by build.py):
  ANIMEIAT_BUILD_LITE=1    -> exclude Chromium browser data
  ANIMEIAT_BUILD_ONEFILE=1 -> produce a single executable
"""

import os
import platform
import playwright
from PyInstaller.utils.hooks import collect_submodules, collect_data_files


_lite = os.environ.get("ANIMEIAT_BUILD_LITE") == "1"
_onefile = os.environ.get("ANIMEIAT_BUILD_ONEFILE") == "1"
_system = platform.system()


datas = []
binaries = []
hiddenimports = []
excludes = [
    "tkinter",
    "test",
    "pip",
    "unittest",
    "http.server",
    "pydoc",
]


hiddenimports += collect_submodules("lxml")
hiddenimports += collect_submodules("Cryptodome")
hiddenimports += [
    "playwright.sync_api",
    "playwright.async_api",
    "src.ui.cli",
    "src.ui.tui",
    "src.config",
    "src.db",
    "src.playback",
    "src.playback.discovery",
    "src.playback.launch",
    "src.playback.progress",
    "src.providers",
    "src.providers.anime3rb",
    "src.providers.anineko",
    "src.providers.witanime",
    "src.cache",
    "src.cache.stream_cache",
    "src.chromium",
]


if not _lite:
    datas += collect_data_files("playwright")

    playwright_dir = os.path.join(
        os.path.dirname(os.path.dirname(playwright.__file__)),
        "playwright",
    )
    browsers_dir = os.path.join(playwright_dir, "driver", "package", ".local-browsers")
    if os.path.isdir(browsers_dir):
        datas.append((browsers_dir, "playwright/driver/package/.local-browsers"))
        if _system == "Darwin":
            for root, dirs, files in os.walk(browsers_dir):
                for f in files:
                    fpath = os.path.join(root, f)
                    if fpath.endswith("Chromium.app"):
                        binaries.append((fpath, "."))


a = Analysis(
    [os.path.join(os.getcwd(), "anime_cli.py")],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    module_collection_mode={},
)

pyz = PYZ(a.pure)

if _onefile:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.datas,
        [],
        name="animeiat-cli",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=["**/Chromium.app/**"],
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        [],
        exclude_binaries=True,
        name="animeiat-cli",
        debug=False,
        bootloader_ignore_signals=False,
        strip=False,
        upx=True,
        upx_exclude=["**/Chromium.app/**"],
        console=True,
        disable_windowed_traceback=False,
        argv_emulation=False,
        target_arch=None,
        codesign_identity=None,
        entitlements_file=None,
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        upx_exclude=["**/Chromium.app/**"],
        name="animeiat-cli",
    )
