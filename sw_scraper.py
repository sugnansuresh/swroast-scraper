import csv
import os
import time
import ssl
import smtplib
from datetime import datetime, timedelta
from email.message import EmailMessage
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

# === CONFIG ===
URL = "https://swroasting.coffee"
SENDER_EMAIL = "sugnan.suresh@gmail.com"
APP_PASSWORD = "bvjjpkrhgjxzrmkb"
RECIPIENTS = ["sugnan.suresh@ametek.com"]

CHECK_INTERVAL_FALLBACK = 600 # fallback sleep time of 10 minutes

LAST_DATE_FILE = "last_date.txt"
LOG_FILE = "log.csv"

# Dynamic interval configuration (24hr format)
SCHEDULE = [
    {"start": 5, "end": 11, "interval_minutes": 10},
    {"start": 11, "end": 17, "interval_minutes": 120},
    {"start": 17, "end": 24, "interval_minutes": None},  # check only once at 23:00
    {"start": 0, "end": 5, "interval_minutes": None},    # no checks unless during rollover
]


# === LOGGING ===
def log(event_type, message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    row = [timestamp, event_type, message]
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Timestamp", "Type", "Message"])
            writer.writerow(row)
    else:
        with open(LOG_FILE, "r", newline="") as f:
            existing = list(csv.reader(f))
        with open(LOG_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(existing[0])  # write headers again
            writer.writerow(row)  # add new row at the top
            writer.writerows(existing[1:])  # write rest of log
    print(f"[{timestamp}] {message}")


# === ROAST DATE FETCHING ===
def get_roast_date():
    try:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--log-level=3")
        driver = webdriver.Chrome(options=options)
        driver.get(URL)
        time.sleep(3)

        elements = driver.find_elements(By.TAG_NAME, "h6")
        for el in elements:
            text = el.text.strip()
            if "Current drop was roasted on" in text:
                # Extract only the date part and clean it
                match = text.split("on")[-1].strip().split()[0]
                driver.quit()
                return match.replace("\n", "").replace("\r", "")
        driver.quit()
        log("ERROR", "Roast date text not found in <h6> tags.")
        return None
    except Exception as e:
        log("ERROR", f"Selenium error: {e}")
        return None


# === FILE HANDLERS ===
def load_last_date():
    if os.path.exists(LAST_DATE_FILE):
        with open(LAST_DATE_FILE, "r") as f:
            return f.read().strip()
    return None

def save_last_date(date_str):
    with open(LAST_DATE_FILE, "w") as f:
        f.write(date_str)


# === EMAIL NOTIFICATION ===
def send_email(new_date):
    try:
        msg = EmailMessage()
        clean_date = new_date.strip().replace('\n', '').replace('\r', '')
        msg["Subject"] = f"New Roast Drop: {clean_date}"
        msg["From"] = SENDER_EMAIL
        msg["To"] = ", ".join(RECIPIENTS)
        msg.set_content(f"The roast date on swroasting.coffee has been updated to {new_date}.")

        context = ssl.create_default_context()
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=context) as server:
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.send_message(msg)

        log("EMAIL", f"Notification sent to: {', '.join(RECIPIENTS)}")
    except Exception as e:
        log("ERROR", f"Failed to send email: {e}")


# === DYNAMIC INTERVAL ===
def get_next_sleep_time_minutes():
    now = datetime.now()
    hour = now.hour
    minute = now.minute

    for slot in SCHEDULE:
        if slot["start"] <= hour < slot["end"]:
            interval = slot["interval_minutes"]
            if interval:
                # Round up to the next scheduled time boundary
                next_check_minute = ((minute // interval) + 1) * interval
                next_time = now.replace(second=0, microsecond=0)

                if next_check_minute >= 60:
                    next_time = next_time.replace(minute=0) + timedelta(hours=1)
                else:
                    next_time = next_time.replace(minute=next_check_minute)

                delta = (next_time - now).total_seconds()
                return max(int(delta), 60)  # minimum 60s to avoid spam-checking
            else:
                # This block only checks once per evening at 11pm
                now_time = now.time()
                scheduled_time = now.replace(hour=23, minute=0, second=0, microsecond=0)
                if now < scheduled_time:
                    return int((scheduled_time - now).total_seconds())
                else:
                    # If it's already past 11pm, sleep until 5am next day
                    next_check = now.replace(hour=5, minute=0, second=0, microsecond=0) + timedelta(days=1)
                    return int((next_check - now).total_seconds())
    # Default fallback
    return CHECK_INTERVAL_FALLBACK



# === MAIN LOOP ===
def main_loop():
    log("INFO", "Script started.")
    current_date = get_roast_date()
    if current_date:
        last_date = load_last_date()
        if current_date != last_date:
            log("UPDATE", f"Roast date updated: {last_date} -> {current_date}")
            save_last_date(current_date)
            send_email(current_date)
        else:
            log("INFO", f"No change. Current roast date: {current_date}")
    else:
        log("ERROR", "Failed to retrieve roast date.")

    # Sleep until next scheduled time
    sleep_seconds = get_next_sleep_time_minutes()
    log("INFO", f"Sleeping for {sleep_seconds // 60} minutes...\n")
    time.sleep(sleep_seconds)


# === RUN ===
if __name__ == "__main__":
    from datetime import timedelta
    while True:
        main_loop()