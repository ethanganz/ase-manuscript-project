"""Sending emails.

Production: Resend (https://resend.com). Tests: in-memory outbox.
"""
import html
import logging

import httpx

import config

logger = logging.getLogger("uvicorn.error")

RESEND_URL = "https://api.resend.com/emails"


class EmailError(Exception):
    """The email could not be sent."""


class EmailSender:
    def send(self, to: str, subject: str, html_body: str, text_body: str) -> None: ...


class ResendEmailSender(EmailSender):
    def send(self, to, subject, html_body, text_body):
        if not config.RESEND_API_KEY:
            raise EmailError("RESEND_API_KEY is not set")
        try:
            response = httpx.post(
                RESEND_URL,
                headers={"Authorization": f"Bearer {config.RESEND_API_KEY}"},
                json={"from": config.EMAIL_FROM, "to": [to], "subject": subject,
                      "html": html_body, "text": text_body},
                timeout=10,
            )
        except httpx.HTTPError as exc:
            raise EmailError(f"Could not reach Resend: {exc}") from exc
        if response.status_code >= 400:
            raise EmailError(f"Resend answered {response.status_code}: {response.text}")


class InMemoryEmailSender(EmailSender):
    def __init__(self) -> None:
        self.outbox: list[dict] = []

    def send(self, to, subject, html_body, text_body):
        self.outbox.append({"to": to, "subject": subject, "html": html_body, "text": text_body})


def verification_link(token: str) -> str:
    """Link that opens the app, which then sends the token to the backend."""
    return f"{config.APP_BASE_URL}/#verify-email/{token}"


def send_verification_email(sender: EmailSender, user: dict, token: str) -> bool:
    """Email the verification link. Returns False (and logs) if sending failed."""
    link = verification_link(token)
    name = user.get("first_name") or "there"
    hours = config.EMAIL_VERIFY_EXPIRE_HOURS
    text_body = (
        f"Hi {name},\n\n"
        f"Please confirm your email address to finish creating your account:\n{link}\n\n"
        f"The link works for {hours} hours. If you did not sign up, ignore this email.\n"
    )
    html_body = (
        f"<p>Hi {html.escape(name)},</p>"
        "<p>Please confirm your email address to finish creating your account.</p>"
        f'<p><a href="{html.escape(link)}">Verify my email</a></p>'
        f"<p>The link works for {hours} hours. If you did not sign up, ignore this email.</p>"
    )
    try:
        sender.send(user["email"], "Verify your email address", html_body, text_body)
    except EmailError:
        logger.exception("Sending the verification email to user %s failed", user["id"])
        return False
    return True
