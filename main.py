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
                print("Fal.ai API Hatası:", response.status_code, response.text)
                return JSONResponse(status_code=response.status_code, content=response.json())

            data = response.json()
            return {"status": "success", "result": data}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
