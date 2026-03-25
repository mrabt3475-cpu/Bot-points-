"""
🎮 PvP Games Bot - نظام تبادل النقاط
💱 Exchange System: نقاط <-> عملات <-> هدايا
"""

import os
import json
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")

    # Economy
    MAX_TOTAL_POINTS = 100000.0
    INITIAL_SUPPLY = 10000.0
    DAILY_EARN_LIMIT = 10.0
    GAME_WIN_POINTS = (0.5, 2.0)
    DAILY_BONUS = 5.0

    # Exchange Rates (Points to other currencies)
    POINTS_TO_TON = 1000  # 1000 points = 1 TON (mock)
    POINTS_TO_USDT = 100  # 100 points = 1 USDT (mock)
    POINTS_TO_GIFT = 50   # 50 points = 1 gift

    # Trading Fees
    TRADE_FEE_PERCENT = 2.0
    EXCHANGE_FEE_PERCENT = 1.0

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
        self.trades_file = f"{config.DB_PATH}/trades.json"
        self.exchange_file = f"{config.DB_PATH}/exchange.json"
        self._init_files()

    def _init_files(self):
        defaults = {
            self.economy_file: {
                "total_supply": config.INITIAL_SUPPLY,
                "burned_points": 0.0,
                "tax_collected": 0.0,
                "daily_minted": 0.0,
                "last_reset": datetime.now().strftime("%Y-%m-%d")
            },
            self.trades_file: {"active_trades": [], "trade_history": []},
            self.exchange_file: {"orders": [], "history": []}
        }

        for path, data in defaults.items():
            if not os.path.exists(path):
                self._save(path, data)

        if not os.path.exists(self.users_file):
            self._save(self.users_file, {})

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
    def trades(self):
        return self._load(self.trades_file)

    @trades.setter
    def trades(self, data):
        self._save(self.trades_file, data)

    @property
    def exchange(self):
        return self._load(self.exchange_file)

    @exchange.setter
    def exchange(self, data):
        self._save(self.exchange_file, data)

db = Database()

# ==================== ECONOMY FUNCTIONS ====================
def get_economy() -> Dict:
    return db.economy

def update_economy(data: Dict):
    eco = db.economy
    eco.update(data)
    db.economy = eco

def reset_daily_limits():
    eco = db.economy
    today = datetime.now().strftime("%Y-%m-%d")
    if eco.get("last_reset") != today:
        eco["daily_minted"] = 0.0
        eco["last_reset"] = today
        db.economy = eco

def can_mint(amount: float) -> bool:
    reset_daily_limits()
    eco = db.economy
    return eco["total_supply"] + amount <= config.MAX_TOTAL_POINTS

def mint_points(amount: float) -> Tuple[bool, float]:
    if not can_mint(amount):
        return False, 0

    burn = amount * 0.05
    actual = amount - burn

    eco = db.economy
    eco["total_supply"] = eco.get("total_supply", 0) + actual
    eco["burned_points"] = eco.get("burned_points", 0) + burn
    eco["daily_minted"] = eco.get("daily_minted", 0) + amount
    db.economy = eco

    return True, actual

def burn_points(amount: float):
    eco = db.economy
    eco["total_supply"] = max(0, eco.get("total_supply", 0) - amount)
    eco["burned_points"] = eco.get("burned_points", 0) + amount
    db.economy = eco

def apply_tax(amount: float) -> Tuple[float, float]:
    tax = amount * config.EXCHANGE_FEE_PERCENT / 100
    net = amount - tax
    eco = db.economy
    eco["tax_collected"] = eco.get("tax_collected", 0) + tax
    db.economy = eco
    return net, tax

# ==================== USER FUNCTIONS ====================
def get_user(user_id: int) -> Dict:
    users = db.users
    uid = str(user_id)
    today = datetime.now().strftime("%Y-%m-%d")

    if uid not in users:
        initial = config.INITIAL_SUPPLY / 100
        users[uid] = {
            "user_id": user_id,
            "points": initial,
            "ton_balance": 0.0,
            "usdt_balance": 0.0,
            "gifts": [],
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "streak": 0,
            "best_streak": 0,
            "daily_earned": 0.0,
            "daily_claimed": "",
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
    user = get_user(user_id)
    if not can_mint(amount):
        return False, 0

    success, actual = mint_points(amount)
    if not success:
        return False, 0

    net, tax = apply_tax(actual)
    new_points = user["points"] + net

    update_user(user_id, {"points": new_points})
    return True, net

def spend_points(user_id: int, amount: float) -> Tuple[bool, str]:
    user = get_user(user_id)
    if user["points"] < amount:
        return False, "نقاط غير كافية!"

    burn = amount * 0.05
    new_points = user["points"] - amount
    burn_points(burn)

    update_user(user_id, {"points": new_points})
    return True, f"-{amount:.2f} (حرق: {burn:.2f})"

# ==================== EXCHANGE SYSTEM ====================
class ExchangeSystem:
    """نظام التبادل"""

    @staticmethod
    def create_trade(sender_id: int, receiver_id: int, amount: float, 
                     want_amount: float, want_currency: str) -> str:
        """إنشاء صفقة تبادل"""
        trade_id = f"TRADE_{random.randint(10000, 99999)}"

        trades = db.trades
        trade = {
            "id": trade_id,
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "offer_amount": amount,
            "offer_currency": "points",
            "want_amount": want_amount,
            "want_currency": want_currency,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }

        trades["active_trades"].append(trade)
        db.trades = trades

        return trade_id

    @staticmethod
    def accept_trade(trade_id: str, user_id: int) -> Tuple[bool, str]:
        """قبول صفقة"""
        trades = db.trades

        for trade in trades["active_trades"]:
            if trade["id"] == trade_id and trade["receiver_id"] == user_id:
                if trade["status"] != "pending":
                    return False, "الصفقة منتهية!"

                sender = get_user(trade["sender_id"])
                receiver = get_user(user_id)

                # Check balances
                if receiver["points"] < trade["want_amount"]:
                    return False, "نقاط غير كافية!"

                # Execute trade
                sender["points"] += trade["offer_amount"]
                receiver["points"] -= trade["want_amount"]

                # Fee
                fee = trade["offer_amount"] * config.TRADE_FEE_PERCENT / 100
                burn_points(fee)

                trade["status"] = "completed"
                trades["history"].append(trade)
                trades["active_trades"].remove(trade)

                db.users = {str(sender["user_id"]): sender, str(receiver["user_id"]): receiver}
                db.trades = trades

                return True, f"✅ تم التبادل!
+{trade['offer_amount']} نقطة
-{trade['want_amount']} نقطة"

        return False, "الصفقة غير موجودة!"

    @staticmethod
    def create_exchange_order(user_id: int, from_amount: float, from_curr: str,
                              to_amount: float, to_curr: str) -> str:
        """إنشاء أمر صرف"""
        order_id = f"EX_{random.randint(10000, 99999)}"

        exchange = db.exchange
        order = {
            "id": order_id,
            "user_id": user_id,
            "from_amount": from_amount,
            "from_currency": from_curr,
            "to_amount": to_amount,
            "to_currency": to_curr,
            "status": "open",
            "created_at": datetime.now().isoformat()
        }

        exchange["orders"].append(order)
        db.exchange = exchange

        return order_id

    @staticmethod
    def execute_exchange(order_id: str, user_id: int) -> Tuple[bool, str]:
        """تنفيذ أمر الصرف"""
        exchange = db.exchange

        for order in exchange["orders"]:
            if order["id"] == order_id and order["user_id"] != user_id:
                if order["status"] != "open":
                    return False, "الأمر منتهي!"

                user = get_user(user_id)
                order_user = get_user(order["user_id"])

                # Check if user has the currency
                from_currency = order["from_currency"]
                user_balance = user.get(f"{from_currency}_balance", 0) if from_currency != "points" else user["points"]

                if user_balance < order["from_amount"]:
                    return False, "رصيد غير كافٍ!"

                # Execute exchange
                if from_currency == "points":
                    user["points"] -= order["from_amount"]
                    order_user["points"] += order["to_amount"]
                elif to_currency == "points":
                    user[f"{from_currency}_balance"] -= order["from_amount"]
                    order_user["points"] += order["to_amount"]
                else:
                    user[f"{from_currency}_balance"] -= order["from_amount"]
                    order_user[f"{to_currency}_balance"] += order["to_amount"]

                order["status"] = "filled"
                order["filled_by"] = user_id
                exchange["history"].append(order)
                exchange["orders"].remove(order)

                db.users = {str(user["user_id"]): user, str(order_user["user_id"]): order_user}
                db.exchange = exchange

                return True, f"✅ تم الصرف!
{order['from_amount']} {from_currency} → {order['to_amount']} {to_currency}"

        return False, "الأمر غير موجود!"

# ==================== LEVELS ====================
def get_level(points: float) -> Tuple[int, str]:
    levels = [(1,"مبتدئ",0,10),(2,"لاعب",10,25),(3,"محترف",25,50),(4,"خبير",50,100),
              (5,"أستاذ",100,200),(6,"موهوب",200,350),(7,"أسطورة",350,500),
              (8,"بطل",500,750),(9,"محقق",750,1000),(10,"ملك",1000,999999)]
    for level, name, min_p, max_p in levels:
        if points < max_p:
            return level, name
    return 10, "ملك"

# ==================== GAMES ====================
QUESTIONS = {
    "عام": [("ما عاصمة فرنسا؟","باريس"),("من مكتشف أمريكا؟","كولومبوس"),("ما أكبر كوكب؟","المشتري")],
    "رياضيات": [("5 + 8 × 2","21"),("10 + 5 × 3","25"),("100 ÷ 4 + 7","32")],
}

# ==================== KEYBOARDS ====================
def main_keyboard(user_id: int):
    user = get_user(user_id)
    level, name = get_level(user['points'])

    keyboard = [
        [InlineKeyboardButton(f"💰 {user['points']:.1f} | lvl {level}", callback_data="profile")],
        [InlineKeyboardButton(f"💵 TON: {user.get('ton_balance', 0):.2f} | USDT: {user.get('usdt_balance', 0):.2f}", callback_data="wallets")],
        [InlineKeyboardButton("❓ سؤال", callback_data="play_عام"), InlineKeyboardButton("🔢 رياضيات", callback_data="play_رياضيات")],
        [InlineKeyboardButton("🔄 تبادل", callback_data="exchange"), InlineKeyboardButton("📜 صفقاتي", callback_data="my_trades")],
        [InlineKeyboardButton("💱 سوق الصرف", callback_data="market"), InlineKeyboardButton("🎁 الهدايا", callback_data="gifts")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), InlineKeyboardButton("🏆 المتصدرين", callback_data="leaderboard")],
    ]
    return InlineKeyboardMarkup(keyboard)

def exchange_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 إرسال نقاط", callback_data="send_points")],
        [InlineKeyboardButton("🔃 تحويل عملات", callback_data="convert")],
        [InlineKeyboardButton("🎫 إنشاء صفقة", callback_data="create_trade")],
        [InlineKeyboardButton("📥 قبول صفقة", callback_data="accept_trade")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ])

def market_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 نقاط → TON", callback_data="buy_ton")],
        [InlineKeyboardButton("💰 نقاط → USDT", callback_data="buy_usdt")],
        [InlineKeyboardButton("💎 TON → نقاط", callback_data="sell_ton")],
        [InlineKeyboardButton("💵 USDT → نقاط", callback_data="sell_usdt")],
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
        f"💱 نظام تبادل النقاط
"
        f"━━━━━━━━━━━━━━━━
"
        f"💰 نقاطك: {get_user(user.id)['points']:.2f}
"
        f"💵 TON: {get_user(user.id).get('ton_balance', 0):.2f}
"
        f"💵 USDT: {get_user(user.id).get('usdt_balance', 0):.2f}

"
        f"📊 الاقتصاد: {eco['total_supply']:.0f}/{config.MAX_TOTAL_POINTS:.0f}",
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
        level, name = get_level(user['points'])
        await query.edit_message_text(
            f"👤 ملفك
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 النقاط: {user['points']:.2f}
"
            f"📊 المستوى: {level} - {name}
"
            f"💵 TON: {user.get('ton_balance', 0):.2f}
"
            f"💵 USDT: {user.get('usdt_balance', 0):.2f}
"
            f"🎮 الألعاب: {user['games_played']}
"
            f"🏆 الانتصارات: {user['games_won']}",
            reply_markup=back_keyboard()
        )

    # Wallets
    elif data == "wallets":
        await query.edit_message_text(
            f"💳 محافظك
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 نقاط: {user['points']:.2f}
"
            f"━━━━━━━━━━━━━━━━
"
            f"💵 TON: {user.get('ton_balance', 0):.2f}
"
            f"   = {user.get('ton_balance', 0) * config.POINTS_TO_TON} نقطة
"
            f"💵 USDT: {user.get('usdt_balance', 0):.2f}
"
            f"   = {user.get('usdt_balance', 0) * config.POINTS_TO_USDT} نقطة

"
            f"💡 1 TON = {config.POINTS_TO_TON} نقطة
"
            f"💡 1 USDT = {config.POINTS_TO_USDT} نقطة",
            reply_markup=back_keyboard()
        )

    # Exchange menu
    elif data == "exchange":
        await query.edit_message_text(
            f"🔄 نظام التبادل
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 رصيدك: {user['points']:.2f}

"
            f"📤 إرسال نقاط لصديق
"
            f"🔃 تحويل بين العملات
"
            f"🎫 إنشاء/قبول صفقة

"
            f"�_fee: {config.TRADE_FEE_PERCENT}%",
            reply_markup=exchange_keyboard()
        )

    # Market
    elif data == "market":
        await query.edit_message_text(
            f"💱 سوق الصرف
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 رصيدك: {user['points']:.2f}

"
            f"💰 شراء:
"
            f"• نقاط → TON: {config.POINTS_TO_TON}:1
"
            f"• نقاط → USDT: {config.POINTS_TO_USDT}:1

"
            f"💎 بيع:
"
            f"• TON → نقاط: 1:{config.POINTS_TO_TON}
"
            f"• USDT → نقاط: 1:{config.POINTS_TO_USDT}

"
            f"�_fee: {config.EXCHANGE_FEE_PERCENT}%",
            reply_markup=market_keyboard()
        )

    # Buy/Sell
    elif data == "buy_ton":
        cost = config.POINTS_TO_TON
        if user['points'] >= cost:
            success, msg = spend_points(user_id, cost)
            if success:
                update_user(user_id, {'ton_balance': user.get('ton_balance', 0) + 1})
                await query.answer("✅ اشتريت 1 TON!", show_alert=True)
        else:
            await query.answer(f"⚠️ تحتاج {cost} نقطة!", show_alert=True)

    elif data == "buy_usdt":
        cost = config.POINTS_TO_USDT
        if user['points'] >= cost:
            success, msg = spend_points(user_id, cost)
            if success:
                update_user(user_id, {'usdt_balance': user.get('usdt_balance', 0) + 1})
                await query.answer("✅ اشتريت 1 USDT!", show_alert=True)
        else:
            await query.answer(f"⚠️ تحتاج {cost} نقطة!", show_alert=True)

    elif data == "sell_ton":
        if user.get('ton_balance', 0) >= 1:
            update_user(user_id, {'ton_balance': user.get('ton_balance', 0) - 1})
            add_points(user_id, config.POINTS_TO_TON)
            await query.answer(f"✅ بعت 1 TON مقابل {config.POINTS_TO_TON} نقطة!", show_alert=True)
        else:
            await query.answer("⚠️ لا تملك TON!", show_alert=True)

    elif data == "sell_usdt":
        if user.get('usdt_balance', 0) >= 1:
            update_user(user_id, {'usdt_balance': user.get('usdt_balance', 0) - 1})
            add_points(user_id, config.POINTS_TO_USDT)
            await query.answer(f"✅ بعت 1 USDT مقابل {config.POINTS_TO_USDT} نقطة!", show_alert=True)
        else:
            await query.answer("⚠️ لا تملك USDT!", show_alert=True)

    # My trades
    elif data == "my_trades":
        trades = db.trades
        user_trades = [t for t in trades["active_trades"] if t["sender_id"] == user_id or t["receiver_id"] == user_id]

        if user_trades:
            text = "📜 صفقاتك النشطة
━━━━━━━━━━━━━━━━
"
            for t in user_trades:
                text += f"🆔 {t['id']}
"
                text += f"📤 {t['offer_amount']} نقاط
"
                text += f"📥 {t['want_amount']} {t['want_currency']}
"
                text += f"📊 {t['status']}

"
        else:
            text = "📜 لا توجد صفقات نشطة"

        await query.edit_message_text(text, reply_markup=back_keyboard())

    # Create trade
    elif data == "create_trade":
        await query.edit_message_text(
            "🎫 إنشاء صفقة

"
            "أرسل بالشكل:
"
            "`تبادل 50 نقاط إلى 123456 مقابل 25 نقاط`

"
            "أو استخدم:
"
            "`صفقة 50 25`",
            reply_markup=back_keyboard()
        )
        context.user_data['waiting_for_trade'] = True

    # Gifts
    elif data == "gifts":
        gifts = user.get('gifts', [])
        await query.edit_message_text(
            f"🎁 هداياك
"
            f"━━━━━━━━━━━━━━━━
"
            f"عدد الهدايا: {len(gifts)}

"
            f"💡 ارسل: `هدية 10` لإرسال هدية
"
            f"   التكلفة: {config.POINTS_TO_GIFT} نقطة",
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
            f"📈 نسبة الفوز: {win_rate:.1f}%",
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

    # Play game
    elif data.startswith("play_"):
        category = data.replace("play_", "")
        q_list = QUESTIONS.get(category, QUESTIONS["عام"])
        q, a = random.choice(q_list)

        context.user_data['current_question'] = (q, a)

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

    # Trade creation
    if context.user_data.get('waiting_for_trade'):
        try:
            parts = text.split()
            if len(parts) >= 2:
                offer = float(parts[0])
                want = float(parts[1])

                if user['points'] >= offer:
                    trade_id = ExchangeSystem.create_trade(
                        user_id, 0, offer, want, "points"
                    )
                    await update.message.reply_text(
                        f"✅ تم إنشاء الصفقة!

"
                        f"🆔 {trade_id}
"
                        f"📤 عرض: {offer} نقاط
"
                        f"📥 طلب: {want} نقاط

"
                        f"شارك هذا الرقم مع صديقك!",
                        reply_markup=main_keyboard(user_id)
                    )
                else:
                    await update.message.reply_text("⚠️ نقاط غير كافية!", reply_markup=main_keyboard(user_id))
            else:
                await update.message.reply_text("⚠️ الصيغة: `50 25`", reply_markup=main_keyboard(user_id))
        except:
            await update.message.reply_text("⚠️ خطأ في الصيغة!", reply_markup=main_keyboard(user_id))

        context.user_data['waiting_for_trade'] = False
        return

    # Accept trade
    if text.startswith("قبول "):
        trade_id = text.replace("قبول ", "").strip()
        success, msg = ExchangeSystem.accept_trade(trade_id, user_id)
        await update.message.reply_text(msg, reply_markup=main_keyboard(user_id))
        return

    # Send points
    if text.startswith("إرسال "):
        try:
            parts = text.replace("إرسال ", "").split()
            amount = float(parts[0])
            receiver_id = int(parts[1]) if len(parts) > 1 else 0

            if receiver_id > 0 and user['points'] >= amount:
                success, msg = spend_points(user_id, amount)
                if success:
                    receiver = get_user(receiver_id)
                    add_points(receiver_id, amount)
                    await update.message.reply_text(
                        f"✅ أرسلت {amount} نقطة للمستخدم {receiver_id}",
                        reply_markup=main_keyboard(user_id)
                    )
            else:
                await update.message.reply_text("⚠️ خطأ!", reply_markup=main_keyboard(user_id))
        except:
            await update.message.reply_text("⚠️ الصيغة: `إرسال 10 123456`", reply_markup=main_keyboard(user_id))
        return

    # Gift
    if text.startswith("هدية "):
        try:
            amount = float(text.replace("هدية ", ""))
            cost = config.POINTS_TO_GIFT

            if user['points'] >= cost:
                success, msg = spend_points(user_id, cost)
                if success:
                    gifts = user.get('gifts', [])
                    gifts.append({"amount": amount, "date": datetime.now().isoformat()})
                    update_user(user_id, {'gifts': gifts})
                    await update.message.reply_text(
                        f"✅ أرسلت هدية بـ {cost} نقطة!",
                        reply_markup=main_keyboard(user_id)
                    )
            else:
                await update.message.reply_text(f"⚠️ تحتاج {cost} نقطة!", reply_markup=main_keyboard(user_id))
        except:
            await update.message.reply_text("⚠️ الصيغة: `هدية 10`", reply_markup=main_keyboard(user_id))
        return

    # Answer question
    if 'current_question' in context.user_data:
        q, correct = context.user_data['current_question']

        if text.lower() == correct.lower():
            points = round(random.uniform(*config.GAME_WIN_POINTS), 2)
            success, amount = add_points(user_id, points)

            if success:
                new_streak = user['streak'] + 1
                update_user(user_id, {
                    'games_played': user['games_played'] + 1,
                    'games_won': user['games_won'] + 1,
                    'streak': new_streak,
                    'best_streak': max(user['best_streak'], new_streak)
                })

                await update.message.reply_text(
                    f"✅ إجابة صحيحة! +{amount:.2f} نقطة
🔥 سلسلة: {new_streak}",
                    reply_markup=main_keyboard(user_id)
                )
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
    logger.info("💱 Starting PvP Games Bot with Exchange System...")

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
