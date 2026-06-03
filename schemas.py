# ============================================================
# schemas.py - Pydantic schemas để validate dữ liệu đầu vào/ra
# ============================================================

from datetime import datetime
from pydantic import BaseModel, validator
from typing import Optional
import re


# ============================================================
# Schema cho GET /api/accounts (danh sách rút gọn)
# Chỉ hiện các field công khai, không lộ description hay login_method
# ============================================================
class AccountListItem(BaseModel):
    id: int
    title: str
    price: int
    rank_level: Optional[str] = None
    image_url: Optional[str] = None

    class Config:
        orm_mode = True  # Cho phép chuyển từ SQLAlchemy object


# ============================================================
# Schema cho GET /api/accounts/{id} (chi tiết đầy đủ)
# ============================================================
class AccountDetail(BaseModel):
    id: int
    title: str
    price: int
    rank_level: Optional[str] = None
    vip_items: Optional[str] = None
    login_method: Optional[str] = None
    status: str
    image_url: Optional[str] = None
    gallery_images: Optional[str] = None  # JSON array string
    description: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True


# ============================================================
# Schema cho POST /api/admin/add (dữ liệu đầu vào khi thêm acc)
# ============================================================
class AccountCreate(BaseModel):
    title: str
    price: int
    rank_level: Optional[str] = None
    vip_items: Optional[str] = None
    login_method: Optional[str] = None
    image_url: Optional[str] = None
    gallery_images: Optional[str] = None  # JSON array string
    description: Optional[str] = None

    @validator("title")
    def title_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Tên acc không được để trống")
        return v.strip()

    @validator("price")
    def price_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Giá phải lớn hơn 0")
        return v

    @validator("image_url")
    def image_url_valid(cls, v):
        if v is not None and v.strip():
            v = v.strip()
            # Cho phép URL http/https hoặc base64 data URL
            if v.startswith("data:image/"):
                return v
            pattern = r"^https?://[^\s]+$"
            if not re.match(pattern, v):
                raise ValueError("image_url phải là URL hợp lệ hoặc ảnh base64")
            return v
        return v


# ============================================================
# Schema cho response khi thêm/sửa acc thành công
# ============================================================
class MessageResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    id: Optional[int] = None


# ============================================================
# Schema cho lỗi
# ============================================================
class ErrorResponse(BaseModel):
    error: str


# ============================================================
# Schema cho POST /api/auth/login
# ============================================================
class LoginRequest(BaseModel):
    username: str
    password: str

    @validator("username")
    def username_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Username không được để trống")
        return v.strip()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 1800
