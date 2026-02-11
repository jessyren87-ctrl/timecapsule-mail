import smtplib
from email.message import EmailMessage

def send_email_smtp(
    *,
    host: str,
    port: int,
    username: str,
    password: str,
    mail_from: str,
    mail_to: str,
    subject: str,
    body: str,
) -> tuple[bool, str]:
    """
    返回 (success, provider_response_or_error)
    """
    msg = EmailMessage()
    msg["From"] = mail_from
    msg["To"] = mail_to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.ehlo()
            server.starttls()
            server.login(username, password)
            resp = server.send_message(msg)
        # send_message 成功时一般返回空 dict
        return True, f"ok send_message_return={resp}"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"
