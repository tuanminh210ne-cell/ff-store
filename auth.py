# ============================================================
# auth.py - Hệ thống JWT Authentication cho FF Store
# ============================================================

import os
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from database import get_db
from models import Admin
from werkzeug.security import check_password_hash


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


# ============================================================
# Cấu hình JWT — đọc từ biến môi trường (bắt buộc)
# ============================================================
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY chưa được cấu hình trong .env — chạy: python3 -c \"import secrets; print(secrets.token_hex(32))\"")
ALGORITHM = "HS256"
TOKEN_EXPIRE = 30  # Phút


# ============================================================
# OAuth2 scheme: tự động lấy token từ header Authorization
# ============================================================
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# ============================================================
# Tạo JWT token
# ============================================================
def create_access_token(data: dict) -> str:
    # Copy data để không thay đổi dict gốc
    to_encode = data.copy()

    # Tính thời gian hết hạn = hiện tại + 30 phút
    expire = datetime.utcnow() + timedelta(minutes=TOKEN_EXPIRE)
    to_encode.update({"exp": expire})

    # Encode thành JWT string
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ============================================================
# Giải mã và xác thực JWT token
# ============================================================
def verify_token(token: str) -> dict:
    try:
        # Decode token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        # Token sai hoặc đã hết hạn → trả 401
        raise HTTPException(
            status_code=401,
            detail={"error": "Token không hợp lệ hoặc đã hết hạn"},
        )


# ============================================================
# Dependency: lấy admin hiện tại từ token
# Dùng trong các route cần xác thực: Depends(get_current_admin)
# ============================================================
def get_current_admin(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Admin:
    # Giải mã token để lấy username
    payload = verify_token(token)
    username = payload.get("sub")

    if username is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Token không hợp lệ"},
        )

    # Tìm admin trong database
    admin = db.query(Admin).filter(Admin.username == username).first()

    if admin is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Admin không tồn tại"},
        )

    return admin
