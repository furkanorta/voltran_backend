Voltran AI Görüntü Düzenleyici - ARKA YÜZ (Backend API)
Bu depo, Fal AI'ın görüntü düzenleme modeline güvenli bir köprü (proxy) görevi gören arka yüz (Backend) servisini içerir. Bu API, Frontend'in direkt olarak Fal AI anahtarını kullanmasını engelleyerek güvenliği sağlar.

🔑 AI Servisi ve Endpoint
AI Motoru: fal.ai

Ana Endpoint: /api/generate (POST isteği bekler)

Canlı API URL'si: https://voltran-backend.onrender.com/api/generate

🛠️ Teknoloji Yığını
Çerçeve: [Python Flask/Node.js Express]

Barındırma: Render

⚙️ API Parametreleri ve İş Akışı
Parametre

Metot

Tür

Açıklama

image

POST (Dosya)

multipart/form-data

Düzenlenecek orijinal görsel dosyası.

prompt

POST (Alan)

String

Yapay zeka dönüşümü için metin talimatı.

İş Akışı:

API, Frontend'den gelen image ve prompt verilerini alır.

Ortam değişkenlerinden Fal AI Anahtarını okur.

Fal AI'a bir POST isteği gönderir.

Fal AI'dan dönen, dönüştürülmüş görselin geçici URL'sini alır.

Bu URL'yi, JSON formatında Frontend'e geri döndürür.

🔒 Güvenlik Notu
Fal AI API anahtarı, kod içinde değil, Render ortam değişkenleri (Environment Variables) içinde saklanmaktadır. Bu sayede anahtar, istemci tarafında (Frontend'de) asla ifşa edilmez.
