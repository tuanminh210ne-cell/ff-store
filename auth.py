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
# Cấu hình JWT — đọc từ biến môi trường (fallback cho dev local)
# ============================================================
SECRET_KEY = os.getenv("SECRET_KEY", "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6")
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
