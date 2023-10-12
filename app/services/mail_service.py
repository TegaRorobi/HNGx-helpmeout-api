""" This module contains the functions for sending emails to users. """
import smtplib
from email.message import EmailMessage
from app.settings import (
    EMAIL_ADDRESS,
    EMAIL_PASSWORD,
    EMAIL_HOST,
    EMAIL_PORT
)

def send_video(video_id: str, recepient_address: str):
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
    msg["Subject"] = "Beautiful Subject"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = recepient_address
    msg.set_content(get_mail(video_id), subtype="html",)

    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)


def get_mail(video_id):
    """
    Returns the HTML for the email to be sent to the user.

    Parameters:
        video_id (str): The id of the video to be sent to the user.

    Returns:
        str: The HTML for the email to be sent to the user.
    """
    if not video_id:
        return None
    return """
    <!DOCTYPE html>
    <html>
        <head>
            <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0" />
            <style type="text/css">
                body {
                    font-family: "Lato", sans-serif;
                    font-size: 18px;
                    background-color: #f5f8fa;
                    margin: 0;
                    padding: 0;
                }
                #email {
                    margin: auto;
                    width: 600px;
                    background-color: #fff;
                    border-radius: 10px;
                }
                #header {
                    background-color: #00a4bd;
                    color: white;
                    text-align: center;
                    padding: 20px;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }
                #content {
                    padding: 30px;
                }
                h1 {
                    font-size: 36px;
                }
                h2 {
                    font-size: 24px;
                    font-weight: bold;
                }
                p {
                    font-weight: 100;
                }
                .button {
                    display: inline-block;
                    padding: 10px 20px;
                    background-color: #00a4bd;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }
                video {
                    width: 100%;
                    height: auto;
                }
            </style>
        </head>
        <body>
            <div id="email">
                <div id="header">
                    <h1>HelpMeOut Screen Recorder</h1>
                </div>
                <div id="content">
                    <h2>Your Screen Recording</h2>
                    <p>
                        Thank you for using our screen recording app. Your recorded
                        video is ready for download. You can also preview it below:
                    </p>
                    <video
                        width="320"
                        height="176"
                        controls="controls"
                        poster="https://www.emailonacid.com/images/blog_images/Emailology/2013/html5_video/bunny_cover.jpg"
                        src="https://www.w3schools.com/htmfrom email.message import EmailMessage
    l/mov_bbb.mp4"
                    >
                        <!-- fallback 1 -->
                        <a href="https://www.emailonacid.com"
                            ><img
                                height="176"
                                src="https://www.emailonacid.com/images/blog_images/Emailology/2013/html5_video/bunny-fallback.jpg"
                                width="320"
                        /></a>
                    </video>
                    <br />
                    <a
                        class="button"
                        href="https://www.cofucan.tech/srce/api/video/5z7aWVvi8lE1SFh.mp4"
                        download
                        >Download Video</a
                    >
                </div>
            </div>
        </body>
    </html>
    """
