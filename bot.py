"""
🎮 PvP Games Bot - ألعاب ضد الأصدقاء + نظام الدمج
"""

from __future__ import annotations
import os
import json
import random
import string
import threading
from datetime import datetime
from typing import Dict, List, Tuple
from dataclasses import dataclass, field, asdict
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")
    MIN_POINTS = 0.01
    MAX_POINTS = 2.0
    MAX_LOBBY_PLAYERS = 10
    DB_PATH = "./data"
    API_PORT = 5000

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("PvPGamesBot")

# ==================== DATA CLASSES ====================
@dataclass
class User:
    user_id: int
    username: str = ""
    first_name: str = ""
    points: float = 0.0
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    current_streak: int = 0
    best_streak: int = 0

@dataclass
class GameRoom:
    id: str
    game_type: str
    host_id: int
    players: List[Dict]
    status: str
    questions: List[Dict] = field(default_factory=list)
    current_question: int = 0

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        self.users_file = f"{db_path}/users.json"
        self.rooms_file = f"{db_path}/rooms.json"
        self._init_files()

    def _init_files(self):
        for f in [self.users_file, self.rooms_file]:
            if not os.path.exists(f):
                with open(f, 'w') as file:
                    json.dump({}, file)

    def _load_json(self, path: str) -> any:
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {}

    def _save_json(self, path: str, data: any):
        with open(path, 'w') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @property
    def users(self) -> Dict:
        return self._load_json(self.users_file)

    @users.setter
    def users(self, data: Dict):
        self._save_json(self.users_file, data)

    @property
    def rooms(self) -> List:
        return self._load_json(self.rooms_file)

    @rooms.setter
    def rooms(self, data: List):
        self._save_json(self.rooms_file, data)

db = Database()

# ==================== HELPERS ====================
def generate_id(prefix: str = "ID", length: int = 6) -> str:
    return f"{prefix}{''.join(random.choices(string.ascii_uppercase + string.digits, k=length))}"

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

def get_random_points() -> float:
    """نقاط عشوائية بين 0.01 و 2"""
    return round(random.uniform(config.MIN_POINTS, config.MAX_POINTS), 2)

# ==================== GAMES CONTENT ====================
QUIZ_BATTLE = [
    {"q": "ما عاصمة فرنسا؟", "a": "باريس"},
    {"q": "من مكتشف أمريكا؟", "a": "كولومبوس"},
    {"q": "ما أكبر كوكب؟", "a": "المشتري"},
    {"q": "كم قارة؟", "a": "7"},
    {"q": "ما أطول نهر؟", "a": "النيل"},
]

MATH_RACE = [
    {"q": "5 + 8 × 2", "a": "21"},
    {"q": "(10 + 5) × 3", "a": "45"},
    {"q": "100 ÷ 4 + 7", "a": "32"},
    {"q": "15 × 15 - 25", "a": "200"},
]

# ==================== GAME ENGINE ====================
class PvPGameEngine:
    @staticmethod
    def create_room(host_id: int, game_type: str) -> GameRoom:
        host = get_user(host_id)
        room = GameRoom(
            id=generate_id("ROOM"),
            game_type=game_type,
            host_id=host_id,
            players=[{"user_id": host_id, "name": host.first_name, "score": 0.0}],
            status="waiting"
        )
        rooms = db.rooms
        rooms.append(asdict(room))
        db.rooms = rooms
        return room

    @staticmethod
    def join_room(room_id: str, user_id: int) -> Tuple[bool, str]:
        rooms = db.rooms
        user = get_user(user_id)

        for i, r in enumerate(rooms):
            if r["id"] == room_id and r["status"] == "waiting":
                if len(r["players"]) >= config.MAX_LOBBY_PLAYERS:
                    return False, "الغرفة ممتلئة!"

                r["players"].append({
                    "user_id": user_id,
                    "name": user.first_name,
                    "score": 0.0
                })

                if len(r["players"]) >= 2:
                    r["status"] = "ready"

                db.rooms = rooms
                return True, f"✅ انضممت للغرفة! 👥 اللاعبون: {len(r['players'])}"

        return False, "الغرفة غير موجودة!"

    @staticmethod
    def answer_question(room_id: str, user_id: int, answer: str) -> Tuple[bool, str]:
        rooms = db.rooms

        for i, r in enumerate(rooms):
            if r["id"] == room_id and r["status"] == "playing":
                current_q = r["current_question"]
                if current_q >= len(r["questions"]):
                    return False, "انتهت الأسئلة!"

                question = r["questions"][current_q]
                correct = answer.strip().lower() == question["a"].strip().lower()

                for p in r["players"]:
                    if p["user_id"] == user_id:
                        if correct:
                            points = get_random_points()
                            p["score"] += points
                            msg = f"✅ إجابة صحيحة! +{points:.2f} نقطة!"
                        else:
                            msg = f"❌ خطأ! الإجابة: {question['a']}"
                        break

                r["current_question"] += 1

                if r["current_question"] >= len(r["questions"]):
                    r["status"] = "finished"
                    sorted_players = sorted(r["players"], key=lambda x: x["score"], reverse=True)
                    winner = sorted_players[0]

                    for p in r["players"]:
                        user = get_user(p["user_id"])
                        update_user(p["user_id"], {
                            "points": user.points + p["score"],
                            "games_played": user.games_played + 1,
                        })

                        if p["user_id"] == winner["user_id"]:
                            update_user(p["user_id"], {
                                "games_won": user.games_won + 1,
                                "current_streak": user.current_streak + 1,
                                "best_streak": max(user.best_streak, user.current_streak + 1)
                            })

                    result = "🏆 النتائج:

"
                    for j, p in enumerate(sorted_players):
                        medal = ["🥇", "🥈", "🥉"][j] if j < 3 else "  "
                        result += f"{medal} {p['name']}: {p['score']:.2f} نقطة
"

                    result += f"
🎉 الفائز: {winner['name']}!"
                    db.rooms = rooms
                    return True, result

                next_q = r["questions"][r["current_question"]]
                msg += f"

🎮 السؤال {r['current_question']+1}/{len(r['questions'])}

{next_q['q']}"

                db.rooms = rooms
                return True, msg

        return False, "اللعبة غير موجودة!"

    @staticmethod
    def get_user_room(user_id: int):
        rooms = db.rooms
        for r in rooms:
            if any(p["user_id"] == user_id for p in r["players"]):
                return GameRoom(**r)
        return None

# ==================== INTEGRATION SYSTEM ====================
class BotIntegration:
    """نظام دمج البوت مع بوتات أخرى"""

    def __init__(self, host="0.0.0.0", port=5000):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self._setup_routes()

    def _setup_routes(self):
        """إعداد المسارات API"""

        @self.app.route('/api/health', methods=['GET'])
        def health():
            return jsonify({"status": "ok", "bot": "PvP Games Bot"})

        @self.app.route('/api/points/<int:user_id>', methods=['GET'])
        def get_user_points(user_id):
            """جلب نقاط مستخدم"""
            user = get_user(user_id)
            return jsonify({
                "user_id": user_id,
                "points": user.points,
                "games_played": user.games_played,
                "games_won": user.games_won
            })

        @self.app.route('/api/add_points', methods=['POST'])
        def add_points_api():
            """إضافة نقاط لمستخدم"""
            data = request.json
            user_id = data.get('user_id')
            points = data.get('points', 0)

            if not user_id:
                return jsonify({"error": "user_id required"}), 400

            user = get_user(user_id)
            update_user(user_id, {"points": user.points + points})

            return jsonify({
                "success": True,
                "user_id": user_id,
                "new_points": user.points + points
            })

        @self.app.route('/api/stats/<int:user_id>', methods=['GET'])
        def get_user_stats(user_id):
            """جلب إحصائيات مستخدم"""
            user = get_user(user_id)
            return jsonify({
                "user_id": user_id,
                "points": user.points,
                "games_played": user.games_played,
                "games_won": user.games_won,
                "games_lost": user.games_lost,
                "current_streak": user.current_streak,
                "best_streak": user.best_streak
            })

        @self.app.route('/api/leaderboard', methods=['GET'])
        def get_leaderboard():
            """جلب قائمة المتصدرين"""
            users = db.users
            sorted_users = sorted(
                users.items(), 
                key=lambda x: x[1].get('points', 0), 
                reverse=True
            )[:10]

            leaderboard = []
            for i, (uid, data) in enumerate(sorted_users, 1):
                leaderboard.append({
                    "rank": i,
                    "user_id": uid,
                    "points": data.get('points', 0),
                    "games_won": data.get('games_won', 0)
                })

            return jsonify({"leaderboard": leaderboard})

        @self.app.route('/api/game/start', methods=['POST'])
        def start_game_api():
            """بدء لعبة عبر API"""
            data = request.json
            user_id = data.get('user_id')
            game_type = data.get('game_type', 'quiz_battle')

            if not user_id:
                return jsonify({"error": "user_id required"}), 400

            room = PvPGameEngine.create_room(user_id, game_type)

            return jsonify({
                "success": True,
                "room_id": room.id,
                "game_type": game_type
            })

        @self.app.route('/api/game/answer', methods=['POST'])
        def answer_game_api():
            """إرسال إجابة عبر API"""
            data = request.json
            user_id = data.get('user_id')
            answer = data.get('answer', '')

            if not user_id:
                return jsonify({"error": "user_id required"}), 400

            room = PvPGameEngine.get_user_room(user_id)
            if not room or room.status != "playing":
                return jsonify({"error": "No active game"}), 400

            success, msg = PvPGameEngine.answer_question(room.id, user_id, answer)

            return jsonify({
                "success": success,
                "message": msg
            })

    def run(self):
        """تشغيل الخادم"""
        print(f"🌐 API Server running on http://{self.host}:{self.port}")
        self.app.run(host=self.host, port=self.port)

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int):
    user = get_user(user_id)
    keyboard = [
        [InlineKeyboardButton(f"⭐ نقاطك: {user.points:.2f} | 🎮 {user.games_played}", callback_data="stats")],
        [InlineKeyboardButton("🎯 غرفة جديدة", callback_data="new_room"), InlineKeyboardButton("🔗 انضم لغرفة", callback_data="join_room")],
    ]
    return InlineKeyboardMarkup(keyboard)

def game_types_keyboard():
    keyboard = [
        [InlineKeyboardButton("❓ سؤال", callback_data="game_quiz_battle")],
        [InlineKeyboardButton("🔢 سباق رياضيات", callback_data="game_math_race")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== BOT HANDLERS ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    user_data = get_user(user_id)

    welcome = f"""⚔️ مرحباً {user.first_name}!

🎮 ألعاب ضد الأصدقاء:

❓ سؤال - أسئلة عامة
🔢 سباق رياضيات

💰 النقاط العشوائية:
• كل إجابة صحيحة
• من {config.MIN_POINTS} إلى {config.MAX_POINTS} نقطة
• عشوائية تماماً!

🌐 API متاح على: http://localhost:5000

⭐ نقاطك: {user_data.points:.2f}
🎮 لعبت: {user_data.games_played}
🏆 فزت: {user_data.games_won}
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)
    win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0

    text = f"""📊 إحصائياتك
━━━━━━━━━━━━━━━━
⭐ النقاط: {user.points:.2f}
🎮 لعبت: {user.games_played}
🏆 فزت: {user.games_won}
🔥 السلسلة: {user.current_streak}
━━━━━━━━━━━━━━━━"""

    if isinstance(update, Update) and update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))
    elif hasattr(update, 'callback_query'):
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(user_id))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "back" or data == "stats":
        await stats_handler(update, context)
        return

    elif data == "new_room":
        await query.edit_message_text("🎯 اختر نوع اللعبة:
", reply_markup=game_types_keyboard())
        return

    elif data.startswith("game_"):
        game_type = data.replace("game_", "")
        room = PvPGameEngine.create_room(user_id, game_type)

        game_names = {"quiz_battle": "❓ سؤال", "math_race": "🔢 سباق رياضيات"}

        await query.edit_message_text(
            f"✅ تم إنشاء غرفة!

"
            f"🎮 النوع: {game_names.get(game_type, game_type)}
"
            f"🔑 كود الغرفة: `{room.id}`

"
            f"شارك الكود مع صديقك!

"
            f"👥 اللاعبين: 1

"
            f"في انتظار لاعب آخر...",
            reply_markup=back_keyboard()
        )
        return

    elif data == "join_room":
        await query.edit_message_text("🔗 انضم لغرفة

أرسل: `انضم ROOM123`", reply_markup=back_keyboard())
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    user_id = update.message.from_user.id

    if text.startswith("انضم "):
        room_id = text.replace("انضم ", "").strip()
        success, msg = PvPGameEngine.join_room(room_id, user_id)
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        return

    if text.startswith("غرفة "):
        game_type = text.replace("غرفة ", "").strip()
        type_map = {"سؤال": "quiz_battle", "رياضيات": "math_race"}
        game = type_map.get(game_type, "quiz_battle")
        room = PvPGameEngine.create_room(user_id, game)
        await update.message.reply_text(
            f"✅ غرفة جديدة!

🔑 الكود: `{room.id}`

صديقك: `انضم {room.id}`",
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    # Answer in game
    room = PvPGameEngine.get_user_room(user_id)
    if room and room.status == "playing":
        success, msg = PvPGameEngine.answer_question(room.id, user_id, text)
        await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        return

    await update.message.reply_text(
        "⚔️ الأوامر:
• `غرفة سؤال`
• `انضم ROOM123`

🌐 API: http://localhost:5000",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== MAIN ====================
def main() -> None:
    logger.info("⚔️ Starting PvP Games Bot with API...")

    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return

    if not FLASK_AVAILABLE:
        logger.warning("Flask not available! API will not start.")

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(message_handler))

    # Start API server in background
    if FLASK_AVAILABLE:
        api_server = BotIntegration(host="0.0.0.0", port=config.API_PORT)
        api_thread = threading.Thread(target=api_server.run, daemon=True)
        api_thread.start()
        logger.info(f"🌐 API: http://localhost:{config.API_PORT}")

    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
