# main.py
from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from fastapi.middleware.cors import CORSMiddleware
import requests
import os
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from TEST.database import SessionLocal, engine, Base
import TEST.models as models

Base.metadata.create_all(bind=engine)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(title="TrackingMore v4 wrapper")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Put your real key in env var TRACKINGMORE_API_KEY or replace below for quick test
API_KEY = os.getenv("TRACKINGMORE_API_KEY", "h9q3qu3o-mqou-bfip-snc3-jdcv3w6gx7xb")
API_BASE_URL = "https://api.trackingmore.com/v4"

# DB dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class DetectRequest(BaseModel):
    tracking_number: str
    courier_code: Optional[str] = None

class CreateTrackingRequest(BaseModel):
    tracking_number: str
    courier_code: Optional[str] = None
    slug: Optional[str] = None
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

# Store tracking data in DB
def save_tracking(db: Session, data: dict):
    # Check if tracking already exists
    existing = db.query(models.Tracking).filter(
        models.Tracking.tracking_number == data["tracking_number"],
        models.Tracking.courier_code == data["carrier"]
    ).first()
    
    if existing:
        # Update existing record
        existing.status = data["status"]
        existing.last_event = data["last_event"]
        existing.note = data.get("note", existing.note)
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # Create new record
        t = models.Tracking(
            tracking_number=data["tracking_number"],
            courier_code=data["carrier"],
            status=data["status"],
            last_event=data["last_event"],
            note=data.get("note", "")
        )
        db.add(t)
        db.commit()
        db.refresh(t)
        return t

@app.get("/")
def read_root():
    return FileResponse(os.path.join(BASE_DIR, "index.html"))

@app.get("/trackings")
def get_all_trackings(tracking_numbers: Optional[List[str]] = None, db: Session = Depends(get_db)):
    if tracking_numbers:
        trackings = db.query(models.Tracking).filter(
            models.Tracking.tracking_number.in_(tracking_numbers)
        ).all()
    else:
        trackings = db.query(models.Tracking).all()
    
    return [
        {
            "id": t.id,
            "tracking_number": t.tracking_number,
            "courier_code": t.courier_code,
            "status": t.status,
            "last_event": t.last_event,
            "note": t.note
        }
        for t in trackings
    ]

@app.post("/trackings/create")
def create_tracking(req: CreateTrackingRequest, db: Session = Depends(get_db)):
    """
    Create (import) a single tracking with TrackingMore v4.
    """
    payload: Dict[str, Any] = req.dict(exclude_none=True)

    # Map legacy 'slug' -> courier_code
    if payload.get("slug") and not payload.get("courier_code"):
        payload["courier_code"] = payload.pop("slug")

    if not payload.get("courier_code"):
        raise HTTPException(
            status_code=400, 
            detail="courier_code (or slug) is required. Use /couriers/detect to auto-detect if needed."
        )

    url = f"{API_BASE_URL}/trackings/create"
    
    try:
        resp = requests.post(url, json=payload, headers=tm_headers(), timeout=15)
        
        if resp.status_code >= 400:
            try:
                error_body = resp.json()
                error_detail = error_body.get("message", resp.text)
            except ValueError:
                error_detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail=error_detail)
        
        response_data = resp.json()
        data = response_data.get("data", {})

        # Prepare result for database storage
        result = {
            "tracking_number": data.get("tracking_number", payload.get("tracking_number")),
            "carrier": data.get("courier_code", payload.get("courier_code")),
            "status": data.get("status", "Pending"),
            "last_event": data.get("lastEvent") or data.get("latest_event") or "No events yet",
            "note": payload.get("note", "")
        }

        # Save to database
        saved_tracking = save_tracking(db, result)
        
        # Return the saved data
        return JSONResponse(content={
            "id": saved_tracking.id,
            "tracking_number": saved_tracking.tracking_number,
            "courier_code": saved_tracking.courier_code,
            "status": saved_tracking.status,
            "last_event": saved_tracking.last_event,
            "note": saved_tracking.note,
            "api_response": response_data  # Include original API response
        })
        
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")

@app.post("/couriers/detect")
def detect_carrier(req: DetectRequest, db: Session = Depends(get_db)):
    """
    Detect carrier and get tracking info.
    If courier_code is provided, get tracking directly.
    If not provided, auto-detect the courier first.
    """
    tracking_number = req.tracking_number.strip()
    courier_code = req.courier_code.strip().lower() if req.courier_code else None
    
    try:
        if courier_code:
            # Get tracking info directly with known courier
            url = f"{API_BASE_URL}/trackings/{courier_code}/{tracking_number}"
            resp = requests.get(url, headers=tm_headers(), timeout=15)
        else:
            # Auto-detect courier first
            detect_url = f"{API_BASE_URL}/carriers/detect"
            detect_resp = requests.post(
                detect_url, 
                json={"tracking_number": tracking_number}, 
                headers=tm_headers(), 
                timeout=15
            )
            
            if detect_resp.status_code != 200:
                raise HTTPException(
                    status_code=detect_resp.status_code,
                    detail=f"Courier detection failed: {detect_resp.text}"
                )
            
            detect_data = detect_resp.json().get("data", {})
            if not detect_data:
                raise HTTPException(status_code=400, detail="Could not detect courier for this tracking number")
            
            # Get the detected courier and fetch tracking info
            detected_courier = detect_data[0].get("courier_code") if detect_data else None
            if not detected_courier:
                raise HTTPException(status_code=400, detail="No suitable courier detected")
            
            courier_code = detected_courier
            url = f"{API_BASE_URL}/trackings/{courier_code}/{tracking_number}"
            resp = requests.get(url, headers=tm_headers(), timeout=15)
        
        if resp.status_code == 404:
            # Try to create tracking first, then retrieve
            create_payload = {
                "tracking_number": tracking_number,
                "courier_code": courier_code
            }
            create_url = f"{API_BASE_URL}/trackings/create"
            create_resp = requests.post(create_url, json=create_payload, headers=tm_headers(), timeout=15)
            
            if create_resp.status_code >= 400:
                raise HTTPException(
                    status_code=404,
                    detail=f"Tracking not found and could not be created: {create_resp.text}"
                )
            
            # Now try to get the tracking info again
            resp = requests.get(url, headers=tm_headers(), timeout=15)
        
        if resp.status_code >= 400:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)
            
        response_data = resp.json()
        track_data = response_data.get("data", {})
        
        if not track_data:
            return JSONResponse(content={
                "message": "Tracking created but no data available yet",
                "tracking_number": tracking_number,
                "carrier": courier_code,
                "status": "Pending"
            })
        
        # Build comprehensive response
        result = {
            "tracking_number": track_data.get("tracking_number", tracking_number),
            "carrier": track_data.get("courier_code", courier_code),
            "status": track_data.get("status") or "Pending",
            "delivery_status": track_data.get("delivery_status"),
            "shipment_type": track_data.get("shipment_type"),
            "note": track_data.get("note"),
            "expected_delivery": track_data.get("expected_delivery"),
            "last_event": (
                track_data.get("lastEvent") 
                or track_data.get("latest_event") 
                or "No events yet"
            ),
            "origin_info": track_data.get("origin_info", {}),
            "destination_info": track_data.get("destination_info", {}),
            "events": track_data.get("origin_info", {}).get("trackinfo", [])
        }
        
        # Save to database
        save_tracking(db, result)
        
        # Clean response (remove empty values)
        clean_response = {k: v for k, v in result.items() if v not in [None, {}, [], ""]}
        return JSONResponse(content=clean_response)
        
    except requests.HTTPError as e:
        raise HTTPException(status_code=500, detail=f"HTTP error: {str(e)}")
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Request error: {str(e)}")

@app.get("/couriers")
def list_couriers():
    """List all available couriers"""
    url = f"{API_BASE_URL}/couriers/all"
    try:
        resp = requests.get(url, headers=tm_headers(), timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch couriers: {str(e)}")

# Mount static files - this should be at the end
app.mount("/static", StaticFiles(directory="TEST", html=True), name="static")