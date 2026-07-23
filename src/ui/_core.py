"""
Core TUI primitives — terminal I/O, key reading, raw mode, constants.
"""
import asyncio
import os
import shutil
import sys
import time

_shared_loop = None

def _run_async(coro):
    global _shared_loop
    if _shared_loop is None or _shared_loop.is_closed():
        _shared_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(_shared_loop)
    return _shared_loop.run_until_complete(coro)

_ANIM_DURATION = 0.3
_DRAG_THRESHOLD = 1.0
_PAGE_SIZE = 50
_LAYOUT_SPLIT = (40, 60)
_REFRESH_RATE = 20

if os.name == 'nt':
    import msvcrt
else:
    import tty
    import termios
    import select

KEY_UP = "up"
KEY_DOWN = "down"
KEY_ENTER = "enter"
KEY_SPACE = "space"
KEY_ESC = "esc"
KEY_CTRL_C = "ctrl_c"
KEY_A = "a"
KEY_UNKNOWN = "unknown"

_in_raw_mode = False
_raw_fd = None

def _should_sync():
    return False

class RawModeContext:
    def __enter__(self):
        global _in_raw_mode, _raw_fd
        if os.name != 'nt' and sys.stdin.isatty():
            try:
                self.fd = sys.stdin.fileno()
                self.old_settings = termios.tcgetattr(self.fd)
                new_settings = termios.tcgetattr(self.fd)
                new_settings[0] &= ~(termios.BRKINT | termios.ICRNL | termios.INPCK | termios.ISTRIP | termios.IXON)
                new_settings[3] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
                new_settings[6][termios.VMIN] = 1
                new_settings[6][termios.VTIME] = 0
                termios.tcsetattr(self.fd, termios.TCSADRAIN, new_settings)
                _in_raw_mode = True
                _raw_fd = self.fd
            except Exception:
                self.fd = None
                self.old_settings = None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _in_raw_mode, _raw_fd
        if os.name != 'nt' and getattr(self, 'fd', None) is not None and getattr(self, 'old_settings', None) is not None:
            try:
                termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)
            except Exception:
                pass
            _in_raw_mode = False
            _raw_fd = None

def read_key():
    if os.name == 'nt':
        try:
            ch = msvcrt.getwch()
            if ch in ('\x00', '\xe0'):
                ch += msvcrt.getwch()
            if ch in ('\xe0H', '\x00H'): return KEY_UP
            if ch in ('\xe0P', '\x00P'): return KEY_DOWN
            if ch in ('\r', '\n'): return KEY_ENTER
            if ch == ' ': return KEY_SPACE
            if ch in ('\x08', '\x7f'): return '\x08'
            if ch == '\x03': return KEY_CTRL_C
            if ch == '\x1b':
                seq = ch
                while msvcrt.kbhit() and len(seq) < 6:
                    seq += msvcrt.getwch()
                    if seq[-1].isalpha() or seq[-1] == '~':
                        break
                if seq == '\x1b[A': return KEY_UP
                if seq == '\x1b[B': return KEY_DOWN
                return KEY_ESC
            if ch in ('a', 'A'): return KEY_A
            if len(ch) == 1:
                return ch
            return KEY_UNKNOWN
        except Exception:
            return KEY_UNKNOWN
    else:
        if not sys.stdin.isatty():
            try:
                ch = sys.stdin.read(1)
                if not ch:
                    return KEY_ESC
                if ch in ('\r', '\n'): return KEY_ENTER
                if ch == ' ': return KEY_SPACE
                if ch in ('a', 'A'): return KEY_A
                return ch
            except Exception:
                return KEY_ESC

        if _in_raw_mode and _raw_fd is not None:
            try:
                b = os.read(_raw_fd, 1)
                if not b:
                    return KEY_ESC
                if b == b'\x1b':
                    r, _, _ = select.select([_raw_fd], [], [], 0.05)
                    if r:
                        extra = os.read(_raw_fd, 2)
                        if extra == b'[A': return KEY_UP
                        if extra == b'[B': return KEY_DOWN
                    return KEY_ESC
                if b in (b'\r', b'\n'): return KEY_ENTER
                if b == b' ': return KEY_SPACE
                if b == b'\x03': return KEY_CTRL_C
                if b in (b'a', b'A'): return KEY_A
                return b.decode('utf-8', errors='ignore')
            except Exception:
                return KEY_UNKNOWN
        else:
            try:
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
            except Exception:
                try:
                    ch = sys.stdin.read(1)
                    if not ch: return KEY_ESC
                    return ch
                except Exception:
                    return KEY_UNKNOWN
            try:
                new_settings = termios.tcgetattr(fd)
                new_settings[0] &= ~(termios.BRKINT | termios.ICRNL | termios.INPCK | termios.ISTRIP | termios.IXON)
                new_settings[3] &= ~(termios.ECHO | termios.ICANON | termios.IEXTEN | termios.ISIG)
                new_settings[6][termios.VMIN] = 1
                new_settings[6][termios.VTIME] = 0
                termios.tcsetattr(fd, termios.TCSADRAIN, new_settings)
                r, _, _ = select.select([fd], [], [])
                if not r:
                    return KEY_UNKNOWN
                b = os.read(fd, 1)
                if not b:
                    return KEY_ESC
                if b == b'\x1b':
                    r, _, _ = select.select([fd], [], [], 0.05)
                    if r:
                        extra = os.read(fd, 2)
                        if extra == b'[A': return KEY_UP
                        if extra == b'[B': return KEY_DOWN
                    return KEY_ESC
                if b in (b'\r', b'\n'): return KEY_ENTER
                if b == b' ': return KEY_SPACE
                if b == b'\x03': return KEY_CTRL_C
                if b in (b'a', b'A'): return KEY_A
                return b.decode('utf-8', errors='ignore')
            except Exception:
                return KEY_UNKNOWN
            finally:
                try:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass

def flush_input_buffer():
    if os.name == 'nt':
        try:
            while msvcrt.kbhit():
                msvcrt.getwch()
        except Exception:
            pass
    else:
        try:
            import select as sel_mod
            while sel_mod.select([sys.stdin], [], [], 0)[0]:
                sys.stdin.read(1)
        except Exception:
            pass

def clear_screen():
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()

def enter_alt_screen():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?1049h")
        sys.stdout.flush()

def exit_alt_screen():
    if sys.stdout.isatty():
        sys.stdout.write("\033[?1049l")
        sys.stdout.flush()

def set_terminal_title(title):
    if sys.stdout.isatty():
        sys.stdout.write(f"\033]0;{title}\007")
        sys.stdout.flush()

def detect_layout_mode(width=None, height=None):
    if width is None or height is None:
        width, height = shutil.get_terminal_size()
    if height < 20 or width < 75:
        return "MINIMAL"
    return "NORMAL"
