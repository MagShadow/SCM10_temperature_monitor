import smtplib
from dataclasses import dataclass
from email.message import EmailMessage


@dataclass
class EmailConfig:
    smtp_host: str
    smtp_port: int
    use_tls: bool
    username: str
    password: str
    from_addr: str
    to_addrs: list[str]
    subject: str


class EmailSender:
    def __init__(self, config: EmailConfig):
        self.config = config

    def send(self, body: str) -> None:
        if not self.config.smtp_host:
            raise ValueError("SMTP host is required")
        if not self.config.to_addrs:
            raise ValueError("Recipient address is required")
        msg = EmailMessage()
        msg["Subject"] = self.config.subject or "SCM10 Alarm"
        msg["From"] = self.config.from_addr or self.config.username
        msg["To"] = ", ".join(self.config.to_addrs)
        msg.set_content(body)

        with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=15) as server:
            if self.config.use_tls:
                server.starttls()
            if self.config.username:
                server.login(self.config.username, self.config.password)
            server.send_message(msg)
