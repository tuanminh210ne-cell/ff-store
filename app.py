# ============================================================
# app.py - FastAPI backend cho website bán acc Free Fire
# Chạy: uvicorn app:app --reload
# ============================================================

import os
import base64
from fastapi import FastAPI, Depends, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# --- Import từ các file đã tách ---
from database import get_db, engine, Base, SessionLocal
from models import Account, Admin, RateLimitLog, AuditLog, VisitorLog, AdminLoginLog, generate_slug
from schemas import (
    AccountListItem, AccountDetail, MessageResponse, ErrorResponse,
    AccountCreate, LoginRequest, LoginResponse,
)
from auth import create_access_token, get_current_admin
from werkzeug.security import check_password_hash, generate_password_hash
from gdrive import upload_image_to_drive, GAS_URL


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
# BƯỚC 3.5: Track visitors (không track admin API calls)
# ============================================================
TRACKED_PAGES = ["/home", "/danh-sach-acc", "/admin"]
ADMIN_PREFIXES = ["/api/admin", "/api/auth"]

@app.middleware("http")
async def track_visitors(request: Request, call_next):
    response = await call_next(request)

    # Chỉ track page visits, không track API calls
    path = request.url.path
    if path in TRACKED_PAGES:
        # Không track nếu là admin request
        is_admin = any(path.startswith(p) for p in ADMIN_PREFIXES)
        if not is_admin:
            try:
                db = SessionLocal()
                visitor = VisitorLog(
                    ip_address=request.client.host,
                    page=path,
                    user_agent=request.headers.get("user-agent", ""),
                    referrer=request.headers.get("referer", ""),
                )
                db.add(visitor)
                db.commit()
                db.close()
            except Exception:
                pass  # Không làm gián đoạn request nếu log lỗi

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
    # Reset database nếu cần (thêm env RESET_DB=true rồi deploy)
    if os.getenv("RESET_DB") == "true":
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Tạo slug cho acc cũ chưa có
    db = SessionLocal()
    try:
        accounts_without_slug = db.query(Account).filter(Account.slug == None).all()
        for acc in accounts_without_slug:
            slug = generate_slug()
            while db.query(Account).filter(Account.slug == slug).first():
                slug = generate_slug()
            acc.slug = slug
        if accounts_without_slug:
            db.commit()
    finally:
        db.close()

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
                    rank_level="80",
                    vip_items="Emote Hiếm 100+, Skin Súng Max, Pet Max Level, Tất Cả Nhân Vật",
                    login_method="Facebook",
                    status="Đang bán",
                    image_url="https://placehold.co/600x400/ff4500/ffffff?text=FF+VIP+1",
                    description="Acc rank Kim Cương, sở hữu bộ sưu tập skin súng cực hiếm: AK Rồng Xanh, M1887 Vương Miện, Scar Titan. Đã mở khóa tất cả nhân vật. Pet Max Level skill hỗ trợ chiến đấu.",
                ),
                Account(
                    title="ACC FREE FIRE THÁNH CHIẾN - LEVEL CAO",
                    price=350000,
                    rank_level="65",
                    vip_items="50+ Skin Súng, 30+ Nhân Vật, Elite Pass Mới Nhất",
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


# Root → redirect tới /home
@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/home")


# Mount StaticFiles ở /static để serve JS/CSS/images
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# Route mới — URL sạch
@app.get("/home", include_in_schema=False)
async def serve_home():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/danh-sach-acc", include_in_schema=False)
async def serve_accounts():
    return FileResponse(os.path.join(STATIC_DIR, "danh-sach-acc.html"))


@app.get("/admin", include_in_schema=False)
async def serve_admin():
    return FileResponse(os.path.join(STATIC_DIR, "admin.html"))


@app.get("/main.js", include_in_schema=False)
async def serve_main_js():
    return FileResponse(os.path.join(STATIC_DIR, "main.js"))


# Route cũ — redirect sang URL mới
@app.get("/index.html", include_in_schema=False)
async def redirect_index():
    return RedirectResponse(url="/home")


# Detail page theo slug: /acc/{slug}
@app.get("/acc/{slug}", include_in_schema=False)
async def serve_detail_by_slug(slug: str, db: Session = Depends(get_db)):
    account = db.query(Account).filter(Account.slug == slug).first()
    if account:
        return FileResponse(os.path.join(STATIC_DIR, "detail.html"))
    raise HTTPException(status_code=404, detail="Not found")


@app.get("/admin.html", include_in_schema=False)
async def redirect_admin():
    return RedirectResponse(url="/admin")


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
    # Trả về TẤT CẢ acc (cả đã bán) để web uy tín hơn
    accounts = db.query(Account).order_by(Account.id.desc()).all()
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
# GET /api/acc/{slug}
# Trả về chi tiết acc theo slug (URL ngắn)
# ============================================================
@app.get(
    "/api/acc/{slug}",
    response_model=AccountDetail,
    summary="Chi tiết acc theo slug",
    responses={404: {"model": ErrorResponse}},
)
@limiter.limit("100/minute")
def get_account_by_slug(
    request: Request,
    slug: str,
    db: Session = Depends(get_db),
):
    account = db.query(Account).filter(Account.slug == slug).first()

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

    # Ghi log IP admin đăng nhập
    try:
        login_log = AdminLoginLog(
            username=admin.username,
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent", ""),
        )
        db.add(login_log)
        db.commit()
    except Exception:
        pass

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
    # Tạo slug unique
    slug = generate_slug()
    while db.query(Account).filter(Account.slug == slug).first():
        slug = generate_slug()

    # Tạo acc mới, status tự động = 'Đang bán'
    new_account = Account(
        slug=slug,
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
# GET /api/admin/analytics
# Thống kê người truy cập (admin only)
# ============================================================
@app.get(
    "/api/admin/analytics",
    summary="Thống kê truy cập (admin only)",
)
@limiter.limit("100/minute")
def get_analytics(
    request: Request,
    db: Session = Depends(get_db),
    current_admin: Admin = Depends(get_current_admin),
):
    from datetime import datetime, timedelta
    from sqlalchemy import func

    now = datetime.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    # Tổng visitors
    total_visitors = db.query(func.count(VisitorLog.id)).scalar() or 0

    # Visitors hôm nay
    today_visitors = db.query(func.count(VisitorLog.id)).filter(
        VisitorLog.timestamp >= today
    ).scalar() or 0

    # Visitors 7 ngày
    week_visitors = db.query(func.count(VisitorLog.id)).filter(
        VisitorLog.timestamp >= week_ago
    ).scalar() or 0

    # Visitors 30 ngày
    month_visitors = db.query(func.count(VisitorLog.id)).filter(
        VisitorLog.timestamp >= month_ago
    ).scalar() or 0

    # Top pages
    top_pages = db.query(
        VisitorLog.page,
        func.count(VisitorLog.id).label("count")
    ).group_by(VisitorLog.page).order_by(func.count(VisitorLog.id).desc()).limit(5).all()

    # Top IPs
    top_ips = db.query(
        VisitorLog.ip_address,
        func.count(VisitorLog.id).label("count")
    ).group_by(VisitorLog.ip_address).order_by(func.count(VisitorLog.id).desc()).limit(10).all()

    # Admin login logs gần đây
    admin_logins = db.query(AdminLoginLog).order_by(
        AdminLoginLog.timestamp.desc()
    ).limit(20).all()

    # Visitors gần đây
    recent_visitors = db.query(VisitorLog).order_by(
        VisitorLog.timestamp.desc()
    ).limit(50).all()

    return {
        "summary": {
            "total": total_visitors,
            "today": today_visitors,
            "week": week_visitors,
            "month": month_visitors,
        },
        "top_pages": [{"page": p[0], "count": p[1]} for p in top_pages],
        "top_ips": [{"ip": ip[0], "count": ip[1]} for ip in top_ips],
        "admin_logins": [
            {
                "username": log.username,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in admin_logins
        ],
        "recent_visitors": [
            {
                "ip_address": v.ip_address,
                "page": v.page,
                "user_agent": v.user_agent,
                "timestamp": v.timestamp.isoformat() if v.timestamp else None,
            }
            for v in recent_visitors
        ],
    }


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
        file = form.get("file")

        if not file:
            raise HTTPException(status_code=400, detail="Thiếu file ảnh")

        filename = file.filename or "image.jpg"
        content_type = file.content_type or "image/jpeg"
        content = await file.read()

        # Log kích thước ảnh
        print(f"[UPLOAD] File: {filename}, Size: {len(content)} bytes, Type: {content_type}")

        # Upload bytes trực tiếp lên Google Drive
        url = upload_image_to_drive(content, filename, content_type)

        print(f"[UPLOAD] Success: {url}")
        return {"success": True, "url": url}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[UPLOAD] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Lỗi upload: {str(e)}")

