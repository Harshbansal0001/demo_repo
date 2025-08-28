from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
from datetime import date
import requests
import os

from TEST.models import Tracking
from TEST.database import engine, Base, get_db


# -------------------
# App setup
# -------------------
app = FastAPI(title="TrackingMore v4 wrapper")

API_KEY = os.getenv("TRACKINGMORE_API_KEY", "9t88jxmp-ivw8-glbt-mf7z-0ez3nrqrz80q")
API_BASE_URL = "https://api.trackingmore.com/v4"


# -------------------
# Schemas
# -------------------
class DetectRequest(BaseModel):
    tracking_number: str
    courier_code: Optional[str] = None


class CreateTrackingRequest(BaseModel):
    tracking_number: str
    courier_code: Optional[str] = None
    slug: Optional[str] = None
    date: Optional[date] = None
    order_number: Optional[str] = None
    copy: Optional[str] = None
    customer_name: Optional[str] = None
    title: Optional[str] = None
    note: Optional[str] = None
    language: Optional[str] = None


# -------------------
# Helpers
# -------------------
def tm_headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "Tracking-Api-Key": API_KEY,
    }


# -------------------
# Routes
# -------------------
@app.post("/trackings/create")
def create_tracking(req: CreateTrackingRequest, db: Session = Depends(get_db)):
    payload: Dict[str, Any] = req.dict(exclude_none=True)

    if payload.get("slug") and not payload.get("courier_code"):
        payload["courier_code"] = payload.pop("slug")

    if not payload.get("courier_code"):
        raise HTTPException(status_code=400, detail="courier_code (or slug) is required.")

    url = f"{API_BASE_URL}/trackings/create"
    try:
        resp = requests.post(url, json=payload, headers=tm_headers(), timeout=15)

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except ValueError:
                body = resp.text
            raise HTTPException(status_code=resp.status_code, detail=body)

        result = resp.json()
        print("✅ API Response:", result)

        try:
            tracking = Tracking(
                tracking_number=req.tracking_number,
                courier_code=req.courier_code,
                date=req.date,
                copy=req.copy,
                order_number=req.order_number,
                customer_name=req.customer_name,
                title=req.title,
                note=req.note,
            )
            db.add(tracking)
            db.commit()
            db.refresh(tracking)
        except Exception as db_error:
            db.rollback()
            print("❌ DB Error:", str(db_error))
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")

        return {"db_id": tracking.id, "tracking": result}

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"TrackingMore API error: {str(e)}")



@app.get("/trackings")
def list_trackings(db: Session = Depends(get_db)):
    return db.query(Tracking).all()


@app.post("/couriers/detect")
def detect_carrier(req: DetectRequest):
    """Detect courier automatically using TrackingMore's detect API."""
    try:
        payload = {"tracking_number": req.tracking_number}
        url = f"{API_BASE_URL}/couriers/detect"
        resp = requests.post(url, json=payload, headers=tm_headers(), timeout=15)

        if resp.status_code >= 400:
            try:
                body = resp.json()
            except ValueError:
                body = resp.text
            raise HTTPException(status_code=resp.status_code, detail=body)

        return resp.json()

    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))


# -------------------
# Static files (served at /static to avoid route conflicts)
# -------------------
app.mount("/static", StaticFiles(directory="TEST", html=True), name="static")
