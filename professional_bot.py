"""
🎮 CryptoPuzzle - Professional Gaming Platform
🏆 Global Challenge Platform with Smart Economy
"""

import os
import json
import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# ==================== SECURITY & CRYPTO ====================
class SecurityManager:
    """نظام الأمان المتقدم"""

    @staticmethod
    def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
        """تشفير كلمة المرور بـ SHA-256"""
        if not salt:
            salt = secrets.token_hex(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return key.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """التحقق من كلمة المرور"""
        key, _ = SecurityManager.hash_password(password, salt)
        return hmac.compare_digest(key, hashed)

    @staticmethod
    def generate_token(user_id: int) -> str:
        """توليد token آمن"""
        data = f"{user_id}:{time.time()}:{secrets.token_hex(8)}"
        return hashlib.sha256(data.encode()).hexdigest()

    @staticmethod
    def verify_token(token: str, user_id: int, db) -> bool:
        """التحقق من token"""
        tokens = db.get("tokens", {})
        if token not in tokens:
            return False
        stored = tokens[token]
        if stored.get("user_id") != user_id:
            return False
        if time.time() - stored.get("created", 0) > 86400:  # 24h
            return False
        return True

# ==================== DATABASE - PostgreSQL Style ====================
class Database:
    """قاعدة بيانات محسنة مع PostgreSQL-style"""

    def __init__(self):
        os.makedirs("./data", exist_ok=True)
        self.users_file = "./data/users.json"
        self.games_file = "./data/games.json"
        self.transactions_file = "./data/transactions.json"
        self.leaderboard_file = "./data/leaderboard.json"
        self._init_db()

    def _init_db(self):
        """تهيئة قاعدة البيانات"""
        tables = {
            self.users_file: {},
            self.games_file: {"active": [], "completed": []},
            self.transactions_file: {"deposits": [], "withdraws": [], "games": [], "referrals": []},
            self.leaderboard_file: {"global": [], "weekly": [], "monthly": []}
        }
        for path, data in tables.items():
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

    def query(self, table: str, filters: Dict = None) -> List[Dict]:
        """استعلام شبيه بـ SQL"""
        data = self._load(getattr(self, f"{table}_file"))
        if not filters:
            return data if isinstance(data, list) else list(data.values())

        results = []
        items = data if isinstance(data, list) else list(data.values())
        for item in items:
            match = True
            for key, value in filters.items():
                if item.get(key) != value:
                    match = False
                    break
            if match:
                results.append(item)
        return results

    def insert(self, table: str, data: Dict) -> str:
        """إدراج بيانات"""
        path = getattr(self, f"{table}_file")
        current = self._load(path)

        if isinstance(current, dict):
            id = str(data.get("id", secrets.token_hex(8)))
            current[id] = data
            self._save(path, current)
            return id
        else:
            id = len(current)
            data["id"] = id
            current.append(data)
            self._save(path, current)
            return str(id)

    def update(self, table: str, id: str, data: Dict):
        """تحديث بيانات"""
        path = getattr(self, f"{table}_file")
        current = self._load(path)

        if isinstance(current, dict):
            if id in current:
                current[id].update(data)
                self._save(path, current)
        else:
            for i, item in enumerate(current):
                if str(item.get("id")) == id:
                    current[i].update(data)
                    self._save(path, current)
                    break

    def delete(self, table: str, id: str):
        """حذف بيانات"""
        path = getattr(self, f"{table}_file")
        current = self._load(path)

        if isinstance(current, dict):
            current.pop(id, None)
            self._save(path, current)
        else:
            current = [item for item in current if str(item.get("id")) != id]
            self._save(path, current)

db = Database()

# ==================== GAME MODES ====================
class GameMode(Enum):
    PUZZLE = "puzzle"           # ألغاز ذكية
    QUIZ = "quiz"               # أسئلة
    MATH = "math"                # رياضيات
    MEMORY = "memory"            # ذاكرة
    REFLEX = "reflex"            # ردود الفعل
    STRATEGY = "strategy"        # استراتيجية
    CTF = "ctf"                 # Capture The Flag
    ESCAPE = "escape"            # هروب

class Difficulty(Enum):
    EASY = 1
    MEDIUM = 2
    HARD = 3
    EXPERT = 4
    MASTER = 5

# ==================== SMART ECONOMY ====================
class SmartEconomy:
    """اقتصاد ذكي مضاد للتضخم"""

    # معاملات الاقتصاد
    INITIAL_SUPPLY = 1000000     # 1M نقطة أولية
    MAX_SUPPLY = 10000000        # 10M حد أقصى
    DAILY_MINT_LIMIT = 50000     # 50K يومياً

    # آليات الحرق
    BURN_ON_TRANSFER = 0.02      # 2% عند التحويل
    BURN_ON_GAME = 0.05          # 5% عند اللعب
    BURN_ON_WITHDRAW = 0.03      # 3% عند السحب

    # المكافآت
    WIN_REWARD_BASE = 10         # مكافأة الفوز الأساسية
    STREAK_BONUS = 0.1           # 10% لكل سلسلة
    REFERRAL_BONUS = 50          # 50 نقطة للإحالة

    # الضرائب
    TRANSACTION_TAX = 0.01        # 1%
    GAME_TAX = 0.02               # 2%
    WITHDRAW_TAX = 0.05           # 5%

    @classmethod
    def calculate_reward(cls, base_reward: float, streak: int, difficulty: Difficulty) -> float:
        """حساب المكافأة بناءً على الصعوبة والسلسلة"""
        streak_bonus = 1 + (streak * cls.STREAK_BONUS)
        difficulty_multiplier = difficulty.value * 0.5 + 0.5
        return base_reward * streak_bonus * difficulty_multiplier

    @classmethod
    def apply_burn(cls, amount: float, burn_rate: float) -> Tuple[float, float]:
        """تطبيق الحرق"""
        burn = amount * burn_rate
        net = amount - burn
        return net, burn

    @classmethod
    def calculate_tax(cls, amount: float, tax_rate: float) -> Tuple[float, float]:
        """حساب الضريبة"""
        tax = amount * tax_rate
        net = amount - tax
        return net, tax

# ==================== ANTI-CHEAT SYSTEM ====================
class AntiCheat:
    """نظام مكافحة الغش"""

    def __init__(self):
        self.suspicious_users = {}
        self.cheat_patterns = []

    def check_answer_speed(self, user_id: int, time_taken: float, expected_time: float) -> bool:
        """فحص سرعة الإجابة"""
        if time_taken < expected_time * 0.1:  # أسرع بـ 10 مرات
            self._flag_user(user_id, "impossible_speed")
            return False
        return True

    def check_answer_pattern(self, user_id: int, answers: List[str]) -> bool:
        """فحص نمط الإجابات"""
        if len(answers) < 3:
            return True

        # فحص التكرار
        if len(set(answers)) == 1:
            self._flag_user(user_id, "same_answer")
            return False
        return True

    def check_win_rate(self, user_id: int, games: int, wins: int) -> bool:
        """فحص نسبة الفوز"""
        if games < 10:
            return True

        win_rate = wins / games
        if win_rate > 0.95:  # أكثر من 95%
            self._flag_user(user_id, "impossible_win_rate")
            return False
        return True

    def _flag_user(self, user_id: int, reason: str):
        """وضع علامة على مستخدم مشبوه"""
        if user_id not in self.suspicious_users:
            self.suspicious_users[user_id] = []
        self.suspicious_users[user_id].append({
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        })

anti_cheat = AntiCheat()

# ==================== USER SYSTEM ====================
class User:
    """نظام المستخدم المتقدم"""

    def __init__(self, user_id: int, username: str = "", first_name: str = ""):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.created_at = datetime.now()

    def register(self, password: str = None) -> Dict:
        """تسجيل مستخدم جديد"""
        hashed_password = None
        salt = None

        if password:
            hashed_password, salt = SecurityManager.hash_password(password)

        user_data = {
            "user_id": self.user_id,
            "username": self.username,
            "first_name": self.first_name,
            "password_hash": hashed_password,
            "salt": salt,
            "points": 100,  # نقاط ترحيبية
            "level": 1,
            "xp": 0,
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "current_streak": 0,
            "best_streak": 0,
            "total_earned": 0,
            "total_spent": 0,
            "referral_code": secrets.token_hex(4),
            "referred_by": None,
            "is_verified": False,
            "is_premium": False,
            "ban_status": "active",
            "created_at": self.created_at.isoformat(),
            "last_play": None,
            "stats": {
                "puzzle": {"played": 0, "won": 0},
                "quiz": {"played": 0, "won": 0},
                "math": {"played": 0, "won": 0},
                "memory": {"played": 0, "won": 0},
                "reflex": {"played": 0, "won": 0},
            }
        }

        db.insert("users", user_data)
        return user_data

    def login(self, password: str) -> Tuple[bool, str]:
        """تسجيل الدخول"""
        users = db.query("users", {"user_id": self.user_id})
        if not users:
            return False, "المستخدم غير موجود"

        user = users[0]
        if user.get("ban_status") != "active":
            return False, "الحساب محظور"

        if not user.get("password_hash"):
            return True, "logged_in"

        if not SecurityManager.verify_password(
            password, 
            user["password_hash"], 
            user["salt"]
        ):
            return False, "كلمة المرور خاطئة"

        return True, "logged_in"

    def get_profile(self) -> Dict:
        """جلب الملف الشخصي"""
        users = db.query("users", {"user_id": self.user_id})
        return users[0] if users else None

    def update_stats(self, game_type: str, won: bool):
        """تحديث الإحصائيات"""
        user = self.get_profile()
        if not user:
            return

        updates = {
            "games_played": user["games_played"] + 1,
            f"stats.{game_type}.played": user["stats"][game_type]["played"] + 1
        }

        if won:
            updates["games_won"] = user["games_won"] + 1
            updates["current_streak"] = user["current_streak"] + 1
            updates["best_streak"] = max(user["best_streak"], user["current_streak"] + 1)
            updates[f"stats.{game_type}.won"] = user["stats"][game_type]["won"] + 1
        else:
            updates["games_lost"] = user["games_lost"] + 1
            updates["current_streak"] = 0

        db.update("users", str(self.user_id), updates)

# ==================== GAME ENGINE ====================
class GameEngine:
    """محرك الألعاب الذكي"""

    # أسئلة لكل نوع ومستوى
    QUESTIONS = {
        GameMode.PUZZLE: {
            Difficulty.EASY: [
                {"q": "ما الذي يأتي مرة واحدة في الدقيقة ومرتين في القرن؟", "a": "حرف الميم"},
                {"q": "ما الذي يمشي بلا أرجل ويبكي بلا عيون؟", "a": "الساعة"},
                {"q": "ما هو الشيء الذي كلما زاد نقص؟", "a": "العمر"},
            ],
            Difficulty.MEDIUM: [
                {"q": "أوجد الرقم التالي: 1, 1, 2, 3, 5, 8, ...", "a": "13"},
                {"q": "ما هو العدد الذي لو ضربته في نفسه كان الناتج أكبر منه بـ 12؟", "a": "4"},
            ],
            Difficulty.HARD: [
                {"q": "لغز السلم: كنت أعلى درجة في سلم، كان الدرجة تحتي وفوقي درجتان، كم درجة السلم؟", "a": "3"},
            ]
        },
        GameMode.QUIZ: {
            Difficulty.EASY: [
                {"q": "ما عاصمة فرنسا؟", "a": "باريس"},
                {"q": "كم قارة في العالم؟", "a": "7"},
            ],
            Difficulty.MEDIUM: [
                {"q": "من مكتشف penicillin؟", "a": "فليمنغ"},
                {"q": "ما أكبر محيط؟", "a": "الهادئ"},
            ]
        },
        GameMode.MATH: {
            Difficulty.EASY: [
                {"q": "5 + 7 × 2", "a": "19"},
                {"q": "12 × 12 - 44", "a": "100"},
            ],
            Difficulty.MEDIUM: [
                {"q": "حل المعادلة: 2x + 5 = 15", "a": "5"},
                {"q": "ما قيمة x: x² = 64", "a": "8"},
            ]
        }
    }

    @classmethod
    def get_question(cls, mode: GameMode, difficulty: Difficulty) -> Dict:
        """جلب سؤال عشوائي"""
        questions = cls.QUESTIONS.get(mode, {}).get(difficulty, [])
        if not questions:
            return {"q": "No questions available", "a": "N/A"}
        return random.choice(questions)

    @classmethod
    def validate_answer(cls, user_answer: str, correct_answer: str) -> bool:
        """التحقق من الإجابة"""
        return user_answer.strip().lower() == correct_answer.strip().lower()

    @classmethod
    def calculate_xp(cls, difficulty: Difficulty, won: bool, streak: int) -> int:
        """حساب XP"""
        base_xp = difficulty.value * 10
        streak_bonus = streak * 2
        win_bonus = 20 if won else 0
        return base_xp + streak_bonus + win_bonus

# ==================== REFERRAL SYSTEM ====================
class ReferralSystem:
    """نظام الإحالة"""

    @classmethod
    def create_referral(cls, referrer_id: int, referred_id: int) -> bool:
        """إنشاء إحالة"""
        referrer = User(referrer_id).get_profile()
        referred = User(referred_id).get_profile()

        if not referrer or not referred:
            return False

        if referred.get("referred_by"):
            return False

        # تسجيل الإحالة
        db.update("users", str(referred_id), {"referred_by": referrer_id})

        # مكافأة المحيل
        db.update("users", str(referrer_id), {
            "points": referrer["points"] + SmartEconomy.REFERRAL_BONUS,
            "total_earned": referrer["total_earned"] + SmartEconomy.REFERRAL_BONUS
        })

        return True

    @classmethod
    def get_referrals(cls, user_id: int) -> List[Dict]:
        """جلب الإحالات"""
        users = db.query("users", {"referred_by": user_id})
        return users

# ==================== LEADERBOARD ====================
class Leaderboard:
    """لوحة المتصدرين"""

    @classmethod
    def update(cls):
        """تحديث اللوحة"""
        users = db.query("users")

        # ترتيب عام
        global_sorted = sorted(users, key=lambda x: x.get("points", 0), reverse=True)[:100]

        # ترتيب أسبوعي
        weekly = [u for u in users if u.get("last_play")]
        weekly_sorted = sorted(weekly, key=lambda x: x.get("points", 0), reverse=True)[:50]

        # ترتيب شهري
        monthly = [u for u in users if u.get("last_play")]
        monthly_sorted = sorted(monthly, key=lambda x: x.get("points", 0), reverse=True)[:50]

        db._save(db.leaderboard_file, {
            "global": global_sorted,
            "weekly": weekly_sorted,
            "monthly": monthly_sorted,
            "updated": datetime.now().isoformat()
        })

    @classmethod
    def get_rank(cls, user_id: int) -> int:
        """جلب الترتيب"""
        lb = db._load(db.leaderboard_file)
        for i, user in enumerate(lb.get("global", []), 1):
            if user.get("user_id") == user_id:
                return i
        return 9999

# ==================== TELEGRAM BOT ====================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

Config = type('Config', (), {
    'BOT_TOKEN': os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
})()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("CryptoPuzzle")

# ==================== BOT HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_obj = User(user.id, user.username, user.first_name)
    profile = user_obj.get_profile()

    if not profile:
        profile = user_obj.register()
        welcome = f"""🎮 مرحباً {user.first_name}!

🏆 CryptoPuzzle - منصة الألعاب الذكية

💰 نقاط ترحيبية: 100

🎯 اختر وضع اللعبة:
"""
    else:
        rank = Leaderboard.get_rank(user.id)
        welcome = f"""🎮 مرحباً {user.first_name}!

🏆 CryptoPuzzle
━━━━━━━━━━━━━━━━
💰 نقاطك: {profile['points']:.0f}
📊 مستواك: {profile['level']}
🎮 لعبت: {profile['games_played']}
🏆 انتصارات: {profile['games_won']}
🔥 السلسلة: {profile['current_streak']}
🏅 ترتيبك: #{rank}

🎯 اختر وضع اللعبة:"""

    keyboard = [
        [InlineKeyboardButton("🧩 لغز", callback_data="game_puzzle"), InlineKeyboardButton("❓ سؤال", callback_data="game_quiz")],
        [InlineKeyboardButton("🔢 رياضيات", callback_data="game_math"), InlineKeyboardButton("🧠 ذاكرة", callback_data="game_memory")],
        [InlineKeyboardButton("⚡ ردود فعل", callback_data="game_reflex")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), InlineKeyboardButton("🏆 المتصدرين", callback_data="leaderboard")],
        [InlineKeyboardButton("👥 الإحالات", callback_data="referrals"), InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")],
    ]

    await update.message.reply_text(welcome, reply_markup=InlineKeyboardMarkup(keyboard))

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    user_obj = User(user_id)
    profile = user_obj.get_profile()

    if data == "stats":
        await query.edit_message_text(
            f"📊 إحصائياتك
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 النقاط: {profile['points']:.0f}
"
            f"📊 المستوى: {profile['level']}
"
            f"🎮 الألعاب: {profile['games_played']}
"
            f"🏆 الانتصارات: {profile['games_won']}
"
            f"🔥 أفضل سلسلة: {profile['best_streak']}
"
            f"💎 XP: {profile['xp']}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
        )

    elif data == "leaderboard":
        lb = db._load(db.leaderboard_file)
        text = "🏆 المتصدرين
━━━━━━━━━━━━━━━━
"
        for i, u in enumerate(lb.get("global", [])[:10], 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            text += f"{medal} {u.get('first_name', 'Unknown')}: {u.get('points', 0):.0f}
"

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

    elif data.startswith("game_"):
        mode_name = data.replace("game_", "")
        mode = GameMode[mode_name.upper()]
        question = GameEngine.get_question(mode, Difficulty.MEDIUM)

        context.user_data['current_question'] = question
        context.user_data['game_mode'] = mode_name
        context.user_data['start_time'] = time.time()

        await query.edit_message_text(
            f"🎮 {mode_name}

"
            f"❓ {question['q']}

"
            f"⏰ أجب بسرعة!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])
        )

    elif data == "back":
        await start(update, context)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    user_obj = User(user_id)
    profile = user_obj.get_profile()

    if 'current_question' in context.user_data:
        question = context.user_data['current_question']
        mode = context.user_data.get('game_mode', 'puzzle')

        # فحص سرعة الإجابة
        time_taken = time.time() - context.user_data.get('start_time', 0)
        if not anti_cheat.check_answer_speed(user_id, time_taken, 30):
            await update.message.reply_text("⚠️ إجابة مشبوهة! تم المراقبة.")
            return

        if GameEngine.validate_answer(text, question['a']):
            reward = SmartEconomy.calculate_reward(
                SmartEconomy.WIN_REWARD_BASE,
                profile['current_streak'],
                Difficulty.MEDIUM
            )

            net, burn = SmartEconomy.apply_burn(reward, SmartEconomy.BURN_ON_GAME)

            user_obj.update_stats(mode, True)
            db.update("users", str(user_id), {
                "points": profile['points'] + net,
                "xp": profile['xp'] + GameEngine.calculate_xp(Difficulty.MEDIUM, True, profile['current_streak']),
                "total_earned": profile['total_earned'] + net
            })

            await update.message.reply_text(
                f"✅ إجابة صحيحة! +{net:.0f} نقطة
"
                f"🔥 سلسلة: {profile['current_streak'] + 1}
"
                f"🔥 حرق: {burn:.0f}"
            )
        else:
            user_obj.update_stats(mode, False)
            await update.message.reply_text(f"❌ خطأ! الإجابة: {question['a']}")

        del context.user_data['current_question']
        return

    await update.message.reply_text("اضغط /start للبدء!")

# ==================== MAIN ====================
def main():
    logger.info("🎮 Starting CryptoPuzzle Professional Platform...")

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
