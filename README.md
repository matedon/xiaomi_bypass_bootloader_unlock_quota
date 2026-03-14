# Xiaomi Bootloader Unlock Quota Helper

This project automates token collection and timed bootloader unlock requests for Xiaomi devices (Global flow), based on Xiaomi Community web/API behavior.

## What This Program Does

The toolchain is built around two main steps:

1. Collect valid login tokens from Xiaomi Community (`new_bbs_serviceToken` and `popRunToken`).
2. Send a precisely timed unlock request to Xiaomi's API around Beijing midnight (`UTC+8`) to improve timing against daily quota limits.

## Requirements

- Python 3.x
- Browser access to Xiaomi Community account
- Chrome WebDriver available for Selenium-based token extraction
- Internet access to NTP servers and Xiaomi API endpoints

The scripts can auto-install Python dependencies when missing.

## Basic Usage (Windows)

**Recommended — one-click launch:**

1. Double-click `AutoStart.bat`.
   - Detects `py` or `python` automatically and starts `AutoStart.py`.
2. `AutoStart.py` opens a new console for `AutoJobs.py`, places it in the left column, and closes itself.
3. Complete login prompts in Chrome and Firefox.
4. `AutoJobs.py` extracts tokens, updates `token.txt`, and starts/restarts 4 `Script.py` windows automatically.

**Alternative — run directly from a terminal:**

```bash
py AutoStart.py
```


## Main Workflow

1. Run `AutoStart.bat` or `python AutoStart.py`.
2. `AutoStart.py` opens a new console for `AutoJobs.py`, places it in the left column, then closes the launcher window.
3. `AutoJobs.py` logs in to `https://c.mi.com/global` in Chrome and Firefox and extracts tokens.
4. `AutoJobs.py` writes tokens to `token.txt` (4 lines, reused by parallel runs).
5. `AutoJobs.py` starts 4 `Script.py` windows and arranges them on the right side in a 2x2 grid.
6. `Script.py`:
   - checks account unlock status via Xiaomi API,
   - synchronizes time with NTP servers,
   - applies an offset from `timeshift.txt`,
   - waits for target request moment,
   - sends POST requests to unlock endpoint and prints API response status.

## Window Layout (Windows)

The screen is divided into 3 equal columns.

**Phase 1 — Token collection (browser login):**

```
┌─────────────────┬─────────────────────────────────┐
│                 │                                 │
│   AutoJobs.py   │     Chrome / Firefox browser    │
│   (log/status)  │        (c.mi.com/global)        │
│                 │                                 │
└─────────────────┴─────────────────────────────────┘
   col 1 (1/3)              cols 2+3 (2/3)
```

**Phase 2 — Timed unlock requests (Script windows):**

```
┌─────────────────┬────────────────┬────────────────┐
│                 │   Script.py    │   Script.py    │
│   AutoJobs.py   │   (token #1)   │   (token #2)   │
│   (log/status)  ├────────────────┼────────────────┤
│                 │   Script.py    │   Script.py    │
│                 │   (token #3)   │   (token #4)   │
└─────────────────┴────────────────┴────────────────┘
   col 1 (1/3)         col 2 (1/3)      col 3 (1/3)
```

## File Roles

- `Script.py`: core timing and unlock request logic.
- `NScript.py`: alternate variant of the core script (different NTP server list).
- `GetTokens.py`: Windows token extraction and multi-window launcher.
- `GetTokens for Gnome on Linux by Jenna-66.py`: Linux/GNOME variant of token extraction.
- `AutoStart.bat`: Windows one-click launcher — detects the Python executable (`py` / `python`) and calls `AutoStart.py`.
- `AutoStart.py`: bootstrap launcher that starts `AutoJobs.py` in a new dedicated console window and places it in column 1, then closes itself.
- `AutoJobs.py`: main workflow — reads credentials from `account.txt`, auto-logs into Xiaomi Community in Chrome and Firefox, extracts tokens, updates `token.txt`, and manages 4 `Script.py` windows.
- `token.txt`: token storage (one token per line).
- `timeshift.txt`: per-window timing offset values (milliseconds).
- `account.txt` / `account_default.txt`: account credential handling for `AutoJobs.py`.
- `Ping.bat`: manual latency checks for listed servers.

## Alternative Token Collection

- `GetTokens.py` (Windows) and `GetTokens for Gnome on Linux by Jenna-66.py` (Linux) are still available as manual token-collection alternatives.

## Notes

- `token.txt` and `timeshift.txt` line order matters: each script window reads the line matching its token row number.
- Expired `new_bbs_serviceToken` values will fail and must be refreshed.
- This project uses unofficial automation around public web/API behavior; use responsibly and at your own risk.

## Credits and Sources

- Original code/source attribution in project scripts:
  - `GetTokens V2 - by byBestix on xdaforums` (see `GetTokens.py` and Linux variant).
- Linux GNOME adaptation file naming credits: `GetTokens for Gnome on Linux by Jenna-66.py`.
- XDA source thread:
  - https://xdaforums.com/t/how-to-unlock-bootloader-on-xiaomi-hyperos-all-devices-except-cn.4654009/
