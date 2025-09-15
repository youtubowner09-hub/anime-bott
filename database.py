# database.py
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

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
    user_id = Column(Integer, primary_key=True, index=True, autoincrement=False)
    first_name = Column(String)
    username = Column(String, nullable=True)

def create_tables():
    print("Ma'lumotlar bazasida jadvallarni yaratishga harakat qilinmoqda...")
    try:
        Base.metadata.create_all(bind=engine)
        print("✅ Jadvallar muvaffaqiyatli yaratildi.")
    except Exception as e:
        print(f"❌ Ma'lumotlar bazasiga ulanishda xatolik: {e}")
