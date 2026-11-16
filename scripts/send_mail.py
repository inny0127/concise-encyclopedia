"""Email a file via Naver SMTP. Password comes from Windows Credential Manager (keyring).

Usage: python send_mail.py <to> <subject> <file> [<file> ...]
"""
import mimetypes
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

import keyring

USER = "inny0127"
SENDER = "inny0127@naver.com"
SERVICE = "naver-smtp"


def main(to, subject, *files):
    password = keyring.get_password(SERVICE, USER)
    if not password:
        sys.exit(f"No password stored: keyring service '{SERVICE}', user '{USER}'")
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = SENDER, to, subject
    msg.set_content("Attached.")
    for f in map(Path, files):
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        maintype, subtype = ctype.split("/")
        msg.add_attachment(f.read_bytes(), maintype=maintype, subtype=subtype, filename=f.name)
    with smtplib.SMTP_SSL("smtp.naver.com", 465, timeout=120) as s:
        s.login(USER, password)
        s.send_message(msg)
    print("sent to", to, [Path(f).name for f in files])


if __name__ == "__main__":
    main(*sys.argv[1:])
