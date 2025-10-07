from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
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

# CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production’da sadece frontend URL ekle
    allow_methods=["*"],
    allow_headers=["*"],
)

# Basit test route
@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}

# Image-to-image endpoint
@app.post("/api/jobs")
async def create_job(prompt: str = Form(...), image: UploadFile = File(...)):
    # 422 hatasına karşı dirençli hale getirildi. 
    # Hata devam ederse, bu dosya boyutu limitini aştığınız anlamına gelir.
    try:
        # 1. Gelen görseli hızlıca oku ve base64'e çevir.
        # .read() işlemi await ile doğru yapılıyor.
        image_bytes = await image.read()
        
        # Dosya boyutunu kontrol etmek iyi bir pratik olabilir. 
        # Render'ın limitleri genellikle 1MB-10MB arasındadır.
        if len(image_bytes) > 5 * 1024 * 1024:  # Örnek: 5MB'tan büyükse reddet
             return JSONResponse(status_code=413, content={"error": "Dosya boyutu 5MB limitini aşıyor."})

        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:{image.content_type};base64,{image_b64}"

        # 2. Fal.ai API'si için Header ve Payload hazırla
        # FAL_API_KEY boşsa hemen hata döndür
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

        # 3. Fal.ai'ye isteği gönder
        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(FAL_URL, headers=headers, json=payload)

            if response.status_code != 200:
                # Fal.ai API'sinden gelen hata yanıtını direkt olarak döndür
                print("Fal.ai API Hatası:", response.status_code, response.text)
                try:
                    content = response.json()
                except:
                    # JSON değilse, ham metni hata olarak ekle
                    content = {"error": "Fal.ai'den beklenmedik yanıt.", "details": response.text}
                
                # Fal.ai'den gelen status kodu döndürmek yerine, sunucudan 502 (Bad Gateway)
                # veya 500 dönmek daha doğrudur.
                return JSONResponse(status_code=502, content=content) 

            data = response.json()
            return {"status": "success", "result": data}

    except Exception as e:
        # Dosya okuma hatası, Form alanının eksikliği veya diğer backend hataları
        error_details = traceback.format_exc()
        print("Backend Hatası:", error_details)
        
        # Eğer hata Pydantic/FastAPI'den geliyorsa (422), bu try bloğu yakalamayabilir.
        # Ama dosya okuma veya httpx hatalarını yakalaması için önemlidir.
        return JSONResponse(status_code=500, content={"error": "Sunucu içinde bir hata oluştu.", "details": str(e)})
