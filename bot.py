"""
🤖 Crypto Wallet Bot + Random Chat + Paid Messages + Gifts
بوت محفظة مع تواصل عشوائي ورسائل مدفوعة ونظام هدايا
"""

import os
import json
import hashlib
import hmac
import random
import string
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputSticker, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes

# ==================== CONFIG ====================
@dataclass
class Config:
    BOT_TOKEN: str = "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc"
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    MAX_WITHDRAWAL_DAILY: float = 1000.0
    MIN_DEPOSIT: float = 1.0
    POINTS_PER_USDT: int = 100
    REFERRAL_BONUS: int = 20
    REFERRAL_COMMISSION: float = 0.10
    WITHDRAWAL_FEE: float = 1.0
    CHAT_TIMEOUT: int = 300
    MAX_CHATS_PER_DAY: int = 20
    # إعدادات الرسائل المدفوعة
    PRIVATE_MESSAGE_COST: int = 10  # نقاط
    GIFT_COST_MIN: int = 5
    GIFT_COST_MAX: int = 100
    ADMIN_MESSAGE_COST: int = 50

config = Config()

# ==================== ENUMS ====================
class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    REFERRAL_BONUS = "referral_bonus"
    PURCHASE = "purchase"
    COMMISSION = "commission"
    PRIVATE_MESSAGE = "private_message"
    GIFT_SENT = "gift_sent"
    GIFT_RECEIVED = "gift_received"

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

class GiftType(Enum):
    STICKER = "sticker"
    PHOTO = "photo"
    VIDEO = "video"
    VOICE = "voice"
    CHANNEL = "channel"
    ADMIN = "admin"

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
    is_premium: bool = False  # مستخدم مميز
    is_model: bool = False   # مشهور/مودل
    daily_withdrawal: float = 0.0
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    pin_code: str = ""
    # إعدادات التواصل
    chat_status: str = "idle"
    current_chat_partner: int = None
    chats_today: int = 0
    last_chat_date: str = ""
    gender: str = ""
    age: int = 0
    bio: str = ""
    # إعدادات الرسائل المدفوعة
    accept_private_messages: bool = True
    private_message_price: int = 10
    accept_gifts: bool = True
    total_gifts_received: int = 0
    total_gifts_value: int = 0

@dataclass
class Gift:
    id: str
    sender_id: int
    receiver_id: int
    gift_type: str
    value: int  # قيمة الهدية بالنقاط
    message: str = ""
    sticker_file_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class PrivateMessage:
    id: str
    sender_id: int
    receiver_id: int
    message: str
    cost: int
    is_read: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Channel:
    id: str
    name: str
    username: str = ""
    invite_link: str = ""
    description: str = ""
    owner_id: int = 0
    is_premium: bool = False
    members_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.users_file = "users.json"
        self.transactions_file = "transactions.json"
        self.chats_file = "chats.json"
        self.waiting_file = "waiting.json"
        self.gifts_file = "gifts.json"
        self.private_messages_file = "private_messages.json"
        self.channels_file = "channels.json"
    
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
    
    def load_gifts(self) -> List:
        try:
            with open(self.gifts_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_gifts(self, gifts: List):
        with open(self.gifts_file, "w") as f:
            json.dump(gifts, f, ensure_ascii=False, indent=2)
    
    def load_private_messages(self) -> List:
        try:
            with open(self.private_messages_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_private_messages(self, messages: List):
        with open(self.private_messages_file, "w") as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)
    
    def load_channels(self) -> List:
        try:
            with open(self.channels_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_channels(self, channels: List):
        with open(self.channels_file, "w") as f:
            json.dump(channels, f, ensure_ascii=False, indent=2)

db = Database()

# ==================== HELPERS ====================
def generate_referral_code() -> str:
    return "REF-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

def generate_transaction_id() -> str:
    return "TXN-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=16))

def generate_chat_id() -> str:
    return "CHAT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))

def generate_gift_id() -> str:
    return "GIFT-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=10))

def generate_message_id() -> str:
    return "MSG-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=12))

def generate_channel_id() -> str:
    return "CH-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

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
    if points >= 100000: return UserLevel.DIAMOND
    elif points >= 50000: return UserLevel.PLATINUM
    elif points >= 20000: return UserLevel.GOLD
    elif points >= 10000: return UserLevel.SILVER
    elif points >= 5000: return UserLevel.BRONZE
    return UserLevel.NEW

def get_level_bonus(level: UserLevel) -> float:
    bonuses = {UserLevel.NEW: 0.0, UserLevel.BRONZE: 0.02, UserLevel.SILVER: 0.05, UserLevel.GOLD: 0.10, UserLevel.PLATINUM: 0.15, UserLevel.DIAMOND: 0.20}
    return bonuses.get(level, 0.0)

def create_transaction(user_id: int, txn_type: TransactionType, amount: float, fee: float = 0.0, recipient_id: int = None, description: str = "") -> Transaction:
    txn = Transaction(id=generate_transaction_id(), user_id=user_id, type=txn_type.value, amount=amount, fee=fee, status=TransactionStatus.PENDING.value, recipient_id=recipient_id, description=description)
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

# ==================== RANDOM CHAT ====================
def add_to_waiting(user_id: int, gender: str = "") -> None:
    waiting = db.load_waiting()
    waiting = [w for w in waiting if w["user_id"] != user_id]
    waiting.append({"user_id": user_id, "gender": gender, "added_at": datetime.now().isoformat()})
    db.save_waiting(waiting)

def remove_from_waiting(user_id: int) -> None:
    waiting = db.load_waiting()
    waiting = [w for w in waiting if w["user_id"] != user_id]
    db.save_waiting(waiting)

def find_match(user_id: int, preferred_gender: str = "") -> Optional[int]:
    waiting = db.load_waiting()
    if preferred_gender:
        matches = [w for w in waiting if w["user_id"] != user_id and w.get("gender") == preferred_gender]
    else:
        matches = [w for w in waiting if w["user_id"] != user_id]
    if matches:
        return matches[0]["user_id"]
    return None

def create_chat_session(user1_id: int, user2_id: int) -> None:
    session = {"id": generate_chat_id(), "user1_id": user1_id, "user2_id": user2_id, "started_at": datetime.now().isoformat()}
    chats = db.load_chats()
    chats.append(session)
    db.save_chats(chats)

# ==================== GIFTS SYSTEM ====================
GIFTS = {
    # ستكرز
    "sticker_rose": {"name": "🌹 وردة", "emoji": "🌹", "price": 5},
    "sticker_heart": {"name": "❤️ قلب", "emoji": "❤️", "price": 10},
    "sticker_fire": {"name": "🔥 نار", "emoji": "🔥", "price": 15},
    "sticker_star": {"name": "⭐ نجمة", "emoji": "⭐", "price": 20},
    "sticker_crown": {"name": "👑 تاج", "emoji": "👑", "price": 50},
    "sticker_diamond": {"name": "💎 ماسة", "emoji": "💎", "price": 100},
    
    # هدايا خاصة
    "gift_coffee": {"name": "☕ قهوة", "emoji": "☕", "price": 15},
    "gift_chocolate": {"name": "🍫 شوكولاتة", "emoji": "🍫", "price": 20},
    "gift_cake": {"name": "🎂 كيك", "emoji": "🎂", "price": 30},
    "gift_ring": {"name": "💍 خاتم", "emoji": "💍", "price": 75},
    "gift_car": {"name": "🚗 سيارة", "emoji": "🚗", "price": 150},
    "gift_house": {"name": "🏠 فيلا", "emoji": "🏠", "price": 300},
    
    # هدايا خاصة للأدمن
    "admin_badge": {"name": "🏅 شارة إدارية", "emoji": "🏅", "price": 200},
    "admin_shield": {"name": "🛡️ درع", "emoji": "🛡️", "price": 250},
}

def send_gift(sender_id: int, receiver_id: int, gift_key: str, message: str = "") -> Tuple[bool, str]:
    """إرسال هدية"""
    if gift_key not in GIFTS:
        return False, "الهدية غير موجودة"
    
    gift_info = GIFTS[gift_key]
    price = gift_info["price"]
    
    sender = get_user(sender_id)
    receiver = get_user(receiver_id)
    
    if sender.points < price:
        return False, f"نقاطك غير كافية! تحتاج {price} نقطة"
    
    if not receiver.accept_gifts:
        return False, "المستخدم لا يقبل الهدايا"
    
    # خصم نقاط المرسل
    update_user(sender_id, {"points": sender.points - price})
    
    # إضافة نقاط للمستلم (80% من القيمة)
    receiver_earnings = int(price * 0.8)
    update_user(receiver_id, {
        "points": receiver.points + receiver_earnings,
        "total_gifts_received": receiver.total_gifts_received + 1,
        "total_gifts_value": receiver.total_gifts_value + price
    })
    
    # تسجيل الهدية
    gift = Gift(
        id=generate_gift_id(),
        sender_id=sender_id,
        receiver_id=receiver_id,
        gift_type=gift_key,
        value=price,
        message=message
    )
    gifts = db.load_gifts()
    gifts.append(asdict(gift))
    db.save_gifts(gifts)
    
    # تسجيل المعاملة
    create_transaction(sender_id, TransactionType.GIFT_SENT, price, description=f"هدية {gift_info['name']} لـ {receiver_id}")
    create_transaction(receiver_id, TransactionType.GIFT_RECEIVED, receiver_earnings, description=f"استلام هدية من {sender_id}")
    
    return True, f"✅ تم إرسال {gift_info['emoji']} {gift_info['name']}!"

def get_user_gifts(user_id: int) -> List:
    gifts = db.load_gifts()
    user_gifts = [g for g in gifts if g["sender_id"] == user_id or g["receiver_id"] == user_id]
    return sorted(user_gifts, key=lambda x: x["created_at"], reverse=True)[:20]

# ==================== PRIVATE MESSAGES ====================
def send_private_message(sender_id: int, receiver_id: int, message: str) -> Tuple[bool, str]:
    """إرسال رسالة خاصة مدفوعة"""
    receiver = get_user(receiver_id)
    
    if not receiver.accept_private_messages:
        return False, "المستخدم لا يقبل رسائل خاصة"
    
    cost = receiver.private_message_price
    sender = get_user(sender_id)
    
    if sender.points < cost:
        return False, f"نقاطك غير كافية! ثمن الرسالة: {cost} نقطة"
    
    # خصم النقاط
    update_user(sender_id, {"points": sender.points - cost})
    
    # إرسال 80% للمستلم
    receiver_earnings = int(cost * 0.8)
    update_user(receiver_id, {"points": receiver.points + receiver_earnings})
    
    # تسجيل الرسالة
    msg = PrivateMessage(
        id=generate_message_id(),
        sender_id=sender_id,
        receiver_id=receiver_id,
        message=message,
        cost=cost
    )
    messages = db.load_private_messages()
    messages.append(asdict(msg))
    db.save_private_messages(messages)
    
    # تسجيل المعاملة
    create_transaction(sender_id, TransactionType.PRIVATE_MESSAGE, cost, description=f"رسالة خاصة لـ {receiver_id}")
    
    return True, f"✅ تم إرسال الرسالة! ({cost} نقطة)"

def get_user_messages(user_id: int) -> List:
    messages = db.load_private_messages()
    user_msgs = [m for m in messages if m["receiver_id"] == user_id]
    return sorted(user_msgs, key=lambda x: x["created_at"], reverse=True)[:20]

# ==================== CHANNELS ====================
def create_channel(owner_id: int, name: str, description: str = "") -> Channel:
    channel = Channel(
        id=generate_channel_id(),
        name=name,
        description=description,
        owner_id=owner_id
    )
    channels = db.load_channels()
    channels.append(asdict(channel))
    db.save_channels(channels)
    return channel

def get_channels() -> List:
    return db.load_channels()

def get_popular_models() -> List[User]:
    """الحصول على أشهر المستخدمين (الأكثر هدايا)"""
    users = db.load_users()
    models = [User(**u) for u in users.values() if u.get("is_model") or u.get("total_gifts_received", 0) > 0]
    return sorted(models, key=lambda x: x.total_gifts_value, reverse=True)[:10]

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int):
    user = get_user(user_id)
    level = UserLevel(user.level)
    keyboard = [
        [InlineKeyboardButton(f"💰 الرصيد: {user.balance:.2f} USDT | ⭐ {user.points} نقطة", callback_data="balance")],
        [InlineKeyboardButton("🟢 إيداع", callback_data="deposit")],
        [InlineKeyboardButton("🔴 سحب", callback_data="withdraw")],
        [InlineKeyboardButton("📤 تحويل", callback_data="transfer")],
        [InlineKeyboardButton("🔗 الإحالة", callback_data="referral")],
        [InlineKeyboardButton("💬 تواصل عشوائي", callback_data="random_chat")],
        [InlineKeyboardButton("💌 رسائل خاصة", callback_data="private_messages")],
        [InlineKeyboardButton("🎁 الهدايا", callback_data="gifts_menu")],
        [InlineKeyboardButton("⭐ المشاهير", callback_data="popular_models")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
    ]
    if user.is_admin:
        keyboard.append([InlineKeyboardButton("👑 لوحة الأدمن", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def gifts_keyboard():
    keyboard = []
    row = []
    for i, (key, gift) in enumerate(GIFTS.items()):
        row.append(InlineKeyboardButton(f"{gift['emoji']} {gift['price']}ن", callback_data=f"gift_{key}"))
        if len(row) == 3:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def chat_keyboard():
    keyboard = [
        [InlineKeyboardButton("⏭️ شخص آخر", callback_data="chat_next")],
        [InlineKeyboardButton("🛑 إنهاء", callback_data="chat_stop")],
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

💰 محفظتك:
• الرصيد: {user_data.balance:.2f} USDT
• النقاط: ⭐ {user_data.points}
• المستوى: {level.name}

💬 أنظمة التواصل:
• تواصل عشوائي - مجاني
• رسائل خاصة مدفوعة
• إرسال هدايا
• المشاهير والنماذج

🔗 كود الإحالة: `{user_data.referral_code}`
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level = UserLevel(user.level)
    
    text = f"""💰 محفظتك
━━━━━━━━━━━━━━━━
🟢 الرصيد: {user.balance:.2f} USDT
⭐ نقاطك: {user.points}
🏆 مستواك: {level.name}

📊 الإحصائيات:
• المُحالين: {user.referrals_count}
• إجمالي الإيداعات: {user.total_deposited:.2f} USDT
• أرباح الإحالة: {user.earnings:.2f} USDT

🎁 الهدايا:
• أرسلت: {user.total_gifts_received}
• استلمت: {user.total_gifts_value} قيمة
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def private_messages_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = f"""💌 الرسائل الخاصة
━━━━━━━━━━━━━━━━
ثمن الرسالة: {user.private_message_price} نقطة
الحالة: {'✅ مقبول' if user.accept_private_messages else '❌ مغلق'}

━━━━━━━━━━━━━━━━

📝 أرسل رسالة خاصة:
`msg [كود_المستخدم] [الرسالة]`

مثال:
`msg REF-ABC123 مرحباً`

💡 يمكنك تغيير الثمن من الإعدادات
"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def gifts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = f"""🎁 نظام الهدايا
━━━━━━━━━━━━━━━━
نقاطك: ⭐ {user.points}

اختر هدية لإرسالها:
"""
    await update.message.reply_text(text, reply_markup=gifts_keyboard())

async def popular_models_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض المشاهير"""
    models = get_popular_models()
    
    if not models:
        text = "⭐ لا يوجد مشاهير بعد!\n\nكن أول مشهور!"
    else:
        text = "⭐ المشاهير والأكثر تلقياً للهدايا:\n━━━━━━━━━━━━━━━━\n"
        for i, model in enumerate(models, 1):
            text += f"{i}. {model.first_name}\n"
            text += f"   🎁 {model.total_gifts_received} هدية | 💰 {model.total_gifts_value} نقطة\n"
            text += f"   💌 ثمن الرسالة: {model.private_message_price} نقطة\n\n"
    
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(update.message.from_user.id))

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = f"""⚙️ الإعدادات
━━━━━━━━━━━━━━━━
👤 الملف:
• الاسم: {user.first_name}
• الجنس: {user.gender or 'غير محدد'}
• العمر: {user.age or 'غير محدد'}

💌 الرسائل الخاصة:
• قبول الرسائل: {'✅ نعم' if user.accept_private_messages else '❌ لا'}
• ثمن الرسالة: {user.private_message_price} نقطة

🎁 الهدايا:
• قبول الهدايا: {'✅ نعم' if user.accept_gifts else '❌ لا'}

━━━━━━━━━━━━━━━━

📝 الأوامر:
• `سعر [رقم]` - تغيير ثمن الرسالة
• `فتح رسائل` / `غلق رسائل`
• `فتح هدايا` / `غلق هدايا`
• `جنس [رجل/امرأة]`
• `عمر [رقم]`
"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

# ==================== RANDOM CHAT ====================
async def random_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    today = datetime.now().strftime("%Y-%m-%d")
    if user.last_chat_date != today:
        update_user(user_id, {"chats_today": 0, "last_chat_date": today})
        user = get_user(user_id)
    
    if user.chats_today >= config.MAX_CHATS_PER_DAY:
        await update.message.reply_text(f"❌ reached حد المحادثات! ({user.chats_today}/{config.MAX_CHATS_PER_DAY})")
        return
    
    if user.chat_status == "chatting":
        await update.message.reply_text("⚠️ أنت في محادثة! /stop للإنهاء")
        return
    
    if not user.gender:
        await update.message.reply_text("👋 حدد جنسك أولاً:", reply_markup=gender_keyboard())
        return
    
    add_to_waiting(user_id, user.gender)
    update_user(user_id, {"chat_status": "waiting"})
    
    await update.message.reply_text("🔍 جاري البحث... /cancel للإلغاء")
    
    # البحث عن مطابق
    match_id = find_match(user_id)
    if match_id:
        remove_from_waiting(user_id)
        remove_from_waiting(match_id)
        
        create_chat_session(user_id, match_id)
        
        update_user(user_id, {"chat_status": "chatting", "current_chat_partner": match_id})
        update_user(match_id, {"chat_status": "chatting", "current_chat_partner": user_id})
        
        try:
            await context.bot.send_message(user_id, "🎉 تم الإقران! ابدأ المحادثة الآن", reply_markup=chat_keyboard())
            await context.bot.send_message(match_id, "🎉 تم الإقران! ابدأ المحادثة الآن", reply_markup=chat_keyboard())
        except:
            pass
    else:
        await update.message.reply_text("⏳ لا يوجد أحد حالياً... ستصلك إشعاراً")

async def stop_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    if user.chat_status != "chatting" or not user.current_chat_partner:
        await update.message.reply_text("❌ لست في محادثة!")
        return
    
    partner_id = user.current_chat_partner
    
    update_user(user_id, {"chat_status": "idle", "current_chat_partner": None, "chats_today": user.chats_today + 1})
    update_user(partner_id, {"chat_status": "idle", "current_chat_partner": None})
    
    try:
        await context.bot.send_message(partner_id, "❌ انتهت المحادثة")
    except:
        pass
    
    await update.message.reply_text("✅ تم إنهاء المحادثة", reply_markup=main_menu_keyboard(user_id))

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
    elif data == "deposit":
        await query.edit_message_text("🟢 الإيداع\n\nارسل المبلغ:")
    elif data == "withdraw":
        await query.edit_message_text("🔴 السحب\n\nارسل العنوان والمبلغ:")
    elif data == "transfer":
        await query.edit_message_text("📤 التحويل\n\n`تحويل 10 REF-XXXXXX`")
    elif data == "referral":
        user = get_user(user_id)
        await query.edit_message_text(f"🔗 الإحالة\n\nكودك: `{user.referral_code}`\n\nرابط: t.me/{context.bot.username}?start={user.referral_code}")
    elif data == "random_chat":
        await random_chat_command(update, context)
    elif data == "private_messages":
        await private_messages_command(update, context)
    elif data == "gifts_menu":
        await gifts_command(update, context)
    elif data == "popular_models":
        await popular_models_command(update, context)
    elif data == "settings":
        await settings_command(update, context)
    elif data.startswith("gift_"):
        gift_key = data.replace("gift_", "")
        if gift_key in GIFTS:
            gift = GIFTS[gift_key]
            await query.edit_message_text(
                f"🎁 {gift['emoji']} {gift['name']}\n"
                f"السعر: {gift['price']} نقطة\n\n"
                f"أرسل كود المستخدم المرسل إليه:",
                reply_markup=back_keyboard()
            )
    elif data.startswith("gender_"):
        gender = data.replace("gender_", "")
        if gender == "any":
            gender = ""
        update_user(user_id, {"gender": gender})
        await query.edit_message_text(f"✅ تم تحديد الجنس: {gender}", reply_markup=main_menu_keyboard(user_id))
    elif data == "chat_next":
        await stop_chat_command(update, context)
        await random_chat_command(update, context)
    elif data == "chat_stop":
        await stop_chat_command(update, context)
    elif data == "chat_block":
        await stop_chat_command(update, context)
        await update.message.reply_text("🚫 تم بلوك المستخدم")

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    # إذا كان في محادثة عشوائية
    if user.chat_status == "chatting" and user.current_chat_partner:
        partner_id = user.current_chat_partner
        try:
            await context.bot.send_message(partner_id, f"💬 {user.first_name}:\n{text}", reply_markup=chat_keyboard())
        except:
            await update.message.reply_text("❌ تعذر إرسال الرسالة")
        return
    
    # أوامر الإعدادات
    if text.startswith("سعر "):
        try:
            price = int(text.replace("سعر ", ""))
            if 1 <= price <= 1000:
                update_user(user_id, {"private_message_price": price})
                await update.message.reply_text(f"✅ تم تحديد ثمن الرسالة: {price} نقطة")
            else:
                await update.message.reply_text("❌ السعر يجب أن يكون بين 1 و 1000")
        except:
            await update.message.reply_text("❌ صيغة خاطئة")
        return
    
    if text == "فتح رسائل":
        update_user(user_id, {"accept_private_messages": True})
        await update.message.reply_text("✅ تم فتح الرسائل الخاصة")
        return
    
    if text == "غلق رسائل":
        update_user(user_id, {"accept_private_messages": False})
        await update.message.reply_text("❌ تم غلق الرسائل الخاصة")
        return
    
    if text == "فتح هدايا":
        update_user(user_id, {"accept_gifts": True})
        await update.message.reply_text("✅ تم فتح استقبال الهدايا")
        return
    
    if text == "غلق هدايا":
        update_user(user_id, {"accept_gifts": False})
        await update.message.reply_text("❌ تم غلق استقبال الهدايا")
        return
    
    if text.startswith("جنس "):
        gender = text.replace("جنس ", "").strip()
        if gender in ["رجل", "امرأة"]:
            update_user(user_id, {"gender": gender})
            await update.message.reply_text(f"✅ تم تحديد الجنس: {gender}")
        else:
            await update.message.reply_text("❌ اكتب: جنس رجل أو جنس امرأة")
        return
    
    if text.startswith("عمر "):
        try:
            age = int(text.replace("عمر ", ""))
            if 13 <= age <= 99:
                update_user(user_id, {"age": age})
                await update.message.reply_text(f"✅ تم تحديد العمر: {age}")
            else:
                await update.message.reply_text("❌ العمر يجب أن يكون بين 13 و 99")
        except:
            await update.message.reply_text("❌ صيغة خاطئة")
        return
    
    # إرسال رسالة خاصة
    if text.startswith("msg ") or text.startswith("رسالة "):
        try:
            parts = text.replace("msg ", "").replace("رسالة ", "").split(" ", 1)
            if len(parts) == 2:
                recipient_code = parts[0]
                message = parts[1]
                
                # البحث عن المستخدم
                users = db.load_users()
                receiver_id = None
                for uid, udata in users.items():
                    if udata.get("referral_code") == recipient_code:
                        receiver_id = int(uid)
                        break
                
                if not receiver_id:
                    await update.message.reply_text("❌ المستخدم غير موجود!")
                    return
                
                if receiver_id == user_id:
                    await update.message.reply_text("❌ لا يمكنك إرسال رسالة لنفسك!")
                    return
                
                success, msg = send_private_message(user_id, receiver_id, message)
                await update.message.reply_text(msg)
                
                if success:
                    receiver = get_user(receiver_id)
                    try:
                        await context.bot.send_message(
                            receiver_id,
                            f"💌 رسالة خاصة جديدة!\n\nمن: {user.first_name}\n\nالرسالة:\n{message}\n\n💰 ربحت: {int(receiver.private_message_price * 0.8)} نقطة"
                        )
                    except:
                        pass
            else:
                await update.message.reply_text("❌ الصيغة: `msg REF-XXXXXX رسالة`")
        except:
            await update.message.reply_text("❌ خطأ! الصيغة: `msg REF-XXXXXX رسالة`")
        return
    
    # إرسال هدية
    if text.startswith("gift ") or text.startswith("هدية "):
        try:
            parts = text.replace("gift ", "").replace("هدية ", "").split(" ", 1)
            if len(parts) == 2:
                recipient_code = parts[0]
                gift_key = parts[1]
                
                users = db.load_users()
                receiver_id = None
                for uid, udata in users.items():
                    if udata.get("referral_code") == recipient_code:
                        receiver_id = int(uid)
                        break
                
                if not receiver_id:
                    await update.message.reply_text("❌ المستخدم غير موجود!")
                    return
                
                success, msg = send_gift(user_id, receiver_id, gift_key)
                await update.message.reply_text(msg)
                
                if success:
                    receiver = get_user(receiver_id)
                    gift_info = GIFTS.get(gift_key, {})
                    try:
                        await context.bot.send_message(
                            receiver_id,
                            f"🎁 تلقيت هدية! {gift_info.get('emoji', '🎁')}\n\nمن: {user.first_name}\n\n💰 ربحت: {int(gift_info.get('price', 0) * 0.8)} نقطة"
                        )
                    except:
                        pass
            else:
                await update.message.reply_text("❌ الصيغة: `gift REF-XXXXXX sticker_rose`")
        except:
            await update.message.reply_text("❌ خطأ! الصيغة: `gift REF-XXXXXX sticker_rose`")
        return
    
    # تحويل نقاط
    if text.startswith("تحويل "):
        try:
            parts = text.replace("تحويل ", "").split()
            amount = float(parts[0])
            recipient_code = parts[1]
            
            if user.points < amount:
                await update.message.reply_text("❌ نقاطك غير كافية!")
                return
            
            users = db.load_users()
            receiver_id = None
            for uid, udata in users.items():
                if udata.get("referral_code") == recipient_code:
                    receiver_id = int(uid)
                    break
            
            if not receiver_id:
                await update.message.reply_text("❌ المستخدم غير موجود!")
                return
            
            update_user(user_id, {"points": user.points - amount})
            receiver = get_user(receiver_id)
            update_user(receiver_id, {"points": receiver.points + amount})
            
            await update.message.reply_text(f"✅ تم تحويل {amount} نقطة!")
        except:
            await update.message.reply_text("❌ خطأ! الصيغة: `تحويل 10 REF-XXXXXX`")
        return
    
    await update.message.reply_text("❌ أمر غير معروف!\n\nاستخدم /start", reply_markup=main_menu_keyboard(user_id))

# ==================== MAIN ====================
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("chat", random_chat_command))
    app.add_handler(CommandHandler("stop", stop_chat_command))
    app.add_handler(CommandHandler("msg", lambda u, c: handle_message(u, c)))  # رسالة خاصة
    app.add_handler(CommandHandler("gift", lambda u, c: handle_message(u, c)))  # هدية
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("models", popular_models_command))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(handle_message))
    
    print("🤖 Crypto Wallet Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
