"""
Sends a single test email via Mailjet to confirm SENDER_EMAIL,
RECEIVER_EMAIL, MAILJET_API_KEY and MAILJET_SECRET_KEY in .env are all
correct, before relying on scraper.py to send real notifications.
"""

import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

SENDER_EMAIL = os.environ['SENDER_EMAIL']
RECEIVER_EMAIL = os.environ['RECEIVER_EMAIL']
MAILJET_API_KEY = os.environ['MAILJET_API_KEY']
MAILJET_SECRET_KEY = os.environ['MAILJET_SECRET_KEY']

subject = 'Test Email from Mailjet'
body = 'Hello, this is a test email sent using Mailjet SMTP relay.'

msg = MIMEText(body)
msg['Subject'] = subject
msg['From'] = SENDER_EMAIL
msg['To'] = RECEIVER_EMAIL

smtp_server = 'in-v3.mailjet.com'
smtp_port = 587  # Use 465 if you prefer SSL

try:
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(MAILJET_API_KEY, MAILJET_SECRET_KEY)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
    print("Email sent successfully via Mailjet.")
except Exception as e:
    print(f"Failed to send email: {e}")
