import subprocess
import sys
import time
import os
import webbrowser

required_packages = ["browser-cookie3", "selenium", "pyperclip", "tkinter"]
for package in required_packages:
    try:
        __import__(package.replace("-", "_"))
    except ImportError:
        print(f"[!] Installing missing package: {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import browser_cookie3
import pyperclip
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tkinter as tk
from tkinter import ttk

token_file = "token.txt" # dont change this 
chrome_link = "https://c.mi.com/global" # dont change this 
firefox_cmd = r'"C:\\Program Files\\Mozilla Firefox\\firefox.exe" %s' # edit this if you installed firefox to another location

def show_taskbar_prompt(title, message, ok_text="OK"):
    root = tk.Tk()
    root.title(title)
    root.resizable(False, False)
    width, height = 420, 140
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    x = (screen_w - width) // 2
    y = (screen_h - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")
    root.attributes("-topmost", True)
    root.after(200, lambda: root.attributes("-topmost", False))
    frm = ttk.Frame(root, padding=12)
    frm.pack(expand=True, fill=tk.BOTH)
    lbl = ttk.Label(frm, text=message, wraplength=width - 30, justify=tk.LEFT)
    lbl.pack(pady=(6, 12), anchor=tk.W)
    result = {"ok": False}
    def on_ok():
        result["ok"] = True
        root.destroy()
    btn = ttk.Button(frm, text=ok_text, command=on_ok)
    btn.pack(side=tk.BOTTOM)
    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.mainloop()
    return result["ok"]

def extract_firefox_token():
    try:
        cj = browser_cookie3.firefox()
        print(f"[i] Using Firefox profile from {cj.filename if hasattr(cj, 'filename') else 'default'}")
    except Exception as e:
        print(f"[!] Failed to load Firefox cookies: {e}")
        return None
    for cookie in cj:
        if "new_bbs_serviceToken" in cookie.name:
            return cookie.value
    return None

def extract_chrome_token(link):
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(link)
    show_taskbar_prompt(
        "Login required - Chrome",
        "Please log in on c.mi.com/global in the opened Chrome window.\nPress OK after logging in. The login fields may be laggy for a few seconds."
    )
    try:
        token = driver.execute_script("""
            var match = document.cookie.match(/popRunToken=([^;]+)/);
            return match ? match[1] : null;
        """)
    except Exception as e:
        print(f"[!] Error executing script in Chrome: {e}")
        token = None
    driver.quit()
    if token:
        print(f"[✔] Chrome Token found!")
    else:
        print("[✖] Chrome Token not found!")
    return token

def update_token_file(firefox_token, chrome_token):
    lines = [
        firefox_token or "N/A",
        chrome_token or "N/A",
        firefox_token or "N/A",
        chrome_token or "N/A"
    ]
    with open(token_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print("[✔] token.txt updated with all tokens!")

def prompt_login_firefox():
    try:
        webbrowser.get(firefox_cmd).open("https://c.mi.com/global")
    except Exception:
        webbrowser.open("https://c.mi.com/global")
    show_taskbar_prompt(
        "Login required - Firefox",
        "Please log in on c.mi.com/global in the opened Firefox window.\nAfter you've finished logging in, press OK to continue."
    )
    kill_firefox()

def kill_firefox(): #this is not a good solution but it adds a fallback whenever firefox cant be killed, too lazy to implement something better tbh - if having problems, modify it. Should work like this.
     subprocess.run(["taskkill", "/IM", "firefox.exe"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
     time.sleep(1)
     tasks = subprocess.run(["tasklist"], capture_output=True, text=True)
     if "firefox.exe" in tasks.stdout:
        subprocess.run(["taskkill", "/F", "/IM", "firefox.exe"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(3)    


if __name__ == "__main__":
    print("GetTokens V2 - by byBestix on xdaforums")
    print("Input the script name here. Has changed in the past so im making it manual")
    script_path = input()
    prompt_login_firefox()
    firefox_token = extract_firefox_token()
    if not firefox_token:
        print("[✖] Firefox token not found!")
    else:
        print("[✔] Firefox token extracted.")
    chrome_token = extract_chrome_token(chrome_link)
    if not chrome_token:
        print("[✖] Chrome token not found!")
    else:
        print("[✔] Chrome token extracted.")
    update_token_file(firefox_token, chrome_token)
    for i in range(1, 5):
        subprocess.Popen(
            f'start cmd /k "echo {i} | py {script_path}"',
            shell=True
        )
        time.sleep(0.1)
    time.sleep(0.5)
    quit
