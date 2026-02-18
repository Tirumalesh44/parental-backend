# from fastapi import FastAPI, File, UploadFile
# from sqlalchemy.orm import Session
# from database import engine, SessionLocal
# from models import Base, Detection
# from datetime import datetime
# import json
# import requests
# import os

# app = FastAPI(title="Parental Control Backend")

# Base.metadata.create_all(bind=engine)

# HF_TOKEN = os.getenv("HF_TOKEN")
# HF_API_URL = "https://api-inference.huggingface.co/models/LukeJacob2023/nsfw-image-detector"

# SEXUAL_THRESHOLD = 0.60
# SESSION_GAP_SECONDS = 30


# def analyze_with_hf(image_bytes):
#     headers = {
#         "Authorization": f"Bearer {HF_TOKEN}"
#     }

#     response = requests.post(
#         HF_API_URL,
#         headers=headers,
#         data=image_bytes
#     )

#     return response.json()


# @app.post("/analyze-frame")
# async def analyze_frame(file: UploadFile = File(...)):

#     image_bytes = await file.read()

#     result = analyze_with_hf(image_bytes)

#     sexual_score = 0.0

#     if isinstance(result, list):
#         for r in result:
#             if r["label"] in ["porn", "sexy", "hentai"]:
#                 sexual_score = max(sexual_score, r["score"])

#     categories = []
#     if sexual_score >= SEXUAL_THRESHOLD:
#         categories.append("sexual")

#     now = datetime.utcnow().isoformat()

#     if categories:
#         db: Session = SessionLocal()
#         detection = Detection(
#             timestamp=now,
#             sexual_score=sexual_score,
#             violent_score=0.0,
#             categories=json.dumps(categories)
#         )
#         db.add(detection)
#         db.commit()
#         db.close()

#     return {
#         "categories": categories,
#         "sexual_score": round(sexual_score, 3),
#         "timestamp": now
#     }


# @app.get("/parent-summary")
# def parent_summary():

#     db: Session = SessionLocal()
#     total = db.query(Detection).count()
#     db.close()

#     return {
#         "total_bad_frames": total
#     }
from fastapi import FastAPI, File, UploadFile
from sqlalchemy.orm import Session
from database import engine, SessionLocal
from models import Base, Detection
from datetime import datetime
import json
import requests
import os

app = FastAPI(title="Parental Control Backend")

Base.metadata.create_all(bind=engine)

HF_TOKEN = os.getenv("HF_TOKEN")

# ⚠️ USE WORKING MODEL
HF_API_URL = "https://api-inference.huggingface.co/models/Falconsai/nsfw_image_detection"

SEXUAL_THRESHOLD = 0.60


def analyze_with_hf(image_bytes):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/octet-stream"
    }

    try:
        response = requests.post(
            HF_API_URL,
            headers=headers,
            data=image_bytes,
            timeout=30
        )

        print("HF STATUS:", response.status_code)
        print("HF RAW RESPONSE:", response.text)

        if response.status_code != 200:
            return []

        try:
            return response.json()
        except:
            return []

    except Exception as e:
        print("HF ERROR:", str(e))
        return []


@app.post("/analyze-frame")
async def analyze_frame(file: UploadFile = File(...)):

    image_bytes = await file.read()

    result = analyze_with_hf(image_bytes)

    sexual_score = 0.0

    if isinstance(result, list):
        for r in result:
            label = r.get("label", "").lower()
            score = r.get("score", 0.0)

            if label in ["nsfw", "porn", "sexy", "hentai"]:
                sexual_score = max(sexual_score, score)

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
