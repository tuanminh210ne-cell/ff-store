# ============================================================
# gdrive.py - Upload ảnh lên Google Drive qua Google Apps Script
# ============================================================

import os
import json
import base64
import requests

# --- Google Apps Script Web App URL ---
GAS_URL = os.getenv(
    "GAS_URL",
    "https://script.google.com/macros/s/AKfycbwgOzSIHZa37ZJIBD5EhLB4inns4gY4XM6pgeyfSag0SNwQfTKXBOA7x6g9WI5PXuA3/exec"
)


def upload_image_to_drive(file_bytes: bytes, filename: str, mimetype: str = "image/jpeg") -> str:
    """
    Upload ảnh bytes lên Google Drive qua Google Apps Script
    Trả về URL công khai của ảnh
    """
    # Tên file an toàn
    safe_name = "".join(c for c in filename if c.isalnum() or c in ".-_ ").strip()
    if not safe_name:
        safe_name = "image.jpg"

    # Chuyển bytes sang base64
    b64_data = base64.b64encode(file_bytes).decode("utf-8")

    # Gửi tới Google Apps Script
    payload = {
        "image": b64_data,
        "filename": safe_name,
        "mimeType": mimetype,
    }

    response = requests.post(
        GAS_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )

    if response.status_code != 200:
        raise Exception(f"Google Apps Script error: {response.status_code}")

    result = response.json()

    if not result.get("success"):
        raise Exception(result.get("error", "Upload thất bại"))

    return result["url"]
