# ============================================================
# database.py - Cấu hình kết nối SQLAlchemy với ff_store.db
# ============================================================

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# --- Đường dẫn database (absolute path để chạy đúng trên mọi server) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'ff_store.db')}"

# --- Tạo engine kết nối ---
# check_same_thread=False: cho phép dùng SQLite với nhiều thread (cần cho FastAPI)
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

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
