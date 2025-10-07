import requests
from datetime import datetime
from utils import load_json, save_json, send_discord_embed, get_ph_time, get_relative_time, DISCORD_WEBHOOK_GITHUB

GITHUB_REPO = "AhmadV99/Script-Games"
GITHUB_FILE_PATH = "Grow a Garden.lua"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/commits?path={GITHUB_FILE_PATH}"
LAST_COMMIT_FILE = "last_commit.json"

def check_github_updates():
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
    last_commit = load_json(LAST_COMMIT_FILE)
    latest = check_github_updates()
    now = datetime.now()

    if not latest:
        print("⚠️ No GitHub commits found.")
        return

    initial_run = last_commit is None
    last_notify = (last_commit or {}).get("last_no_update_notify")

    # Format time information for the latest commit
    utc_time = latest["date"]
    ph_time = get_ph_time(utc_time)
    utc_dt = datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
    relative = get_relative_time(utc_dt)

    if initial_run or last_commit.get("sha") != latest["sha"]:
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
            color=0x00BFFF,
            mention="@everyone"
        ):
            print("✅ GitHub commit embed sent successfully.")

        save_json(LAST_COMMIT_FILE, {**latest, "last_no_update_notify": now.isoformat()})
    else:
        if initial_run:
            print("✅ Initial run – skipping 'No update' embed.")
            return
        
        send_no_update = True
        if last_notify:
            last_notify_dt = datetime.fromisoformat(last_notify)
            if (now - last_notify_dt).total_seconds() < 3600:
                send_no_update = False
        
        if send_no_update:
            print("⏱️ No new GitHub commits in the last hour. Sending 'No update' embed.")
            
            # Include last commit time in "no update" embed
            description = (
                f"No new commits detected in the past hour.\n\n"
                f"🕒 **Last Commit Time:**\n"
                f"• UTC: `{utc_time}`\n"
                f"• PH: `{ph_time}`\n"
                f"⏱️ {relative}"
            )
            
            if send_discord_embed(
                DISCORD_WEBHOOK_GITHUB,
                "✅ GitHub Update Check",
                description,
                color=0x2ECC71
            ):
                print("✅ 'No update' embed sent successfully.")
            
            last_commit_data = last_commit or {"sha": latest["sha"]}
            last_commit_data["last_no_update_notify"] = now.isoformat()
            save_json(LAST_COMMIT_FILE, last_commit_data)
        else:
            print("✅ No new GitHub commits since last check.")

if __name__ == "__main__":
    run_github_monitor()