"""
Sends students their sign-in codes, through a Gmail account's SMTP server.

Set SMTP_USER (the Gmail address) and SMTP_PASSWORD (an app password for it, made at
https://myaccount.google.com/apppasswords — never the account's real password).

Without those, a laptop just prints the code in the server's terminal so everything
can be tried offline; on Vercel sending is refused instead, because nobody reads a
serverless function's terminal.
"""

import os
import smtplib
import ssl
from email.message import EmailMessage


class MailError(Exception):
    """The code could not be sent; the message is safe to show a student."""


def configured() -> bool:
    return bool(os.environ.get("SMTP_USER", "").strip() and os.environ.get("SMTP_PASSWORD", "").strip())


def send_code(to: str, code: str) -> None:
    if not configured():
        if os.environ.get("VERCEL"):
            raise MailError("Email isn't set up on the server yet, so no code can be sent. "
                            "Tell whoever runs Stridian.")
        print(f"[mail] SMTP not set up - the code for {to} is {code}", flush=True)
        return

    user = os.environ["SMTP_USER"].strip()
    msg = EmailMessage()
    msg["From"] = f"Stridian <{user}>"
    msg["To"] = to
    msg["Subject"] = f"{code} is your Stridian code"
    msg.set_content(
        f"Your Stridian code is {code}\n\n"
        "Type it on the Stridian page to finish signing in. It works for 15 minutes.\n\n"
        "Stridian never asks for your university email password - the password you choose "
        "on Stridian is separate.\n\n"
        "If you didn't ask for this, ignore this email; nothing changes without the code.\n"
    )
    try:
        # port 465 with TLS from the first byte; Vercel blocks only port 25
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20,
                              context=ssl.create_default_context()) as smtp:
            # Google shows app passwords in groups of four ("abcd efgh ..."); the spaces
            # are not part of it
            smtp.login(user, os.environ["SMTP_PASSWORD"].replace(" ", "").strip())
            # the recipient is given explicitly, never re-read from the parsed header
            smtp.send_message(msg, to_addrs=[to])
    except (smtplib.SMTPException, OSError) as exc:
        raise MailError("Couldn't send the email just now - try again in a minute.") from exc
