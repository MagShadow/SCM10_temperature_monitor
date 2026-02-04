import json
import os
import socket
import unittest
from pathlib import Path

from scm10_monitor.emailer import EmailConfig, EmailSender


def _load_config() -> dict:
    path = os.getenv("SCM10_EMAIL_TEST_CONFIG", "tests/email_test_config.json")
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(
            f"Email test config not found: {config_path}. "
            "Create it from tests/email_test_config.example.json."
        )
    return json.loads(config_path.read_text(encoding="utf-8"))


def _parse_recipients(value) -> list[str]:
    if isinstance(value, list):
        return [item.strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        parts = [p.strip() for p in value.replace("\n", ";").split(";")]
        return [p for p in parts if p]
    return []


class EmailSendTest(unittest.TestCase):
    def test_send_email(self) -> None:
        try:
            data = _load_config()
        except FileNotFoundError as exc:
            self.skipTest(str(exc))
            return

        required = ["smtp_host", "smtp_port", "username", "password", "to_addrs"]
        missing = [key for key in required if not data.get(key)]
        if missing:
            self.skipTest(f"Missing required fields: {', '.join(missing)}")

        recipients = _parse_recipients(data.get("to_addrs"))
        if not recipients:
            self.skipTest("No recipients provided")

        # DNS resolution check for clearer failures.
        try:
            socket.getaddrinfo(data["smtp_host"], data["smtp_port"], 0, socket.SOCK_STREAM)
        except socket.gaierror as exc:
            raise RuntimeError(f"SMTP host not resolvable: {data['smtp_host']}") from exc

        config = EmailConfig(
            smtp_host=data["smtp_host"],
            smtp_port=int(data["smtp_port"]),
            use_tls=bool(data.get("use_tls", True)),
            username=data["username"],
            password=data["password"],
            from_addr=data.get("from_addr", data["username"]),
            to_addrs=recipients,
            subject=data.get("subject", "SCM10 Email Test"),
        )

        sender = EmailSender(config)
        sender.send("SCM10 email test from unit test.")


if __name__ == "__main__":
    unittest.main()
