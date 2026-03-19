from fastapi import APIRouter, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from services.watermark_svc import apply_watermark, extract_watermark
import base64
import io

router = APIRouter()

@router.post("/watermark")
async def trust_process(image: UploadFile = File(...), username: str = Form(...)):
    try:
        file_bytes = await image.read()
        b64_result = apply_watermark(file_bytes, username)

        # Convertit le base64 en bytes et retourne un vrai fichier
        image_bytes = base64.b64decode(b64_result)
        return StreamingResponse(
            io.BytesIO(image_bytes),
            media_type="image/png",
            headers={"Content-Disposition": f"attachment; filename=watermarked_{username}.png"}
        )
    except Exception as e:
        return {"error": str(e)}


@router.post("/extract")
async def extract(
    original:    UploadFile = File(...),
    watermarked: UploadFile = File(...)
):
    try:
        original_bytes    = await original.read()
        watermarked_bytes = await watermarked.read()
        message = extract_watermark(original_bytes, watermarked_bytes)
        return {"message": message}
    except Exception as e:
        return {"error": str(e)}