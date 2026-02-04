# SCM10 Temperature Monitor

A Windows GUI application for the Scientific Instruments SCM10 Temperature Monitor.
It provides connection control (Ethernet/RS232), real-time temperature display and logging, and alarm notifications.

## Features

- Ethernet or RS232 (USB) connection with connection test
- Real-time temperature readout and plot
- CSV logging (new file per run)
- Alarm thresholds with continuous beeping and email notifications
- Email settings dialog with optional encrypted password storage (OS keyring)
- Alarm evaluation uses the **average of the most recent 5 points**

## Project Structure

```
SCM10_T_monitor/
  environment.yml
  scm10_monitor/
  tests/
  requirements.txt
  README.md
```

## Setup (Conda)

```bash
conda env create -f environment.yml
conda activate scm10_monitor
```

Run the app:

```bash
python -m scm10_monitor.main
```

## Windows Shortcut (Hidden Console)

Create a launcher script and a shortcut that runs it without showing a console window.

1. Create a file named `run_scm10_monitor.cmd` in the project folder with:

```bat
@echo off
setlocal
call "<CONDA_BASE>\condabin\conda.bat" activate scm10_monitor
cd /d "C:\Path\To\SCM10_T_monitor"
python -m scm10_monitor.main
endlocal
```

2. Create a file named `run_scm10_monitor.vbs` in the same folder with:

```vbscript
Set WshShell = CreateObject("WScript.Shell")
WshShell.Run """C:\Path\To\SCM10_T_monitor\run_scm10_monitor.cmd""", 0, False
```

3. Create a Windows shortcut to `run_scm10_monitor.vbs`.

Notes:
- Replace `<CONDA_BASE>` with your conda base path (from `conda info --base`).
- Replace `C:\Path\To\SCM10_T_monitor` with your project folder.

## Usage Notes

- **Connection settings** (including terminator and commands) are saved to:
  `%APPDATA%\SCM10_T_monitor\settings.json`
- **Logging** creates a new CSV each time reading starts:
  `scm10_log_YYYYMMDD_HHMMSS.csv`
- **Alarm averaging** uses the latest 5 points to decide threshold crossings
- **Email settings** are configured via the “Email Settings...” dialog
  - If “Remember Password” is enabled and keyring is available, the password is stored encrypted

## Email Test (optional)

A simple integration-style test is provided to verify SMTP settings.

1. Copy and edit the test config:

```
cp tests/email_test_config.example.json tests/email_test_config.json
```

2. Fill in SMTP credentials and recipients.

3. Run the test:

```bash
python -m unittest tests.test_email_send -v
```

> `tests/email_test_config.json` is in `.gitignore` so secrets are not committed.

### Gmail App Passwords

Gmail blocks normal account passwords for SMTP when 2‑step verification is enabled. You must use an **App Password**.

Steps:
1. Enable **2‑Step Verification** on the Gmail account.
2. Go to **Google Account → Security → App passwords**.
3. Create a new app password (e.g., “SCM10 Monitor”).
4. Use that 16‑character app password in `tests/email_test_config.json` or the Email Settings dialog.

## Build a Standalone Windows `.exe`

If you created the environment with `environment.yml`, `pyinstaller` is included.
Otherwise install it with conda:

```bash
conda install -c conda-forge pyinstaller
```

Build:

```bash
pyinstaller --noconfirm --clean --windowed --name SCM10_Monitor --collect-all pyqtgraph scm10_monitor/main.py
```

Output:

```
dist/SCM10_Monitor/SCM10_Monitor.exe
```

Copy the entire `dist/SCM10_Monitor` folder to another Windows PC to run the app.

## Troubleshooting

- If SMTP login fails for Gmail, use an **App Password** (requires 2‑step verification).
- If connection fails, confirm the instrument’s TCP port or serial settings.
