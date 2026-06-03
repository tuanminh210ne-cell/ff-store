# ============================================================
# database.py - Cấu hình kết nối database
# Hỗ trợ: SQLite (local dev) và PostgreSQL (production trên Render)
# ============================================================

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Đọc DATABASE_URL từ biến môi trường ---
# Nếu có DATABASE_URL (trên Render) → dùng PostgreSQL
# Nếu không có (local) → dùng SQLite
DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL:
    # PostgreSQL trên Render
    # Fix: Render dùng "postgres://" nhưng SQLAlchemy cần "postgresql://"
    if DATABASE_URL.startswith("postgres://"):
        DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
    engine = create_engine(DATABASE_URL)
else:
    # SQLite cho dev local
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    SQLITE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'ff_store.db')}"
    engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})

# --- Tạo session factory ---
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# --- Base class để khai báo model ---
Base = declarative_base()


# --- Dependency: tạo session cho mỗi request, tự động đóng sau khi xong ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
