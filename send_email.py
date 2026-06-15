import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def read_results(filename="results.txt"):
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def send_email(body):
    sender   = os.environ["EMAIL_SENDER"]
    password = os.environ["EMAIL_PASSWORD"]
    receiver = os.environ["EMAIL_RECEIVER"]

    msg = MIMEMultipart()
    msg["From"]    = sender
    msg["To"]      = receiver
    msg["Subject"] = "Weekly Flight Prices Update"

    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())
        print("Email sent!")

send_email(read_results())
