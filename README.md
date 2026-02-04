# SCM10 Temperature Monitor (Python)

This project provides a Windows GUI application for the Scientific Instruments SCM10 Temperature Monitor.
It uses Python internally and can be compiled into a standalone Windows `.exe`.

## Features (mapped to your requirements)

1. **Python-based, standalone Windows `.exe`**
   - Uses Python + PySide6 + pyqtgraph + pyserial.
   - Build instructions below for a self-contained executable.

2. **Connection area (Ethernet / RS232 USB) + test**
   - Select connection type (Ethernet or RS232/USB).
   - Enter IP/port or COM/baud.
   - Test connection using `*IDN?` (configurable).

3. **Real-time reading + plot + logging**
   - Toggle reading **ON/OFF**.
   - Set reading period (default 1 second).
   - Plot temperature vs. time from the moment reading starts.
   - Choose log folder and automatically create a new log file for every start.

4. **Alarm with thresholds + beep/email**
   - Enable/disable alarm.
   - Configure high/low thresholds.
   - Beep and/or email on alarm.
   - Email includes a minimum reminder period (default 60 minutes).

## Folder structure

```
SCM10_T_monitor/
  environment.yml
  scm10_monitor/
    __init__.py
    alarm.py
    comms.py
    emailer.py
    logger.py
    main.py
    main_window.py
    protocol.py
    settings.py
  requirements.txt
  README.md
```

## Quick start (run from source, Conda)

1. Create and activate a conda environment:

```bash
conda env create -f environment.yml
conda activate scm10_monitor
```

2. Run the app:

```bash
python -m scm10_monitor.main
```

## Connection and protocol settings

The SCM10 command summary in the manual shows query commands like:

- `*IDN?` (identification)
- `T?` (temperature)

Default command strings are set in the UI and stored in your settings file:

```
%APPDATA%\SCM10_T_monitor\settings.json
```

If your instrument expects a different terminator or command format, you can adjust these fields in the UI:

- **Terminator** (default `\r\n`)
- **IDN Query** (default `*IDN?`)
- **Temp Query** (default `T?`)

> If communication fails, try changing the terminator to `\n` or `\r`.

## Logging

Each time reading starts, a new CSV log file is created:

```
scm10_log_YYYYMMDD_HHMMSS.csv
```

Columns:

```
timestamp_iso,elapsed_s,temperature_k
```

## Alarm behavior

- If the temperature crosses the configured thresholds, the alarm triggers.
- **Beep** is issued when entering alarm state.
- **Email** is sent on alarm and then at the configured minimum reminder interval.

## Build a standalone Windows `.exe` (Conda)

If you created the environment with `environment.yml`, `pyinstaller` is already included.
Otherwise, install it in the same conda environment:

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

You can copy the entire `dist/SCM10_Monitor` folder to any Windows PC to run the program.

## Notes

- **Ethernet port**: The SCM10 manual lists a "TCP Data Socket" value. If you are unsure of the port,
  check the instrument configuration or manual and set the correct port in the UI.
- **Serial port**: Make sure the correct COM port and baud rate are selected.
- **Email**: Most providers require app passwords or SMTP-specific credentials.

## Customization

All settings are persisted to:

```
%APPDATA%\SCM10_T_monitor\settings.json
```

You can edit this file directly if you want to change defaults or provide new command strings.
