"""
💰 Smart Wallet Bot - محفظة ذكية مع نقاط ودفع
Electronic Wallet + Points System + Payments
"""

import os
import json
import hashlib
import hmac
import random
import string
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, PreCheckoutQueryHandler

# ==================== CONFIG ====================
@dataclass
class Config:
    BOT_TOKEN: str = "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc"
    # المحفظة
    MIN_DEPOSIT: float = 1.0
    MIN_WITHDRAWAL: float = 5.0
    MAX_WITHDRAWAL_DAILY: float = 1000.0
    WITHDRAWAL_FEE: float = 1.0
    TRANSFER_FEE: float = 0.5
    # النقاط
    POINTS_PER_USDT: float = 100.0
    REFERRAL_BONUS: int = 50
    REFERRAL_COMMISSION: float = 0.05
    DAILY_BONUS: int = 10
    # الدفع
    PAYMENT_PROVIDER_TOKEN: str = ""  # Stripe أو غيره
    SUBSCRIPTION_PRICE: int = 9.99  # دولار
    # الأمان
    VERIFICATION_REQUIRED: bool = True
    KYC_ENABLED: bool = True

config = Config()

# ==================== ENUMS ====================
class TransactionType(Enum):
    DEPOSIT = "إيداع"
    WITHDRAWAL = "سحب"
    TRANSFER = "تحويل"
    PAYMENT = "دفع"
    PURCHASE = "شراء"
    REFERRAL_BONUS = "مكافأة إحالة"
    DAILY_BONUS = "مكافأة يومية"
    GAME_REWARD = "مكافأة لعبة"
    SUBSCRIPTION = "اشتراك"
    REFUND = "استرداد"

class TransactionStatus(Enum):
    PENDING = "معلق"
    COMPLETED = "مكتمل"
    FAILED = "فاشل"
    CANCELLED = "ملغى"
    VERIFYING = "قيد التحقق"

class WalletStatus(Enum):
    INACTIVE = "غير نشط"
    ACTIVE = "نشط"
    VERIFIED = "موثق"
    FROZEN = "مجمّد"

class SubscriptionTier(Enum):
    FREE = "مجاني"
    BASIC = "أساسي"
    PREMIUM = "مميز"
    VIP = "VIP"

# ==================== DATA CLASSES ====================
@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    # المحفظة
    wallet_address: str = ""
    balance: float = 0.0
    wallet_status: str = "inactive"
    # النقاط
    points: int = 0
    points_lifetime: int = 0
    # المستوى
    level: int = 1
    experience: int = 0
    # الإحالة
    referral_code: str = ""
    referred_by: int = None
    referrals_count: int = 0
    referral_earnings: float = 0.0
    # الاشتراك
    subscription_tier: str = "free"
    subscription_expires: str = ""
    # التحقق
    is_verified: bool = False
    kyc_status: str = "none"  # none, pending, approved, rejected
    # الأمان
    pin_code: str = ""
    two_factor_secret: str = ""
    failed_attempts: int = 0
    lock_until: str = ""
    # الإحصائيات
    total_deposited: float = 0.0
    total_withdrawn: float = 0.0
    total_transferred: float = 0.0
    total_spent: float = 0.0
    # الوقت
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    # الأ：admin
    is_admin: bool = False
    is_banned: bool = False

@dataclass
class Transaction:
    id: str
    user_id: int
    type: str
    amount: float
    fee: float
    status: str
    wallet_address: str = ""
    tx_hash: str = ""
    recipient_id: int = None
    description: str = ""
    payment_method: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: str = ""

@dataclass
class PaymentMethod:
    id: str
    user_id: int
    type: str  # card, wallet, crypto
    provider: str
    last_four: str = ""
    is_default: bool = False
    is_verified: bool = False
    expiry_date: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Invoice:
    id: str
    user_id: int
    amount: float
    currency: str
    description: str
    status: str
    payment_url: str = ""
    expires_at: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Subscription:
    id: str
    user_id: int
    tier: str
    price: float
    start_date: str
    end_date: str
    auto_renew: bool = False
    status: str = "active"

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.users_file = "users.json"
        self.transactions_file = "transactions.json"
        self.payment_methods_file = "payment_methods.json"
        self.invoices_file = "invoices.json"
        self.subscriptions_file = "subscriptions.json"
    
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
    
    def load_payment_methods(self) -> List:
        try:
            with open(self.payment_methods_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_payment_methods(self, methods: List):
        with open(self.payment_methods_file, "w") as f:
            json.dump(methods, f, ensure_ascii=False, indent=2)
    
    def load_invoices(self) -> List:
        try:
            with open(self.invoices_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_invoices(self, invoices: List):
        with open(self.invoices_file, "w") as f:
            json.dump(invoices, f, ensure_ascii=False, indent=2)
    
    def load_subscriptions(self) -> List:
        try:
            with open(self.subscriptions_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_subscriptions(self, subs: List):
        with open(self.subscriptions_file, "w") as f:
            json.dump(subs, f, ensure_ascii=False, indent=2)

db = Database()

# ==================== HELPERS ====================
def generate_id(prefix: str = "ID", length: int = 12) -> str:
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_wallet_address() -> str:
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))

def generate_referral_code() -> str:
    return "REF" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))

def get_user(user_id: int) -> User:
    users = db.load_users()
    if str(user_id) not in users:
        user = User(
            user_id=user_id,
            wallet_address=generate_wallet_address(),
            referral_code=generate_referral_code()
        )
        users[str(user_id)] = asdict(user)
        db.save_users(users)
        return user
    return User(**users[str(user_id)])

def update_user(user_id: int, data: Dict):
    users = db.load_users()
    if str(user_id) in users:
        users[str(user_id)].update(data)
        db.save_users(users)

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

def calculate_level(experience: int) -> int:
    thresholds = [0, 500, 1500, 3500, 7000, 15000, 30000, 50000]
    for i, threshold in enumerate(thresholds):
        if experience < threshold:
            return i + 1
    return len(thresholds) + 1

# ==================== WALLET OPERATIONS ====================
def create_transaction(user_id: int, txn_type: TransactionType, amount: float, description: str = "", recipient_id: int = None, fee: float = 0.0) -> Transaction:
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

def deposit(user_id: int, amount: float, payment_method: str = "card") -> Tuple[bool, str]:
    """إيداع"""
    if amount < config.MIN_DEPOSIT:
        return False, f"الحد الأدنى للإيداع: {config.MIN_DEPOSIT} USDT"
    
    user = get_user(user_id)
    
    # إنشاء معاملة
    txn = create_transaction(user_id, TransactionType.DEPOSIT, amount, f"إيداع عبر {payment_method}")
    
    # تحديث الرصيد
    update_user(user_id, {
        "balance": user.balance + amount,
        "total_deposited": user.total_deposited + amount,
        "wallet_status": "active"
    })
    
    complete_transaction(txn.id)
    
    # منح نقاط
    points_earned = int(amount * config.POINTS_PER_USDT)
    update_user(user_id, {"points": user.points + points_earned, "points_lifetime": user.points_lifetime + points_earned})
    
    return True, f"✅ تم الإيداع!

💰 المبلغ: {amount} USDT
⭐ النقاط المكتسبة: {points_earned}
💳 الرصيد الجديد: {user.balance + amount} USDT"

def withdraw(user_id: int, amount: float, address: str) -> Tuple[bool, str]:
    """سحب"""
    user = get_user(user_id)
    
    if amount < config.MIN_WITHDRAWAL:
        return False, f"الحد الأدنى للسحب: {config.MIN_WITHDRAWAL} USDT"
    
    if user.balance < amount:
        return False, "رصيدك غير كافٍ!"
    
    fee = config.WITHDRAWAL_FEE
    total = amount + fee
    
    if user.balance < total:
        return False, f"تحتاج {total} USDT (شامل الرسوم)"
    
    # التحقق من الحد اليومي
    today = datetime.now().strftime("%Y-%m-%d")
    today_withdrawn = get_today_withdrawals(user_id)
    
    if today_withdrawn + amount > config.MAX_WITHDRAWAL_DAILY:
        return False, f"الحد اليومي: {config.MAX_WITHDRAWAL_DAILY} USDT"
    
    # إنشاء معاملة
    txn = create_transaction(user_id, TransactionType.WITHDRAWAL, amount, f"سحب إلى {address}", fee=fee)
    
    # تحديث الرصيد
    update_user(user_id, {
        "balance": user.balance - total,
        "total_withdrawn": user.total_withdrawn + amount
    })
    
    complete_transaction(txn.id)
    
    return True, f"✅ تم إنشاء طلب السحب!

💰 المبلغ: {amount} USDT
📝 الرسوم: {fee} USDT
💳 الرصيد الجديد: {user.balance - total} USDT
⏳ awaiting التحويل خلال 24 ساعة"

def transfer(sender_id: int, recipient_code: str, amount: float) -> Tuple[bool, str]:
    """تحويل"""
    sender = get_user(sender_id)
    
    if amount <= 0:
        return False, "المبلغ يجب أن يكون موجباً"
    
    if sender.balance < amount:
        return False, "رصيدك غير كافٍ!"
    
    # البحث عن المستلم
    users = db.load_users()
    recipient_id = None
    for uid, udata in users.items():
        if udata.get("referral_code") == recipient_code:
            recipient_id = int(uid)
            break
    
    if not recipient_id:
        return False, "المستخدم غير موجود!"
    
    if recipient_id == sender_id:
        return False, "لا يمكنك تحويل لنفسك!"
    
    fee = amount * config.TRANSFER_FEE / 100
    total = amount + fee
    
    if sender.balance < total:
        return False, f"تحتاج {total} USDT (شامل الرسوم {fee:.2f} USDT)"
    
    recipient = get_user(recipient_id)
    
    # إنشاء معاملة
    txn = create_transaction(sender_id, TransactionType.TRANSFER, amount, f"تحويل لـ {recipient.first_name}", recipient_id=recipient_id, fee=fee)
    
    # التحويل
    update_user(sender_id, {
        "balance": sender.balance - total,
        "total_transferred": sender.total_transferred + amount
    })
    
    update_user(recipient_id, {
        "balance": recipient.balance + amount
    })
    
    complete_transaction(txn.id)
    
    return True, f"✅ تم التحويل!

💰 المبلغ: {amount} USDT
📝 الرسوم: {fee:.2f} USDT
👤 المستلم: {recipient.first_name}
💳 رصيدك الجديد: {sender.balance - total} USDT"

def get_today_withdrawals(user_id: int) -> float:
    today = datetime.now().strftime("%Y-%m-%d")
    transactions = db.load_transactions()
    total = 0
    for t in transactions:
        if t["user_id"] == user_id and t["type"] == TransactionType.WITHDRAWAL.value:
            if t["created_at"].startswith(today):
                total += t["amount"]
    return total

def get_user_transactions(user_id: int, limit: int = 10) -> List[Transaction]:
    transactions = db.load_transactions()
    user_txns = [Transaction(**t) for t in transactions if t["user_id"] == user_id]
    return sorted(user_txns, key=lambda x: x.created_at, reverse=True)[:limit]

# ==================== PAYMENT SYSTEM ====================
def create_invoice(user_id: int, amount: float, description: str, currency: str = "USD") -> Invoice:
    """إنشاء فاتورة"""
    invoice = Invoice(
        id=generate_id("INV"),
        user_id=user_id,
        amount=amount,
        currency=currency,
        description=description,
        status="pending",
        expires_at=(datetime.now() + timedelta(days=3)).isoformat()
    )
    
    invoices = db.load_invoices()
    invoices.append(asdict(invoice))
    db.save_invoices(invoices)
    
    return invoice

def create_subscription(user_id: int, tier: str, duration_days: int = 30) -> Subscription:
    """إنشاء اشتراك"""
    prices = {
        "basic": 4.99,
        "premium": 9.99,
        "vip": 19.99
    }
    
    price = prices.get(tier, 0)
    now = datetime.now()
    end_date = now + timedelta(days=duration_days)
    
    subscription = Subscription(
        id=generate_id("SUB"),
        user_id=user_id,
        tier=tier,
        price=price,
        start_date=now.isoformat(),
        end_date=end_date.isoformat()
    )
    
    subs = db.load_subscriptions()
    subs.append(asdict(subscription))
    db.save_subscriptions(subs)
    
    # تحديث المستخدم
    user = get_user(user_id)
    update_user(user_id, {
        "subscription_tier": tier,
        "subscription_expires": end_date.isoformat()
    })
    
    return subscription

def add_payment_method(user_id: int, method_type: str, provider: str, last_four: str = "") -> PaymentMethod:
    """إضافة طريقة دفع"""
    method = PaymentMethod(
        id=generate_id("PM"),
        user_id=user_id,
        type=method_type,
        provider=provider,
        last_four=last_four
    )
    
    methods = db.load_payment_methods()
    methods.append(asdict(method))
    db.save_payment_methods(methods)
    
    return method

# ==================== REFERRAL SYSTEM ====================
def process_referral(referrer_id: int, new_user_id: int):
    """معالجة الإحالة"""
    referrer = get_user(referrer_id)
    new_user = get_user(new_user_id)
    
    if referrer.referred_by == new_user_id:
        return  # لا إحالة متداخلة
    
    # منح المكافأة
    bonus = config.REFERRAL_BONUS
    update_user(referrer_id, {
        "points": referrer.points + bonus,
        "referrals_count": referrer.referrals_count + 1,
        "referral_earnings": referrer.referral_earnings + bonus
    })
    
    # منح نقاط للمُحال
    update_user(new_user_id, {"points": new_user.points + bonus // 2})
    
    create_transaction(referrer_id, TransactionType.REFERRAL_BONUS, bonus, f"إحالة من المستخدم {new_user_id}")

# ==================== DAILY BONUS ====================
def claim_daily_bonus(user_id: int) -> Tuple[bool, str]:
    """المكافأة اليومية"""
    user = get_user(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if hasattr(user, 'last_bonus_date') and user.last_bonus_date == today:
        return False, "المكافأة اليومية مُطالَبة بالفعل!"
    
    bonus = config.DAILY_BONUS
    update_user(user_id, {
        "points": user.points + bonus,
        "last_bonus_date": today
    })
    
    create_transaction(user_id, TransactionType.DAILY_BONUS, bonus, "مكافأة يومية")
    
    return True, f"✅ مكافأة يومية: +{bonus} نقطة!"

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int):
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    keyboard = [
        [InlineKeyboardButton(f"💰 الرصيد: {user.balance:.2f} USDT", callback_data="wallet")],
        [InlineKeyboardButton("🟢 إيداع", callback_data="deposit"), InlineKeyboardButton("🔴 سحب", callback_data="withdraw")],
        [InlineKeyboardButton("📤 تحويل", callback_data="transfer"), InlineKeyboardButton("📜 سِجل", callback_data="transactions")],
        [InlineKeyboardButton("⭐ نقاطي: {user.points}", callback_data="points")],
        [InlineKeyboardButton("🎁 مكافأة", callback_data="daily_bonus"), InlineKeyboardButton("🔗 إحالة", callback_data="referral")],
        [InlineKeyboardButton("💳 طرق الدفع", callback_data="payment_methods"), InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
        [InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def wallet_keyboard():
    keyboard = [
        [InlineKeyboardButton("🟢 إيداع", callback_data="deposit")],
        [InlineKeyboardButton("🔴 سحب", callback_data="withdraw")],
        [InlineKeyboardButton("📤 تحويل", callback_data="transfer")],
        [InlineKeyboardButton("📜 سجل المعاملات", callback_data="transactions")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def deposit_keyboard():
    keyboard = [
        [InlineKeyboardButton("💳 بطاقة بنكية", callback_data="deposit_card")],
        [InlineKeyboardButton("₿ USDT", callback_data="deposit_crypto")],
        [InlineKeyboardButton("📱 محفظة إلكترونية", callback_data="deposit_wallet")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def subscription_keyboard():
    keyboard = [
        [InlineKeyboardButton("⭐ Basic - 4.99$/شهر", callback_data="sub_basic")],
        [InlineKeyboardButton("💎 Premium - 9.99$/شهر", callback_data="sub_premium")],
        [InlineKeyboardButton("👑 VIP - 19.99$/شهر", callback_data="sub_vip")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== BOT COMMANDS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    
    # معالجة الإحالة
    args = context.args
    if args:
        ref_code = args[0]
        users = db.load_users()
        for uid, udata in users.items():
            if udata.get("referral_code") == ref_code and int(uid) != user_id:
                if not get_user(user_id).referred_by:
                    update_user(user_id, {"referred_by": int(uid)})
                    process_referral(int(uid), user_id)
                break
    
    user_data = get_user(user_id)
    level_name, _ = get_level_info(user_data.level)
    
    welcome = f"""💰 مرحباً {user.first_name}!

🏦 محفظتك:
• الرصيد: {user_data.balance:.2f} USDT
• الحالة: {user_data.wallet_status}

⭐ نقاطك: {user_data.points}
📊 مستواك: {level_name}

🔗 كود الإحالة: `{user_data.referral_code}`

💡 الأوامر:
• إيداع [المبلغ]
• سحب [المالع] [العنوان]
• تحويل [المبلغ] [كود]
• نقاط
• مكافأة
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))

async def wallet_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    text = f"""💰 محفظتك
━━━━━━━━━━━━━━━━
💵 الرصيد: {user.balance:.2f} USDT
⭐ النقاط: {user.points}
🏆 المستوى: {level_name}

📊 الإحصائيات:
• إجمالي الإيداعات: {user.total_deposited:.2f} USDT
• إجمالي السحبات: {user.total_withdrawn:.2f} USDT
• إجمالي التحويلات: {user.total_transferred:.2f} USDT

📧 العنوان: `{user.wallet_address}`
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=wallet_keyboard())

async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    text = """🟢 الإيداع
━━━━━━━━━━━━━━━━
اختر طريقة الإيداع:
"""
    await update.message.reply_text(text, reply_markup=deposit_keyboard())

async def withdraw_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = f"""🔴 السحب
━━━━━━━━━━━━━━━━
💰 رصيدك: {user.balance:.2f} USDT
📊 الحد الأدنى: {config.MIN_WITHDRAWAL} USDT
📈 الحد اليومي: {config.MAX_WITHDRAWAL_DAILY} USDT
📝 رسوم السحب: {config.WITHDRAWAL_FEE} USDT

━━━━━━━━━━━━━━━━

الصيغة:
`سحب [المبلغ] [عنوان_المحفظة]`

مثال:
`سحب 10 0x1234567890...`
"""
    await update.message.reply_text(text, reply_markup=back_keyboard())

async def transfer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = f"""📤 التحويل
━━━━━━━━━━━━━━━━
💰 رصيدك: {user.balance:.2f} USDT
📝 رسوم التحويل: {config.TRANSFER_FEE}%

━━━━━━━━━━━━━━━━

الصيغة:
`تحويل [المبلغ] [كود_المستلم]`

مثال:
`تحويل 5 REFABC123`
"""
    await update.message.reply_text(text, reply_markup=back_keyboard())

async def points_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    text = f"""⭐ نقاطي
━━━━━━━━━━━━━━━━
💰 الرصيد: {user.points} نقطة
📊 إجمالي النقاط: {user.points_lifetime}
🏆 مستواك: {level_name}

💡 كيف تكسب:
• الإيداع: 100 نقطة/USDT
• الإحالة: {config.REFERRAL_BONUS} نقطة
• المكافأة اليومية: {config.DAILY_BONUS} نقطة

━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = f"""🔗 نظام الإحالة
━━━━━━━━━━━━━━━━
كود الإحالة: `{user.referral_code}`

📊 إحصائياتك:
• المُحالين: {user.referrals_count}
• أرباحك: {user.referral_earnings} نقطة

💡 شارك كودك واربح {config.REFERRAL_BONUS} نقطة لكل إحالة!
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

# ==================== CALLBACK HANDLERS ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back":
        await wallet_command(update, context)
    elif data == "wallet":
        await wallet_command(update, context)
    elif data == "deposit":
        await deposit_command(update, context)
    elif data == "withdraw":
        await withdraw_command(update, context)
    elif data == "transfer":
        await transfer_command(update, context)
    elif data == "points":
        await points_command(update, context)
    elif data == "referral":
        await referral_command(update, context)
    elif data == "daily_bonus":
        success, msg = claim_daily_bonus(user_id)
        await query.edit_message_text(msg, reply_markup=main_menu_keyboard(user_id))
    elif data == "transactions":
        txns = get_user_transactions(user_id)
        text = "📜 سجل المعاملات\n━━━━━━━━━━━━━━━━\n"
        for t in txns[:10]:
            emoji = "✅" if t.status == "مكتمل" else "⏳"
            text += f"{emoji} {t.type}: {t.amount} USDT\n"
            text += f"   📅 {t.created_at[:10]}\n\n"
        await query.edit_message_text(text, reply_markup=wallet_keyboard())
    elif data == "stats":
        user = get_user(user_id)
        level_name, _ = get_level_info(user.level)
        await query.edit_message_text(
            f"📊 إحصائياتك\n━━━━━━━━━━━━━━━━\n"
            f"🏆 المستوى: {level_name}\n"
            f"💰 الرصيد: {user.balance:.2f} USDT\n"
            f"⭐ النقاط: {user.points}\n"
            f"📥 الإيداعات: {user.total_deposited:.2f}\n"
            f"📤 السحبات: {user.total_withdrawn:.2f}\n"
            f"🔗 الإحالات: {user.referrals_count}\n"
            f"💵 أرباح الإحالة: {user.referral_earnings}",
            reply_markup=main_menu_keyboard(user_id)
        )
    elif data.startswith("deposit_"):
        method = data.replace("deposit_", "")
        await query.edit_message_text(
            f"🟢 إيداع عبر {method}\n\n"
            f"أرسل المبلغ الذي تريد إيداعه:\n"
            f"مثال: `إيداع 100`",
            reply_markup=back_keyboard()
        )
    elif data.startswith("sub_"):
        tier = data.replace("sub_", "")
        prices = {"basic": "4.99", "premium": "9.99", "vip": "19.99"}
        await query.edit_message_text(
            f"💎 اشتراك {tier}\n\n"
            f"السعر: ${prices[tier]}/شهر\n\n"
            f"للاشتراك، أرسل: `اشتراك {tier}`",
            reply_markup=back_keyboard()
        )

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    
    # إيداع
    if text.startswith("إيداع "):
        try:
            amount = float(text.replace("إيداع ", ""))
            success, msg = deposit(user_id, amount)
            await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        except:
            await update.message.reply_text("❌ الصيغة: `إيداع 100`")
        return
    
    # سحب
    if text.startswith("سحب "):
        try:
            parts = text.replace("سحب ", "").split()
            amount = float(parts[0])
            address = parts[1] if len(parts) > 1 else ""
            
            if not address:
                await update.message.reply_text("❌ أدخل عنوان المحفظة!")
                return
            
            success, msg = withdraw(user_id, amount, address)
            await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        except:
            await update.message.reply_text("❌ الصيغة: `سحب 10 0x123...`")
        return
    
    # تحويل
    if text.startswith("تحويل "):
        try:
            parts = text.replace("تحويل ", "").split()
            amount = float(parts[0])
            code = parts[1] if len(parts) > 1 else ""
            
            success, msg = transfer(user_id, code, amount)
            await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        except:
            await update.message.reply_text("❌ الصيغة: `تحويل 10 REFABC123`")
        return
    
    # نقاط
    if text == "نقاط" or text == "⭐":
        await points_command(update, context)
        return
    
    # مكافأة
    if text == "مكافأة" or text == "🎁":
        success, msg = claim_daily_bonus(user_id)
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        return
    
    # اشتراك
    if text.startswith("اشتراك "):
        tier = text.replace("اشتراك ", "").strip()
        if tier in ["basic", "premium", "vip"]:
            sub = create_subscription(user_id, tier)
            await update.message.reply_text(
                f"✅ تم إنشاء الاشتراك!\n\n"
                f"💎 الخطة: {tier}\n"
                f"💰 السعر: ${sub.price}\n"
                f"📅 ينتهي: {sub.end_date[:10]}\n\n"
                f"للدفع، استخدم /pay",
                reply_markup=main_menu_keyboard(user_id)
            )
        else:
            await update.message.reply_text("❌ الخطط المتاحة: basic, premium, vip")
        return
    
    await update.message.reply_text("❌ أمر غير معروف!\n\n/start", reply_markup=main_menu_keyboard(user_id))

# ==================== MAIN ====================
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("wallet", wallet_command))
    app.add_handler(CommandHandler("إيداع", deposit_command))
    app.add_handler(CommandHandler("سحب", withdraw_command))
    app.add_handler(CommandHandler("تحويل", transfer_command))
    app.add_handler(CommandHandler("نقاط", points_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""الأوامر:
/start - بدء
/wallet - المحفظة
إيداع [المبلغ]
سحب [المبلغ] [العنوان]
تحويل [المبلغ] [كود]
نقاط
مكافأة
اشتراك [basic/premium/vip]
""")))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(handle_message))
    
    print("💰 Smart Wallet Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
