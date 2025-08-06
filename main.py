import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update

# Charger les variables d'environnement
load_dotenv()

# Activer les logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Fonction /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎵 Bienvenue sur Deezdownloader ! Envoie un lien Spotify, Deezer, YouTube ou SoundCloud.")

def main():
    try:
        TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
        if not TELEGRAM_TOKEN:
            raise ValueError("TELEGRAM_TOKEN non défini dans .env")

        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        logging.info("Bot lancé avec succès.")
        app.run_polling()

    except Exception as e:
        logging.error(f"Erreur critique au lancement du bot : {e}")

if __name__ == '__main__':
    main()