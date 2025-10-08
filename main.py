from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
import traceback

# Ortam değişkenlerini yükle (.env dosyasından)
load_dotenv()
FAL_API_KEY = os.getenv("FAL_API_KEY")

# Fal.ai endpoint
FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"

# FastAPI instance
app = FastAPI()

# CORS (frontend bağlantısı için)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prod'da domain ekle
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Veri modeli
class JobRequest(BaseModel):
    prompt: str
    image_base64: str


@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}


@app.post("/api/jobs")
async def create_job(request: JobRequest):
    try:
        prompt = request.prompt
        image_data_url = request.image_base64

        # Görsel boyut kontrolü (yaklaşık 5MB limit)
        if len(image_data_url) > 7 * 1024 * 1024:
            return JSONResponse(
                status_code=413,
                content={"error": "Görsel verisi çok büyük. Maksimum 5MB dosya boyutu limitini aşıyor."},
            )

        if not FAL_API_KEY:
            return JSONResponse(
                status_code=500,
                content={"error": "FAL_API_KEY ortam değişkeni ayarlanmamış."},
            )

        headers = {
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": {
                "prompt": prompt,
                "image_url": image_data_url
            }
        }

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(FAL_URL, headers=headers, json=payload)

        if response.status_code != 200:
            print("Fal.ai API Hatası:", response.status_code, response.text)
            try:
                content = response.json()
            except:
                content = {"error": "Fal.ai'den beklenmedik yanıt.", "details": response.text}

            return JSONResponse(status_code=502, content=content)

        data = response.json()
        return {"status": "success", "result": data}

    except Exception as e:
        print("Backend Hatası:", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Sunucu içinde bir hata oluştu.", "details": str(e)},
        )
