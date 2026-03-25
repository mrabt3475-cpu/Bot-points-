"""
🤖 Crypto Wallet Bot - Ultimate Edition
محفظة ذكية مع ألعاب ذكية و AI وأمان متقدم
"""

import os
import json
import hashlib
import hmac
import random
import string
import asyncio
import re
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
from cryptography.fernet import Fernet
import requests

# ==================== CONFIG ====================
@dataclass
class Config:
    BOT_TOKEN: str = "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc"
    BINANCE_API_KEY: str = ""
    BINANCE_SECRET_KEY: str = ""
    # الأمان
    MAX_WITHDRAWAL_DAILY: float = 1000.0
    MIN_DEPOSIT: float = 1.0
    MAX_TRANSACTION_PER_DAY: int = 100
    RATE_LIMIT_PER_MINUTE: int = 10
    # النقاط
    POINTS_PER_USDT: int = 100
    REFERRAL_BONUS: int = 20
    REFERRAL_COMMISSION: float = 0.10
    WITHDRAWAL_FEE: float = 1.0
    # الألعاب
    MIN_BET: int = 10
    MAX_BET: int = 1000
    GAME_FEE: float = 0.05  # 5% رسوم
    # AI
    OPENAI_API_KEY: str = ""
    AI_ENABLED: bool = False

config = Config()

# ==================== ENCRYPTION ====================
try:
    ENCRYPTION_KEY = Fernet.generate_key()
    cipher = Fernet(ENCRYPTION_KEY)
except:
    ENCRYPTION_KEY = None
    cipher = None

def encrypt_data(data: str) -> str:
    if cipher:
        return cipher.encrypt(data.encode()).decode()
    return data

def decrypt_data(data: str) -> str:
    if cipher:
        return cipher.decrypt(data.encode()).decode()
    return data

# ==================== ENUMS ====================
class TransactionType(Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    REFERRAL_BONUS = "referral_bonus"
    PRIVATE_MESSAGE = "private_message"
    GIFT_SENT = "gift_sent"
    GIFT_RECEIVED = "gift_received"
    GAME_BET = "game_bet"
    GAME_WIN = "game_win"
    GAME_LOSS = "game_loss"

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
    VIP = 7

class GameType(Enum):
    PREDICTION = "prediction"
    LOTTERY = "lottery"
    ROULETTE = "roulette"
    COIN_FLIP = "coin_flip"
    NUMBER_GUESS = "number_guess"
    TRIVIA = "trivia"
    QUIZ = "quiz"

class GameStatus(Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"

# ==================== DATA CLASSES ====================
@dataclass
class Transaction:
    id: str
    user_id: int
    type: str
    amount: float
    fee: float
    status: str
    recipient_id: Optional[int] = None
    description: str = ""
    ip_address: str = ""
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
    is_premium: bool = False
    is_model: bool = False
    # الأمان
    pin_code: str = ""
    two_factor_enabled: bool = False
    two_factor_secret: str = ""
    failed_attempts: int = 0
    lock_until: str = ""
    ip_history: List[str] = field(default_factory=list)
    # الإعدادات
    daily_withdrawal: float = 0.0
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_active: str = field(default_factory=lambda: datetime.now().isoformat())
    # التواصل
    chat_status: str = "idle"
    current_chat_partner: int = None
    chats_today: int = 0
    gender: str = ""
    age: int = 0
    bio: str = ""
    accept_private_messages: bool = True
    private_message_price: int = 10
    accept_gifts: bool = True
    total_gifts_received: int = 0
    total_gifts_value: int = 0
    # الألعاب
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    total_winnings: int = 0
    total_losses: int = 0
    streak_wins: int = 0
    max_streak: int = 0
    # AI
    ai_chats: int = 0
    last_ai_chat: str = ""

@dataclass
class Game:
    id: str
    game_type: str
    user_id: int
    bet_amount: int
    status: str
    prediction: str = ""
    result: str = ""
    multiplier: float = 1.0
    winnings: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str = ""

@dataclass
class LotteryTicket:
    id: str
    user_id: int
    numbers: List[int]
    round_id: str
    price: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class LotteryRound:
    id: str
    numbers: List[int]
    prize_pool: int
    winner_ids: List[int]
    status: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    draw_at: str = ""

@dataclass
class TriviaQuestion:
    id: str
    question: str
    options: List[str]
    correct_answer: int
    category: str
    difficulty: str

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.users_file = "users.json"
        self.transactions_file = "transactions.json"
        self.games_file = "games.json"
        self.lottery_file = "lottery.json"
        self.waiting_file = "waiting.json"
        self.gifts_file = "gifts.json"
        self.private_messages_file = "private_messages.json"
        self.rate_limit_file = "rate_limits.json"
    
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
    
    def load_games(self) -> List:
        try:
            with open(self.games_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_games(self, games: List):
        with open(self.games_file, "w") as f:
            json.dump(games, f, ensure_ascii=False, indent=2)
    
    def load_lottery(self) -> Dict:
        try:
            with open(self.lottery_file, "r") as f:
                return json.load(f)
        except:
            return {"rounds": [], "tickets": []}
    
    def save_lottery(self, data: Dict):
        with open(self.lottery_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_waiting(self) -> List:
        try:
            with open(self.waiting_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_waiting(self, waiting: List):
        with open(self.waiting_file, "w") as f:
            json.dump(waiting, f, ensure_ascii=False, indent=2)
    
    def load_rate_limits(self) -> Dict:
        try:
            with open(self.rate_limit_file, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def save_rate_limits(self, data: Dict):
        with open(self.rate_limit_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

db = Database()

# ==================== HELPERS ====================
def generate_id(prefix: str, length: int = 12) -> str:
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_wallet_address() -> str:
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))

def get_user(user_id: int) -> User:
    users = db.load_users()
    if str(user_id) not in users:
        user = User(user_id=user_id, referral_code=generate_id("REF", 8), wallet_address=generate_wallet_address())
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
    if points >= 500000: return UserLevel.VIP
    elif points >= 100000: return UserLevel.DIAMOND
    elif points >= 50000: return UserLevel.PLATINUM
    elif points >= 20000: return UserLevel.GOLD
    elif points >= 10000: return UserLevel.SILVER
    elif points >= 5000: return UserLevel.BRONZE
    return UserLevel.NEW

def get_level_bonus(level: UserLevel) -> float:
    bonuses = {UserLevel.NEW: 0.0, UserLevel.BRONZE: 0.02, UserLevel.SILVER: 0.05, UserLevel.GOLD: 0.10, UserLevel.PLATINUM: 0.15, UserLevel.DIAMOND: 0.20, UserLevel.VIP: 0.30}
    return bonuses.get(level, 0.0)

def create_transaction(user_id: int, txn_type: TransactionType, amount: float, description: str = "", recipient_id: int = None) -> Transaction:
    txn = Transaction(id=generate_id("TXN"), user_id=user_id, type=txn_type.value, amount=amount, fee=0, status=TransactionStatus.PENDING.value, description=description, recipient_id=recipient_id)
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

# ==================== SECURITY ====================
def check_rate_limit(user_id: int) -> bool:
    """التحقق من معدل الطلبات"""
    rate_limits = db.load_rate_limits()
    now = time.time()
    user_key = str(user_id)
    
    if user_key not in rate_limits:
        rate_limits[user_key] = {"count": 1, "reset_at": now + 60}
        db.save_rate_limits(rate_limits)
        return True
    
    user_limit = rate_limits[user_key]
    if now > user_limit["reset_at"]:
        rate_limits[user_key] = {"count": 1, "reset_at": now + 60}
        db.save_rate_limits(rate_limits)
        return True
    
    if user_limit["count"] >= config.RATE_LIMIT_PER_MINUTE:
        return False
    
    user_limit["count"] += 1
    db.save_rate_limits(rate_limits)
    return True

def check_user_lock(user_id: int) -> bool:
    """التحقق إذا كان المستخدم مقفل"""
    user = get_user(user_id)
    if user.lock_until:
        lock_time = datetime.fromisoformat(user.lock_until)
        if datetime.now() < lock_time:
            return False
        else:
            update_user(user_id, {"lock_until": "", "failed_attempts": 0})
    return True

def record_failed_attempt(user_id: int):
    """تسجيل محاولة فاشلة"""
    user = get_user(user_id)
    attempts = user.failed_attempts + 1
    
    if attempts >= 5:
        lock_time = datetime.now() + timedelta(minutes=30)
        update_user(user_id, {"failed_attempts": attempts, "lock_until": lock_time.isoformat()})
    else:
        update_user(user_id, {"failed_attempts": attempts})

def verify_pin(user_id: int, pin: str) -> bool:
    """التحقق من PIN"""
    user = get_user(user_id)
    if not user.pin_code:
        return True
    return user.pin_code == hashlib.sha256(pin.encode()).hexdigest()[:8]

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()[:8]

# ==================== GAMES SYSTEM ====================
GAMES = {
    "prediction": {
        "name": "🎯 تخمين السعر",
        "description": "تخمن سعر USDT",
        "min_bet": 10,
        "max_bet": 500,
        "multiplier_range": (1.5, 3.0)
    },
    "coin_flip": {
        "name": "🪙 قلب العملة",
        "description": "اختر رأس أو كتابة",
        "min_bet": 10,
        "max_bet": 1000,
        "multiplier": 2.0
    },
    "number_guess": {
        "name": "🔢 تخمين الرقم",
        "description": "تخمن رقم من 1-100",
        "min_bet": 10,
        "max_bet": 500,
        "multiplier": 10.0
    },
    "roulette": {
        "name": "🎰 الروليت",
        "description": "دور الروليت",
        "min_bet": 20,
        "max_bet": 1000,
        "multiplier": 36.0
    },
    "lottery": {
        "name": "🎱 اليانصيب",
        "description": "فوز كبير",
        "min_bet": 50,
        "max_bet": 100,
        "multiplier": 100.0
    },
    "trivia": {
        "name": "❓ مسابقة",
        "description": "أجب على الأسئلة",
        "min_bet": 5,
        "max_bet": 100,
        "multiplier": 5.0
    }
}

TRIVIA_QUESTIONS = [
    {"q": "ما عاصمة فرنسا؟", "options": ["باريس", "لندن", "برلين", "مدريد"], "answer": 0, "category": "جغرافيا"},
    {"q": "من مكتشف أمريكا؟", "options": ["كولومبوس", "ماغلان", "فاسكو دا غاما", "أمريكو فيسبوتشي"], "answer": 0, "category": "تاريخ"},
    {"q": "ما أكبر كوكب في النظام الشمسي؟", "options": ["المريخ", "زحل", "المشتري", "الأرض"], "answer": 2, "category": "علم"},
    {"q": "من написа رواية哈利波特؟", "options": ["تولكين", "رولنغ", "مارتن", "ستيفن كينغ"], "answer": 1, "category": "أدب"},
    {"q": "ما لون الدم في الأوردة؟", "options": ["أحمر", "أزرق", "أخضر", "أصفر"], "answer": 1, "category": "علم"},
    {"q": "كم قارة في العالم؟", "options": ["5", "6", "7", "8"], "answer": 2, "category": "جغرافيا"},
    {"q": "من هو أب物理学 الحديثة؟", "options": ["نيوتن", "أينشتاين", "غاليليو", "كوبلر"], "answer": 1, "category": "علم"},
    {"q": "ما أطول نهر في العالم؟", "options": ["الأمازون", "النيل", "السند", "اليانغتسي"], "answer": 1, "category": "جغرافيا"},
]

def play_game(user_id: int, game_type: str, bet: int, prediction: str = "") -> Tuple[bool, str, int]:
    """اللعب لعبة"""
    user = get_user(user_id)
    
    if game_type not in GAMES:
        return False, "اللعبة غير موجودة", 0
    
    game_info = GAMES[game_type]
    
    if bet < game_info["min_bet"]:
        return False, f"الحد الأدنى: {game_info['min_bet']} نقطة", 0
    
    if bet > game_info["max_bet"]:
        return False, f"الحد الأقصى: {game_info['max_bet']} نقطة", 0
    
    if user.points < bet:
        return False, "نقاطك غير كافية", 0
    
    # خصم الرهان
    update_user(user_id, {"points": user.points - bet})
    
    result = ""
    won = False
    multiplier = 1.0
    winnings = 0
    
    if game_type == "coin_flip":
        result = random.choice(["head", "tail"])
        won = (prediction.lower() == result)
        multiplier = game_info["multiplier"]
    
    elif game_type == "number_guess":
        try:
            target = random.randint(1, 100)
            user_guess = int(prediction)
            result = str(target)
            
            if user_guess == target:
                won = True
                multiplier = game_info["multiplier"]
            elif abs(user_guess - target) <= 5:
                won = True
                multiplier = 2.0
            elif abs(user_guess - target) <= 10:
                won = True
                multiplier = 1.5
        except:
            pass
    
    elif game_type == "prediction":
        # تخمين سعر USDT (محاكاة)
        current_price = 1.0 + random.uniform(-0.05, 0.05)
        try:
            user_prediction = float(prediction)
            diff = abs(current_price - user_prediction)
            
            if diff < 0.001:
                won = True
                multiplier = 3.0
            elif diff < 0.01:
                won = True
                multiplier = 2.0
            elif diff < 0.02:
                won = True
                multiplier = 1.5
            
            result = f"{current_price:.4f}"
        except:
            pass
    
    elif game_type == "roulette":
        result_num = random.randint(0, 36)
        result = str(result_num)
        
        try:
            user_num = int(prediction)
            if user_num == result_num:
                won = True
                multiplier = 36.0
            elif user_num % 2 == result_num % 2:
                won = True
                multiplier = 2.0
        except:
            pass
    
    elif game_type == "trivia":
        question = random.choice(TRIVIA_QUESTIONS)
        try:
            user_answer = int(prediction)
            if user_answer == question["answer"]:
                won = True
                multiplier = game_info["multiplier"]
            result = question["category"]
        except:
            pass
    
    elif game_type == "lottery":
        # شراء تذكرة يانصيب
        ticket_numbers = sorted(random.sample(range(1, 50), 5))
        result = str(ticket_numbers)
        won = random.random() < 0.01  # 1% فرصة
        multiplier = game_info["multiplier"] if won else 0
    
    # حساب الأرباح
    if won:
        winnings = int(bet * multiplier)
        fee = int(winnings * config.GAME_FEE)
        winnings -= fee
        
        update_user(user_id, {
            "points": user.points - bet + winnings,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1,
            "total_winnings": user.total_winnings + winnings,
            "streak_wins": user.streak_wins + 1,
            "max_streak": max(user.max_streak, user.streak_wins + 1)
        })
        
        create_transaction(user_id, TransactionType.GAME_WIN, winnings, f"فوز في {game_type}")
        return True, f"🎉 مبروك! فزت بـ {winnings} نقطة!", winnings
    else:
        update_user(user_id, {
            "games_played": user.games_played + 1,
            "games_lost": user.games_lost + 1,
            "total_losses": user.total_losses + bet,
            "streak_wins": 0
        })
        
        create_transaction(user_id, TransactionType.GAME_LOSS, bet, f"خسارة في {game_type}")
        return False, f"😢 خسرت! النتيجة: {result}", 0

def get_user_games(user_id: int, limit: int = 10) -> List:
    games = db.load_games()
    user_games = [g for g in games if g["user_id"] == user_id]
    return sorted(user_games, key=lambda x: x["created_at"], reverse=True)[:limit]

# ==================== AI SYSTEM ====================
class AISystem:
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        self.enabled = config.AI_ENABLED and bool(self.api_key)
    
    async def chat(self, user_id: int, message: str) -> str:
        """الدردشة مع AI"""
        user = get_user(user_id)
        
        if not self.enabled:
            # ردود ذكية محلية
            responses = {
                "مرحبا": "مرحباً! كيف يمكنني مساعدتك؟",
                "كيف حالك": "بخير، شكراً! وأنت؟",
                "ما هو": "أنا بوت ذكي متقدم!",
                "help": "يمكنني مساعدتك في:\n• المحفظة\n• الألعاب\n• الهدايا\n• التواصل\n\nاكتب سؤالك"
            }
            
            for key, response in responses.items():
                if key in message.lower():
                    return response
            
            return f"🤖 فهمت رسالتك: {message}\n\nللحصول على مساعدة، اكتب: help"
        
        # استخدام OpenAI
        try:
            headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
            data = {
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": message}],
                "max_tokens": 200
            }
            response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
        except:
            pass
        
        return "عذراً، حدث خطأ. حاول لاحقاً"
    
    def get_recommendation(self, user_id: int) -> str:
        """توصيات ذكية للمستخدم"""
        user = get_user(user_id)
        
        if user.points < 50:
            return "💡 نصيحة: العب ألعاب بسيطة لكسب نقاط!"
        
        if user.games_won > user.games_lost:
            return "🔥 أنت محظوظ! جرب لعبة الروليت"
        
        if user.streak_wins >= 3:
            return f"🎉 سلسلة انتصارات {user.streak_wins}! استمر!"
        
        return "💡 جرب لعبة تخمين الرقم - نسبة الفوز أعلى!"

ai = AISystem()

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int):
    user = get_user(user_id)
    level = UserLevel(user.level)
    keyboard = [
        [InlineKeyboardButton(f"💰 {user.balance:.2f} USDT | ⭐ {user.points}", callback_data="balance")],
        [InlineKeyboardButton("🟢 إيداع", callback_data="deposit"), InlineKeyboardButton("🔴 سحب", callback_data="withdraw")],
        [InlineKeyboardButton("📤 تحويل", callback_data="transfer"), InlineKeyboardButton("🔗 إحالة", callback_data="referral")],
        [InlineKeyboardButton("🎮 الألعاب", callback_data="games_menu")],
        [InlineKeyboardButton("💬 تواصل عشوائي", callback_data="random_chat")],
        [InlineKeyboardButton("💌 رسائل", callback_data="private_messages"), InlineKeyboardButton("🎁 هدايا", callback_data="gifts_menu")],
        [InlineKeyboardButton("🤖 AI", callback_data="ai_chat"), InlineKeyboardButton("⚙️ إعدادات", callback_data="settings")],
    ]
    if user.is_admin:
        keyboard.append([InlineKeyboardButton("👑 الأدمن", callback_data="admin")])
    return InlineKeyboardMarkup(keyboard)

def games_keyboard():
    keyboard = []
    for game_key, game_info in GAMES.items():
        keyboard.append([InlineKeyboardButton(f"{game_info['name']} ({game_info['min_bet']}-{game_info['max_bet']}ن)", callback_data=f"game_{game_key}")])
    keyboard.append([InlineKeyboardButton("📊 إحصائيات الألعاب", callback_data="game_stats")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== BOT COMMANDS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    
    # فحص الأمان
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳太多 الطلبات! انتظر قليلاً")
        return
    
    if not check_user_lock(user_id):
        await update.message.reply_text("🔒 حسابك مقفل مؤقتاً!")
        return
    
    user_data = get_user(user_id)
    
    # معالجة الإحالة
    args = context.args
    if args:
        ref_code = args[0]
        users = db.load_users()
        for uid, udata in users.items():
            if udata.get("referral_code") == ref_code and int(uid) != user_id:
                if not user_data.referred_by:
                    update_user(user_id, {"referred_by": int(uid)})
                    referrer = get_user(int(uid))
                    update_user(int(uid), {"referrals_count": referrer.referrals_count + 1, "points": referrer.points + config.REFERRAL_BONUS})
                break
    
    level = UserLevel(user_data.level)
    welcome = f"""🎉 مرحباً {user.first_name}!

💰 محفظتك:
• USDT: {user_data.balance:.2f}
• النقاط: ⭐ {user_data.points}
• المستوى: {level.name}

🎮 الألعاب الذكية متاحة!
🤖 AI متاح للدردشة

🔐 حسابك مؤمن
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level = UserLevel(user.level)
    
    win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0
    
    text = f"""💰 محفظتك
━━━━━━━━━━━━━━━━
🟢 USDT: {user.balance:.2f}
⭐ النقاط: {user.points}
🏆 المستوى: {level.name}

🎮 إحصائيات الألعاب:
• لعب: {user.games_played}
• فاز: {user.games_won}
• خسر: {user.games_lost}
• نسبة الفوز: {win_rate:.1f}%
• أفضل سلسلة: {user.max_streak}
• إجمالي الأرباح: {user.total_winnings}

💡 {ai.get_recommendation(user_id)}
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def games_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = f"""🎮 الألعاب الذكية
━━━━━━━━━━━━━━━━
نقاطك: ⭐ {user.points}

اختر لعبة للعب:
"""
    await update.message.reply_text(text, reply_markup=games_keyboard())

async def ai_chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    text = """🤖 الدردشة مع AI
━━━━━━━━━━━━━━━━
اكتب رسالتك وسأرد عليك!

مثال:
• مرحباً
• ما هو البيتكوين؟
• نصيحة للعب

للخروج: /cancel
"""
    await update.message.reply_text(text, reply_markup=back_keyboard())

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
    elif data == "games_menu":
        await games_command(update, context)
    elif data == "game_stats":
        user = get_user(user_id)
        win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0
        await query.edit_message_text(
            f"📊 إحصائياتك:\n━━━━━━━━━━━━━━━━\n"
            f"• لعبت: {user.games_played}\n"
            f"• فزت: {user.games_won}\n"
            f"• خسرت: {user.games_lost}\n"
            f"• نسبة الفوز: {win_rate:.1f}%\n"
            f"• أفضل سلسلة: {user.max_streak}\n"
            f"• إجمالي الأرباح: {user.total_winnings}\n"
            f"• إجمالي الخسائر: {user.total_losses}",
            reply_markup=games_keyboard()
        )
    elif data.startswith("game_"):
        game_type = data.replace("game_", "")
        if game_type in GAMES:
            game_info = GAMES[game_type]
            await query.edit_message_text(
                f"🎮 {game_info['name']}\n"
                f"{game_info['description']}\n\n"
                f"الحد: {game_info['min_bet']}-{game_info['max_bet']} نقطة\n\n"
                f"أرسل:\n`لعب {game_type} [الرهان] [تخمينك]`\n\n"
                f"مثال: `لعب coin_flip 50 head`",
                reply_markup=back_keyboard()
            )
    elif data == "ai_chat":
        await ai_chat_command(update, context)
    elif data == "settings":
        user = get_user(user_id)
        await query.edit_message_text(
            f"⚙️ الإعدادات\n━━━━━━━━━━━━━━━━\n"
            f"• PIN: {'مفعل' if user.pin_code else 'غير مفعل'}\n"
            f"• 2FA: {'مفعل' if user.two_factor_enabled else 'غير مفعل'}\n\n"
            f"الأوامر:\n"
            f"• pin [رقم] - تفعيل PIN\n"
            f"• فتح / غلق رسائل\n"
            f"• فتح / غلق هدايا",
            reply_markup=back_keyboard()
        )

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    
    # فحص الأمان
    if not check_rate_limit(user_id):
        await update.message.reply_text("⏳太多 الطلبات!")
        return
    
    user = get_user(user_id)
    
    # AI Chat
    if user.ai_chats > 0 or text.startswith("ai ") or text.startswith("🤖"):
        user.ai_chats += 1
        update_user(user_id, {"ai_chats": user.ai_chats, "last_ai_chat": text})
        response = await ai.chat(user_id, text.replace("ai ", "").replace("🤖", ""))
        await update.message.reply_text(response)
        return
    
    # اللعب
    if text.startswith("لعب "):
        try:
            parts = text.replace("لعب ", "").split()
            if len(parts) >= 2:
                game_type = parts[0]
                bet = int(parts[1])
                prediction = parts[2] if len(parts) > 2 else ""
                
                won, msg, winnings = play_game(user_id, game_type, bet, prediction)
                await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
                return
        except:
            await update.message.reply_text("❌ الصيغة: `لعب coin_flip 50 head`")
            return
    
    # PIN
    if text.startswith("pin "):
        pin = text.replace("pin ", "")
        if len(pin) == 4 and pin.isdigit():
            update_user(user_id, {"pin_code": hash_pin(pin)})
            await update.message.reply_text("✅ تم تفعيل PIN")
        else:
            await update.message.reply_text("❌ PIN يجب быть 4 أرقام")
        return
    
    # التحويل
    if text.startswith("تحويل "):
        try:
            parts = text.replace("تحويل ", "").split()
            amount = float(parts[0])
            code = parts[1]
            
            if user.points < amount:
                await update.message.reply_text("❌ نقاط غير كافية")
                return
            
            users = db.load_users()
            receiver_id = None
            for uid, udata in users.items():
                if udata.get("referral_code") == code:
                    receiver_id = int(uid)
                    break
            
            if receiver_id:
                update_user(user_id, {"points": user.points - amount})
                receiver = get_user(receiver_id)
                update_user(receiver_id, {"points": receiver.points + amount})
                await update.message.reply_text(f"✅ تم تحويل {amount} نقطة")
        except:
            await update.message.reply_text("❌ خطأ")
        return
    
    await update.message.reply_text("❌ أمر غير معروف\n\n/start", reply_markup=main_menu_keyboard(user_id))

# ==================== MAIN ====================
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("games", games_command))
    app.add_handler(CommandHandler("ai", ai_chat_command))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""الأوامر:
/start - بدء
/balance - الرصيد
/games - الألعاب
/ai - الدردشة مع AI

الألعاب:
لعب coin_flip 50 head
لعب number_guess 50 25
لعب trivia 10 0
""")))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(handle_message))
    
    print("🤖 Crypto Wallet Bot - Ultimate Edition")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
