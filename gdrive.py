# ============================================================
# gdrive.py - Upload ảnh lên Google Drive
# ============================================================

import os
import json
import io
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

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


def upload_image_to_drive(file_bytes: bytes, filename: str, mimetype: str = "image/jpeg") -> str:
    """
    Upload ảnh bytes lên Google Drive
    Trả về URL công khai của ảnh
    """
    # Tạo Drive service
    service = get_drive_service()

    # Metadata cho file — chỉ dùng tên_ascii để tránh lỗi JSON
    safe_name = "".join(c for c in filename if c.isalnum() or c in ".-_ ").strip()
    if not safe_name:
        safe_name = "image.jpg"

    file_metadata = {
        "name": safe_name,
        "parents": [GDRIVE_FOLDER_ID],
    }

    # Upload file dạng binary
    media = MediaIoBaseUpload(
        io.BytesIO(file_bytes),
        mimetype=mimetype,
        resumable=True,
    )

    file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields="id",
    ).execute()

    file_id = file["id"]

    # Set quyền public
    service.permissions().create(
        fileId=file_id,
        body={"role": "reader", "type": "anyone"},
    ).execute()

    # URL công khai
    public_url = f"https://drive.google.com/uc?export=view&id={file_id}"

    return public_url
