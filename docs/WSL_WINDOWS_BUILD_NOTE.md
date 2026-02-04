# PyInstaller Build Output: WSL vs Windows (Conda)

## Summary
If you run PyInstaller inside WSL (Linux), it will produce a **Linux binary**, even if your project files live under `/mnt/d/...`. A Linux binary will **not** run on Windows, and simply renaming the file to `.exe` does not work.

## Symptoms
- Build log ends with a Linux path like `/mnt/d/.../dist`.
- Output folder contains a file named `SCM10_Monitor` (no `.exe`).
- Renaming to `.exe` still fails to run on Windows.

## Root Cause
PyInstaller builds **native binaries for the OS it runs on**. WSL is Linux, so it cannot generate Windows executables.

## Correct Build Approach (Windows)
Run the build in a native Windows environment (PowerShell or CMD) using a Windows Python/Conda installation.

Example (Windows):

```bat
cd "D:\Long Ju Group\Projects\Measurement Programs\SCM10_T_monitor"
conda activate scm10_monitor
pyinstaller --noconfirm --clean --windowed --name SCM10_Monitor --collect-all pyqtgraph scm10_monitor\main.py
```

Expected output:

```
dist\SCM10_Monitor\SCM10_Monitor.exe
```

Copy the entire `dist\SCM10_Monitor` folder to another Windows PC to run the app.

## Notes
- Building on WSL **cannot** generate a Windows `.exe`.
- Building on Windows **does not** require WSL at all.
- Keep the build command consistent across environments; just run it on Windows.
