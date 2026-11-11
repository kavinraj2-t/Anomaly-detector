import os
import smtplib
from email.message import EmailMessage


def send_registration_otp(recipient_email, recipient_name, otp_code, generated_upi_id):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or "kajjnj05@gmail.com"
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_SENDER") or os.getenv("SMTP_FROM") or smtp_user or ""

    if not smtp_host:
        smtp_host = "smtp.gmail.com"
    if not smtp_password:
        smtp_password = "mhbmslztdeudmwbh"

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, smtp_from]):
        return {
            "sent": False,
            "message": "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_SENDER.",
        }

    message = EmailMessage()
    message["Subject"] = "Your UPI Fraud Shield registration OTP"
    message["From"] = smtp_from
    message["To"] = recipient_email
    message.set_content(
        f"""Hello {recipient_name},

Your registration OTP is: {otp_code}

This OTP is valid for 10 minutes.
Your generated UPI ID will be: {generated_upi_id}

If you did not request this, you can ignore this email.
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    except Exception as exc:
        return {"sent": False, "message": f"Failed to send OTP email: {exc}"}

    return {"sent": True, "message": "OTP email sent"}


def send_upi_pin_reset_otp(recipient_email, recipient_name, otp_code, user_id):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or "kajjnj05@gmail.com"
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_SENDER") or os.getenv("SMTP_FROM") or smtp_user or ""

    if not smtp_host:
        smtp_host = "smtp.gmail.com"
    if not smtp_password:
        smtp_password = "mhbmslztdeudmwbh"

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, smtp_from]):
        return {
            "sent": False,
            "message": "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_SENDER.",
        }

    message = EmailMessage()
    message["Subject"] = "Your UPI Fraud Shield PIN reset OTP"
    message["From"] = smtp_from
    message["To"] = recipient_email
    message.set_content(
        f"""Hello {recipient_name},

Your UPI PIN reset OTP is: {otp_code}

This OTP is valid for 10 minutes.
Account: {user_id}

If you did not request this, you can ignore this email.
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    except Exception as exc:
        return {"sent": False, "message": f"Failed to send OTP email: {exc}"}

    return {"sent": True, "message": "OTP email sent"}


def send_password_reset_otp(recipient_email, recipient_name, otp_code, user_id):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or "kajjnj05@gmail.com"
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_SENDER") or os.getenv("SMTP_FROM") or smtp_user or ""

    if not smtp_host:
        smtp_host = "smtp.gmail.com"
    if not smtp_password:
        smtp_password = "mhbmslztdeudmwbh"

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, smtp_from]):
        return {
            "sent": False,
            "message": "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_SENDER.",
        }

    message = EmailMessage()
    message["Subject"] = "Your UPI Fraud Shield password reset OTP"
    message["From"] = smtp_from
    message["To"] = recipient_email
    message.set_content(
        f"""Hello {recipient_name},

Your password reset OTP is: {otp_code}

This OTP is valid for 10 minutes.
Account: {user_id}

If you did not request this, you can ignore this email.
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    except Exception as exc:
        return {"sent": False, "message": f"Failed to send OTP email: {exc}"}

    return {"sent": True, "message": "OTP email sent"}


def send_transaction_otp(recipient_email, recipient_name, otp_code, amount, receiver_id):
    smtp_host = os.getenv("SMTP_HOST")
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_user = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER") or "kajjnj05@gmail.com"
    smtp_password = os.getenv("SMTP_PASSWORD")
    smtp_from = os.getenv("SMTP_SENDER") or os.getenv("SMTP_FROM") or smtp_user or ""

    if not smtp_host:
        smtp_host = "smtp.gmail.com"
    if not smtp_password:
        smtp_password = "mhbmslztdeudmwbh"

    if not all([smtp_host, smtp_port, smtp_user, smtp_password, smtp_from]):
        return {
            "sent": False,
            "message": "SMTP is not configured. Set SMTP_HOST, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, and SMTP_SENDER.",
        }

    message = EmailMessage()
    message["Subject"] = "Your UPI Fraud Shield transaction OTP"
    message["From"] = smtp_from
    message["To"] = recipient_email
    message.set_content(
        f"""Hello {recipient_name},

Your transaction OTP is: {otp_code}

This OTP is valid for 10 minutes.
Payment amount: Rs {amount:.2f}
Beneficiary: {receiver_id}

If you did not request this transaction, please ignore this email.
"""
    )

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(message)
    except Exception as exc:
        return {"sent": False, "message": f"Failed to send OTP email: {exc}"}

    return {"sent": True, "message": "OTP email sent"}
