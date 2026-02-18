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

# ENV VARIABLES
HF_TOKEN = os.getenv("HF_TOKEN")
HF_API_URL = "https://api-inference.huggingface.co/models/LukeJacob2023/nsfw-image-detector"

SEXUAL_THRESHOLD = 0.60


# -----------------------------
# SAFE HUGGINGFACE CALL
# -----------------------------
def analyze_with_hf(image_bytes):

    if not HF_TOKEN:
        return {"error": "HF_TOKEN not configured"}

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            data=image_bytes,
            timeout=60
        )

        print("HF STATUS:", response.status_code)
        print("HF RESPONSE:", response.text)

        if response.status_code != 200:
            return {"error": response.text}

        try:
            return response.json()
        except Exception:
            return {"error": "Invalid JSON returned from HF"}

    except Exception as e:
        return {"error": str(e)}


# -----------------------------
# ANALYZE FRAME
# -----------------------------
@app.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):

    image_bytes = await file.read()

    result = analyze_with_hf(image_bytes)

    # If HF error → do NOT crash backend
    if isinstance(result, dict) and "error" in result:
        return {
            "categories": [],
            "sexual_score": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "hf_error": result["error"]
        }

    sexual_score = 0.0

    if isinstance(result, list):
        for r in result:
            label = r.get("label", "")
            score = r.get("score", 0.0)

            if label.lower() in ["porn", "sexy", "hentai"]:
                sexual_score = max(sexual_score, score)

    categories = []
    if sexual_score >= SEXUAL_THRESHOLD:
        categories.append("sexual")

    now = datetime.utcnow().isoformat()

    # Store only bad detections
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


# -----------------------------
# PARENT SUMMARY
# -----------------------------
@app.get("/parent-summary")
def parent_summary():

    db: Session = SessionLocal()
    total = db.query(Detection).count()
    db.close()

    return {
        "total_bad_frames": total
    }


# -----------------------------
# HEALTH CHECK (IMPORTANT)
# -----------------------------
@app.get("/")
def health():
    return {"status": "Backend running"}
