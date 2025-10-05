import os
import time
import json
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

# ============ CONFIGURATION ============
load_dotenv()

# GitHub info
GITHUB_REPO = "AhmadV99/Script-Games"
GITHUB_FILE_PATH = "Grow a Garden.lua"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits?path={GITHUB_FILE_PATH}"

# Webhooks (stored safely in .env)
DISCORD_WEBHOOK_GITHUB = os.getenv("DISCORD_WEBHOOK_GITHUB")
DISCORD_WEBHOOK_MERCHANT = os.getenv("DISCORD_WEBHOOK_MERCHANT")

# GAG API
API_URL_GAG = "https://gagstock.gleeze.com/grow-a-garden"

# Interval
CHECK_INTERVAL = 10 * 60  # 10 minutes

# Storage files
LAST_COMMIT_FILE = "last_commit.json"
LAST_MERCHANT_FILE = "last_merchant_status.json"


# ============ UTILITY FUNCTIONS ============
def get_ph_time(utc_time_str):
    """Convert UTC string to PH time."""
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    ph_time = utc_time + timedelta(hours=8)
    return ph_time.strftime("%Y-%m-%d %H:%M:%S")

def get_relative_time(dt: datetime):
    """Return Discord-formatted relative time."""
    timestamp = int(dt.replace(tzinfo=timezone.utc).timestamp())
    return f"<t:{timestamp}:R>"

def load_json(file):
    """Safely load JSON from file."""
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    return None

def save_json(file, data):
    """Write JSON to file."""
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def send_discord_embed(webhook_url, title, description, color=0x00FFAA, fields=None):
    """Send an embedded message to Discord."""
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if fields:
        embed["fields"] = fields
    payload = {"embeds": [embed]}
    resp = requests.post(webhook_url, json=payload)
    print(f"📨 Discord embed sent ({resp.status_code})")
    return resp.status_code == 204 or resp.status_code == 200


# ============ GITHUB MONITOR ============
def check_github_updates():
    """Fetch latest commit info from GitHub."""
    try:
        resp = requests.get(GITHUB_API_URL, timeout=10)
        if resp.status_code != 200:
            print(f"❌ GitHub request failed: {resp.status_code}")
            return None
        commits = resp.json()
        if not commits:
            return None
        latest = commits[0]
        return {
            "sha": latest["sha"],
            "author": latest["commit"]["author"]["name"],
            "date": latest["commit"]["author"]["date"],
            "message": latest["commit"]["message"]
        }
    except Exception as e:
        print("⚠️ GitHub error:", e)
        return None

def run_github_monitor():
    """Compare and send updates if new commit found."""
    last_commit = load_json(LAST_COMMIT_FILE)
    latest = check_github_updates()
    if not latest:
        print("⚠️ No GitHub commits found.")
        return

    if not last_commit or last_commit["sha"] != latest["sha"]:
        utc_time = latest["date"]
        ph_time = get_ph_time(utc_time)
        utc_dt = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
        relative = get_relative_time(utc_dt)

        description = (
            f"🧠 **Message:** {latest['message']}\n"
            f"👤 **Author:** {latest['author']}\n\n"
            f"🕒 **Last Commit Time:**\n"
            f"• UTC: `{utc_time}`\n"
            f"• PH: `{ph_time}`\n"
            f"⏱️ {relative}"
        )

        print("🚨 New GitHub commit detected!")
        if send_discord_embed(
            DISCORD_WEBHOOK_GITHUB,
            "🚨 New Commit Detected on Grow a Garden.lua",
            description,
            color=0x00BFFF
        ):
            print("✅ GitHub commit embed sent successfully.")
        save_json(LAST_COMMIT_FILE, latest)
    else:
        print("✅ No new GitHub commits since last check.")


# ============ MERCHANT MONITOR ============
def check_merchant():
    """Fetch traveling merchant info from GAG API."""
    try:
        resp = requests.get(API_URL_GAG, timeout=10)
        if resp.status_code != 200:
            print(f"❌ GAG API failed: {resp.status_code}")
            return None
        return resp.json()
    except Exception as e:
        print("⚠️ Merchant check error:", e)
        return None

def run_merchant_monitor():
    """Check traveling merchant status and notify Discord."""
    last_status = load_json(LAST_MERCHANT_FILE)
    data = check_merchant()

    if not data:
        print("⚠️ No merchant data received.")
        return

    # Ensure the JSON contains the expected structure
    merchant_data = data.get("data", {}).get("travelingmerchant")
    if not merchant_data:
        print("⚠️ Invalid JSON structure — 'travelingmerchant' not found.")
        return

    # Extract relevant info
    status = str(merchant_data.get("status", "")).lower()
    merchant_name = merchant_data.get("merchantName", "Unknown")
    items = merchant_data.get("items", [])
    appear_in = merchant_data.get("appearIn", "N/A")

    print(f"📦 Merchant check → Name: {merchant_name}, Status: {status}, Items: {len(items)}")

    # Detect if status changed since last run
    last_status_val = (last_status or {}).get("status", "")
    if last_status_val == status:
        print("✅ Merchant status unchanged since last check.")
        return

    # If merchant is active — send Discord embed
    if status == "active":
        print("🧳 Merchant is active.")
        fields = []
        for item in items:
            name = item.get("name", "")
            qty = item.get("quantity", "")
            emoji = item.get("emoji", "")
            fields.append({
                "name": f"{emoji} {name}",
                "value": f"Quantity: `{qty}`",
                "inline": True
            })

        sent = send_discord_embed(
            DISCORD_WEBHOOK_MERCHANT,
            "🧳 Traveling Merchant is Now Active!",
            f"**Merchant:** {merchant_name}\n⏱️ Appears in: `{appear_in}`",
            color=0xF1C40F,
            fields=fields
        )
        if sent:
            print("✅ Merchant embed sent successfully.")
    else:
        print(f"❌ Merchant inactive or left (Status: {status}).")

    # Save latest merchant status
    save_json(LAST_MERCHANT_FILE, {"status": status, "merchantName": merchant_name})



# ============ TIMING HANDLER ============
def get_seconds_until_next_10min():
    """Align checks to the next :00, :10, :20, etc."""
    now = datetime.now()
    minutes = now.minute
    next_minute = ((minutes // 10) + 1) * 10
    if next_minute == 60:
        next_minute = 0
        next_hour = now.hour + 1
    else:
        next_hour = now.hour
    next_time = now.replace(hour=next_hour % 24, minute=next_minute, second=0, microsecond=0)
    delta = (next_time - now).total_seconds()
    if delta <= 0:
        delta += 600  # fallback if missed
    return delta, next_time


# ============ MAIN LOOP ============
if __name__ == "__main__":
    print("🚀 Starting GitHub + Merchant Monitor")
    print(f"🕓 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    while True:
        print(f"⏰ Running checks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        run_github_monitor()
        run_merchant_monitor()

        wait_sec, next_run = get_seconds_until_next_10min()
        print(f"💤 Waiting {int(wait_sec)}s until next check at {next_run.strftime('%H:%M:%S')}...\n")
        time.sleep(wait_sec)
