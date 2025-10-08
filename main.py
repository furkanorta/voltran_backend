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

# Fal.ai endpoint
FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"

# FastAPI instance
app = FastAPI(title="Voltran Backend API 🚀")

# CORS middleware
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


# API sınıfı
class FalAPI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.url = FAL_URL

    async def send_job(self, prompt: str, image_base64: str):
        if not self.api_key:
            raise HTTPException(status_code=500, detail="FAL_API_KEY ortam değişkeni ayarlanmamış.")

        # 5MB boyut limiti (~7MB base64 hali)
        if len(image_base64) > 7 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Görsel verisi çok büyük. Maksimum 5MB.")

        headers = {
            "Authorization": f"Key {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "prompt": prompt,
            "image_base64": image_base64
        }

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(self.url, headers=headers, json=payload)

        if response.status_code != 200:
            try:
                content = response.json()
            except:
                content = {"error": "Fal.ai'den beklenmedik yanıt.", "details": response.text}
            raise HTTPException(status_code=502, detail=content)

        return response.json()


# FalAPI örneği
fal_api = FalAPI(FAL_API_KEY)


# Routes
@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}


@app.post("/api/jobs")
async def create_job(request: JobRequest):
    try:
        result = await fal_api.send_job(request.prompt, request.image_base64)
        return {"status": "success", "result": result}
    except HTTPException as e:
        raise e
    except Exception as e:
        print("Backend Hatası:", traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"error": "Sunucu içinde bir hata oluştu.", "details": str(e)},
        )
