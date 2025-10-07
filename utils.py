import os
import json
import requests
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_GITHUB = os.getenv("DISCORD_WEBHOOK_GITHUB")
DISCORD_WEBHOOK_MERCHANT = os.getenv("DISCORD_WEBHOOK_MERCHANT")

def get_ph_time(utc_time_str):
    utc_time = datetime.strptime(utc_time_str, "%Y-%m-%dT%H:%M:%SZ")
    ph_time = utc_time + timedelta(hours=8)
    return ph_time.strftime("%Y-%m-%d %H:%M:%S")

def get_relative_time(dt: datetime):
    timestamp = int(dt.replace(tzinfo=timezone.utc).timestamp())
    return f"<t:{timestamp}:R>"

def load_json(file):
    if os.path.exists(file):
        try:
            with open(file, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None
    return None

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

def send_discord_embed(webhook_url, title, description, color=0x00FFAA, fields=None):
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
    return resp.status_code in (200, 204)

def send_discord_embed(webhook_url, title, description, color=0x00FFAA, fields=None, mention=None):
    embed = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    if fields:
        embed["fields"] = fields
    payload = {"embeds": [embed]}
    if mention:
        payload["content"] = mention
    resp = requests.post(webhook_url, json=payload)
    print(f"📨 Discord embed sent ({resp.status_code})")
    return resp.status_code in (200, 204)