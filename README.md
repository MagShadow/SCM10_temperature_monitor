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
