import base64
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_cookie_warn_count = {}
_key_cache = {}

def _cookie_warn(msg):
    _cookie_warn_count[msg] = _cookie_warn_count.get(msg, 0) + 1
    if _cookie_warn_count[msg] <= 3:
        print(f"[animeiat-cli] Warning: {msg}")


try:
    from Cryptodome.Cipher import AES as _AES
except ImportError:
    try:
        from Crypto.Cipher import AES as _AES
    except ImportError:
        _AES = None


def get_user_data_path(browser_name):
    home = os.path.expanduser("~")
    if os.name == 'nt':
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            return None
        if browser_name == "chrome":
            return os.path.join(local_app_data, r"Google\Chrome\User Data")
        elif browser_name == "edge":
            return os.path.join(local_app_data, r"Microsoft\Edge\User Data")
    elif sys.platform == "darwin":
        if browser_name == "chrome":
            return os.path.join(home, "Library/Application Support/Google/Chrome")
        elif browser_name == "edge":
            return os.path.join(home, "Library/Application Support/Microsoft Edge")
    else:
        if browser_name == "chrome":
            return os.path.join(home, ".config/google-chrome")
        elif browser_name == "edge":
            return os.path.join(home, ".config/microsoft-edge")
    return None


def get_macos_key(browser_name):
    service = "Chrome Safe Storage" if browser_name == "chrome" else "Microsoft Edge Safe Storage"
    try:
        cmd = ["security", "find-generic-password", "-w", "-s", service]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
        return result.stdout.strip().encode("utf-8")
    except Exception as e:
        print(f"[animeiat-cli] Warning: macOS key query failed: {e}")
        try:
            import keyring
            key = keyring.get_password(service, "Chrome" if browser_name == "chrome" else "Microsoft Edge")
            if key:
                return key.encode("utf-8")
        except Exception as e2:
            print(f"[animeiat-cli] Warning: cookie query setup failed: {e2}")
    return None


def get_linux_key(browser_name):
    service = "Chrome Safe Storage" if browser_name == "chrome" else "Microsoft Edge Safe Storage"
    account = "Chrome" if browser_name == "chrome" else "edge"
    try:
        cmd = ["secret-tool", "lookup", "service", service, "account", account]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
        if result.stdout.strip():
            return result.stdout.strip().encode("utf-8")
    except Exception as e:
        print(f"[animeiat-cli] Warning: cookie DB query failed: {e}")

    try:
        cmd = ["secret-tool", "lookup", "xdg:schema", "org.chromium.Chromium.SafeStorage", "password", "chrome" if browser_name == "chrome" else "edge"]
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=True)
        if result.stdout.strip():
            return result.stdout.strip().encode("utf-8")
    except Exception as e:
        print(f"[animeiat-cli] Warning: cookie decryption failed: {e}")

    try:
        import keyring
        key = keyring.get_password(service, account)
        if key:
            return key.encode("utf-8")
    except Exception as e:
        print(f"[animeiat-cli] Warning: cookie processing failed: {e}")

    return b"peanuts"


def decrypt_cbc_cookie(encrypted_value, key):
    if not encrypted_value:
        return ""
    if not _AES:
        return ""
    if encrypted_value.startswith(b"v10") or encrypted_value.startswith(b"v11"):
        ciphertext = encrypted_value[3:]
    else:
        ciphertext = encrypted_value

    try:
        cipher = _AES.new(key, _AES.MODE_CBC, iv=b' ' * 16)
        decrypted = cipher.decrypt(ciphertext)
        padding_len = decrypted[-1]
        if 1 <= padding_len <= 16:
            if all(x == padding_len for x in decrypted[-padding_len:]):
                decrypted = decrypted[:-padding_len]
        return decrypted.decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[animeiat-cli] Warning: CBC cookie decrypt failed: {e}")
        return ""


def get_browser_cookies(browser_name):
    cached = _key_cache.get(browser_name)
    if cached:
        decrypted_key, is_gcm = cached
        return _read_cookies(browser_name, decrypted_key, is_gcm)

    user_data_path = get_user_data_path(browser_name)
    if not user_data_path or not os.path.exists(user_data_path):
        return []

    decrypted_key = None
    is_gcm = False
    win32crypt = None

    if os.name == 'nt':
        local_state_path = os.path.join(user_data_path, "Local State")
        if os.path.exists(local_state_path):
            try:
                with open(local_state_path, "r", encoding="utf-8") as f:
                    local_state = json.loads(f.read())
                encrypted_key = base64.b64decode(local_state["os_crypt"]["encrypted_key"])
                encrypted_key = encrypted_key[5:]
                try:
                    import win32crypt
                    decrypted_key = win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
                    is_gcm = True
                except ImportError:
                    pass
            except Exception as e:
                print(f"[animeiat-cli] Warning: local state decryption failed: {e}")
        if not decrypted_key:
            return []
    elif sys.platform == "darwin":
        password = get_macos_key(browser_name)
        if password:
            import hashlib
            decrypted_key = hashlib.pbkdf2_hmac("sha1", password, b"saltysalt", 1003, 16)
            is_gcm = False
        if not decrypted_key:
            return []
    else:
        password = get_linux_key(browser_name)
        if password:
            import hashlib
            decrypted_key = hashlib.pbkdf2_hmac("sha1", password, b"saltysalt", 1003, 16)
            is_gcm = False
        if not decrypted_key:
            return []

    _key_cache[browser_name] = (decrypted_key, is_gcm)
    return _read_cookies(user_data_path, decrypted_key, is_gcm)


def _read_cookies(user_data_path, decrypted_key, is_gcm):
    cookies = {}
    profiles = ["Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4", "Profile 5"]
    win32crypt = None
    if os.name == 'nt':
        try:
            import win32crypt
        except ImportError:
            pass

    try:
        for item in os.listdir(user_data_path):
            if (item.startswith("Profile") or item == "Default") and os.path.isdir(os.path.join(user_data_path, item)):
                if item not in profiles:
                    profiles.append(item)
    except Exception as e:
        print(f"[animeiat-cli] Warning: browser profile listing failed: {e}")

    for profile in profiles:
        cookie_path = os.path.join(user_data_path, profile, "Network", "Cookies")
        if not os.path.exists(cookie_path):
            cookie_path = os.path.join(user_data_path, profile, "Cookies")
        if not os.path.exists(cookie_path):
            continue

        conn = None
        try:
            conn = sqlite3.connect(cookie_path, timeout=1)
            conn.execute("PRAGMA query_only=ON")
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "SELECT name, encrypted_value, host_key FROM cookies WHERE host_key LIKE '%anime3rb.com%' OR host_key LIKE '%vid3rb.com%' OR host_key LIKE '%witanime%'"
                )
            except sqlite3.OperationalError:
                continue
            for name, encrypted_value, host_key in cursor.fetchall():
                domain = "." + host_key if not host_key.startswith(".") else host_key
                try:
                    if is_gcm:
                        if encrypted_value[:3] == b'v10' or encrypted_value[:3] == b'v11':
                            nonce = encrypted_value[3:15]
                            ciphertext = encrypted_value[15:-16]
                            tag = encrypted_value[-16:]
                            cipher = _AES.new(decrypted_key, _AES.MODE_GCM, nonce=nonce)
                            value = cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")
                        else:
                            if win32crypt:
                                value = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)[1].decode("utf-8")
                            else:
                                continue
                    else:
                        value = decrypt_cbc_cookie(encrypted_value, decrypted_key)

                    cookies[f"{domain}:{name}"] = {
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": "/"
                    }
                except Exception as e:
                    _cookie_warn(f"cookie decrypt failed: {e}")
                    cookies.pop(f"{domain}:{name}", None)
        except Exception as e:
            _cookie_warn(f"cookie profile failed: {e}")
        finally:
            if conn:
                conn.close()

    return list(cookies.values())


def get_preferred_cookies():
    from src.config import load_config
    cfg = load_config()
    pref = cfg.get("preferred_browser", "auto")
    if pref == "chrome":
        return get_browser_cookies("chrome")
    elif pref == "edge":
        return get_browser_cookies("edge")
    else:
        return get_browser_cookies("chrome") or get_browser_cookies("edge")
