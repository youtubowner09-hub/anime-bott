# main.py
# 1-VERSIYA: BOTNI JONLANTIRISH

import os
from database import create_tables, SessionLocal, BotUser
from flask import Flask
from threading import Thread
from telegram.ext import Updater, CommandHandler, CallbackContext
from telegram import Update

# --- RENDER UCHUN WEB-SERVER QISMI ---
app = Flask('')
@app.route('/')
def home():
    return "Bot ishlamoqda"
def run():
    app.run(host="0.0.0.0", port=int(os.environ.get('PORT', 8080)))
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- ASOSIY FUNKSIYALAR ---
def start(update: Update, context: CallbackContext):
    """/start buyrug'i uchun javob"""
    user = update.message.from_user
    db_session = SessionLocal()
    
    # Foydalanuvchi bazada bor-yo'qligini tekshiramiz
    existing_user = db_session.query(BotUser).filter(BotUser.user_id == user.id).first()
    
    # Agar bazada yo'q bo'lsa, qo'shamiz
    if not existing_user:
        new_user = BotUser(
            user_id=user.id,
            first_name=user.first_name,
            username=user.username
        )
        db_session.add(new_user)
        db_session.commit()
        print(f"Yangi foydalanuvchi qo'shildi: {user.first_name} (ID: {user.id})")

    db_session.close()
    
    update.message.reply_text(f"Assalomu alaykum, {user.first_name}! Siz botga muvaffaqiyatli kirdingiz.")

# --- BOTNI ISHGA TUSHIRISH ---
def main():
    # Render uxlatib qo'ymasligi uchun web-serverni ishga tushiramiz
    keep_alive()

    # Ma'lumotlar bazasida jadvallarni yaratamiz
    create_tables()

    # Bot sozlamalari
    TOKEN = os.environ.get("BOT_TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Buyruqlarni qo'shamiz
    dp.add_handler(CommandHandler("start", start))

    # Botni ishga tushiramiz
    updater.start_polling(timeout=30)
    print("Bot ishga tushdi va foydalanuvchilarni kutmoqda...")
    updater.idle()

if __name__ == "__main__":
    main()
