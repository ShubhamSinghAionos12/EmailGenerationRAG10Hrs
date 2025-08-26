import os
import email
import smtplib
import ssl
from imapclient import IMAPClient
from email.mime.text import MIMEText


# Fetch UNSEEN messages from INBOX; returns (uid, message)
def fetch_unread(label: str = None):
    host = os.getenv("IMAP_HOST")
    user = os.getenv("IMAP_USERNAME")
    pwd = os.getenv("IMAP_PASSWORD")

    with IMAPClient(host, ssl=True) as c:
        c.login(user, pwd)
        c.select_folder("INBOX")
        msgs = c.search(['UNSEEN'])
        for uid in msgs:
            raw = c.fetch([uid], ['RFC822'])[uid][b'RFC822']
            msg = email.message_from_bytes(raw)
            yield uid, msg


# Send via SMTP (TLS)
def smtp_send(to_addr: str, subject: str, body: str, from_addr=None):
    from_addr = from_addr or os.getenv("SMTP_USERNAME")
    msg = MIMEText(body, "plain", "utf-8")
    msg["From"], msg["To"], msg["Subject"] = from_addr, to_addr, subject

    with smtplib.SMTP(os.getenv("SMTP_HOST"), int(os.getenv("SMTP_PORT", "587"))) as s:
        s.starttls(context=ssl.create_default_context())
        s.login(os.getenv("SMTP_USERNAME"), os.getenv("SMTP_PASSWORD"))
        s.send_message(msg)
