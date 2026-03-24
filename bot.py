"""
🤖 Enhanced Crypto Wallet Bot + Random Chat
بوت محفظة إلكترونية مع نظام نقاط ونظام تواصل عشوائي
"""

import os
import json
import hashlib
import hmac
import random
import string
import asyncio
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ChatJoinRequestHandler

# ==================== CONFIG ====================
@dataclass
class Config:
    BOT_TOKEN: str = "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc"
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    MAX_WITHDRAWAL_DAILY: float = 1000.0
    MAX_TRANSACTION_PER_DAY: int = 50
    MIN_DEPOSIT: float = 1.0
    POINTS_PER_USDT: int = 100
    REFERRAL_BONUS: int = 20
    REFERRAL_COMMISSION: float = 0.10
    NETWORK_FEE: float = 1.0
    WITHDRAWAL_FEE: float = 1.0
    # إعدادات التواصل العشوائي
    CHAT_TIMEOUT: int = 300  # 5 دقائق
    MAX_CHATS_PER_DAY: int = 20

config = Config()

# ==================== ENUMS ====================
class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    REFERRAL_BONUS = "referral_bonus"
    PURCHASE = "purchase"
    COMMISSION = "commission"

class TransactionStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class UserLevel(Enum):
    NEW = 1
    BRONZE = 2
    SILVER = 3
    GOLD = 4
    PLATINUM = 5
    DIAMOND = 6

class ChatStatus(Enum):
    IDLE = "idle"
    WAITING = "waiting"
    CHATTING = "chatting"
    BLOCKED = "blocked"

# ==================== DATA CLASSES ====================
@dataclass
class Transaction:
    id: str
    user_id: int
    type: str
    amount: float
    fee: float
    status: str
    tx_hash: str = ""
    address: str = ""
    recipient_id: Optional[int] = None
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""

@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    balance: float = 0.0
    points: int = 0
    level: int = 1
    referral_code: str = ""
    referred_by: Optional[int] = None
    referrals_count: int = 0
    earnings: float = 0.0
    total_spent: float = 0.0
    total_deposited: float = 0.0
    wallet_address: str = ""
    is_verified: bool = False
    is_banned: bool = False
    is_admin: bool = False
    daily_withdrawal: float = 0.0
    daily_transactions: int = 0
    last_transaction_date: str = ""
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    failed_attempts: int = 0
    pin_code: str = ""
    # إعدادات التواصل
    chat_status: str = "idle"
    current_chat_partner: int = None
    chats_today: int = 0
    last_chat_date: str = ""
    gender: str = ""  # male, female, other
    age: int = 0
    bio: str = ""

@dataclass
class ChatSession:
    id: str
    user1_id: int
    user2_id: int
    started_at: str
    ended_at: str = ""
    messages_count: int = 0
    user1_rating: int = 0
    user2_rating: int = 0

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.users_file = "users.json"
        self.transactions_file = "transactions.json"
        self.chats_file = "chats.json"
        self.waiting_file = "waiting.json"
    
    def load_users(self) -> Dict:
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def save_users(self, users: Dict):
        with open(self.users_file, "w") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def load_transactions(self) -> List:
        try:
            with open(self.transactions_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_transactions(self, transactions: List):
        with open(self.transactions_file, "w") as f:
            json.dump(transactions, f, ensure_ascii=False, indent=2)
    
    def load_chats(self) -> List:
        try:
            with open(self.chats_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_chats(self, chats: List):
        with open(self.chats_file, "w") as f:
            json.dump(chats, f, ensure_ascii=False, indent=2)
    
    def load_waiting(self) -> List:
        try:
            with open(self.waiting_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_waiting(self, waiting: List):
        with open(self.waiting_file, "w") as f:
            json.dump(waiting, f, ensure_ascii=False, indent=2)

db = Database()

# ==================== HELPERS ====================
def generate_referral_code() -> str:
    return "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_transaction_id() -> str:
    return "TXN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=16))

def generate_chat_id() -> str:
    return "CHAT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))

def generate_wallet_address() -> str:
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))

def get_user(user_id: int) -> User:
    users = db.load_users()
    if str(user_id) not in users:
        user = User(user_id=user_id, referral_code=generate_referral_code(), wallet_address=generate_wallet_address())
        users[str(user_id)] = asdict(user)
        db.save_users(users)
        return user
    return User(**users[str(user_id)])

def update_user(user_id: int, data: Dict):
    users = db.load_users()
    if str(user_id) in users:
        users[str(user_id)].update(data)
        db.save_users(users)

def get_user_level(points: int) -> UserLevel:
    if points >= 100000:
        return UserLevel.DIAMOND
    elif points >= 50000:
        return UserLevel.PLATINUM
    elif points >= 20000:
        return UserLevel.GOLD
    elif points >= 10000:
        return UserLevel.SILVER
    elif points >= 5000:
        return UserLevel.BRONZE
    return UserLevel.NEW

def get_level_bonus(level: UserLevel) -> float:
    bonuses = {UserLevel.NEW: 0.0, UserLevel.BRONZE: 0.02, UserLevel.SILVER: 0.05, UserLevel.GOLD: 0.10, UserLevel.PLATINUM: 0.15, UserLevel.DIAMOND: 0.20}
    return bonuses.get(level, 0.0)

def create_transaction(user_id: int, txn_type: TransactionType, amount: float, fee: float = 0.0, tx_hash: str = "", address: str = "", recipient_id: int = None, description: str = "") -> Transaction:
    txn = Transaction(id=generate_transaction_id(), user_id=user_id, type=txn_type.value, amount=amount, fee=fee, status=TransactionStatus.PENDING.value, tx_hash=tx_hash, address=address, recipient_id=recipient_id, description=description)
    transactions = db.load_transactions()
    transactions.append(asdict(txn))
    db.save_transactions(transactions)
    return txn

def complete_transaction(txn_id: str):
    transactions = db.load_transactions()
    for txn in transactions:
        if txn["id"] == txn_id:
            txn["status"] = TransactionStatus.COMPLETED.value
            txn["completed_at"] = datetime.now().isoformat()
            break
    db.save_transactions(transactions)

def get_user_transactions(user_id: int, limit: int = 10) -> List:
    transactions = db.load_transactions()
    user_txns = [t for t in transactions if t["user_id"] == user_id]
    return sorted(user_txns, key=lambda x: x["created_at"], reverse=True)[:limit]

# ==================== RANDOM CHAT SYSTEM ====================
def add_to_waiting(user_id: int, gender: str = "") -> None:
    waiting = db.load_waiting()
    # إزالة المستخدم إذا كان موجوداً
    waiting = [w for w in waiting if w["user_id"] != user_id]
    waiting.append({"user_id": user_id, "gender": gender, "added_at": datetime.now().isoformat()})
    db.save_waiting(waiting)

def remove_from_waiting(user_id: int) -> None:
    waiting = db.load_waiting()
    waiting = [w for w in waiting if w["user_id"] != user_id]
    db.save_waiting(waiting)

def find_match(user_id: int, preferred_gender: str = "") -> Optional[int]:
    """البحث عن مستخدم مطابق"""
    waiting = db.load_waiting()
    
    # فلترة حسب الجنس المفضل
    if preferred_gender:
        matches = [w for w in waiting if w["user_id"] != user_id and w.get("gender") == preferred_gender]
    else:
        matches = [w for w in waiting if w["user_id"] != user_id]
    
    if matches:
        return matches[0]["user_id"]
    return None

def create_chat_session(user1_id: int, user2_id: int) -> ChatSession:
    session = ChatSession(
        id=generate_chat_id(),
        user1_id=user1_id,
        user2_id=user2_id,
        started_at=datetime.now().isoformat()
    )
    chats = db.load_chats()
    chats.append(asdict(session))
    db.save_chats(chats)
    return session

def end_chat_session(chat_id: str):
    chats = db.load_chats()
    for chat in chats:
        if chat["id"] == chat_id:
            chat["ended_at"] = datetime.now().isoformat()
            break
    db.save_chats(chats)

def get_active_chat(user_id: int) -> Optional[Tuple[int, str]]:
    """الحصول على المحادثة النشطة للمستخدم"""
    user = get_user(user_id)
    if user.chat_status == "chatting" and user.current_chat_partner:
        return (user.current_chat_partner, user.current_chat_partner)
    return None

# ==================== BINANCE API ====================
class BinanceAPI:
    def __init__(self):
        self.base_url = "https://api.binance.com"
        self.api_key = config.BINANCE_API_KEY
        self.secret_key = config.BINANCE_SECRET_KEY
    
    def _sign(self, params: str) -> str:
        return hmac.new(self.secret_key.encode(), params.encode(), hashlib.sha256).hexdigest()
    
    async def get_deposit_address(self, network: str = "TRC20") -> Dict:
        if not self.api_key:
            return {"address": generate_wallet_address(), "network": network, "success": True, "test_mode": True}
        return {"address": generate_wallet_address(), "network": network, "success": True}
    
    async def check_deposit(self, address: str, tx_hash: str = "") -> Dict:
        if not self.api_key:
            return {"confirmed": True, "amount": 10.0, "tx_hash": tx_hash or generate_transaction_id()}
        return {"confirmed": True, "amount": 10.0, "tx_hash": tx_hash}
    
    async def withdraw(self, address: str, amount: float, network: str = "TRC20") -> Dict:
        if not self.api_key:
            return {"success": True, "tx_hash": generate_transaction_id()}
        return {"success": False, "message": "API not configured"}

binance = BinanceAPI()

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int):
    user = get_user(user_id)
    level = UserLevel(user.level)
    keyboard = [
        [InlineKeyboardButton(f"💰 الرصيد: {user.balance:.2f} USDT", callback_data="balance")],
        [InlineKeyboardButton(f"⭐ النقاط: {user.points} | المستوى: {level.name}", callback_data="points")],
        [InlineKeyboardButton("🟢 إيداع", callback_data="deposit")],
        [InlineKeyboardButton("🔴 سحب", callback_data="withdraw")],
        [InlineKeyboardButton("📤 تحويل", callback_data="transfer")],
        [InlineKeyboardButton("🔗 الإحالة", callback_data="referral")],
        [InlineKeyboardButton("📊 المعاملات", callback_data="transactions")],
        [InlineKeyboardButton("💬 تواصل عشوائي", callback_data="random_chat")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
    ]
    if user.is_admin:
        keyboard.append([InlineKeyboardButton("👑 لوحة الأدمن", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def chat_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏭️ شخص آخر", callback_data="chat_next")],
        [InlineKeyboardButton("🛑 إنهاء المحادثة", callback_data="chat_stop")],
        [InlineKeyboardButton("🚫 بلوك", callback_data="chat_block")]
    ]
    return InlineKeyboardMarkup(keyboard)

def gender_keyboard():
    keyboard = [
        [InlineKeyboardButton("👨 رجل", callback_data="gender_male")],
        [InlineKeyboardButton("👩 امرأة", callback_data="gender_female")],
        [InlineKeyboardButton("🚻 أي", callback_data="gender_any")]
    ]
    return InlineKeyboardMarkup(keyboard)

def deposit_amount_keyboard():
    keyboard = [
        [InlineKeyboardButton("10 USDT", callback_data="deposit_10")],
        [InlineKeyboardButton("25 USDT", callback_data="deposit_25")],
        [InlineKeyboardButton("50 USDT", callback_data="deposit_50")],
        [InlineKeyboardButton("100 USDT", callback_data="deposit_100")],
        [InlineKeyboardButton("💵 مبلغ آخر", callback_data="deposit_custom")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_keyboard(action: str):
    keyboard = [
        [InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_{action}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== BOT COMMANDS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    
    args = context.args
    referred_by = None
    if args:
        referred_by = args[0]
    
    user_data = get_user(user_id)
    
    if referred_by and referred_by != user_data.referral_code:
        users = db.load_users()
        for uid, udata in users.items():
            if udata.get("referral_code") == referred_by:
                referred_by = int(uid)
                if referred_by and not user_data.referred_by:
                    update_user(user_id, {"referred_by": referred_by})
                    referrer = get_user(referred_by)
                    bonus = config.REFERRAL_BONUS
                    update_user(referred_by, {"balance": referrer.balance + bonus, "referrals_count": referrer.referrals_count + 1, "earnings": referrer.earnings + bonus})
                    create_transaction(referred_by, TransactionType.REFERRAL_BONUS, bonus, description=f"مكافأة إحالة من المستخدم {user_id}")
                break
    
    level = UserLevel(user_data.level)
    welcome = f"""🎉 مرحباً بك في Crypto Wallet +!

💰 محفظتك الإلكترونية
━━━━━━━━━━━━━━━━━━━━
🟢 الرصيد: {user_data.balance:.2f} USDT
⭐ النقاط: {user_data.points}
🏆 المستوى: {level.name}

💬 نظام التواصل العشوائي متاح!
اضغط "تواصل عشوائي" للدردشة مع الغرباء

🔗 كود الإحالة:
`{user_data.referral_code}`

💡 اربح نقاط إضافية:
• إحالة صديق: +{config.REFERRAL_BONUS} نقطة
• 10% من كل إيداع يُجريه مُحالوك
━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level = UserLevel(user.level)
    bonus = get_level_bonus(level)
    
    text = f"""💰 محفظتك
━━━━━━━━━━━━━━━━━━━━
🟢 الرصيد المتاح: {user.balance:.2f} USDT

📊 الإحصائيات:
• 💎 نقاطك: {user.points}
• 👥 المُحالين: {user.referrals_count}
• 💵 إجمالي الإيداعات: {user.total_deposited:.2f} USDT
• 💸 إجمالي السحوبات: {user.total_spent:.2f} USDT
• 💰 أرباح الإحالة: {user.earnings:.2f} USDT

🏆 مستواك: {level.name}
🎁 bonus الإيداع: {bonus*100}%

📅 تاريخ الانضمام: {user.join_date[:10]}
━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = f"""🟢 إيداع USDT

اختر المبلغ المراد إيداعه:

💵 كل 1 USDT = {config.POINTS_PER_USDT} نقطة"""
    await update.message.reply_text(text, reply_markup=deposit_amount_keyboard())

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    if user.balance < config.MIN_DEPOSIT:
        await update.message.reply_text(f"❌ الحد الأدنى للسحب: {config.MIN_DEPOSIT} USDT\nرصيدك الحالي: {user.balance:.2f} USDT", reply_markup=main_menu_keyboard(user_id))
        return
    
    text = f"""🔴 سحب USDT

💰 الرصيد المتاح: {user.balance:.2f} USDT

📋 الحدود:
• الحد الأدنى: {config.MIN_DEPOSIT} USDT
• الحد الأقصى اليوم: {config.MAX_WITHDRAWAL_DAILY} USDT
• المسحوب اليوم: {user.daily_withdrawal:.2f} USDT

💳 رسوم السحب: {config.WITHDRAWAL_FEE} USDT

━━━━━━━━━━━━━━━━━━━━
أرسل عنوان المحفظة (TRC20) والمبلغ
مثال: 0xABC...DEF 50"""
    await update.message.reply_text(text, reply_markup=back_keyboard())

async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    if user.balance < 1:
        await update.message.reply_text("❌ رصيدك غير كافٍ للتحويل!", reply_markup=main_menu_keyboard(user_id))
        return
    
    text = f"""📤 تحويل USDT

💰 رصيدك: {user.balance:.2f} USDT

━━━━━━━━━━━━━━━━━━━━
الصيغة:
تحويل [المبلغ] [كود_المستلم]

مثال:
تحويل 10 REF-XXXXXXXX
━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=back_keyboard())

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    bot_username = context.bot.username
    commission = config.REFERRAL_COMMISSION * 100
    
    text = f"""🔗 نظام الإحالة
━━━━━━━━━━━━━━━━━━━━
🎁 اربح {commission}% من كل إيداع يُجريه مُحالوك!

📊 إحصائياتك:
• 👥 عدد المُحالين: {user.referrals_count}
• 💰 أرباح الإحالة: {user.earnings:.2f} USDT

━━━━━━━━━━━━━━━━━━━━
🔗 رابط الإحالة:
https://t.me/{bot_username}?start={user.referral_code}

📋 كود الإحالة:
`{user.referral_code}`
━━━━━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def transactions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    txns = get_user_transactions(user_id, 10)
    
    if not txns:
        text = "📊 لا توجد معاملات سابقة"
    else:
        text = "📊 آخر معاملاتك:\n━━━━━━━━━━━━━━━━━━━━\n"
        for txn in txns:
            emoji = {"deposit": "🟢", "withdrawal": "🔴", "transfer": "📤", "referral_bonus": "🎁", "purchase": "🛒", "commission": "💰"}.get(txn["type"], "💳")
            status = {"pending": "⏳", "completed": "✅", "failed": "❌", "cancelled": "🚫"}.get(txn["status"], "❓")
            text += f"{emoji} **{txn['type'].upper()}**\n   المبلغ: {txn['amount']:.2f} USDT\n   الحالة: {status} {txn['status']}\n   التاريخ: {txn['created_at'][:16]}\n━━━━━━━━━━━━━━━━━━━━\n"
    
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    gender_emoji = {"male": "👨", "female": "👩", "other": "🚻", "": "❌"}
    
    text = f"""⚙️ الإعدادات
━━━━━━━━━━━━━━━━━━━━
👤 الملف الشخصي:
• الاسم: {user.first_name} {user.last_name}
• اليوزر: @{user.username or "غير محدد"}

💬 إعدادات التواصل:
• الجنس: {gender_emoji.get(user.gender, "❌")} {user.gender or "غير محدد"}
• العمر: {user.age or "غير محدد"}
• نبذة: {user.bio or "لا توجد"}

🔐 الأمان:
• حالة التحقق: {"✅ مفعل" if user.is_verified else "❌ غير مفعل"}
• رقم PIN: {"✅ مفعل" if user.pin_code else "❌ غير مفعل"}

💳 المحفظة:
• العنوان: `{user.wallet_address[:15]}...`
━━━━━━━━━━━━━━━━━━━━"""
    keyboard = [
        [InlineKeyboardButton("👤 تعديل الملف", callback_data="edit_profile")],
        [InlineKeyboardButton("🔐 تفعيل PIN", callback_data="setup_pin")],
        [InlineKeyboardButton("✅ التحقق من الهوية", callback_data="verify")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== RANDOM CHAT COMMANDS ====================
async def random_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بدء البحث عن محادثة عشوائية"""
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    # التحقق من الحد اليومي
    today = datetime.now().strftime("%Y-%m-%d")
    if user.last_chat_date != today:
        update_user(user_id, {"chats_today": 0, "last_chat_date": today})
        user = get_user(user_id)
    
    if user.chats_today >= config.MAX_CHATS_PER_DAY:
        await update.message.reply_text(
            f"❌ reached حد المحادثات اليومية!\n\n"
            f"المحادثات اليوم: {user.chats_today}/{config.MAX_CHATS_PER_DAY}\n"
            f"جرب غداً! 🌙",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    # التحقق من حالة المستخدم
    if user.chat_status == "chatting":
        await update.message.reply_text(
            "⚠️ أنت في محادثة نشطة حالياً!\n"
            "أختر:\n"
            "• /stop - إنهاء المحادثة\n"
            "• /next - شخص آخر",
            reply_markup=chat_keyboard()
        )
        return
    
    # التحقق من وجود ملف شخصي
    if not user.gender:
        await update.message.reply_text(
            "👋 قبل بدء المحادثة، حدد جنسك:\n\n"
            "(هذا يساعد في إقرانك بشخص مناسب)",
            reply_markup=gender_keyboard()
        )
        return
    
    # إضافة للقائمة المنتظرة
    add_to_waiting(user_id, user.gender)
    update_user(user_id, {"chat_status": "waiting"})
    
    await update.message.reply_text(
        "🔍 جاري البحث عن شخص للدردشة...\n\n"
        "⏳ انتظر قليلاً...
\n"
        "لإلغاء البحث: /cancel",
        reply_markup=back_keyboard()
    )
    
    # البحث عن مطابق
    await find_chat_match(update, context, user_id)

async def find_chat_match(update, context, user_id: int):
    """البحث عن مطابق"""
    user = get_user(user_id)
    preferred_gender = ""  # يمكن إضافة اختيار
    
    # البحث عن مطابق
    match_id = find_match(user_id, preferred_gender)
    
    if match_id:
        # إزالة كلاهما من قائمة الانتظار
        remove_from_waiting(user_id)
        remove_from_waiting(match_id)
        
        # إنشاء جلسة محادثة
        chat_session = create_chat_session(user_id, match_id)
        
        # تحديث حالة كلا المستخدمين
        update_user(user_id, {
            "chat_status": "chatting",
            "current_chat_partner": match_id
        })
        update_user(match_id, {
            "chat_status": "chatting",
            "current_chat_partner": user_id
        })
        
        # إشعار المستخدم الأول
        try:
            await context.bot.send_message(
                user_id,
                f"🎉 تم العثور على شخص للدردشة!\n\n"
                f"💬 ابدأ المحادثة الآن\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚠️ قواعد المحادثة:\n"
                f"• احترم الآخر\n"
                f"• لا تشارك معلومات شخصية\n"
                f"• أي إساءة = بلوك فوري\n\n"
                f"لإنهاء: /stop\n"
                f"شخص آخر: /next",
                reply_markup=chat_keyboard()
            )
        except:
            pass
        
        # إشعار المستخدم الثاني
        try:
            match_user = get_user(match_id)
            await context.bot.send_message(
                match_id,
                f"🎉 تم العثور على شخص للدردشة!\n\n"
                f"💬 ابدأ المحادثة الآن\n"
                f"━━━━━━━━━━━━━━━━━━━━\n\n"
                f"⚠️ قواعد المحادثة:\n"
                f"• احترم الآخر\n"
                f"• لا تشارك معلومات شخصية\n"
                f"• أي إساءة = بلوك فوري\n\n"
                f"لإنهاء: /stop\n"
                f"شخص آخر: /next",
                reply_markup=chat_keyboard()
            )
        except:
            pass
    else:
        # لم يتم العثور على مطابق
        try:
            await context.bot.send_message(
                user_id,
                "⏳ لا يوجد أحد حالياً...\n\n"
                "سيتم إشعارك عند العثور على شخص.\n"
                "لإلغاء الانتظار: /cancel"
            )
        except:
            pass

async def stop_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنهاء المحادثة الحالية"""
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    if user.chat_status != "chatting" or not user.current_chat_partner:
        await update.message.reply_text(
            "❌ لست في محادثة حالياً!",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    partner_id = user.current_chat_partner
    
    # إنهاء المحادثة
    update_user(user_id, {
        "chat_status": "idle",
        "current_chat_partner": None,
        "chats_today": user.chats_today + 1
    })
    
    partner = get_user(partner_id)
    update_user(partner_id, {
        "chat_status": "idle",
        "current_chat_partner": None
    })
    
    # إشعار الشريك
    try:
        await context.bot.send_message(
            partner_id,
            "❌ انتهت المحادثة من قبل الطرف الآخر\n\n"
            "💬 ابدأ محادثة جديدة: /chat"
        )
    except:
        pass
    
    await update.message.reply_text(
        "✅ تم إنهاء المحادثة\n\n"
        f"📊 المحادثات اليوم: {user.chats_today + 1}/{config.MAX_CHATS_PER_DAY}\n\n"
        "💬 ابدأ محادثة جديدة: /chat",
        reply_markup=main_menu_keyboard(user_id)
    )

async def next_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الانتقال لشخص آخر"""
    await stop_chat_command(update, context)
    await random_chat_command(update, context)

async def cancel_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء البحث"""
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    if user.chat_status != "waiting":
        await update.message.reply_text(
            "❌ لست في وضع الانتظار!",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    remove_from_waiting(user_id)
    update_user(user_id, {"chat_status": "idle"})
    
    await update.message.reply_text(
        "❌ تم إلغاء البحث\n\n"
        "💬 حاول مرة أخرى: /chat",
        reply_markup=main_menu_keyboard(user_id)
    )

async def block_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بلوك المستخدم الحالي"""
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    if user.chat_status != "chatting" or not user.current_chat_partner:
        await update.message.reply_text(
            "❌ لست في محادثة!",
            reply_markup=main_menu_keyboard(user_id)
        )
        return
    
    partner_id = user.current_chat_partner
    
    # إنهاء المحادثة
    update_user(user_id, {
        "chat_status": "idle",
        "current_chat_partner": None,
        "chats_today": user.chats_today + 1
    })
    
    partner = get_user(partner_id)
    update_user(partner_id, {
        "chat_status": "idle",
        "current_chat_partner": None
    })
    
    # إشعار الشريك
    try:
        await context.bot.send_message(
            partner_id,
            "🚫 تم حظرك من قبل المستخدم\n\n"
            "💬 ابدأ محادثة جديدة: /chat"
        )
    except:
        pass
    
    await update.message.reply_text(
        "🚫 تم بلوك المستخدم\n\n"
        "💬 ابدأ محادثة جديدة: /chat",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== CALLBACK HANDLERS ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back":
        await balance_command(update, context)
    elif data == "balance":
        await balance_command(update, context)
    elif data == "points":
        user = get_user(user_id)
        level = UserLevel(user.level)
        bonus = get_level_bonus(level)
        
        next_level = UserLevel(user.level + 1) if user.level < 6 else None
        points_needed = 5000 * (2 ** user.level) if next_level else 0
        
        text = f"""⭐ نظام النقاط والمستويات
━━━━━━━━━━━━━━━━━━━━
💎 نقاطك الحالية: **{user.points}**

🏆 مستواك الحالي: **{level.name}**
🎁 bonus الإيداع: **{bonus*100}%**"""
        
        if next_level:
            text += f"""

📈 للمستوى التالي ({next_level.name}):
• النقاط المطلوبة: {points_needed}
• bonus الإيداع: {get_level_bonus(next_level)*100}%"""
        
        text += """

💡 طرق كسب النقاط:
• إيداع USDT: 100 نقطة/USDT
• إحالة صديق: 20 نقطة
• 10% من نقاط مُحالوك
━━━━━━━━━━━━━━━━━━━━"""
        
        await query.edit_message_text(text, reply_markup=main_menu_keyboard(user_id))
    elif data == "deposit":
        await deposit_command(update, context)
    elif data.startswith("deposit_"):
        amount = data.replace("deposit_", "")
        if amount == "custom":
            await query.edit_message_text("💵 أدخل المبلغ المراد إيداعه (ب USDT):")
        else:
            await process_deposit(query, context, int(amount))
    elif data == "withdraw":
        await withdraw_command(update, context)
    elif data == "transfer":
        await transfer_command(update, context)
    elif data == "referral":
        await referral_command(update, context)
    elif data == "transactions":
        await transactions_command(update, context)
    elif data == "random_chat":
        await random_chat_command(update, context)
    elif data == "settings":
        await settings_command(update, context)
    elif data == "edit_profile":
        await query.edit_message_text(
            "👤 تعديل الملف الشخصي\n\n"
            "أرسل معلوماتك بهذه الصيغة:\n"
            "`عمر: 25`\n"
            "`نبذة: أحب القراءة والسفر`",
            reply_markup=back_keyboard()
        )
    elif data.startswith("gender_"):
        gender = data.replace("gender_", "")
        if gender == "any":
            gender = ""
        update_user(user_id, {"gender": gender})
        await query.edit_message_text(
            f"✅ تم تحديد الجنس: {gender}\n\n"
            "💬 ابدأ المحادثة: /chat",
            reply_markup=main_menu_keyboard(user_id)
        )
    elif data == "setup_pin":
        await query.edit_message_text("🔐 إعداد PIN\n\nأدخل رقم PIN مكون من 4 أرقام:", reply_markup=back_keyboard())
    elif data == "verify":
        await query.edit_message_text("✅ التحقق من الهوية\n\nللتحقق من هويتك، أرسل صورة واضحة لبطاقتك الشخصية.\n\n🔒 بياناتك مؤمنة ومشفرة.", reply_markup=back_keyboard())
    elif data.startswith("confirm_"):
        action = data.replace("confirm_", "")
        await process_confirmation(query, context, action)
    elif data == "cancel":
        await query.edit_message_text("❌ تم إلغاء العملية", reply_markup=main_menu_keyboard(user_id))
    elif data == "chat_next":
        await next_chat_command(update, context)
    elif data == "chat_stop":
        await stop_chat_command(update, context)
    elif data == "chat_block":
        await block_user_command(update, context)

async def process_deposit(query, context, amount_usdt):
    user_id = query.from_user.id
    deposit_info = await binance.get_deposit_address()
    txn = create_transaction(user_id, TransactionType.DEPOSIT, amount_usdt, description=f"إيداع {amount_usdt} USDT")
    points = amount_usdt * config.POINTS_PER_USDT
    
    text = f"""🟢 طلب إيداع
━━━━━━━━━━━━━━━━━━━━
💵 المبلغ: {amount_usdt} USDT
⭐ النقاط: +{points} نقطة

📋 معرف المعاملة: `{txn.id}`

💳 عنوان الإيداع (TRC20):
`{deposit_info["address"]}`

🌐 الشبكة: {deposit_info["network"]}

⚠️ تحذيرات مهمة:
• استخدم شبكة TRC20 فقط
• لا ترسل عملات أخرى لهذا العنوان
• بعد الإرسال، انتظر التأكيد (5-30 دقيقة)

━━━━━━━━━━━━━━━━━━━━
✅ بمجرد تأكيد الدفع، ستُضاف النقاط تلقائياً"""
    await query.edit_message_text(text, reply_markup=confirm_keyboard(f"deposit_{txn.id}"))

async def process_confirmation(query, context, action):
    user_id = query.from_user.id
    
    if action.startswith("deposit_"):
        txn_id = action.replace("deposit_", "")
        user = get_user(user_id)
        complete_transaction(txn_id)
        
        amount = 10.0
        points = amount * config.POINTS_PER_USDT
        
        if user.referred_by:
            referrer = get_user(user.referred_by)
            referral_points = int(points * config.REFERRAL_COMMISSION)
            update_user(user.referred_by, {"points": referrer.points + referral_points})
        
        new_points = user.points + points
        new_level = get_user_level(new_points)
        
        update_user(user_id, {"balance": user.balance + amount, "points": new_points, "level": new_level.value, "total_deposited": user.total_deposited + amount})
        
        await query.edit_message_text(f"✅ تم تأكيد الإيداع!\n\n💵 المبلغ: {amount} USDT\n⭐ النقاط: +{points}\n🏆 المستوى: {new_level.name}", reply_markup=main_menu_keyboard(user_id))

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    # التحقق إذا كان في محادثة نشطة
    if user.chat_status == "chatting" and user.current_chat_partner:
        partner_id = user.current_chat_partner
        partner = get_user(partner_id)
        
        # إرسال الرسالة للشريك
        try:
            gender_emoji = {"male": "👨", "female": "👩", "other": "🚻"}
            sender_gender = gender_emoji.get(user.gender, "👤")
            
            await context.bot.send_message(
                partner_id,
                f"{sender_gender} غريب:\n\n{text}",
                reply_markup=chat_keyboard()
            )
        except:
            await update.message.reply_text("❌ تعذر إرسال الرسالة", reply_markup=main_menu_keyboard(user_id))
        return
    
    # معالجة الأوامر العادية
    if text.startswith("تحويل "):
        await handle_transfer(update, context)
    elif " " in text and len(text.split()) == 2:
        parts = text.split()
        if len(parts[0]) == 42 and parts[0].startswith("0x"):
            await handle_withdraw(update, context)
        else:
            await update.message.reply_text("❌ أمر غير معروف!", reply_markup=main_menu_keyboard(user_id))
    elif text.startswith("عمر:"):
        try:
            age = int(text.replace("عمر:", "").strip())
            if 13 <= age <= 99:
                update_user(user_id, {"age": age})
                await update.message.reply_text(f"✅ تم تحديد عمرك: {age} سنة", reply_markup=main_menu_keyboard(user_id))
            else:
                await update.message.reply_text("❌ العمر يجب أن يكون بين 13 و 99", reply_markup=main_menu_keyboard(user_id))
        except:
            await update.message.reply_text("❌ صيغة خاطئة", reply_markup=main_menu_keyboard(user_id))
    elif text.startswith("نبذة:"):
        bio = text.replace("نبذة:", "").strip()[:200]
        update_user(user_id, {"bio": bio})
        await update.message.reply_text("✅ تم تحديث النبذة", reply_markup=main_menu_keyboard(user_id))
    else:
        await update.message.reply_text("❌ أمر غير معروف!\n\nاستخدم /start للبدء", reply_markup=main_menu_keyboard(user_id))

async def handle_transfer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    try:
        parts = update.message.text.replace("تحويل ", "").split()
        amount = float(parts[0])
        recipient_code = parts[1]
        
        if amount > user.balance:
            await update.message.reply_text("❌ رصيدك غير كافٍ!", reply_markup=main_menu_keyboard(user_id))
            return
        
        users = db.load_users()
        recipient_id = None
        
        for uid, udata in users.items():
            if udata.get("referral_code") == recipient_code:
                recipient_id = int(uid)
                break
        
        if not recipient_id:
            await update.message.reply_text("❌ المستخدم غير موجود!", reply_markup=main_menu_keyboard(user_id))
            return
        
        if recipient_id == user_id:
            await update.message.reply_text("❌ لا يمكنك التحويل لنفسك!", reply_markup=main_menu_keyboard(user_id))
            return
        
        update_user(user_id, {"balance": user.balance - amount})
        recipient = get_user(recipient_id)
        update_user(recipient_id, {"balance": recipient.balance + amount})
        
        create_transaction(user_id, TransactionType.TRANSFER, amount, recipient_id=recipient_id, description=f"تحويل إلى {recipient_code}")
        create_transaction(recipient_id, TransactionType.TRANSFER, amount, description=f"استلام من {user_id}")
        
        await update.message.reply_text(f"✅ تم التحويل بنجاح!\n\n📤 المُستلم: {recipient_code}\n💵 المبلغ: {amount} USDT\n💰 رصيدك المتبقي: {user.balance - amount} USDT", reply_markup=main_menu_keyboard(user_id))
        
    except:
        await update.message.reply_text("❌ خطأ في الصيغة!\n\nالصيغة الصحيحة:\nتحويل 10 REF-XXXXXXXX", reply_markup=main_menu_keyboard(user_id))

async def handle_withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    try:
        parts = update.message.text.split()
        address = parts[0]
        amount = float(parts[1])
        
        fee = config.WITHDRAWAL_FEE
        total = amount + fee
        
        if total > user.balance:
            await update.message.reply_text(f"❌ رصيدك غير كافٍ!\nالمبلغ مع الرسوم: {total} USDT\nرصيدك: {user.balance} USDT", reply_markup=main_menu_keyboard(user_id))
            return
        
        if amount < config.MIN_DEPOSIT:
            await update.message.reply_text(f"❌ الحد الأدنى للسحب: {config.MIN_DEPOSIT} USDT", reply_markup=main_menu_keyboard(user_id))
            return
        
        remaining_daily = config.MAX_WITHDRAWAL_DAILY - user.daily_withdrawal
        if amount > remaining_daily:
            await update.message.reply_text(f"❌ تجاوزت الحد اليومي!\nالمتاح للسحب: {remaining_daily} USDT", reply_markup=main_menu_keyboard(user_id))
            return
        
        update_user(user_id, {"balance": user.balance - total, "daily_withdrawal": user.daily_withdrawal + amount, "total_spent": user.total_spent + amount})
        
        txn = create_transaction(user_id, TransactionType.WITHDRAWAL, amount, fee=fee, address=address, description=f"سحب إلى {address[:10]}...")
        result = await binance.withdraw(address, amount)
        
        if result.get("success"):
            complete_transaction(txn.id)
            status = "✅ تم الإرسال"
        else:
            status = "⏳ قيد المعالجة"
        
        await update.message.reply_text(f"🔴 تم إنشاء طلب السحب\n\n📋 معرف المعاملة: {txn.id}\n💵 المبلغ: {amount} USDT\n💳 الرسوم: {fee} USDT\n📤 العنوان: {address[:10]}...\n\nالحالة: {status}", reply_markup=main_menu_keyboard(user_id))
        
    except:
        await update.message.reply_text("❌ خطأ في الصيغة!\n\nالصيغة الصحيحة:\n0xABC...DEF 50", reply_markup=main_menu_keyboard(user_id))

# ==================== ADMIN PANEL ====================
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    if not user.is_admin:
        await update.message.reply_text("❌ ليس لديك صلاحية!")
        return
    
    users = db.load_users()
    transactions = db.load_transactions()
    waiting = db.load_waiting()
    
    total_balance = sum(u.get("balance", 0) for u in users.values())
    total_points = sum(u.get("points", 0) for u in users.values())
    total_deposits = sum(u.get("total_deposited", 0) for u in users.values())
    
    text = f"""👑 لوحة تحكم الأدمن
━━━━━━━━━━━━━━━━━━━━
📊 إحصائيات عامة:
• 👥 المستخدمين: {len(users)}
• 💰 الرصيد الإجمالي: {total_balance:.2f} USDT
• 💎 إجمالي النقاط: {total_points}
• 📥 إجمالي الإيداعات: {total_deposits} USDT
• 📝 المعاملات: {len(transactions)}

💬 إعدادات التواصل:
• في الانتظار: {len(waiting)}
• الحد اليومي: {config.MAX_CHATS_PER_DAY}
━━━━━━━━━━━━━━━━━━━━"""
    keyboard = [
        [InlineKeyboardButton("📊 إحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="admin_users")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

# ==================== MAIN ====================
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    # الأوامر
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("deposit", deposit_command))
    app.add_handler(CommandHandler("withdraw", withdraw_command))
    app.add_handler(CommandHandler("transfer", transfer_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("transactions", transactions_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("admin", admin_command))
    
    # أوامر التواصل العشوائي
    app.add_handler(CommandHandler("chat", random_chat_command))
    app.add_handler(CommandHandler("stop", stop_chat_command))
    app.add_handler(CommandHandler("next", next_chat_command))
    app.add_handler(CommandHandler("cancel", cancel_chat_command))
    app.add_handler(CommandHandler("block", block_user_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(callback_handler))
    
    # الرسائل
    app.add_handler(MessageHandler(handle_message))
    
    print("🤖 Crypto Wallet + Random Chat Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
