# database.py
import os
# QO'SHILGAN IMPORT: Katta sonlar uchun
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, BigInteger
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- Jadvallarni Python klasslari sifatida tavsiflaymiz ---

class Anime(Base):
    __tablename__ = "animes"
    id = Column(Integer, primary_key=True, index=True)
    search_code = Column(String, unique=True, index=True, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text)
    main_photo_id = Column(String)
    episodes = relationship("Episode", back_populates="anime")

class Episode(Base):
    __tablename__ = "episodes"
    id = Column(Integer, primary_key=True, index=True)
    anime_id = Column(Integer, ForeignKey("animes.id"))
    episode_number = Column(Integer, nullable=False)
    video_file_id = Column(String, nullable=False)
    anime = relationship("Anime", back_populates="episodes")

class BotUser(Base):
    __tablename__ = "bot_users"
    # O'ZGARTIRILGAN QATOR: Katta ID raqamlar uchun Integer -> BigInteger
    user_id = Column(BigInteger, primary_key=True, index=True, autoincrement=False)
    first_name = Column(String)
    username = Column(String, nullable=True)

class Settings(Base):
    __tablename__ = "settings"
    key = Column(String, primary_key=True)
    value = Column(Text)


# --- Jadvallarni yaratuvchi funksiya ---
def create_tables():
    """Barcha jadvallarni ma'lumotlar bazasida yaratadi"""
    print("Ma'lumotlar bazasida jadvallarni yaratishga harakat qilinmoqda...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Jadvallar muvaffaqiyatli yaratildi.")
    except Exception as e:
        print(f"❌ Ma'lumotlar bazasiga ulanishda xatolik: {e}")
