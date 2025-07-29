import os
import json
import re
import time
import shutil
import zipfile
import tempfile
import requests
import subprocess
from datetime import datetime, timedelta
from telegram import Update, ForceReply
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

TELEGRAM_TOKEN = "7746150496:AAEHw_Uc-BcNTSouAS8SO5LT0DF6NS1PHmQ"
PAYPAL_EMAIL = "benjaminallemand3@gmail.com"
PAYPAL_PRICE = 2.00

USERS_FILE = "users.json"
LIMIT_TRACKS = 1000
LIMIT_PLAYLISTS = 100

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def is_validated(user_id):
    users = load_users()
    user = users.get(str(user_id))
    if not user:
        return False
    if "valid_until" not in user:
        return False
    return datetime.strptime(user["valid_until"], "%Y-%m-%d") >= datetime.today()

def update_usage(user_id, content_type):
    users = load_users()
    user = users.get(str(user_id), {})
    today = datetime.today()
    if "valid_until" not in user or datetime.strptime(user["valid_until"], "%Y-%m-%d") < today:
        user = {
            "valid_until": (today + timedelta(days=30)).strftime("%Y-%m-%d"),
            "tracks": 0,
            "playlists": 0,
        }
    if content_type == "track":
        user["tracks"] = user.get("tracks", 0) + 1
    elif content_type == "playlist":
        user["playlists"] = user.get("playlists", 0) + 1
    users[str(user_id)] = user
    save_users(users)

def is_within_limits(user_id, content_type):
    users = load_users()
    user = users.get(str(user_id), {})
    if content_type == "track":
        return user.get("tracks", 0) < LIMIT_TRACKS
    elif content_type == "playlist":
        return user.get("playlists", 0) < LIMIT_PLAYLISTS
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_validated(user_id):
        msg = (
            "✅ Envoyez un lien Spotify, Deezer, YouTube ou SoundCloud.\n"
            "🎧 MP3 (morceaux) ou ZIP (playlists).\n\n"
            "💬 This bot costs 2€/month. Legal use only.\n"
            "⏳ Le fichier peut mettre du temps à arriver selon la taille."
        )
    else:
        msg = (
            "🔒 Ce bot coûte 2€ par mois.\n"
            "👉 Payez via PayPal : benjaminallemand3@gmail.com\n"
            "✅ Puis prévenez l’admin pour activation (valide 30 jours)."
        )
    await update.message.reply_text(msg)

def detect_link_type(url):
    if "playlist" in url:
        return "playlist"
    return "track"

def download_spotdl(link, output_dir):
    try:
        subprocess.run([
            "spotdl", link,
            "--output", output_dir,
            "--bitrate", "320k",
            "--ffmpeg", "ffmpeg"
        ], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def zip_directory(path, zip_name):
    with zipfile.ZipFile(zip_name, 'w') as zipf:
        for root, _, files in os.walk(path):
            for file in files:
                abs_path = os.path.join(root, file)
                arcname = os.path.relpath(abs_path, path)
                zipf.write(abs_path, arcname)

def upload_transfer_sh(file_path):
    with open(file_path, 'rb') as f:
        response = requests.put(f"https://transfer.sh/{os.path.basename(file_path)}", data=f)
    return response.text.strip()

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_validated(user_id):
        await update.message.reply_text("🔒 Vous n'êtes pas encore validé. Envoyez 2€ via PayPal à benjaminallemand3@gmail.com et contactez l’admin.")
        return

    url = update.message.text.strip()
    if not re.match(r'^https?://', url):
        await update.message.reply_text("❌ Lien invalide.")
        return

    link_type = detect_link_type(url)
    if not is_within_limits(user_id, link_type):
        await update.message.reply_text(f"🚫 Vous avez atteint la limite de {LIMIT_TRACKS if link_type == 'track' else LIMIT_PLAYLISTS} {link_type}s ce mois-ci.")
        return

    msg = await update.message.reply_text("⏳ Téléchargement en cours, merci de patienter...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        success = download_spotdl(url, tmp_dir)
        if not success:
            await msg.edit_text("❌ Échec du téléchargement. Essayez un autre lien.")
            return

        if link_type == "track":
            files = os.listdir(tmp_dir)
            if not files:
                await msg.edit_text("❌ Aucun fichier trouvé.")
                return
            file_path = os.path.join(tmp_dir, files[0])
        else:
            zip_path = os.path.join(tmp_dir, "playlist.zip")
            zip_directory(tmp_dir, zip_path)
            file_path = zip_path

        download_url = upload_transfer_sh(file_path)
        update_usage(user_id, link_type)
        await msg.edit_text(f"✅ Voici ton fichier :\n{download_url}")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    app.run_polling()