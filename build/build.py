#!/usr/bin/env python3
"""
Build script for animeiat-cli.

Creates standalone executables using PyInstaller.
One command for all platforms.

Usage:
  python build.py              onedir (default) + bundled Chromium
  python build.py --onedir     onedir + bundled Chromium
  python build.py --onefile    single executable + bundled Chromium
  python build.py --lite       onedir, no Chromium (downloads on first-run)
  python build.py --check      validate build environment only
  python build.py --clean      remove previous build artifacts
"""

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import time


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC_FILE = os.path.join(PROJECT_ROOT, "build", "animeiat-cli.spec")
DIST_DIR = os.path.join(PROJECT_ROOT, "dist")
BUILD_DIR = os.path.join(PROJECT_ROOT, "build")
PYPROJECT_FILE = os.path.join(PROJECT_ROOT, "pyproject.toml")


def _read_version():
    try:
        with open(PYPROJECT_FILE, encoding="utf-8") as f:
            m = re.search(r'^version\s*=\s*"([^"]+)"', f.read(), re.MULTILINE)
            if m:
                return m.group(1)
    except Exception:
        pass
    return "0.0.0"


VERSION = _read_version()
APP_NAME = f"animeiat-cli v{VERSION}"


def _print_banner():
    print(f"{'=' * 56}")
    print(f"  {APP_NAME} — Build Script")
    print(f"  Platform: {platform.system()} ({platform.machine()})")
    print(f"  Python:   {platform.python_version()}")
    print(f"{'=' * 56}")


def _run(cmd, **kwargs):
    sys.stdout.flush()
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"[!] Command failed: {' '.join(cmd)}")
        sys.exit(result.returncode)
    return result


def _check_python():
    ver = tuple(map(int, platform.python_version_tuple()[:2]))
    if ver < (3, 10):
        print("[!] Python >= 3.10 required")
        sys.exit(1)
    print(f"[ok] Python {platform.python_version()}")


def _ensure_pyinstaller():
    try:
        import PyInstaller
        print(f"[ok] PyInstaller {PyInstaller.__version__}")
    except ImportError:
        print("[*] Installing PyInstaller...")
        _run([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[ok] PyInstaller installed")
        import PyInstaller


def _ensure_chromium_installed():
    env = os.environ.copy()
    env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
    try:
        import playwright
        has_playwright = True
    except ImportError:
        has_playwright = False

    if has_playwright:
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
            capture_output=True, text=True, env=env,
        )
        if "already exists" in result.stdout or "already" in result.stdout.lower():
            print("[ok] Chromium browser already installed")
            return

    print("[*] Installing Playwright Chromium browser...")
    _run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        env=env,
    )
    print("[ok] Chromium browser installed")


def _clean_artifacts():
    dist_dir = os.path.join(PROJECT_ROOT, "dist")
    if os.path.isdir(dist_dir):
        print(f"  rm -r {os.path.relpath(dist_dir, PROJECT_ROOT)}")
        shutil.rmtree(dist_dir, ignore_errors=True)

    for d in ("pyinstaller-work",):
        path = os.path.join(PROJECT_ROOT, "build", d)
        if os.path.isdir(path):
            print(f"  rm -r {os.path.relpath(path, PROJECT_ROOT)}")
            shutil.rmtree(path, ignore_errors=True)

    for root, dirs, files in os.walk(PROJECT_ROOT):
        base = os.path.relpath(root, PROJECT_ROOT)
        if base.startswith(".") or "site-packages" in base:
            continue
        if base.startswith("build") and not base.startswith("build\\"):
            continue
        for d in dirs:
            if d == "__pycache__":
                full = os.path.join(root, d)
                print(f"  rm -r {os.path.relpath(full, PROJECT_ROOT)}")
                shutil.rmtree(full, ignore_errors=True)

    print("[ok] Cleaned build artifacts")


def _validate_output(output_path):
    if not os.path.exists(output_path):
        print(f"[!] Output not found: {output_path}")
        return False

    size = os.path.getsize(output_path)
    if os.path.isdir(output_path):
        total = 0
        for root, dirs, files in os.walk(output_path):
            for f in files:
                total += os.path.getsize(os.path.join(root, f))
        print(f"[ok] Output: {os.path.relpath(output_path, PROJECT_ROOT)} ({_fmt_size(total)})")
    else:
        print(f"[ok] Output: {os.path.relpath(output_path, PROJECT_ROOT)} ({_fmt_size(size)})")

    if platform.system() == "Windows":
        exe_path = os.path.join(output_path, "animeiat-cli.exe") if os.path.isdir(output_path) else output_path
    else:
        exe_path = os.path.join(output_path, "animeiat-cli") if os.path.isdir(output_path) else output_path

    if os.path.exists(exe_path):
        try:
            result = subprocess.run(
                [exe_path, "--version"],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                output = (result.stdout or result.stderr).strip()
                print(f"[ok] Validation: {output}")
            else:
                print(f"[!] Validation warning: exit code {result.returncode}")
        except FileNotFoundError:
            print(f"[!] Validation skipped (executable not found at {exe_path})")
        except subprocess.TimeoutExpired:
            print("[!] Validation skipped (timeout)")
        except Exception as e:
            print(f"[!] Validation skipped: {e}")

    return True


def _fmt_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _pkg_ver(name):
    try:
        from importlib.metadata import version as _iv
        return _iv(name)
    except Exception:
        return "installed"


def _cmd_check():
    print(f"\n[*] Checking build environment for {APP_NAME}")
    print()

    print(f"  Platform:    {platform.system()} {platform.release()} ({platform.machine()})")
    _check_python()

    try:
        import PyInstaller
        print(f"  PyInstaller: {PyInstaller.__version__}")
    except ImportError:
        print("  PyInstaller: not installed (will be auto-installed during build)")

    try:
        import playwright
        print(f"  Playwright:  {_pkg_ver('playwright')}")
    except ImportError:
        print("  Playwright:  not installed")

    try:
        import lxml
        print(f"  lxml:        {_pkg_ver('lxml')}")
    except ImportError:
        print("  lxml:        not installed")

    try:
        from Cryptodome import __version__ as crypt_ver
        print(f"  pycryptodome: {crypt_ver}")
    except ImportError:
        try:
            from Crypto import __version__ as crypt_ver
            print(f"  pycryptodome: {crypt_ver} (Crypto compat)")
        except ImportError:
            print("  pycryptodome: not installed")

    try:
        import rich
        print(f"  rich:        {_pkg_ver('rich')}")
    except ImportError:
        print("  rich:        not installed")

    try:
        import httpx
        print(f"  httpx:       {_pkg_ver('httpx')}")
    except ImportError:
        print("  httpx:       not installed")

    print()
    print(f"  Spec file:   {os.path.relpath(SPEC_FILE, PROJECT_ROOT)}")
    print(f"  Entry point: anime_cli.py")
    print(f"  Output:      dist/")

    cwd_size = _fmt_size(
        sum(os.path.getsize(os.path.join(root, f)) for root, _, files in os.walk(PROJECT_ROOT) for f in files)
    )
    print(f"  Project size: {cwd_size}")

    has_chromium = False
    try:
        import playwright
        browsers = os.path.join(
            os.path.dirname(playwright.__file__),
            "driver", "package", ".local-browsers",
        )
        has_chromium = os.path.isdir(browsers) and any(
            "chromium" in d.lower()
            for d in os.listdir(browsers)
        )
    except Exception:
        pass
    print(f"  Chromium bundled: {'yes' if has_chromium else 'no (run build once to install)'}")

    print()
    print("[ok] Environment check complete")


def _cmd_build(args):
    _print_banner()
    print()

    _check_python()
    _ensure_pyinstaller()

    if not os.path.isfile(SPEC_FILE):
        print(f"[!] Spec file not found: {SPEC_FILE}")
        sys.exit(1)

    if not args.lite:
        _ensure_chromium_installed()

    start = time.time()

    env = os.environ.copy()
    env["ANIMEIAT_BUILD_LITE"] = "1" if args.lite else "0"
    env["ANIMEIAT_BUILD_ONEFILE"] = "1" if args.onefile else "0"

    spec_rel = os.path.relpath(SPEC_FILE, PROJECT_ROOT)
    print(f"[*] Building: {spec_rel}")
    print(f"    Mode:     {'--onefile' if args.onefile else '--onedir'}")
    print(f"    Chromium: {'lite (download on first-run)' if args.lite else 'bundled'}")

    workpath = os.path.join(PROJECT_ROOT, "build", "pyinstaller-work")
    _run(
        [
            sys.executable, "-m", "PyInstaller", spec_rel,
            "--workpath", workpath,
            "--distpath", DIST_DIR,
        ],
        cwd=PROJECT_ROOT,
        env=env,
    )

    elapsed = time.time() - start
    print(f"[ok] Build completed in {elapsed:.1f}s")

    dist_name = "animeiat-cli"
    if platform.system() == "Windows" and args.onefile:
        dist_name += ".exe"
    output_path = os.path.join(DIST_DIR, dist_name)

    _validate_output(output_path)


def _parse_args():
    parser = argparse.ArgumentParser(
        description=f"Build {APP_NAME}.py into a standalone executable.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--onedir",
        action="store_true",
        default=True,
        dest="onedir",
        help="Build as directory (default, faster startup)",
    )
    mode.add_argument(
        "--onefile",
        action="store_true",
        help="Build as single executable file",
    )
    parser.add_argument(
        "--lite",
        action="store_true",
        help="Exclude Chromium from bundle (downloads on first run)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate build environment without building",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove previous build artifacts",
    )

    args = parser.parse_args()

    if args.onefile:
        args.onedir = False

    return args


def main():
    args = _parse_args()

    if args.check:
        _cmd_check()
        return

    if args.clean:
        print(f"[*] Cleaning build artifacts for {APP_NAME}")
        _clean_artifacts()
        return

    _cmd_build(args)


if __name__ == "__main__":
    main()
