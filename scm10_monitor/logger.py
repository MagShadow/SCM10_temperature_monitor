from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class DataLogger:
    folder: Path
    file_path: Optional[Path] = None
    _handle: Optional[object] = None

    def start(self) -> Path:
        self.folder.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.file_path = self.folder / f"scm10_log_{timestamp}.csv"
        self._handle = self.file_path.open("w", encoding="utf-8")
        self._handle.write("timestamp_iso,elapsed_s,temperature_k\n")
        self._handle.flush()
        return self.file_path

    def log(self, timestamp_iso: str, elapsed_s: float, temperature_k: float) -> None:
        if not self._handle:
            return
        self._handle.write(f"{timestamp_iso},{elapsed_s:.3f},{temperature_k:.6f}\n")
        self._handle.flush()

    def close(self) -> None:
        if self._handle:
            try:
                self._handle.close()
            finally:
                self._handle = None
