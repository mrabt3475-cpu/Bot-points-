"""
🤖 Smart Game Bot - نظام ألعاب ذكي
اكسب نقاطاً باللعب - بدون قمار!
"""

import os
import json
import random
import string
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes

# ==================== CONFIG ====================
@dataclass
class Config:
    BOT_TOKEN: str = "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc"
    # نظام النقاط
    POINTS_PER_GAME: int = 10        # نقاط لكل لعبة تلعبها
    WIN_BONUS: int = 20              # نقاط إضافية للفوز
    STREAK_BONUS: int = 5            # نقاط لكل سلسلة انتصارات
    DAILY_PLAY_BONUS: int = 50       # نقاط إضافية للعب اليومي
    LEVEL_UP_BONUS: int = 100        # نقاط عند الصعود لمستوى
    # حدود اللعب
    FREE_GAMES_DAILY: int = 10       # ألعاب مجانية يومياً
    MAX_LEVEL: int = 50
    # AI
    AI_ENABLED: bool = True

config = Config()

# ==================== ENUMS ====================
class UserLevel(Enum):
    NOVICE = 1        # مبتدئ
    BEGINNER = 2      # مبتدئ
    AMATEUR = 3       # هاوٍ
    SKILLED = 4       # ماهر
    EXPERT = 5        # خبير
    MASTER = 6        # أستاذ
    LEGEND = 7        # أسطورة

class GameCategory(Enum):
    PUZZLE = "puzzle"        # ألغاز
    MEMORY = "memory"        # ذاكرة
    QUIZ = "quiz"            # أسئلة
    REFLEX = "reflex"        # ردود فعل
    STRATEGY = "strategy"    # استراتيجية
    CREATIVE = "creative"    # إبداع

# ==================== DATA CLASSES ====================
@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    # النقاط والخبرة
    points: int = 0
    experience: int = 0
    level: int = 1
    # الإحصائيات
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    current_streak: int = 0
    best_streak: int = 0
    # المكافآت
    daily_bonus_claimed: bool = False
    last_claim_date: str = ""
    total_earnings: int = 0
    # التحديات
    challenges_completed: int = 0
    puzzles_solved: int = 0
    quizzes_answered: int = 0
    # الوقت
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())
    last_play: str = ""
    # الأمان
    is_banned: bool = False
    is_admin: bool = False

@dataclass
class GameSession:
    id: str
    user_id: int
    game_type: str
    category: str
    difficulty: str
    score: int = 0
    time_taken: int = 0
    won: bool = False
    points_earned: int = 0
    bonus_points: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class DailyChallenge:
    id: str
    user_id: int
    game_type: str
    target: int
    progress: int = 0
    completed: bool = False
    reward: int = 0
    expires_at: str = ""

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.users_file = "users.json"
        self.sessions_file = "game_sessions.json"
        self.challenges_file = "daily_challenges.json"
        self.puzzles_file = "puzzles.json"
    
    def load_users(self) -> Dict:
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def save_users(self, users: Dict):
        with open(self.users_file, "w") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def load_sessions(self) -> List:
        try:
            with open(self.sessions_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_sessions(self, sessions: List):
        with open(self.sessions_file, "w") as f:
            json.dump(sessions, f, ensure_ascii=False, indent=2)
    
    def load_challenges(self) -> List:
        try:
            with open(self.challenges_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_challenges(self, challenges: List):
        with open(self.challenges_file, "w") as f:
            json.dump(challenges, f, ensure_ascii=False, indent=2)
    
    def load_puzzles(self) -> List:
        try:
            with open(self.puzzles_file, "r") as f:
                return json.load(f)
        except:
            return self.get_default_puzzles()
    
    def save_puzzles(self, puzzles: List):
        with open(self.puzzles_file, "w") as f:
            json.dump(puzzles, f, ensure_ascii=False, indent=2)
    
    def get_default_puzzles(self) -> List:
        return [
            # ألغاز منطقية
            {"type": "logic", "question": "ما هو الرقم التالي: 2، 6، 12، 20، 30، ...", "answer": "42", "hint": "الفروق: 4، 6، 8، 10، 12"},
            {"type": "logic", "question": "ما هو الرقم الخطأ: 2، 3، 5، 8، 12، 17", "answer": "12", "hint": "كل رقم هو مجموع السابقتين + 1"},
            {"type": "logic", "question": "أكمل السلسلة: أ، ج، هـ، ...", "answer": "و", "hint": "الحروف المتحركة"},
            {"type": "logic", "question": "إذا كان A=1، B=2، ما هو CAB؟", "answer": "312", "hint": "C=3, A=1, B=2"},
            {"type": "logic", "question": "ما هو اليوم بعد tomorrow yesterday؟", "answer": "اليوم", "hint": "فكر في المعنى"},
            # ألغاز رياضية
            {"type": "math", "question": "ما هو 7 × 8 - 4؟", "answer": "52", "hint": "الضرب أولاً"},
            {"type": "math", "question": "ما هو 100 ÷ 4 + 3 × 5؟", "answer": "40", "hint": "العمليات بالترتيب"},
            {"type": "math", "question": "ما هو مربع 12؟", "answer": "144", "hint": "12 × 12"},
            {"type": "math", "question": "ما هو 15% من 200؟", "answer": "30", "hint": "15 ÷ 100 × 200"},
            # ألغاز كلمات
            {"type": "word", "question": "ما هو عكس 'ساخن'؟", "answer": "بارد", "hint": "برد"},
            {"type": "word", "question": "ما هو جمع 'كتاب'؟", "answer": "كتب", "hint": "ك ت ب"},
            {"type": "word", "question": "ما هو اسم الفاعل من 'كتب'؟", "answer": "كاتب", "hint": "يكتب"},
            # ألغاز عامة
            {"type": "general", "question": "ما هو أكبر كوكب في النظام الشمسي؟", "answer": "المشتري", "hint": "كبير"},
            {"type": "general", "question": "ما عاصمة فرنسا؟", "answer": "باريس", "hint": "برج"},
            {"type": "general", "question": "من مكتشف أمريكا؟", "answer": "كولومبوس", "hint": "كريستوفر"},
            {"type": "general", "question": "كم قارة في العالم؟", "answer": "7", "hint": "سبع"},
            {"type": "general", "question": "ما أطول نهر في العالم؟", "answer": "النيل", "hint": "في أفريقيا"},
        ]

db = Database()

# ==================== HELPERS ====================
def generate_id(prefix: str = "ID", length: int = 8) -> str:
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_user(user_id: int) -> User:
    users = db.load_users()
    if str(user_id) not in users:
        user = User(user_id=user_id)
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
        2: ("هاوٍ", 100),
        3: ("ماهر", 300),
        4: ("خبير", 600),
        5: ("أستاذ", 1000),
        6: ("محترف", 1500),
        7: ("أسطورة", 2500),
        8: ("موهوب", 4000),
        9: ("عبقري", 6000),
        10: ("خرافي", 10000),
    }
    
    for lvl in range(10, 0, -1):
        if level >= lvl:
            return levels.get(lvl, ("غير معروف", 0))
    return ("مبتدئ", 0)

def calculate_level(experience: int) -> int:
    """حساب المستوى من الخبرة"""
    thresholds = [0, 100, 300, 600, 1000, 1500, 2500, 4000, 6000, 10000, 15000, 20000]
    for i, threshold in enumerate(thresholds):
        if experience < threshold:
            return i + 1
    return len(thresholds)

def get_xp_for_next_level(current_level: int) -> int:
    """الخبرة المطلوبة للمستوى التالي"""
    thresholds = [0, 100, 300, 600, 1000, 1500, 2500, 4000, 6000, 10000, 15000, 20000]
    if current_level < len(thresholds):
        return thresholds[current_level]
    return thresholds[-1]

# ==================== GAMES ====================
GAMES = {
    # ألغاز
    "puzzle": {
        "name": "🧩 لغز",
        "category": "puzzle",
        "description": "حل الألغاز المنطقية",
        "base_points": 15,
        "win_bonus": 10,
        "difficulty_levels": ["easy", "medium", "hard"]
    },
    "math_puzzle": {
        "name": "🔢 لغز رياضي",
        "category": "puzzle",
        "description": "حل المسائل الرياضية",
        "base_points": 12,
        "win_bonus": 8,
        "difficulty_levels": ["easy", "medium", "hard"]
    },
    # ذاكرة
    "memory": {
        "name": "🧠 ذاكرة",
        "category": "memory",
        "description": "تذكر تسلسل الأرقام",
        "base_points": 10,
        "win_bonus": 5,
        "difficulty_levels": ["easy", "medium", "hard"]
    },
    # أسئلة
    "quiz": {
        "name": "❓ سؤال",
        "category": "quiz",
        "description": "أجب على الأسئلة العامة",
        "base_points": 8,
        "win_bonus": 5,
        "difficulty_levels": ["easy", "medium", "hard"]
    },
    # ردود فعل
    "reflex": {
        "name": "⚡ ردود فعل",
        "category": "reflex",
        "description": "اضغط في الوقت المناسب",
        "base_points": 10,
        "win_bonus": 7,
        "difficulty_levels": ["easy", "medium", "hard"]
    },
    # سرعة
    "speed": {
        "name": "🚀 سرعة",
        "category": "reflex",
        "description": "أجب بسرعة",
        "base_points": 12,
        "win_bonus": 8,
        "difficulty_levels": ["easy", "medium", "hard"]
    },
}

def get_puzzle(difficulty: str = "medium") -> Dict:
    """الحصول على لغز عشوائي"""
    puzzles = db.load_puzzles()
    
    if difficulty == "easy":
        filtered = [p for p in puzzles if p.get("type") in ["word", "general"]]
    elif difficulty == "hard":
        filtered = [p for p in puzzles if p.get("type") == "logic"]
    else:
        filtered = puzzles
    
    return random.choice(filtered) if filtered else puzzles[0]

def get_quiz_question(difficulty: str = "medium") -> Dict:
    """الحصول على سؤال"""
    quizzes = [
        {"q": "ما عاصمة اليابان؟", "a": "طوكيو", "options": ["طوكيو", "كيوتو", "أوساكا", "يوكوهاما"]},
        {"q": "من написа 'Romeo and Juliet'؟", "a": "شكسبير", "options": ["شكسبير", "ديكنز", "هاملت", "برنارد شو"]},
        {"q": "ما هو العنصر الرمز 'O'؟", "a": "الأكسجين", "options": ["الأكسجين", "الذهب", "الفضة", "الحديد"]},
        {"q": "كم عدد ألوان قوس قزح؟", "a": "7", "options": ["7", "6", "8", "5"]},
        {"q": "ما هو أكبر محيط؟", "a": "الهادئ", "options": ["الهادئ", "الأطلسي", "الهندي", "القطبي"]},
        {"q": "من هو مؤسس فيسبوك؟", "a": "مارك", "options": ["مارك", "إيلون", "جيف", "بيل"]},
        {"q": "ما هو أقرب كوكب للشمس؟", "a": "عطارد", "options": ["عطارد", "الزهرة", "المريخ", "الأرض"]},
        {"q": "كم عدد أسنان الإنسان البالغ؟", "a": "32", "options": ["32", "28", "30", "34"]},
    ]
    return random.choice(quizzes)

def play_game(user_id: int, game_type: str, user_answer: str, difficulty: str = "medium") -> Tuple[bool, str, int]:
    """اللعب - كلعبة تكسب نقاط بغض النظر عن النتيجة!"""
    user = get_user(user_id)
    
    if game_type not in GAMES:
        return False, "اللعبة غير موجودة", 0
    
    game = GAMES[game_type]
    won = False
    points_earned = game["base_points"]
    bonus_points = 0
    
    # التحقق من الإجابة
    if game_type in ["puzzle", "math_puzzle"]:
        puzzle = get_puzzle(difficulty)
        correct_answer = puzzle.get("answer", "").strip().lower()
        user_answer = user_answer.strip().lower()
        
        if correct_answer == user_answer:
            won = True
            bonus_points = game["win_bonus"]
            points_earned += bonus_points
            feedback = f"✅ إجابة صحيحة! +{points_earned} نقطة"
        else:
            feedback = f"❌ إجابة خاطئة. الإجابة: {puzzle['answer']}\n💡 تلميح: {puzzle.get('hint', '')}\n+{points_earned} نقطة للمحاولة!"
    
    elif game_type == "quiz":
        quiz = get_quiz_question(difficulty)
        correct_answer = quiz.get("a", "").strip()
        
        if user_answer.strip() == correct_answer:
            won = True
            bonus_points = game["win_bonus"]
            points_earned += bonus_points
            feedback = f"✅ إجابة صحيحة! +{points_earned} نقطة"
        else:
            feedback = f"❌ الإجابة الصحيحة: {correct_answer}\n+{points_earned} نقطة للمحاولة!"
    
    elif game_type == "memory":
        # لعبة الذاكرة - محاكاة
        try:
            user_num = int(user_answer)
            target = random.randint(1, 9)
            if user_num == target:
                won = True
                bonus_points = game["win_bonus"]
                points_earned += bonus_points
                feedback = f"✅ تذكرت الرقم {target}! +{points_earned} نقطة"
            else:
                feedback = f"الرقم كان {target}. +{points_earned} نقطة!",
        except:
            feedback = "أدخل رقماً من 1-9"
            points_earned = 0
    
    else:
        # ألعاب أخرى
        won = random.random() > 0.5
        if won:
            bonus_points = game["win_bonus"]
            points_earned += bonus_points
            feedback = f"✅ فزت! +{points_earned} نقطة"
        else:
            feedback = f"حاول مرة أخرى! +{points_earned} نقطة"
    
    # تحديث المستخدم
    new_streak = user.current_streak + 1 if won else 0
    streak_bonus = new_streak * config.STREAK_BONUS if won else 0
    
    total_points = points_earned + streak_bonus
    new_experience = user.experience + total_points
    new_level = calculate_level(new_experience)
    
    level_up = new_level > user.level
    if level_up:
        total_points += config.LEVEL_UP_BONUS
        new_experience += config.LEVEL_UP_BONUS
    
    update_user(user_id, {
        "points": user.points + total_points,
        "experience": new_experience,
        "level": new_level,
        "games_played": user.games_played + 1,
        "games_won": user.games_won + 1 if won else user.games_won,
        "games_lost": user.games_lost + 1 if not won else user.games_lost,
        "current_streak": new_streak,
        "best_streak": max(user.best_streak, new_streak),
        "total_earnings": user.total_earnings + total_points,
        "puzzles_solved": user.puzzles_solved + 1 if game_type == "puzzle" else user.puzzles_solved,
        "quizzes_answered": user.quizzes_answered + 1 if game_type == "quiz" else user.quizzes_answered,
        "last_play": datetime.now().isoformat()
    })
    
    # حفظ الجلسة
    session = GameSession(
        id=generate_id("SESSION"),
        user_id=user_id,
        game_type=game_type,
        category=game["category"],
        difficulty=difficulty,
        score=points_earned,
        won=won,
        points_earned=total_points,
        bonus_points=bonus_points + streak_bonus
    )
    sessions = db.load_sessions()
    sessions.append(asdict(session))
    db.save_sessions(sessions)
    
    result_msg = feedback
    if level_up:
        level_name, _ = get_level_info(new_level)
        result_msg += f"\n🎉 تهانينا! صعدت للمستوى {new_level} ({level_name})! +{config.LEVEL_UP_BONUS} نقطة"
    
    if won and new_streak >= 3:
        result_msg += f"\n🔥 سلسلة انتصارات: {new_streak}! +{streak_bonus} نقطة"
    
    return won, result_msg, total_points

def get_daily_bonus(user_id: int) -> Tuple[bool, str]:
    """المكافأة اليومية"""
    user = get_user(user_id)
    today = datetime.now().strftime("%Y-%m-%d")
    
    if user.last_claim_date == today and user.daily_bonus_claimed:
        return False, "المكافأة اليومية مُطالَبة بالفعل!"
    
    update_user(user_id, {
        "points": user.points + config.DAILY_PLAY_BONUS,
        "daily_bonus_claimed": True,
        "last_claim_date": today
    })
    
    return True, f"✅ مكافأة يومية: +{config.DAILY_PLAY_BONUS} نقطة!"

def get_user_stats(user_id: int) -> str:
    """إحصائيات المستخدم"""
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0
    
    next_level_xp = get_xp_for_next_level(user.level)
    progress = (user.experience / next_level_xp * 100) if next_level_xp > 0 else 100
    
    stats = f"""📊 إحصائياتك
━━━━━━━━━━━━━━━━
🎮 المستوى: {user.level} ({level_name})
⭐ النقاط: {user.points}
📈 الخبرة: {user.experience}/{next_level_xp}

📊 الألعاب:
• لعبت: {user.games_played}
• فزت: {user.games_won}
• خسرت: {user.games_lost}
• نسبة الفوز: {win_rate:.1f}%

🔥 السلسلة:
• الحالية: {user.current_streak}
• الأفضل: {user.best_streak}

🏆 الإنجازات:
• الألغاز: {user.puzzles_solved}
• الأسئلة: {user.quizzes_answered}
• المكاسب: {user.total_earnings}

📏 التقدم للمستوى التالي:
[{('█' * int(progress/10)) + ('░' * (10-int(progress/10)))}] {progress:.1f}%
━━━━━━━━━━━━━━━━"""
    return stats

# ==================== AI ASSISTANT ====================
class AIAssistant:
    """مساعد ذكي"""
    
    def __init__(self):
        self.tips = {
            "puzzle": [
                "💡 نصيحة: فكر في الأنماط!",
                "💡 حلل السؤال بعناية",
                "💡 جرب كل الاحتمالات",
            ],
            "quiz": [
                "💡 اقرأ السؤال بتمعن",
                "💡 استبعد الإجابات الخاطئة",
                "💡 ثق بحدسك",
            ],
            "memory": [
                "💡 ركز على التسلسل",
                "💡 كرر بصوت عالٍ",
                "💡 تخيل الأرقام",
            ]
        }
    
    def get_tip(self, game_type: str) -> str:
        return random.choice(self.tips.get(game_type, ["💡 حاول مرة أخرى!"]))
    
    def analyze_performance(self, user: User) -> str:
        if user.games_played == 0:
            return "🌟 مبتدئ جديد! ابدأ اللعب لكسب النقاط!"
        
        win_rate = user.games_won / user.games_played
        
        if win_rate >= 0.8:
            return f"🔥 أداء رائع! {user.games_won} فوز من {user.games_played}!",
        elif win_rate >= 0.6:
            return f"⭐ أداء جيد! استمر في التقدم!",
        elif win_rate >= 0.4:
            return f"💪 جيد!Practice makes perfect!",
        else:
            return f"🎯 كل محاولة تقربك من النجاح!"
    
    def suggest_game(self, user: User) -> str:
        if user.puzzles_solved < 5:
            return "🎯 جرب ألغاز بسيطة!",
        elif user.quizzes_answered < 10:
            return "❓ جرب أسئلة متنوعة!",
        else:
            return "🚀 جرب جميع الألعاب!",

ai = AIAssistant()

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int):
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    keyboard = [
        [InlineKeyboardButton(f"🎮 المستوى {user.level} ({level_name}) | ⭐ {user.points}", callback_data="stats")],
        [InlineKeyboardButton("🧩 ألغاز", callback_data="game_puzzle"), InlineKeyboardButton("❓ أسئلة", callback_data="game_quiz")],
        [InlineKeyboardButton("🧠 ذاكرة", callback_data="game_memory"), InlineKeyboardButton("⚡ سرعة", callback_data="game_speed")],
        [InlineKeyboardButton("🎯 تحدي", callback_data="daily_challenge"), InlineKeyboardButton("📊 إحصائيات", callback_data="stats")],
        [InlineKeyboardButton("💡 نصائح AI", callback_data="ai_tips"), InlineKeyboardButton("🎁 مكافأة", callback_data="daily_bonus")],
    ]
    return InlineKeyboardMarkup(keyboard)

def games_keyboard():
    keyboard = []
    for game_key, game in GAMES.items():
        keyboard.append([InlineKeyboardButton(f"{game['name']} (+{game['base_points']}+{game['win_bonus']})", callback_data=f"play_{game_key}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def difficulty_keyboard(game_type: str):
    keyboard = [
        [InlineKeyboardButton("🟢 سهل", callback_data=f"diff_easy_{game_type}")],
        [InlineKeyboardButton("🟡 متوسط", callback_data=f"diff_medium_{game_type}")],
        [InlineKeyboardButton("🔴 صعب", callback_data=f"diff_hard_{game_type}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== BOT COMMANDS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    
    user_data = get_user(user_id)
    level_name, _ = get_level_info(user_data.level)
    
    welcome = f"""🎮 مرحباً {user.first_name}!

✨ نظام اللعب الذكي:
• كل لعبة تكسب نقاط!
• الفوز يمنح نقاط إضافية
• السلسلة تزيد المكافآت
• المستوى يرفع النقاط

🎯 الألعاب:
• 🧩 ألغاز منطقية
• ❓ أسئلة عامة
• 🧠 ذاكرة
• ⚡ سرعة

💰 كلعبة = {config.POINTS_PER_GAME} نقاط
🏆 الفوز = +{config.WIN_BONUS} نقاط إضافية
🔥 السلسلة = +{config.STREAK_BONUS} لكل سلسلة

🎮 مستواك: {user_data.level} ({level_name})
⭐ نقاطك: {user_data.points}
📈 خبرك: {user_data.experience}
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    stats = get_user_stats(user_id)
    await update.message.reply_text(stats, reply_markup=main_menu_keyboard(user_id))

async def games_menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """🎮 اختر لعبة للعب:
━━━━━━━━━━━━━━━━
كل لعبة تكسب نقاط بغض النظر عن النتيجة!
"""
    await update.message.reply_text(text, reply_markup=games_keyboard())

async def bonus_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    success, msg = get_daily_bonus(user_id)
    await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))

# ==================== CALLBACK HANDLERS ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back":
        await start_command(update, context)
    elif data == "stats":
        stats = get_user_stats(user_id)
        await query.edit_message_text(stats, reply_markup=main_menu_keyboard(user_id))
    elif data == "daily_bonus":
        success, msg = get_daily_bonus(user_id)
        await query.edit_message_text(msg, reply_markup=main_menu_keyboard(user_id))
    elif data == "ai_tips":
        user = get_user(user_id)
        tip = ai.get_tip("puzzle")
        analysis = ai.analyze_performance(user)
        suggestion = ai.suggest_game(user)
        await query.edit_message_text(
            f"🤖 نصائح AI\n━━━━━━━━━━━━━━━━\n\n"
            f"{tip}\n\n{analysis}\n\n{suggestion}",
            reply_markup=main_menu_keyboard(user_id)
        )
    elif data.startswith("game_"):
        game_type = data.replace("game_", "")
        if game_type in GAMES:
            game = GAMES[game_type]
            await query.edit_message_text(
                f"{game['name']}\n"
                f"{game['description']}\n\n"
                f"📊 النقاط:\n"
                f"• الأساسية: {game['base_points']}\n"
                f"• الفوز: +{game['win_bonus']}\n\n"
                f"اختر المستوى:",
                reply_markup=difficulty_keyboard(game_type)
            )
    elif data.startswith("play_"):
        game_type = data.replace("play_", "")
        if game_type in GAMES:
            game = GAMES[game_type]
            await query.edit_message_text(
                f"🎮 {game['name']}\n\n"
                f"أرسل إجابتك الآن!\n"
                f"مثال: جواب 42\n\n"
                f"💡 كل محاولة تكسب {game['base_points']} نقاط",
                reply_markup=back_keyboard()
            )
    elif data.startswith("diff_"):
        parts = data.split("_")
        difficulty = parts[1]
        game_type = parts[2]
        
        if game_type == "puzzle":
            puzzle = get_puzzle(difficulty)
            await query.edit_message_text(
                f"🧩 لغز ({difficulty})\n\n"
                f"{puzzle['question']}\n\n"
                f"أرسل: جواب [إجابتك]",
                reply_markup=back_keyboard()
            )
        elif game_type == "quiz":
            quiz = get_quiz_question(difficulty)
            options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(quiz['options'])])
            await query.edit_message_text(
                f"❓ سؤال ({difficulty})\n\n"
                f"{quiz['question']}\n\n"
                f"{options_text}\n\n"
                f"أرسل: جواب [رقم_الإجابة]",
                reply_markup=back_keyboard()
            )

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    # جواب
    if text.startswith("جواب "):
        answer = text.replace("جواب ", "").strip()
        
        # استخدام آخر لعبة لعبها المستخدم
        sessions = db.load_sessions()
        user_sessions = [s for s in sessions if s["user_id"] == user_id]
        
        if user_sessions:
            last_game = user_sessions[-1]["game_type"]
            won, msg, points = play_game(user_id, last_game, answer)
            await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        else:
            await update.message.reply_text("❌ اختر لعبة أولاً من القائمة!")
        return
    
    # لعبة مباشرة
    if text.startswith("لعب "):
        try:
            parts = text.replace("لعب ", "").split(" ", 1)
            game_type = parts[0]
            answer = parts[1] if len(parts) > 1 else ""
            
            if game_type in GAMES:
                won, msg, points = play_game(user_id, game_type, answer)
                await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
            else:
                await update.message.reply_text("❌ اللعبة غير موجودة!")
        except:
            await update.message.reply_text("❌ الصيغة: `لعب puzzle إجابتك`")
        return
    
    # لغز
    if text == "لغز" or text == "🧩":
        puzzle = get_puzzle("medium")
        await update.message.reply_text(
            f"🧩 لغز\n\n{puzzle['question']}\n\nأرسل: جواب [إجابتك]",
            reply_markup=back_keyboard()
        )
        return
    
    # سؤال
    if text == "سؤال" or text == "❓":
        quiz = get_quiz_question("medium")
        options_text = "\n".join([f"{i+1}. {opt}" for i, opt in enumerate(quiz['options'])])
        await update.message.reply_text(
            f"❓ سؤال\n\n{quiz['question']}\n\n{options_text}\n\nأرسل: جواب [رقم]",
            reply_markup=back_keyboard()
        )
        return
    
    # مكافأة
    if text == "مكافأة" or text == "🎁":
        success, msg = get_daily_bonus(user_id)
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        return
    
    # إحصائيات
    if text == "إحصائيات" or text == "📊":
        stats = get_user_stats(user_id)
        await update.message.reply_text(stats, reply_markup=main_menu_keyboard(user_id))
        return
    
    await update.message.reply_text("❌ أمر غير معروف!\n\n/start", reply_markup=main_menu_keyboard(user_id))

# ==================== MAIN ====================
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("games", games_menu_command))
    app.add_handler(CommandHandler("bonus", bonus_command))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""الأوامر:
/start - بدء
/stats - إحصائياتك
/games - الألعاب
/bonus - مكافأة يومية

الألعاب:
لعب puzzle إجابتك
لعب quiz 1
لغز
سؤال

النقاط:
• كل لعبة: 10+ نقاط
• الفوز: +20 نقطة
• السلسلة: +5 لكل سلسلة
"""))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(handle_message))
    
    print("🎮 Smart Game Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
