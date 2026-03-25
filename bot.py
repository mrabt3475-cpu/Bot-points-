"""
🤖 Crypto Wallet Bot - PvP Edition
ألعاب تنافسية مع AI حكم
"""

import os
import json
import hashlib
import random
import string
import asyncio
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
    # PvP Games
    PVP_MIN_BET: int = 20
    PVP_MAX_BET: int = 500
    TOURNAMENT_ENTRY_FEE: int = 100
    LEADERBOARD_SIZE: int = 10
    # AI
    AI_JUDGE_ENABLED: bool = True

config = Config()

# ==================== ENUMS ====================
class GameType(Enum):
    COIN_FLIP = "coin_flip"
    NUMBER_GUESS = "number_guess"
    ROCK_PAPER_SCISSORS = "rps"
    TIC_TAC_TOE = "tictactoe"
    MEMORY_GAME = "memory"
    QUIZ_BATTLE = "quiz_battle"
    SPEED_TYPING = "speed_typing"
    TRIVIA_BATTLE = "trivia_battle"

class MatchStatus(Enum):
    WAITING = "waiting"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"

class TournamentStatus(Enum):
    REGISTRATION = "registration"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

# ==================== DATA CLASSES ====================
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
    # PvP Stats
    pvp_wins: int = 0
    pvp_losses: int = 0
    pvp_draws: int = 0
    total_pvp_bets: int = 0
    biggest_win: int = 0
    current_streak: int = 0
    best_streak: int = 0
    # Tournaments
    tournaments_won: int = 0
    tournament_points: int = 0
    # Games
    games_played: int = 0
    games_won: int = 0
    # AI
    ai_chats: int = 0
    # Security
    is_banned: bool = False
    is_admin: bool = False
    pin_code: str = ""
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class PvPMatch:
    id: str
    game_type: str
    player1_id: int
    player2_id: int
    bet_amount: int
    status: str
    player1_move: str = ""
    player2_move: str = ""
    winner_id: int = None
    prize: int = 0
    ai_judge_comment: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    ended_at: str = ""

@dataclass
class Tournament:
    id: str
    name: str
    game_type: str
    entry_fee: int
    max_players: int
    status: str
    players: List[Dict] = field(default_factory=list)
    rounds: List[Dict] = field(default_factory=list)
    winner_id: int = None
    prize_pool: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Leaderboard:
    type: str  # daily, weekly, monthly, all_time
    game_type: str
    entries: List[Dict] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.users_file = "users.json"
        self.matches_file = "pvp_matches.json"
        self.tournaments_file = "tournaments.json"
        self.leaderboard_file = "leaderboard.json"
        self.challenges_file = "challenges.json"
    
    def load_users(self) -> Dict:
        try:
            with open(self.users_file, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def save_users(self, users: Dict):
        with open(self.users_file, "w") as f:
            json.dump(users, f, ensure_ascii=False, indent=2)
    
    def load_matches(self) -> List:
        try:
            with open(self.matches_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_matches(self, matches: List):
        with open(self.matches_file, "w") as f:
            json.dump(matches, f, ensure_ascii=False, indent=2)
    
    def load_tournaments(self) -> List:
        try:
            with open(self.tournaments_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_tournaments(self, tournaments: List):
        with open(self.tournaments_file, "w") as f:
            json.dump(tournaments, f, ensure_ascii=False, indent=2)
    
    def load_leaderboard(self) -> Dict:
        try:
            with open(self.leaderboard_file, "r") as f:
                return json.load(f)
        except:
            return {}
    
    def save_leaderboard(self, data: Dict):
        with open(self.leaderboard_file, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_challenges(self) -> List:
        try:
            with open(self.challenges_file, "r") as f:
                return json.load(f)
        except:
            return []
    
    def save_challenges(self, challenges: List):
        with open(self.challenges_file, "w") as f:
            json.dump(challenges, f, ensure_ascii=False, indent=2)

db = Database()

# ==================== HELPERS ====================
def generate_id(prefix: str, length: int = 10) -> str:
    return prefix + "-" + "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def get_user(user_id: int) -> User:
    users = db.load_users()
    if str(user_id) not in users:
        user = User(user_id=user_id, referral_code=generate_id("REF", 8))
        users[str(user_id)] = asdict(user)
        db.save_users(users)
        return user
    return User(**users[str(user_id)])

def update_user(user_id: int, data: Dict):
    users = db.load_users()
    if str(user_id) in users:
        users[str(user_id)].update(data)
        db.save_users(users)

# ==================== AI JUDGE ====================
class AIJudge:
    """AI حكم ذكي للمباريات"""
    
    def __init__(self):
        self.comments = {
            "fair_play": [
                "🤖 الحكم: لعبة عادلة! كلا اللاعبين لعبا بشكل ممتاز.",
                "🤖 الحكم: أداء مذهل من الطرفين!",
                "🤖 الحكم: هذه المباراة كانت مثيرة!",
            ],
            "close_match": [
                "🤖 الحكم: المباراة كانت متقاربة جداً!",
                "🤖 الحكم: الفارق كان ضئيلاً!",
                "🤖 الحكم: أي لاعب كان يمكن أن يفوز!",
            ],
            "domination": [
                "🤖 الحكم: أداء ساحق من الفائز!",
                "🤖 الحكم: السيطرة كانت كاملة!",
                "🤖 الحكم: لاعب واحد كان واضحاً الأفضل!",
            ],
            "comeback": [
                "🤖 الحكم:逆转 رائع!",
                "🤖 الحكم: لم يستسلم وحقق الفوز!",
                "🤖 الحكم: قلب الموازين في اللحظة الأخيرة!",
            ],
            "draw": [
                "🤖 الحكم: تعادل عادل!",
                "🤖 الحكم: كلا اللاعبين يستحقان التقدير!",
                "🤖 الحكم: مباراة مثيرة انتهت بالتعادل!",
            ],
            "dispute": [
                "🤖 الحكم: هناك لبس في النتيجة. سأفحص مرة أخرى.",
                "🤖 الحكم: يتطلب الأمر مراجعة.",
            ]
        }
    
    def judge_match(self, match: PvPMatch, player1: User, player2: User) -> str:
        """الحكم في المباراة"""
        
        if match.winner_id is None:
            return random.choice(self.comments["draw"])
        
        winner = player1 if match.winner_id == player1.user_id else player2
        loser = player2 if match.winner_id == player1.user_id else player1
        
        # تحليل سير المباراة
        score_diff = abs(winner.pvp_wins - loser.pvp_wins)
        
        if score_diff > 10:
            return random.choice(self.comments["domination"]) + f"\n🎉 تهانينا لـ {winner.first_name}!"
        elif score_diff <= 2:
            return random.choice(self.comments["close_match"]) + f"\n🎉 مبروك لـ {winner.first_name}!"
        else:
            return random.choice(self.comments["fair_play"]) + f"\n🎉 تهانينا لـ {winner.first_name}!"
    
    def analyze_player(self, user: User) -> str:
        """تحليل أداء اللاعب"""
        if user.pvp_wins + user.pvp_losses == 0:
            return f"⚡ {user.first_name} لاعب جديد يبحث عن التحديات!"
        
        win_rate = (user.pvp_wins / (user.pvp_wins + user.pvp_losses)) * 100
        
        if win_rate >= 80:
            return f"🔥 {user.first_name} أسطورة! نسبة الفوز {win_rate:.1f}%"
        elif win_rate >= 60:
            return f"⭐ {user.first_name} لاعب قوي! نسبة الفوز {win_rate:.1f}%"
        elif win_rate >= 40:
            return f"💪 {user.first_name} منافس شرس! نسبة الفوز {win_rate:.1f}%"
        else:
            return f"🎯 {user.first_name} يحتاج ممارسة أكثر"
    
    def get_match_prediction(self, player1: User, player2: User) -> str:
        """تنبؤ بنتيجة المباراة"""
        p1_rate = player1.pvp_wins / max(1, player1.pvp_wins + player1.pvp_losses)
        p2_rate = player2.pvp_wins / max(1, player2.pvp_wins + player2.pvp_losses)
        
        diff = abs(p1_rate - p2_rate)
        
        if diff > 0.3:
            leader = player1 if p1_rate > p2_rate else player2
            return f"🤖 التوقع: {leader.first_name} favorito"
        else:
            return "🤖 التوقع: المباراة متقاربة جداً!"
    
    def generate_cheer_message(self, user_id: int) -> str:
        """رسالة تشجيع"""
        messages = [
            "💪 You've got this!",
            "🔥 Fight!",
            "⭐ You can do it!",
            "🎯 Focus and win!",
            "🏆 Champion material!",
        ]
        return random.choice(messages)

ai_judge = AIJudge()

# ==================== PVP GAMES ====================
PVP_GAMES = {
    "coin_flip": {
        "name": "🪙 قلب العملة",
        "description": "اختر رأس أو كتابة",
        "moves": ["head", "tail"],
        "min_bet": 20,
        "max_bet": 500
    },
    "rps": {
        "name": "✊✋✌ حجر ورقة مقص",
        "description": "اختر حجر، ورقة، أو مقص",
        "moves": ["rock", "paper", "scissors"],
        "min_bet": 20,
        "max_bet": 500
    },
    "number_guess": {
        "name": "🔢 تخمين الرقم",
        "description": "من 1-10",
        "moves": [str(i) for i in range(1, 11)],
        "min_bet": 30,
        "max_bet": 300
    },
    "dice": {
        "name": "🎲 النرد",
        "description": "اختر رقم من 1-6",
        "moves": [str(i) for i in range(1, 7)],
        "min_bet": 20,
        "max_bet": 400
    }
}

def determine_winner(game_type: str, move1: str, move2: str) -> Optional[int]:
    """تحديد الفائز"""
    if game_type == "coin_flip":
        return 1 if move1 == move2 else 2
    
    elif game_type == "rps":
        wins = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
        if move1 == move2:
            return None  # تعادل
        if wins[move1] == move2:
            return 1
        return 2
    
    elif game_type == "number_guess":
        target = random.randint(1, 10)
        try:
            p1_guess = int(move1)
            p2_guess = int(move2)
            p1_diff = abs(target - p1_guess)
            p2_diff = abs(target - p2_guess)
            
            if p1_diff < p2_diff:
                return 1
            elif p2_diff < p1_diff:
                return 2
            else:
                return None
        except:
            return None
    
    elif game_type == "dice":
        target = random.randint(1, 6)
        try:
            p1_guess = int(move1)
            p2_guess = int(move2)
            p1_diff = abs(target - p1_guess)
            p2_diff = abs(target - p2_guess)
            
            if p1_diff < p2_diff:
                return 1
            elif p2_diff < p1_diff:
                return 2
            else:
                return None
        except:
            return None
    
    return None

def create_pvp_match(player1_id: int, player2_id: int, game_type: str, bet: int) -> PvPMatch:
    match = PvPMatch(
        id=generate_id("MATCH"),
        game_type=game_type,
        player1_id=player1_id,
        player2_id=player2_id,
        bet_amount=bet,
        status=MatchStatus.READY.value,
        prize=bet * 2
    )
    
    matches = db.load_matches()
    matches.append(asdict(match))
    db.save_matches(matches)
    
    return match

def play_pvp_match(match_id: str, player_id: int, move: str) -> Tuple[bool, str]:
    """اللعب في مباراة PvP"""
    matches = db.load_matches()
    
    for match_dict in matches:
        if match_dict["id"] == match_id:
            match = PvPMatch(**match_dict)
            
            # التحقق من اللاعب
            if player_id == match.player1_id:
                if match.player1_move:
                    return False, "لقد لعبت بالفعل!"
                match.player1_move = move
            elif player_id == match.player2_id:
                if match.player2_move:
                    return False, "لقد لعبت بالفعل!"
                match.player2_move = move
            else:
                return False, "لست جزءاً من هذه المباراة!"
            
            # التحقق من اكتمال اللعبتين
            if match.player1_move and match.player2_move:
                match.status = MatchStatus.IN_PROGRESS.value
                
                # تحديد الفائز
                winner = determine_winner(match.game_type, match.player1_move, match.player2_move)
                
                player1 = get_user(match.player1_id)
                player2 = get_user(match.player2_id)
                
                if winner is None:
                    # تعادل
                    match.winner_id = None
                    match.status = MatchStatus.COMPLETED.value
                    
                    # استرداد الرهان
                    update_user(match.player1_id, {"points": player1.points + match.bet_amount})
                    update_user(match.player2_id, {"points": player2.points + match.bet_amount})
                    
                    update_user(match.player1_id, {"pvp_draws": player1.pvp_draws + 1})
                    update_user(match.player2_id, {"pvp_draws": player2.pvp_draws + 1})
                    
                    match.ai_judge_comment = random.choice(ai_judge.comments["draw"])
                    
                else:
                    # تحديد الفائز
                    winner_id = match.player1_id if winner == 1 else match.player2_id
                    loser_id = match.player2_id if winner == 1 else match.player1_id
                    
                    match.winner_id = winner_id
                    match.status = MatchStatus.COMPLETED.value
                    
                    winner_user = get_user(winner_id)
                    loser_user = get_user(loser_id)
                    
                    # منح الجائزة
                    prize = match.bet_amount * 2
                    update_user(winner_id, {
                        "points": winner_user.points + prize,
                        "pvp_wins": winner_user.pvp_wins + 1,
                        "current_streak": winner_user.current_streak + 1,
                        "best_streak": max(winner_user.best_streak, winner_user.current_streak + 1),
                        "biggest_win": max(winner_user.biggest_win, prize)
                    })
                    
                    update_user(loser_id, {
                        "pvp_losses": loser_user.pvp_losses + 1,
                        "current_streak": 0
                    })
                    
                    # تعليق الحكم
                    match.ai_judge_comment = ai_judge.judge_match(match, player1, player2)
                
                match.ended_at = datetime.now().isoformat()
            else:
                match.status = MatchStatus.READY.value
            
            # حفظ
            for i, m in enumerate(matches):
                if m["id"] == match_id:
                    matches[i] = asdict(match)
                    break
            db.save_matches(matches)
            
            return True, "تم تسجيل حركتك! انتظر اللاعب الآخر."
    
    return False, "المباراة غير موجودة"

def get_active_matches(user_id: int) -> List[PvPMatch]:
    matches = db.load_matches()
    user_matches = []
    
    for m in matches:
        if (m["player1_id"] == user_id or m["player2_id"] == user_id) and m["status"] in ["ready", "in_progress"]:
            user_matches.append(PvPMatch(**m))
    
    return user_matches

# ==================== CHALLENGES ====================
def create_challenge(challenger_id: int, challenged_id: int, game_type: str, bet: int) -> bool:
    """إنشاء تحدي"""
    challenger = get_user(challenger_id)
    challenged = get_user(challenged_id)
    
    if challenger.points < bet:
        return False
    if challenged.points < bet:
        return False
    
    # خصم الرهان
    update_user(challenger_id, {"points": challenger.points - bet})
    
    challenge = {
        "id": generate_id("CHALLENGE"),
        "challenger_id": challenger_id,
        "challenged_id": challenged_id,
        "game_type": game_type,
        "bet_amount": bet,
        "status": "pending",
        "created_at": datetime.now().isoformat()
    }
    
    challenges = db.load_challenges()
    challenges.append(challenge)
    db.save_challenges(challenges)
    
    return True

def accept_challenge(challenge_id: str, user_id: int) -> Tuple[bool, str]:
    """قبول التحدي"""
    challenges = db.load_challenges()
    
    for ch in challenges:
        if ch["id"] == challenge_id and ch["challenged_id"] == user_id and ch["status"] == "pending":
            challenged = get_user(user_id)
            
            # خصم الرهان
            update_user(user_id, {"points": challenged.points - ch["bet_amount"]})
            
            # إنشاء المباراة
            create_pvp_match(ch["challenger_id"], user_id, ch["game_type"], ch["bet_amount"])
            
            ch["status"] = "accepted"
            db.save_challenges(challenges)
            
            return True, "✅ تم قبول التحدي! ابدأ اللعب."
    
    return False, "التحدي غير موجود أو منتهي"

# ==================== TOURNAMENTS ====================
def create_tournament(name: str, game_type: str, max_players: int, entry_fee: int) -> Tournament:
    tournament = Tournament(
        id=generate_id("TOURNAMENT"),
        name=name,
        game_type=game_type,
        entry_fee=entry_fee,
        max_players=max_players,
        status=TournamentStatus.REGISTRATION.value
    )
    
    tournaments = db.load_tournaments()
    tournaments.append(asdict(tournament))
    db.save_tournaments(tournaments)
    
    return tournament

def join_tournament(tournament_id: str, user_id: int) -> Tuple[bool, str]:
    """الانضمام لبطولة"""
    tournaments = db.load_tournaments()
    user = get_user(user_id)
    
    for t in tournaments:
        if t["id"] == tournament_id:
            if t["status"] != TournamentStatus.REGISTRATION.value:
                return False, "البطولة بدأت بالفعل!"
            
            if len(t["players"]) >= t["max_players"]:
                return False, "البطولة ممتلئة!"
            
            if user.points < t["entry_fee"]:
                return False, "نقاطك غير كافية!"
            
            # خصم رسوم الدخول
            update_user(user_id, {"points": user.points - t["entry_fee"]})
            
            t["players"].append({
                "user_id": user_id,
                "name": user.first_name,
                "wins": 0,
                "losses": 0
            })
            t["prize_pool"] += t["entry_fee"]
            
            db.save_tournaments(tournaments)
            return True, f"✅ انضممت للبطولة! رسوم الدخول: {t['entry_fee']} نقطة"
    
    return False, "البطولة غير موجودة"

# ==================== LEADERBOARD ====================
def update_leaderboard(game_type: str = "all"):
    """تحديث لوحة المتصدرين"""
    users = db.load_users()
    
    # ترتيب حسب النقاط
    sorted_users = sorted(
        [User(**u) for u in users.values()],
        key=lambda x: x.points,
        reverse=True
    )[:config.LEADERBOARD_SIZE]
    
    leaderboard = {
        "type": "all_time",
        "game_type": game_type,
        "entries": [
            {
                "rank": i + 1,
                "user_id": u.user_id,
                "name": u.first_name,
                "points": u.points,
                "wins": u.pvp_wins,
                "win_rate": round((u.pvp_wins / max(1, u.pvp_wins + u.pvp_losses)) * 100, 1)
            }
            for i, u in enumerate(sorted_users)
        ],
        "updated_at": datetime.now().isoformat()
    }
    
    db.save_leaderboard(leaderboard)
    return leaderboard

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int):
    user = get_user(user_id)
    keyboard = [
        [InlineKeyboardButton(f"💰 الرصيد: ⭐ {user.points}", callback_data="balance")],
        [InlineKeyboardButton("⚔️ مبارزة", callback_data="pvp_menu")],
        [InlineKeyboardButton("🏆 بطولات", callback_data="tournaments")],
        [InlineKeyboardButton("📊 المتصدرين", callback_data="leaderboard")],
        [InlineKeyboardButton("🎮 ألعاب منفردة", callback_data="single_games")],
        [InlineKeyboardButton("🤖 AI الحكم", callback_data="ai_judge")],
    ]
    return InlineKeyboardMarkup(keyboard)

def pvp_games_keyboard():
    keyboard = []
    for game_key, game_info in PVP_GAMES.items():
        keyboard.append([InlineKeyboardButton(f"{game_info['name']} ({game_info['min_bet']}-{game_info['max_bet']}ن)", callback_data=f"pvp_{game_key}")])
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back")])
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

# ==================== BOT COMMANDS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    
    user_data = get_user(user_id)
    
    welcome = f"""⚔️ مرحباً {user.first_name}!

🎮 نظام الألعاب التنافسية:
• 🪙 قلب العملة
• ✊✋✌ حجر ورقة مقص
• 🔢 تخمين الرقم
• 🎲 النرد

🏆 البطولات متاحة!
📊 لوحة المتصدرين
🤖 AI حكم ذكي

نقاطك: ⭐ {user_data.points}
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))

async def pvp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    text = """⚔️ الألعاب التنافسية
━━━━━━━━━━━━━━━━
اختر لعبة للعب ضد خصم:
"""
    await update.message.reply_text(text, reply_markup=pvp_games_keyboard())

async def challenge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء تحدي"""
    user_id = update.message.from_user.id
    
    text = """⚔️ إنشاء تحدي
━━━━━━━━━━━━━━━━
الصيغة:
`تحدي [كود_الخصم] [اللعبة] [الرهان]`

مثال:
`تحدي REF-ABC123 coin_flip 50`

الألعاب المتاحة:
• coin_flip
• rps
• number_guess
• dice
"""
    await update.message.reply_text(text, reply_markup=back_keyboard())

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض لوحة المتصدرين"""
    leaderboard = update_leaderboard()
    
    text = "📊 لوحة المتصدرين\n━━━━━━━━━━━━━━━━\n"
    
    for entry in leaderboard["entries"]:
        medal = "🥇" if entry["rank"] == 1 else "🥈" if entry["rank"] == 2 else "🥉" if entry["rank"] == 3 else f"{entry['rank']}."
        text += f"{medal} {entry['name']}\n"
        text += f"   ⭐ {entry['points']} نقطة | 🎮 {entry['wins']} فوز | {entry['win_rate']}%\n\n"
    
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(update.message.from_user.id))

async def tournament_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض البطولات"""
    tournaments = db.load_tournaments()
    
    text = "🏆 البطولات\n━━━━━━━━━━━━━━━━\n"
    
    active_tournaments = [t for t in tournaments if t["status"] != "completed"]
    
    if not active_tournaments:
        text += "لا توجد بطولات حالياً!\n\nأنشئ واحدة: `بطولة [الاسم] [اللعبة] [الحد] [الرسوم]`"
    else:
        for t in active_tournaments:
            text += f"📌 {t['name']}\n"
            text += f"   اللعبة: {t['game_type']}\n"
            text += f"   اللاعبون: {len(t['players'])}/{t['max_players']}\n"
            text += f"   الجائزة: {t['prize_pool']} نقطة\n"
            text += f"   الحالة: {t['status']}\n\n"
    
    await update.message.reply_text(text, reply_markup=main_menu_keyboard(update.message.from_user.id))

# ==================== CALLBACK HANDLERS ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "back":
        await start_command(update, context)
    elif data == "pvp_menu":
        await pvp_command(update, context)
    elif data == "leaderboard":
        await leaderboard_command(update, context)
    elif data == "tournaments":
        await tournament_command(update, context)
    elif data.startswith("pvp_"):
        game_type = data.replace("pvp_", "")
        if game_type in PVP_GAMES:
            game = PVP_GAMES[game_type]
            await query.edit_message_text(
                f"⚔️ {game['name']}\n"
                f"{game['description']}\n\n"
                f"الرهان: {game['min_bet']}-{game['max_bet']} نقطة\n\n"
                f"أنشئ تحدي:
`تحدي [كود_الخصم] {game_type} [الرهان]`\n\n"
                f"أو العب عشوائياً:
`عشوائي {game_type} [الرهان]`",
                reply_markup=back_keyboard()
            )
    elif data == "ai_judge":
        user = get_user(user_id)
        analysis = ai_judge.analyze_player(user)
        await query.edit_message_text(
            f"🤖 AI الحكم\n━━━━━━━━━━━━━━━━\n\n"
            f"{analysis}\n\n"
            f"إحصائياتك:\n"
            f"• الفوز: {user.pvp_wins}\n"
            f"• الخسارة: {user.pvp_losses}\n"
            f"• التعادل: {user.pvp_draws}\n"
            f"• أفضل سلسلة: {user.best_streak}\n"
            f"• أكبر فوز: {user.biggest_win}",
            reply_markup=back_keyboard()
        )

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    # تحدي
    if text.startswith("تحدي "):
        try:
            parts = text.replace("تحدي ", "").split()
            if len(parts) >= 3:
                code = parts[0]
                game_type = parts[1]
                bet = int(parts[2])
                
                # البحث عن المستخدم
                users = db.load_users()
                challenged_id = None
                for uid, udata in users.items():
                    if udata.get("referral_code") == code:
                        challenged_id = int(uid)
                        break
                
                if not challenged_id:
                    await update.message.reply_text("❌ المستخدم غير موجود!")
                    return
                
                if challenged_id == user_id:
                    await update.message.reply_text("❌ لا يمكنك تحدي نفسك!")
                    return
                
                success = create_challenge(user_id, challenged_id, game_type, bet)
                if success:
                    await update.message.reply_text(
                        f"✅ تم إنشاء التحدي!\n\n"
                        f"🎮 اللعبة: {game_type}\n"
                        f"💰 الرهان: {bet} نقطة\n\n"
                        f"أرسل للكود: {code}\n"
                        f"ليقبل التحدي: `قبول [كود_التحدي]`"
                    )
                else:
                    await update.message.reply_text("❌ نقاطك غير كافية!")
        except:
            await update.message.reply_text("❌ خطأ! الصيغة: `تحدي REF-XXX coin_flip 50`")
        return
    
    # قبول التحدي
    if text.startswith("قبول "):
        try:
            challenge_id = text.replace("قبول ", "").strip()
            success, msg = accept_challenge(challenge_id, user_id)
            await update.message.reply_text(msg)
        except:
            await update.message.reply_text("❌ خطأ!")
        return
    
    # اللعب
    if text.startswith("لعب "):
        try:
            parts = text.replace("لعب ", "").split()
            if len(parts) >= 2:
                game_type = parts[0]
                move = parts[1]
                
                # البحث عن مباراة نشطة
                active = get_active_matches(user_id)
                if active:
                    match = active[0]
                    success, msg = play_pvp_match(match.id, user_id, move)
                    await update.message.reply_text(msg)
                    
                    if match.status == "completed":
                        player1 = get_user(match.player1_id)
                        player2 = get_user(match.player2_id)
                        
                        result_text = f"⚔️ النتيجة:\n"
                        result_text += f"{player1.first_name}: {match.player1_move}\n"
                        result_text += f"{player2.first_name}: {match.player2_move}\n\n"
                        result_text += match.ai_judge_comment
                        
                        await update.message.reply_text(result_text)
                else:
                    await update.message.reply_text("❌ لا توجد مباريات نشطة!")
        except:
            await update.message.reply_text("❌ خطأ! الصيغة: `لعب coin_flip head`")
        return
    
    # عشوائي
    if text.startswith("عشوائي "):
        try:
            parts = text.replace("عشوائي ", "").split()
            game_type = parts[0]
            bet = int(parts[1]) if len(parts) > 1 else 50
            
            await update.message.reply_text(
                f"🔍 جاري البحث عن خصم...\n\n"
                f"اللعبة: {game_type}\n"
                f"الرهان: {bet} نقطة\n\n"
                "(هذه الميزة تحتاج تطوير إضافي)"
            )
        except:
            await update.message.reply_text("❌ خطأ! الصيغة: `عشوائي coin_flip 50`")
        return
    
    # بطاقة
    if text.startswith("بطولة "):
        try:
            parts = text.replace("بطولة ", "").split()
            if len(parts) >= 4:
                name = parts[0]
                game_type = parts[1]
                max_players = int(parts[2])
                entry_fee = int(parts[3])
                
                tournament = create_tournament(name, game_type, max_players, entry_fee)
                await update.message.reply_text(
                    f"✅ تم إنشاء锦标赛!\n\n"
                    f"الاسم: {name}\n"
                    f"اللعبة: {game_type}\n"
                    f"الحد: {max_players}\n"
                    f"الرسوم: {entry_fee}\n\n"
                    f"انضم: `انضم {tournament.id}`"
                )
        except:
            await update.message.reply_text("❌ خطأ!")
        return
    
    # انضم
    if text.startswith("انضم "):
        try:
            tournament_id = text.replace("انضم ", "").strip()
            success, msg = join_tournament(tournament_id, user_id)
            await update.message.reply_text(msg)
        except:
            await update.message.reply_text("❌ خطأ!")
        return
    
    await update.message.reply_text("❌ أمر غير معروف!\n\n/start", reply_markup=main_menu_keyboard(user_id))

# ==================== MAIN ====================
def main():
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("pvp", pvp_command))
    app.add_handler(CommandHandler("تحدي", challenge_command))
    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(CommandHandler("lb", leaderboard_command))
    app.add_handler(CommandHandler("tournament", tournament_command))
    app.add_handler(CommandHandler("بطولة", lambda u, c: u.message.reply_text("استخدم: `بطولة [الاسم] [اللعبة] [الحد] [الرسوم]`")))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(handle_message))
    
    print("⚔️ PvP Games Bot is running...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
