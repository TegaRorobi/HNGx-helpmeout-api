""" This module contains the functions for sending emails to users. """
import smtplib
import ssl
from mjml import mjml_to_html
import pystache
from email.message import EmailMessage
from email.utils import formataddr
from app.settings import (
    EMAIL_NAME,
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    EMAIL_HOST,
    EMAIL_PORT
)


def send_video(username: str, video_id: str, recepient_address: str):
    """
    Sends an email to the user with the video embedded in the email.

    Parameters:
        video_id (str): The id of the video to be sent to the user.
        recepient_address (str): The email address of the user.

    Returns:
        message (str): A message indicating whether the email was sent
            successfully.
    """
    msg = EmailMessage()
    msg["Subject"] = "HelpMeOut Screen Recorder"
    msg["From"] = formataddr((EMAIL_NAME, EMAIL_ADDRESS))
    msg["To"] = recepient_address

    with open("app/services/video_mail.mjml", "rb") as f:
        mail = mjml_to_html(f)

    mail = mail.html
    context = {
        'username': username,
        'video_id': video_id,
    }
    mail = pystache.render(mail, context)

    msg.set_content(mail, subtype="html")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


def send_otp(recepient_address: str, otp: str):
    """
    Sends an email to the user with the video embedded in the email.

    Parameters:
        video_id (str): The id of the video to be sent to the user.
        recepient_address (str): The email address of the user.

    Returns:
        message (str): A message indicating whether the email was sent
            successfully.
    """
    msg = EmailMessage()
    msg["Subject"] = "Forgotten Helpmeout Password"
    msg["From"] = formataddr((EMAIL_NAME, EMAIL_ADDRESS))
    msg["To"] = "yiradesat@gmail.com"

    with open("app/services/forgot_password.mjml", "rb") as f:
        mail = mjml_to_html(f)

    mail = mail.html
    context = {
        'verification_code': otp,
    }
    mail = pystache.render(mail, context)

    msg.set_content(mail, subtype="html")

    with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)
