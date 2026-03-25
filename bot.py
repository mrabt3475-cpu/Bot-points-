"""
🎮 Smart Interactive Games Bot
ألعاب تفاعلية كاملة مع أزرار ولعب حي

🎯 الميزات:
- ألعاب تفاعلية بأزرار
- تحديات يومية
- إنجازات وميداليات
- مسابقات
- ألعاب ذاكرة
- ألعاب سرعة
- ألغاز تفاعلية
"""

from __future__ import annotations
import os
import json
import random
import string
import time
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field, asdict
from functools import wraps
import logging

# Telegram
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, ConversationHandler
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")
    # Points
    POINTS_PER_GAME: int = 15
    WIN_BONUS: int = 25
    STREAK_BONUS: int = 10
    DAILY_BONUS: int = 50
    # Games
    MEMORY_SEQUENCE_LENGTH: int = 5
    REFLEX_TIMEOUT: int = 3
    QUIZ_TIME_LIMIT: int = 30
    # Database
    DB_PATH: str = "./data"

config = Config()

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    level=logging.INFO
)
logger = logging.getLogger("GamesBot")

# ==================== ENUMS ====================
class GameType(str, Enum):
    MEMORY = "memory"
    REFLEX = "reflex"
    QUIZ = "quiz"
    MATH = "math"
    WORD = "word"
    EMOJI = "emoji"
    TIC_TAC_TOE = "tictactoe"
    GUESS_NUMBER = "guess_number"

class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
    TIMEOUT = "timeout"

class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

# ==================== DATA CLASSES ====================
@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    points: int = 0
    points_lifetime: int = 0
    level: int = 1
    experience: int = 0
    # Games stats
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    current_streak: int = 0
    best_streak: int = 0
    # Specific games
    memory_best: int = 0
    reflex_best: float = 0.0
    quiz_correct: int = 0
    quiz_total: int = 0
    math_solved: int = 0
    # Achievements
    achievements: List[str] = field(default_factory=list)
    # Daily
    daily_played: int = 0
    last_play_date: str = ""
    # Admin
    is_admin: bool = False
    is_banned: bool = False
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class GameSession:
    id: str
    user_id: int
    game_type: str
    status: str
    score: int = 0
    time_taken: float = 0.0
    difficulty: str = "medium"
    data: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    icon: str
    requirement: int
    points: int

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        self.users_file = f"{db_path}/users.json"
        self.sessions_file = f"{db_path}/sessions.json"
        self.achievements_file = f"{db_path}/achievements.json"
        self._init_files()
    
    def _init_files(self):
        for f in [self.users_file, self.sessions_file, self.achievements_file]:
            if not os.path.exists(f):
                self._save_json(f, {} if "users" in f or "achievements" in f else [])
    
    def _load_json(self, path: str) -> Any:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {} if "users" in path or "achievements" in path else []
    
    def _save_json(self, path: str, data: Any):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @property
    def users(self) -> Dict:
        return self._load_json(self.users_file)
    
    @users.setter
    def users(self, data: Dict):
        self._save_json(self.users_file, data)
    
    @property
    def sessions(self) -> List:
        return self._load_json(self.sessions_file)
    
    @sessions.setter
    def sessions(self, data: List):
        self._save_json(self.sessions_file, data)

db = Database()

# ==================== ACHIEVEMENTS ====================
ACHIEVEMENTS = [
    Achievement("first_game", "البداية", "العب أول لعبة", "🎮", 1, 10),
    Achievement("streak_3", "م连续胜利", "3 انتصارات متتالية", "🔥", 3, 25),
    Achievement("streak_5", "خارق", "5 انتصارات متتالية", "⚡", 5, 50),
    Achievement("streak_10", "أسطورة", "10 انتصارات متتالية", "👑", 10, 100),
    Achievement("memory_master", "عبقري الذاكرة", "10 مستويات ذاكرة", "🧠", 10, 75),
    Achievement("reflex_master", "سرعة البرق", "فوز في 10 ألعاب سرعة", "⚡", 10, 75),
    Achievement("quiz_master", "عالم", "50 إجابة صحيحة", "📚", 50, 100),
    Achievement("math_wizard", "ساحر الرياضيات", "حل 30 مسألة", "🔢", 30, 75),
    Achievement("games_100", "لاعب نشط", "100 لعبة", "🏆", 100, 50),
    Achievement("games_500", "محترف", "500 لعبة", "⭐", 500, 150),
    Achievement("points_1000", "مليونير نقاط", "1000 نقطة", "💰", 1000, 100),
    Achievement("points_5000", "ثري", "5000 نقطة", "💎", 5000, 250),
]

# ==================== GAMES CONTENT ====================
QUIZ_QUESTIONS = [
    # General
    {"q": "ما عاصمة فرنسا؟", "a": "باريس", "c": "جغرافيا"},
    {"q": "من مكتشف أمريكا؟", "a": "كولومبوس", "c": "تاريخ"},
    {"q": "ما أكبر كوكب؟", "a": "المشتري", "c": "علم"},
    {"q": "كم قارة؟", "a": "7", "c": "جغرافيا"},
    {"q": "ما أطول نهر؟", "a": "النيل", "c": "جغرافيا"},
    # Science
    {"q": "ما لون الدم في الأوردة؟", "a": "أزرق", "c": "علم"},
    {"q": "من أبو الفيزياء؟", "a": "أينشتاين", "c": "علم"},
    {"q": "ما عنصر الأكسجين؟", "a": "O", "c": "كيمياء"},
    # Math
    {"q": "ما 12 × 12؟", "a": "144", "c": "رياضيات"},
    {"q": "ما الجذر التربيعي لـ 64؟", "a": "8", "c": "رياضيات"},
    {"q": "ما 25% من 200؟", "a": "50", "c": "رياضيات"},
    # Arabic
    {"q": "ما جمع كتاب؟", "a": "كتب", "c": "لغة"},
    {"q": "ما عكس كبير؟", "a": "صغير", "c": "لغة"},
    {"q": "ما اسم الفاعل من كتب؟", "a": "كاتب", "c": "لغة"},
]

MATH_PROBLEMS = [
    {"q": "5 + 8 × 2", "a": "21", "difficulty": "easy"},
    {"q": "(10 + 5) × 3", "a": "45", "difficulty": "easy"},
    {"q": "100 ÷ 4 + 7", "a": "32", "difficulty": "medium"},
    {"q": "15 × 15 - 25", "a": "200", "difficulty": "medium"},
    {"q": "(50 - 20) ÷ 5 + 10", "a": "16", "difficulty": "hard"},
    {"q": "8² + 6²", "a": "100", "difficulty": "hard"},
    {"q": "3³ + 4³", "a": "91", "difficulty": "hard"},
    {"q": "√144 + √169", "a": "25", "difficulty": "hard"},
]

EMOJI_PUZZLES = [
    {"q": "🐱 + 🐱 = ?", "a": "🐈", "hint": "قط"},
    {"q": "☀️ + 🌙 = ?", "a": "🌗", "hint": "قمر"},
    {"q": "🔥 + 💧 = ?", "a": "🧖", "hint": "بخار"},
    {"q": "🍎 + 🍋 = ?", "a": "🍹", "hint": "عصير"},
    {"q": "👨 + 👩 = ?", "a": "👶", "hint": "طفل"},
    {"q": "🌱 + ☀️ = ?", "a": "🌻", "hint": "زهرة"},
    {"q": "💰 + 💰 = ?", "a": "💵", "hint": "فلوس"},
    {"q": "📖 + 👓 = ?", "a": "📚", "hint": "مكتبة"},
]

# ==================== HELPERS ====================
def generate_id(prefix: str = "ID", length: int = 8) -> str:
    return f"{prefix}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=length))}"

def get_user(user_id: int) -> User:
    users = db.users
    if str(user_id) not in users:
        user = User(user_id=user_id)
        users[str(user_id)] = asdict(user)
        db.users = users
        return user
    return User(**users[str(user_id)])

def update_user(user_id: int, data: Dict):
    users = db.users
    if str(user_id) in users:
        users[str(user_id)].update(data)
        db.users = users

def get_level_info(level: int) -> Tuple[str, int]:
    levels = {
        1: ("مبتدئ", 0),
        2: ("هاوٍ", 100),
        3: ("ماهر", 300),
        4: ("خبير", 600),
        5: ("أستاذ", 1000),
        6: ("محترف", 1800),
        7: ("أسطورة", 3000),
        8: ("خرافي", 5000),
    }
    return levels.get(level, ("غير معروف", 0))

def calculate_level(exp: int) -> int:
    thresholds = [0, 100, 300, 600, 1000, 1800, 3000, 5000]
    for i, t in enumerate(thresholds):
        if exp < t:
            return i + 1
    return len(thresholds) + 1

def check_achievements(user: User) -> List[str]:
    """التحقق من الإنجازات"""
    new_achievements = []
    
    for ach in ACHIEVEMENTS:
        if ach.id in user.achievements:
            continue
        
        earned = False
        
        if ach.id == "first_game" and user.games_played >= 1:
            earned = True
        elif ach.id == "streak_3" and user.current_streak >= 3:
            earned = True
        elif ach.id == "streak_5" and user.current_streak >= 5:
            earned = True
        elif ach.id == "streak_10" and user.current_streak >= 10:
            earned = True
        elif ach.id == "memory_master" and user.memory_best >= 10:
            earned = True
        elif ach.id == "reflex_master" and user.reflex_best > 0:
            earned = True
        elif ach.id == "quiz_master" and user.quiz_correct >= 50:
            earned = True
        elif ach.id == "math_wizard" and user.math_solved >= 30:
            earned = True
        elif ach.id == "games_100" and user.games_played >= 100:
            earned = True
        elif ach.id == "games_500" and user.games_played >= 500:
            earned = True
        elif ach.id == "points_1000" and user.points >= 1000:
            earned = True
        elif ach.id == "points_5000" and user.points >= 5000:
            earned = True
        
        if earned:
            new_achievements.append(ach)
            user.achievements.append(ach.id)
    
    return new_achievements

# ==================== GAMES ====================
class GameEngine:
    """محرك الألعاب التفاعلية"""
    
    @staticmethod
    def start_memory(user_id: int, difficulty: str = "medium") -> Dict:
        """لعبة الذاكرة - تسلسل الأرقام"""
        length = {"easy": 3, "medium": 5, "hard": 7}.get(difficulty, 5)
        sequence = [random.randint(1, 9) for _ in range(length)]
        
        session = GameSession(
            id=generate_id("MEM"),
            user_id=user_id,
            game_type="memory",
            status="waiting",
            difficulty=difficulty,
            data={"sequence": sequence, "length": length, "show_time": 3}
        )
        
        sessions = db.sessions
        sessions.append(asdict(session))
        db.sessions = sessions
        
        return {
            "session_id": session.id,
            "sequence": sequence,
            "show_time": 3,
            "length": length
        }
    
    @staticmethod
    def check_memory(user_id: int, user_input: str) -> Tuple[bool, str, int]:
        """التحقق من إجابة الذاكرة"""
        sessions = db.sessions
        user_sessions = [s for s in sessions if s["user_id"] == user_id and s["game_type"] == "memory"]
        
        if not user_sessions:
            return False, "ابدأ لعبة جديدة!", 0
        
        session = user_sessions[-1]
        sequence = session["data"]["sequence"]
        user_seq = [int(c) for c in user_input if c.isdigit()]
        
        won = user_seq == sequence
        points = config.POINTS_PER_GAME
        
        if won:
            points += config.WIN_BONUS
            msg = f"✅ صحيح! التسلسل: {''.join(map(str, sequence))}\n+{points} نقطة!"
        else:
            msg = f"❌ خطأ! التسلسل كان: {''.join(map(str, sequence))}\n+{config.POINTS_PER_GAME} نقطة"
        
        # Update user
        user = get_user(user_id)
        new_streak = user.current_streak + 1 if won else 0
        streak_bonus = new_streak * config.STREAK_BONUS if won else 0
        total = points + streak_bonus
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if won else user.games_won,
            "games_lost": user.games_lost + 1 if not won else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "memory_best": max(user.memory_best, len(sequence)) if won else user.memory_best,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        # Check achievements
        user = get_user(user_id)
        new_achs = check_achievements(user)
        if new_achs:
            for ach in new_achs:
                msg += f"\n🏆 إنجاز جديد: {ach.icon} {ach.name} (+{ach.points})
"
        
        return won, msg, total
    
    @staticmethod
    def start_reflex(user_id: int) -> Dict:
        """لعبة ردود الفعل - اضغط عند ظهور الإشارة"""
        wait_time = random.uniform(2, 5)
        
        session = GameSession(
            id=generate_id("REF"),
            user_id=user_id,
            game_type="reflex",
            status="waiting",
            data={"wait_time": wait_time, "start_time": time.time()}
        )
        
        sessions = db.sessions
        sessions.append(asdict(session))
        db.sessions = sessions
        
        return {
            "session_id": session.id,
            "wait_time": wait_time
        }
    
    @staticmethod
    def check_reflex(user_id: int, reaction_time: float) -> Tuple[bool, str, int]:
        """التحقق من سرعة رد الفعل"""
        sessions = db.sessions
        user_sessions = [s for s in sessions if s["user_id"] == user_id and s["game_type"] == "reflex"]
        
        if not user_sessions:
            return False, "ابدأ لعبة جديدة!", 0
        
        session = user_sessions[-1]
        wait_time = session["data"]["wait_time"]
        
        won = reaction_time < config.REFLEX_TIMEOUT
        points = config.POINTS_PER_GAME
        
        if won:
            points += config.WIN_BONUS
            msg = f"⚡ رد فعل: {reaction_time:.3f} ثانية!\n+{points} نقطة!"
        else:
            msg = f"❌ بطيء جداً: {reaction_time:.3f} ثانية\n+{config.POINTS_PER_GAME} نقطة"
        
        user = get_user(user_id)
        new_streak = user.current_streak + 1 if won else 0
        total = points + (new_streak * config.STREAK_BONUS if won else 0)
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if won else user.games_won,
            "games_lost": user.games_lost + 1 if not won else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "reflex_best": max(user.reflex_best, reaction_time) if reaction_time < user.reflex_best or user.reflex_best == 0 else user.reflex_best,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        return won, msg, total
    
    @staticmethod
    def get_quiz(difficulty: str = "medium") -> Dict:
        """الحصول على سؤال"""
        if difficulty == "easy":
            qs = [q for q in QUIZ_QUESTIONS if q.get("c") in ["جغرافيا", "لغة"]]
        elif difficulty == "hard":
            qs = [q for q in QUIZ_QUESTIONS if q.get("c") in ["رياضيات", "علم"]]
        else:
            qs = QUIZ_QUESTIONS
        
        q = random.choice(qs)
        return {
            "question": q["q"],
            "answer": q["a"],
            "category": q.get("c", "عام")
        }
    
    @staticmethod
    def check_quiz(user_id: int, user_answer: str, correct_answer: str) -> Tuple[bool, str, int]:
        """التحقق من إجابة السؤال"""
        won = user_answer.strip().lower() == correct_answer.strip().lower()
        points = config.POINTS_PER_GAME
        
        if won:
            points += config.WIN_BONUS
            msg = f"✅ إجابة صحيحة! +{points} نقطة!"
        else:
            msg = f"❌ الإجابة: {correct_answer}\n+{config.POINTS_PER_GAME} نقطة"
        
        user = get_user(user_id)
        new_streak = user.current_streak + 1 if won else 0
        total = points + (new_streak * config.STREAK_BONUS if won else 0)
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if won else user.games_won,
            "games_lost": user.games_lost + 1 if not won else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "quiz_correct": user.quiz_correct + 1 if won else user.quiz_correct,
            "quiz_total": user.quiz_total + 1,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        return won, msg, total
    
    @staticmethod
    def get_math(difficulty: str = "medium") -> Dict:
        """الحصول على مسألة رياضية"""
        if difficulty == "easy":
            problems = [p for p in MATH_PROBLEMS if p.get("difficulty") == "easy"]
        elif difficulty == "hard":
            problems = [p for p in MATH_PROBLEMS if p.get("difficulty") == "hard"]
        else:
            problems = MATH_PROBLEMS
        
        p = random.choice(problems)
        return {
            "question": p["q"],
            "answer": p["a"],
            "difficulty": p.get("difficulty", "medium")
        }
    
    @staticmethod
    def check_math(user_id: int, user_answer: str, correct_answer: str) -> Tuple[bool, str, int]:
        """التحقق من إجابة الرياضيات"""
        won = user_answer.strip() == correct_answer.strip()
        points = config.POINTS_PER_GAME + 5
        
        if won:
            points += config.WIN_BONUS
            msg = f"✅ صحيح! +{points} نقطة!"
        else:
            msg = f"❌ الإجابة: {correct_answer}\n+{config.POINTS_PER_GAME} نقطة"
        
        user = get_user(user_id)
        new_streak = user.current_streak + 1 if won else 0
        total = points + (new_streak * config.STREAK_BONUS if won else 0)
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if won else user.games_won,
            "games_lost": user.games_lost + 1 if not won else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "math_solved": user.math_solved + 1 if won else user.math_solved,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        return won, msg, total
    
    @staticmethod
    def get_emoji_puzzle() -> Dict:
        """الحصول على لغز إيموجي"""
        p = random.choice(EMOJI_PUZZLES)
        return {
            "question": p["q"],
            "answer": p["a"],
            "hint": p.get("hint", "")
        }

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    keyboard = [
        [InlineKeyboardButton(f"🎮 المستوى {user.level} ({level_name}) | ⭐ {user.points}", callback_data="stats")],
        [InlineKeyboardButton("🧠 ذاكرة", callback_data="game_memory"), InlineKeyboardButton("⚡ سرعة", callback_data="game_reflex")],
        [InlineKeyboardButton("❓ سؤال", callback_data="game_quiz"), InlineKeyboardButton("🔢 رياضيات", callback_data="game_math")],
        [InlineKeyboardButton("😀 إيموجي", callback_data="game_emoji"), InlineKeyboardButton("🎯 تحدي", callback_data="daily_challenge")],
        [InlineKeyboardButton("🏆 إنجازات", callback_data="achievements"), InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(keyboard)

def games_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🧠 ذاكرة - تذكر الأرقام", callback_data="game_memory")],
        [InlineKeyboardButton("⚡ سرعة - اضغط بسرعة", callback_data="game_reflex")],
        [InlineKeyboardButton("❓ سؤال - أسئلة عامة", callback_data="game_quiz")],
        [InlineKeyboardButton("🔢 رياضيات - مسائل", callback_data="game_math")],
        [InlineKeyboardButton("😀 إيموجي - حل اللغز", callback_data="game_emoji")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def difficulty_keyboard(game_type: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🟢 سهل", callback_data=f"diff_easy_{game_type}")],
        [InlineKeyboardButton("🟡 متوسط", callback_data=f"diff_medium_{game_type}")],
        [InlineKeyboardButton("🔴 صعب", callback_data=f"diff_hard_{game_type}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

def play_again_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔄 لعب مرة أخرى", callback_data="play_again")],
        [InlineKeyboardButton("🏠 القائمة", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== BOT HANDLERS ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    
    user_data = get_user(user_id)
    level_name, _ = get_level_info(user_data.level)
    
    welcome = f"""🎮 مرحباً {user.first_name}!

✨ ألعاب تفاعلية:
• 🧠 ذاكرة - تذكر تسلسل الأرقام
• ⚡ سرعة - اضغط عند ظهور الإشارة
• ❓ سؤال - أسئلة عامة
• 🔢 رياضيات - مسائل حسابية
• 😀 إيموجي - حل لغز الإيموجي

🏆 نظام النقاط:
• كل لعبة: {config.POINTS_PER_GAME} نقاط
• الفوز: +{config.WIN_BONUS} نقاط
• السلسلة: +{config.STREAK_BONUS} لكل سلسلة

🎯 مستواك: {user_data.level} ({level_name})
⭐ نقاطك: {user_data.points}
🔥 السلسلة: {user_data.current_streak}
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))
    logger.info(f"User {user_id} started games bot")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0
    
    text = f"""📊 إحصائياتك
━━━━━━━━━━━━━━━━
🏆 المستوى: {user.level} ({level_name})
⭐ النقاط: {user.points}
📈 الخبرة: {user.experience}

🎮 الألعاب:
• لعبت: {user.games_played}
• فزت: {user.games_won}
• خسرت: {user.games_lost}
• نسبة الفوز: {win_rate:.1f}%

🔥 السلسلة:
• الحالية: {user.current_streak}
• الأفضل: {user.best_streak}

🧠 أفضل ذاكرة: {user.memory_best}
⚡ أفضل سرعة: {user.reflex_best:.3f}s
❓ صحيحة: {user.quiz_correct}/{user.quiz_total}
🔢 رياضيات: {user.math_solved}

🏆 الإنجازات: {len(user.achievements)}/{len(ACHIEVEMENTS)}
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def achievements_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = "🏆 الإنجازات\n━━━━━━━━━━━━━━━━\n"
    
    for ach in ACHIEVEMENTS:
        earned = ach.id in user.achievements
        status = "✅" if earned else "⬜"
        text += f"{status} {ach.icon} {ach.name}\n"
        text += f"   📝 {ach.description}\n"
        text += f"   💰 +{ach.points} نقطة\n\n"
    
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    # Navigation
    if data == "back" or data == "home":
        await stats_handler(update, context)
        return
    
    elif data == "stats":
        await stats_handler(update, context)
        return
    
    elif data == "achievements":
        await achievements_handler(update, context)
        return
    
    # Game selection
    elif data == "game_memory":
        await query.edit_message_text(
            "🧠 لعبة الذاكرة\n\n"
            "ستظهر أرقاماً، تذكرها وأدخلها!\n\n"
            "اختر المستوى:",
            reply_markup=difficulty_keyboard("memory")
        )
        return
    
    elif data == "game_reflex":
        game_data = GameEngine.start_reflex(user_id)
        await query.edit_message_text(
            "⚡ لعبة السرعة\n\n"
            "⏳ انتظر الإشارة...\n\n"
            "عندما تظهر 🔔 اضغط بسرعة!\n\n"
            "⏱️ اضغط على الزر خلال 3 ثوانٍ",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔔 اضغط هنا!", callback_data="reflex_press")
            ]])
        )
        # Store wait time in context for later
        context.user_data['reflex_wait'] = game_data['wait_time']
        context.user_data['reflex_start'] = time.time()
        return
    
    elif data == "game_quiz":
        quiz = GameEngine.get_quiz("medium")
        context.user_data['current_quiz'] = quiz
        await query.edit_message_text(
            f"❓ سؤال\n\n{quiz['question']}\n\n"
            f"📝 أرسل إجابتك الآن!\n"
            f"⏱️ {config.QUIZ_TIME_LIMIT} ثانية",
            reply_markup=back_keyboard()
        )
        return
    
    elif data == "game_math":
        math = GameEngine.get_math("medium")
        context.user_data['current_math'] = math
        await query.edit_message_text(
            f"🔢 مسألة رياضية\n\n{math['question']}\n\n"
            f"📝 أرسل الإجابة!",
            reply_markup=back_keyboard()
        )
        return
    
    elif data == "game_emoji":
        emoji = GameEngine.get_emoji_puzzle()
        context.user_data['current_emoji'] = emoji
        await query.edit_message_text(
            f"😀 لغز الإيموجي\n\n{emoji['question']}\n\n"
            f"💡 تلميح: {emoji['hint']}\n\n"
            f"📝 أرسل إجابتك!",
            reply_markup=back_keyboard()
        )
        return
    
    # Difficulty selection
    elif data.startswith("diff_"):
        parts = data.split("_")
        difficulty = parts[1]
        game_type = parts[2]
        
        if game_type == "memory":
            game_data = GameEngine.start_memory(user_id, difficulty)
            await query.edit_message_text(
                f"🧠 الذاكرة ({difficulty})\n\n"
                f"📱 الأرقام: {''.join(map(str, game_data['sequence']))}\n\n"
                f"⏱️ تذكر خلال {game_data['show_time']} ثوانٍ!\n\n"
                f"أدخل الأرقام الآن:",
                reply_markup=back_keyboard()
            )
        return
    
    # Reflex press
    elif data == "reflex_press":
        start_time = context.user_data.get('reflex_start', 0)
        if start_time:
            reaction_time = time.time() - start_time
            won, msg, points = GameEngine.check_reflex(user_id, reaction_time)
            await query.edit_message_text(msg, reply_markup=play_again_keyboard())
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Quiz answer
    if 'current_quiz' in context.user_data:
        quiz = context.user_data['current_quiz']
        won, msg, points = GameEngine.check_quiz(user_id, text, quiz['answer'])
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        del context.user_data['current_quiz']
        return
    
    # Math answer
    if 'current_math' in context.user_data:
        math = context.user_data['current_math']
        won, msg, points = GameEngine.check_math(user_id, text, math['answer'])
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        del context.user_data['current_math']
        return
    
    # Emoji answer
    if 'current_emoji' in context.user_data:
        emoji = context.user_data['current_emoji']
        won = text == emoji['answer']
        points = config.POINTS_PER_GAME + config.WIN_BONUS if won else config.POINTS_PER_GAME
        
        user = get_user(user_id)
        new_streak = user.current_streak + 1 if won else 0
        total = points + (new_streak * config.STREAK_BONUS if won else 0)
        
        if won:
            msg = f"✅ صحيح! الإيموجي: {emoji['answer']}\n+{total} نقطة!"
        else:
            msg = f"❌ الإجابة: {emoji['answer']}\n+{config.POINTS_PER_GAME} نقطة"
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if won else user.games_won,
            "games_lost": user.games_lost + 1 if not won else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        del context.user_data['current_emoji']
        return
    
    # Memory answer (numbers only)
    if text.isdigit() and len(text) >= 3:
        won, msg, points = GameEngine.check_memory(user_id, text)
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        return
    
    # Default
    await update.message.reply_text(
        "🎮 العب من القائمة!",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== MAIN ====================
def main() -> None:
    logger.info("🎮 Starting Interactive Games Bot...")
    
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("achievements", achievements_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""الأوامر:
/start - بدء
/stats - إحصائياتك
/achievements - إنجازاتك

اختر لعبة من القائمة!
"""))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(message_handler))
    
    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
