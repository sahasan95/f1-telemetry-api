from fastapi import FastAPI, HTTPException
from typing import Union
import requests
import time

app = FastAPI(title="F1 Analytics & Telemetry API")

OPEN_F1_BASE = "https://api.openf1.org/v1"

# --- Simple In-Memory Cache Store ---

DRIVER_CACHE = {
    "data": None,
    "last_fetched": 0,
    "ttl_seconds": 300  # Cache lasts for 5 minutes
}

@app.get("/")
def home():
    return {"message": "Welcome to the F1 Analytics API Engine!"}

@app.get("/drivers")
def get_active_drivers(session_key: Union[int, str] = "latest"):
    """
    Fetches driver details for a given race session with internal caching mechanisms.
    """
    current_time = time.time()
    
    # 1. Check if we have valid cached data for 'latest' sessions
    if session_key == "latest" and DRIVER_CACHE["data"] is not None:
        time_elapsed = current_time - DRIVER_CACHE["last_fetched"]
        if time_elapsed < DRIVER_CACHE["ttl_seconds"]:
            print("🚀 Serving driver data directly from local memory cache!")
            return {
                "source": "cache",
                "cache_expires_in_seconds": int(DRIVER_CACHE["ttl_seconds"] - time_elapsed),
                **DRIVER_CACHE["data"]
            }

    # 2. Cache miss or explicit session query -> Hit the live network
    url = f"{OPEN_F1_BASE}/drivers?session_key={session_key}"
    print("🌐 Cache miss! Requesting live data from OpenF1 network...")
    
    try:
        response = requests.get(url)
        response.raise_for_status() 
        drivers_data = response.json()
        
        if not drivers_data:
            return {"message": f"No driver data found for session: {session_key}", "drivers": []}
            
        structured_drivers = []
        for driver in drivers_data:
            structured_drivers.append({
                "driver_number": driver.get("driver_number"),
                "full_name": driver.get("full_name"),
                "team_name": driver.get("team_name"),
                "team_color": f"#{driver.get('team_color')}" if driver.get('team_color') else "#FFFFFF",
                "country_code": driver.get("country_code"),
                "broadcast_name": driver.get("broadcast_name")
            })
            
        result_payload = {
            "session_key": session_key,
            "total_drivers": len(structured_drivers),
            "drivers": structured_drivers
        }
        
        # 3. Save to cache if it's the general 'latest' session
        if session_key == "latest":
            DRIVER_CACHE["data"] = result_payload
            DRIVER_CACHE["last_fetched"] = current_time
            
        return {
            "source": "network",
            **result_payload
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch data from OpenF1: {str(e)}")
    

@app.get("/telemetry")
def get_driver_telemetry(driver_number: int, session_key: Union[int, str] = "latest", limit: int = 10):
    """
    Fetches the absolute latest real-time car telemetry data frames for a specific driver.
    Limits output size to prevent API throttling and excessive network overhead.
    """
    # OpenF1 Endpoint: https://api.openf1.org/v1/car_data?driver_number=44&session_key=latest
    url = f"{OPEN_F1_BASE}/car_data?driver_number={driver_number}&session_key={session_key}"
    
    print(f"🏎️ Fetching latest {limit} telemetry frames for Driver #{driver_number}...")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        telemetry_raw = response.json()
        
        if not telemetry_raw:
            return {
                "driver_number": driver_number,
                "session_key": session_key,
                "message": "No live telemetry frames found for this driver in the current session."
            }
            
        # Since OpenF1 returns sequential historical items up to the current second, 
        # let's slice the array from the tail to grab the absolute latest packets.
        latest_frames = telemetry_raw[-limit:]
        latest_frames.reverse() # Order by newest first
        
        structured_telemetry = []
        for frame in latest_frames:
            structured_telemetry.append({
                "timestamp": frame.get("date"),
                "speed_kmh": frame.get("speed"),
                "rpm": frame.get("rpm"),
                "gear": frame.get("n_gear"),
                "throttle_percentage": frame.get("throttle"),
                "brake_active": frame.get("brake") == 100,  # 100 means fully pressed, 0 means off
                "drs_status": frame.get("drs")
            })
            
        return {
            "driver_number": driver_number,
            "session_key": session_key,
            "frames_returned": len(structured_telemetry),
            "telemetry": structured_telemetry
        }
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch telemetry from OpenF1: {str(e)}")