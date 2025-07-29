import os
import json
import subprocess
import time
import uuid
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from datetime import datetime, timedelta

# === CONFIGURATION ===
ADMIN_IDS = [2082519170]  # Benjamin
USERS_FILE = "users.json"
TEMP_DIR = "temp"
DOWNLOAD_LIMIT_TRACKS = 1000
DOWNLOAD_LIMIT_PLAYLISTS = 100

# === UTILS ===
def load_users():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w") as f:
            json.dump({}, f)
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=4)

def is_playlist(link):
    return "playlist" in link or "album" in link

def user_valid(user_id):
    users = load_users()
    user_data = users.get(str(user_id))
    if not user_data:
        return False
    expiration = datetime.fromisoformat(user_data["expiration"])
    return expiration > datetime.now()

def increment_usage(user_id, is_playlist_dl):
    users = load_users()
    user_data = users[str(user_id)]

    if is_playlist_dl:
        user_data["playlists"] += 1
    else:
        user_data["tracks"] += 1

    save_users(users)

def usage_limit_reached(user_id, is_playlist_dl):
    users = load_users()
    user_data = users[str(user_id)]

    if is_playlist_dl:
        return user_data["playlists"] >= DOWNLOAD_LIMIT_PLAYLISTS
    else:
        return user_data["tracks"] >= DOWNLOAD_LIMIT_TRACKS

def get_unique_path():
    return os.path.join(TEMP_DIR, str(uuid.uuid4()))

def upload_to_transfer_sh(file_path):
    try:
        filename = os.path.basename(file_path)
        result = subprocess.run(
            ["curl", "--upload-file", file_path, f"https://transfer.sh/{filename}"],
            capture_output=True, text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Upload failed: {str(e)}"

def ensure_temp_dir():
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

# === HANDLERS ===
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if not user_valid(user_id):
        await update.message.reply_text("⛔️ You are not subscribed. Send 2€ via PayPal to benjaminallemand3@gmail.com to activate access.")
        return

    if not text.startswith("http"):
        await update.message.reply_text("❗️Please send a valid link from Spotify, Deezer, YouTube, Beatport or SoundCloud.")
        return

    await update.message.reply_text("⏳ Download in progress... It may take some time.")

    ensure_temp_dir()
    path = get_unique_path()
    is_playlist_dl = is_playlist(text)

    if usage_limit_reached(user_id, is_playlist_dl):
        await update.message.reply_text("⚠️ Monthly download limit reached.")
        return

    try:
        command = ["spotdl", "--output", path, text]
        subprocess.run(command, check=True)

        increment_usage(user_id, is_playlist_dl)

        if is_playlist_dl:
            zip_path = f"{path}.zip"
            subprocess.run(["zip", "-r", zip_path, path])
            link = upload_to_transfer_sh(zip_path)
        else:
            files = os.listdir(path)
            if not files:
                await update.message.reply_text("❌ No files found.")
                return
            file_path = os.path.join(path, files[0])
            link = upload_to_transfer_sh(file_path)

        await update.message.reply_text(f"✅ Done! Download your file here:\n{link}\n\n⚠️ File expires in 14 days.")

    except subprocess.CalledProcessError:
        await update.message.reply_text("❌ Download failed. Please try again later.")

# === ADMIN ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Send a music link (Spotify, Deezer, YouTube, SoundCloud, Beatport).\n\n💳 Price: 2€ via PayPal (benjaminallemand3@gmail.com).")

async def validate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔️ Unauthorized.")
        return

    if len(context.args) != 1:
        await update.message.reply_text("Usage: /valider email")
        return

    email = context.args[0].strip().lower()
    users = load_users()

    # Use email as key to user ID
    users[str(email)] = {
        "expiration": (datetime.now() + timedelta(days=30)).isoformat(),
        "tracks": 0,
        "playlists": 0
    }
    save_users(users)
    await update.message.reply_text(f"✅ {email} is now validated for 30 days.")

# === MAIN ===
if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()

    app = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex("^/start$"), start))
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex("^/valider "), validate))

    print("Bot started...")
    app.run_polling()