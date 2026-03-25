"""
🎮 Ultimate Games Bot - PvP + XO + Interactive Games
ألعاب متعددةplayer مع XO وتحديات

🎯 الميزات:
- PvP ضد لاعبين
- XO (tic-tac-toe)
- أحجار ورقة مقص
- تخمين الرقم
- مسابقات
- بطولات
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
    # Points
    POINTS_PER_GAME: int = 15
    WIN_BONUS: int = 25
    PVP_BONUS: int = 35
    STREAK_BONUS: int = 10
    TOURNAMENT_PRIZE: int = 200
    # Games
    DB_PATH: str = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("GamesBot")

# ==================== ENUMS ====================
class GameType(str, Enum):
    MEMORY = "memory"
    REFLEX = "reflex"
    QUIZ = "quiz"
    MATH = "math"
    EMOJI = "emoji"
    XO = "xo"
    RPS = "rps"
    GUESS_NUMBER = "guess_number"
    PVP_CHALLENGE = "pvp"

class GameStatus(str, Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    WON = "won"
    LOST = "lost"
    DRAW = "draw"

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
    # Stats
    games_played: int = 0
    games_won: int = 0
    games_lost: int = 0
    current_streak: int = 0
    best_streak: int = 0
    # PvP
    pvp_wins: int = 0
    pvp_losses: int = 0
    pvp_draws: int = 0
    xo_wins: int = 0
    xo_losses: int = 0
    rps_wins: int = 0
    # Achievements
    achievements: List[str] = field(default_factory=list)
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class PvPMatch:
    id: str
    game_type: str
    player1_id: int
    player2_id: int
    bet: int
    status: str
    player1_move: str = ""
    player2_move: str = ""
    winner_id: int = None
    rounds: List[Dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class XOGame:
    id: str
    player1_id: int
    player2_id: int
    board: List[str] = field(default_factory=lambda: ["1", "2", "3", "4", "5", "6", "7", "8", "9"])
    current_turn: int = 0
    moves: List[str] = field(default_factory=list)
    winner_id: int = None
    status: str = "playing"
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Tournament:
    id: str
    name: str
    game_type: str
    max_players: int
    players: List[Dict] = field(default_factory=list)
    matches: List[Dict] = field(default_factory=list)
    status: str = "registration"
    prize: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        self.users_file = f"{db_path}/users.json"
        self.pvp_file = f"{db_path}/pvp.json"
        self.xo_file = f"{db_path}/xo.json"
        self.tournaments_file = f"{db_path}/tournaments.json"
        self._init_files()
    
    def _init_files(self):
        for f in [self.users_file, self.pvp_file, self.xo_file, self.tournaments_file]:
            if not os.path.exists(f):
                self._save_json(f, {} if "users" in f else [])
    
    def _load_json(self, path: str) -> Any:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {} if "users" in path else []
    
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
    def pvp_matches(self) -> List:
        return self._load_json(self.pvp_file)
    
    @pvp_matches.setter
    def pvp_matches(self, data: List):
        self._save_json(self.pvp_file, data)
    
    @property
    def xo_games(self) -> List:
        return self._load_json(self.xo_file)
    
    @xo_games.setter
    def xo_games(self, data: List):
        self._save_json(self.xo_file, data)
    
    @property
    def tournaments(self) -> List:
        return self._load_json(self.tournaments_file)
    
    @tournaments.setter
    def tournaments(self, data: List):
        self._save_json(self.tournaments_file, data)

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
    levels = {1: ("مبتدئ", 0), 2: ("هاوٍ", 100), 3: ("ماهر", 300), 4: ("خبير", 600), 5: ("أستاذ", 1000), 6: ("محترف", 1800), 7: ("أسطورة", 3000)}
    return levels.get(level, ("غير معروف", 0))

def calculate_level(exp: int) -> int:
    thresholds = [0, 100, 300, 600, 1000, 1800, 3000]
    for i, t in enumerate(thresholds):
        if exp < t:
            return i + 1
    return len(thresholds) + 1

# ==================== XO GAME ====================
class XOGameEngine:
    """محرك لعبة XO"""
    
    WIN_PATTERNS = [
        [0, 1, 2], [3, 4, 5], [6, 7, 8],  # rows
        [0, 3, 6], [1, 4, 7], [2, 5, 8],  # cols
        [0, 4, 8], [2, 4, 6]              # diagonals
    ]
    
    @staticmethod
    def create_game(player1_id: int, player2_id: int) -> XOGame:
        game = XOGame(
            id=generate_id("XO"),
            player1_id=player1_id,
            player2_id=player2_id,
            board=[" "] * 9,
            current_turn=player1_id
        )
        games = db.xo_games
        games.append(asdict(game))
        db.xo_games = games
        return game
    
    @staticmethod
    def get_board_display(board: List[str]) -> str:
        return f"""
┌───┬───┬───
│ {board[0]} │ {board[1]} │ {board[2]} │
├───┼───┼───
│ {board[3]} │ {board[4]} │ {board[5]} │
├───┼───┼───
│ {board[6]} │ {board[7]} │ {board[8]} │
└───┴───┴───
        """.replace(" ", "⬜").replace("X", "❌").replace("O", "⭕")
    
    @staticmethod
    def make_move(game_id: str, player_id: int, position: int) -> Tuple[bool, str]:
        games = db.xo_games
        
        for i, g in enumerate(games):
            if g["id"] == game_id:
                game = XOGame(**g)
                
                # التحقق من الدور
                if player_id != game.current_turn:
                    return False, "ليس دورك!"
                
                # التحقق من الموضع
                if position < 0 or position > 8 or game.board[position] != " ":
                    return False, "موضع غير صالح!"
                
                # تحديد الرمز
                symbol = "X" if player_id == game.player1_id else "O"
                game.board[position] = symbol
                game.moves.append(str(position))
                
                # التحقق من الفوز
                winner = XOGameEngine.check_winner(game.board)
                
                if winner:
                    game.winner_id = game.player1_id if winner == "X" else game.player2_id
                    game.status = "finished"
                    
                    # منح النقاط
                    winner_user = get_user(game.winner_id)
                    loser_id = game.player2_id if game.winner_id == game.player1_id else game.player1_id
                    loser_user = get_user(loser_id)
                    
                    points = config.PVP_BONUS
                    
                    update_user(game.winner_id, {
                        "points": winner_user.points + points,
                        "points_lifetime": winner_user.points_lifetime + points,
                        "games_won": winner_user.games_won + 1,
                        "xo_wins": winner_user.xo_wins + 1,
                        "pvp_wins": winner_user.pvp_wins + 1,
                        "current_streak": winner_user.current_streak + 1,
                        "best_streak": max(winner_user.best_streak, winner_user.current_streak + 1),
                        "experience": winner_user.experience + points,
                        "level": calculate_level(winner_user.experience + points)
                    })
                    
                    update_user(loser_id, {
                        "games_lost": loser_user.games_lost + 1,
                        "xo_losses": loser_user.xo_losses + 1,
                        "pvp_losses": loser_user.pvp_losses + 1,
                        "current_streak": 0
                    })
                    
                    msg = f"🎉 فاز اللاعب!

{XOGameEngine.get_board_display(game.board)}

+{points} نقطة للفائز!"
                
                elif len(game.moves) >= 9:
                    game.status = "draw"
                    msg = f"🤝 تعادل!

{XOGameEngine.get_board_display(game.board)}

+{config.POINTS_PER_GAME} نقطة لكل لاعب!"
                    
                    # نقاط التعادل
                    p1 = get_user(game.player1_id)
                    p2 = get_user(game.player2_id)
                    update_user(game.player1_id, {"points": p1.points + config.POINTS_PER_GAME, "pvp_draws": p1.pvp_draws + 1})
                    update_user(game.player2_id, {"points": p2.points + config.POINTS_PER_GAME, "pvp_draws": p2.pvp_draws + 1})
                
                else:
                    # تبديل الدور
                    game.current_turn = game.player2_id if game.current_turn == game.player1_id else game.player1_id
                    next_player = get_user(game.current_turn)
                    msg = f"🎮 دور: {next_player.first_name}

{XOGameEngine.get_board_display(game.board)}

اختر رقم الموضع (1-9)"
                
                games[i] = asdict(game)
                db.xo_games = games
                
                return True, msg
        
        return False, "اللعبة غير موجودة!"
    
    @staticmethod
    def check_winner(board: List[str]) -> Optional[str]:
        for pattern in XOGameEngine.WIN_PATTERNS:
            if board[pattern[0]] == board[pattern[1]] == board[pattern[2]] != " ":
                return board[pattern[0]]
        return None
    
    @staticmethod
    def get_active_game(user_id: int) -> Optional[XOGame]:
        games = db.xo_games
        for g in games:
            if (g["player1_id"] == user_id or g["player2_id"] == user_id) and g["status"] == "playing":
                return XOGame(**g)
        return None

# ==================== RPS GAME ====================
class RPSEngine:
    """محرك حجر ورقة مقص"""
    
    CHOICES = {
        "rock": {"emoji": "✊", "name": "حجر", "beats": "scissors"},
        "paper": {"emoji": "✋", "name": "ورقة", "beats": "rock"},
        "scissors": {"emoji": "✌️", "name": "مقص", "beats": "paper"}
    }
    
    @staticmethod
    def play(player1_choice: str, player2_choice: str) -> Tuple[int, str]:
        """تحديد الفائز: 1=player1, 2=player2, 0=تعادل"""
        if player1_choice == player2_choice:
            return 0, "تعادل!"
        
        if RPSEngine.CHOICES[player1_choice]["beats"] == player2_choice:
            return 1, f"{RPSEngine.CHOICES[player1_choice]['emoji']} يهزم {RPSEngine.CHOICES[player2_choice]['emoji']}"
        
        return 2, f"{RPSEngine.CHOICES[player2_choice]['emoji']} يهزم {RPSEngine.CHOICES[player1_choice]['emoji']}"

# ==================== GUESS NUMBER ====================
class GuessNumberEngine:
    """محرك تخمين الرقم"""
    
    @staticmethod
    def create_game(difficulty: str = "medium") -> Dict:
        if difficulty == "easy":
            max_num = 10
        elif difficulty == "hard":
            max_num = 100
        else:
            max_num = 50
        
        target = random.randint(1, max_num)
        return {
            "target": target,
            "max": max_num,
            "difficulty": difficulty,
            "attempts": 0,
            "max_attempts": {"easy": 5, "medium": 7, "hard": 10}.get(difficulty, 7)
        }
    
    @staticmethod
    def guess(guess: int, target: int, attempts: int, max_attempts: int) -> Tuple[bool, str, int]:
        attempts += 1
        
        if guess == target:
            return True, f"✅ صحيح! الرقم كان {target}", attempts
        
        if attempts >= max_attempts:
            return False, f"❌ انتهت المحاولات! الرقم كان {target}", attempts
        
        if guess < target:
            return None, f"⬆️ أكبر! (محاولة {attempts}/{max_attempts})", attempts
        else:
            return None, f"⬇️ أصغر! (محاولة {attempts}/{max_attempts})", attempts

# ==================== TOURNAMENT ====================
class TournamentEngine:
    """محرك البطولات"""
    
    @staticmethod
    def create(name: str, game_type: str, max_players: int, prize: int) -> Tournament:
        tournament = Tournament(
            id=generate_id("TOURNEY"),
            name=name,
            game_type=game_type,
            max_players=max_players,
            prize=prize
        )
        tournaments = db.tournaments
        tournaments.append(asdict(tournament))
        db.tournaments = tournaments
        return tournament
    
    @staticmethod
    def join(tournament_id: str, user_id: int) -> Tuple[bool, str]:
        tournaments = db.tournaments
        
        for t in tournaments:
            if t["id"] == tournament_id and t["status"] == "registration":
                if len(t["players"]) >= t["max_players"]:
                    return False, "البطولة ممتلئة!"
                
                user = get_user(user_id)
                if user.points < 50:
                    return False, "تحتاج 50 نقطة للتسجيل!"
                
                t["players"].append({"user_id": user_id, "name": user.first_name, "wins": 0})
                db.tournaments = tournaments
                
                return True, f"✅ انضممت للبطولة! ({len(t['players'])}/{t['max_players']})"
        
        return False, "البطولة غير موجودة!"
    
    @staticmethod
    def start(tournament_id: str) -> Tuple[bool, str]:
        tournaments = db.tournaments
        
        for t in tournaments:
            if t["id"] == tournament_id:
                if len(t["players"]) < 2:
                    return False, "تحتاج لاعبين على الأقل!"
                
                t["status"] = "started"
                db.tournaments = tournaments
                
                return True, f"🏆 بدأت锦标赛! {len(t['players'])} لاعبين"
        
        return False, "البطولة غير موجودة!"

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    keyboard = [
        [InlineKeyboardButton(f"🎮 المستوى {user.level} ({level_name}) | ⭐ {user.points}", callback_data="stats")],
        [InlineKeyboardButton("❌⭕ XO", callback_data="game_xo"), InlineKeyboardButton("✊✋✌ حجر ورقة مقص", callback_data="game_rps")],
        [InlineKeyboardButton("🔢 تخمين الرقم", callback_data="game_guess"), InlineKeyboardButton("🧠 ذاكرة", callback_data="game_memory")],
        [InlineKeyboardButton("⚔️ PvP", callback_data="pvp_menu"), InlineKeyboardButton("🏆 بطولات", callback_data="tournaments")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), InlineKeyboardButton("🏆 إنجازات", callback_data="achievements")],
    ]
    return InlineKeyboardMarkup(keyboard)

def xo_positions_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("1", callback_data="xo_0"), InlineKeyboardButton("2", callback_data="xo_1"), InlineKeyboardButton("3", callback_data="xo_2")],
        [InlineKeyboardButton("4", callback_data="xo_3"), InlineKeyboardButton("5", callback_data="xo_4"), InlineKeyboardButton("6", callback_data="xo_5")],
        [InlineKeyboardButton("7", callback_data="xo_6"), InlineKeyboardButton("8", callback_data="xo_7"), InlineKeyboardButton("9", callback_data="xo_8")],
    ]
    return InlineKeyboardMarkup(keyboard)

def rps_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("✊ حجر", callback_data="rps_rock"), InlineKeyboardButton("✋ ورقة", callback_data="rps_paper"), InlineKeyboardButton("✌️ مقص", callback_data="rps_scissors")],
    ]
    return InlineKeyboardMarkup(keyboard)

def pvp_menu_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("❌⭕ تحدي XO", callback_data="pvp_xo")],
        [InlineKeyboardButton("✊✋✌ حجر ورقة مقص", callback_data="pvp_rps")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

def play_again_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 لعب مرة أخرى", callback_data="play_again")
    ]])

# ==================== BOT HANDLERS ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    
    user_data = get_user(user_id)
    level_name, _ = get_level_info(user_data.level)
    
    welcome = f"""🎮 مرحباً {user.first_name}!

⚔️ ألعاب PvP:
• ❌⭕ XO ضد صديق
• ✊✋✌ حجر ورقة مقص

🎯 ألعاب منفردة:
• 🔢 تخمين الرقم
• 🧠 ذاكرة

🏆 بطولات

💰 النقاط:
• كل لعبة: {config.POINTS_PER_GAME}
• الفوز: +{config.WIN_BONUS}
• PvP: +{config.PVP_BONUS}

🎯 مستواك: {user_data.level} ({level_name})
⭐ نقاطك: {user_data.points}
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))
    logger.info(f"User {user_id} started")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    win_rate = (user.games_won / user.games_played * 100) if user.games_played > 0 else 0
    
    text = f"""📊 إحصائياتك
━━━━━━━━━━━━━━━━
🏆 المستوى: {user.level} ({level_name})
⭐ النقاط: {user.points}

🎮 إجمالي:
• لعبت: {user.games_played}
• فزت: {user.games_won}
• خسرت: {user.games_lost}

⚔️ PvP:
• انتصارات: {user.pvp_wins}
• هزائم: {user.pvp_losses}
• تعادلات: {user.pvp_draws}

❌⭕ XO:
• انتصارات: {user.xo_wins}
• هزائم: {user.xo_losses}

🔥 السلسلة: {user.current_streak}
🏆 الأفضل: {user.best_streak}
━━━━━━━━━━━━━━━━"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(user_id))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)
    
    # Navigation
    if data == "back":
        await stats_handler(update, context)
        return
    elif data == "stats":
        await stats_handler(update, context)
        return
    
    # XO Game
    elif data == "game_xo":
        active = XOGameEngine.get_active_game(user_id)
        if active:
            board = XOGameEngine.get_board_display(active.board)
            next_player = get_user(active.current_turn)
            await query.edit_message_text(
                f"❌⭕ لعبة XO\n\n"
                f"🎮 دور: {next_player.first_name}\n\n"
                f"{board}\n\n"
                f"اختر الموضع:",
                reply_markup=xo_positions_keyboard()
            )
        else:
            await query.edit_message_text(
                "❌⭕ لعبة XO\n\n"
                "لا توجد لعبة نشطة!\n\n"
                "أنشئ تحدي: `xo [كود_الخصم]`\n\n"
                "أو العب عشوائياً: `عشوائي xo`",
                reply_markup=back_keyboard()
            )
        return
    
    # XO Move
    elif data.startswith("xo_"):
        position = int(data.replace("xo_", ""))
        active = XOGameEngine.get_active_game(user_id)
        
        if active:
            success, msg = XOGameEngine.make_move(active.id, user_id, position)
            
            if "فاز" in msg or "تعادل" in msg:
                await query.edit_message_text(msg, reply_markup=main_menu_keyboard(user_id))
            else:
                await query.edit_message_text(msg, reply_markup=xo_positions_keyboard())
        return
    
    # RPS Game
    elif data == "game_rps":
        await query.edit_message_text(
            "✊✋✌ حجر ورقة مقص\n\n"
            "اختر:",
            reply_markup=rps_keyboard()
        )
        return
    
    # RPS Move
    elif data.startswith("rps_"):
        choice = data.replace("rps_", "")
        bot_choice = random.choice(["rock", "paper", "scissors"])
        
        winner, result = RPSEngine.play(choice, bot_choice)
        
        user_choice_emoji = RPSEngine.CHOICES[choice]["emoji"]
        bot_choice_emoji = RPSEngine.CHOICES[bot_choice]["emoji"]
        
        if winner == 1:
            points = config.WIN_BONUS
            msg = f"✅ فزت!\n\n{user_choice_emoji} vs {bot_choice_emoji}\n\n{result}\n\n+{points} نقطة!"
            update_user(user_id, {
                "points": user.points + points,
                "games_won": user.games_won + 1,
                "rps_wins": user.rps_wins + 1,
                "current_streak": user.current_streak + 1,
                "best_streak": max(user.best_streak, user.current_streak + 1)
            })
        elif winner == 2:
            points = config.POINTS_PER_GAME
            msg = f"❌ خسرت!\n\n{user_choice_emoji} vs {bot_choice_emoji}\n\n{result}\n\n+{points} نقطة"
            update_user(user_id, {"games_lost": user.games_lost + 1, "current_streak": 0})
        else:
            points = config.POINTS_PER_GAME
            msg = f"🤝 تعادل!\n\n{user_choice_emoji} vs {bot_choice_emoji}\n\n{result}\n\n+{points} نقطة"
            update_user(user_id, {"points": user.points + points})
        
        await query.edit_message_text(msg, reply_markup=play_again_keyboard())
        return
    
    # Guess Number
    elif data == "game_guess":
        game = GuessNumberEngine.create_game("medium")
        context.user_data['guess_game'] = game
        await query.edit_message_text(
            f"🔢 تخمين الرقم\n\n"
            f"تخمن رقم من 1-{game['max']}\n\n"
            f"لديك {game['max_attempts']} محاولات\n\n"
            f"أرسل رقماً:",
            reply_markup=back_keyboard()
        )
        return
    
    # PvP Menu
    elif data == "pvp_menu":
        await query.edit_message_text(
            "⚔️ PvP - العب ضد أصدقائك\n\n"
            "❌⭕ XO\n"
            "✊✋✌ حجر ورقة مقص\n\n"
            "الأوامر:\n"
            "• `xo REFCODE` - تحدي صديق\n"
            "• `rps REFCODE` - حجر ورقة مقص\n"
            "• `عشوائي xo` - ضد عشوائي",
            reply_markup=pvp_menu_keyboard()
        )
        return
    
    # Tournaments
    elif data == "tournaments":
        tournaments = db.tournaments
        text = "🏆 البطولات\n━━━━━━━━━━━━━━━━\n"
        
        active = [t for t in tournaments if t["status"] != "finished"]
        if not active:
            text += "لا توجد بطولات!\n\nأنشئ: `بطولة [الاسم] [اللعبة] [العدد]`"
        else:
            for t in active:
                text += f"📌 {t['name']}\n"
                text += f"   اللاعبون: {len(t['players'])}/{t['max_players']}\n"
                text += f"   الجائزة: {t['prize']}\n\n"
        
        await query.edit_message_text(text, reply_markup=back_keyboard())
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    # XO Challenge
    if text.startswith("xo "):
        code = text.replace("xo ", "").strip()
        users = db.users
        opponent_id = None
        for uid, udata in users.items():
            if udata.get("referral_code", "").upper() == code.upper():
                opponent_id = int(uid)
                break
        
        if opponent_id and opponent_id != user_id:
            game = XOGameEngine.create_game(user_id, opponent_id)
            opponent = get_user(opponent_id)
            await update.message.reply_text(
                f"✅ تم إنشاء تحدي XO!\n\n"
                f"أنت: ❌\n"
                f"{opponent.first_name}: ⭕\n\n"
                f"دورك أولاً!\n\n"
                f"اختر رقم 1-9:",
                reply_markup=xo_positions_keyboard()
            )
            try:
                await context.bot.send_message(
                    opponent_id,
                    f"⚔️ تحدي XO من {user.first_name}!\n\n"
                    f"أنت: ⭕\n"
                    f"{user.first_name}: ❌\n\n"
                    f"انتظر دورك..."
                )
            except:
                pass
        else:
            await update.message.reply_text("❌ المستخدم غير موجود!")
        return
    
    # RPS Challenge
    if text.startswith("rps "):
        choice = text.replace("rps ", "").strip()
        if choice in ["rock", "paper", "scissors", "حجر", "ورقة", "مقص"]:
            choice_map = {"حجر": "rock", "ورقة": "paper", "مقص": "scissors"}
            choice = choice_map.get(choice, choice)
            
            bot_choice = random.choice(["rock", "paper", "scissors"])
            winner, result = RPSEngine.play(choice, bot_choice)
            
            user_emoji = RPSEngine.CHOICES[choice]["emoji"]
            bot_emoji = RPSEngine.CHOICES[bot_choice]["emoji"]
            
            if winner == 1:
                points = config.WIN_BONUS
                msg = f"✅ فزت!\n{user_emoji} vs {bot_emoji}\n{result}\n+{points} نقطة!"
                update_user(user_id, {"points": user.points + points, "games_won": user.games_won + 1, "rps_wins": user.rps_wins + 1})
            elif winner == 2:
                msg = f"❌ خسرت!\n{user_emoji} vs {bot_emoji}\n{result}\n+{config.POINTS_PER_GAME} نقطة"
                update_user(user_id, {"games_lost": user.games_lost + 1})
            else:
                msg = f"🤝 تعادل!\n{user_emoji} vs {bot_emoji}\n+{config.POINTS_PER_GAME} نقطة"
                update_user(user_id, {"points": user.points + config.POINTS_PER_GAME})
            
            await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
        return
    
    # Guess Number
    if 'guess_game' in context.user_data:
        try:
            guess = int(text)
            game = context.user_data['guess_game']
            
            correct, msg, attempts = GuessNumberEngine.guess(guess, game['target'], game['attempts'], game['max_attempts'])
            game['attempts'] = attempts
            
            if correct:
                points = config.WIN_BONUS
                msg += f"\n+{points} نقطة!"
                update_user(user_id, {"points": user.points + points, "games_won": user.games_won + 1})
                del context.user_data['guess_game']
                await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
            elif correct is False:
                update_user(user_id, {"games_lost": user.games_lost + 1})
                del context.user_data['guess_game']
                await update.message.reply_text(msg, reply_markup=main_menu_keyboard(user_id))
            else:
                await update.message.reply_text(msg + "\n\nأرسل رقماً:", reply_markup=back_keyboard())
        except ValueError:
            await update.message.reply_text("أدخل رقماً صحيحاً!")
        return
    
    # Tournament
    if text.startswith("بطولة "):
        parts = text.replace("بطولة ", "").split()
        if len(parts) >= 3:
            name = parts[0]
            game_type = parts[1]
            max_players = int(parts[2])
            
            tourney = TournamentEngine.create(name, game_type, max_players, config.TOURNAMENT_PRIZE)
            await update.message.reply_text(
                f"✅ تم إنشاء锦标赛!\n\n"
                f"الاسم: {name}\n"
                f"اللعبة: {game_type}\n\n"
                f"انضم: `انضم {tourney.id}`"
            )
        return
    
    if text.startswith("انضم "):
        tourney_id = text.replace("انضم ", "").strip()
        success, msg = TournamentEngine.join(tourney_id, user_id)
        await update.message.reply_text(msg)
        return
    
    # Default
    await update.message.reply_text(
        "🎮 العب من القائمة!",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== MAIN ====================
def main() -> None:
    logger.info("🎮 Starting Ultimate Games Bot...")
    
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""الأوامر:
/start - بدء
/stats - إحصائيات

PvP:
xo [كود] - تحدي XO
rps [اختيار] - حجر ورقة مقص
عشوائي xo - ضد عشوائي

ألعاب:
تخمين [رقم] - تخمين الرقم

بطولات:
بطولة [اسم] [لعبة] [عدد]
انضم [كود]
"""))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(message_handler))
    
    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
