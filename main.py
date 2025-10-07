from fastapi import FastAPI, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
import base64
import traceback

# .env dosyasını yükle
# Render ortamında, ortam değişkenlerinin otomatik yüklendiğini varsayarız.
load_dotenv()
FAL_API_KEY = os.getenv("FAL_API_KEY")

# Fal.ai image-to-image endpoint
FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"

# FastAPI instance
app = FastAPI()

# Gelen JSON isteğinin yapısını tanımlayan Pydantic modeli
class JobRequest(BaseModel):
    # prompt: Kullanıcının metin istemi (String)
    prompt: str
    # image_base64: Base64 kodlanmış görsel verisi (data:image/png;base64,... formatında olmalı)
    image_base64: str


# CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production’da sadece frontend URL ekle
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True, # Genellikle JSON body ile çalışırken gereklidir
)

# Basit test route
@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}

# Image-to-image endpoint
# NOT: Artık form-data yerine JSON body bekliyor.
@app.post("/api/jobs")
async def create_job(request: JobRequest):
    try:
        # Pydantic modelinden verileri al
        prompt = request.prompt
        image_data_url = request.image_base64
        
        # 1. Base64 Veri Kontrolü (URL'den 1MB'lık Base64 başlığını keserek boyut kontrolü)
        # Base64 veri yaklaşık 4/3 oranında daha büyük olacağı için 5MB * 4/3 = 6.6MB
        # URL'nin tamamı yerine veri kısmının uzunluğunu kontrol edin.
        if len(image_data_url) > 7 * 1024 * 1024:  # Örnek: Base64 string boyutu 7MB'tan büyükse reddet
             return JSONResponse(status_code=413, content={"error": "Görsel verisi çok büyük. Maksimum 5MB dosya boyutu limitini aşıyor."})

        # 2. Fal.ai API'si için Header ve Payload hazırla
        if not FAL_API_KEY:
             return JSONResponse(status_code=500, content={"error": "FAL_API_KEY ortam değişkeni ayarlanmamış."})


        headers = {
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "input": {
                "prompt": prompt,
                "image_url": image_data_url # Fal.ai Base64 Data URL'i bekler
            }
        }

        # 3. Fal.ai'ye isteği gönder
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
        error_details = traceback.format_exc()
        print("Backend Hatası:", error_details)
        
        return JSONResponse(status_code=500, content={"error": "Sunucu içinde bir hata oluştu.", "details": str(e)})
