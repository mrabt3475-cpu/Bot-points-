"""
🎮 Smart Games Bot - ألعاب ذكية بدون قمار
ألعاب ترفيهية وتعلمية

🎯 المبدأ:
- اللعب للاستمتاع والتعلم
- كل لعبة تكسب نقاط
- المهارة هي المفتاح
- لا رهانات ولا مخاطر
"""

from __future__ import annotations
import os
import json
import random
import string
import time
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass, field, asdict
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")
    # نقاط - بدون قمار!
    POINTS_PER_GAME: int = 15      # كل لعبة
    WIN_BONUS: int = 20            # الفوز
    STREAK_BONUS: int = 5          # السلسلة
    DAILY_BONUS: int = 50          # المكافأة اليومية
    PERFECT_BONUS: int = 30        # إجابة مثالية
    SPEED_BONUS: int = 10          # سرعة
    # حدود
    MAX_LEVEL: int = 50
    DB_PATH: str = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("SmartGamesBot")

# ==================== ENUMS ====================
class GameCategory(str, Enum):
    PUZZLE = "puzzle"        # ألغاز
    MEMORY = "memory"        # ذاكرة
    QUIZ = "quiz"            # أسئلة
    MATH = "math"            # رياضيات
    LOGIC = "logic"          # منطق
    CREATIVE = "creative"    # إبداع
    SPORTS = "sports"        # رياضة
    VOCAB = "vocab"          # مفردات

# ==================== DATA CLASSES ====================
@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    # النقاط والخبرة
    points: int = 0
    points_lifetime: int = 0
    level: int = 1
    experience: int = 0
    # الإحصائيات
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    current_streak: int = 0
    best_streak: int = 0
    perfect_answers: int = 0
    # حسب اللعبة
    puzzles_solved: int = 0
    memory_levels: int = 0
    quiz_correct: int = 0
    quiz_total: int = 0
    math_solved: int = 0
    logic_solved: int = 0
    # وقت
    total_time_played: int = 0
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_play: str = ""

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    icon: str
    requirement: int
    category: str

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        self.users_file = f"{db_path}/users.json"
        self._init_file()
    
    def _init_file(self):
        if not os.path.exists(self.users_file):
            self._save_json({})
    
    def _load_json(self) -> Dict:
        try:
            with open(self.users_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    
    def _save_json(self, data: Dict):
        with open(self.users_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    @property
    def users(self) -> Dict:
        return self._load_json()
    
    @users.setter
    def users(self, data: Dict):
        self._save_json(data)

db = Database()

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
        1: ("مبتدئ", 0), 2: ("هاوٍ", 100), 3: ("ماهر", 300),
        4: ("خبير", 600), 5: ("أستاذ", 1000), 6: ("محترف", 1800),
        7: ("أسطورة", 3000), 8: ("عبقري", 5000), 9: ("خرافي", 8000),
        10: ("الكمال", 12000)
    }
    return levels.get(level, ("غير معروف", 0))

def calculate_level(exp: int) -> int:
    thresholds = [0, 100, 300, 600, 1000, 1800, 3000, 5000, 8000, 12000]
    for i, t in enumerate(thresholds):
        if exp < t:
            return i + 1
    return len(thresholds) + 1

# ==================== GAMES CONTENT ====================
class GameContent:
    """محتوى الألعاب - أسئلة وألغاز"""
    
    # ألغاز منطقية
    LOGIC_PUZZLES = [
        {"q": "ما الرقم التالي: 2، 6، 12، 20، 30، ...", "a": "42", "hint": "الفروق: 4، 6، 8، 10، 12"},
        {"q": "ما الرقم الخطأ: 2، 3، 5، 8، 12، 17", "a": "12", "hint": "كل رقم = مجموع السابقتين + 1"},
        {"q": "أكمل: أ، ج، هـ، ...", "a": "و", "hint": "الحروف المتحركة"},
        {"q": "إذا A=1، B=2، ما قيمة CAB؟", "a": "312", "hint": "C=3, A=1, B=2"},
        {"q": "ما هو اليوم بعد 'بعد tomorrow'؟", "a": "اليوم", "hint": "فكر في المعنى الحرفي"},
        {"q": "5 + 5 + 5 = 550 أضف خطاً واحداً لتصبح صحيحة", "a": "545+5", "hint": "حول علامة + إلى 4"},
        {"q": "لديك 3 صناديق. واحد فيه كل التفاحات، واحد فيه كل البرتقال، واحد فيه كلاهما. جميع الصناديق مُسماة خطأ. كيف تعرف كل صندوق بفتح صندوق واحد فقط؟", "a": "افتح صندوق البرتقال والتفاح", "hint": "الصندوق المسمى كلاهما"},
    ]
    
    # أسئلة عامة
    QUIZ_QUESTIONS = [
        {"q": "ما عاصمة فرنسا؟", "a": "باريس", "c": "جغرافيا"},
        {"q": "من مكتشف أمريكا؟", "a": "كولومبوس", "c": "تاريخ"},
        {"q": "ما أكبر كوكب في النظام الشمسي؟", "a": "المشتري", "c": "علم"},
        {"q": "كم قارة في العالم؟", "a": "7", "c": "جغرافيا"},
        {"q": "ما أطول نهر في العالم؟", "a": "النيل", "c": "جغرافيا"},
        {"q": "ما لون الدم في الأوردة؟", "a": "أزرق", "c": "علم"},
        {"q": "من أبو الفيزياء الحديثة؟", "a": "أينشتاين", "c": "علم"},
        {"q": "ما عنصر الأكسجين؟", "a": "O", "c": "كيمياء"},
        {"q": "ما 12 × 12؟", "a": "144", "c": "رياضيات"},
        {"q": "ما الجذر التربيعي لـ 64؟", "a": "8", "c": "رياضيات"},
        {"q": "ما جمع كتاب؟", "a": "كتب", "c": "لغة"},
        {"q": "ما عكس كبير؟", "a": "صغير", "c": "لغة"},
        {"q": "ما اسم الفاعل من كتب؟", "a": "كاتب", "c": "لغة"},
        {"q": "من هو مؤسس فيسبوك؟", "a": "مارك", "c": "تكنولوجيا"},
        {"q": "ما أقرب كوكب للشمس؟", "a": "عطارد", "c": "علم"},
    ]
    
    # مسائل رياضية
    MATH_PROBLEMS = [
        {"q": "5 + 8 × 2", "a": "21"},
        {"q": "(10 + 5) × 3", "a": "45"},
        {"q": "100 ÷ 4 + 7", "a": "32"},
        {"q": "15 × 15 - 25", "a": "200"},
        {"q": "(50 - 20) ÷ 5 + 10", "a": "16"},
        {"q": "8² + 6²", "a": "100"},
        {"q": "3³ + 4³", "a": "91"},
        {"q": "√144 + √169", "a": "25"},
        {"q": "25% من 200", "a": "50"},
        {"q": "10 + 10 × 10", "a": "110"},
    ]
    
    # مفردات إنجليزية
    VOCAB_WORDS = [
        {"q": "ما معنى 'Hello'؟", "a": "مرحبا", "c": "أساسي"},
        {"q": "ما معنى 'Thank you'؟", "a": "شكرا", "c": "أساسي"},
        {"q": "ما معنى 'Computer'؟", "a": "حاسوب", "c": "تكنولوجيا"},
        {"q": "ما معنى 'Internet'؟", "a": "إنترنت", "c": "تكنولوجيا"},
        {"q": "ما معنى 'Beautiful'؟", "a": "جميل", "c": "صفة"},
        {"q": "ما معنى 'Happy'؟", "a": "سعيد", "c": "صفة"},
    ]
    
    @classmethod
    def get_logic(cls) -> Dict:
        return random.choice(cls.LOGIC_PUZZLES)
    
    @classmethod
    def get_quiz(cls) -> Dict:
        return random.choice(cls.QUIZ_QUESTIONS)
    
    @classmethod
    def get_math(cls) -> Dict:
        return random.choice(cls.MATH_PROBLEMS)
    
    @classmethod
    def get_vocab(cls) -> Dict:
        return random.choice(cls.VOCAB_WORDS)

# ==================== ACHIEVEMENTS ====================
ACHIEVEMENTS = [
    Achievement("first_game", "البداية", "العب أول لعبة", "🎮", 1, "general"),
    Achievement("puzzle_10", "محقق", "حل 10 ألغاز", "🧩", 10, "puzzle"),
    Achievement("puzzle_50", "عالم الألغاز", "حل 50 لغز", "🧩", 50, "puzzle"),
    Achievement("quiz_20", "مثقف", "20 إجابة صحيحة", "📚", 20, "quiz"),
    Achievement("quiz_100", "عالم", "100 إجابة صحيحة", "📚", 100, "quiz"),
    Achievement("math_10", "حاسب", "حل 10 مسائل", "🔢", 10, "math"),
    Achievement("math_50", "رياضي", "50 مسألة", "🔢", 50, "math"),
    Achievement("streak_5", "مثابر", "5 انتصارات متتالية", "🔥", 5, "streak"),
    Achievement("streak_10", "متميز", "10 انتصارات", "🔥", 10, "streak"),
    Achievement("streak_25", "أسطورة", "25 انتصار", "👑", 25, "streak"),
    Achievement("games_50", "لاعب نشط", "50 لعبة", "🏃", 50, "general"),
    Achievement("games_200", "محترف", "200 لعبة", "⭐", 200, "general"),
    Achievement("perfect_5", "دقيق", "5 إجابات مثالية", "💯", 5, "special"),
    Achievement("level_5", "صاعد", "المستوى 5", "⬆️", 5, "level"),
    Achievement("level_10", "متقدم", "المستوى 10", "⬆️", 10, "level"),
]

# ==================== GAME ENGINE ====================
class GameEngine:
    """محرك الألعاب"""
    
    @staticmethod
    def play_logic(user_id: int, answer: str) -> Tuple[bool, str, int]:
        """لعبة منطقية"""
        puzzle = GameContent.get_logic()
        correct = answer.strip().lower() == puzzle["a"].strip().lower()
        
        points = config.POINTS_PER_GAME
        user = get_user(user_id)
        
        if correct:
            points += config.WIN_BONUS
            msg = f"✅ إجابة صحيحة!\n\n💡 {puzzle['a']}\n\n+{points} نقطة!"
        else:
            msg = f"❌ الإجابة الصحيحة: {puzzle['a']}\n\n💡 تلميح: {puzzle['hint']}\n\n+{points} نقطة"
        
        # تحديث
        new_streak = user.current_streak + 1 if correct else 0
        total = points + (new_streak * config.STREAK_BONUS if correct else 0)
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if correct else user.games_won,
            "games_lost": user.games_lost + 1 if not correct else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "puzzles_solved": user.puzzles_solved + 1 if correct else user.puzzles_solved,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        return correct, msg, total
    
    @staticmethod
    def play_quiz(user_id: int, answer: str) -> Tuple[bool, str, int]:
        """لعبة سؤال"""
        quiz = GameContent.get_quiz()
        correct = answer.strip().lower() == quiz["a"].strip().lower()
        
        points = config.POINTS_PER_GAME
        user = get_user(user_id)
        
        if correct:
            points += config.WIN_BONUS
            msg = f"✅ صحيح! ({quiz['c']})\n\n+{points} نقطة!"
        else:
            msg = f"❌ الإجابة: {quiz['a']}\n\n+{points} نقطة"
        
        new_streak = user.current_streak + 1 if correct else 0
        total = points + (new_streak * config.STREAK_BONUS if correct else 0)
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if correct else user.games_won,
            "games_lost": user.games_lost + 1 if not correct else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "quiz_correct": user.quiz_correct + 1 if correct else user.quiz_correct,
            "quiz_total": user.quiz_total + 1,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        return correct, msg, total
    
    @staticmethod
    def play_math(user_id: int, answer: str) -> Tuple[bool, str, int]:
        """لعبة رياضيات"""
        problem = GameContent.get_math()
        correct = answer.strip() == problem["a"].strip()
        
        points = config.POINTS_PER_GAME + 5
        user = get_user(user_id)
        
        if correct:
            points += config.WIN_BONUS
            msg = f"✅ إجابة صحيحة!\n\n🔢 {problem['a']}\n\n+{points} نقطة!"
        else:
            msg = f"❌ الإجابة: {problem['a']}\n\n+{points} نقطة"
        
        new_streak = user.current_streak + 1 if correct else 0
        total = points + (new_streak * config.STREAK_BONUS if correct else 0)
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if correct else user.games_won,
            "games_lost": user.games_lost + 1 if not correct else user.games_lost,
            "current_streak": new_streak,
            "best_streak": max(user.best_streak, new_streak),
            "math_solved": user.math_solved + 1 if correct else user.math_solved,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        return correct, msg, total
    
    @staticmethod
    def play_vocab(user_id: int, answer: str) -> Tuple[bool, str, int]:
        """لعبة مفردات إنجليزية"""
        word = GameContent.get_vocab()
        correct = answer.strip().lower() == word["a"].strip().lower()
        
        points = config.POINTS_PER_GAME
        user = get_user(user_id)
        
        if correct:
            points += config.WIN_BONUS
            msg = f"✅ صحيح! ({word['c']})\n\n+{points} نقطة!"
        else:
            msg = f"❌ الإجابة: {word['a']}\n\n+{points} نقطة"
        
        new_streak = user.current_streak + 1 if correct else 0
        total = points + (new_streak * config.STREAK_BONUS if correct else 0)
        
        update_user(user_id, {
            "points": user.points + total,
            "points_lifetime": user.points_lifetime + total,
            "games_played": user.games_played + 1,
            "games_won": user.games_won + 1 if correct else user.games_won,
            "current_streak": new_streak,
            "experience": user.experience + total,
            "level": calculate_level(user.experience + total)
        })
        
        return correct, msg, total
    
    @staticmethod
    def get_daily_bonus(user_id: int) -> Tuple[bool, str]:
        """مكافأة يومية"""
        user = get_user(user_id)
        today = datetime.now().strftime("%Y-%m-%d")
        
        if user.last_play == today:
            return False, "المكافأة اليومية مُطالَبة بالفعل!"
        
        bonus = config.DAILY_BONUS
        update_user(user_id, {
            "points": user.points + bonus,
            "last_play": today
        })
        
        return True, f"🎁 مكافأة يومية: +{bonus} نقطة!"

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    keyboard = [
        [InlineKeyboardButton(f"🎮 المستوى {user.level} ({level_name}) | ⭐ {user.points}", callback_data="stats")],
        [InlineKeyboardButton("🧩 لغز", callback_data="game_logic"), InlineKeyboardButton("❓ سؤال", callback_data="game_quiz")],
        [InlineKeyboardButton("🔢 رياضيات", callback_data="game_math"), InlineKeyboardButton("📝 مفردات", callback_data="game_vocab")],
        [InlineKeyboardButton("🎁 مكافأة", callback_data="daily_bonus"), InlineKeyboardButton("🏆 إنجازات", callback_data="achievements")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

def play_again_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 لعبة أخرى", callback_data="play_again")]])

# ==================== BOT HANDLERS ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    
    user_data = get_user(user_id)
    level_name, _ = get_level_info(user_data.level)
    
    welcome = f"""🎮 مرحباً {user.first_name}!

✨ ألعاب ذكية بدون قمار:

🧩 ألغاز منطقية
❓ أسئلة عامة
🔢 مسائل رياضية
📝 مفردات إنجليزية

💰 نظام النقاط:
• كل لعبة: +{config.POINTS_PER_GAME} نقطة
• الفوز: +{config.WIN_BONUS} نقطة
• السلسلة: +{config.STREAK_BONUS} لكل مستوى
• مكافأة يومية: +{config.DAILY_BONUS} نقطة

🎯 مستواك: {user_data.level} ({level_name})
⭐ نقاطك: {user_data.points}
🔥 السلسلة: {user_data.current_streak}

💡 العب وتعلم واستمتع!
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))
    logger.info(f"User {user_id} started")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    next_level_xp = get_level_info(user.level + 1)[1]
    current_level_xp = get_level_info(user.level)[1]
    progress = ((user.experience - current_level_xp) / (next_level_xp - current_level_xp) * 100) if next_level_xp > current_level_xp else 100
    
    win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0
    
    text = f"""📊 إحصائياتك
━━━━━━━━━━━━━━━━
🏆 المستوى: {user.level} ({level_name})
⭐ النقاط: {user.points}
📈 الخبرة: {user.experience}

📏 التقدم: [{('█' * int(progress/10)) + ('░' * (10-int(progress/10)))}] {progress:.0f}%

🎮 الألعاب:
• لعبت: {user.games_played}
• فزت: {user.games_won}
• خسرت: {user.games_lost}
• نسبة الفوز: {win_rate:.1f}%

🧩 الألغاز: {user.puzzles_solved}
❓ الأسئلة: {user.quiz_correct}/{user.quiz_total}
🔢 الرياضيات: {user.math_solved}

🔥 السلسلة: {user.current_streak}
🏆 الأفضل: {user.best_streak}
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def achievements_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    text = "🏆 الإنجازات\n━━━━━━━━━━━━━━━━\n"
    
    for ach in ACHIEVEMENTS:
        earned = False
        
        if ach.category == "general" and ach.id == "first_game":
            earned = user.games_played >= ach.requirement
        elif ach.category == "puzzle":
            earned = user.puzzles_solved >= ach.requirement
        elif ach.category == "quiz":
            earned = user.quiz_correct >= ach.requirement
        elif ach.category == "math":
            earned = user.math_solved >= ach.requirement
        elif ach.category == "streak":
            earned = user.best_streak >= ach.requirement
        elif ach.category == "level":
            earned = user.level >= ach.requirement
        elif ach.category == "general" and ach.id == "games_50":
            earned = user.games_played >= 50
        elif ach.category == "general" and ach.id == "games_200":
            earned = user.games_played >= 200
        
        status = "✅" if earned else "⬜"
        text += f"{status} {ach.icon} {ach.name}\n"
        text += f"   📝 {ach.description}\n\n"
    
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back" or data == "play_again":
        await stats_handler(update, context)
        return
    elif data == "stats":
        await stats_handler(update, context)
        return
    elif data == "achievements":
        await achievements_handler(update, context)
        return
    elif data == "daily_bonus":
        success, msg = GameEngine.get_daily_bonus(user_id)
        await query.edit_message_text(msg, reply_markup=main_menu_keyboard(user_id))
        return
    
    # Games
    elif data == "game_logic":
        puzzle = GameContent.get_logic()
        context.user_data['current_game'] = 'logic'
        await query.edit_message_text(
            f"🧩 لغز منطقي\n\n{puzzle['q']}\n\n"
            f"📝 أرسل إجابتك:",
            reply_markup=back_keyboard()
        )
        return
    
    elif data == "game_quiz":
        quiz = GameContent.get_quiz()
        context.user_data['current_game'] = 'quiz'
        await query.edit_message_text(
            f"❓ سؤال\n\n{quiz['q']}\n\n"
            f"📝 أرسل إجابتك:",
            reply_markup=back_keyboard()
        )
        return
    
    elif data == "game_math":
        problem = GameContent.get_math()
        context.user_data['current_game'] = 'math'
        await query.edit_message_text(
            f"🔢 مسألة رياضية\n\n{problem['q']}\n\n"
            f"📝 أرسل الإجابة:",
            reply_markup=back_keyboard()
        )
        return
    
    elif data == "game_vocab":
        word = GameContent.get_vocab()
        context.user_data['current_game'] = 'vocab'
        await query.edit_message_text(
            f"📝 مفردات إنجليزية\n\n{word['q']}\n\n"
            f"📝 أرسل الترجمة:",
            reply_markup=back_keyboard()
        )
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    
    # Get current game from context
    current_game = context.user_data.get('current_game', '')
    
    if current_game == 'logic':
        correct, msg, points = GameEngine.play_logic(user_id, text)
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        del context.user_data['current_game']
        return
    
    elif current_game == 'quiz':
        correct, msg, points = GameEngine.play_quiz(user_id, text)
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        del context.user_data['current_game']
        return
    
    elif current_game == 'math':
        correct, msg, points = GameEngine.play_math(user_id, text)
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        del context.user_data['current_game']
        return
    
    elif current_game == 'vocab':
        correct, msg, points = GameEngine.play_vocab(user_id, text)
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        del context.user_data['current_game']
        return
    
    # Shortcuts
    if text == "لغز" or text == "🧩":
        puzzle = GameContent.get_logic()
        context.user_data['current_game'] = 'logic'
        await update.message.reply_text(f"🧩 {puzzle['q']}\n\nأرسل إجابتك:", reply_markup=back_keyboard())
        return
    
    if text == "سؤال" or text == "❓":
        quiz = GameContent.get_quiz()
        context.user_data['current_game'] = 'quiz'
        await update.message.reply_text(f"❓ {quiz['q']}\n\nأرسل إجابتك:", reply_markup=back_keyboard())
        return
    
    if text == "رياضيات" or text == "🔢":
        problem = GameContent.get_math()
        context.user_data['current_game'] = 'math'
        await update.message.reply_text(f"🔢 {problem['q']}\n\nأرسل الإجابة:", reply_markup=back_keyboard())
        return
    
    if text == "مفردات" or text == "📝":
        word = GameContent.get_vocab()
        context.user_data['current_game'] = 'vocab'
        await update.message.reply_text(f"📝 {word['q']}\n\nأرسل الترجمة:", reply_markup=back_keyboard())
        return
    
    if text == "مكافأة" or text == "🎁":
        success, msg = GameEngine.get_daily_bonus(user_id)
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        return
    
    if text == "إحصائيات" or text == "📊":
        await stats_handler(update, context)
        return
    
    if text == "إنجازات" or text == "🏆":
        await achievements_handler(update, context)
        return
    
    # Default
    await update.message.reply_text(
        "🎮 العب من القائمة أو استخدم:\n🧩 لغز\n❓ سؤال\n🔢 رياضيات\n📝 مفردات",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== MAIN ====================
def main() -> None:
    logger.info("🎮 Starting Smart Games Bot (No Gambling)...")
    
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("achievements", achievements_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""🎮 الأوامر:
/start - بدء
/stats - إحصائياتك
/achievements - إنجازاتك

🧩 لغز - لعبة منطقية
❓ سؤال - سؤال عام
🔢 رياضيات - مسألة
📝 مفردات - ترجمة
🎁 مكافأة - مكافأة يومية
"""))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(message_handler))
    
    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
