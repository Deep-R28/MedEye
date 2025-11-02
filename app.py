from flask import Flask, request, jsonify
from pywebpush import webpush, WebPushException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Flask setup ---
app = Flask(__name__)

# --- Load VAPID keys from files ---
def load_vapid_keys():
    with open("private_key.pem", "r") as f:
        private_key = f.read().strip()
    with open("public_key.pem", "r") as f:
        public_key = f.read().strip()
    return public_key, private_key

VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY = load_vapid_keys()

# --- Email credentials ---
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"   # ⚠️ Use Gmail App Password, not your real password

# --- Web Push Notification Function ---
def send_web_push(subscription_info, message_body):
    try:
        webpush(
            subscription_info=subscription_info,
            data=message_body,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": f"mailto:{SENDER_EMAIL}"}
        )
        print("✅ Push notification sent!")
    except WebPushException as ex:
        print("❌ Push notification failed:", repr(ex))

# --- Email Notification Function ---
def send_email(recipient_email, subject, message):
    msg = MIMEMultipart()
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg["Subject"] = subject
    msg.attach(MIMEText(message, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            print(f"📧 Email sent to {recipient_email}")
    except Exception as e:
        print("❌ Email failed:", e)

# --- API Endpoint to Trigger Notifications ---
@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    subscription_info = data.get("subscription")
    recipient_email = data.get("email")

    message = "💊 You have to take your meds!"

    # Send both push and email notifications
    send_web_push(subscription_info, message)
    if recipient_email:
        send_email(recipient_email, "Medication Reminder", message)

    return jsonify({"success": True, "message": "Push and email sent successfully!"})

if __name__ == "__main__":
    print(f"🚀 Flask server running with VAPID Public Key: {VAPID_PUBLIC_KEY[:30]}...")
    app.run(debug=True)