"""
🎮 PvP Games Bot - الإصدار المحسن
✨ تحسينات: مستويات، مكافآت، إنجازات، تحديات، فرق
"""

import os
import json
import random
import string
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field, asdict
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ChatBoostRemoved, ChatBoost
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")
    MIN_POINTS = 0.01
    MAX_POINTS = 2.0
    DAILY_BONUS = 5.0
    LEVEL_UP_BONUS = 10.0
    DB_PATH = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("PvPGamesBot")

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        os.makedirs(config.DB_PATH, exist_ok=True)
        self.users_file = f"{config.DB_PATH}/users.json"
        self.teams_file = f"{config.DB_PATH}/teams.json"
        self.achievements_file = f"{config.DB_PATH}/achievements.json"
        self._init_files()

    def _init_files(self):
        for f in [self.users_file, self.teams_file, self.achievements_file]:
            if not os.path.exists(f):
                self._save(f, {})

    def _load(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save(self, path, data):
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def users(self):
        return self._load(self.users_file)

    @users.setter
    def users(self, data):
        self._save(self.users_file, data)

    @property
    def teams(self):
        return self._load(self.teams_file)

    @teams.setter
    def teams(self, data):
        self._save(self.teams_file, data)

    @property
    def achievements(self):
        return self._load(self.achievements_file)

    @achievements.setter
    def achievements(self, data):
        self._save(self.achievements_file, data)

db = Database()

# ==================== ACHIEVEMENTS ====================
ACHIEVEMENTS = {
    "first_win": {"name": "🎉 الفوز الأول", "desc": "اربح أول لعبة", "points": 5},
    "streak_5": {"name": "🔥 سلسلة 5", "desc": "اربح 5 مرات متتالية", "points": 15},
    "streak_10": {"name": "⚡ سلسلة 10", "desc": "اربح 10 مرات متتالية", "points": 30},
    "points_50": {"name": "💰 جمع 50", "desc": "اجم 50 نقطة", "points": 20},
    "points_100": {"name": "💎 جمع 100", "desc": "اجم 100 نقطة", "points": 50},
    "games_10": {"name": "🎮 لعب 10", "desc": "العب 10 ألعاب", "points": 10},
    "games_50": {"name": "🏆 لعب 50", "desc": "العب 50 لعبة", "points": 40},
    "team_player": {"name": "👥 روح الفريق", "desc": "انضم لفريق", "points": 15},
}

# ==================== LEVELS ====================
def get_level(points: float) -> Tuple[int, float, float]:
    """حساب المستوى بناءً على النقاط"""
    levels = [
        (1, 0, 10),
        (2, 10, 25),
        (3, 25, 50),
        (4, 50, 100),
        (5, 100, 200),
        (6, 200, 350),
        (7, 350, 500),
        (8, 500, 750),
        (9, 750, 1000),
        (10, 1000, 1500),
    ]
    for level, min_p, max_p in levels:
        if points < max_p:
            return level, min_p, max_p
    return 10, 1000, 99999

def get_level_name(level: int) -> str:
    names = {
        1: "مبتدئ", 2: "لاعب", 3: "محترف", 4: "خبير",
        5: "أستاذ", 6: "موهوب", 7: "أسطورة", 8: "بطل",
        9: "محقق", 10: "ملك"
    }
    return names.get(level, "لاعب")

# ==================== HELPERS ====================
def get_user(user_id: int) -> Dict:
    users = db.users
    uid = str(user_id)
    now = datetime.now().isoformat()

    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "points": 0.0,
            "games_played": 0,
            "games_won": 0,
            "games_lost": 0,
            "streak": 0,
            "best_streak": 0,
            "level": 1,
            "daily_claimed": "",
            "achievements": [],
            "team_id": None,
            "hints": 3,
            "created_at": now
        }
        db.users = users
    return users[uid]

def update_user(user_id: int, data: Dict):
    users = db.users
    uid = str(user_id)
    if uid in users:
        users[uid].update(data)
        db.users = users

def get_random_points() -> float:
    return round(random.uniform(config.MIN_POINTS, config.MAX_POINTS), 2)

def check_achievements(user_id: int, user: Dict):
    """فحص الإنجازات"""
    new_achievements = []
    user_achievements = user.get('achievements', [])

    for key, ach in ACHIEVEMENTS.items():
        if key not in user_achievements:
            if key == "first_win" and user['games_won'] >= 1:
                new_achievements.append(key)
            elif key == "streak_5" and user['streak'] >= 5:
                new_achievements.append(key)
            elif key == "streak_10" and user['streak'] >= 10:
                new_achievements.append(key)
            elif key == "points_50" and user['points'] >= 50:
                new_achievements.append(key)
            elif key == "points_100" and user['points'] >= 100:
                new_achievements.append(key)
            elif key == "games_10" and user['games_played'] >= 10:
                new_achievements.append(key)
            elif key == "games_50" and user['games_played'] >= 50:
                new_achievements.append(key)
            elif key == "team_player" and user.get('team_id'):
                new_achievements.append(key)

    if new_achievements:
        bonus = sum(ACHIEVEMENTS[k]['points'] for k in new_achievements)
        user_achievements.extend(new_achievements)
        update_user(user_id, {
            'achievements': user_achievements,
            'points': user['points'] + bonus
        })
        return new_achievements, bonus
    return [], 0

# ==================== GAMES ====================
QUESTIONS = {
    "عام": [
        ("ما عاصمة فرنسا؟", "باريس"),
        ("من مكتشف أمريكا؟", "كولومبوس"),
        ("ما أكبر كوكب؟", "المشتري"),
        ("كم قارة في العالم؟", "7"),
        ("ما أطول نهر؟", "النيل"),
        ("ما عاصمة اليابان؟", "طوكيو"),
        ("من написа هاملت؟", "شكسبير"),
        ("ما أصغر قارة؟", "أستراليا"),
    ],
    "رياضيات": [
        ("5 + 8 × 2", "21"),
        ("10 + 5 × 3", "25"),
        ("100 ÷ 4 + 7", "32"),
        ("15 × 15 - 25", "200"),
        ("50 + 50 ÷ 2", "75"),
    ],
    "علم": [
        ("ما لون الدم؟", "أحمر"),
        ("كم عدد الأسنان؟", "32"),
        ("ما أقرب كوكب للشمس؟", "عطارد"),
        ("ما غاز التنفس؟", "أكسجين"),
    ],
    "تاريخ": [
        ("متى بدأت الحرب العالمية الثانية؟", "1939"),
        ("من بنى الأهرامات؟", "الفراعنة"),
        ("متى اكتشف أمريكا؟", "1492"),
    ]
}

# ==================== KEYBOARDS ====================
def main_keyboard(user_id: int):
    user = get_user(user_id)
    level, min_p, max_p = get_level(user['points'])

    keyboard = [
        [InlineKeyboardButton(f"⭐ {user['points']:.1f} | lvl {level} {get_level_name(level)}", callback_data="profile")],
        [InlineKeyboardButton("❓ سؤال", callback_data="play_عام"), InlineKeyboardButton("🔢 رياضيات", callback_data="play_رياضيات")],
        [InlineKeyboardButton("🔬 علم", callback_data="play_علم"), InlineKeyboardButton("📜 تاريخ", callback_data="play_تاريخ")],
        [InlineKeyboardButton("🎁 مكافأة يومية", callback_data="daily"), InlineKeyboardButton("💡 تلميح", callback_data="hint")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), InlineKeyboardButton("🏆 المتصدرين", callback_data="leaderboard")],
        [InlineKeyboardButton("🏅 الإنجازات", callback_data="achievements"), InlineKeyboardButton("👥 الفرق", callback_data="teams")],
    ]
    return InlineKeyboardMarkup(keyboard)

def game_keyboard(category: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("❓ سؤال جديد", callback_data=f"play_{category}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ])

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

def teams_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إنشاء فريق", callback_data="create_team")],
        [InlineKeyboardButton("🔗 انضم لفريق", callback_data="join_team")],
        [InlineKeyboardButton("👥 فريقي", callback_data="my_team")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    get_user(user.id)

    await update.message.reply_text(
        f"⚔️ مرحباً {user.first_name}!

"
        f"🎮 ألعاب PvP المحسنة
"
        f"━━━━━━━━━━━━━━━━
"
        f"💰 نقاط عشوائية: {config.MIN_POINTS} - {config.MAX_POINTS}
"
        f"🎁 مكافأة يومية: {config.DAILY_BONUS} نقطة
"
        f"💡 تلميحات مجانية: 3

"
        f"اختر لعبة من الأزرار!",
        reply_markup=main_keyboard(user.id)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)

    # Profile
    if data == "profile":
        level, min_p, max_p = get_level(user['points'])
        progress = (user['points'] - min_p) / (max_p - min_p) * 100 if max_p != 99999 else 100

        await query.edit_message_text(
            f"👤 ملفك الشخصي
"
            f"━━━━━━━━━━━━━━━━
"
            f"⭐ النقاط: {user['points']:.1f}
"
            f"📊 المستوى: {level} - {get_level_name(level)}
"
            f"📈 التقدم: {progress:.0f}%
"
            f"🎮 لعبت: {user['games_played']}
"
            f"🏆 فزت: {user['games_won']}
"
            f"🔥 أفضل سلسلة: {user['best_streak']}
"
            f"💡 التلميحات: {user.get('hints', 3)}",
            reply_markup=back_keyboard()
        )

    # Stats
    elif data == "stats":
        win_rate = (user['games_won'] / user['games_played'] * 100) if user['games_played'] > 0 else 0

        await query.edit_message_text(
            f"📊 إحصائياتك
"
            f"━━━━━━━━━━━━━━━━
"
            f"⭐ النقاط: {user['points']:.1f}
"
            f"🎮 لعبت: {user['games_played']}
"
            f"🏆 فزت: {user['games_won']}
"
            f"❌ خسرت: {user['games_lost']}
"
            f"📈 نسبة الفوز: {win_rate:.1f}%
"
            f"🔥 السلسلة: {user['streak']}
"
            f"🏅 الإنجازات: {len(user.get('achievements', []))}",
            reply_markup=back_keyboard()
        )

    # Leaderboard
    elif data == "leaderboard":
        users = db.users
        sorted_users = sorted(users.items(), key=lambda x: x[1]['points'], reverse=True)[:10]

        text = "🏆 المتصدرين
━━━━━━━━━━━━━━━━
"
        for i, (uid, u) in enumerate(sorted_users, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            level = get_level(u['points'])[0]
            text += f"{medal} {u['points']:.1f} نقطة (lvl {level})
"

        await query.edit_message_text(text, reply_markup=back_keyboard())

    # Achievements
    elif data == "achievements":
        user_achs = user.get('achievements', [])
        text = "🏅 الإنجازات
━━━━━━━━━━━━━━━━
"

        for key, ach in ACHIEVEMENTS.items():
            status = "✅" if key in user_achs else "⬜"
            text += f"{status} {ach['name']}
   {ach['desc']} (+{ach['points']})
"

        await query.edit_message_text(text, reply_markup=back_keyboard())

    # Daily bonus
    elif data == "daily":
        today = datetime.now().strftime("%Y-%m-%d")
        last_claim = user.get('daily_claimed', '')

        if last_claim == today:
            await query.answer("⚠️你已经领取了今天的奖励!", show_alert=True)
        else:
            update_user(user_id, {
                'points': user['points'] + config.DAILY_BONUS,
                'daily_claimed': today
            })
            await query.answer(f"🎁 +{config.DAILY_BONUS} نقطة!", show_alert=True)
            user = get_user(user_id)
            await query.edit_message_text(
                f"✅ مكافأة يومية!

🎁 +{config.DAILY_BONUS} نقطة

⭐ نقاطك: {user['points']:.1f}",
                reply_markup=back_keyboard()
            )

    # Hint
    elif data == "hint":
        hints = user.get('hints', 3)
        if hints <= 0:
            await query.answer("⚠️ لا توجد تلميحات!", show_alert=True)
        elif 'current_question' not in context.user_data:
            await query.answer("⚠️ لست في لعبة!", show_alert=True)
        else:
            q, correct = context.user_data['current_question']
            hint = correct[0] + "?" * (len(correct) - 1)
            update_user(user_id, {'hints': hints - 1})
            await query.edit_message_text(
                f"💡 التلميح: {hint}

السؤال: {q}",
                reply_markup=game_keyboard(context.user_data.get('category', 'عام'))
            )

    # Teams
    elif data == "teams":
        await query.edit_message_text("👥 إدارة الفرق
━━━━━━━━━━━━━━━━", reply_markup=teams_keyboard())

    elif data == "create_team":
        await query.edit_message_text(
            "➕ إنشاء فريق جديد

"
            "أرسل اسم الفريق الجديد!",
            reply_markup=back_keyboard()
        )
        context.user_data['waiting_for_team_name'] = True

    elif data == "join_team":
        await query.edit_message_text(
            "🔗 الانضمام لفريق

"
            "أرسل: انضم اسم_الفريق",
            reply_markup=back_keyboard()
        )

    elif data == "my_team":
        team_id = user.get('team_id')
        if not team_id:
            await query.edit_message_text("⚠️ لست في فريق!

انضم أو أنشئ فريقاً.", reply_markup=teams_keyboard())
        else:
            teams = db.teams
            if team_id in teams:
                team = teams[team_id]
                text = f"👥 فـ {team['name']}
━━━━━━━━━━━━━━━━
"
                text += f"👑 المؤسس: {team['owner_name']}
"
                text += f"👥 الأعضاء: {len(team['members'])}
"
                text += f"⭐ مجموع النقاط: {team['points']:.1f}"
                await query.edit_message_text(text, reply_markup=teams_keyboard())

    # Play game
    elif data.startswith("play_"):
        category = data.replace("play_", "")
        q_list = QUESTIONS.get(category, QUESTIONS["عام"])
        q, a = random.choice(q_list)

        context.user_data['current_question'] = (q, a)
        context.user_data['category'] = category

        await query.edit_message_text(
            f"🎮 {category}

❓ {q}

أرسل إجابتك!",
            reply_markup=game_keyboard(category)
        )

    # Back
    elif data == "back":
        await query.edit_message_text(
            f"⚔️ القائمة الرئيسية

⭐ نقاطك: {user['points']:.1f}",
            reply_markup=main_keyboard(user_id)
        )

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    # Create team
    if context.user_data.get('waiting_for_team_name'):
        team_name = text
        team_id = f"team_{random.randint(1000, 9999)}"

        teams = db.teams
        teams[team_id] = {
            "name": team_name,
            "owner_id": user_id,
            "owner_name": update.message.from_user.first_name,
            "members": [user_id],
            "points": 0.0,
            "created_at": datetime.now().isoformat()
        }
        db.teams = teams

        update_user(user_id, {'team_id': team_id})

        await update.message.reply_text(
            f"✅ تم إنشاء الفريق: {team_name}

🔑 معرف الفريق: `{team_id}`",
            reply_markup=main_keyboard(user_id)
        )
        context.user_data['waiting_for_team_name'] = False
        return

    # Join team
    if text.startswith("انضم "):
        team_name = text.replace("انضم ", "").strip()
        teams = db.teams

        found_team = None
        for tid, t in teams.items():
            if t['name'] == team_name:
                found_team = (tid, t)
                break

        if found_team:
            tid, team = found_team
            if user_id not in team['members']:
                team['members'].append(user_id)
                teams[tid] = team
                db.teams = teams
                update_user(user_id, {'team_id': tid})
                await update.message.reply_text(f"✅ انضممت للفريق: {team['name']}", reply_markup=main_keyboard(user_id))
            else:
                await update.message.reply_text("⚠️ أنت بالفعل في هذا الفريق!", reply_markup=main_keyboard(user_id))
        else:
            await update.message.reply_text("⚠️ الفريق غير موجود!", reply_markup=main_keyboard(user_id))
        return

    # Answer question
    if 'current_question' in context.user_data:
        q, correct = context.user_data['current_question']
        category = context.user_data.get('category', 'عام')

        if text.lower() == correct.lower():
            points = get_random_points()
            new_streak = user['streak'] + 1

            update_user(user_id, {
                'points': user['points'] + points,
                'games_played': user['games_played'] + 1,
                'games_won': user['games_won'] + 1,
                'streak': new_streak,
                'best_streak': max(user['best_streak'], new_streak)
            })

            # Check achievements
            user = get_user(user_id)
            new_achs, bonus = check_achievements(user_id, user)

            msg = f"✅ إجابة صحيحة! +{points:.2f} نقطة!
🔥 سلسلة: {new_streak}"
            if new_achs:
                msg += f"

🏅 إنجازات جديدة: {', '.join([ACHIEVEMENTS[a]['name'] for a in new_achs])} (+{bonus})"

            await update.message.reply_text(msg, reply_markup=main_keyboard(user_id))
        else:
            update_user(user_id, {
                'games_played': user['games_played'] + 1,
                'games_lost': user['games_lost'] + 1,
                'streak': 0
            })

            await update.message.reply_text(
                f"❌ خطأ! الإجابة: {correct}",
                reply_markup=main_keyboard(user_id)
            )

        del context.user_data['current_question']
        return

    # Default
    await update.message.reply_text(
        "⚔️ اضغط /start للبدء!",
        reply_markup=main_keyboard(user_id)
    )

# ==================== MAIN ====================
def main():
    logger.info("🎮 Starting PvP Games Bot (Enhanced)...")

    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(message))

    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
