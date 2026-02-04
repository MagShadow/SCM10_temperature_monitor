from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Optional

try:
    import winsound
except Exception:  # pragma: no cover - non-Windows systems
    winsound = None

from .emailer import EmailConfig, EmailSender


@dataclass
class AlarmSettings:
    enabled: bool
    low_enabled: bool
    low_threshold: float
    high_enabled: bool
    high_threshold: float
    beep_enabled: bool
    email_enabled: bool
    email_min_interval_min: int


class AlarmManager:
    def __init__(self) -> None:
        self._last_email_ts: Optional[float] = None
        self._in_alarm = False

    def reset(self) -> None:
        self._last_email_ts = None
        self._in_alarm = False

    def evaluate(
        self,
        temperature: float,
        settings: AlarmSettings,
        email_config: Optional[EmailConfig] = None,
    ) -> None:
        if not settings.enabled:
            self._in_alarm = False
            return

        is_low = settings.low_enabled and temperature < settings.low_threshold
        is_high = settings.high_enabled and temperature > settings.high_threshold
        in_alarm = is_low or is_high

        if in_alarm and settings.beep_enabled:
            self._beep()

        if in_alarm and settings.email_enabled and email_config:
            now = time.time()
            min_interval = max(1, settings.email_min_interval_min) * 60
            if self._last_email_ts is None or (now - self._last_email_ts) >= min_interval:
                self._last_email_ts = now
                self._send_email_async(email_config, temperature, is_low, is_high)

        self._in_alarm = in_alarm

    def _beep(self) -> None:
        if winsound:
            try:
                winsound.Beep(1000, 400)
            except Exception:
                pass

    def _send_email_async(
        self,
        email_config: EmailConfig,
        temperature: float,
        is_low: bool,
        is_high: bool,
    ) -> None:
        def _send():
            sender = EmailSender(email_config)
            status = "LOW" if is_low else "HIGH"
            body = f"SCM10 alarm triggered: {status}\nTemperature: {temperature:.6f} K"
            sender.send(body)

        threading.Thread(target=_send, daemon=True).start()
