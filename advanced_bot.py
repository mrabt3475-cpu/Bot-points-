"""
🎮 CryptoPuzzle Pro - المنصة الاحترافية
🏆 نظام اقتصادي متقدم + ألعاب ذكية + دفع احترافي
"""

import os
import json
import random
import secrets
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
from collections import defaultdict
import logging
import asyncio

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
    ADMIN_IDS = [123456789]  # Admin user IDs
    DB_PATH = "./data"

    # Economy
    INITIAL_SUPPLY = 1_000_000
    MAX_SUPPLY = 10_000_000
    DAILY_MINT_LIMIT = 100_000

    # Game
    BASE_WIN_POINTS = 10
    STREAK_BONUS_PERCENT = 10
    LEVEL_XP_REQUIREMENT = 100

    # Payments
    MIN_DEPOSIT = 1  # USDT
    MIN_WITHDRAW = 1  # USDT
    COMMISSION_PERCENT = 2

    # Box
    BOX_TAX_PERCENT = 5

    # VIP
    VIP_THRESHOLDS = [0, 1000, 5000, 15000, 50000]
    VIP_PERKS = {
        0: {"name": "مجاني", "bonus": 0, "daily_limit": 100},
        1: {"name": "برونزي", "bonus": 5, "daily_limit": 500},
        2: {"name": "فضي", "bonus": 10, "daily_limit": 2000},
        3: {"name": "ذهبي", "bonus": 20, "daily_limit": 10000},
        4: {"name": "ماسي", "bonus": 50, "daily_limit": 50000},
    }

config = Config()

logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler('./data/bot.log'), logging.StreamHandler()]
)
logger = logging.getLogger("CryptoPuzzlePro")

# ==================== ADVANCED DATABASE ====================
class AdvancedDB:
    """قاعدة بيانات متقدمة مع PostgreSQL-like features"""

    def __init__(self):
        os.makedirs(config.DB_PATH, exist_ok=True)
        self.tables = {
            "users": f"{config.DB_PATH}/users.json",
            "transactions": f"{config.DB_PATH}/transactions.json",
            "games": f"{config.DB_PATH}/games.json",
            "economy": f"{config.DB_PATH}/economy.json",
            "analytics": f"{config.DB_PATH}/analytics.json",
            "vip": f"{config.DB_PATH}/vip.json",
            "tournaments": f"{config.DB_PATH}/tournaments.json",
            "achievements": f"{config.DB_PATH}/achievements.json",
        }
        self._init_tables()

    def _init_tables(self):
        defaults = {
            "users": {},
            "transactions": {"deposits": [], "withdraws": [], "transfers": []},
            "games": {"active": [], "history": []},
            "economy": {
                "supply": config.INITIAL_SUPPLY,
                "burned": 0,
                "tax_collected": 0,
                "daily_minted": 0,
                "last_reset": datetime.now().strftime("%Y-%m-%d"),
                "inflation_rate": 0,
                "velocity": 0,
            },
            "analytics": {
                "daily_active": [],
                "revenue": [],
                "game_stats": {},
            },
            "vip": {},
            "tournaments": {"active": [], "completed": []},
            "achievements": {},
        }
        for path, data in defaults.items():
            if not os.path.exists(self.tables[path]):
                self._save(self.tables[path], data)

    def _load(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {} if "users" in path else []

    def _save(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def query(self, table: str, filters: Dict = None) -> List[Dict]:
        data = self._load(self.tables[table])
        if isinstance(data, dict):
            data = list(data.values())
        else:
            data = data or []

        if not filters:
            return data

        return [item for item in data if all(
            item.get(k) == v for k, v in filters.items()
        )]

    def insert(self, table: str, data: Dict) -> str:
        path = self.tables[table]
        current = self._load(path)

        if isinstance(current, dict):
            id = str(data.get("id", secrets.token_hex(8)))
            data["id"] = id
            data["created_at"] = datetime.now().isoformat()
            current[id] = data
            self._save(path, current)
            return id
        else:
            id = len(current)
            data["id"] = id
            data["created_at"] = datetime.now().isoformat()
            current.append(data)
            self._save(path, current)
            return str(id)

    def update(self, table: str, id: str, data: Dict):
        path = self.tables[table]
        current = self._load(path)

        if isinstance(current, dict):
            if id in current:
                current[id].update(data)
                current[id]["updated_at"] = datetime.now().isoformat()
                self._save(path, current)
        else:
            for i, item in enumerate(current):
                if str(item.get("id")) == id:
                    current[i].update(data)
                    current[i]["updated_at"] = datetime.now().isoformat()
                    self._save(path, current)
                    break

    def get(self, table: str, id: str) -> Optional[Dict]:
        path = self.tables[table]
        current = self._load(path)

        if isinstance(current, dict):
            return current.get(id)
        else:
            for item in current:
                if str(item.get("id")) == id:
                    return item
        return None

    def __getattr__(self, table: str):
        return lambda: self._load(self.tables.get(table, f"./data/{table}.json"))

db = AdvancedDB()

# ==================== SMART ECONOMY ENGINE ====================
class EconomyEngine:
    """محرك الاقتصاد الذكي"""

    # Tokenomics
    INITIAL_SUPPLY = config.INITIAL_SUPPLY
    MAX_SUPPLY = config.MAX_SUPPLY
    ANNUAL_INFLATION_TARGET = 0.05  # 5% سنوياً

    # Burn mechanisms
    BURN_ON_TRANSFER = 0.02      # 2%
    BURN_ON_GAME = 0.03          # 3%
    BURN_ON_BOX = 0.05           # 5%
    BURN_ON_WITHDRAW = 0.01      # 1%

    # Tax
    TRANSACTION_TAX = 0.01       # 1%
    GAME_TAX = 0.02              # 2%
    WITHDRAW_TAX = 0.03          # 3%

    @classmethod
    def get_supply(cls) -> float:
        return db.economy[0].get("supply", 0) if isinstance(db.economy[0], dict) else 0

    @classmethod
    def calculate_inflation(cls) -> float:
        """حساب معدل التضخم"""
        supply = cls.get_supply()
        if supply < cls.INITIAL_SUPPLY:
            return 0
        return (supply - cls.INITIAL_SUPPLY) / cls.INITIAL_SUPPLY

    @classmethod
    def adjust_rewards(cls) -> float:
        """تعديل المكافآت بناءً على التضخم"""
        inflation = cls.calculate_inflation()
        multiplier = 1 - min(inflation, 0.5)  #最多 reduce by 50%
        return config.BASE_WIN_POINTS * multiplier

    @classmethod
    def mint(cls, amount: float) -> Tuple[bool, float, float]:
        """طباعة مع فحص الحدود"""
        eco = db.economy[0] if isinstance(db.economy[0], dict) else {}
        today = datetime.now().strftime("%Y-%m-%d")

        if eco.get("last_reset") != today:
            eco["daily_minted"] = 0
            eco["last_reset"] = today

        if eco.get("daily_minted", 0) + amount > config.DAILY_MINT_LIMIT:
            return False, 0, 0

        if cls.get_supply() + amount > cls.MAX_SUPPLY:
            return False, 0, 0

        burn = amount * cls.BURN_ON_GAME
        net = amount - burn

        eco["supply"] = eco.get("supply", 0) + net
        eco["burned"] = eco.get("burned", 0) + burn
        eco["daily_minted"] = eco.get("daily_minted", 0) + amount

        db._save(db.tables["economy"], [eco])
        return True, net, burn

    @classmethod
    def apply_transfer_tax(cls, amount: float) -> Tuple[float, float, float]:
        """تطبيق ضريبة التحويل"""
        tax = amount * cls.TRANSACTION_TAX
        burn = amount * cls.BURN_ON_TRANSFER
        net = amount - tax - burn

        eco = db.economy[0] if isinstance(db.economy[0], dict) else {}
        eco["tax_collected"] = eco.get("tax_collected", 0) + tax
        eco["burned"] = eco.get("burned", 0) + burn
        db._save(db.tables["economy"], [eco])

        return net, tax, burn

# ==================== SECURITY SYSTEM ====================
class SecurityManager:
    """نظام الأمان المتقدم"""

    @staticmethod
    def hash_data(data: str) -> str:
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def verify_signature(data: str, signature: str, secret: str) -> bool:
        expected = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)

    @staticmethod
    def generate_session_token(user_id: int) -> str:
        data = f"{user_id}:{time.time()}:{secrets.token_hex(16)}"
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def check_rate_limit(user_id: int, action: str, limit: int = 10) -> bool:
        """فحص معدل الاستخدام"""
        key = f"rate_{user_id}_{action}"
        # Simplified rate limiting
        return True

# ==================== ANTI-CHEAT ====================
class AntiCheat:
    """نظام مكافحة الغش"""

    def __init__(self):
        self.suspicious = defaultdict(list)
        self.banned = set()

    def check_answer_time(self, user_id: int, time_taken: float, expected: float = 30) -> bool:
        """فحص وقت الإجابة"""
        if time_taken < expected * 0.1:
            self._flag(user_id, "impossible_speed", f"{time_taken}s")
            return False
        return True

    def check_answer_pattern(self, user_id: int, answers: List[str]) -> bool:
        """فحص نمط الإجابات"""
        if len(answers) < 3:
            return True
        if len(set(answers)) == 1:
            self._flag(user_id, "same_answer", f"{answers}")
            return False
        return True

    def check_win_rate(self, user_id: int, games: int, wins: int) -> bool:
        """فحص نسبة الفوز"""
        if games < 20:
            return True
        rate = wins / games
        if rate > 0.95:
            self._flag(user_id, "impossible_win_rate", f"{rate:.2%}")
            return False
        return True

    def check_ip(self, user_id: int, ip: str) -> bool:
        """فحص عنوان IP"""
        # Simplified - in production check for VPN/proxy
        return True

    def _flag(self, user_id: int, reason: str, details: str = ""):
        """وضع علامة على مستخدم مشبوه"""
        self.suspicious[user_id].append({
            "reason": reason,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
        logger.warning(f"🚨 Flagged user {user_id}: {reason} - {details}")

    def is_banned(self, user_id: int) -> bool:
        return user_id in self.banned

anti_cheat = AntiCheat()

# ==================== VIP SYSTEM ====================
class VIPSystem:
    """نظام VIP المتقدم"""

    @classmethod
    def get_level(cls, total_spent: float) -> int:
        """تحديد مستوى VIP"""
        thresholds = config.VIP_THRESHOLDS
        for i in range(len(thresholds) - 1, -1, -1):
            if total_spent >= thresholds[i]:
                return i
        return 0

    @classmethod
    def get_perks(cls, level: int) -> Dict:
        return config.VIP_PERKS.get(level, config.VIP_PERKS[0])

    @classmethod
    def calculate_bonus(cls, base_amount: float, user_id: int) -> float:
        """حساب مكافأة VIP"""
        user = get_user(user_id)
        level = cls.get_level(user.get("total_spent", 0))
        perks = cls.get_perks(level)
        return base_amount * (perks["bonus"] / 100)

# ==================== ACHIEVEMENTS ====================
class Achievement:
    """نظام الإنجازات"""

    ACHIEVEMENTS = {
        "first_game": {"name": "البداية", "desc": "العب أول لعبة", "xp": 10},
        "first_win": {"name": "الفوز الأول", "desc": "اربح أول لعبة", "xp": 25},
        "streak_10": {"name": "عشرية", "desc": "حقق سلسلة من 10", "xp": 100},
        "streak_50": {"name": "خمسونية", "desc": "حقق سلسلة من 50", "xp": 500},
        "box_master": {"name": "سيد الصناديق", "desc": "افتح 100 صندوق", "xp": 250},
        "big_spender": {"name": "الإنفاق الكبير", "desc": "أنفق 10000 نقطة", "xp": 200},
        "rich": {"name": "الثروة", "desc": "اجمع 10000 نقطة", "xp": 200},
        "vip_gold": {"name": "الذهب", "desc": "ارتقِ للـ VIP ذهبي", "xp": 500},
    }

    @classmethod
    def check_and_award(cls, user_id: int, achievement_id: str) -> Optional[Dict]:
        """فحص ومنح إنجاز"""
        user = get_user(user_id)
        achievements = user.get("achievements", [])

        if achievement_id in achievements:
            return None

        achievement = cls.ACHIEVEMENTS.get(achievement_id)
        if not achievement:
            return None

        achievements.append(achievement_id)
        update_user(user_id, {
            "achievements": achievements,
            "xp": user.get("xp", 0) + achievement["xp"]
        })

        return achievement

# ==================== TOURNAMENT SYSTEM ====================
class Tournament:
    """نظام البطولات"""

    @classmethod
    def create(cls, name: str, entry_fee: float, prize_pool: float, duration: int) -> str:
        """إنشاء بطولة"""
        tournament = {
            "name": name,
            "entry_fee": entry_fee,
            "prize_pool": prize_pool,
            "duration": duration,
            "participants": [],
            "status": "active",
            "starts_at": datetime.now().isoformat(),
            "ends_at": (datetime.now() + timedelta(hours=duration)).isoformat(),
        }
        return db.insert("tournaments", tournament)

    @classmethod
    def join(cls, tournament_id: str, user_id: int) -> bool:
        """الانضمام لبطولة"""
        tournament = db.get("tournaments", tournament_id)
        if not tournament or tournament["status"] != "active":
            return False

        user = get_user(user_id)
        if user.get("points", 0) < tournament["entry_fee"]:
            return False

        # Deduct entry fee
        user["points"] -= tournament["entry_fee"]
        tournament["prize_pool"] = tournament.get("prize_pool", 0) + tournament["entry_fee"]
        tournament["participants"].append(user_id)

        update_user(user_id, user)
        db.update("tournaments", tournament_id, tournament)
        return True

# ==================== PAYMENT SYSTEM ====================
class PaymentSystem:
    """نظام الدفع الاحترافي"""

    # محاكاة محافظ crypto
    PAYMENT_ADDRESSES = {
        "TON": "UQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA",
        "USDT": "0x0000000000000000000000000000000000000000",
    }

    @classmethod
    def create_deposit(cls, user_id: int, amount: float, currency: str) -> Dict:
        """إنشاء إيداع"""
        deposit = {
            "user_id": user_id,
            "amount": amount,
            "currency": currency,
            "address": cls.PAYMENT_ADDRESSES.get(currency, ""),
            "status": "pending",
            "tx_hash": secrets.token_hex(32),
            "created_at": datetime.now().isoformat(),
        }
        db.insert("transactions", deposit)
        return deposit

    @classmethod
    def create_withdraw(cls, user_id: int, amount: float, currency: str, address: str) -> Tuple[bool, str]:
        """إنشاء سحب"""
        user = get_user(user_id)

        # Check balance
        balance_key = f"{currency.lower()}_balance"
        if user.get(balance_key, 0) < amount:
            return False, "رصيد غير كافٍ"

        # Check minimum
        if amount < config.MIN_WITHDRAW:
            return False, f"الحد الأدنى للسحب: {config.MIN_WITHDRAW}"

        # Apply withdraw tax
        tax = amount * EconomyEngine.WITHDRAW_TAX
        net_amount = amount - tax

        # Deduct
        user[balance_key] -= amount
        update_user(user_id, user)

        # Record transaction
        withdraw = {
            "user_id": user_id,
            "amount": net_amount,
            "currency": currency,
            "address": address,
            "status": "pending",
            "tx_hash": secrets.token_hex(32),
            "tax": tax,
            "created_at": datetime.now().isoformat(),
        }
        db.insert("transactions", withdraw)

        return True, f"✅ تم إنشاء طلب السحب!
المبلغ: {net_amount} {currency}
الضريبة: {tax} {currency}"

    @classmethod
    def process_deposit(cls, tx_hash: str, amount: float) -> bool:
        """معالجة الإيداع"""
        # Find pending deposit
        deposits = db.query("transactions", {"status": "pending", "tx_hash": tx_hash})
        if not deposits:
            return False

        deposit = deposits[0]
        user_id = deposit["user_id"]

        # Convert to points (mock rate: 1 USDT = 100 points)
        points = amount * 100

        # Add to user
        user = get_user(user_id)
        user["points"] = user.get("points", 0) + points
        user["total_deposited"] = user.get("total_deposited", 0) + amount
        update_user(user_id, user)

        # Update deposit status
        db.update("transactions", deposit["id"], {
            "status": "completed",
            "points_received": points
        })

        return True

# ==================== GAME ENGINE ====================
class GameEngine:
    """محرك الألعاب المتقدم"""

    GAMES = {
        "puzzle": {
            "name": "🧩 لغز",
            "difficulty": ["سهل", "متوسط", "صعب", "خبير"],
            "xp_multiplier": [1, 1.5, 2, 3],
        },
        "quiz": {
            "name": "❓ سؤال",
            "difficulty": ["سهل", "متوسط", "صعب"],
            "xp_multiplier": [1, 1.5, 2],
        },
        "math": {
            "name": "🔢 رياضيات",
            "difficulty": ["سهل", "متوسط", "صعب"],
            "xp_multiplier": [1, 1.5, 2],
        },
        "memory": {
            "name": "🧠 ذاكرة",
            "difficulty": ["4", "6", "8"],
            "xp_multiplier": [1, 1.5, 2],
        },
    }

    QUESTIONS = {
        "puzzle": {
            "سهل": [
                ("ما الذي يأتي مرة واحدة في الدقيقة ومرتين في القرن؟", "حرف الميم"),
                ("ما الذي يمشي بلا أرجل ويبكي بلا عيون؟", "الساعة"),
            ],
            "متوسط": [
                ("أوجد الرقم التالي: 1, 1, 2, 3, 5, 8, ...", "13"),
                ("ما هو العدد الذي لو ضربته في نفسه كان أكبر منه بـ 12؟", "4"),
            ],
            "صعب": [
                ("لغز السلم: كنت أعلى درجة، تحتي درجتان وفوقي درجتان، كم درجة؟", "3"),
            ],
            "خبير": [
                ("ما هو الشيء الذي يدور حول الغرفة دون أن يتحرك؟", "الجدار"),
            ],
        },
        "quiz": {
            "سهل": [
                ("ما عاصمة فرنسا؟", "باريس"),
                ("كم قارة في العالم؟", "7"),
            ],
            "متوسط": [
                ("من مكتشف penicillin؟", "فليمنغ"),
                ("ما أكبر محيط؟", "الهادئ"),
            ],
            "صعب": [
                ("في أي سنة بدأت الحرب العالمية الثانية؟", "1939"),
            ],
        },
        "math": {
            "سهل": [
                ("5 + 7 × 2", "19"),
                ("12 × 12 - 44", "100"),
            ],
            "متوسط": [
                ("2x + 5 = 15", "5"),
                ("x² = 64", "8"),
            ],
            "صعب": [
                ("حل: 2x + 3y = 12, x - y = 1", "x=3,y=2"),
            ],
        },
    }

    @classmethod
    def get_question(cls, game_type: str, difficulty: str = "سهل") -> Dict:
        """جلب سؤال"""
        questions = cls.QUESTIONS.get(game_type, {}).get(difficulty, [])
        if not questions:
            questions = cls.QUESTIONS.get("puzzle", {}).get("سهل", [])
        q, a = random.choice(questions)
        return {"question": q, "answer": a, "difficulty": difficulty}

    @classmethod
    def calculate_reward(cls, base: float, difficulty: str, streak: int, is_vip: bool) -> float:
        """حساب المكافأة"""
        game = cls.GAMES.get(game_type, {})
        diff_index = game.get("difficulty", ["سهل"]).index(difficulty) if difficulty in game.get("difficulty", []) else 0
        diff_mult = game.get("xp_multiplier", [1])[diff_index]

        streak_bonus = 1 + (streak * EconomyEngine.STREAK_BONUS_PERCENT / 100)
        vip_bonus = 1 + (VIPSystem.get_perks(VIPSystem.get_level(
            get_user(0).get("total_spent", 0)
        ))["bonus"] / 100) if is_vip else 1

        return base * diff_mult * streak_bonus * vip_bonus

# ==================== BOX SYSTEM ====================
class BoxSystem:
    """نظام الصناديق الاحترافي"""

    BOXES = {
        "basic": {"name": "📦 أساسي", "price": 50, "weight": 50},
        "silver": {"name": "🥈 فضي", "price": 150, "weight": 30},
        "gold": {"name": "🥇 ذهبي", "price": 500, "weight": 15},
        "diamond": {"name": "💎 ماسي", "price": 1500, "weight": 4},
        "mythic": {"name": "🔥 أسطوري", "price": 5000, "weight": 1},
    }

    REWARDS = {
        "basic": [
            ("points", 10, 50, 80),
            ("gems", 1, 5, 20),
        ],
        "silver": [
            ("points", 50, 150, 60),
            ("gems", 5, 15, 25),
            ("item", 15),
        ],
        "gold": [
            ("points", 200, 500, 45),
            ("gems", 20, 50, 20),
            ("item", 20),
            ("title", 15),
        ],
        "diamond": [
            ("points", 500, 1500, 35),
            ("gems", 50, 100, 20),
            ("item", 25),
            ("title", 10),
            ("boost", 10),
        ],
        "mythic": [
            ("points", 2000, 5000, 25),
            ("gems", 100, 300, 20),
            ("item", 20),
            ("title", 15),
            ("boost", 10),
            ("ton", 10),
        ],
    }

    ITEMS = [
        {"id": "sword_bronze", "name": "سيف برونزي", "rarity": "common", "value": 100},
        {"id": "sword_silver", "name": "سيف فضي", "rarity": "uncommon", "value": 300},
        {"id": "sword_gold", "name": "سيف ذهبي", "rarity": "rare", "value": 1000},
        {"id": "shield_diamond", "name": "درع ماسي", "rarity": "epic", "value": 3000},
    ]

    TITLES = [
        {"id": "lucky", "name": "محظوظ", "emoji": "🟢"},
        {"id": "champion", "name": "بطل", "emoji": "🏆"},
        {"id": "legend", "name": "أسطورة", "emoji": "🔥"},
    ]

    @classmethod
    def open(cls, box_id: str) -> Dict:
        """فتح صندوق"""
        rewards = cls.REWARDS.get(box_id, cls.REWARDS["basic"])
        roll = random.random() * 100
        cumulative = 0

        for reward in rewards:
            cumulative += reward[-1]  # chance is last element
            if roll <= cumulative:
                rtype = reward[0]
                if rtype == "points":
                    return {"type": "points", "amount": random.randint(reward[1], reward[2])}
                elif rtype == "gems":
                    return {"type": "gems", "amount": random.randint(reward[1], reward[2])}
                elif rtype == "item":
                    return {"type": "item", "item": random.choice(cls.ITEMS)}
                elif rtype == "title":
                    return {"type": "title", "title": random.choice(cls.TITLES)}
                elif rtype == "boost":
                    return {"type": "boost", "boost": {"name": "XP ×2", "duration": 3600}}
                elif rtype == "ton":
                    return {"type": "ton", "amount": round(random.uniform(0.1, 1.0), 2)}

        return {"type": "points", "amount": 10}

# ==================== USER SYSTEM ====================
def get_user(user_id: int) -> Dict:
    users = db._load(db.tables["users"])
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "points": 100,
            "gems": 0,
            "ton_balance": 0,
            "usdt_balance": 0,
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "streak": 0,
            "best_streak": 0,
            "level": 1,
            "xp": 0,
            "total_spent": 0,
            "total_earned": 0,
            "total_deposited": 0,
            "inventory": {},
            "items": [],
            "titles": [],
            "boosts": [],
            "achievements": [],
            "vip_level": 0,
            "created_at": datetime.now().isoformat(),
            "last_play": None,
        }
        db._save(db.tables["users"], users)

    return users[uid]

def update_user(user_id: int, data: Dict):
    users = db._load(db.tables["users"])
    uid = str(user_id)
    if uid in users:
        users[uid].update(data)
        db._save(db.tables["users"], users)

def add_points(user_id: int, amount: float) -> Tuple[bool, float]:
    """إضافة نقاط مع الاقتصاد الذكي"""
    success, net, burn = EconomyEngine.mint(amount)
    if not success:
        return False, 0

    net, tax, burn2 = EconomyEngine.apply_transfer_tax(net)
    user = get_user(user_id)
    user["points"] += net
    user["total_earned"] = user.get("total_earned", 0) + net
    update_user(user_id, user)
    return True, net

def spend_points(user_id: int, amount: float) -> Tuple[bool, str]:
    """إنفاق النقاط"""
    user = get_user(user_id)
    if user.get("points", 0) < amount:
        return False, "نقاط غير كافية!"

    # Apply box tax
    burn = amount * EconomyEngine.BURN_ON_BOX

    user["points"] -= amount
    user["total_spent"] = user.get("total_spent", 0) + amount
    update_user(user_id, user)
    return True, f"-{amount}"

# ==================== KEYBOARDS ====================
def main_keyboard(user_id: int):
    user = get_user(user_id)
    level = user.get("level", 1)
    vip = VIPSystem.get_perks(VIPSystem.get_level(user.get("total_spent", 0)))

    keyboard = [
        [InlineKeyboardButton(f"💰 {user['points']:.0f} | lvl {level}", callback_data="profile")],
        [InlineKeyboardButton(f"👑 {vip['name']} | +{vip['bonus']}%", callback_data="vip_info")],
        [InlineKeyboardButton("🎮 الألعاب", callback_data="games"), InlineKeyboardButton("🎁 الصناديق", callback_data="boxes")],
        [InlineKeyboardButton("💰 الإيداع", callback_data="deposit"), InlineKeyboardButton("💸 السحب", callback_data="withdraw")],
        [InlineKeyboardButton("🏆 البطولات", callback_data="tournaments"), InlineKeyboardButton("🎖️ الإنجازات", callback_data="achievements")],
        [InlineKeyboardButton("💳 المحفظة", callback_data="wallet"), InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
    ]
    return InlineKeyboardMarkup(keyboard)

def games_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧩 لغز", callback_data="game_puzzle"), InlineKeyboardButton("❓ سؤال", callback_data="game_quiz")],
        [InlineKeyboardButton("🔢 رياضيات", callback_data="game_math"), InlineKeyboardButton("🧠 ذاكرة", callback_data="game_memory")],
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

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    get_user(user.id)
    eco = db.economy[0] if isinstance(db.economy[0], dict) else {}

    await update.message.reply_text(
        f"🎮 <b>CryptoPuzzle Pro</b>
"
        f"━━━━━━━━━━━━━━━━
"
        f"💰 نقاطك: <b>{get_user(user.id)['points']:.0f}</b>
"
        f"💎 جوائرك: {get_user(user.id).get('gems', 0)}
"
        f"🪙 TON: {get_user(user.id).get('ton_balance', 0):.2f}
"
        f"💵 USDT: {get_user(user.id).get('usdt_balance', 0):.2f}

"
        f"📊 الاقتصاد: {eco.get('supply', 0):.0f}/{config.MAX_SUPPLY:,}
"
        f"🔥 محترق: {eco.get('burned', 0):.0f}

"
        f"<i>اختر:</i>",
        parse_mode=ParseMode.HTML,
        reply_markup=main_keyboard(user.id)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)

    if data == "profile":
        vip = VIPSystem.get_perks(VIPSystem.get_level(user.get("total_spent", 0)))
        await query.edit_message_text(
            f"👤 <b>ملفك</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 النقاط: {user['points']:.0f}
"
            f"📊 المستوى: {user.get('level', 1)}
"
            f"💎 XP: {user.get('xp', 0)}
"
            f"👑 VIP: {vip['name']} (+{vip['bonus']}%)
"
            f"🎮 الألعاب: {user.get('games_played', 0)}
"
            f"🏆 الانتصارات: {user.get('games_won', 0)}
"
            f"🔥 السلسلة: {user.get('streak', 0)}
"
            f"⭐ أفضل سلسلة: {user.get('best_streak', 0)}
"
            f"💵 إجمالي الصرف: {user.get('total_spent', 0):.0f}",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    elif data == "vip_info":
        level = VIPSystem.get_level(user.get("total_spent", 0))
        vip = VIPSystem.get_perks(level)

        text = f"👑 <b>نظام VIP</b>
━━━━━━━━━━━━━━━━
"
        text += f"مستواك: {vip['name']}
"
        text += f"مكافأة: +{vip['bonus']}%
"
        text += f"الحد اليومي: {vip['daily_limit']}

"
        text += f"<b>المستويات:</b>
"
        for i, perks in config.VIP_PERKS.items():
            marker = "👉 " if i == level else ""
            text += f"{marker}{perks['name']}: +{perks['bonus']}%
"

        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    elif data == "games":
        await query.edit_message_text(
            f"🎮 <b>الألعاب</b>
━━━━━━━━━━━━━━━━
اختر:",
            parse_mode=ParseMode.HTML,
            reply_markup=games_keyboard()
        )

    elif data.startswith("game_"):
        game_type = data.replace("game_", "")
        question = GameEngine.get_question(game_type)

        context.user_data['current_question'] = question
        context.user_data['game_type'] = game_type
        context.user_data['start_time'] = time.time()

        await query.edit_message_text(
            f"🎮 {GameEngine.GAMES.get(game_type, {}).get('name', game_type)}
"
            f"━━━━━━━━━━━━━━━━
"
            f"❓ <b>{question['question']}</b>

"
            f"⏰ أجب خلال 30 ثانية!",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    elif data == "boxes":
        await query.edit_message_text(
            f"🎁 <b>الصناديق</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 نقاطك: {user['points']:.0f}

"
            f"اختر:",
            parse_mode=ParseMode.HTML,
            reply_markup=boxes_keyboard()
        )

    elif data.startswith("buy_"):
        box_id = data.replace("buy_", "")
        box = BoxSystem.BOXES.get(box_id)

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
📦 في الحقيبة: {user['inventory'].get(box_id, 0)}",
                    reply_markup=boxes_keyboard()
                )
            else:
                await query.answer("⚠️ نقاط غير كافية!", show_alert=True)

    elif data == "open_box":
        inv = user.get("inventory", {})
        available = [k for k, v in inv.items() if v > 0]

        if not available:
            await query.answer("⚠️ لا تملك صناديق!", show_alert=True)
            return

        box_id = available[0]
        box = BoxSystem.BOXES[box_id]

        inv[box_id] -= 1
        update_user(user_id, {"inventory": inv})

        reward = BoxSystem.open(box_id)

        if reward["type"] == "points":
            user["points"] += reward["amount"]
        elif reward["type"] == "gems":
            user["gems"] = user.get("gems", 0) + reward["amount"]
        elif reward["type"] == "ton":
            user["ton_balance"] = user.get("ton_balance", 0) + reward["amount"]

        user["boxes_opened"] = user.get("boxes_opened", 0) + 1
        update_user(user_id, user)

        emojis = {"points": "💰", "gems": "💎", "item": "🎁", "title": "🏅", "boost": "⚡", "ton": "🪙"}
        emoji = emojis.get(reward["type"], "🎁")

        await query.edit_message_text(
            f"🎉 <b>تهانينا!</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"📦 {box['name']}

"
            f"🎁 {emoji} <b>{reward.get('amount', reward.get('item', {}).get('name', 'مكافأة'))}</b>",
            parse_mode=ParseMode.HTML,
            reply_markup=boxes_keyboard()
        )

    elif data == "deposit":
        await query.edit_message_text(
            f"💰 <b>الإيداع</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"<b>محافظ الإيداع:</b>

"
            f"<code>TON:</code>
{PaymentSystem.PAYMENT_ADDRESSES['TON']}

"
            f"<code>USDT:</code>
{PaymentSystem.PAYMENT_ADDRESSES['USDT']}

"
            f"💡 أرسل USDT/TON للعنوان أعلاه، ثم أرسل TX Hash للتحقق.",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    elif data == "withdraw":
        await query.edit_message_text(
            f"💸 <b>السحب</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💵 رصيد USDT: {user.get('usdt_balance', 0):.2f}
"
            f"🪙 رصيد TON: {user.get('ton_balance', 0):.2f}

"
            f"💡 الحد الأدنى: {config.MIN_WITHDRAW} USDT
"
            f"📊 الضريبة: {EconomyEngine.WITHDRAW_TAX*100}%",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    elif data == "wallet":
        await query.edit_message_text(
            f"💳 <b>محفظتك</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 نقاط: {user['points']:.0f}
"
            f"💎 جواهر: {user.get('gems', 0)}
"
            f"🪙 TON: {user.get('ton_balance', 0):.2f}
"
            f"💵 USDT: {user.get('usdt_balance', 0):.2f}

"
            f"📈 إجمالي الإيداع: {user.get('total_deposited', 0):.2f}
"
            f"📉 إجمالي الصرف: {user.get('total_spent', 0):.0f}",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    elif data == "achievements":
        achievements = user.get("achievements", [])
        text = f"🎖️ <b>إنجازاتك</b>
━━━━━━━━━━━━━━━━
"

        for ach_id, ach in Achievement.ACHIEVEMENTS.items():
            status = "✅" if ach_id in achievements else "⬜"
            text += f"{status} {ach['name']}: {ach['desc']} (+{ach['xp']} XP)
"

        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    elif data == "tournaments":
        await query.edit_message_text(
            f"🏆 <b>البطولات</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💡 لم تُطلق بعد!
"
            f"📺 تابعنا قريباً.",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    elif data == "back":
        await start(update, context)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    if 'current_question' in context.user_data:
        question = context.user_data['current_question']
        game_type = context.user_data.get('game_type', 'puzzle')

        # Anti-cheat check
        time_taken = time.time() - context.user_data.get('start_time', 0)
        if not anti_cheat.check_answer_time(user_id, time_taken):
            await update.message.reply_text("⚠️ إجابة مشبوهة! تم المراقبة.")
            return

        if text.lower() == question['answer'].lower():
            base_reward = EconomyEngine.adjust_rewards()
            reward = GameEngine.calculate_reward(base_reward, question['difficulty'], user.get('streak', 0), False)

            success, amount = add_points(user_id, reward)

            if success:
                streak = user.get('streak', 0) + 1
                update_user(user_id, {
                    "games_played": user.get('games_played', 0) + 1,
                    "games_won": user.get('games_won', 0) + 1,
                    "streak": streak,
                    "best_streak": max(user.get('best_streak', 0), streak),
                    "xp": user.get('xp', 0) + 10
                })

                # Check achievements
                Achievement.check_and_award(user_id, "first_win")
                if streak >= 10:
                    Achievement.check_and_award(user_id, "streak_10")

                await update.message.reply_text(
                    f"✅ إجابة صحيحة! +{amount:.1f} نقطة
🔥 سلسلة: {streak}",
                    reply_markup=main_keyboard(user_id)
                )
        else:
            update_user(user_id, {
                "games_played": user.get('games_played', 0) + 1,
                "games_lost": user.get('games_lost', 0) + 1,
                "streak": 0
            })
            await update.message.reply_text(
                f"❌ خطأ! الإجابة: {question['answer']}",
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
    logger.info("🎮 Starting CryptoPuzzle Pro...")

    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return

    app = Application.builder().token(Config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))

    logger.info("✅ CryptoPuzzle Pro is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
