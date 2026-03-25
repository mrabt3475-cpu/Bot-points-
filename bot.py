"""
💰 Smart Wallet Bot - Ultimate Edition
محفظة ذكية مع نقاط ودفع - بأحدث التقنيات

🚀 التقنيات المستخدمة:
- Python 3.11+ Type Hints
- Pydantic Models
- Async/Await
- Context Managers
- Logging System
- Rate Limiting
- Environment Variables
- Security Best Practices
"""

from __future__ import annotations

import os
import sys
import json
import hashlib
import hmac
import random
import string
import time
import uuid
import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any, Union
from functools import wraps, lru_cache
from dataclasses import dataclass, field, asdict
from pathlib import Path

# Pydantic for validation
try:
    from pydantic import BaseModel, Field, validator, field_validator
    USE_PYDANTIC = True
except ImportError:
    USE_PYDANTIC = False
    BaseModel = object

# Telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIGURATION ====================
class Settings:
    """إعدادات التطبيق"""
    
    # Bot
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")
    
    # Wallet
    MIN_DEPOSIT: float = 1.0
    MIN_WITHDRAWAL: float = 5.0
    MAX_WITHDRAWAL_DAILY: float = 1000.0
    WITHDRAWAL_FEE: float = 1.0
    TRANSFER_FEE: float = 0.5
    
    # Points
    POINTS_PER_USDT: float = 100.0
    REFERRAL_BONUS: int = 50
    DAILY_BONUS: int = 10
    
    # Security
    RATE_LIMIT_PER_MINUTE: int = 10
    MAX_FAILED_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30
    
    # Database
    DB_PATH: str = os.getenv("DB_PATH", "./data")
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "bot.log")

settings = Settings()

# ==================== LOGGING ====================
class Logger:
    """نظام تسجيل محسّن"""
    
    _instance: Optional[logging.Logger] = None
    
    @classmethod
    def get_logger(cls, name: str = "WalletBot") -> logging.Logger:
        if cls._instance is None:
            logger = logging.getLogger(name)
            logger.setLevel(getattr(logging, settings.LOG_LEVEL))
            
            # Console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.DEBUG)
            
            # File handler
            file_handler = logging.FileHandler(settings.LOG_FILE)
            file_handler.setLevel(logging.INFO)
            
            # Formatter
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            console_handler.setFormatter(formatter)
            file_handler.setFormatter(formatter)
            
            logger.addHandler(console_handler)
            logger.addHandler(file_handler)
            
            cls._instance = logger
        
        return cls._instance

logger = Logger.get_logger()

# ==================== ENUMS ====================
class TransactionType(str, Enum):
    DEPOSIT = "إيداع"
    WITHDRAWAL = "سحب"
    TRANSFER = "تحويل"
    PAYMENT = "دفع"
    REFERRAL_BONUS = "مكافأة إحالة"
    DAILY_BONUS = "مكافأة يومية"
    GAME_REWARD = "مكافأة لعبة"

class TransactionStatus(str, Enum):
    PENDING = "معلق"
    COMPLETED = "مكتمل"
    FAILED = "فاشل"
    CANCELLED = "ملغى"

class WalletStatus(str, Enum):
    INACTIVE = "غير نشط"
    ACTIVE = "نشط"
    VERIFIED = "موثق"
    FROZEN = "مجمّد"

# ==================== PYDANTIC MODELS ====================
if USE_PYDANTIC:
    class UserModel(BaseModel):
        """نموذج المستخدم"""
        user_id: int
        username: str = ""
        first_name: str = ""
        last_name: str = ""
        wallet_address: str = ""
        balance: float = 0.0
        wallet_status: str = "inactive"
        points: int = 0
        points_lifetime: int = 0
        level: int = 1
        experience: int = 0
        referral_code: str = ""
        referred_by: Optional[int] = None
        referrals_count: int = 0
        referral_earnings: float = 0.0
        subscription_tier: str = "free"
        is_verified: bool = False
        is_admin: bool = False
        is_banned: bool = False
        pin_code: str = ""
        failed_attempts: int = 0
        lock_until: str = ""
        total_deposited: float = 0.0
        total_withdrawn: float = 0.0
        join_date: str = field(default_factory=lambda: datetime.now().isoformat())
        last_active: str = field(default_factory=lambda: datetime.now().isoformat())
        
        @field_validator('balance')
        @classmethod
        def validate_balance(cls, v: float) -> float:
            if v < 0:
                raise ValueError("الرصيد لا يمكن أن يكون سالباً")
            return round(v, 2)
    
    class TransactionModel(BaseModel):
        """نموذج المعاملة"""
        id: str
        user_id: int
        type: str
        amount: float
        fee: float = 0.0
        status: str = "معلق"
        recipient_id: Optional[int] = None
        description: str = ""
        created_at: str = field(default_factory=lambda: datetime.now().isoformat())
        completed_at: str = ""
        
        @field_validator('amount')
        @classmethod
        def validate_amount(cls, v: float) -> float:
            if v <= 0:
                raise ValueError("المبلغ يجب أن يكون موجباً")
            return round(v, 2)

# ==================== DATACLASSES ====================
@dataclass
class User:
    """مستخدم المحفظة"""
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    wallet_address: str = ""
    balance: float = 0.0
    wallet_status: str = "inactive"
    points: int = 0
    points_lifetime: int = 0
    level: int = 1
    experience: int = 0
    referral_code: str = ""
    referred_by: Optional[int] = None
    referrals_count: int = 0
    referral_earnings: float = 0.0
    subscription_tier: str = "free"
    is_verified: bool = False
    is_admin: bool = False
    is_banned: bool = False
    pin_code: str = ""
    failed_attempts: int = 0
    lock_until: str = ""
    total_deposited: float = 0.0
    total_withdrawn: float = 0.0
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Transaction:
    """معاملة مالية"""
    id: str
    user_id: int
    type: str
    amount: float
    fee: float = 0.0
    status: str = "معلق"
    recipient_id: Optional[int] = None
    description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""

# ==================== DATABASE ====================
class Database:
    """قاعدة بيانات محسّنة"""
    
    def __init__(self, db_path: str = settings.DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self.users_file = self.db_path / "users.json"
        self.transactions_file = self.db_path / "transactions.json"
        self.rate_limits_file = self.db_path / "rate_limits.json"
        self.cache_file = self.db_path / "cache.json"
        
        # Initialize files
        self._init_file(self.users_file, {})
        self._init_file(self.transactions_file, [])
        self._init_file(self.rate_limits_file, {})
        self._init_file(self.cache_file, {})
        
        logger.info("✅ Database initialized")
    
    def _init_file(self, path: Path, default: Any) -> None:
        """تهيئة الملف"""
        if not path.exists():
            self._save_json(path, default)
    
    def _load_json(self, path: Path) -> Any:
        """تحميل JSON"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            logger.error(f"Error loading {path}: {e}")
            return {} if "users" in str(path) or "rate" in str(path) else []
    
    def _save_json(self, path: Path, data: Any) -> None:
        """حفظ JSON"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving {path}: {e}")
    
    @property
    def users(self) -> Dict:
        return self._load_json(self.users_file)
    
    @users.setter
    def users(self, data: Dict) -> None:
        self._save_json(self.users_file, data)
    
    @property
    def transactions(self) -> List:
        return self._load_json(self.transactions_file)
    
    @transactions.setter
    def transactions(self, data: List) -> None:
        self._save_json(self.transactions_file, data)
    
    @property
    def rate_limits(self) -> Dict:
        return self._load_json(self.rate_limits_file)
    
    @rate_limits.setter
    def rate_limits(self, data: Dict) -> None:
        self._save_json(self.rate_limits_file, data)

# Initialize database
db = Database()

# ==================== CACHE SYSTEM ====================
class Cache:
    """نظام التخزين المؤقت"""
    
    def __init__(self, ttl: int = 300):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._ttl = ttl
    
    def get(self, key: str) -> Optional[Any]:
        """الحصول على قيمة"""
        if key in self._cache:
            value, expiry = self._cache[key]
            if time.time() < expiry:
                return value
            del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """تعيين قيمة"""
        expiry = time.time() + (ttl or self._ttl)
        self._cache[key] = (value, expiry)
    
    def delete(self, key: str) -> None:
        """حذف قيمة"""
        if key in self._cache:
            del self._cache[key]
    
    def clear(self) -> None:
        """مسح كل شيء"""
        self._cache.clear()

cache = Cache()

# ==================== HELPERS ====================
def generate_id(prefix: str = "ID", length: int = 12) -> str:
    """توليد معرف فريد"""
    return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=length))}"

def generate_wallet_address() -> str:
    """توليد عنوان محفظة"""
    return f"0x{''.join(random.choices('0123456789abcdef', k=40))}"

def generate_referral_code() -> str:
    """توليد كود إحالة"""
    return f"REF{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"

def hash_pin(pin: str) -> str:
    """تشفير PIN"""
    return hashlib.sha256(pin.encode()).hexdigest()[:8]

def format_amount(amount: float, decimals: int = 2) -> str:
    """تنسيق المبلغ"""
    return f"{amount:,.{decimals}f}"

# ==================== RATE LIMITING ====================
class RateLimiter:
    """محدد المعدل"""
    
    def __init__(self, max_requests: int = 10, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self._requests: Dict[int, List[float]] = {}
    
    def is_allowed(self, user_id: int) -> bool:
        """التحقق من السماح"""
        now = time.time()
        
        if user_id not in self._requests:
            self._requests[user_id] = []
        
        # إزالة الطلبات القديمة
        self._requests[user_id] = [
            t for t in self._requests[user_id]
            if now - t < self.window
        ]
        
        if len(self._requests[user_id]) >= self.max_requests:
            return False
        
        self._requests[user_id].append(now)
        return True
    
    def reset(self, user_id: int) -> None:
        """إعادة تعيين"""
        if user_id in self._requests:
            del self._requests[user_id]

rate_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window=60
)

# ==================== USER OPERATIONS ====================
class UserManager:
    """مدير المستخدمين"""
    
    @staticmethod
    def get(user_id: int) -> User:
        """الحصول على مستخدم"""
        # Try cache first
        cached = cache.get(f"user_{user_id}")
        if cached:
            return cached
        
        users = db.users
        if str(user_id) not in users:
            user = User(
                user_id=user_id,
                wallet_address=generate_wallet_address(),
                referral_code=generate_referral_code()
            )
            users[str(user_id)] = asdict(user)
            db.users = users
            cache.set(f"user_{user_id}", user)
            return user
        
        user = User(**users[str(user_id)])
        cache.set(f"user_{user_id}", user)
        return user
    
    @staticmethod
    def update(user_id: int, data: Dict) -> None:
        """تحديث مستخدم"""
        users = db.users
        if str(user_id) in users:
            users[str(user_id)].update(data)
            db.users = users
            cache.delete(f"user_{user_id}")
            logger.info(f"User {user_id} updated")
    
    @staticmethod
    def get_level_info(level: int) -> Tuple[str, int]:
        """معلومات المستوى"""
        levels = {
            1: ("مبتدئ", 0),
            2: ("برونزي", 500),
            3: ("فضي", 1500),
            4: ("ذهبي", 3500),
            5: ("بلاتيني", 7000),
            6: ("ماسي", 15000),
            7: ("VIP", 30000),
        }
        return levels.get(level, ("غير معروف", 0))
    
    @staticmethod
    def calculate_level(experience: int) -> int:
        """حساب المستوى"""
        thresholds = [0, 500, 1500, 3500, 7000, 15000, 30000]
        for i, threshold in enumerate(thresholds):
            if experience < threshold:
                return i + 1
        return len(thresholds) + 1

# ==================== WALLET OPERATIONS ====================
class WalletManager:
    """مدير المحفظة"""
    
    @staticmethod
    def create_transaction(
        user_id: int,
        txn_type: TransactionType,
        amount: float,
        description: str = "",
        recipient_id: Optional[int] = None,
        fee: float = 0.0
    ) -> Transaction:
        """إنشاء معاملة"""
        txn = Transaction(
            id=generate_id("TXN"),
            user_id=user_id,
            type=txn_type.value,
            amount=amount,
            fee=fee,
            status=TransactionStatus.PENDING.value,
            description=description,
            recipient_id=recipient_id
        )
        
        transactions = db.transactions
        transactions.append(asdict(txn))
        db.transactions = transactions
        
        logger.info(f"Transaction created: {txn.id} - {txn_type.value} - {amount}")
        return txn
    
    @staticmethod
    def complete_transaction(txn_id: str) -> None:
        """إكمال معاملة"""
        transactions = db.transactions
        for txn in transactions:
            if txn["id"] == txn_id:
                txn["status"] = TransactionStatus.COMPLETED.value
                txn["completed_at"] = datetime.now().isoformat()
                break
        db.transactions = transactions
    
    @staticmethod
    def deposit(user_id: int, amount: float) -> Tuple[bool, str]:
        """إيداع"""
        if amount < settings.MIN_DEPOSIT:
            return False, f"الحد الأدنى: {settings.MIN_DEPOSIT} USDT"
        
        user = UserManager.get(user_id)
        
        # Create transaction
        txn = WalletManager.create_transaction(
            user_id, TransactionType.DEPOSIT, amount, "إيداع"
        )
        
        # Update balance
        UserManager.update(user_id, {
            "balance": user.balance + amount,
            "total_deposited": user.total_deposited + amount,
            "wallet_status": WalletStatus.ACTIVE.value
        })
        
        # Complete transaction
        WalletManager.complete_transaction(txn.id)
        
        # Add points
        points = int(amount * settings.POINTS_PER_USDT)
        UserManager.update(user_id, {
            "points": user.points + points,
            "points_lifetime": user.points_lifetime + points
        })
        
        logger.info(f"User {user_id} deposited {amount} USDT")
        
        return True, (
            f"✅ تم الإيداع!\n\n"
            f"💰 المبلغ: {format_amount(amount)} USDT\n"
            f"⭐ النقاط: +{points}\n"
            f"💳 الرصيد: {format_amount(user.balance + amount)} USDT"
        )
    
    @staticmethod
    def withdraw(user_id: int, amount: float, address: str) -> Tuple[bool, str]:
        """سحب"""
        user = UserManager.get(user_id)
        
        if amount < settings.MIN_WITHDRAWAL:
            return False, f"الحد الأدنى: {settings.MIN_WITHDRAWAL} USDT"
        
        fee = settings.WITHDRAWAL_FEE
        total = amount + fee
        
        if user.balance < total:
            return False, "رصيدك غير كافٍ!"
        
        # Create transaction
        txn = WalletManager.create_transaction(
            user_id, TransactionType.WITHDRAWAL, amount,
            f"سحب إلى {address[:10]}...", fee=fee
        )
        
        # Update balance
        UserManager.update(user_id, {
            "balance": user.balance - total,
            "total_withdrawn": user.total_withdrawn + amount
        })
        
        WalletManager.complete_transaction(txn.id)
        
        logger.info(f"User {user_id} withdrew {amount} USDT")
        
        return True, (
            f"✅ تم السحب!\n\n"
            f"💰 المبلغ: {format_amount(amount)} USDT\n"
            f"📝 الرسوم: {format_amount(fee)} USDT\n"
            f"💳 الرصيد: {format_amount(user.balance - total)} USDT"
        )
    
    @staticmethod
    def transfer(sender_id: int, recipient_code: str, amount: float) -> Tuple[bool, str]:
        """تحويل"""
        sender = UserManager.get(sender_id)
        
        if amount <= 0:
            return False, "المبلغ يجب أن يكون موجباً"
        
        if sender.balance < amount:
            return False, "رصيدك غير كافٍ!"
        
        # Find recipient
        users = db.users
        recipient_id = None
        for uid, udata in users.items():
            if udata.get("referral_code") == recipient_code:
                recipient_id = int(uid)
                break
        
        if not recipient_id:
            return False, "المستخدم غير موجود!"
        
        if recipient_id == sender_id:
            return False, "لا يمكنك تحويل لنفسك!"
        
        fee = amount * settings.TRANSFER_FEE / 100
        total = amount + fee
        
        if sender.balance < total:
            return False, f"تحتاج {format_amount(total)} USDT"
        
        recipient = UserManager.get(recipient_id)
        
        # Create transaction
        txn = WalletManager.create_transaction(
            sender_id, TransactionType.TRANSFER, amount,
            f"تحويل لـ {recipient.first_name}", recipient_id, fee
        )
        
        # Transfer
        UserManager.update(sender_id, {
            "balance": sender.balance - total,
            "total_transferred": sender.total_transferred + amount
        })
        UserManager.update(recipient_id, {
            "balance": recipient.balance + amount
        })
        
        WalletManager.complete_transaction(txn.id)
        
        logger.info(f"User {sender_id} transferred {amount} to {recipient_id}")
        
        return True, (
            f"✅ تم التحويل!\n\n"
            f"💰 المبلغ: {format_amount(amount)} USDT\n"
            f"📝 الرسوم: {format_amount(fee)} USDT\n"
            f"👤 المستلم: {recipient.first_name}"
        )
    
    @staticmethod
    def get_transactions(user_id: int, limit: int = 10) -> List[Transaction]:
        """الحصول على المعاملات"""
        transactions = db.transactions
        user_txns = [
            Transaction(**t) for t in transactions
            if t["user_id"] == user_id
        ]
        return sorted(user_txns, key=lambda x: x.created_at, reverse=True)[:limit]

# ==================== KEYBOARDS ====================
def create_main_keyboard(user_id: int) -> InlineKeyboardMarkup:
    """إنشاء لوحة المفاتيح الرئيسية"""
    user = UserManager.get(user_id)
    level_name, _ = UserManager.get_level_info(user.level)
    
    keyboard = [
        [InlineKeyboardButton(
            f"💰 {format_amount(user.balance)} USDT | ⭐ {user.points}",
            callback_data="wallet"
        )],
        [
            InlineKeyboardButton("🟢 إيداع", callback_data="deposit"),
            InlineKeyboardButton("🔴 سحب", callback_data="withdraw")
        ],
        [
            InlineKeyboardButton("📤 تحويل", callback_data="transfer"),
            InlineKeyboardButton("📜 سِجل", callback_data="transactions")
        ],
        [
            InlineKeyboardButton("🎁 مكافأة", callback_data="daily_bonus"),
            InlineKeyboardButton("🔗 إحالة", callback_data="referral")
        ],
        [
            InlineKeyboardButton("📊 إحصائيات", callback_data="stats"),
            InlineKeyboardButton("⚙️ إعدادات", callback_data="settings")
        ],
    ]
    return InlineKeyboardMarkup(keyboard)

def create_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 رجوع", callback_data="back")
    ]])

# ==================== BOT HANDLERS ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج بدء البوت"""
    user = update.message.from_user
    user_id = user.id
    
    # Check rate limit
    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text("⏳太多 الطلبات! انتظر قليلاً")
        return
    
    # Process referral
    args = context.args
    if args:
        ref_code = args[0]
        users = db.users
        for uid, udata in users.items():
            if udata.get("referral_code") == ref_code and int(uid) != user_id:
                if not UserManager.get(user_id).referred_by:
                    UserManager.update(user_id, {"referred_by": int(uid)})
                break
    
    user_data = UserManager.get(user_id)
    level_name, _ = UserManager.get_level_info(user_data.level)
    
    welcome = f"""💰 مرحباً {user.first_name}!

🏦 محفظتك:
• الرصيد: {format_amount(user_data.balance)} USDT
• النقاط: ⭐ {user_data.points}
• المستوى: {level_name}

🔗 كود الإحالة: `{user_data.referral_code}`

💡 الأوامر:
• إيداع [المبلغ]
• سحب [المبلغ] [العنوان]
• تحويل [المبلغ] [كود]
• نقاط
• مكافأة
"""
    await update.message.reply_text(welcome, reply_markup=create_main_keyboard(user_id))
    logger.info(f"User {user_id} started bot")

async def wallet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج المحفظة"""
    user_id = update.message.from_user.id
    user = UserManager.get(user_id)
    level_name, _ = UserManager.get_level_info(user.level)
    
    text = f"""💰 محفظتك
━━━━━━━━━━━━━━━━
💵 الرصيد: {format_amount(user.balance)} USDT
⭐ النقاط: {user.points}
🏆 المستوى: {level_name}

📊 الإحصائيات:
• الإيداعات: {format_amount(user.total_deposited)} USDT
• السحبات: {format_amount(user.total_withdrawn)} USDT

📧 العنوان: `{user.wallet_address}`
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=create_main_keyboard(user_id))

async def points_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج النقاط"""
    user_id = update.message.from_user.id
    user = UserManager.get(user_id)
    level_name, _ = UserManager.get_level_info(user.level)
    
    text = f"""⭐ نقاطي
━━━━━━━━━━━━━━━━
💰 الرصيد: {user.points} نقطة
📊 إجمالي النقاط: {user.points_lifetime}
🏆 مستواك: {level_name}

💡 كيف تكسب:
• الإيداع: {int(settings.POINTS_PER_USDT)} نقطة/USDT
• الإحالة: {settings.REFERRAL_BONUS} نقطة
• المكافأة اليومية: {settings.DAILY_BONUS} نقطة
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=create_main_keyboard(user_id))

async def daily_bonus_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج المكافأة اليومية"""
    user_id = update.message.from_user.id
    user = UserManager.get(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if hasattr(user, 'last_bonus_date') and user.last_bonus_date == today:
        await update.message.reply_text(
            "❌ المكافأة اليومية مُطالَبة بالفعل!\n\nجرّب غداً!",
            reply_markup=create_main_keyboard(user_id)
        )
        return
    
    bonus = settings.DAILY_BONUS
    UserManager.update(user_id, {
        "points": user.points + bonus,
        "last_bonus_date": today
    })
    
    await update.message.reply_text(
        f"✅ مكافأة يومية: +{bonus} نقطة!\n\n"
        f"⭐ نقاطك الجديدة: {user.points + bonus}",
        reply_markup=create_main_keyboard(user_id)
    )
    logger.info(f"User {user_id} claimed daily bonus")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back":
        await wallet_handler(update, context)
    elif data == "wallet":
        await wallet_handler(update, context)
    elif data == "deposit":
        await query.edit_message_text(
            "🟢 الإيداع\n\nأرسل المبلغ:\n`إيداع 100`",
            reply_markup=create_back_keyboard()
        )
    elif data == "withdraw":
        await query.edit_message_text(
            f"🔴 السحب\n\n"
            f"الحد الأدنى: {settings.MIN_WITHDRAWAL} USDT\n\n"
            f"الصيغة: `سحب 10 0x123...`",
            reply_markup=create_back_keyboard()
        )
    elif data == "transfer":
        await query.edit_message_text(
            f"📤 التحويل\n\n"
            f"الرسوم: {settings.TRANSFER_FEE}%\n\n"
            f"الصيغة: `تحويل 10 REFABC123`",
            reply_markup=create_back_keyboard()
        )
    elif data == "transactions":
        txns = WalletManager.get_transactions(user_id)
        text = "📜 المعاملات\n━━━━━━━━━━━━━━━━\n"
        for t in txns[:8]:
            emoji = "✅" if t.status == "مكتمل" else "⏳"
            text += f"{emoji} {t.type}: {format_amount(t.amount)}\n"
        await query.edit_message_text(text, reply_markup=create_back_keyboard())
    elif data == "daily_bonus":
        user = UserManager.get(user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        if hasattr(user, 'last_bonus_date') and user.last_bonus_date == today:
            await query.edit_message_text("❌ مُطالَبة!", reply_markup=create_back_keyboard())
        else:
            bonus = settings.DAILY_BONUS
            UserManager.update(user_id, {
                "points": user.points + bonus,
                "last_bonus_date": today
            })
            await query.edit_message_text(
                f"✅ +{bonus} نقطة!",
                reply_markup=create_main_keyboard(user_id)
            )
    elif data == "referral":
        user = UserManager.get(user_id)
        await query.edit_message_text(
            f"🔗 الإحالة\n\n"
            f"كودك: `{user.referral_code}`\n\n"
            f"المُحالين: {user.referrals_count}\n"
            f"الأرباح: {user.referral_earnings} نقطة",
            reply_markup=create_back_keyboard()
        )
    elif data == "stats":
        user = UserManager.get(user_id)
        level_name, _ = UserManager.get_level_info(user.level)
        await query.edit_message_text(
            f"📊 الإحصائيات\n━━━━━━━━━━━━━━━━\n"
            f"🏆 المستوى: {level_name}\n"
            f"💰 الرصيد: {format_amount(user.balance)} USDT\n"
            f"⭐ النقاط: {user.points}\n"
            f"📥 الإيداعات: {format_amount(user.total_deposited)}\n"
            f"📤 السحبات: {format_amount(user.total_withdrawn)}",
            reply_markup=create_main_keyboard(user_id)
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الرسائل"""
    text = update.message.text
    user_id = update.message.from_user.id
    
    # Rate limit
    if not rate_limiter.is_allowed(user_id):
        await update.message.reply_text("⏳太多 الطلبات!")
        return
    
    # Deposit
    if text.startswith("إيداع "):
        try:
            amount = float(text.replace("إيداع ", ""))
            success, msg = WalletManager.deposit(user_id, amount)
            await update.message.reply_text(msg, reply_markup=create_main_keyboard(user_id))
        except ValueError:
            await update.message.reply_text("❌ أدخل رقماً صحيحاً!")
        return
    
    # Withdraw
    if text.startswith("سحب "):
        try:
            parts = text.replace("سحب ", "").split()
            amount = float(parts[0])
            address = parts[1] if len(parts) > 1 else ""
            if not address:
                await update.message.reply_text("❌ أدخل العنوان!")
                return
            success, msg = WalletManager.withdraw(user_id, amount, address)
            await update.message.reply_text(msg, reply_markup=create_main_keyboard(user_id))
        except (ValueError, IndexError):
            await update.message.reply_text("❌ الصيغة: `سحب 10 0x123...`")
        return
    
    # Transfer
    if text.startswith("تحويل "):
        try:
            parts = text.replace("تحويل ", "").split()
            amount = float(parts[0])
            code = parts[1] if len(parts) > 1 else ""
            success, msg = WalletManager.transfer(user_id, code, amount)
            await update.message.reply_text(msg, reply_markup=create_main_keyboard(user_id))
        except (ValueError, IndexError):
            await update.message.reply_text("❌ الصيغة: `تحويل 10 REFABC123`")
        return
    
    # Points
    if text == "نقاط":
        await points_handler(update, context)
        return
    
    # Bonus
    if text == "مكافأة":
        await daily_bonus_handler(update, context)
        return
    
    # Default
    await update.message.reply_text(
        "❌ أمر غير معروف!\n\n/start",
        reply_markup=create_main_keyboard(user_id)
    )

# ==================== MAIN ====================
def main() -> None:
    """تشغيل البوت"""
    logger.info("🚀 Starting Wallet Bot...")
    
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram library not available!")
        return
    
    app = Application.builder().token(settings.BOT_TOKEN).build()
    
    # Handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("wallet", wallet_handler))
    app.add_handler(CommandHandler("points", points_handler))
    app.add_handler(CommandHandler("bonus", daily_bonus_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""الأوامر:
/start - بدء
/wallet - المحفظة
/points - النقاط
/bonus - مكافأة

إيداع [المبلغ]
سحب [المبلغ] [عنوان]
تحويل [المبلغ] [كود]
"""))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(message_handler))
    
    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
