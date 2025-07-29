import os
import json
import asyncio
import subprocess
import time
import shutil
import tempfile
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")
AUTHORIZED_USERS_FILE = "users.json"
VALIDITY_DAYS = 30
MAX_TRACKS = 1000
MAX_PLAYLISTS = 100

def load_users():
    if not os.path.exists(AUTHORIZED_USERS_FILE):
        return {}
    with open(AUTHORIZED_USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(AUTHORIZED_USERS_FILE, "w") as f:
        json.dump(users, f, indent=2)

def is_valid(user_data):
    start = datetime.strptime(user_data["start_date"], "%Y-%m-%d")
    return datetime.now() <= start + timedelta(days=VALIDITY_DAYS)

def update_usage(user_data, is_playlist):
    if is_playlist:
        user_data["playl]()_