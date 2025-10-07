from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv
import base64
import traceback

# .env dosyasını yükle
load_dotenv()
FAL_API_KEY = os.getenv("FAL_API_KEY")

# Fal.ai image-to-image endpoint
FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"

# FastAPI instance
app = FastAPI()

# CORS ayarı (frontend ile iletişim için)
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
    try:
        # Görseli oku ve base64'e çevir
        image_bytes = await image.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        image_data_url = f"data:{image.content_type};base64,{image_b64}"

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
                # Hata mesajını yazdır ve geri döndür
                print("Fal.ai API Hatası:", response.status_code, response.text)
                try:
                    content = response.json()
                except:
                    content = {"error": response.text}
                return JSONResponse(status_code=response.status_code, content=content)

            data = response.json()
            return {"status": "success", "result": data}

    except Exception as e:
        # Hata logunu gör
        print("Backend Hatası:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})
