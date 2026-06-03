from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware # Add this import
from typing import Union
import requests
import time

app = FastAPI(title="F1 Analytics & Telemetry API")

# --- CONFIGURE CORS MIDDLEWARE ---
# This allows your local Vue dev server to communicate with the Python backend safely
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all local ports during development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
def get_driver_telemetry(limit: int = 10):
    """
    Reads directly from our real-time localized data store populated by our background pipeline.
    Zero upstream network delays. Instant sub-millisecond response delivery.
    """
    import os
    import json
    STORE_FILE = "telemetry_store.json"
    
    if not os.path.exists(STORE_FILE):
        return {
            "message": "Data store initializing. Please wait for the background ingestion worker to save data frames."
        }
        
    with open(STORE_FILE, "r") as f:
        db = json.load(f)
        
    # Grab the newest frames out of our sliding pipeline window
    telemetry_records = db.get("buffer", [])
    latest_slices = telemetry_records[-limit:]
    latest_slices.reverse() # Sort newest first
    
    return {
        "driver_number": db.get("driver_number"),
        "source": "local_ingestion_pipeline",
        "frames_returned": len(latest_slices),
        "telemetry": latest_slices
    }

@app.get("/tyre-matrix")
def get_grid_tyre_matrix():
    """
    Queries all active driver records and maps out their current 
    tyre compounds. Safely sorts pre-race staging states.
    """
    SESSION_KEY = "latest"
    BASE_URL = "https://api.openf1.org/v1"
    
    try:
        # 1. Grab drivers data
        driver_res = requests.get(f"{BASE_URL}/drivers?session_key={SESSION_KEY}")
        # 2. Grab stints data
        stint_res = requests.get(f"{BASE_URL}/stints?session_key={SESSION_KEY}")
        
        if driver_res.status_code != 200 or stint_res.status_code != 200:
            raise HTTPException(status_code=502, detail="Upstream F1 grid feeds unreachable")
            
        drivers = driver_res.json()
        stints = stint_res.json()
        
        # If no drivers are returned yet for this specific session key, fallback to last known grid
        if not drivers:
            driver_res = requests.get(f"{BASE_URL}/drivers")
            drivers = driver_res.json()[-20:] if driver_res.status_code == 200 else []
        
        # Build driver map with explicit string fallbacks to prevent sorting crashes
        driver_map = {}
        for d in drivers:
            dn = d.get("driver_number")
            if dn is not None:
                driver_map[dn] = {
                    "name": d.get("broadcast_name") or f"Driver {dn}",
                    "code": d.get("name_acronym") or str(dn),
                    "team": d.get("team_name") or "AAA_UNKNOWN", # Prefix ensures sorted grouping fallback
                    "color": f"#{d['team_colour']}" if d.get("team_colour") else "#444"
                }
        
        # Group stints by driver safely
        latest_stints = {}
        if isinstance(stints, list) and len(stints) > 0:
            for s in stints:
                dn = s.get("driver_number")
                if dn is None:
                    continue
                if dn not in latest_stints or s.get("lap_start", 0) > latest_stints[dn].get("lap_start", 0):
                    latest_stints[dn] = s
                    
        matrix = []
        
        # If stints are completely empty because the race is starting right now
        if not latest_stints:
            for dn, profile in driver_map.items():
                matrix.append({
                    "driver_number": dn,
                    "broadcast_name": profile["name"],
                    "acronym": profile["code"],
                    "team_name": profile["team"],
                    "team_color": profile["color"],
                    "compound": "FORMATION LAP", # Perfect real-time status update!
                    "stint_number": 0,
                    "tyre_age_laps": 0
                })
        else:
            # Build the matrix using active stint details
            for dn, s_data in latest_stints.items():
                profile = driver_map.get(dn, {"name": f"Driver {dn}", "code": str(dn), "team": "AAA_UNKNOWN", "color": "#737373"})
                matrix.append({
                    "driver_number": dn,
                    "broadcast_name": profile["name"],
                    "acronym": profile["code"],
                    "team_name": profile["team"],
                    "team_color": profile["color"],
                    "compound": str(s_data.get("compound", "UNKNOWN")).upper(),
                    "stint_number": s_data.get("stint_number", 1),
                    "tyre_age_laps": s_data.get("tyre_age_laps", 0)
                })
            
        # Secure sorting structure using strings explicitly to eliminate 500 crashes
        matrix.sort(key=lambda x: (str(x["team_name"]), int(x["driver_number"])))
        return {"session_key": SESSION_KEY, "grid_count": len(matrix), "stands": matrix}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))