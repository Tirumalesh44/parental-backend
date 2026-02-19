from fastapi import FastAPI, File, UploadFile
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base, Detection
from datetime import datetime
import json
import io
from PIL import Image
from transformers import pipeline
import torch

app = FastAPI(title="Parental Control Backend")

Base.metadata.create_all(bind=engine)

device = 0 if torch.cuda.is_available() else -1

nsfw_classifier = pipeline(
    "image-classification",
    model="LukeJacob2023/nsfw-image-detector",
    device=device
)

SEXUAL_THRESHOLD = 0.60

@app.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):

    contents = await file.read()
    image = Image.open(io.BytesIO(contents)).convert("RGB")

    result = nsfw_classifier(image)

    sexual_score = max(
        (r["score"] for r in result if r["label"] in ["porn", "sexy", "hentai"]),
        default=0.0
    )

    categories = []
    if sexual_score >= SEXUAL_THRESHOLD:
        categories.append("sexual")

    now = datetime.utcnow().isoformat()

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

@app.get("/parent-summary")
def parent_summary():

    db: Session = SessionLocal()
    total = db.query(Detection).count()
    db.close()

    return {
        "total_bad_frames": total
    }
