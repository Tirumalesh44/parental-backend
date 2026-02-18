# app.py (or main.py) - Unchanged from previous, but confirming for completeness
from fastapi import FastAPI, File, UploadFile
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base, Detection
from datetime import datetime
import json
import os
from PIL import Image
import io
from transformers import pipeline

app = FastAPI(title="Parental Control Backend")

# Create tables
Base.metadata.create_all(bind=engine)

# ==============================
# CONFIG
# ==============================

# Using Marqo/nsfw-image-detection-384 for lighter weight (~5.8M params, faster on CPU)
MODEL_NAME = "Marqo/nsfw-image-detection-384"  # Switch to "Falconsai/nsfw_image_detection" if preferred

SEXUAL_THRESHOLD = 0.60
SESSION_GAP_SECONDS = 30  # Not used in code, but kept as is

# Load model at startup (CPU only, since Render has no GPU)
classifier = pipeline("image-classification", model=MODEL_NAME, device=-1)
print(f"Loaded model: {MODEL_NAME}")  # For logs

# ==============================
# LOCAL INFERENCE
# ==============================

def analyze_local(image: Image.Image):
    try:
        return classifier(image)
    except Exception as e:
        return {
            "error": f"Local Inference Error: {str(e)}"
        }

# ==============================
# ANALYZE FRAME
# ==============================

@app.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):

    contents = await file.read()
    try:
        image = Image.open(io.BytesIO(contents))
    except Exception as e:
        return {
            "categories": [],
            "sexual_score": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "hf_error": f"Image Open Error: {str(e)}"  # Reuse field for error
        }

    hf_result = analyze_local(image)

    # If error → return safely
    if isinstance(hf_result, dict) and "error" in hf_result:
        return {
            "categories": [],
            "sexual_score": 0.0,
            "timestamp": datetime.utcnow().isoformat(),
            "hf_error": hf_result["error"]
        }

    # Results are list of predictions
    # Example for Marqo/Falconsai:
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