# ============================================================
# gdrive.py - Upload ảnh lên Google Drive (dùng requests)
# ============================================================

import os
import json
import base64
import requests
import google.auth.transport.requests
from google.oauth2 import service_account

# --- Folder ID trên Google Drive ---
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "1-tFo_uphd3lWL77_q3lVq5lEV9Wx2SVl")

# --- Credentials từ biến môi trường (base64 encoded) ---
GDRIVE_CREDENTIALS_B64 = os.getenv("GDRIVE_CREDENTIALS")


def get_access_token():
    """Lấy access token từ service account"""
    if not GDRIVE_CREDENTIALS_B64:
        raise Exception("GDRIVE_CREDENTIALS chưa được cấu hình")

    # Decode base64 → JSON string → dict
    creds_json = base64.b64decode(GDRIVE_CREDENTIALS_B64).decode("utf-8")
    creds_info = json.loads(creds_json)

    creds = service_account.Credentials.from_service_account_info(
        creds_info,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def upload_image_to_drive(file_bytes: bytes, filename: str, mimetype: str = "image/jpeg") -> str:
    """
    Upload ảnh bytes lên Google Drive
    Trả về URL công khai của ảnh
    """
    access_token = get_access_token()

    # Tên file an toàn
    safe_name = "".join(c for c in filename if c.isalnum() or c in ".-_ ").strip()
    if not safe_name:
        safe_name = "image.jpg"

    # Metadata
    metadata = {
        "name": safe_name,
        "parents": [GDRIVE_FOLDER_ID],
    }

    # Upload file
    url = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"

    # Dùng multipart form data
    files = {
        "metadata": ("metadata", json.dumps(metadata), "application/json; charset=UTF-8"),
        "file": (safe_name, file_bytes, mimetype),
    }

    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    response = requests.post(url, headers=headers, files=files)

    if response.status_code != 200:
        raise Exception(f"Google Drive API error: {response.status_code} - {response.text}")

    file_id = response.json()["id"]

    # Set quyền public
    perm_url = f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
    perm_data = {"role": "reader", "type": "anyone"}
    requests.post(
        perm_url,
        headers={**headers, "Content-Type": "application/json"},
        json=perm_data,
    )

    # URL công khai
    public_url = f"https://drive.google.com/uc?export=view&id={file_id}"

    return public_url
