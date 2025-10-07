from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
from dotenv import load_dotenv
import traceback

load_dotenv()
FAL_API_KEY = os.getenv("FAL_API_KEY")

# Fal.ai image-to-image endpoint
FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"
UPLOAD_URL = "https://fal.run/api/upload"  # fal.ai upload endpoint

app = FastAPI()

# CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # frontend URL ekle
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}

@app.post("/api/jobs")
async def create_job(prompt: str = Form(...), image: UploadFile = File(...)):
    try:
        headers = {"Authorization": f"Key {FAL_API_KEY}"}

        # 1️⃣ Görseli Fal.ai'ye upload et
        async with httpx.AsyncClient(timeout=180) as client:
            upload_resp = await client.post(
                UPLOAD_URL,
                headers=headers,
                files={"file": (image.filename, await image.read(), image.content_type)}
            )

            if upload_resp.status_code != 200:
                print("Fal.ai Upload Hatası:", upload_resp.text)
                return JSONResponse(status_code=upload_resp.status_code, content=upload_resp.json())

            upload_data = upload_resp.json()
            image_url = upload_data.get("url")
            if not image_url:
                return {"error": "Upload başarısız", "raw": upload_data}

            # 2️⃣ prompt + image_url ile resmi düzenlet
            payload = {"input": {"prompt": prompt, "image_url": image_url}}
            response = await client.post(FAL_URL, headers=headers, json=payload)

            if response.status_code != 200:
                print("Fal.ai API Hatası:", response.status_code, response.text)
                return JSONResponse(status_code=response.status_code, content=response.json())

            data = response.json()
            return {"status": "success", "result": data}

    except Exception as e:
        print("Backend Hatası:", traceback.format_exc())
        return JSONResponse(status_code=500, content={"error": str(e)})
