



# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
import os
from fastapi.responses import FileResponse


app = FastAPI(title="TrackingMore v4 wrapper")

# Put your real key in env var TRACKINGMORE_API_KEY or replace below for quick test
API_KEY = os.getenv("TRACKINGMORE_API_KEY", "9t88jxmp-ivw8-glbt-mf7z-0ez3nrqrz80q")
API_BASE_URL = "https://api.trackingmore.com/v4"
    
class DetectRequest(BaseModel):
    tracking_number: str

class CreateTrackingRequest(BaseModel):
    tracking_number: str
    courier_code: Optional[str] = None  # preferred for v4
    slug: Optional[str] = None          # accept old-field name if frontend sends it
    order_number: Optional[str] = None
    customer_name: Optional[str] = None
    title: Optional[str] = None
    note: Optional[str] = None
    language: Optional[str] = None

def tm_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Tracking-Api-Key": API_KEY
    }



@app.post("/trackings/create")
def create_tracking(req: CreateTrackingRequest):
    """
    Create (import) a single tracking with TrackingMore v4 (create = create+get).
    v4 expects field 'courier_code' and 'tracking_number' in JSON body.
    If client sent 'slug', we map it to 'courier_code'.
    """
    payload: Dict[str, Any] = req.dict(exclude_none=True)

    # map legacy 'slug' -> courier_code
    if payload.get("slug") and not payload.get("courier_code"):
        payload["courier_code"] = payload.pop("slug")

    if not payload.get("courier_code"):
        raise HTTPException(status_code=400, detail="courier_code (or slug) is required. Use /couriers/detect to auto-detect if needed.")

    url = f"{API_BASE_URL}/trackings/create"
    try:
        resp = requests.post(url, json=payload, headers=tm_headers(), timeout=15)
        # Return TM JSON on success, or forward error body
        if resp.status_code >= 400:
            # helpful: include TM response JSON if available
            try:
                body = resp.json()
            except ValueError:
                body = resp.text
            raise HTTPException(status_code=resp.status_code, detail=body)
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))
    







@app.post("/couriers/detect")
def detect_carrier(req: DetectRequest):
    """
    Detect possible couriers for a tracking number,
    then fetch tracking info from dashboard if exists.
    """
    try:
        # Step 1: Detect courier
        detect_url = f"{API_BASE_URL}/couriers/detect"
        detect_resp = requests.post(
            detect_url,
            json={"tracking_number": req.tracking_number},
            headers=tm_headers(),
            timeout=15
        )
        detect_resp.raise_for_status()
        couriers = detect_resp.json().get("data", [])

        if not couriers:
            return {"error": "No courier detected"}

        courier_code = couriers[0]["courier_code"]

        # Step 2: Fetch tracking details (CORRECT ENDPOINT)
        track_url = f"{API_BASE_URL}/trackings/{courier_code}/{req.tracking_number}"
        track_resp = requests.get(track_url, headers=tm_headers(), timeout=15)
        track_resp.raise_for_status()

        data = track_resp.json().get("data", {})

        if data:
            return {
                "tracking_number": data.get("tracking_number"),
                "carrier": data.get("courier_code"),
                "status": data.get("status") or "Pending",
                "lastEvent": data.get("lastEvent") or data.get("latest_event") or "No events yet",
                "expected_delivery": data.get("expected_delivery"),
                "origin_info": data.get("origin_info", {}),
                "destination_info": data.get("destination_info", {})
            }

        # If no details yet but number exists in dashboard
        return {
            "tracking_number": req.tracking_number,
            "carrier": courier_code,
            "status": "Pending",
            "lastEvent": "No events yet",
            "expected_delivery": None,
            "origin_info": {},
            "destination_info": {}
        }

    except requests.HTTPError as e:
        raise HTTPException(status_code=detect_resp.status_code, detail=detect_resp.text)
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

    
from fastapi.staticfiles import StaticFiles

app.mount("/", StaticFiles(directory="TEST", html=True), name="static")