import json
import os
from copy import deepcopy
from pathlib import Path

DEFAULT_SETTINGS = {
    "connection": {
        "type": "ethernet",  # ethernet | serial
        "serial": {
            "port": "",
            "baud": 9600,
            "timeout_s": 3.0,
        },
        "ethernet": {
            "ip": "",
            "port": 2000,
            "timeout_s": 5.0,
        },
    },
    "protocol": {
        "terminator": "\\r\\n",
        "idn_query": "*IDN?",
        "temp_query": "T?",
    },
    "readout": {
        "period_s": 1.0,
        "log_folder": "",
        "max_points": 0,
    },
    "alarm": {
        "enabled": False,
        "low_enabled": False,
        "low_threshold": 0.0,
        "high_enabled": False,
        "high_threshold": 0.0,
        "beep_enabled": True,
        "email_enabled": False,
        "email_min_interval_min": 60,
    },
    "email": {
        "smtp_host": "",
        "smtp_port": 587,
        "use_tls": True,
        "username": "",
        "password": "",
        "from_addr": "",
        "to_addrs": [],
        "subject": "SCM10 Alarm",
        "remember_password": False,
        "keyring_service": "SCM10_T_monitor",
    },
    "history": {
        "log_folder": "",
    },
}


def _config_dir() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "SCM10_T_monitor"
    return Path.home() / ".scm10_t_monitor"


def config_path() -> Path:
    return _config_dir() / "settings.json"


def _deep_update(base: dict, updates: dict) -> dict:
    for key, value in updates.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
    return base


def load_settings() -> dict:
    settings = deepcopy(DEFAULT_SETTINGS)
    path = config_path()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            _deep_update(settings, data)
        except Exception:
            # If settings are corrupted, fall back to defaults.
            pass
    return settings


def save_settings(settings: dict) -> None:
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2), encoding="utf-8")


def decode_terminator(value: str) -> str:
    # Allow users to type \r, \n, \t in the UI/settings file.
    return value.encode("utf-8").decode("unicode_escape")


def encode_terminator(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n").replace("\t", "\\t")
