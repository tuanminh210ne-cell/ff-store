# ============================================================
# gdrive.py - Upload ảnh lên Google Drive qua Google Apps Script
# ============================================================

import os
import json
import base64
import requests


# ============================================================
# Load .env file (không cần python-dotenv)
# ============================================================
def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip()
            if key and key not in os.environ:
                os.environ[key] = value

_load_env()

# --- Google Apps Script Web App URL (bắt buộc) ---
GAS_URL = os.getenv("GAS_URL")
if not GAS_URL:
    raise RuntimeError("GAS_URL chưa được cấu hình trong .env")


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
