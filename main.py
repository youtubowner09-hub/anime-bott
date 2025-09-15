# main.py
# 7-VERSIYA: ANIME O'CHIRISH VA XATOLIKLARNI TUZATISH

import os
import time
from database import create_tables, SessionLocal, BotUser, Settings, Anime, Episode
from flask import Flask
from threading import Thread
from telegram.ext import (Updater, CommandHandler, CallbackContext, CallbackQueryHandler, 
                          ConversationHandler, MessageHandler, Filters)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo

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
AD_USER = os.environ.get("AD_USER")
CATALOGUE_LINK = os.environ.get("CATALOGUE_LINK")
DEFAULT_MANDATORY_CHANNEL = os.environ.get("DEFAULT_MANDATORY_CHANNEL")


# --- YORDAMCHI FUNKSIYALAR ---
def get_setting(key):
    db = SessionLocal()
    setting = db.query(Settings).filter(Settings.key == key).first()
    db.close()
    return setting.value if setting else None

# --- FOYDALANUVCHI FUNKSIYALARI ---
def is_subscribed(user_id: int, context: CallbackContext) -> bool:
    if user_id == ADMIN_ID: return True
    channel = get_setting('mandatory_channel')
    if not channel: return True 
    try:
        member = context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        if member.status in ['creator', 'administrator', 'member']: return True
    except Exception as e: print(f"Obunani tekshirishda xatolik: {e}")
    return False

def send_main_menu(update: Update, context: CallbackContext, message_text="👋 Botimizga xush kelibsiz!"):
    buttons = [
        [InlineKeyboardButton("🔍 Kod Orqali Qidiruv", callback_data="search_by_code")],
        [InlineKeyboardButton("📞 Reklama", callback_data="advertisement")],
        [InlineKeyboardButton("📂 Ro'yxat", url=CATALOGUE_LINK)],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    chat_id = update.effective_chat.id
    photo_id = os.environ.get("MAIN_PHOTO_ID")

    if update.callback_query:
        try:
            context.bot.edit_message_text(chat_id=chat_id, message_id=update.callback_query.message.message_id, text=message_text, reply_markup=reply_markup)
        except:
             context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)
    else:
        if photo_id:
            context.bot.send_photo(chat_id=chat_id, photo=photo_id, caption=message_text, reply_markup=reply_markup)
        else:
            context.bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup)

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    db = SessionLocal()
    if not db.query(BotUser).filter(BotUser.user_id == user.id).first():
        db.add(BotUser(user_id=user.id, first_name=user.first_name, username=user.username))
        db.commit()
    db.close()
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
        query.answer("Rahmat!", show_alert=True); query.message.delete(); send_main_menu(update, context)
    else:
        query.answer("Siz hali kanalga obuna bo'lmadingiz.", show_alert=True)

def search_by_code_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    context.bot.send_message(chat_id=update.effective_chat.id, text="Iltimos, anime kodini yuboring:")

def advertisement_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Reklama va hamkorlik uchun murojaat: {AD_USER}")

# ANIME QIDIRISH VA TOMOSHA QILISH... (O'zgarishsiz)

# --- ADMIN PANELI ---
# Holatlar
ADMIN_MAIN, ADD_ANIME_CODE, ADD_ANIME_TITLE, ADD_ANIME_DESC, ADD_ANIME_PHOTO, \
ADD_EPISODE_CODE, ADD_EPISODE_VIDEOS, BROADCAST_MESSAGE, \
DELETE_ANIME_CODE, DELETE_ANIME_CONFIRM = range(10) # YANGI HOLATLAR QO'SHILDI

def send_admin_panel(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton("➕ Anime Qo'shish", callback_data="admin_add_anime")],
        [InlineKeyboardButton("🎞 Qismlar Qo'shish", callback_data="admin_add_episodes")],
        [InlineKeyboardButton("❌ Animeni O'chirish", callback_data="admin_delete_anime")],
        [InlineKeyboardButton("📢 Hammaga Xabar", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⬅️ Chiqish", callback_data="admin_exit")],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text("🔑 Admin paneliga xush kelibsiz!", reply_markup=reply_markup)

def admin_entry(update: Update, context: CallbackContext):
    if update.message.from_user.id == ADMIN_ID and update.message.text == SECRET_CODE:
        send_admin_panel(update, context)
        return ADMIN_MAIN
    handle_anime_code(update, context)
    return ConversationHandler.END

# ANIME QO'SHISH
def add_anime_start(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    query.edit_message_text("Yangi anime qo'shish.\n\nIltimos, anime uchun unikal qidiruv kodini yuboring (yoki /cancel):")
    return ADD_ANIME_CODE
def get_anime_code(update: Update, context: CallbackContext):
    code = update.message.text
    db = SessionLocal()
    # YANGI TEKSHIRUV: Bu kod band emasligini tekshiramiz
    existing_anime = db.query(Anime).filter(Anime.search_code == code).first()
    db.close()
    if existing_anime:
        update.message.reply_text("❌ Bu kod allaqachon band. Iltimos, boshqa kod kiriting.")
        return ADD_ANIME_CODE # Shu holatda qolamiz
    
    context.user_data['new_anime_code'] = code
    update.message.reply_text("Kod qabul qilindi. Endi anime nomini yuboring:")
    return ADD_ANIME_TITLE
# ... (Anime qo'shishning qolgan qismi o'zgarishsiz) ...

# ANIME O'CHIRISH FUNKSIYALARI
def delete_anime_start(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    query.edit_message_text("❌ O'chirish uchun anime kodini yuboring (yoki /cancel):")
    return DELETE_ANIME_CODE

def get_anime_to_delete(update: Update, context: CallbackContext):
    code = update.message.text
    db = SessionLocal()
    anime = db.query(Anime).filter(Anime.search_code == code).first()
    db.close()

    if not anime:
        update.message.reply_text("❌ Bunday kodli anime topilmadi. Qaytadan kiriting yoki /cancel bosing.")
        return DELETE_ANIME_CODE
    
    context.user_data['anime_to_delete_id'] = anime.id
    buttons = [
        [InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"delete_confirm_{anime.id}")],
        [InlineKeyboardButton("🚫 Yo'q, bekor qilish", callback_data="delete_cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text(f"❓Siz rostdan ham '{anime.title}' (kodi: {anime.search_code}) animesini barcha qismlari bilan birga o'chirmoqchimisiz?",
                              reply_markup=reply_markup)
    return DELETE_ANIME_CONFIRM

def delete_anime_confirm(update: Update, context: CallbackContext):
    query = update.callback_query
    anime_id = int(query.data.split('_')[-1])
    
    db = SessionLocal()
    # Avval shu animega tegishli barcha qismlarni o'chiramiz
    db.query(Episode).filter(Episode.anime_id == anime_id).delete()
    # Keyin animening o'zini o'chiramiz
    db.query(Anime).filter(Anime.id == anime_id).delete()
    db.commit()
    db.close()
    
    query.answer("Anime muvaffaqiyatli o'chirildi!", show_alert=True)
    query.message.delete()
    
    # Asosiy admin paneliga qaytish uchun bo'sh update yaratib chaqiramiz
    # Bu biroz "hiyla", lekin ishlaydi
    fake_update = Update(update_id=0, message=query.message)
    send_admin_panel(fake_update, context)
    return ConversationHandler.END

def delete_anime_cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    query.edit_message_text("Amal bekor qilindi.")
    
    fake_update = Update(update_id=0, message=query.message)
    send_admin_panel(fake_update, context)
    return ConversationHandler.END

# Qolgan funksiyalar... (o'zgarishsiz)


# --- BOTNI ISHGA TUSHIRISH ---
def main():
    keep_alive()
    create_tables()
    initialize_settings()

    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    admin_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(Filters.text & ~Filters.command, admin_entry),
            CallbackQueryHandler(add_anime_start, pattern='admin_add_anime'),
            CallbackQueryHandler(add_episodes_start, pattern='admin_add_episodes'),
            CallbackQueryHandler(broadcast_start, pattern='admin_broadcast'),
            CallbackQueryHandler(delete_anime_start, pattern='admin_delete_anime') # YANGI
        ],
        states={
            ADMIN_MAIN: [
                CallbackQueryHandler(add_anime_start, pattern='admin_add_anime'),
                CallbackQueryHandler(add_episodes_start, pattern='admin_add_episodes'),
                CallbackQueryHandler(broadcast_start, pattern='admin_broadcast'),
                CallbackQueryHandler(delete_anime_start, pattern='admin_delete_anime'), # YANGI
                CallbackQueryHandler(admin_exit_callback, pattern='admin_exit')
            ],
            ADD_ANIME_CODE: [MessageHandler(Filters.text & ~Filters.command, get_anime_code)],
            ADD_ANIME_TITLE: [MessageHandler(Filters.text & ~Filters.command, get_anime_title)],
            ADD_ANIME_DESC: [MessageHandler(Filters.text & ~Filters.command, get_anime_description)],
            ADD_ANIME_PHOTO: [MessageHandler(Filters.photo, get_anime_photo)],
            
            ADD_EPISODE_CODE: [MessageHandler(Filters.text & ~Filters.command, add_episodes_get_code)],
            ADD_EPISODE_VIDEOS: [MessageHandler(Filters.video, add_episode_video), CommandHandler('done', cancel_conversation)],
            
            BROADCAST_MESSAGE: [MessageHandler(Filters.all & ~Filters.command, broadcast_message_handler)],

            # YANGI HOLATLAR
            DELETE_ANIME_CODE: [MessageHandler(Filters.text & ~Filters.command, get_anime_to_delete)],
            DELETE_ANIME_CONFIRM: [
                CallbackQueryHandler(delete_anime_confirm, pattern=r'^delete_confirm_'),
                CallbackQueryHandler(delete_anime_cancel, pattern='delete_cancel')
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    
    # ... (qolgan handlerlar o'zgarishsiz) ...
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(check_subscription_callback, pattern='check_subscription'))
    dp.add_handler(CallbackQueryHandler(main_menu_callback, pattern='main_menu'))
    dp.add_handler(CallbackQueryHandler(advertisement_callback, pattern='advertisement'))
    dp.add_handler(CallbackQueryHandler(watch_anime_callback, pattern=r'^watch_'))
    dp.add_handler(CallbackQueryHandler(episode_select_callback, pattern=r'^episode_'))
    dp.add_handler(CallbackQueryHandler(back_to_anime_callback, pattern=r'^back_to_anime_'))
    dp.add_handler(CallbackQueryHandler(search_by_code_callback, pattern='search_by_code'))
    dp.add_handler(admin_conv_handler)

    updater.start_polling(timeout=30)
    print("Bot ishga tushdi...")
    updater.idle()

if __name__ == "__main__":
    main()
