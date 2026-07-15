from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import redis
import uuid
import os
import json

app = FastAPI()

# Connect to Redis using the Kubernetes service DNS name
REDIS_HOST = os.getenv("REDIS_HOST", "redis-service")
r = redis.Redis(host=REDIS_HOST, port=6379, db=0, decode_responses=True)

PRICING = {
    "car": 2000,
    "dog": 1000,
    "child": 750
}

class ApplicationData(BaseModel):
    catalog_item: str
    name: str
    address: str
    item_age: int
    years_of_insurance: int

@app.post("/api/apply")
def create_application(data: ApplicationData):
    if data.catalog_item not in PRICING:
        raise HTTPException(status_code=400, detail="Invalid catalog item")
    
    app_id = str(uuid.uuid4())
    total_price = PRICING[data.catalog_item]
    
    payload = data.model_dump()
    payload["total_price"] = total_price
    payload["status"] = "Pending"
    
    # Store in Redis for 1 hour (3600 seconds)
    r.setex(app_id, 3600, json.dumps(payload))
    return {"application_id": app_id}

@app.get("/api/application/{app_id}")
def get_application(app_id: str):
    data = r.get(app_id)
    if not data:
        raise HTTPException(status_code=404, detail="Application not found")
    return json.loads(data)

@app.post("/api/confirm/{app_id}")
def confirm_application(app_id: str):
    data = r.get(app_id)
    if not data:
        raise HTTPException(status_code=404, detail="Application not found")
    
    payload = json.loads(data)
    payload["status"] = "Confirmed"
    
    # Update status or save to permanent DB (Deleting from cache for cleanup here)
    r.delete(app_id)
    return {"message": "Insurance Confirmed Successfully!", "details": payload}