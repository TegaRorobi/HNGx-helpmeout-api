""" This module contains the functions for sending emails to users. """
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr

import pystache
from mjml import mjml_to_html

from app.settings import (
    EMAIL_NAME,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    EMAIL_HOST,
    EMAIL_PORT,
)


def send_video(username: str, video_id: str, recipient_address: str):
    """
    Sends an email to the user with the video embedded in the email.

    Parameters:
        username (str): The username of the sender.
        video_id (str): The ID of the video to be sent to the user.
        recipient_address (str): The email address where video will be sent.

    Returns:
        message (str): A message indicating whether the email was sent
            successfully.
    """
    msg = EmailMessage()
    msg["Subject"] = "HelpMeOut Screen Recorder"
    msg["From"] = formataddr((EMAIL_NAME, EMAIL_ADDRESS))
    msg["To"] = recipient_address

    with open("app/services/video_mail.mjml", "rb") as f:
        mail = mjml_to_html(f)

    mail = mail.html
    context = {
        "username": username,
        "video_id": video_id,
    }
    mail = pystache.render(mail, context)

    msg.set_content(mail, subtype="html")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


def send_otp(recipient_address: str, otp: str, subject: str) -> None:
    """
    Sends an email to the user with the video embedded in the email.

    Parameters:
        recipient_address (str): The email address of the user.
        otp (str): The OTP to be sent to the user.

    Returns:
        message (str): A message indicating whether the email was sent
            successfully.
    """

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((EMAIL_NAME, EMAIL_ADDRESS))
    msg["To"] = recipient_address

    with open("app/services/forgot_password.mjml", "rb") as file:
        mail = mjml_to_html(file)

    mail = mail.html
    context = {
        "verification_code": otp,
    }
    mail = pystache.render(mail, context)

    msg.set_content(mail, subtype="html")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

    return None


def send_welcome_mail(recipient_address: str, username: str) -> None:
    """
    Sends a welcome email to a new user.

    Parameters:
        recipient_address (str): The email address of the recipient.
        username (str): The username of the sender.

    Returns:
        message (str): A message indicating whether the email was sent
        successfully.
    """

    msg = EmailMessage()
    msg["Subject"] = "Welcome, welcome, welcome!"
    msg["From"] = formataddr((EMAIL_NAME, EMAIL_ADDRESS))
    msg["To"] = recipient_address

    with open("app/services/welcome.mjml", "rb") as file:
        mail = mjml_to_html(file)

    mail = mail.html
    context = {
        "username": username,
        "link": "https://helpmeout-dev.vercel.app/"
    }
    mail = pystache.render(mail, context)

    msg.set_content(mail, subtype="html")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

    return None
