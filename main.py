import os
import json
import logging
import tempfile
import subprocess
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TELEGRAM_TOKEN")
ALLOWED_USERS_FILE = "users.json"

logging.basicConfig(level=logging.INFO)

def is_user_authorized(user_id):
    try:
        with open(ALLOWED_USERS_FILE, "r") as f:
            users = json.load(f)
        return str(user_id) in users
    except FileNotFoundError:
        return False

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text

    if not is_user_authorized(user_id):
        await update.message.reply_text("You are not authorized to use this bot. Please subscribe first.")
        return

    if not message.startswith("http"):
        await update.message.reply_text("Please send a valid link (Spotify, Deezer, YouTube, etc.).")
        return

    await update.message.reply_text("⏳ Downloading your file, please wait...")

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                ["spotdl", message],
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode != 0:
                await update.message.reply_text("❌ Download failed:\n" + result.stderr)
                return

            files = os.listdir(tmpdir)
            if not files:
                await update.message.reply_text("⚠️ No files found after download.")
                return

            if len(files) == 1 and files[0].endswith(".mp3"):
                mp3_path = os.path.join(tmpdir, files[0])
                response = subprocess.run(
                    ["curl", "--upload-file", mp3_path, f"https://transfer.sh/{files[0]}"],
                    capture_output=True,
                    text=True
                )
                await update.message.reply_text("✅ File ready:\n" + response.stdout)
            else:
                zip_path = os.path.join(tmpdir, "playlist.zip")
                subprocess.run(["zip", "-r", zip_path, "."], cwd=tmpdir)
                response = subprocess.run(
                    ["curl", "--upload-file", zip_path, "https://transfer.sh/playlist.zip"],
                    capture_output=True,
                    text=True
                )
                await update.message.reply_text("✅ Playlist ready:\n" + response.stdout)

        except Exception as e:
            await update.message.reply_text(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()