import json
import websocket
import requests
import time
from datetime import datetime, timezone
from utils import (
    send_discord_embed,
    load_json,
    save_json,
    DISCORD_WEBHOOK_MERCHANT,
)

# Direct constants
API_URL_GAG = "https://gagstock.gleeze.com/grow-a-garden"
LAST_MERCHANT_FILE = "last_merchant.json"


def fetch_json(url):
    """Fetch JSON data safely from API URL."""
    print(f"🌐 Checking API: {url}")
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        print(f"✅ Got valid JSON from {url}")
        return data
    except Exception as e:
        print(f"⚠️ Error checking {url}: {e}")
        return None


def get_data_from_wss():
    """Retrieve travelingMerchant data from WebSocket."""
    try:
        print("🌐 Connecting to GrowAGardenPro WebSocket...")
        ws = websocket.create_connection("wss://ws.growagardenpro.com/", timeout=15)
        
        # Give it a moment to establish connection
        time.sleep(0.5)
        
        print("⏳ Waiting for data from WebSocket...")
        message = ws.recv()
        ws.close()
        
        print(f"📨 Received message (length: {len(message)} chars)")
        data = json.loads(message)
        
        # Debug: Show the structure
        print(f"🔍 Top-level keys in WebSocket response: {list(data.keys())}")
        
        # Check if it's wrapped in 'data' object first
        if "data" in data and "travelingMerchant" in data["data"]:
            print("✅ Found travelingMerchant in data.travelingMerchant")
            return data["data"]["travelingMerchant"]
        elif "travelingMerchant" in data:
            print("✅ Found travelingMerchant at root level")
            return data["travelingMerchant"]
        else:
            print("⚠️ No travelingMerchant key found in WebSocket data.")
            # Show nested structure if data exists
            if "data" in data:
                print(f"   Keys in 'data': {list(data['data'].keys())}")
            return None
    except Exception as e:
        print(f"⚠️ WebSocket error: {e}")
        import traceback
        traceback.print_exc()
        return None


def parse_discord_timestamp(tag):
    """Extract Unix timestamp from Discord-like tag format <t:1759755600:f>"""
    if isinstance(tag, str) and tag.startswith("<t:") and ":" in tag:
        try:
            timestamp = int(tag.split(":")[1])
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (ValueError, IndexError):
            return None
    return None


def check_wss_merchant_active(pro_data):
    """Check if WebSocket merchant is currently active based on arrivedAt/leavesAt."""
    if not pro_data:
        return False
    
    arrived_at = pro_data.get("arrivedAt")
    leaves_at = pro_data.get("leavesAt")
    
    if not arrived_at or not leaves_at:
        return False
    
    try:
        now = datetime.now(timezone.utc)
        arrived_dt = parse_discord_timestamp(arrived_at)
        leaves_dt = parse_discord_timestamp(leaves_at)
        
        if arrived_dt and leaves_dt:
            is_active = arrived_dt <= now <= leaves_dt
            print(f"🕒 WSS Time Check - Arrived: {arrived_dt}, Leaves: {leaves_dt}, Now: {now}")
            print(f"🟢 WSS Status: {'ACTIVE' if is_active else 'INACTIVE'}")
            return is_active
    except Exception as e:
        print(f"⚠️ Error parsing WebSocket timestamps: {e}")
    
    return False


def run_merchant_monitor():
    """Cross-check merchant status between API and WebSocket, then send Discord alert if active."""
    last_status = load_json(LAST_MERCHANT_FILE)

    # --- Fetch GAG API data ---
    gag_data = fetch_json(API_URL_GAG)
    gag_status = "inactive"
    gag_items = []
    gag_merchant_name = "Traveling Merchant"
    appear_in = "N/A"
    countdown = "N/A"

    if gag_data and "data" in gag_data and "travelingmerchant" in gag_data["data"]:
        tm = gag_data["data"]["travelingmerchant"]
        api_status = tm.get("status", "unknown")
        gag_status = "active" if api_status == "active" else "inactive"
        gag_items = tm.get("items", [])
        appear_in = tm.get("appearIn")
        countdown = tm.get("countdown", "N/A")
        print(f"✅ GAG API merchant status: {api_status} → {gag_status}")
        print(f"   Items found: {len(gag_items)}")
        print(f"   Countdown: {countdown}")
        print(f"   Appear In: {appear_in}")
    else:
        print("⚠️ Invalid or empty GAG API response.")

    # --- Fetch WebSocket data ---
    pro_data = get_data_from_wss()
    pro_status = "inactive"
    pro_merchant_name = "Unknown"
    pro_items = []

    if pro_data:
        pro_merchant_name = pro_data.get("merchantName", "Traveling Merchant")
        pro_items = pro_data.get("items", [])
        
        # Check if merchant is active based on timestamps
        if check_wss_merchant_active(pro_data):
            pro_status = "active"
        
        print(f"🧩 PRO merchant name: '{pro_merchant_name}'")
        print(f"🟩 PRO merchant status: {pro_status}")
    else:
        print("⚠️ No data received from WebSocket.")

    # --- Cross-check both sources ---
    items = gag_items or pro_items
    merchant_name = pro_merchant_name if pro_merchant_name != "Unknown" else gag_merchant_name
    
    print(f"\n📦 CROSS-CHECK SUMMARY:")
    print(f"   Merchant Name: {merchant_name}")
    print(f"   GAG API Status: {gag_status}")
    print(f"   WSS PRO Status: {pro_status}")
    print(f"   Items Count: {len(items)}")

    # Active only if BOTH sources confirm active
    if gag_status == "active" and pro_status == "active":
        status = "active"
        print("✅ BOTH SOURCES CONFIRM: Merchant is ACTIVE")
    else:
        status = "inactive"
        print(f"❌ MISMATCH or INACTIVE: Cannot confirm merchant status")

    # Check if status changed
    last_status_val = (last_status or {}).get("status", "")
    last_items = (last_status or {}).get("items", [])
    status_changed = status != last_status_val or items != last_items

    # --- Send embed if merchant just became active ---
    if status == "active" and items and status_changed:
        print("\n🧳 Sending Discord notification...")

        fields = [
            {
                "name": f"{item.get('emoji', '❓')} {item.get('name', 'Unknown Item')}",
                "value": f"Quantity: `{item.get('quantity', 0)}`",
                "inline": False
            }
            for item in items
        ]

        # Use countdown if appearIn is None
        time_info = countdown if appear_in is None else appear_in
        
        sent = send_discord_embed(
            DISCORD_WEBHOOK_MERCHANT,
            "🧳 Traveling Merchant is Now Active! ✅",
            f"**Merchant:** {merchant_name}\n⏱️ Time remaining: `{time_info}`\n\n*Cross-verified by both API and WebSocket*",
            color=0xF1C40F,
            fields=fields
        )
        if sent:
            print("✅ Merchant embed sent successfully to Discord.")
    elif status == "active" and not status_changed:
        print("ℹ️ Merchant is active but no change detected (already notified).")
    else:
        print(f"❌ No notification sent - Status: {status}, Changed: {status_changed}")

    # --- Save last known state ---
    save_json(LAST_MERCHANT_FILE, {
        "status": status,
        "merchantName": merchant_name,
        "items": items
    })
    print(f"\n💾 State saved to {LAST_MERCHANT_FILE}")


# Run directly for testing
if __name__ == "__main__":
    run_merchant_monitor()