import time
from datetime import datetime
from github_monitor import run_github_monitor
from merchant_monitor import run_merchant_monitor

def get_seconds_until_next_10min():
    now = datetime.now()
    next_minute = (now.minute // 10 + 1) * 10
    next_hour, next_day, next_month, next_year = now.hour, now.day, now.month, now.year

    if next_minute == 60:
        next_minute = 0
        next_hour += 1
        if next_hour == 24:
            next_hour = 0
            from calendar import monthrange
            if now.day == monthrange(now.year, now.month)[1]:
                next_day, next_month = 1, now.month + 1 if now.month < 12 else 1
                if next_month == 1:
                    next_year += 1
            else:
                next_day += 1

    next_time = datetime(next_year, next_month, next_day, next_hour, next_minute, 0)
    return (next_time - now).total_seconds(), next_time

if __name__ == "__main__":
    print("🚀 Starting GitHub + Merchant Monitor")
    print(f"🕓 Current Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    while True:
        print(f"⏰ Running checks at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        run_github_monitor()
        run_merchant_monitor()
        wait_sec, next_run = get_seconds_until_next_10min()
        print(f"💤 Waiting {int(wait_sec) + 10}s until next check at {next_run.strftime('%H:%M:%S')}...\n")
        time.sleep(wait_sec + 10)
