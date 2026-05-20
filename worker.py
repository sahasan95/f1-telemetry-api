import requests
import json
import time
import os

OPEN_F1_BASE = "https://api.openf1.org/v1"
STORE_FILE = "telemetry_store.json"

# Target Driver (e.g., Driver #44 Lewis Hamilton or #1 Max Verstappen)
TARGET_DRIVER = 44
SESSION_KEY = "latest"

def initialize_store():
    """Creates a clean database file if it doesn't exist."""
    if not os.path.exists(STORE_FILE):
        with open(STORE_FILE, "w") as f:
            json.dump({"driver_number": TARGET_DRIVER, "buffer": []}, f)

def append_telemetry_to_store(new_frames):
    """Appends new unique data frames and maintains a sliding rolling buffer."""
    initialize_store()
    
    with open(STORE_FILE, "r") as f:
        try:
            db = json.load(f)
        except json.JSONDecodeError:
            db = {"driver_number": TARGET_DRIVER, "buffer": []}

    existing_timestamps = {frame["timestamp"] for frame in db["buffer"]}
    added_count = 0

    for frame in new_frames:
        timestamp = frame.get("date")
        if timestamp not in existing_timestamps:
            db["buffer"].append({
                "timestamp": timestamp,
                "speed_kmh": frame.get("speed"),
                "rpm": frame.get("rpm"),
                "gear": frame.get("n_gear"),
                "throttle_percentage": frame.get("throttle"),
                "brake_active": frame.get("brake") == 100,
                "drs_status": frame.get("drs")
            })
            added_count += 1

    # Keep only the last 50 latest records so our file doesn't grow infinitely (Sliding Window)
    db["buffer"] = db["buffer"][-50:]

    with open(STORE_FILE, "w") as f:
        json.dump(db, f, indent=4)
        
    if added_count > 0:
        print(f"📦 [WORKER] Successfully ingested {added_count} fresh telemetry frames into local data store.")

def run_worker():
    print(f"⚡ F1 Background Ingestion Engine Started for Driver #{TARGET_DRIVER}...")
    
    while True:
        url = f"{OPEN_F1_BASE}/car_data?driver_number={TARGET_DRIVER}&session_key={SESSION_KEY}"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                raw_data = response.json()
                if raw_data:
                    # Grab the last 10 frames from the streaming sequence
                    latest_subset = raw_data[-10:]
                    append_telemetry_to_store(latest_subset)
            else:
                print(f"⚠️ [WORKER] Unexpected status code from OpenF1: {response.status_code}")
        except Exception as e:
            print(f"❌ [WORKER] Network connection error: {str(e)}")
        
        print("💤 [WORKER] Sleeping for 3s...")
        time.sleep(3)

if __name__ == "__main__":
    run_worker()