import os
import asyncio
import logging
import yt_dlp
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# --- LOGGING SETUP ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# --- CONFIGURATION ---
# I have added both of your tokens here. 
TOKENS = [
    "8696860625:AAHha3afRieD4j8MF-KkHoncq5SGn910H9I",
    "8756326457:AAFe66o9I9y-NToIInxN-LhZkYt8E-vXk0o"
]

# --- DOWNLOAD LOGIC ---
async def download_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"):
        return

    status_msg = await update.message.reply_text("🔎 **Processing link...**", parse_mode="Markdown")

    # Unique filename based on user ID and timestamp
    file_id = f"{update.effective_user.id}_{int(asyncio.get_event_loop().time())}"
    output_template = f"downloads/{file_id}.%(ext)s"

    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': output_template,
        'noplaylist': True,
        'quiet': True,
    }

    try:
        # Download video in a separate thread to keep the bot responsive
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            await status_msg.edit_text("📥 **Downloading to server...**", parse_mode="Markdown")
            info = await asyncio.to_thread(ydl.extract_info, url, download=True)
            file_path = ydl.prepare_filename(info)

        # Check size (Telegram limit for standard bots is 50MB)
        file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        if file_size_mb > 50:
            await status_msg.edit_text(f"⚠️ **File too large ({file_size_mb:.1f}MB).**\nTelegram limit is 50MB.")
            os.remove(file_path)
            return

        await status_msg.edit_text("📤 **Uploading to Telegram...**", parse_mode="Markdown")
        
        with open(file_path, 'rb') as video:
            await update.message.reply_video(
                video=video, 
                caption=f"✅ **{info.get('title', 'Video')}**",
                parse_mode="Markdown"
            )
        
        await status_msg.delete()

    except Exception as e:
        await status_msg.edit_text(f"❌ **Error:** `{str(e)[:100]}`", parse_mode="Markdown")
    
    finally:
        # Ensure file is deleted even if error occurs
        if 'file_path' in locals() and os.path.exists(file_path):
            os.remove(file_path)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🤖 **Video Downloader Active!**\nSend me a link from YouTube, TikTok, or Twitter.")

# --- BOT RUNNER ---
async def start_bot(token):
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_and_send))
    
    await application.initialize()
    await application.start_polling()
    print(f"✅ Bot Started: {token[:10]}...")
    
    # Run forever
    while True:
        await asyncio.sleep(3600)

async def main():
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    # This starts both bots at the same time
    await asyncio.gather(*(start_bot(t) for t in TOKENS))

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 Bots stopped.")
