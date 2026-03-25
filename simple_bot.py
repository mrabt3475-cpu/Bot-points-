"""
🎮 PvP Games Bot - Simple Telegram Integration
"""

import os
import json
import random
import string
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, field, asdict
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, InlineQueryHandler
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")
    MIN_POINTS = 0.01
    MAX_POINTS = 2.0
    DB_PATH = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("PvPGamesBot")

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        os.makedirs(config.DB_PATH, exist_ok=True)
        self.users_file = f"{config.DB_PATH}/users.json"
        self._init_file()

    def _init_file(self):
        if not os.path.exists(self.users_file):
            self._save({})

    def _load(self):
        try:
            with open(self.users_file, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save(self, data):
        with open(self.users_file, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def users(self):
        return self._load()

    @users.setter
    def users(self, data):
        self._save(data)

db = Database()

# ==================== HELPERS ====================
def get_user(user_id: int) -> Dict:
    users = db.users
    uid = str(user_id)
    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "points": 0.0,
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "streak": 0,
            "best_streak": 0
        }
        db.users = users
    return users[uid]

def update_user(user_id: int, data: Dict):
    users = db.users
    uid = str(user_id)
    if uid in users:
        users[uid].update(data)
        db.users = users

def get_random_points() -> float:
    return round(random.uniform(config.MIN_POINTS, config.MAX_POINTS), 2)

# ==================== GAMES ====================
QUESTIONS = {
    "عام": [
        ("ما عاصمة فرنسا؟", "باريس"),
        ("من مكتشف أمريكا؟", "كولومبوس"),
        ("ما أكبر كوكب؟", "المشتري"),
        ("كم قارة في العالم؟", "7"),
        ("ما أطول نهر؟", "النيل"),
    ],
    "رياضيات": [
        ("5 + 8 × 2", "21"),
        ("10 + 5 × 3", "25"),
        ("100 ÷ 4 + 7", "32"),
        ("15 × 15 - 25", "200"),
    ]
}

# ==================== KEYBOARDS ====================
def main_keyboard(user_id: int):
    user = get_user(user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ {user['points']:.2f} نقطة", callback_data="points")],
        [InlineKeyboardButton("❓ سؤال", callback_data="play_عام"), InlineKeyboardButton("🔢 رياضيات", callback_data="play_رياضيات")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), InlineKeyboardButton("🏆 المتصدرين", callback_data="leaderboard")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    get_user(user.id)

    await update.message.reply_text(
        f"⚔️ مرحباً {user.first_name}!

"
        f"🎮 ألعاب ضد الأصدقاء
"
        f"💰 نقاط عشوائية: {config.MIN_POINTS} - {config.MAX_POINTS}

"
        f"اختر لعبة من الأزرار!",
        reply_markup=main_keyboard(user.id)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # Points
    if data == "points":
        user = get_user(user_id)
        await query.edit_message_text(
            f"⭐ نقاطك: {user['points']:.2f}",
            reply_markup=back_keyboard()
        )

    # Stats
    elif data == "stats":
        user = get_user(user_id)
        await query.edit_message_text(
            f"📊 إحصائياتك
"
            f"━━━━━━━━━━━━━━━━
"
            f"⭐ النقاط: {user['points']:.2f}
"
            f"🎮 لعبت: {user['games_played']}
"
            f"🏆 فزت: {user['games_won']}
"
            f"🔥 السلسلة: {user['streak']}",
            reply_markup=back_keyboard()
        )

    # Leaderboard
    elif data == "leaderboard":
        users = db.users
        sorted_users = sorted(users.items(), key=lambda x: x[1]['points'], reverse=True)[:5]

        text = "🏆 المتصدرين
━━━━━━━━━━━━━━━━
"
        for i, (uid, u) in enumerate(sorted_users, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            text += f"{medal} {u['points']:.2f} نقطة
"

        await query.edit_message_text(text, reply_markup=back_keyboard())

    # Play game
    elif data.startswith("play_"):
        category = data.replace("play_", "")
        q_list = QUESTIONS.get(category, QUESTIONS["عام"])
        q, a = random.choice(q_list)

        context.user_data['current_question'] = (q, a)
        context.user_data['category'] = category

        await query.edit_message_text(
            f"🎮 {category}

{q}

أرسل إجابتك!",
            reply_markup=back_keyboard()
        )

    # Back
    elif data == "back":
        user = update.callback_query.from_user
        await query.edit_message_text(
            f"⚔️ مرحباً {user.first_name}!

"
            f"🎮 ألعاب ضد الأصدقاء
"
            f"💰 نقاط عشوائية: {config.MIN_POINTS} - {config.MAX_POINTS}

"
            f"اختر لعبة من الأزرار!",
            reply_markup=main_keyboard(user_id)
        )

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    answer = update.message.text.strip()

    # Check if in game
    if 'current_question' in context.user_data:
        q, correct = context.user_data['current_question']
        category = context.user_data.get('category', 'عام')

        if answer.lower() == correct.lower():
            points = get_random_points()
            user = get_user(user_id)
            new_points = user['points'] + points
            new_streak = user['streak'] + 1

            update_user(user_id, {
                'points': new_points,
                'games_played': user['games_played'] + 1,
                'games_won': user['games_won'] + 1,
                'streak': new_streak,
                'best_streak': max(user['best_streak'], new_streak)
            })

            await update.message.reply_text(
                f"✅ إجابة صحيحة! +{points:.2f} نقطة!
🔥 سلسلة: {new_streak}",
                reply_markup=main_keyboard(user_id)
            )
        else:
            user = get_user(user_id)
            update_user(user_id, {
                'games_played': user['games_played'] + 1,
                'games_lost': user['games_lost'] + 1,
                'streak': 0
            })

            await update.message.reply_text(
                f"❌ خطأ! الإجابة: {correct}",
                reply_markup=main_keyboard(user_id)
            )

        del context.user_data['current_question']
        return

    # Default
    await update.message.reply_text(
        "⚔️ اضغط /start للبدء!",
        reply_markup=main_keyboard(user_id)
    )

# ==================== MAIN ====================
def main():
    logger.info("🎮 Starting PvP Games Bot...")

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(message))

    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
