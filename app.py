from fastapi import FastAPI, File, UploadFile
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base, Detection
from datetime import datetime
import json
import requests
import os

app = FastAPI(title="Parental Control Backend")

# Create tables
Base.metadata.create_all(bind=engine)

# ==============================
# CONFIG
# ==============================

HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/Falconsai/nsfw_image_detection"

SEXUAL_THRESHOLD = 0.60
SESSION_GAP_SECONDS = 30

headers = {
    "Authorization": f"Bearer {HF_TOKEN}"
}

# ==============================
# HUGGINGFACE INFERENCE
# ==============================

def analyze_with_hf(image_bytes: bytes):

    response = requests.post(
        HF_API_URL,
        headers=headers,
        data=image_bytes,
        timeout=30
    )

    if response.status_code != 200:
        return {
            "error": f"HuggingFace Error {response.status_code}",
            "raw": response.text
        }

    try:
        return response.json()
    except:
        return {
            "error": "Invalid JSON from HuggingFace",
            "raw": response.text
        }

# ==============================
# ANALYZE FRAME
# ==============================

@app.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):

    contents = await file.read()

    hf_result = analyze_with_hf(contents)

    # If HF error → return safely
    if isinstance(hf_result, dict) and "error" in hf_result:
        return {
            "categories": [],
            "sexual_score": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "hf_error": hf_result["error"]
        }

    # HF returns list of predictions
    # Example:
    # [
    #   {"label": "nsfw", "score": 0.98},
    #   {"label": "sfw", "score": 0.02}
    # ]

    sexual_score = 0.0

    for item in hf_result:
        if item["label"].lower() == "nsfw":
            sexual_score = item["score"]
            break

    categories = []
    if sexual_score >= SEXUAL_THRESHOLD:
        categories.append("sexual")

    now = datetime.utcnow().isoformat()

    # Store only if bad content
    if categories:
        db: Session = SessionLocal()

        detection = Detection(
            timestamp=now,
            sexual_score=sexual_score,
            violent_score=0.0,
            categories=json.dumps(categories)
        )

        db.add(detection)
        db.commit()
        db.close()

    return {
        "categories": categories,
        "sexual_score": round(sexual_score, 3),
        "timestamp": now
    }

# ==============================
# PARENT SUMMARY
# ==============================

@app.get("/parent-summary")
def parent_summary():

    db: Session = SessionLocal()

    total_bad_frames = db.query(Detection).count()

    db.close()

    return {
        "total_bad_frames": total_bad_frames
    }

# ==============================
# HEALTH CHECK
# ==============================

@app.get("/")
def health():
    return {"status": "Backend Running"}
