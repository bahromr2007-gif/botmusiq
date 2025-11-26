import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pydub import AudioSegment
from shazamio import Shazam
import yt_dlp

TOKEN = "8172860090:AAESHIwiNU2n9vgtBVxKthIoQcvRzlHZSNw"    # Railway env
cookies_file = "cookies.txt"          # Instagram cookies
yt_cache = {}                         # Tanlangan videolarni saqlash

AudioSegment.converter = "/usr/bin/ffmpeg"

# --------------------------
#  MUSIC RECOGNIZER
# --------------------------
async def recognize_music_safe(audio_path: str):
    try:
        shazam = Shazam()
        out = await shazam.recognize(audio_path)
        track = out.get("track")
        if not track:
            return "❌ Musiqa topilmadi."

        title = track.get("title", "Noma'lum")
        artist = track.get("subtitle", "Noma'lum")
        return f"🎧 Musiqa topildi:\n🎵 {title}\n👤 {artist}"

    except Exception:
        return "❌ Shazam xato berdi."

# --------------------------
#  INSTAGRAM DOWNLOADER
# --------------------------
async def download_instagram(update: Update, link: str):
    await update.message.reply_text("📥 Yuklanyapti...")

    video_filename = None
    audio_filename = None

    ydl_opts = {
        "format": "best",
        "outtmpl": "insta_video.%(ext)s",
        "quiet": True,
        "cookies": cookies_file
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=True)
            video_filename = ydl.prepare_filename(info)

        await update.message.reply_video(video=open(video_filename, "rb"), caption="📸 Video tayyor!")

        audio_filename = "music.mp3"
        audio = AudioSegment.from_file(video_filename)
        audio.export(audio_filename, format="mp3")

        await update.message.reply_audio(audio=open(audio_filename, "rb"), caption="🎧 Musiqa ajratildi!")
        await update.message.reply_text("🔍 Musiqa nomi aniqlanmoqda...")

        music_info = await recognize_music_safe(audio_filename)
        await update.message.reply_text(music_info)

    except Exception as e:
        await update.message.reply_text(f"❌ Xato: {e}")

    finally:
        for file in [video_filename, audio_filename]:
            if file and os.path.exists(file):
                os.remove(file)

# --------------------------
#  YOUTUBE QIDIRUV & MP3
# --------------------------
async def search_music_by_text(update: Update, query: str):
    search = f"ytsearch5:{query}"
    ydl_opts = {"quiet": True, "format": "bestaudio/best", "noplaylist": True, "cookies": cookies_file}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(search, download=False)
            videos = info.get("entries", [])
    except Exception as e:
        await update.message.reply_text(f"❌ YouTube xatosi: {e}")
        return

    if not videos:
        await update.message.reply_text("❌ Hech qanday qo‘shiq topilmadi.")
        return

    keyboard = []
    for i, v in enumerate(videos, start=1):
        title = v.get("title")[:60]
        url = v.get("webpage_url")
        yt_cache[i] = url
        keyboard.append([InlineKeyboardButton(f"{i}. {title}", callback_data=f"yt|{i}")])

    await update.message.reply_text(
        "🎵 Topilgan qo‘shiqlardan birini tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def send_chosen_song(update: Update, song_id: int):
    url = yt_cache.get(song_id)
    if not url:
        await update.callback_query.message.reply_text("⚠️ Xatolik: qo‘shiq topilmadi.")
        return

    await update.callback_query.edit_message_text("⏳ Yuklanmoqda...")

    ydl_opts = {"format": "bestaudio/best", "outtmpl": "download.%(ext)s", "quiet": True}

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        mp3_file = "audio.mp3"
        audio = AudioSegment.from_file(filename)
        audio.export(mp3_file, format="mp3")

        await update.effective_chat.send_audio(
            audio=open(mp3_file, "rb"),
            caption=f"🎵 {info.get('title')}"
        )

    finally:
        for f in [filename, mp3_file]:
            if os.path.exists(f):
                os.remove(f)

# --------------------------
#  MESSAGE HANDLER
# --------------------------
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "instagram.com" in text:
        await download_instagram(update, text)
    else:
        # Foydalanuvchi yozgan matndan YouTube qidiruv
        await search_music_by_text(update, text)

# --------------------------
#  CALLBACK HANDLER
# --------------------------
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = update.callback_query.data
    if data.startswith("yt|"):
        song_id = int(data.split("|")[1])
        await send_chosen_song(update, song_id)

# --------------------------
#  BOT STARTER
# --------------------------
async def main():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
