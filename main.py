from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
import traceback

# Ortam değişkenlerini yükle
load_dotenv()
FAL_API_KEY = os.getenv("FAL_API_KEY")

FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"

app = FastAPI(title="Voltran Backend API 🚀")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

class JobRequest(BaseModel):
    prompt: str
    image_base64: str

@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}

@app.post("/api/jobs")
async def create_job(request: JobRequest):
    try:
        if not FAL_API_KEY:
            raise HTTPException(status_code=500, detail="FAL_API_KEY ortam değişkeni ayarlanmamış.")

        # 5MB limit kontrolü (~7MB base64)
        if len(request.image_base64) > 7 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Görsel çok büyük. Maksimum 5MB.")

        headers = {
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": request.prompt,
            "image_base64": request.image_base64
        }

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(FAL_URL, headers=headers, json=payload)

        if response.status_code != 200:
            try:
                content = response.json()
            except:
                content = {"error": "Fal.ai'den beklenmedik yanıt.", "details": response.text}
            raise HTTPException(status_code=502, detail=content)

        return {"status": "success", "result": response.json()}

    except HTTPException as e:
        raise e
    except Exception as e:
        print("Backend Hatası:", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Sunucu içinde bir hata oluştu.", "details": str(e)},
        )
