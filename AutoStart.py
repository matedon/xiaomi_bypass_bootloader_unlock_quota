"""
AutoStart.py bootstrap launcher.

Starts AutoJobs.py in a dedicated console window, places that window in column 1,
and then closes the current launcher window.
"""

import ctypes
import os
import subprocess
import sys
import time
from ctypes import wintypes

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUTOJOBS_FILE = os.path.join(BASE_DIR, "AutoJobs.py")
AUTOJOBS_WINDOW_TITLE = "AutoJobsMain"
LAUNCHER_BAT = os.path.join(BASE_DIR, "_autostart_launch_autojobs.bat")


def get_work_area():
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


def get_first_column_rect():
    wx, wy, ww, wh = get_work_area()
    col1_w = ww // 3
    return wx, wy, col1_w, wh


def find_window_by_title_substring(substring, timeout_seconds=15):
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

    found = {"hwnd": None}

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        if substring in buf.value:
            found["hwnd"] = hwnd
            return False
        return True

    cb = WNDENUMPROC(_cb)

    end_time = time.time() + timeout_seconds
    while time.time() < end_time:
        found["hwnd"] = None
        user32.EnumWindows(cb, 0)
        if found["hwnd"]:
            return found["hwnd"]
        time.sleep(0.1)

    return None


def place_window_in_first_column(hwnd):
    user32 = ctypes.windll.user32
    x, y, w, h = get_first_column_rect()

    SW_RESTORE = 9
    SWP_SHOWWINDOW = 0x0040

    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.05)
    user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_SHOWWINDOW)


def build_launcher_bat():
    py = sys.executable
    with open(LAUNCHER_BAT, "w", encoding="utf-8") as bf:
        bf.write("@echo off\n")
        bf.write(f"title {AUTOJOBS_WINDOW_TITLE}\n")
        bf.write(f"cd /d \"{BASE_DIR}\"\n")
        bf.write(f"\"{py}\" \"{AUTOJOBS_FILE}\"\n")


def launch_autojobs_window():
    if not os.path.exists(AUTOJOBS_FILE):
        print(f"[ERR] Missing file: {AUTOJOBS_FILE}")
        return False

    build_launcher_bat()
    subprocess.Popen(f'start "{AUTOJOBS_WINDOW_TITLE}" cmd /k "{LAUNCHER_BAT}"', shell=True)

    hwnd = find_window_by_title_substring(AUTOJOBS_WINDOW_TITLE, timeout_seconds=20)
    if hwnd:
        place_window_in_first_column(hwnd)
        print("[OK] AutoJobs window launched and placed in column 1.")
    else:
        print("[!] AutoJobs window started, but could not be positioned automatically.")

    try:
        os.remove(LAUNCHER_BAT)
    except Exception:
        pass

    return True


def close_current_console_window():
    kernel32 = ctypes.windll.kernel32
    user32 = ctypes.windll.user32
    hwnd = kernel32.GetConsoleWindow()
    if not hwnd:
        return
    WM_CLOSE = 0x0010
    user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)


def main():
    print("[i] Starting AutoJobs launcher...")
    ok = launch_autojobs_window()
    if not ok:
        input("Press Enter to exit...")
        sys.exit(1)

    # Close the launcher window after handing over control to AutoJobs.
    close_current_console_window()


if __name__ == "__main__":
    main()
