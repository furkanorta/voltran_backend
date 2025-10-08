from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import os
from dotenv import load_dotenv
import base64
import traceback
import re # Düzenli ifadeler için eklendi

# .env dosyasını yükle
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
    # image_base64: Base64 kodlanmış görsel verisi. 
    # Mümkünse Data URI (data:image/jpeg;base64,...) olmalı, ancak ham base64 de kabul edilir.
    image_base64: str 


# CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Basit test route
@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}

# Image-to-image endpoint
@app.post("/api/jobs")
async def create_job(request: JobRequest):
    try:
        prompt = request.prompt
        input_image_b64_data = request.image_base64
        
        # 1. Base64 Verisini Fal.ai'nin Beklediği Data URI Formatına Çevir (KRİTİK ADIM)
        # Bu, Postman'den sadece ham Base64 gelse bile, Data URI'yi doğru oluşturmayı sağlar.
        
        # Eğer veri zaten "data:" ile başlıyorsa, aynen kullan.
        if input_image_b64_data.startswith("data:"):
            image_data_url = input_image_b64_data
        else:
            # Ham Base64 stringi ise, yaygın MIME tipini varsayarak Data URI oluştur.
            # (Bu, Postman'de tam formatı girmeyi unuttuğunuz durumlar için bir önlemdir.)
            # Gerçek uygulamada, frontend'den MIME tipini almanız gerekir. Burada 'image/jpeg' varsayıyoruz.
            image_data_url = f"data:image/jpeg;base64,{input_image_b64_data}"

        # Boyut Kontrolü: Base64 stringin uzunluğunu kontrol et.
        if len(image_data_url) > 7 * 1024 * 1024:
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
                "image_url": image_data_url 
            }
        }

        # 3. Fal.ai'ye isteği gönder (Timeout 5 dakikaya yükseltildi)
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(FAL_URL, headers=headers, json=payload)

            if response.status_code != 200:
                print("Fal.ai API Hatası:", response.status_code, response.text)
                try:
                    content = response.json()
                    # Fal.ai'den 422 gelirse, detayları direk döndürelim.
                    if response.status_code == 422:
                        return JSONResponse(status_code=422, content=content)
                except:
                    content = {"error": "Fal.ai'den beklenmedik yanıt.", "details": response.text}
                
                # Fal.ai'den gelen başarısız yanıtlar için 502 kullanmak doğrudur.
                return JSONResponse(status_code=502, content=content) 

            data = response.json()
            return {"status": "success", "result": data}

    except Exception as e:
        error_details = traceback.format_exc()
        print("Backend Hatası:", error_details)
        
        # Beklenmedik bir hata olursa 500 dön.
        return JSONResponse(status_code=500, content={"error": "Sunucu içinde bir hata oluştu.", "details": str(e)})
