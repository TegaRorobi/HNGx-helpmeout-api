import smtplib
import os
from email.message import EmailMessage

EMAIL_ADDRESS = 'helpmeout.hngx@gmail.com'
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
RECEIPIENT = 'billmal071@gmail.com'

msg = EmailMessage()
msg['Subject'] = 'Beautiful Subject'
msg['From'] = EMAIL_ADDRESS
msg['To'] = RECEIPIENT
msg.set_content('''
<!DOCTYPE html>
<html>
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style type="text/css">
        body {
            font-family: 'Lato', sans-serif;
            font-size: 18px;
            background-color: #F5F8FA;
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
            background-color: #00A4BD;
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
            background-color: #00A4BD;
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
            <p>Thank you for using our screen recording app. Your recorded video is ready for download. You can also preview it below:</p>
            <video width="320" height="176" controls="controls"  poster="https://www.emailonacid.com/images/blog_images/Emailology/2013/html5_video/bunny_cover.jpg" src="https://www.w3schools.com/html/mov_bbb.mp4" >
      <!-- fallback 1 -->
      <a href="https://www.emailonacid.com" ><img height="176" 
        src="https://www.emailonacid.com/images/blog_images/Emailology/2013/html5_video/bunny-fallback.jpg" width="320" /></a>
</video>
            <br>
            <a class="button" href="https://www.cofucan.tech/srce/api/video/5z7aWVvi8lE1SFh.mp4" download>Download Video</a>
        </div>
    </div>
</body>
</html>
''', subtype='html')

with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
    smtp.send_message(msg)
