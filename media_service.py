from fastapi import APIRouter, UploadFile, File, HTTPException
import cloudinary.uploader
import os

cloudinary.config(
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "tu_cloud_name"),
  api_key = os.getenv("CLOUDINARY_API_KEY", "tu_api_key"),
  api_secret = os.getenv("CLOUDINARY_API_SECRET", "tu_api_secret"),
  secure = True
)

media_router = APIRouter(prefix="/admin/media", tags=["Medios en la Nube"])

@media_router.post("/upload")
async def upload_media_file(file: UploadFile = File(...)):
    try:
        filename = file.filename.lower()
        resource_type = "video" if filename.endswith(('.mp4', '.mov', '.mp3', '.wav')) else "raw"
        contents = await file.read()

        upload_result = cloudinary.uploader.upload(
            contents, resource_type=resource_type, folder="autodidacta_plataforma"
        )
        return {"status": "success", "url": upload_result.get("secure_url")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))