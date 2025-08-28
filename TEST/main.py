
<<<<<<< main



=======
>>>>>>> local
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import requests
import os
from fastapi.responses import FileResponse
<<<<<<< main
=======
from fastapi import HTTPException
from fastapi.responses import JSONResponse
import requests
>>>>>>> local


app = FastAPI(title="TrackingMore v4 wrapper")

# Put your real key in env var TRACKINGMORE_API_KEY or replace below for quick test
API_KEY = os.getenv("TRACKINGMORE_API_KEY", "9t88jxmp-ivw8-glbt-mf7z-0ez3nrqrz80q")
<<<<<<< main
API_BASE_URL = "https://api.trackingmore.com/v4"
    
class DetectRequest(BaseModel):
    tracking_number: str
=======
API_BASE_URL ="https://api.trackingmore.com/v4"
    
class DetectRequest(BaseModel):
    tracking_number: str
    courier_code: Optional[str] = None  # Optional courier code
>>>>>>> local

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


<<<<<<< main

=======
 
>>>>>>> local
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
    
<<<<<<< main





=======




# @app.post("/couriers/detect")
# def detect_carrier(req: DetectRequest):
#     try:
#         # Clean inputs
#         tracking_number = req.tracking_number.strip()
#         courier_code = req.courier_code.strip().lower()
        
#         # Fetch tracking details directly using provided courier_code
#         track_url = f"{API_BASE_URL}/trackings/{courier_code}/{tracking_number}"
#         track_resp = requests.get(track_url, headers=tm_headers(), timeout=15)
        
#         # Handle 404 - tracking not found in your dashboard
#         if track_resp.status_code == 404:
#             return JSONResponse(content={
#                 "error": "Tracking not found", 
#                 "message": "This tracking number does not exist in your TrackingMore dashboard"
#             })
            
#         track_resp.raise_for_status()
#         track_data = track_resp.json().get("data", {})
        
#         # If no data returned (empty response)
#         if not track_data:
#             return JSONResponse(content={
#                 "error": "No tracking data available",
#                 "message": "Tracking exists but no details available yet"
#             })
        
#         # Build comprehensive response with all available fields
#         response = {
#             "tracking_number": track_data.get("tracking_number", tracking_number),
#             "carrier": track_data.get("courier_code", courier_code),
#             "status": track_data.get("status") or "Pending",
#             "delivery_status": track_data.get("delivery_status"),
#             "shipment_type": track_data.get("shipment_type"),  # Hard Copy/Soft Copy
#             "delivery_type": track_data.get("delivery_type"),  # Alternative field name
#             "note": track_data.get("note"),
#             "customer_name": track_data.get("customer_name"),
#             "order_number": track_data.get("order_number"),
#             "expected_delivery": track_data.get("expected_delivery"),
#             "last_event": (
#                 track_data.get("lastEvent") 
#                 or track_data.get("latest_event") 
#                 or track_data.get("last_update_time")
#                 or "No events yet"
#             ),
#             "origin_info": track_data.get("origin_info", {}),
#             "destination_info": track_data.get("destination_info", {}),
#             "events": track_data.get("origin_info", {}).get("trackinfo", []),
#             "transit_time": track_data.get("transit_time"),
#             "stay_time": track_data.get("stay_time"),
#             "service_code": track_data.get("service_code"),
#             "package_status": track_data.get("package_status")
#         }
        
#         # Remove empty/null values for cleaner response
#         clean_response = {
#             k: v for k, v in response.items() 
#             if v not in [None, {}, [], ""]
#         }
        
#         return JSONResponse(content=clean_response)
        
#     except requests.HTTPError as e:
#         error_detail = f"TrackingMore API error: {e}"
#         try:
#             # Try to get more specific error from response
#             error_response = track_resp.json()
#             error_detail = error_response.get("meta", {}).get("message", str(e))
#         except:
#             pass
            
#         raise HTTPException(status_code=track_resp.status_code, detail=error_detail)
        
#     except requests.RequestException as e:
#         raise HTTPException(status_code=500, detail=f"Request failed: {str(e)}")
>>>>>>> local


@app.post("/couriers/detect")
def detect_carrier(req: DetectRequest):
<<<<<<< main
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
=======
    try:
        tracking_number = req.tracking_number.strip()
        courier_code = req.courier_code.strip().lower()
        
       
    
        track_url = f"{API_BASE_URL}/trackings/{courier_code}/{tracking_number}"
        track_resp = requests.get(track_url, headers=tm_headers(), timeout=15)
        print(track_url)
        
        if track_resp.status_code == 404:
            return JSONResponse(content={
                "error": "Tracking still not found after creation attempt",
                "message": "Please verify courier code and tracking number are correct"
            })
            
        track_resp.raise_for_status()
        track_data = track_resp.json().get("data", {})
        
        if not track_data:
            return JSONResponse(content={
                "message": "Tracking created but no data available yet",
                "tracking_number": tracking_number,
                "carrier": courier_code,
                "status": "Pending"
            })
        
        # Build response with all available fields
        response = {
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
        
        # Clean response
        clean_response = {k: v for k, v in response.items() if v not in [None, {}, [], ""]}
        return JSONResponse(content=clean_response)
        
    except requests.HTTPError as e:
        raise HTTPException(status_code=track_resp.status_code, detail=str(e))
>>>>>>> local
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=str(e))

    
from fastapi.staticfiles import StaticFiles

<<<<<<< main
=======
    
from fastapi.staticfiles import StaticFiles

>>>>>>> local
app.mount("/", StaticFiles(directory="TEST", html=True), name="static")