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

# Shared check interval (seconds)
CHECK_INTERVAL = 10 * 60  # every 10 minutes

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
    print(f"📨 Sent Discord embed ({resp.status_code})")

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
        print("No GitHub commits found.")
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

        send_discord_embed(
            DISCORD_WEBHOOK_GITHUB,
            "🚨 New Commit Detected on Grow a Garden.lua",
            description,
            color=0x00BFFF
        )

        save_json(LAST_COMMIT_FILE, latest)
    else:
        send_discord_embed(
            DISCORD_WEBHOOK_GITHUB,
            "✅ No Update Detected",
            "No new commits since last check.",
            color=0x2ECC71
        )

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
        print("No merchant data.")
        return

    tm = data.get("data", {}).get("travelingmerchant", {})
    status = tm.get("status")
    merchant_name = tm.get("merchantName", "Unknown")
    items = tm.get("items", [])
    appear_in = tm.get("appearIn", "N/A")

    if status == "active":
        if not last_status or last_status.get("status") != "active":
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

            send_discord_embed(
                DISCORD_WEBHOOK_MERCHANT,
                "🧳 Traveling Merchant is Now Active!",
                f"**Merchant:** {merchant_name}",
                color=0xF1C40F,
                fields=fields
            )
    else:
        if last_status and last_status.get("status") == "active":
            send_discord_embed(
                DISCORD_WEBHOOK_MERCHANT,
                "❌ Traveling Merchant Left",
                f"{merchant_name} is no longer active.\nWill appear again in `{appear_in}`.",
                color=0xFF5555
            )

    save_json(LAST_MERCHANT_FILE, {"status": status, "merchantName": merchant_name})

# ============ MAIN LOOP ============
if __name__ == "__main__":
    print("🚀 Starting GitHub + GAG Monitor\n")
    while True:
        print(f"⏰ Running checks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        run_github_monitor()
        run_merchant_monitor()
        print(f"💤 Sleeping for {CHECK_INTERVAL / 60:.0f} minutes...\n")
        time.sleep(CHECK_INTERVAL)
