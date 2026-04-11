from __future__ import annotations

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from config.settings import (
    EMAIL_SMTP_HOST,
    EMAIL_SMTP_PORT,
    EMAIL_SENDER,
    EMAIL_APP_PASSWORD,
    EMAIL_RECIPIENT,
)

class EmailService:
    def send_summary(self, subject: str, html_body: str, text_body: str) -> None:
        if not EMAIL_SENDER or not EMAIL_APP_PASSWORD or not EMAIL_RECIPIENT:
            raise RuntimeError("Email configuration is incomplete.")

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = EMAIL_SENDER
        message["To"] = EMAIL_RECIPIENT

        message.attach(MIMEText(text_body, "plain", "utf-8"))
        message.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP(EMAIL_SMTP_HOST, EMAIL_SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_APP_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, message.as_string())