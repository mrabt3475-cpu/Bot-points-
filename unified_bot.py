"""
🎮 CryptoPuzzle - المنصة الشاملة
💰 نظام اقتصادي + ألعاب + صناديق + تبادل
"""

import os
import json
import random
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
    DB_PATH = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("CryptoPuzzle")

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        os.makedirs(config.DB_PATH, exist_ok=True)
        self.users_file = f"{config.DB_PATH}/users.json"
        self.boxes_file = f"{config.DB_PATH}/boxes.json"
        self.eco_file = f"{config.DB_PATH}/economy.json"
        self._init_files()

    def _init_files(self):
        defaults = {
            self.users_file: {},
            self.boxes_file: {"stats": {"opened": 0, "spent": 0}},
            self.eco_file: {"supply": 100000, "burned": 0, "tax": 0}
        }
        for path, data in defaults.items():
            if not os.path.exists(path):
                self._save(path, data)

    def _load(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def users(self):
        return self._load(self.users_file)

    @users.setter
    def users(self, data):
        self._save(self.users_file, data)

    @property
    def boxes(self):
        return self._load(self.boxes_file)

    @boxes.setter
    def boxes(self, data):
        self._save(self.boxes_file, data)

    @property
    def economy(self):
        return self._load(self.eco_file)

    @economy.setter
    def economy(self, data):
        self._save(self.eco_file, data)

db = Database()

# ==================== ECONOMY ====================
class Economy:
    MAX_SUPPLY = 1000000
    DAILY_LIMIT = 50000
    BURN_RATE = 0.05
    TAX_RATE = 0.02

    @classmethod
    def can_mint(cls, amount: float) -> bool:
        eco = db.economy
        return eco.get("supply", 0) + amount <= cls.MAX_SUPPLY

    @classmethod
    def mint(cls, amount: float) -> Tuple[bool, float]:
        if not cls.can_mint(amount):
            return False, 0
        burn = amount * cls.BURN_RATE
        net = amount - burn
        eco = db.economy
        eco["supply"] = eco.get("supply", 0) + net
        eco["burned"] = eco.get("burned", 0) + burn
        db.economy = eco
        return True, net

    @classmethod
    def apply_tax(cls, amount: float) -> Tuple[float, float]:
        tax = amount * cls.TAX_RATE
        eco = db.economy
        eco["tax"] = eco.get("tax", 0) + tax
        db.economy = eco
        return amount - tax, tax

# ==================== BOX SYSTEM ====================
BOXES = {
    "basic": {"name": "📦 أساسي", "price": 50, "emoji": "📦"},
    "silver": {"name": "🥈 فضي", "price": 150, "emoji": "🥈"},
    "gold": {"name": "🥇 ذهبي", "price": 500, "emoji": "🥇"},
    "diamond": {"name": "💎 ماسي", "price": 1500, "emoji": "💎"},
    "mythic": {"name": "🔥 أسطوري", "price": 5000, "emoji": "🔥"},
}

REWARDS = {
    "basic": [
        {"type": "points", "min": 10, "max": 50, "chance": 80},
        {"type": "gems", "min": 1, "max": 5, "chance": 20},
    ],
    "silver": [
        {"type": "points", "min": 50, "max": 150, "chance": 60},
        {"type": "gems", "min": 5, "max": 15, "chance": 25},
        {"type": "item", "chance": 15},
    ],
    "gold": [
        {"type": "points", "min": 200, "max": 500, "chance": 45},
        {"type": "gems", "min": 20, "max": 50, "chance": 20},
        {"type": "item", "chance": 20},
        {"type": "title", "chance": 15},
    ],
    "diamond": [
        {"type": "points", "min": 500, "max": 1500, "chance": 35},
        {"type": "gems", "min": 50, "max": 100, "chance": 20},
        {"type": "item", "chance": 25},
        {"type": "title", "chance": 10},
        {"type": "boost", "chance": 10},
    ],
    "mythic": [
        {"type": "points", "min": 2000, "max": 5000, "chance": 25},
        {"type": "gems", "min": 100, "max": 300, "chance": 20},
        {"type": "item", "chance": 20},
        {"type": "title", "chance": 15},
        {"type": "boost", "chance": 10},
        {"type": "ton", "chance": 10},
    ],
}

ITEMS = [
    {"id": "sword_bronze", "name": "سيف برونزي", "rarity": "common", "value": 100},
    {"id": "sword_silver", "name": "سيف فضي", "rarity": "uncommon", "value": 300},
    {"id": "sword_gold", "name": "سيف ذهبي", "rarity": "rare", "value": 1000},
    {"id": "shield_diamond", "name": "درع ماسي", "rarity": "epic", "value": 3000},
    {"id": "gem_red", "name": "ياقوت أحمر", "rarity": "rare", "value": 500},
]

TITLES = [
    {"id": "lucky", "name": "محظوظ", "emoji": "🟢"},
    {"id": "champion", "name": "بطل", "emoji": "🏆"},
    {"id": "master", "name": "أستاذ", "emoji": "🎓"},
    {"id": "legend", "name": "أسطورة", "emoji": "🔥"},
    {"id": "king", "name": "ملك", "emoji": "👑"},
]

BOOSTS = [
    {"id": "xp_2x", "name": "XP ×2", "duration": 3600},
    {"id": "points_2x", "name": "نقاط ×2", "duration": 3600},
    {"id": "streak_freeze", "name": "تجميد السلسلة", "duration": 86400},
]

def open_box(box_id: str) -> Dict:
    """فتح صندوق"""
    rewards = REWARDS.get(box_id, REWARDS["basic"])
    roll = random.random() * 100
    cumulative = 0

    for reward in rewards:
        cumulative += reward.get("chance", 0)
        if roll <= cumulative:
            rtype = reward["type"]

            if rtype == "points":
                return {"type": "points", "amount": random.randint(reward["min"], reward["max"])}
            elif rtype == "gems":
                return {"type": "gems", "amount": random.randint(reward["min"], reward["max"])}
            elif rtype == "item":
                return {"type": "item", "item": random.choice(ITEMS)}
            elif rtype == "title":
                return {"type": "title", "title": random.choice(TITLES)}
            elif rtype == "boost":
                return {"type": "boost", "boost": random.choice(BOOSTS)}
            elif rtype == "ton":
                return {"type": "ton", "amount": round(random.uniform(0.1, 1.0), 2)}

    return {"type": "points", "amount": 10}

# ==================== GAMES ====================
QUESTIONS = {
    "puzzle": [
        ("ما الذي يأتي مرة واحدة في الدقيقة ومرتين في القرن؟", "حرف الميم"),
        ("ما الذي يمشي بلا أرجل ويبكي بلا عيون؟", "الساعة"),
        ("ما هو الشيء الذي كلما زاد نقص؟", "العمر"),
        ("أوجد الرقم التالي: 1, 1, 2, 3, 5, 8, ...", "13"),
    ],
    "quiz": [
        ("ما عاصمة فرنسا؟", "باريس"),
        ("كم قارة في العالم؟", "7"),
        ("من مكتشف أمريكا؟", "كولومبوس"),
        ("ما أكبر كوكب؟", "المشتري"),
    ],
    "math": [
        ("5 + 7 × 2", "19"),
        ("12 × 12 - 44", "100"),
        ("100 ÷ 4 + 7", "32"),
    ],
}

# ==================== USER ====================
def get_user(user_id: int) -> Dict:
    users = db.users
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "points": 100,
            "gems": 0,
            "ton": 0,
            "games_played": 0,
            "games_won": 0,
            "streak": 0,
            "level": 1,
            "xp": 0,
            "inventory": {},
            "items": [],
            "titles": [],
            "boosts": [],
            "created_at": datetime.now().isoformat()
        }
        db.users = users

    return users[uid]

def update_user(user_id: int, data: Dict):
    users = db.users
    uid = str(user_id)
    if uid in users:
        users[uid].update(data)
        db.users = users

def add_points(user_id: int, amount: float) -> Tuple[bool, float]:
    """إضافة نقاط مع الاقتصاد"""
    success, net = Economy.mint(amount)
    if not success:
        return False, 0

    net, tax = Economy.apply_tax(net)
    user = get_user(user_id)
    user["points"] += net
    update_user(user_id, {"points": user["points"]})
    return True, net

def spend_points(user_id: int, amount: float) -> Tuple[bool, str]:
    """إنفاق النقاط"""
    user = get_user(user_id)
    if user["points"] < amount:
        return False, "نقاط غير كافية!"

    user["points"] -= amount
    update_user(user_id, {"points": user["points"]})
    return True, f"-{amount}"

# ==================== KEYBOARDS ====================
def main_keyboard(user_id: int):
    user = get_user(user_id)
    level = user.get("level", 1)

    keyboard = [
        [InlineKeyboardButton(f"💰 {user['points']:.0f} | lvl {level}", callback_data="profile")],
        [InlineKeyboardButton("🎮 الألعاب", callback_data="games_menu")],
        [InlineKeyboardButton("🎁 الصناديق", callback_data="boxes_menu")],
        [InlineKeyboardButton("💱 التبادل", callback_data="exchange_menu")],
        [InlineKeyboardButton("🏆 المتصدرين", callback_data="leaderboard")],
    ]
    return InlineKeyboardMarkup(keyboard)

def games_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 لغز", callback_data="game_puzzle"), InlineKeyboardButton("❓ سؤال", callback_data="game_quiz")],
        [InlineKeyboardButton("🔢 رياضيات", callback_data="game_math")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ])

def boxes_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 أساسي (50)", callback_data="buy_basic")],
        [InlineKeyboardButton("🥈 فضي (150)", callback_data="buy_silver")],
        [InlineKeyboardButton("🥇 ذهبي (500)", callback_data="buy_gold")],
        [InlineKeyboardButton("💎 ماسي (1500)", callback_data="buy_diamond")],
        [InlineKeyboardButton("🔥 أسطوري (5000)", callback_data="buy_mythic")],
        [InlineKeyboardButton("🎁 فتح", callback_data="open_box")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ])

def exchange_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 نقاط → TON", callback_data="ex_ton_buy")],
        [InlineKeyboardButton("💎 نقاط → جواهر", callback_data="ex_gems_buy")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    get_user(user.id)
    eco = db.economy

    await update.message.reply_text(
        f"🎮 CryptoPuzzle - المنصة الشاملة
"
        f"━━━━━━━━━━━━━━━━
"
        f"💰 نقاطك: {get_user(user.id)['points']:.0f}
"
        f"💎 جواهر: {get_user(user.id).get('gems', 0)}
"
        f"🪙 TON: {get_user(user.id).get('ton', 0):.2f}

"
        f"📊 الاقتصاد: {eco.get('supply', 0):.0f}/1,000,000

"
        f"اختر:",
        reply_markup=main_keyboard(user.id)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)

    # Profile
    if data == "profile":
        await query.edit_message_text(
            f"👤 ملفك
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 النقاط: {user['points']:.0f}
"
            f"💎 الجواهر: {user.get('gems', 0)}
"
            f"🪙 TON: {user.get('ton', 0):.2f}
"
            f"📊 المستوى: {user.get('level', 1)}
"
            f"🎮 الألعاب: {user.get('games_played', 0)}
"
            f"🏆 الانتصارات: {user.get('games_won', 0)}
"
            f"🔥 السلسلة: {user.get('streak', 0)}",
            reply_markup=back_keyboard()
        )

    # Games menu
    elif data == "games_menu":
        await query.edit_message_text(
            f"🎮 الألعاب
━━━━━━━━━━━━━━━━
اختر:",
            reply_markup=games_keyboard()
        )

    # Start game
    elif data.startswith("game_"):
        game_type = data.replace("game_", "")
        questions = QUESTIONS.get(game_type, QUESTIONS["puzzle"])
        q, a = random.choice(questions)

        context.user_data['current_question'] = (q, a)
        context.user_data['game_type'] = game_type

        await query.edit_message_text(
            f"🎮 {game_type}

❓ {q}",
            reply_markup=back_keyboard()
        )

    # Boxes menu
    elif data == "boxes_menu":
        await query.edit_message_text(
            f"🎁 الصناديق
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 نقاطك: {user['points']:.0f}

"
            f"اختر:",
            reply_markup=boxes_keyboard()
        )

    # Buy box
    elif data.startswith("buy_"):
        box_id = data.replace("buy_", "")
        box = BOXES.get(box_id)

        if box:
            success, msg = spend_points(user_id, box["price"])
            if success:
                inv = user.get("inventory", {})
                inv[box_id] = inv.get(box_id, 0) + 1
                update_user(user_id, {"inventory": inv})

                await query.answer(f"✅ اشتريت {box['name']}!", show_alert=True)
                user = get_user(user_id)
                await query.edit_message_text(
                    f"✅ تم!
{box['name']}

"
                    f"📦 في الحقيبة: {user['inventory'].get(box_id, 0)}",
                    reply_markup=boxes_keyboard()
                )
            else:
                await query.answer("⚠️ نقاط غير كافية!", show_alert=True)

    # Open box
    elif data == "open_box":
        inv = user.get("inventory", {})
        available = [k for k, v in inv.items() if v > 0]

        if not available:
            await query.answer("⚠️ لا تملك صناديق!", show_alert=True)
            return

        # Open first available
        box_id = available[0]
        box = BOXES[box_id]

        inv[box_id] -= 1
        update_user(user_id, {"inventory": inv})

        # Get reward
        reward = open_box(box_id)

        # Add reward
        if reward["type"] == "points":
            user["points"] += reward["amount"]
        elif reward["type"] == "gems":
            user["gems"] = user.get("gems", 0) + reward["amount"]
        elif reward["type"] == "item":
            items = user.get("items", [])
            items.append(reward["item"])
            user["items"] = items
        elif reward["type"] == "title":
            titles = user.get("titles", [])
            titles.append(reward["title"])
            user["titles"] = titles
        elif reward["type"] == "boost":
            boosts = user.get("boosts", [])
            boosts.append(reward["boost"])
            user["boosts"] = boosts
        elif reward["type"] == "ton":
            user["ton"] = user.get("ton", 0) + reward["amount"]

        user["boxes_opened"] = user.get("boxes_opened", 0) + 1
        update_user(user_id, user)

        # Update stats
        boxes = db.boxes
        boxes["stats"]["opened"] = boxes["stats"].get("opened", 0) + 1
        boxes["stats"]["spent"] = boxes["stats"].get("spent", 0) + box["price"]
        db.boxes = boxes

        # Show reward
        emojis = {"points": "💰", "gems": "💎", "item": "🎁", "title": "🏅", "boost": "⚡", "ton": "🪙"}
        emoji = emojis.get(reward["type"], "🎁")

        if reward["type"] == "points":
            msg = f"{emoji} {reward['amount']} نقطة"
        elif reward["type"] == "gems":
            msg = f"{emoji} {reward['amount']} جوهرة"
        elif reward["type"] == "item":
            msg = f"{emoji} {reward['item']['name']}"
        elif reward["type"] == "title":
            msg = f"{emoji} {reward['title']['emoji']} {reward['title']['name']}"
        elif reward["type"] == "boost":
            msg = f"{emoji} {reward['boost']['name']}"
        elif reward["type"] == "ton":
            msg = f"{emoji} {reward['amount']} TON"

        user = get_user(user_id)
        await query.edit_message_text(
            f"🎉 تهانينا!
"
            f"━━━━━━━━━━━━━━━━
"
            f"📦 {box['name']}

"
            f"🎁 {msg}

"
            f"💰 نقاط: {user['points']:.0f}",
            reply_markup=boxes_keyboard()
        )

    # Exchange menu
    elif data == "exchange_menu":
        await query.edit_message_text(
            f"💱 التبادل
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 نقاطك: {user['points']:.0f}
"
            f"💎 جوائرك: {user.get('gems', 0)}

"
            f"📊 الأسعار:
"
            f"• 1000 نقطة = 1 TON
"
            f"• 100 نقطة = 1 جوهرة

"
            f"اختر:",
            reply_markup=exchange_keyboard()
        )

    # Exchange
    elif data.startswith("ex_"):
        if data == "ex_ton_buy":
            cost = 1000
            if user["points"] >= cost:
                success, _ = spend_points(user_id, cost)
                if success:
                    update_user(user_id, {"ton": user.get("ton", 0) + 1})
                    await query.answer("✅ اشتريت 1 TON!", show_alert=True)
            else:
                await query.answer(f"⚠️ تحتاج {cost} نقطة!", show_alert=True)

        elif data == "ex_gems_buy":
            cost = 100
            if user["points"] >= cost:
                success, _ = spend_points(user_id, cost)
                if success:
                    update_user(user_id, {"gems": user.get("gems", 0) + 1})
                    await query.answer("✅ اشتريت 1 جوهرة!", show_alert=True)
            else:
                await query.answer(f"⚠️ تحتاج {cost} نقطة!", show_alert=True)

    # Leaderboard
    elif data == "leaderboard":
        users = db.users
        sorted_users = sorted(users.items(), key=lambda x: x[1].get("points", 0), reverse=True)[:10]

        text = "🏆 المتصدرين
━━━━━━━━━━━━━━━━
"
        for i, (uid, u) in enumerate(sorted_users, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            text += f"{medal} {u.get('points', 0):.0f} نقطة
"

        await query.edit_message_text(text, reply_markup=back_keyboard())

    # Back
    elif data == "back":
        await start(update, context)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    # Answer question
    if 'current_question' in context.user_data:
        q, correct = context.user_data['current_question']
        game_type = context.user_data.get('game_type', 'puzzle')

        if text.lower() == correct.lower():
            points = random.uniform(1, 5)
            success, amount = add_points(user_id, points)

            if success:
                streak = user.get("streak", 0) + 1
                update_user(user_id, {
                    "games_played": user.get("games_played", 0) + 1,
                    "games_won": user.get("games_won", 0) + 1,
                    "streak": streak,
                    "xp": user.get("xp", 0) + 10
                })

                # Level up
                xp = user.get("xp", 0) + 10
                level = xp // 100 + 1
                if level > user.get("level", 1):
                    update_user(user_id, {"level": level})

                await update.message.reply_text(
                    f"✅ إجابة صحيحة! +{amount:.1f} نقطة
🔥 سلسلة: {streak}",
                    reply_markup=main_keyboard(user_id)
                )
        else:
            update_user(user_id, {
                "games_played": user.get("games_played", 0) + 1,
                "streak": 0
            })
            await update.message.reply_text(
                f"❌ خطأ! الإجابة: {correct}",
                reply_markup=main_keyboard(user_id)
            )

        del context.user_data['current_question']
        return

    await update.message.reply_text(
        "🎮 اضغط /start للبدء!",
        reply_markup=main_keyboard(user_id)
    )

# ==================== MAIN ====================
def main():
    logger.info("🎮 Starting CryptoPuzzle Unified Platform...")

    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return

    app = Application.builder().token(Config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(message))

    logger.info("✅ CryptoPuzzle is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
