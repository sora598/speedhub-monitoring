import requests
import time
from datetime import datetime, timezone, timedelta
import os

# === Configuration ===
GITHUB_API_URL = "https://api.github.com/repos/AhmadV99/Script-Games/commits?path=Grow%20a%20Garden.lua"
DISCORD_WEBHOOK = os.getenv("WEBHOOK")
CHECK_INTERVAL = 10 * 60  # 10 minutes (use 60 for testing)
STORAGE_FILE = "last_commit.txt"

# === Time helpers ===
def utc_to_ph(utc_time):
    """Convert UTC datetime to Philippine Time (UTC+8)."""
    return utc_time.astimezone(timezone(timedelta(hours=8)))

def format_datetime(dt):
    """Format datetime as YYYY-MM-DD HH:MM AM/PM"""
    return dt.strftime("%Y-%m-%d %I:%M %p")

# === File helpers ===
def load_last_commit():
    """Read last saved commit SHA from file."""
    if not os.path.exists(STORAGE_FILE):
        return None
    with open(STORAGE_FILE, "r") as f:
        return f.read().strip() or None
def get_relative_time(dt):
    """Get relative time string for Discord."""
    timestamp = int(dt.timestamp())
    return f"<t:{timestamp}:R>"

def save_last_commit(sha):
    """Save the latest commit SHA to file."""
    with open(STORAGE_FILE, "w") as f:
        f.write(sha)

# === Helper: Fetch latest commit info ===
def get_latest_commit():
    try:
        response = requests.get(GITHUB_API_URL)
        data = response.json()
        if not data or "message" in data:
            print("❌ Error fetching commit data.")
            return None, None
        latest_commit = data[0]
        sha = latest_commit["sha"]
        commit_time_str = latest_commit["commit"]["committer"]["date"]
        commit_time_utc = datetime.strptime(commit_time_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return sha, commit_time_utc
    except Exception as e:
        print("❌ Error:", e)
        return None, None

# === Helper: Send message to Discord ===
def send_discord_message(message):
    payload = {"content": message}
    resp = requests.post(DISCORD_WEBHOOK, json=payload)
    print(f"[Discord] Status: {resp.status_code}")

# === Main Program ===
print("🔍 Starting GitHub file monitor...")
print("📁 Target file: Grow a Garden.lua")

# Load previously saved commit
stored_commit = load_last_commit()
if stored_commit:
    print(f"📄 Stored last commit: {stored_commit}")
else:
    print("📄 No stored commit found (first run).")

# Get the latest commit from GitHub
latest_commit, latest_commit_utc = get_latest_commit()
if not latest_commit:
    print("❌ Could not retrieve initial commit.")
    exit()

latest_commit_ph = utc_to_ph(latest_commit_utc)
current_utc = datetime.now(timezone.utc)
current_ph = utc_to_ph(current_utc)

# === Display info ===
print(f"✅ Latest commit SHA: {latest_commit}\n")
print("🕒 Last commit time:")
print(f"📅 PH:  {format_datetime(latest_commit_ph)}")
print(f"🌐 UTC: {format_datetime(latest_commit_utc)}\n")

print("⌚ Current time:")
print(f"📅 PH:  {format_datetime(current_ph)}")
print(f"🌐 UTC: {format_datetime(current_utc)}")

# === Compare with stored commit ===
if stored_commit != latest_commit:
    print("🔔 Detected new commit since last check!")
    send_discord_message(
        f"@everyone 🚨 **New commit detected since last session!**\n"
        f"SHA: `{latest_commit}`\n\n"
        f"🕒 **Last commit time:**\n"
        f"📅 PH:  {format_datetime(latest_commit_ph)}\n"
        f"🌐 UTC: {format_datetime(latest_commit_utc)}\n\n"
        f"⌚ **Current time:**\n"
        f"📅 PH:  {format_datetime(current_ph)}\n"
        f"🌐 UTC: {format_datetime(current_utc)}\n\n"
        f"🔗 https://github.com/AhmadV99/Script-Games/commits/main/Grow%20a%20Garden.lua"
        f"\n⌚ **Time checked: {get_relative_time(current_ph)} **"
    )
    save_last_commit(latest_commit)
else:
    print("ℹ️ No new updates since last session.")
    send_discord_message(
        f"✅ Latest commit SHA: `{latest_commit}`\n\n"
        f"🕒 **Last commit time:**\n"
        f"📅 PH:  {format_datetime(latest_commit_ph)}\n"
        f"🌐 UTC: {format_datetime(latest_commit_utc)}\n\n"
        f"⌚ **Current time:**\n"
        f"📅 PH:  {format_datetime(current_ph)}\n"
        f"🌐 UTC: {format_datetime(current_utc)}\n\n"
        f"_No update so far._"
        f"\n⌚ **Time checked: {get_relative_time(current_ph)} **"
    )


# === Fix the time interval ===
time_executed  = datetime.now().minute
if time_executed % 10 != 0:
    time.sleep((10 - (time_executed % 10)) * 60)

# === Continuous monitor loop ===
while True:
    time.sleep(CHECK_INTERVAL)
    new_commit, new_commit_utc = get_latest_commit()

    if not new_commit:
        print("⚠️ Could not fetch new commit data. Retrying later...")
        continue

    if new_commit != latest_commit:
        print("🔔 New commit detected during monitoring!")

        new_commit_ph = utc_to_ph(new_commit_utc)
        current_utc = datetime.now(timezone.utc)
        current_ph = utc_to_ph(current_utc)

        message = (
            f"@everyone 🚨 **New commit detected!**\n"
            f"SHA: `{new_commit}`\n\n"
            f"🕒 **Last commit time:**\n"
            f"📅 PH:  {format_datetime(new_commit_ph)}\n"
            f"🌐 UTC: {format_datetime(new_commit_utc)}\n\n"
            f"⌚ **Current time:**\n"
            f"📅 PH:  {format_datetime(current_ph)}\n"
            f"🌐 UTC: {format_datetime(current_utc)}\n\n"
            f"🔗 https://github.com/AhmadV99/Script-Games/commits/main/Grow%20a%20Garden.lua"
            f"\n⌚ **Time checked: {get_relative_time(current_ph)} **"
        )
        send_discord_message(message)

        # Update stored values
        save_last_commit(new_commit)
        latest_commit, latest_commit_utc = new_commit, new_commit_utc
    else:
        print("⏳ No new updates.")
        send_discord_message(
        f"ℹ️**No update so far**\n"
        f"**Last commit was at**:\n"
        f"PH: {format_datetime(utc_to_ph(latest_commit_utc))}\n"
        f"UTC: {format_datetime(latest_commit_utc)}\n\n"
        f"\n⌚ **Time checked: {get_relative_time(current_ph)} **"
        )
