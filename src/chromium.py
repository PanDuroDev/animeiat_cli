import os
import subprocess
import sys


def ensure_chromium() -> bool:
    """Install Playwright Chromium browser if not present.
    Returns True if Chromium is available after the call.
    """
    try:
        import playwright
    except ImportError:
        return False

    browsers_dir = os.path.join(
        os.path.dirname(playwright.__file__),
        "driver", "package", ".local-browsers",
    )
    if os.path.isdir(browsers_dir) and any(
        "chromium" in d.lower()
        for d in os.listdir(browsers_dir)
    ):
        return True

    print("[*] Chromium browser not found. Installing...")
    print("    (This is a one-time setup; ~150MB download)")
    try:
        env = os.environ.copy()
        env["PLAYWRIGHT_BROWSERS_PATH"] = "0"
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            env=env, check=True,
        )
        print("[ok] Chromium browser installed")
        return True
    except Exception as e:
        print(f"[!] Failed to install Chromium: {e}")
        print("    You can install it manually: playwright install chromium")
        return False


async def ensure_chromium_async() -> bool:
    """Async wrapper around ensure_chromium()."""
    return ensure_chromium()
