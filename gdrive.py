# ============================================================
# gdrive.py - Upload ảnh lên Google Drive
# ============================================================

import os
import json
import base64
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io

# --- Folder ID trên Google Drive ---
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "1-tFo_uphd3lWL77_q3lVq5lEV9Wx2SVl")

# --- Credentials từ biến môi trường ---
GDRIVE_CREDENTIALS = os.getenv("GDRIVE_CREDENTIALS")


def get_drive_service():
    """Tạo Google Drive service từ credentials"""
    if not GDRIVE_CREDENTIALS:
        raise Exception("GDRIVE_CREDENTIALS chưa được cấu hình")

    creds_info = json.loads(GDRIVE_CREDENTIALS)
    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=creds)


def upload_image_to_drive(base64_data: str, filename: str) -> str:
    """
    Upload ảnh base64 lên Google Drive
    Trả về URL công khai của ảnh
    """
    # Tách header base64 nếu có (data:image/jpeg;base64,...)
    if "," in base64_data:
        base64_data = base64_data.split(",")[1]

    # Decode base64 thành bytes
    image_bytes = base64.b64decode(base64_data)

    # Tạo Drive service
    service = get_drive_service()

    # Metadata cho file
    file_metadata = {
        "name": filename,
        "parents": [GDRIVE_FOLDER_ID],
    }

    # Upload file
    media = MediaIoBaseUpload(
        io.BytesIO(image_bytes),
        mimetype="image/jpeg",
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id, webContentLink",
    ).execute()

    # Set quyền public (ai cũng xem được)
    service.permissions().create(
        fileId=file["id"],
        body={"role": "reader", "type": "anyone"},
    ).execute()

    # Lấy URL công khai
    file_id = file["id"]
    public_url = f"https://drive.google.com/thumbnail?id={file_id}&sz=w1000"

    return public_url
