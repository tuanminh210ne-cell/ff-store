# ============================================================
# models.py - Định nghĩa 3 bảng trong database ff_store.db
# Chỉ chứa ORM models, không chứa Pydantic schemas
# ============================================================

import random
import string
from datetime import datetime

# --- SQLAlchemy ---
from sqlalchemy import Column, Integer, Text, DateTime

# --- Import Base từ database.py (dùng chung) ---
from database import Base, engine, SessionLocal

# --- werkzeug: hash password ---
from werkzeug.security import generate_password_hash


def generate_slug(length=8):
    """Tạo slug random (VD: fbdhjsfghjs)"""
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


# ============================================================
# Định nghĩa 3 bảng trong database
# ============================================================

# --- Bảng accounts: lưu thông tin acc Free Fire ---
class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(Text, unique=True)                # URL ngắn (random, không đoán được)
    title = Column(Text, nullable=False)           # Tên acc
    price = Column(Integer, nullable=False)         # Giá tiền (VNĐ)
    rank_level = Column(Text)                       # Level (số)
    vip_items = Column(Text)                        # Danh sách vật phẩm VIP
    login_method = Column(Text)                     # Cách đăng nhập (Facebook/Google)
    status = Column(Text, default="Đang bán")       # Trạng thái mặc định
    image_url = Column(Text)                        # Ảnh bìa (hiển thị ở danh sách)
    gallery_images = Column(Text)                   # Album ảnh (JSON array, tối đa 100)
    description = Column(Text)                      # Mô tả chi tiết
    created_at = Column(DateTime, default=datetime.now)  # Thời gian tạo


# --- Bảng admins: lưu tài khoản quản trị viên ---
class Admin(Base):
    __tablename__ = "admins"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(Text, unique=True, nullable=False)  # Tên đăng nhập
    hashed_password = Column(Text, nullable=False)         # Mật khẩu đã hash


# --- Bảng rate_limit_log: ghi log chống spam ---
class RateLimitLog(Base):
    __tablename__ = "rate_limit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ip_address = Column(Text)       # Địa chỉ IP
    endpoint = Column(Text)         # Đường dẫn API bị gọi
    timestamp = Column(DateTime, default=datetime.now)  # Thời gian gọi


# --- Bảng audit_log: ghi log hành động admin ---
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    admin_user = Column(Text)           # Tên admin thực hiện
    action = Column(Text)               # Hành động (LOGIN, ADD, DELETE, MARK_SOLD)
    target_id = Column(Integer)         # ID acc bị ảnh hưởng (nếu có)
    detail = Column(Text)               # Chi tiết (tên acc, giá, etc.)
    ip_address = Column(Text)           # IP của admin
    timestamp = Column(DateTime, default=datetime.now)  # Thời gian


# ============================================================
# Tạo bảng và chèn dữ liệu mẫu
# ============================================================
def init_db():
    # Tạo tất cả bảng trong database
    Base.metadata.create_all(engine)
    print("  [OK] Da tao cac bang: accounts, admins, rate_limit_log")

    # Mở session để thao tác dữ liệu
    session = SessionLocal()

    # --- Kiểm tra xem đã có dữ liệu chưa (tránh chạy lại bị trùng) ---
    if session.query(Account).count() == 0:

        # ---- 2 acc Free Fire cực VIP ----
        acc1 = Account(
            title="ACC FREE FIRE CỰC VIP - ĐẲNG CẤP THÁNH",
            price=500000,
            rank_level="Lv 80",
            vip_items="Nhẫn Kim Cương VĨNH VIỄN, Emote Hiếm 100+, Skin Súng Max, Pet Max Level",
            login_method="Facebook",
            status="Đang bán",
            image_url="https://placehold.co/600x400/ff4500/ffffff?text=FF+VIP+1",
            description="Acc full nhẫn rank Kim Cương, sở hữu bộ sưu tập skin súng cực hiếm: AK Rồng Xanh, M1887 Vương Miện, Scar Titan. Đã mở khóa tất cả nhân vật. Pet Max Level skill hỗ trợ chiến đấu. Đây là acc cày từ Season 1, rất uy tín.",
        )

        acc2 = Account(
            title="ACC FREE FIRE THÁNH CHIẾN - FULL NHẪN",
            price=350000,
            rank_level="Lv 65",
            vip_items="Nhẫn Bạch Kim VĨNH VIỄN, 50+ Skin Súng, 30+ Nhân Vật, Elite Pass Mới Nhất",
            login_method="Google",
            status="Đang bán",
            image_url="https://placehold.co/600x400/1e90ff/ffffff?text=FF+VIP+2",
            description="Acc đạt rank Bạch Kim nhiều mùa liên tiếp. Đã mở khóa 30+ nhân vật bao gồm Chrono, Alok, Wukong. Sở hữu Elite Pass mùa mới nhất và nhiều skin súng hot. Login bằng Google, dễ dàng đổi thông tin sau khi mua.",
        )

        session.add_all([acc1, acc2])
        print("  [OK] Da them 2 acc Free Fire VIP mau")

    # --- Thêm admin mặc định (nếu chưa có) ---
    if session.query(Admin).count() == 0:
        default_admin = Admin(
            username="admin",
            hashed_password=generate_password_hash("Admin@2024"),
        )
        session.add(default_admin)
        print("  [OK] Da them admin mac dinh: admin / Admin@2024")

    # Lưu thay đổi vào database
    session.commit()

    # --- In ra kiểm tra ---
    print()
    print("=" * 55)
    print("  DATABASE ff_store.db DA DUOC TAO THANH CONG!")
    print("=" * 55)
    print()

    # Liệt kê acc trong database
    accounts = session.query(Account).all()
    print(f"  So luong acc: {len(accounts)}")
    for acc in accounts:
        print(f"    [{acc.id}] {acc.title} - {acc.price:,} VND - {acc.status}")

    # Liệt kê admin
    admins = session.query(Admin).all()
    print(f"\n  So luong admin: {len(admins)}")
    for adm in admins:
        print(f"    [{adm.id}] {adm.username}")

    print()
    print("  File ff_store.db da san sang. Ban co the su dung ngay!")

    session.close()


# ============================================================
# CHẠY FILE: python3 models.py
# ============================================================
if __name__ == "__main__":
    init_db()
