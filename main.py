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
import logging
import traceback
import contextlib # Yeni import

# Logging ayarları
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env dosyasını yükle
load_dotenv()

FAL_API_KEY = os.getenv("FAL_API_KEY")
CLOUD_NAME = os.getenv("CLOUD_NAME")
CLOUD_API_KEY = os.getenv("CLOUD_API_KEY")
CLOUD_API_SECRET = os.getenv("CLOUD_API_SECRET")

# GÜNCELLENDİ: Sınav gereksinimi doğrultusunda 'nano-banana' (resmi Fal.ai yolu) modeline geçiş yapıldı.
# nano-banana'nın resmi API yolu şudur:
FAL_URL = "https://fal.run/gemini-2-5-flash-image-preview" 

# Cloudinary config
try:
    cloudinary.config(
        cloud_name=CLOUD_NAME,
        api_key=CLOUD_API_KEY,
        api_secret=CLOUD_API_SECRET
    )
    logger.info("Cloudinary konfigürasyonu başarılı.")
except Exception as e:
    logger.error(f"Cloudinary konfigürasyon hatası: {e}")

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

# Basit test route
@app.get("/")
def home():
    return {"message": "Voltran Backend API çalışıyor 🚀"}

# Upload fonksiyonu
def upload_to_cloudinary(local_file_path: str) -> str:
    # Upload işlemi sırasında 300 saniye (5 dakika) timeout süresi tanımlandı
    res = cloudinary.uploader.upload(local_file_path, timeout=300) 
    logger.info(f"Cloudinary'ye yükleme başarılı. URL: {res.get('secure_url')}")
    return res['secure_url']


# Endpoint adını değiştirdik: /api/generate
@app.post("/api/generate") 
async def create_job(prompt: str = Form(...), image: UploadFile = File(...)):
    tmp_file_path = None
    logger.info(f"İstek alındı. Prompt: {prompt[:50]}..., Dosya: {image.filename}") 
    
    try:
        # Geçici dosya oluşturma ve içeriği kopyalama (Daha güvenli hale getirildi)
        suffix = os.path.splitext(image.filename)[1]
        
        with contextlib.ExitStack() as stack:
            # Geçici dosyayı oluştur
            tmp = stack.enter_context(tempfile.NamedTemporaryFile(delete=False, suffix=suffix))
            tmp_file_path = tmp.name
            
            # Yüklenen dosyayı geçici dosyaya kopyala
            shutil.copyfileobj(image.file, tmp)
            
        # UploadedFile'ı kapat
        await image.close()

        # Cloudinary'ye upload et
        if not all([CLOUD_NAME, CLOUD_API_KEY, CLOUD_API_SECRET]):
            logger.error("Cloudinary ortam değişkenleri eksik.")
            return JSONResponse(status_code=500, content={"error": "Cloudinary ortam değişkenleri eksik."})

        public_url = upload_to_cloudinary(tmp_file_path)

        if not FAL_API_KEY:
            logger.error("FAL_API_KEY ortam değişkeni ayarlanmamış.")
            return JSONResponse(
                status_code=500,
                content={"error": "FAL_API_KEY ortam değişkeni ayarlanmamış."},
            )

        headers = {
            "Authorization": f"Key {FAL_API_KEY}",
            "Content-Type": "application/json"
        }

        # Payload yapısı aynı kalıyor. nano-banana da prompt ve image_url bekler.
        # İpucu: nano-banana ile daha iyi sonuç almak için prompt'a orijinal resmi tarif eden
        # detaylar eklemek iyi olabilir.
        payload = {
            "prompt": prompt,
            "image_url": public_url
        }
        
        logger.info("Fal.ai'ye istek gönderiliyor...")

        # Timeout süresi 300 saniyeye yükseltildi
        async with httpx.AsyncClient(timeout=300) as client:
            response = await client.post(FAL_URL, headers=headers, json=payload)

        logger.info(f"Fal.ai'den yanıt alındı. Status: {response.status_code}")
        
        if response.status_code != 200:
            try:
                content = response.json()
            except Exception as parse_e:
                logger.error(f"Fal.ai yanıtı JSON'a dönüştürülemedi: {parse_e}")
                content = {"error": "Fal.ai'den beklenmedik yanıt.", "details": response.text}
            
            # Fal.ai hatalarını 502 Bad Gateway olarak döndür
            return JSONResponse(status_code=502, content=content)

        data = response.json()
        return {"status": "success", "result": data}

    except httpx.TimeoutException:
        logger.error("Fal.ai isteği zaman aşımına uğradı (300 saniye).")
        return JSONResponse(
            status_code=504, # Gateway Timeout daha uygun
            content={"error": "Görsel oluşturma isteği zaman aşımına uğradı. Lütfen daha sonra tekrar deneyin."},
        )

    except Exception as e:
        error_details = traceback.format_exc()
        logger.error(f"İşlem sırasında beklenmedik hata: {str(e)}\n{error_details}")
        return JSONResponse(
            status_code=500,
            content={"error": "Sunucu hatası oluştu.", "details": str(e)},
        )
        
    finally:
        # **KRİTİK:** Geçici dosyayı sil
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.remove(tmp_file_path)
                logger.info(f"Geçici dosya başarıyla silindi: {tmp_file_path}")
            except Exception as e:
                logger.error(f"Geçici dosya silinirken hata: {e}")
