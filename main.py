# main.py
# 4-VERSIYA: ADMIN PANELIGA KIRISH

import os
from database import create_tables, SessionLocal, BotUser, Settings, Anime, Episode
from flask import Flask
from threading import Thread
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler, ConversationHandler, MessageHandler, Filters
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup

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

# --- SOZLAMALAR ---
TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID"))
SECRET_CODE = os.environ.get("SECRET_CODE")
# Render'dan o'qiladigan boshqa o'zgaruvchilar
MAIN_PHOTO_ID = os.environ.get("MAIN_PHOTO_ID")
AD_USER = os.environ.get("AD_USER")
CATALOGUE_LINK = os.environ.get("CATALOGUE_LINK")
DEFAULT_MANDATORY_CHANNEL = os.environ.get("DEFAULT_MANDATORY_CHANNEL")


# --- YORDAMCHI FUNKSIYALAR ---
def get_setting(key):
    db = SessionLocal()
    setting = db.query(Settings).filter(Settings.key == key).first()
    db.close()
    return setting.value if setting else None

# --- ASOSIY FOYDALANUVCHI FUNKSIYALARI ---
def is_subscribed(user_id: int, context: CallbackContext) -> bool:
    if user_id == ADMIN_ID:
        return True
    channel = get_setting('mandatory_channel')
    if not channel:
        return True 
    try:
        member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']:
            return True
    except Exception as e:
        print(f"Obunani tekshirishda xatolik: {e}")
    return False

def send_main_menu(update, context: CallbackContext, message_text="👋 Botimizga xush kelibsiz!"):
    """Foydalanuvchiga asosiy menyuni yuboradi"""
    buttons = [
        [InlineKeyboardButton("🔍 Kod Orqali Qidiruv", callback_data="search_by_code")],
        [InlineKeyboardButton("📞 Reklama", callback_data="advertisement")],
        [InlineKeyboardButton("📂 Ro'yxat", url=CATALOGUE_LINK)],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message_text,
        reply_markup=reply_markup
    )

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    db_session = SessionLocal()
    if not db_session.query(BotUser).filter(BotUser.user_id == user.id).first():
        new_user = BotUser(user_id=user.id, first_name=user.first_name, username=user.username)
        db_session.add(new_user)
        db_session.commit()
    db_session.close()
    if is_subscribed(user.id, context):
        send_main_menu(update, context)
    else:
        channel_to_join = get_setting('mandatory_channel')
        buttons = [[InlineKeyboardButton("📢 Kanalga Obuna Bo'lish", url=f"https://t.me/{channel_to_join.replace('@', '')}")],
                   [InlineKeyboardButton("✅ Tasdiqlash", callback_data="check_subscription")]]
        reply_markup = InlineKeyboardMarkup(buttons)
        update.message.reply_text(f"Botdan to'liq foydalanish uchun, iltimos, {channel_to_join} kanaliga obuna bo'ling:", reply_markup=reply_markup)

def check_subscription_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    if is_subscribed(query.from_user.id, context):
        query.answer("Rahmat! Endi botdan foydalanishingiz mumkin.", show_alert=True)
        query.message.delete()
        send_main_menu(update, context)
    else:
        query.answer("Siz hali kanalga obuna bo'lmadingiz.", show_alert=True)

# Asosiy menyu tugmalari uchun javoblar
def search_by_code_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    context.bot.send_message(chat_id=update.effective_chat.id, text="Iltimos, anime kodini yuboring:")
def advertisement_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Reklama va hamkorlik uchun murojaat: {AD_USER}")

# --- ADMIN PANELI FUNKSIYALARI ---
ADMIN_MAIN_MENU = range(1)

def admin_entry(update: Update, context: CallbackContext):
    """Admin paneliga maxfiy kod orqali kirish"""
    if update.message.from_user.id != ADMIN_ID:
        return ConversationHandler.END
    
    # Foydalanuvchi yuborgan xabar maxfiy kodga teng bo'lsa
    if update.message.text == SECRET_CODE:
        buttons = [
            [InlineKeyboardButton("➕ Anime Qo'shish", callback_data="admin_add_anime")],
            [InlineKeyboardButton("✏️ Animeni Tahrirlash", callback_data="admin_edit_anime")],
            [InlineKeyboardButton("❌ Animeni O'chirish", callback_data="admin_delete_anime")],
            [InlineKeyboardButton("📢 Hammaga Xabar Yuborish", callback_data="admin_broadcast")],
            [InlineKeyboardButton("⚙️ Sozlamalar", callback_data="admin_settings")],
            [InlineKeyboardButton("⬅️ Chiqish", callback_data="admin_exit")],
        ]
        reply_markup = InlineKeyboardMarkup(buttons)
        update.message.reply_text("🔑 Admin paneliga xush kelibsiz!", reply_markup=reply_markup)
        return ADMIN_MAIN_MENU
    return ConversationHandler.END

def admin_panel_fallback(update: Update, context: CallbackContext):
    """Admin panelidan noto'g'ri buyruq kelsa"""
    update.message.reply_text("Admin panelidan chiqdingiz. Qaytadan kirish uchun maxfiy kodni yuboring.")
    return ConversationHandler.END

# Admin paneli tugmalari uchun vaqtinchalik javoblar
def admin_button_tapped(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text(f"Siz '{query.data}' tugmasini bosdingiz. Bu funksiya tez orada qo'shiladi.")
    return ConversationHandler.END

def admin_exit_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Admin panelidan chiqdingiz.")
    # Oddiy foydalanuvchi menyusini ko'rsatamiz
    send_main_menu(update, context, message_text="Siz asosiy menyudasiz.")
    return ConversationHandler.END

# --- BAZANI BIRINCHI MARTA TO'LDIRISH ---
def initialize_settings():
    db = SessionLocal()
    if not db.query(Settings).filter(Settings.key == 'mandatory_channel').first() and DEFAULT_MANDATORY_CHANNEL:
        db.add(Settings(key='mandatory_channel', value=DEFAULT_MANDATORY_CHANNEL))
        db.commit()
        print(f"Standart majburiy kanal ({DEFAULT_MANDATORY_CHANNEL}) bazaga qo'shildi.")
    db.close()

# --- BOTNI ISHGA TUSHIRISH ---
def main():
    keep_alive()
    create_tables()
    initialize_settings()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Admin paneli uchun ConversationHandler
    admin_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, admin_entry)],
        states={
            ADMIN_MAIN_MENU: [
                CallbackQueryHandler(admin_exit_callback, pattern='admin_exit'),
                CallbackQueryHandler(admin_button_tapped), # Boshqa barcha tugmalar uchun
            ]
        },
        fallbacks=[MessageHandler(Filters.text & ~Filters.command, admin_panel_fallback)]
    )
    
    # Handlerlarni ro'yxatdan o'tkazish
    dp.add_handler(admin_conv_handler) # Admin panelini birinchi tekshiradi
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(check_subscription_callback, pattern='check_subscription'))
    dp.add_handler(CallbackQueryHandler(search_by_code_callback, pattern='search_by_code'))
    dp.add_handler(CallbackQueryHandler(advertisement_callback, pattern='advertisement'))
    # Boshqa handlerlar...

    updater.start_polling(timeout=30)
    print("Bot ishga tushdi va foydalanuvchilarni kutmoqda...")
    updater.idle()

if __name__ == "__main__":
    main()
