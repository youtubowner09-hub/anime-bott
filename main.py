# main.py
# YAKUNIY TO'LIQ VERSIYA (TUZATILGAN)

import os
import time
from database import create_tables, SessionLocal, BotUser, Settings, Anime, Episode
from flask import Flask
from threading import Thread
from telegram.ext import (Updater, CommandHandler, CallbackContext, CallbackQueryHandler, 
                          ConversationHandler, MessageHandler, Filters)
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaVideo
from sqlalchemy.orm import sessionmaker

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

def send_main_menu(update, context: CallbackContext, message_text="👋 Botimizga xush kelibsiz!"):
    buttons = [
        [InlineKeyboardButton("🔍 Kod Orqali Qidiruv", callback_data="search_by_code")],
        [InlineKeyboardButton("📞 Reklama", callback_data="advertisement")],
        [InlineKeyboardButton("📂 Ro'yxat", url=CATALOGUE_LINK)],
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    chat_id = update.effective_chat.id
    
    # Rasm bilan yuborish uchun MAIN_PHOTO_ID'ni tekshiramiz
    photo_id = os.environ.get("MAIN_PHOTO_ID")
    if photo_id and not update.callback_query: # Faqat /start da rasm yuboriladi
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

# ANIME QIDIRISH VA TOMOSHA QILISH
def handle_anime_code(update: Update, context: CallbackContext):
    code = update.message.text.strip()
    db = SessionLocal()
    anime = db.query(Anime).filter(Anime.search_code == code).first()
    db.close()
    if anime:
        send_anime_interface(update.message.chat_id, context, anime)
    else:
        update.message.reply_text("❌ Bunday kodga ega anime topilmadi.")

def send_anime_interface(chat_id, context: CallbackContext, anime: Anime):
    caption = f"🎬 *Nomi:* {anime.title}\n\n📝 *Tavsif:* {anime.description}"
    buttons = [[InlineKeyboardButton("▶️ Tomosha Qilish", callback_data=f"watch_{anime.id}")],
               [InlineKeyboardButton("⬅️ Asosiy Menyu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(buttons)
    context.bot.send_photo(chat_id=chat_id, photo=anime.main_photo_id, 
                           caption=caption, reply_markup=reply_markup, parse_mode='Markdown')

def main_menu_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer(); query.message.delete()
    send_main_menu(update, context)

def watch_anime_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    anime_id = int(query.data.split('_')[1])
    db = SessionLocal()
    episodes = db.query(Episode).filter(Episode.anime_id == anime_id).order_by(Episode.episode_number).all()
    db.close()
    if not episodes:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Bu anime uchun hali qismlar qo'shilmagan.")
        return
    
    first_episode_video_id = episodes[0].video_file_id
    
    buttons = []; row = []
    for episode in episodes:
        row.append(InlineKeyboardButton(str(episode.episode_number), callback_data=f"episode_{episode.id}"))
        if len(row) == 5: buttons.append(row); row = []
    if row: buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"back_to_anime_{anime_id}")])
    reply_markup = InlineKeyboardMarkup(buttons)

    query.message.delete()
    context.bot.send_video(chat_id=update.effective_chat.id, video=first_episode_video_id,
                           caption=f"1-qism. Kerakli qismni tanlang:", reply_markup=reply_markup)

def episode_select_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    episode_id = int(query.data.split('_')[1])
    db = SessionLocal()
    episode = db.query(Episode).filter(Episode.id == episode_id).first()
    db.close()
    if episode:
        media = InputMediaVideo(media=episode.video_file_id, caption=f"{episode.episode_number}-qism. Kerakli qismni tanlang:")
        try: query.edit_message_media(media=media, reply_markup=query.message.reply_markup)
        except Exception as e: print(f"Videoni o'zgartirishda xato: {e}")

def back_to_anime_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    anime_id = int(query.data.split('_')[-1])
    db = SessionLocal()
    anime = db.query(Anime).filter(Anime.id == anime_id).first()
    db.close()
    query.message.delete()
    send_anime_interface(query.message.chat_id, context, anime)

# --- ADMIN PANELI ---
ADMIN_MAIN, ADD_ANIME_CODE, ADD_ANIME_TITLE, ADD_ANIME_DESC, ADD_ANIME_PHOTO, \
ADD_EPISODE_CODE, ADD_EPISODE_VIDEOS, BROADCAST_MESSAGE = range(8)

def send_admin_panel(update: Update, context: CallbackContext):
    """Admin panel menyusini yuboradi"""
    buttons = [
        [InlineKeyboardButton("➕ Anime Qo'shish", callback_data="admin_add_anime")],
        [InlineKeyboardButton("🎞 Qismlar Qo'shish", callback_data="admin_add_episodes")],
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

def add_anime_start(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    query.edit_message_text("Yangi anime qo'shish.\n\nIltimos, anime uchun unikal qidiruv kodini yuboring (yoki /cancel):")
    return ADD_ANIME_CODE
def get_anime_code(update: Update, context: CallbackContext):
    context.user_data['new_anime_code'] = update.message.text
    update.message.reply_text("Kod qabul qilindi. Endi anime nomini yuboring:")
    return ADD_ANIME_TITLE
def get_anime_title(update: Update, context: CallbackContext):
    context.user_data['new_anime_title'] = update.message.text
    update.message.reply_text("Nomi qabul qilindi. Endi tavsifni yuboring:")
    return ADD_ANIME_DESC
def get_anime_description(update: Update, context: CallbackContext):
    context.user_data['new_anime_desc'] = update.message.text
    update.message.reply_text("Tavsif qabul qilindi. Endi asosiy rasmni yuboring:")
    return ADD_ANIME_PHOTO
def get_anime_photo(update: Update, context: CallbackContext):
    photo_id = update.message.photo[-1].file_id
    db = SessionLocal()
    new_anime = Anime(
        search_code=context.user_data['new_anime_code'], title=context.user_data['new_anime_title'],
        description=context.user_data['new_anime_desc'], main_photo_id=photo_id)
    db.add(new_anime); db.commit(); db.close()
    update.message.reply_text("✅ Yangi anime muvaffaqiyatli saqlandi!")
    send_admin_panel(update, context) # XATOLIKNI TUZATISH
    return ConversationHandler.END

def add_episodes_start(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    query.edit_message_text("Qaysi anime'ga qism qo'shmoqchisiz? Anime kodini yuboring (yoki /cancel):")
    return ADD_EPISODE_CODE
def add_episodes_get_code(update: Update, context: CallbackContext):
    code = update.message.text; db = SessionLocal()
    anime = db.query(Anime).filter(Anime.search_code == code).first()
    db.close()
    if not anime:
        update.message.reply_text("❌ Bunday kodli anime topilmadi. Qaytadan urinib ko'ring yoki /cancel bosing.")
        return ADD_EPISODE_CODE
    context.user_data['anime_to_add_episode_id'] = anime.id
    update.message.reply_text(f"✅ Anime '{anime.title}' topildi. Endi qismlarni (videolarni) birma-bir yuboring.\n\nBarcha qismlarni yuborib bo'lgach, /done buyrug'ini yuboring.")
    return ADD_EPISODE_VIDEOS
def add_episode_video(update: Update, context: CallbackContext):
    if not update.message.video:
        update.message.reply_text("Iltimos, faqat video yuboring.")
        return ADD_EPISODE_VIDEOS
    video_id = update.message.video.file_id
    anime_id = context.user_data['anime_to_add_episode_id']
    db = SessionLocal()
    episode_count = db.query(Episode).filter(Episode.anime_id == anime_id).count()
    new_episode = Episode(anime_id=anime_id, episode_number=episode_count + 1, video_file_id=video_id)
    db.add(new_episode); db.commit()
    update.message.reply_text(f"{episode_count + 1}-qism qo'shildi. Yana video yuboring yoki /done bosing.")
    db.close()
    return ADD_EPISODE_VIDEOS
def broadcast_start(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer()
    query.edit_message_text("Barcha foydalanuvchilarga yuborish uchun xabaringizni kiriting (yoki /cancel):")
    return BROADCAST_MESSAGE
def broadcast_message_handler(update: Update, context: CallbackContext):
    db = SessionLocal(); users = db.query(BotUser.user_id).all(); db.close()
    successful_sends = 0; failed_sends = 0
    update.message.reply_text(f"Xabar yuborish boshlandi. Jami foydalanuvchilar: {len(users)}. Bu biroz vaqt olishi mumkin.")
    for user in users:
        try:
            context.bot.copy_message(chat_id=user.user_id, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
            successful_sends += 1
        except Exception as e:
            failed_sends += 1; print(f"Xabar yuborishda xato (ID: {user.user_id}): {e}")
        time.sleep(0.1)
    context.bot.send_message(chat_id=ADMIN_ID, text=f"📢 Ommaviy xabar yuborish yakunlandi.\n\nMuvaffaqiyatli: {successful_sends}\nXatolik: {failed_sends}")
    send_admin_panel(update, context) # XATOLIKNI TUZATISH
    return ConversationHandler.END

def admin_exit_callback(update: Update, context: CallbackContext):
    query = update.callback_query; query.answer(); query.message.delete()
    send_main_menu(update, context, message_text="Siz asosiy menyudasiz.")
    return ConversationHandler.END
def cancel_conversation(update: Update, context: CallbackContext):
    update.message.reply_text("Amal bekor qilindi.")
    send_admin_panel(update, context) # XATOLIKNI TUZATISH
    return ConversationHandler.END
def initialize_settings():
    db = SessionLocal()
    if not db.query(Settings).filter(Settings.key == 'mandatory_channel').first() and DEFAULT_MANDATORY_CHANNEL:
        db.add(Settings(key='mandatory_channel', value=DEFAULT_MANDATORY_CHANNEL))
        db.commit(); print(f"Standart majburiy kanal ({DEFAULT_MANDATORY_CHANNEL}) bazaga qo'shildi.")
    db.close()

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
        ],
        states={
            ADMIN_MAIN: [
                CallbackQueryHandler(add_anime_start, pattern='admin_add_anime'),
                CallbackQueryHandler(add_episodes_start, pattern='admin_add_episodes'),
                CallbackQueryHandler(broadcast_start, pattern='admin_broadcast'),
                CallbackQueryHandler(admin_exit_callback, pattern='admin_exit')
            ],
            ADD_ANIME_CODE: [MessageHandler(Filters.text & ~Filters.command, get_anime_code)],
            ADD_ANIME_TITLE: [MessageHandler(Filters.text & ~Filters.command, get_anime_title)],
            ADD_ANIME_DESC: [MessageHandler(Filters.text & ~Filters.command, get_anime_description)],
            ADD_ANIME_PHOTO: [MessageHandler(Filters.photo, get_anime_photo)],
            ADD_EPISODE_CODE: [MessageHandler(Filters.text & ~Filters.command, add_episodes_get_code)],
            ADD_EPISODE_VIDEOS: [MessageHandler(Filters.video, add_episode_video), CommandHandler('done', cancel_conversation)],
            BROADCAST_MESSAGE: [MessageHandler(Filters.all & ~Filters.command, broadcast_message_handler)]
        },
        fallbacks=[CommandHandler('cancel', cancel_conversation)]
    )
    
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
