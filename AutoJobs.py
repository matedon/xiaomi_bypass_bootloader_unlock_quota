"""
AutoJobs.py

1. Reads email and password from account.txt
2. Logs into Mi Community Global in Chrome and Firefox
3. Extracts new_bbs_serviceToken and popRunToken cookies
4. Updates token.txt
5. Starts NScript.py in 4 separate windows (token rows: 1, 2, 3, 4)
"""

import ctypes
import os
import random
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from ctypes import wintypes

# Auto-install missing packages.
_required = ["selenium"]
for _pkg in _required:
    try:
        __import__(_pkg)
    except ImportError:
        print(f"[!] Installing: {_pkg} ...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", _pkg])

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import tkinter as tk
from tkinter import ttk

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNT_FILE = os.path.join(BASE_DIR, "account.txt")
ACCOUNT_DEFAULT = os.path.join(BASE_DIR, "account_default.txt")
TOKEN_FILE = os.path.join(BASE_DIR, "token.txt")
SCRIPT_FILE = os.path.join(BASE_DIR, "NScript.py")
LOGIN_URL = "https://c.mi.com/global/"
LOGOUT_CALLBACK_URL = "https://c.mi.com/global/"
LOGOUT_URL = (
    "https://sgp-api.buy.mi.com/bbs/api/global/user/login-out"
    f"?callbackurl={urllib.parse.quote(LOGOUT_CALLBACK_URL, safe='')}"
)
REFRESH_INTERVAL = 20 * 60  # seconds
SCRIPT_WIN_TITLES = [f"ScriptWin{i}" for i in range(1, 5)]
AUTOJOBS_WINDOW_TITLE = "AutoJobsMain"

_CURRENT_SCRIPT_PIDS = []  # wrapper process IDs started by this run
_LAST_BROWSER_TOKENS = {
    "chrome": {"bbs": None, "pop": None},
    "firefox": {"bbs": None, "pop": None},
}


def get_work_area():
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0)  # SPI_GETWORKAREA
    x = rect.left
    y = rect.top
    w = rect.right - rect.left
    h = rect.bottom - rect.top
    return x, y, w, h


def get_layout_rects():
    wx, wy, ww, wh = get_work_area()

    col1_w = ww // 3
    col2_w = ww // 3
    col3_w = ww - col1_w - col2_w

    col1 = (wx, wy, col1_w, wh)
    right_x = wx + col1_w
    right_w = col2_w + col3_w
    right_panel = (right_x, wy, right_w, wh)

    return {
        "col1": col1,
        "right_panel": right_panel,
    }


def layout_autojobs_console():
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = kernel32.GetConsoleWindow()
    if not hwnd:
        return

    x, y, w, h = get_layout_rects()["col1"]
    SW_RESTORE = 9
    SWP_SHOWWINDOW = 0x0040

    user32.ShowWindow(hwnd, SW_RESTORE)
    time.sleep(0.05)
    user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_SHOWWINDOW)


def layout_browser_window(driver):
    # Browser windows always occupy the full right 2/3 area (columns 2 + 3).
    x, y, w, h = get_layout_rects()["right_panel"]

    try:
        driver.set_window_rect(x, y, w, h)
    except Exception:
        try:
            driver.set_window_size(w, h)
        except Exception:
            pass


def show_prompt(title, message):
    root = tk.Tk()
    root.title(title)
    root.resizable(False, False)
    w, h = 460, 160
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth()-w)//2}+{(root.winfo_screenheight()-h)//2}")
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))

    frm = ttk.Frame(root, padding=14)
    frm.pack(expand=True, fill=tk.BOTH)
    ttk.Label(frm, text=message, wraplength=w - 28, justify=tk.LEFT).pack(pady=(4, 14), anchor=tk.W)

    def on_ok():
        root.destroy()

    ttk.Button(frm, text="OK - Continue", command=on_ok).pack(side=tk.BOTTOM)
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.mainloop()


def ask_credentials_gui():
    """Prompt for email and password, then save them into account.txt."""
    result = {"ok": False, "user": "", "pwd": ""}

    root = tk.Tk()
    root.title("Enter Account Credentials")
    root.resizable(False, False)
    w, h = 420, 210
    root.geometry(f"{w}x{h}+{(root.winfo_screenwidth()-w)//2}+{(root.winfo_screenheight()-h)//2}")
    root.attributes("-topmost", True)

    frm = ttk.Frame(root, padding=16)
    frm.pack(expand=True, fill=tk.BOTH)

    ttk.Label(frm, text="Email / Xiaomi account:").grid(row=0, column=0, sticky=tk.W, pady=4)
    user_var = tk.StringVar()
    ttk.Entry(frm, textvariable=user_var, width=34).grid(row=0, column=1, pady=4)

    ttk.Label(frm, text="Password:").grid(row=1, column=0, sticky=tk.W, pady=4)
    pwd_var = tk.StringVar()
    ttk.Entry(frm, textvariable=pwd_var, show="*", width=34).grid(row=1, column=1, pady=4)

    def on_save():
        u = user_var.get().strip()
        p = pwd_var.get().strip()
        if not u or not p:
            return
        result["ok"] = True
        result["user"] = u
        result["pwd"] = p
        root.destroy()

    ttk.Button(frm, text="Save and Continue", command=on_save).grid(
        row=2, column=0, columnspan=2, pady=12
    )

    root.protocol("WM_DELETE_WINDOW", lambda: None)
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.mainloop()

    if not result["ok"]:
        print("[!] Credentials were not provided. Exiting.")
        sys.exit(1)

    with open(ACCOUNT_FILE, "w", encoding="utf-8") as f:
        f.write(f"{result['user']}\n{result['pwd']}\n")
    print(f"[OK] Credentials saved: {ACCOUNT_FILE}")
    return result["user"], result["pwd"]


def _read_account_file(path):
    if not os.path.exists(path):
        return None, None
    with open(path, "r", encoding="utf-8") as f:
        lines = [ln.strip() for ln in f if ln.strip()]
    if len(lines) < 2:
        return None, None
    return lines[0], lines[1]


def read_credentials():
    default_user = "email@example.com"
    default_pass = "password"

    if not os.path.exists(ACCOUNT_DEFAULT):
        with open(ACCOUNT_DEFAULT, "w", encoding="utf-8") as f:
            f.write(f"{default_user}\n{default_pass}\n")

    def_user, def_pass = _read_account_file(ACCOUNT_DEFAULT)
    cur_user, cur_pass = _read_account_file(ACCOUNT_FILE)

    need_gui = (
        cur_user is None
        or not cur_user
        or (cur_user == (def_user or default_user) and cur_pass == (def_pass or default_pass))
    )

    if need_gui:
        print("[!] Missing/default credentials detected. Opening GUI prompt.")
        return ask_credentials_gui()

    return cur_user, cur_pass


def _safe_click(driver, css, timeout=6):
    """Click element if available and clickable; silently fail otherwise."""
    try:
        el = WebDriverWait(driver, timeout).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css)))
        el.click()
        return True
    except Exception:
        return False


def _wait_ready(driver, extra_ms=300):
    """Wait for document.readyState == complete, then sleep extra_ms."""
    try:
        WebDriverWait(driver, 15).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
    except Exception:
        pass
    time.sleep(extra_ms / 1000)


def _do_login(driver, username, password, browser_label):
    """Run full login flow and return (bbs_token, pop_token)."""
    wait = WebDriverWait(driver, 40)
    bbs_token = None
    pop_token = None

    print(f"[i] [{browser_label}] Opening: {LOGIN_URL}")
    driver.get(LOGIN_URL)
    WebDriverWait(driver, 20).until(lambda d: d.current_url != "data:,")
    _wait_ready(driver)
    print(f"[i] [{browser_label}] Page loaded: {driver.current_url}")

    if _safe_click(driver, "#truste-consent-button", timeout=5):
        print(f"[OK] [{browser_label}] Cookie consent accepted (#truste-consent-button).")
        _wait_ready(driver)
    elif _safe_click(driver, ".acceptAllButtonLower", timeout=3):
        print(f"[OK] [{browser_label}] Cookie consent accepted (.acceptAllButtonLower fallback).")
        _wait_ready(driver)
    else:
        print(f"[i] [{browser_label}] Cookie banner did not appear.")

    if _safe_click(driver, ".pdynamicbutton .close", timeout=5):
        print(f"[OK] [{browser_label}] Popup closed.")
        _wait_ready(driver)
    else:
        print(f"[i] [{browser_label}] Popup did not appear.")

    if not _safe_click(driver, ".login-btn", timeout=10):
        print(f"[!] [{browser_label}] .login-btn not found. Manual click required.")
        show_prompt(
            f"Login button ({browser_label})",
            f"Please click the Login button in the {browser_label} window, then press OK.",
        )
    else:
        print(f"[OK] [{browser_label}] Login button clicked.")

    print(f"[i] [{browser_label}] Waiting for login form...")
    email_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='account']")))
    print(f"[OK] [{browser_label}] Form loaded.")

    email_field.clear()
    email_field.send_keys(username)
    print(f"[OK] [{browser_label}] Email entered.")
    time.sleep(0.4)

    pass_field = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[name='password']")))
    pass_field.clear()
    pass_field.send_keys(password)
    print(f"[OK] [{browser_label}] Password entered.")
    time.sleep(0.3)

    try:
        cb_inner = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".mi-accept-terms .ant-checkbox-inner"))
        )
        driver.execute_script("arguments[0].click();", cb_inner)
        print(f"[OK] [{browser_label}] Terms checkbox checked.")
    except Exception:
        try:
            driver.execute_script(
                """
                var cb = document.querySelector('.mi-accept-terms input.ant-checkbox-input');
                if (cb && !cb.checked) { cb.click(); }
                """
            )
            print(f"[OK] [{browser_label}] Terms checkbox checked (JS fallback).")
        except Exception:
            print(f"[i] [{browser_label}] Terms checkbox not found.")
    time.sleep(0.3)

    sign_in_css = "button.mi-button--primary.mi-button--fullwidth[type='submit']"
    if not _safe_click(driver, sign_in_css, timeout=8):
        if not _safe_click(driver, "button[type='submit']", timeout=5):
            print(f"[!] [{browser_label}] Sign in button not found. Manual action required.")
            show_prompt(
                f"Sign in ({browser_label})",
                f"Please press Sign in in the {browser_label} window, then click OK.",
            )
    else:
        print(f"[OK] [{browser_label}] Sign in submitted.")

    print(f"[i] [{browser_label}] Waiting for successful login...")

    def logged_in(d):
        url = d.current_url
        return "c.mi.com/global" in url and "login" not in url and "account.xiaomi.com" not in url

    try:
        WebDriverWait(driver, 15).until(logged_in)
        print(f"[OK] [{browser_label}] Logged in: {driver.current_url}")
    except Exception:
        print(f"[!] [{browser_label}] Auto login did not finish. reCAPTCHA or 2FA may be required.")
        show_prompt(
            f"Manual verification ({browser_label})",
            f"reCAPTCHA or 2FA appeared.\n\n"
            f"Please complete it in the {browser_label} window,\n"
            f"then click OK.",
        )
        try:
            WebDriverWait(driver, 180).until(logged_in)
            print(f"[OK] [{browser_label}] Logged in: {driver.current_url}")
        except Exception:
            print(f"[ERR] [{browser_label}] Timeout: login failed.")
            return None, None

    time.sleep(3)

    for c in driver.get_cookies():
        if c["name"] == "new_bbs_serviceToken":
            bbs_token = c["value"]
        elif c["name"] == "popRunToken":
            pop_token = c["value"]

    if not pop_token:
        try:
            pop_token = driver.execute_script(
                "var m = document.cookie.match(/popRunToken=([^;]+)/); return m ? m[1] : null;"
            )
        except Exception:
            pass

    if not bbs_token:
        try:
            bbs_token = driver.execute_script(
                "var m = document.cookie.match(/new_bbs_serviceToken=([^;]+)/); return m ? m[1] : null;"
            )
        except Exception:
            pass

    return bbs_token, pop_token


def login_chrome(username, password):
    opts = ChromeOptions()
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-extensions")

    print("[i] Starting Chrome...")
    driver = webdriver.Chrome(options=opts)

    layout_autojobs_console()
    layout_browser_window(driver)

    try:
        return _do_login(driver, username, password, "Chrome")
    except Exception as e:
        print(f"[ERR] Chrome error: {e}")
        show_prompt("Chrome error", f"Error during Chrome login:\n{e}")
        return None, None
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def login_firefox(username, password):
    opts = FirefoxOptions()

    print("[i] Starting Firefox...")
    driver = webdriver.Firefox(options=opts)

    layout_autojobs_console()
    layout_browser_window(driver)

    try:
        return _do_login(driver, username, password, "Firefox")
    except Exception as e:
        print(f"[ERR] Firefox error: {e}")
        show_prompt("Firefox error", f"Error during Firefox login:\n{e}")
        return None, None
    finally:
        try:
            driver.quit()
        except Exception:
            pass


def close_script_windows():
    """Close Script cmd windows by title (WM_CLOSE), then use PID kill fallback."""
    user32 = ctypes.windll.user32
    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    WM_CLOSE = 0x0010

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value
        for t in SCRIPT_WIN_TITLES:
            if t in title:
                print(f"[i] Closing window: {title}")
                user32.PostMessageW(hwnd, WM_CLOSE, 0, 0)
        return True

    cb = WNDENUMPROC(_cb)
    user32.EnumWindows(cb, 0)
    time.sleep(1.5)

    for pid in _CURRENT_SCRIPT_PIDS:
        try:
            subprocess.run(
                ["taskkill", "/F", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass
    _CURRENT_SCRIPT_PIDS.clear()


def refresh_tokens(username, password):
    """Refresh tokens with Chrome and Firefox login, then update token.txt."""
    print()
    print("-" * 58)
    print("  Token refresh")
    print("-" * 58)

    print("  1/2  Chrome login")
    chrome_bbs, chrome_pop = login_chrome(username, password)

    print("  2/2  Firefox login")
    firefox_bbs, firefox_pop = login_firefox(username, password)

    _store_browser_tokens(chrome_bbs, chrome_pop, firefox_bbs, firefox_pop)

    final_bbs = firefox_bbs or chrome_bbs
    final_pop = chrome_pop or firefox_pop

    if not final_bbs and not final_pop:
        print("[ERR] Token refresh failed. Script windows will not restart.")
        return False

    if final_bbs:
        print(f"[OK] Firefox BBS token : {final_bbs[:24]}...")
    if final_pop:
        print(f"[OK] Chrome Pop token  : {final_pop[:24]}...")

    write_tokens(final_bbs, final_pop)
    return True


def _store_browser_tokens(chrome_bbs, chrome_pop, firefox_bbs, firefox_pop):
    _LAST_BROWSER_TOKENS["chrome"]["bbs"] = chrome_bbs
    _LAST_BROWSER_TOKENS["chrome"]["pop"] = chrome_pop
    _LAST_BROWSER_TOKENS["firefox"]["bbs"] = firefox_bbs
    _LAST_BROWSER_TOKENS["firefox"]["pop"] = firefox_pop


def _read_token_lines(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f if ln.strip()]


def _attempt_logout_for_session(bbs_token, pop_token):
    cookie_parts = []
    if bbs_token and bbs_token != "N/A":
        cookie_parts.append(f"new_bbs_serviceToken={bbs_token}")
    if pop_token and pop_token != "N/A":
        cookie_parts.append(f"popRunToken={pop_token}")

    if not cookie_parts:
        return False, None

    cookie_header = "; ".join(cookie_parts) + ";"
    req = urllib.request.Request(
        LOGOUT_URL,
        headers={
            "Cookie": cookie_header,
            "Referer": LOGIN_URL,
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            code = getattr(resp, "status", None) or resp.getcode()
        return 200 <= code < 400, code
    except Exception:
        return False, None


def _collect_fallback_sessions_from_token_file(lines):
    # token.txt layout currently: line1/3 BBS, line2/4 POP.
    # Build two session attempts from rows 1-2 and 3-4 for compatibility fallback.
    sessions = []
    if len(lines) >= 2:
        sessions.append(("tokenfile#1", lines[0], lines[1]))
    if len(lines) >= 4:
        sessions.append(("tokenfile#2", lines[2], lines[3]))
    return sessions


def logout_previous_sessions():
    """Best-effort logout for previous BBS token sessions before refresh."""
    sessions = []
    chrome_bbs = _LAST_BROWSER_TOKENS["chrome"]["bbs"]
    chrome_pop = _LAST_BROWSER_TOKENS["chrome"]["pop"]
    firefox_bbs = _LAST_BROWSER_TOKENS["firefox"]["bbs"]
    firefox_pop = _LAST_BROWSER_TOKENS["firefox"]["pop"]

    # Always try browser-separated session logout first.
    sessions.append(("chrome", chrome_bbs, chrome_pop))
    sessions.append(("firefox", firefox_bbs, firefox_pop))

    # If no in-memory browser tokens exist (e.g. after restart), fallback to token.txt layout.
    has_any_in_memory = any([chrome_bbs, chrome_pop, firefox_bbs, firefox_pop])
    if not has_any_in_memory:
        lines = _read_token_lines(TOKEN_FILE)
        sessions = _collect_fallback_sessions_from_token_file(lines)

    sessions = [s for s in sessions if (s[1] and s[1] != "N/A") or (s[2] and s[2] != "N/A")]
    if not sessions:
        print("[i] Logout phase skipped: no prior browser session token found.")
        return

    print("[i] Logout phase: closing previous browser sessions...")
    ok_count = 0
    for idx, (label, bbs_tok, pop_tok) in enumerate(sessions, start=1):
        ok, code = _attempt_logout_for_session(bbs_tok, pop_tok)
        if ok:
            ok_count += 1
            print(f"[OK] Logout request #{idx} ({label}) accepted (HTTP {code}).")
        else:
            print(f"[!] Logout request #{idx} ({label}) could not be confirmed.")

    print(f"[i] Logout phase done: {ok_count}/{len(sessions)} request(s) accepted.")


def _randomized_refresh_interval(base_interval):
    min_interval = max(1, int(base_interval * 0.8))
    max_interval = max(min_interval, int(base_interval * 1.2))
    return random.randint(min_interval, max_interval)


def countdown_and_refresh(username, password):
    """20-minute countdown, then refresh tokens and restart 4 script windows."""
    base_interval = REFRESH_INTERVAL
    interval = _randomized_refresh_interval(base_interval)
    delta_pct = ((interval - base_interval) / base_interval) * 100 if base_interval else 0.0

    print()
    print(
        "[i] Refresh interval randomized "
        f"(+/-20%) to avoid a fixed periodic session pattern: {interval // 60:02d}:{interval % 60:02d} "
        f"({delta_pct:+.1f}% vs base {base_interval // 60:02d}:{base_interval % 60:02d})."
    )
    print("[i] This helps reduce predictable timing on repeated reconnect/logout cycles.")
    print(f"[i] Next token refresh in {interval // 60} minutes. Press Ctrl+C to stop.")

    try:
        for remaining in range(interval, 0, -1):
            mins, secs = divmod(remaining, 60)
            print(f"\r[timer] Next refresh: {mins:02d}:{secs:02d}   ", end="", flush=True)
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[!] Interrupted by user.")
        sys.exit(0)

    print("\n[i] Refresh window reached.")

    print("[i] Closing script windows...")
    close_script_windows()
    time.sleep(1)

    logout_previous_sessions()
    time.sleep(1)

    ok = refresh_tokens(username, password)

    if ok:
        print("[i] Restarting 4 NScript.py windows...")
        launch_scripts()
    else:
        print("[ERR] Token refresh failed, windows were not restarted.")


def write_tokens(firefox_bbs, chrome_pop):
    # Line 1 and 3 -> Firefox new_bbs_serviceToken
    # Line 2 and 4 -> Chrome popRunToken
    t_ff = firefox_bbs or chrome_pop or "N/A"
    t_chr = chrome_pop or firefox_bbs or "N/A"

    content = "\n".join([t_ff, t_chr, t_ff, t_chr])
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] {TOKEN_FILE} updated (4 lines).")


def _tile_windows_right_panel_2x2(window_titles):
    """Place 4 windows as 2x2 inside columns 2 and 3 (right panel)."""
    user32 = ctypes.windll.user32

    right_x, right_y, right_w, right_h = get_layout_rects()["right_panel"]
    half_w = right_w // 2
    half_h = right_h // 2

    positions = [
        (right_x, right_y, half_w, half_h),
        (right_x + half_w, right_y, right_w - half_w, half_h),
        (right_x, right_y + half_h, half_w, right_h - half_h),
        (right_x + half_w, right_y + half_h, right_w - half_w, right_h - half_h),
    ]

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    found = {}

    def _cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd):
            return True
        buf = ctypes.create_unicode_buffer(512)
        user32.GetWindowTextW(hwnd, buf, 512)
        title = buf.value
        for t in window_titles:
            if t not in found and t in title:
                found[t] = hwnd
        return True

    cb = WNDENUMPROC(_cb)

    print("[i] Waiting for script windows to appear...")
    for _ in range(60):
        found.clear()
        user32.EnumWindows(cb, 0)
        if all(t in found for t in window_titles):
            break
        time.sleep(0.2)
    else:
        missing = [t for t in window_titles if t not in found]
        print(f"[!] Missing windows: {missing}")

    SW_RESTORE = 9
    SWP_SHOWWINDOW = 0x0040

    for idx, title in enumerate(window_titles):
        hwnd = found.get(title)
        if not hwnd:
            print(f"[i] Window not found: {title}")
            continue

        x, y, w, h = positions[idx]
        user32.ShowWindow(hwnd, SW_RESTORE)
        time.sleep(0.05)
        user32.SetWindowPos(hwnd, 0, x, y, w, h, SWP_SHOWWINDOW)
        print(f"[OK] {title} arranged: {x},{y}  {w}x{h}")


def launch_scripts():
    layout_autojobs_console()

    py = sys.executable
    bat_files = []
    window_titles = []

    for i in range(1, 5):
        title = SCRIPT_WIN_TITLES[i - 1]
        bat_path = os.path.join(BASE_DIR, f"_autostart_window_{i}.bat")

        with open(bat_path, "w", encoding="utf-8") as bf:
            bf.write("@echo off\n")
            bf.write(f"title {title}\n")
            bf.write(f"echo {i}| \"{py}\" \"{SCRIPT_FILE}\"\n")

        bat_files.append(bat_path)
        window_titles.append(title)

        proc = subprocess.Popen(f'start "{title}" cmd /k "{bat_path}"', shell=True)
        _CURRENT_SCRIPT_PIDS.append(proc.pid)
        time.sleep(0.3)
        print(f"[OK] Window {i} started (title: {title}).")

    _tile_windows_right_panel_2x2(window_titles)

    time.sleep(2)
    for bp in bat_files:
        try:
            os.remove(bp)
        except Exception:
            pass


def main():
    if os.name == "nt":
        os.system(f"title {AUTOJOBS_WINDOW_TITLE}")

    layout_autojobs_console()

    print("=" * 58)
    print("  AutoJobs - Token refresher + 4-window launcher")
    print("=" * 58)
    print()

    username, password = read_credentials()
    print(f"[i] Account: {username}")
    print()

    print("-" * 58)
    print("  1/2  Chrome login")
    print("-" * 58)
    chrome_bbs, chrome_pop = login_chrome(username, password)

    print()
    print("-" * 58)
    print("  2/2  Firefox login")
    print("-" * 58)
    firefox_bbs, firefox_pop = login_firefox(username, password)

    _store_browser_tokens(chrome_bbs, chrome_pop, firefox_bbs, firefox_pop)

    final_bbs = firefox_bbs or chrome_bbs
    final_pop = chrome_pop or firefox_pop

    if not final_bbs and not final_pop:
        print("[ERR] No token could be extracted. Exiting.")
        input("Press Enter to exit...")
        sys.exit(1)

    print()
    if final_bbs:
        print(f"[OK] Firefox BBS token : {final_bbs[:24]}...")
    else:
        print("[-] Firefox BBS token : not found")

    if final_pop:
        print(f"[OK] Chrome Pop token  : {final_pop[:24]}...")
    else:
        print("[-] Chrome Pop token  : not found")

    print()
    write_tokens(final_bbs, final_pop)

    print()
    print("[i] Starting 4 NScript.py windows...")
    launch_scripts()

    while True:
        countdown_and_refresh(username, password)


if __name__ == "__main__":
    main()
