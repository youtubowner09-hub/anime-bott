# main.py
from database import create_tables
import time

if __name__ == "__main__":
    print("Dastur ishga tushdi...")
    create_tables()
    print("Jadvallar yaratildi. Dastur 60 soniyadan so'ng o'z ishini yakunlaydi.")
    time.sleep(60) # Loglarni ko'rish uchun biroz kutamiz
