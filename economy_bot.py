"""
🎮 PvP Games Bot - الاقتصاد الرقمي المستدام
💰 نظام اقتصادي متوازن ضد التضخم
"""

import os
import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG - ECONOMY LIMITS ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")

    # 💰 ECONOMY -总量控制 (Total Supply Control)
    MAX_TOTAL_POINTS = 100000.0  # الحد الأقصى من النقاط في الاقتصاد
    INITIAL_SUPPLY = 10000.0     # التوريد الأولي

    # 🎮 EARNING LIMITS - حدود الكسب
    DAILY_EARN_LIMIT = 10.0      # максимальный الكسب اليومي
    GAME_WIN_POINTS = (0.5, 2.0) # نقاط الفوز (min, max)
    DAILY_BONUS = 5.0            # مكافأة يومية

    # 🏆 SPENDING - نقاط الصرف (Point Sinks)
    UPGRADE_COST = 50.0          # ترقية مستوى
    GIFT_COST = 10.0             # إرسال هدية
    BET_COST = 5.0               # رهان
    BOOST_COST = 20.0            # تعزيز

    # 🔥 DEFLATION - آليات الانكماش
    BURN_PERCENT = 0.05          # حرق 5% من كل معاملة
    TAX_PERCENT = 0.10           # ضريبة 10%

    # 📊 LEVEL REQUIREMENTS
    LEVEL_THRESHOLDS = [0, 10, 25, 50, 100, 200, 350, 500, 750, 1000]

    DB_PATH = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("PvPGamesBot")

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        os.makedirs(config.DB_PATH, exist_ok=True)
        self.economy_file = f"{config.DB_PATH}/economy.json"
        self.users_file = f"{config.DB_PATH}/users.json"
        self.market_file = f"{config.DB_PATH}/market.json"
        self._init_files()

    def _init_files(self):
        # Initialize economy stats
        if not os.path.exists(self.economy_file):
            self._save(self.economy_file, {
                "total_supply": config.INITIAL_SUPPLY,
                "burned_points": 0.0,
                "tax_collected": 0.0,
                "daily_minted": 0.0,
                "last_reset": datetime.now().strftime("%Y-%m-%d")
            })

        if not os.path.exists(self.users_file):
            self._save(self.users_file, {})

        if not os.path.exists(self.market_file):
            self._save(self.market_file, {"items": [], "bets": []})

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
    def economy(self):
        return self._load(self.economy_file)

    @economy.setter
    def economy(self, data):
        self._save(self.economy_file, data)

    @property
    def users(self):
        return self._load(self.users_file)

    @users.setter
    def users(self, data):
        self._save(self.users_file, data)

    @property
    def market(self):
        return self._load(self.market_file)

    @market.setter
    def market(self, data):
        self._save(self.market_file, data)

db = Database()

# ==================== ECONOMY FUNCTIONS ====================
def get_economy() -> Dict:
    return db.economy

def update_economy(data: Dict):
    eco = db.economy
    eco.update(data)
    db.economy = eco

def reset_daily_limits():
    """إعادة تعيين الحدود اليومية"""
    eco = db.economy
    today = datetime.now().strftime("%Y-%m-%d")

    if eco.get("last_reset") != today:
        eco["daily_minted"] = 0.0
        eco["last_reset"] = today
        db.economy = eco

def can_mint(amount: float) -> bool:
    """فحص إذا كان يمكن طباعة النقاط"""
    reset_daily_limits()
    eco = db.economy

    if eco["total_supply"] + amount > config.MAX_TOTAL_POINTS:
        return False
    if eco["daily_minted"] + amount > config.DAILY_EARN_LIMIT * 10:  # 10x daily limit buffer
        return False
    return True

def mint_points(amount: float) -> Tuple[bool, float]:
    """طباعة نقاط مع حرق جزء"""
    if not can_mint(amount):
        return False, 0

    # حرق جزء من النقاط
    burn_amount = amount * config.BURN_PERCENT
    actual_amount = amount - burn_amount

    eco = db.economy
    eco["total_supply"] = eco.get("total_supply", 0) + actual_amount
    eco["burned_points"] = eco.get("burned_points", 0) + burn_amount
    eco["daily_minted"] = eco.get("daily_minted", 0) + amount
    db.economy = eco

    return True, actual_amount

def burn_points(amount: float):
    """حرق النقاط"""
    eco = db.economy
    eco["total_supply"] = max(0, eco.get("total_supply", 0) - amount)
    eco["burned_points"] = eco.get("burned_points", 0) + amount
    db.economy = eco

def apply_tax(amount: float) -> Tuple[float, float]:
    """تطبيق الضريبة"""
    tax = amount * config.TAX_PERCENT
    net = amount - tax

    eco = db.economy
    eco["tax_collected"] = eco.get("tax_collected", 0) + tax
    db.economy = eco

    return net, tax

# ==================== LEVELS ====================
def get_level(points: float) -> Tuple[int, str, float, float]:
    """حساب المستوى"""
    levels = [
        (1, "مبتدئ", 0, 10),
        (2, "لاعب", 10, 25),
        (3, "محترف", 25, 50),
        (4, "خبير", 50, 100),
        (5, "أستاذ", 100, 200),
        (6, "موهوب", 200, 350),
        (7, "أسطورة", 350, 500),
        (8, "بطل", 500, 750),
        (9, "محقق", 750, 1000),
        (10, "ملك", 1000, 999999),
    ]
    for level, name, min_p, max_p in levels:
        if points < max_p:
            return level, name, min_p, max_p
    return 10, "ملك", 1000, 999999

# ==================== USER FUNCTIONS ====================
def get_user(user_id: int) -> Dict:
    users = db.users
    uid = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if uid not in users:
        # Give initial points (from initial supply)
        initial = config.INITIAL_SUPPLY / 100  # 1% of initial supply per user
        users[uid] = {
            "user_id": user_id,
            "points": initial,
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "streak": 0,
            "best_streak": 0,
            "level": 1,
            "daily_earned": 0.0,
            "daily_limit": config.DAILY_EARN_LIMIT,
            "daily_claimed": "",
            "hints": 3,
            "created_at": datetime.now().isoformat(),
            "last_play": ""
        }
        db.users = users
    return users[uid]

def update_user(user_id: int, data: Dict):
    users = db.users
    uid = str(user_id)
    if uid in users:
        users[uid].update(data)
        db.users = users

def can_earn(user_id: int, amount: float) -> bool:
    """فحص إذا كان المستخدم يمكنه الكسب"""
    user = get_user(user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if user.get("last_play") != today:
        user["daily_earned"] = 0
        user["last_play"] = today

    return user.get("daily_earned", 0) + amount <= user.get("daily_limit", config.DAILY_EARN_LIMIT)

def add_points(user_id: int, amount: float, reason: str = "") -> Tuple[bool, float, str]:
    """إضافة نقاط مع فحص الاقتصاد"""
    user = get_user(user_id)

    if not can_earn(user_id, amount):
        return False, 0, "⚠️ وصلت للحد اليومي!"

    # طباعة النقاط من الاقتصاد
    success, actual = mint_points(amount)
    if not success:
        return False, 0, "⚠️ الاقتصاد مشبّع! لا يمكن طباعة المزيد."

    # تطبيق الضريبة
    net, tax = apply_tax(actual)

    # تحديث المستخدم
    new_points = user["points"] + net
    daily_earned = user.get("daily_earned", 0) + amount

    update_user(user_id, {
        "points": new_points,
        "daily_earned": daily_earned
    })

    return True, net, f"+{net:.2f} نقطة {reason}"

def spend_points(user_id: int, amount: float, reason: str = "") -> Tuple[bool, str]:
    """إنفاق النقاط مع حرق"""
    user = get_user(user_id)

    if user["points"] < amount:
        return False, "⚠️ نقاط غير كافية!"

    # حرق جزء من المبلغ
    burn = amount * config.BURN_PERCENT
    net_spend = amount - burn

    new_points = user["points"] - amount
    burn_points(burn)

    update_user(user_id, {"points": new_points})

    return True, f"-{amount:.2f} نقطة {reason} (حرق: {burn:.2f})"

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
    ],
}

# ==================== KEYBOARDS ====================
def main_keyboard(user_id: int):
    user = get_user(user_id)
    level, name, min_p, max_p = get_level(user['points'])
    eco = get_economy()

    keyboard = [
        [InlineKeyboardButton(f"💰 {user['points']:.1f} | lvl {level} {name}", callback_data="profile")],
        [InlineKeyboardButton(f"📈 الاقتصاد: {eco['total_supply']:.0f}/{config.MAX_TOTAL_POINTS:.0f}", callback_data="economy")],
        [InlineKeyboardButton("❓ سؤال", callback_data="play_عام"), InlineKeyboardButton("🔢 رياضيات", callback_data="play_رياضيات")],
        [InlineKeyboardButton("🎁 مكافأة", callback_data="daily"), InlineKeyboardButton("💡 تلميح", callback_data="hint")],
        [InlineKeyboardButton("🎰 السوق", callback_data="market"), InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
        [InlineKeyboardButton("🏆 المتصدرين", callback_data="leaderboard"), InlineKeyboardButton("💳 الصرف", callback_data="spend")],
    ]
    return InlineKeyboardMarkup(keyboard)

def spend_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⬆️ ترقية ({config.UPGRADE_COST})", callback_data="spend_upgrade")],
        [InlineKeyboardButton(f"🎁 هدية ({config.GIFT_COST})", callback_data="spend_gift")],
        [InlineKeyboardButton(f"🎯 رهان ({config.BET_COST})", callback_data="spend_bet")],
        [InlineKeyboardButton(f"🚀 تعزيز ({config.BOOST_COST})", callback_data="spend_boost")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    get_user(user.id)
    eco = get_economy()

    await update.message.reply_text(
        f"⚔️ مرحباً {user.first_name}!

"
        f"💰 الاقتصاد الرقمي المستدام
"
        f"━━━━━━━━━━━━━━━━
"
        f"📊 إجمالي النقاط: {eco['total_supply']:.0f}/{config.MAX_TOTAL_POINTS:.0f}
"
        f"🔥 النقاط المحترقة: {eco['burned_points']:.1f}
"
        f"💵 الضرائب: {eco['tax_collected']:.1f}

"
        f"🎮 النظام:
"
        f"• الكسب اليومي: {config.DAILY_EARN_LIMIT}
"
        f"• حرق المعاملات: {config.BURN_PERCENT*100}%
"
        f"• ضريبة: {config.TAX_PERCENT*100}%",
        reply_markup=main_keyboard(user.id)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)
    eco = get_economy()

    # Economy stats
    if data == "economy":
        supply_percent = (eco['total_supply'] / config.MAX_TOTAL_POINTS) * 100
        await query.edit_message_text(
            f"📊 حالة الاقتصاد
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 التوريد: {eco['total_supply']:.0f}/{config.MAX_TOTAL_POINTS:.0f}
"
            f"📈 النسبة: {supply_percent:.1f}%
"
            f"🔥 محترق: {eco['burned_points']:.1f}
"
            f"💵 ضرائب: {eco['tax_collected']:.1f}
"
            f"📅 اليومي: {eco['daily_minted']:.1f}

"
            f"{'🟢 اقتصاد صحي' if supply_percent < 70 else '🟡 اقترب من التشبع' if supply_percent < 90 else '🔴 اقتصاد مشبع'}",
            reply_markup=back_keyboard()
        )

    # Profile
    elif data == "profile":
        level, name, min_p, max_p = get_level(user['points'])
        progress = (user['points'] - min_p) / (max_p - min_p) * 100 if max_p != 999999 else 100
        today = datetime.now().strftime("%Y-%m-%d")
        daily_left = user.get("daily_limit", config.DAILY_EARN_LIMIT) - user.get("daily_earned", 0)

        await query.edit_message_text(
            f"👤 ملفك
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 النقاط: {user['points']:.2f}
"
            f"📊 المستوى: {level} - {name}
"
            f"📈 التقدم: {progress:.0f}%
"
            f"🎮 لعبت: {user['games_played']}
"
            f"🏆 فزت: {user['games_won']}
"
            f"🔥 السلسلة: {user['streak']}
"
            f"📅 الكسب المتبقي: {daily_left:.1f}",
            reply_markup=back_keyboard()
        )

    # Stats
    elif data == "stats":
        win_rate = (user['games_won'] / user['games_played'] * 100) if user['games_played'] > 0 else 0
        await query.edit_message_text(
            f"📊 الإحصائيات
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 النقاط: {user['points']:.2f}
"
            f"🎮 الألعاب: {user['games_played']}
"
            f"🏆 الانتصارات: {user['games_won']}
"
            f"❌ الخسارات: {user['games_lost']}
"
            f"📈 نسبة الفوز: {win_rate:.1f}%
"
            f"🔥 أفضل سلسلة: {user['best_streak']}",
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
            text += f"{medal} {u['points']:.1f} نقطة
"

        await query.edit_message_text(text, reply_markup=back_keyboard())

    # Daily bonus
    elif data == "daily":
        today = datetime.now().strftime("%Y-%m-%d")
        last_claim = user.get("daily_claimed", "")

        if last_claim == today:
            await query.answer("⚠️ Already claimed today!", show_alert=True)
        else:
            success, amount, msg = add_points(user_id, config.DAILY_BONUS, "(مكافأة)")
            if success:
                update_user(user_id, {'daily_claimed': today})
                await query.answer(f"🎁 +{amount:.2f}!", show_alert=True)
                user = get_user(user_id)
                await query.edit_message_text(
                    f"✅ مكافأة يومية!

+{amount:.2f} نقطة

💰 رصيدك: {user['points']:.2f}",
                    reply_markup=back_keyboard()
                )
            else:
                await query.answer(msg, show_alert=True)

    # Hint
    elif data == "hint":
        hints = user.get('hints', 3)
        if hints <= 0:
            await query.answer("⚠️ لا توجد تلميحات!", show_alert=True)
        elif 'current_question' not in context.user_data:
            await query.answer("⚠️ لست في لعبة!", show_alert=True)
        else:
            q, correct = context.user_data['current_question']
            hint = correct[0] + "?" * (len(correct) - 1)
            update_user(user_id, {'hints': hints - 1})
            await query.edit_message_text(
                f"💡 التلميح: {hint}

السؤال: {q}",
                reply_markup=back_keyboard()
            )

    # Market
    elif data == "market":
        await query.edit_message_text(
            f"🎰 السوق
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 رصيدك: {user['points']:.2f}

"
            f"• رهان: {config.BET_COST} نقطة
"
            f"• ترقية: {config.UPGRADE_COST} نقطة
"
            f"• تعزيز: {config.BOOST_COST} نقطة

"
            f"💡 اضغط على الزر للشراء!",
            reply_markup=spend_keyboard()
        )

    # Spend options
    elif data == "spend":
        await query.edit_message_text(
            f"💳 الصرف والنفقات
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 رصيدك: {user['points']:.2f}

"
            f"🔥 حرق {config.BURN_PERCENT*100}% من كل عملية!

"
            f"اختر:",
            reply_markup=spend_keyboard()
        )

    elif data.startswith("spend_"):
        action = data.replace("spend_", "")
        costs = {"upgrade": config.UPGRADE_COST, "gift": config.GIFT_COST, "bet": config.BET_COST, "boost": config.BOST_COST}
        cost = costs.get(action, 10)

        success, msg = spend_points(user_id, cost, f"({action})")
        if success:
            await query.answer(msg, show_alert=True)
            user = get_user(user_id)
            await query.edit_message_text(
                f"✅ تم!

{msg}

💰 الرصيد: {user['points']:.2f}",
                reply_markup=back_keyboard()
            )
        else:
            await query.answer(msg, show_alert=True)

    # Play game
    elif data.startswith("play_"):
        category = data.replace("play_", "")
        q_list = QUESTIONS.get(category, QUESTIONS["عام"])
        q, a = random.choice(q_list)

        context.user_data['current_question'] = (q, a)
        context.user_data['category'] = category

        await query.edit_message_text(
            f"🎮 {category}

❓ {q}

أرسل إجابتك!",
            reply_markup=back_keyboard()
        )

    # Back
    elif data == "back":
        await query.edit_message_text(
            f"⚔️ القائمة الرئيسية

💰 رصيدك: {user['points']:.2f}",
            reply_markup=main_keyboard(user_id)
        )

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    # Answer question
    if 'current_question' in context.user_data:
        q, correct = context.user_data['current_question']

        if text.lower() == correct.lower():
            # Calculate points with random
            points = round(random.uniform(*config.GAME_WIN_POINTS), 2)

            success, amount, msg = add_points(user_id, points, "(فوز)")

            if success:
                new_streak = user['streak'] + 1
                update_user(user_id, {
                    'games_played': user['games_played'] + 1,
                    'games_won': user['games_won'] + 1,
                    'streak': new_streak,
                    'best_streak': max(user['best_streak'], new_streak)
                })

                await update.message.reply_text(
                    f"✅ إجابة صحيحة!
{msg}
🔥 سلسلة: {new_streak}",
                    reply_markup=main_keyboard(user_id)
                )
            else:
                await update.message.reply_text(msg, reply_markup=main_keyboard(user_id))
        else:
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
    logger.info("💰 Starting PvP Games Bot with Sustainable Economy...")

    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(message))

    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
