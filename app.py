# ============================================================
# app.py - FastAPI backend cho website bán acc Free Fire
# Chạy: uvicorn app:app --reload
# ============================================================

import os
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# --- Import từ các file đã tách ---
from database import get_db, engine, Base, SessionLocal
from models import Account, Admin, RateLimitLog, AuditLog
from schemas import (
    AccountListItem, AccountDetail, MessageResponse, ErrorResponse,
    AccountCreate, LoginRequest, LoginResponse,
)
from auth import create_access_token, get_current_admin
from werkzeug.security import check_password_hash, generate_password_hash
from gdrive import upload_image_to_drive


# ============================================================
# Helper: Ghi audit log
# ============================================================
def write_audit_log(admin_user: str, action: str, target_id: int = None, detail: str = None, ip_address: str = None):
    db = SessionLocal()
    try:
        log = AuditLog(
            admin_user=admin_user,
            action=action,
            target_id=target_id,
            detail=detail,
            ip_address=ip_address,
        )
        db.add(log)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ============================================================
# BƯỚC 1: Khởi tạo FastAPI app
# ============================================================
app = FastAPI(
    title="FF Store API",
    description="API cho website bán acc Free Fire",
    version="1.0.0",
)


# ============================================================
# BƯỚC 2: Cấu hình CORS Middleware
# Đọc origins từ biến môi trường (fallback cho dev local)
# ============================================================
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://127.0.0.1:5500,http://localhost:5500"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ============================================================
# BƯỚC 3: Security Headers — bảo vệ XSS, clickjacking, MIME sniff
# ============================================================
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"          # Chống MIME sniff
    response.headers["X-Frame-Options"] = "DENY"                     # Chống clickjacking
    response.headers["X-XSS-Protection"] = "1; mode=block"           # Chống XSS (cũ)
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"  # Giới hạn referrer
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"  # Chặn truy cập thiết bị
    # Chỉ cho phép HTTPS sau 1 năm (HSTS)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


# ============================================================
# BƯỚC 4: Cấu hình Rate Limiting (100 request/phút/IP)
# ============================================================
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


# --- Xử lý khi vượt quá rate limit → trả HTTP 429 ---
@app.exception_handler(RateLimitExceeded)
def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": "Quá nhiều request, thử lại sau 1 phút"},
    )


# ============================================================
# BƯỚC 4: Tạo bảng + seed admin mặc định khi khởi động
# ============================================================
@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # Tạo admin mặc định từ biến môi trường (nếu chưa có)
        if db.query(Admin).count() == 0:
            admin_user = os.getenv("ADMIN_USERNAME", "admin")
            admin_pass = os.getenv("ADMIN_PASSWORD", "Admin@2024")
            db.add(Admin(
                username=admin_user,
                hashed_password=generate_password_hash(admin_pass),
            ))
            db.commit()

        # Seed 2 acc mẫu (nếu chưa có)
        if db.query(Account).count() == 0:
            db.add_all([
                Account(
                    title="ACC FREE FIRE CỰC VIP - ĐẲNG CẤP THÁNH",
                    price=500000,
                    rank_level="Kim Cương",
                    vip_items="Nhẫn Kim Cương VĨNH VIỄN, Emote Hiếm 100+, Skin Súng Max, Pet Max Level",
                    login_method="Facebook",
                    status="Đang bán",
                    image_url="https://placehold.co/600x400/ff4500/ffffff?text=FF+VIP+1",
                    description="Acc full nhẫn rank Kim Cương, sở hữu bộ sưu tập skin súng cực hiếm: AK Rồng Xanh, M1887 Vương Miện, Scar Titan. Đã mở khóa tất cả nhân vật. Pet Max Level skill hỗ trợ chiến đấu.",
                ),
                Account(
                    title="ACC FREE FIRE THÁNH CHIẾN - FULL NHẪN",
                    price=350000,
                    rank_level="Bạch Kim",
                    vip_items="Nhẫn Bạch Kim VĨNH VIỄN, 50+ Skin Súng, 30+ Nhân Vật, Elite Pass Mới Nhất",
                    login_method="Google",
                    status="Đang bán",
                    image_url="https://placehold.co/600x400/1e90ff/ffffff?text=FF+VIP+2",
                    description="Acc đạt rank Bạch Kim nhiều mùa liên tiếp. Đã mở khóa 30+ nhân vật bao gồm Chrono, Alok, Wukong. Sở hữu Elite Pass mùa mới nhất và nhiều skin súng hot.",
                ),
            ])
            db.commit()
    finally:
        db.close()


# ============================================================
# BƯỚC 5: Serve file tĩnh (HTML/JS/CSS) cho frontend
# Mount StaticFiles SAU tất cả API routes
# ============================================================
from fastapi.responses import FileResponse, RedirectResponse

STATIC_DIR = os.path.dirname(os.path.abspath(__file__))


# Root → redirect tới index.html
@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# Mount StaticFiles ở /static để serve JS/CSS/images
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Route explicit cho các file HTML (không dùng catch-all)
@app.get("/index.html", include_in_schema=False)
async def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/detail.html", include_in_schema=False)
async def serve_detail():
    return FileResponse(os.path.join(STATIC_DIR, "detail.html"))


@app.get("/admin.html", include_in_schema=False)
async def serve_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


@app.get("/main.js", include_in_schema=False)
async def serve_main_js():
    return FileResponse(os.path.join(STATIC_DIR, "main.js"))


# ============================================================
# GET /api/accounts
# Trả về danh sách acc đang bán (chỉ hiện field công khai)
# ============================================================
@app.get(
    "/api/accounts",
    response_model=list[AccountListItem],
    summary="Danh sách acc đang bán",
)
@limiter.limit("100/minute")
def list_accounts(request: Request, db: Session = Depends(get_db)):
    accounts = (
        db.query(Account)
        .filter(Account.status == "Đang bán")
        .all()
    )
    return accounts


# ============================================================
# GET /api/admin/accounts
# Trả về TẤT CẢ acc (cả đã bán) — dùng cho trang admin
# ============================================================
@app.get(
    "/api/admin/accounts",
    response_model=list[AccountDetail],
    summary="Tất cả acc (admin only)",
)
@limiter.limit("100/minute")
def admin_list_accounts(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    accounts = db.query(Account).order_by(Account.id.desc()).all()
    return accounts


# ============================================================
# GET /api/accounts/{id}
# Trả về chi tiết đầy đủ 1 acc theo ID
# ============================================================
@app.get(
    "/api/accounts/{account_id}",
    response_model=AccountDetail,
    summary="Chi tiết acc theo ID",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("100/minute")
def get_account(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.id == account_id).first()

    if account is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Không tìm thấy acc này"},
        )

    return account


# ============================================================
# POST /api/auth/login
# Đăng nhập admin, trả về JWT token
# Rate limit: 5 lần/phút (chống brute force)
# ============================================================
@app.post(
    "/api/auth/login",
    response_model=LoginResponse,
    summary="Đăng nhập admin",
    responses={401: {"model": ErrorResponse}},
)
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    # Tìm admin theo username
    admin = db.query(Admin).filter(Admin.username == body.username).first()

    # Kiểm tra username và password
    if admin is None or not check_password_hash(admin.hashed_password, body.password):
        raise HTTPException(
            status_code=401,
            detail={"error": "Sai tên đăng nhập hoặc mật khẩu"},
        )

    # Tạo JWT token
    access_token = create_access_token(data={"sub": admin.username})

    # Ghi audit log
    write_audit_log(
        admin_user=admin.username,
        action="LOGIN",
        detail="Đăng nhập thành công",
        ip_address=request.client.host,
    )

    return LoginResponse(access_token=access_token)


# ============================================================
# POST /api/admin/add
# Thêm acc mới (yêu cầu JWT)
# ============================================================
@app.post(
    "/api/admin/add",
    response_model=MessageResponse,
    summary="Thêm acc mới (admin only)",
    responses={401: {"model": ErrorResponse}},
)
@limiter.limit("100/minute")
def add_account(
    request: Request,
    body: AccountCreate,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    # Tạo acc mới, status tự động = 'Đang bán'
    new_account = Account(
        title=body.title,
        price=body.price,
        rank_level=body.rank_level,
        vip_items=body.vip_items,
        login_method=body.login_method,
        status="Đang bán",
        image_url=body.image_url,
        gallery_images=body.gallery_images,
        description=body.description,
    )

    db.add(new_account)
    db.commit()
    db.refresh(new_account)

    # Ghi audit log
    write_audit_log(
        admin_user=current_admin.username,
        action="ADD",
        target_id=new_account.id,
        detail=f"{body.title} - {body.price:,}đ",
        ip_address=request.client.host,
    )

    return MessageResponse(
        success=True,
        id=new_account.id,
        message="Đã thêm acc thành công",
    )


# ============================================================
# PUT /api/admin/sold/{id}
# Đánh dấu acc đã bán (yêu cầu JWT)
# ============================================================
@app.put(
    "/api/admin/sold/{account_id}",
    response_model=MessageResponse,
    summary="Đánh dấu acc đã bán (admin only)",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("100/minute")
def mark_as_sold(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    # Tìm acc theo ID
    account = db.query(Account).filter(Account.id == account_id).first()

    if account is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Không tìm thấy acc này"},
        )

    # Cập nhật status
    account.status = "Đã bán"
    db.commit()

    # Ghi audit log
    write_audit_log(
        admin_user=current_admin.username,
        action="MARK_SOLD",
        target_id=account.id,
        detail=f"{account.title}",
        ip_address=request.client.host,
    )

    return MessageResponse(
        success=True,
        message="Đã đánh dấu là Đã bán",
    )


# ============================================================
# DELETE /api/admin/delete/{id}
# Xóa acc (yêu cầu JWT)
# ============================================================
@app.delete(
    "/api/admin/delete/{account_id}",
    response_model=MessageResponse,
    summary="Xóa acc (admin only)",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("100/minute")
def delete_account(
    request: Request,
    account_id: int,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    # Tìm acc theo ID
    account = db.query(Account).filter(Account.id == account_id).first()

    if account is None:
        raise HTTPException(
            status_code=404,
            detail={"error": "Không tìm thấy acc này"},
        )

    # Xóa acc
    title = account.title
    db.delete(account)
    db.commit()

    # Ghi audit log
    write_audit_log(
        admin_user=current_admin.username,
        action="DELETE",
        target_id=account_id,
        detail=f"{title}",
        ip_address=request.client.host,
    )

    return MessageResponse(
        success=True,
        message="Đã xóa acc thành công",
    )


# ============================================================
# GET /api/admin/audit-log
# Xem lịch sử hành động admin (yêu cầu JWT)
# ============================================================
@app.get(
    "/api/admin/audit-log",
    summary="Lịch sử hành động admin (admin only)",
)
@limiter.limit("100/minute")
def get_audit_log(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    logs = db.query(AuditLog).order_by(AuditLog.timestamp.desc()).limit(100).all()
    return [
        {
            "id": log.id,
            "admin_user": log.admin_user,
            "action": log.action,
            "target_id": log.target_id,
            "detail": log.detail,
            "ip_address": log.ip_address,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
        }
        for log in logs
    ]


# ============================================================
# POST /api/admin/upload
# Upload ảnh lên Google Drive (yêu cầu JWT)
# ============================================================
@app.post(
    "/api/admin/upload",
    summary="Upload ảnh lên Google Drive (admin only)",
)
@limiter.limit("50/minute")
async def upload_image(
    request: Request,
    current_admin: Admin = Depends(get_current_admin),
):
    try:
        form = await request.form()
        image_data = form.get("image")
        filename = form.get("filename", "image.jpg")

        if not image_data:
            raise HTTPException(status_code=400, detail="Thiếu dữ liệu ảnh")

        # Log kích thước ảnh
        data_size = len(str(image_data))
        print(f"[UPLOAD] File: {filename}, Size: {data_size} chars")

        # Upload lên Google Drive
        url = upload_image_to_drive(str(image_data), str(filename))

        print(f"[UPLOAD] Success: {url}")
        return {"success": True, "url": url}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi upload: {str(e)}")

