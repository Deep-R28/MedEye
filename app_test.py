from flask import Flask, request, jsonify
from pywebpush import webpush, WebPushException
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import resend
import json

# --- Flask setup ---
app = Flask(__name__)

# --- Load VAPID keys ---
def load_vapid_keys():
    with open("private_key.pem", "r") as f:
        private_key = f.read().strip()
    with open("public_key.pem", "r") as f:
        public_key = f.read().strip()
    return public_key, private_key

VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY = load_vapid_keys()

# --- Email credentials (use App Password for Gmail) ---
SENDER_EMAIL = "your_email@gmail.com"
SENDER_PASSWORD = "your_app_password"   # Use Gmail App Password (not real password)

# --- Initialize Resend API (optional for transactional emails) ---
resend.api_key = "re_xxxxxxxxx"

# --- Store active subscriptions (for simplicity, in-memory) ---
subscriptions = []

# --- Medicine schedule (example times) ---
# Set 24-hour format times as strings
MEDICINE_SCHEDULE = {
    "Morning": "09:00",
    "Afternoon": "13:00",
    "Evening": "18:00",
    "Night": "22:00"
}

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

# --- Combined Notification ---
def send_reminder(subscription, email, time_label):
    message = f"💊 It's time to take your {time_label} medicine!"
    send_web_push(subscription, message)
    send_email(email, f"Medication Reminder — {time_label}", message)

# --- Flask API Endpoint to Subscribe User ---
@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()
    subscription_info = data.get("subscription")
    recipient_email = data.get("email")

    if not subscription_info or not recipient_email:
        return jsonify({"error": "Missing subscription or email"}), 400

    subscriptions.append({
        "subscription": subscription_info,
        "email": recipient_email
    })

    print(f"✅ New subscription added for {recipient_email}")
    return jsonify({"success": True, "message": "Subscription added successfully!"})

# --- Scheduler Job: Triggered at medicine times ---
def scheduled_medicine_reminders(time_label):
    print(f"🕒 Triggering reminders for {time_label} at {datetime.now().strftime('%H:%M:%S')}")
    for sub in subscriptions:
        send_reminder(sub["subscription"], sub["email"], time_label)

# --- Setup Background Scheduler ---
scheduler = BackgroundScheduler()

# Schedule jobs for each time slot
for label, time_str in MEDICINE_SCHEDULE.items():
    hour, minute = map(int, time_str.split(":"))
    scheduler.add_job(
        scheduled_medicine_reminders,
        "cron",
        hour=hour,
        minute=minute,
        args=[label],
        id=f"job_{label}"
    )

scheduler.start()

# --- Main ---
if __name__ == "__main__":
    print(f"🚀 Flask server running with VAPID Public Key: {VAPID_PUBLIC_KEY[:30]}...")
    print("📅 Scheduler active for medicine times:", json.dumps(MEDICINE_SCHEDULE, indent=2))
    try:
        app.run(debug=True, use_reloader=False)
    finally:
        scheduler.shutdown()