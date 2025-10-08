from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import os
import tempfile
import shutil
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# .env dosyasını yükle
load_dotenv()

FAL_API_KEY = os.getenv("FAL_API_KEY")
CLOUD_NAME = os.getenv("CLOUD_NAME")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY")
CLOUD_API_SECRET = os.getenv("CLOUD_API_SECRET")

FAL_URL = "https://fal.run/fal-ai/flux/dev/image-to-image"

# Cloudinary config
cloudinary.config(
    cloud_name=CLOUD_NAME,
    api_key=CLOUD_API_KEY,
    api_secret=CLOUD_API_SECRET
)

# FastAPI instance
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Prod'da sadece frontend domain ekle
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# Upload fonksiyonu
def upload_to_cloudinary(local_file_path: str) -> str:
    res = cloudinary.uploader.upload(local_file_path)
    return res['secure_url']


@app.post("/api/jobs")
async def create_job(prompt: str = Form(...), file: UploadFile = File(...)):
    try:
        # Geçici dosya oluştur
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_file_path = tmp.name

        # Cloudinary'ye upload et
        public_url = upload_to_cloudinary(tmp_file_path)

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
                "image_url": public_url
            }
        }

        async with httpx.AsyncClient(timeout=180) as client:
            response = await client.post(FAL_URL, headers=headers, json=payload)

        if response.status_code != 200:
            try:
                content = response.json()
            except:
                content = {"error": "Fal.ai'den beklenmedik yanıt.", "details": response.text}
            return JSONResponse(status_code=502, content=content)

        data = response.json()
        return {"status": "success", "result": data}

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": "Sunucu hatası oluştu.", "details": str(e)},
        )
