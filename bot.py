"""
🃏 Ultimate Card Games Bot - بلوت وورق
ألعاب البلوت والورق والكازينو

🎯 الميزات:
- بلوت (Balot)
- ورق (Blackjack)
- بوكر (Poker) - مبسط
- سلوت (Slot)
- النرد
"""

from __future__ import annotations
import os
import json
import random
import string
import time
from datetime import datetime
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
    POINTS_PER_GAME: int = 20
    WIN_BONUS: int = 30
    BLACKJACK_BONUS: int = 50
    SLOT_COST: int = 10
    DB_PATH: str = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("CardGamesBot")

# ==================== ENUMS ====================
class GameType(str, Enum):
    BALOT = "balot"
    BLACKJACK = "blackjack"
    POKER = "poker"
    SLOT = "slot"
    DICE = "dice"

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
    # Card games
    balot_wins: int = 0
    balot_losses: int = 0
    blackjack_wins: int = 0
    blackjack_losses: int = 0
    poker_wins: int = 0
    slots_played: int = 0
    slots_won: int = 0
    dice_played: int = 0
    dice_won: int = 0
    join_date: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class Card:
    suit: str  # ♠️ ♥️ ♦️ ♣️
    rank: str  # A,2-10,J,Q,K
    value: int

@dataclass
class BlackjackGame:
    id: str
    user_id: int
    player_cards: List[Dict]
    dealer_cards: List[Dict]
    player_score: int
    dealer_score: int
    status: str  # playing, won, lost, push
    bet: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

@dataclass
class BalotGame:
    id: str
    player1_id: int
    player2_id: int
    player1_cards: List[Dict]
    player2_cards: List[Dict]
    player1_score: int
    player2_score: int
    current_turn: int
    deck: List[Dict]
    status: str
    round: int
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

# ==================== DATABASE ====================
class Database:
    def __init__(self, db_path: str = config.DB_PATH):
        self.db_path = db_path
        os.makedirs(db_path, exist_ok=True)
        self.users_file = f"{db_path}/users.json"
        self.blackjack_file = f"{db_path}/blackjack.json"
        self.balot_file = f"{db_path}/balot.json"
        self._init_files()
    
    def _init_files(self):
        for f in [self.users_file, self.blackjack_file, self.balot_file]:
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
    def blackjack_games(self) -> List:
        return self._load_json(self.blackjack_file)
    
    @blackjack_games.setter
    def blackjack_games(self, data: List):
        self._save_json(self.blackjack_file, data)
    
    @property
    def balot_games(self) -> List:
        return self._load_json(self.balot_file)
    
    @balot_games.setter
    def balot_games(self, data: List):
        self._save_json(self.balot_file, data)

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

# ==================== CARD DECK ====================
class Deck:
    """مجموعة أوراق"""
    
    SUITS = ["♠️", "♥️", "♦️", "♣️"]
    RANKS = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    
    @staticmethod
    def create_shuffled() -> List[Dict]:
        deck = []
        for suit in Deck.SUITS:
            for rank in Deck.RANKS:
                value = 11 if rank == "A" else 10 if rank in ["J", "Q", "K"] else int(rank)
                deck.append({"suit": suit, "rank": rank, "value": value})
        random.shuffle(deck)
        return deck
    
    @staticmethod
    def draw(deck: List[Dict], count: int = 1) -> Tuple[List[Dict], List[Dict]]:
        cards = deck[:count]
        remaining = deck[count:]
        return cards, remaining

# ==================== BLACKJACK ====================
class BlackjackEngine:
    """محرك لعبة ورق (Blackjack)"""
    
    @staticmethod
    def start(user_id: int, bet: int) -> BlackjackGame:
        user = get_user(user_id)
        if user.points < bet:
            return None
        
        # خصم الرهان
        update_user(user_id, {"points": user.points - bet})
        
        deck = Deck.create_shuffled()
        player_cards, deck = Deck.draw(deck, 2)
        dealer_cards, deck = Deck.draw(deck, 2)
        
        player_score = BlackjackEngine.calculate_score(player_cards)
        dealer_score = BlackjackEngine.calculate_score(dealer_cards)
        
        game = BlackjackGame(
            id=generate_id("BJ"),
            user_id=user_id,
            player_cards=player_cards,
            dealer_cards=dealer_cards,
            player_score=player_score,
            dealer_score=dealer_score,
            status="playing",
            bet=bet
        )
        
        games = db.blackjack_games
        games.append(asdict(game))
        db.blackjack_games = games
        
        return game
    
    @staticmethod
    def calculate_score(cards: List[Dict]) -> int:
        score = sum(c["value"] for c in cards)
        aces = sum(1 for c in cards if c["rank"] == "A")
        
        while score > 21 and aces > 0:
            score -= 10
            aces -= 1
        
        return score
    
    @staticmethod
    def get_display(cards: List[Dict], hide_first: bool = False) -> str:
        if hide_first and len(cards) > 0:
            return "🃏 " + " ".join([f"{c['suit']}{c['rank']}" for c in cards[1:]])
        return " ".join([f"{c['suit']}{c['rank']}" for c in cards])
    
    @staticmethod
    def hit(game_id: str, user_id: int) -> Tuple[bool, str]:
        games = db.blackjack_games
        
        for i, g in enumerate(games):
            if g["id"] == game_id and g["user_id"] == user_id and g["status"] == "playing":
                game = BlackjackGame(**g)
                
                # إضافة ورقة
                deck = Deck.create_shuffled()
                new_card, _ = Deck.draw(deck, 1)
                game.player_cards.extend(new_card)
                game.player_score = BlackjackEngine.calculate_score(game.player_cards)
                
                if game.player_score > 21:
                    # خسر
                    game.status = "lost"
                    update_user(user_id, {"games_lost": get_user(user_id).games_lost + 1})
                    msg = f"❌ خسرت!\n\n"
                    msg += f"🎮 يدك: {BlackjackEngine.get_display(game.player_cards)}\n"
                    msg += f"   النقاط: {game.player_score}\n\n"
                    msg += f"🃏 الديلر: {BlackjackEngine.get_display(game.dealer_cards, True)}\n"
                    msg += f"   النقاط: {game.dealer_score}\n\n"
                    msg += f"تجاوزت 21! +{config.POINTS_PER_GAME} نقطة"
                else:
                    msg = f"🎮 يدك: {BlackjackEngine.get_display(game.player_cards)}\n"
                    msg += f"   النقاط: {game.player_score}\n\n"
                    msg += f"اختر:\n"
                    msg += f"• hit - سحب ورقة أخرى\n"
                    msg += f"• stand - توقف"
                
                games[i] = asdict(game)
                db.blackjack_games = games
                return True, msg
        
        return False, "اللعبة غير موجودة!"
    
    @staticmethod
    def stand(game_id: str, user_id: int) -> Tuple[bool, str]:
        games = db.blackjack_games
        
        for i, g in enumerate(games):
            if g["id"] == game_id and g["user_id"] == user_id and g["status"] == "playing":
                game = BlackjackGame(**g)
                
                # الديلر يسحب
                deck = Deck.create_shuffled()
                while game.dealer_score < 17:
                    new_card, _ = Deck.draw(deck, 1)
                    game.dealer_cards.extend(new_card)
                    game.dealer_score = BlackjackEngine.calculate_score(game.dealer_cards)
                
                # تحديد الفائز
                if game.dealer_score > 21 or game.player_score > game.dealer_score:
                    game.status = "won"
                    points = game.bet * 2 + config.BLACKJACK_BONUS
                    user = get_user(user_id)
                    update_user(user_id, {
                        "points": user.points + points,
                        "games_won": user.games_won + 1,
                        "blackjack_wins": user.blackjack_wins + 1
                    })
                    msg = f"🎉 فزت!\n\n"
                    msg += f"🎮 يدك: {BlackjackEngine.get_display(game.player_cards)} = {game.player_score}\n\n"
                    msg += f"🃏 الديلر: {BlackjackEngine.get_display(game.dealer_cards)} = {game.dealer_score}\n\n"
                    msg += f"+{points} نقطة!"
                
                elif game.player_score == game.dealer_score:
                    game.status = "push"
                    points = game.bet
                    user = get_user(user_id)
                    update_user(user_id, {"points": user.points + points})
                    msg = f"🤝 تعادل!\n\n"
                    msg += f"🎮 يدك: {game.player_score}\n"
                    msg += f"🃏 الديلر: {game.dealer_score}\n\n"
                    msg += f"استرداد رهانك: {points}"
                
                else:
                    game.status = "lost"
                    update_user(user_id, {"games_lost": get_user(user_id).games_lost + 1})
                    msg = f"❌ خسرت!\n\n"
                    msg += f"🎮 يدك: {game.player_score}\n"
                    msg += f"🃏 الديلر: {game.dealer_score}\n\n"
                    msg += f"+{config.POINTS_PER_GAME} نقطة"
                
                games[i] = asdict(game)
                db.blackjack_games = games
                return True, msg
        
        return False, "اللعبة غير موجودة!"

# ==================== SLOT MACHINE ====================
class SlotEngine:
    """محرك السلوت"""
    
    SYMBOLS = ["🍒", "🍋", "🍇", "💎", "🔔", "7️⃣"]
    PAYOUTS = {
        ("7️⃣", "7️⃣", "7️⃣"): 100,
        ("💎", "💎", "💎"): 50,
        ("🔔", "🔔", "🔔"): 25,
        ("🍇", "🍇", "🍇"): 15,
        ("🍒", "🍒", "🍒"): 10,
        ("🍋", "🍋", "🍋"): 5,
    }
    
    @staticmethod
    def spin(user_id: int) -> Tuple[bool, str, int]:
        user = get_user(user_id)
        cost = config.SLOT_COST
        
        if user.points < cost:
            return False, "نقاطك غير كافية! تحتاج 10 نقاط", 0
        
        update_user(user_id, {"points": user.points - cost, "slots_played": user.slots_played + 1})
        
        # تدوير
        result = [random.choice(SlotEngine.SYMBOLS) for _ in range(3)]
        
        # فحص الفوز
        win = False
        multiplier = 0
        
        for pattern, mult in SlotEngine.PAYOUTS.items():
            if result[0] == pattern[0] and result[1] == pattern[1] and result[2] == pattern[2]:
                win = True
                multiplier = mult
                break
        
        # حتى رمزين متطابقين
        if not win:
            if result[0] == result[1] or result[1] == result[2] or result[0] == result[2]:
                win = True
                multiplier = 2
        
        if win:
            points = cost * multiplier
            update_user(user_id, {
                "points": get_user(user_id).points + points,
                "slots_won": get_user(user_id).slots_won + 1
            })
            msg = f"🎰 {result[0]} {result[1]} {result[2]}\n\n"
            msg += f"🎉 مبروك! +{points} نقطة!"
            return True, msg, points
        else:
            msg = f"🎰 {result[0]} {result[1]} {result[2]}\n\n"
            msg += f"❌ لم تربح! +{config.POINTS_PER_GAME} نقطة"
            return True, msg, config.POINTS_PER_GAME

# ==================== DICE ====================
class DiceEngine:
    """محرك النرد"""
    
    @staticmethod
    def roll(user_id: int, prediction: str, bet: int) -> Tuple[bool, str, int]:
        user = get_user(user_id)
        
        if user.points < bet:
            return False, "نقاطك غير كافية!", 0
        
        update_user(user_id, {"points": user.points - bet, "dice_played": user.dice_played + 1})
        
        dice1 = random.randint(1, 6)
        dice2 = random.randint(1, 6)
        total = dice1 + dice2
        
        won = False
        
        if prediction == "high" and total >= 7:
            won = True
        elif prediction == "low" and total <= 6:
            won = True
        elif prediction.isdigit() and int(prediction) == total:
            won = True
        elif prediction == "even" and total % 2 == 0:
            won = True
        elif prediction == "odd" and total % 2 == 1:
            won = True
        
        if won:
            points = bet * 2
            update_user(user_id, {
                "points": get_user(user_id).points + points,
                "dice_won": get_user(user_id).dice_won + 1
            })
            msg = f"🎲 النرد: {dice1} + {dice2} = {total}\n\n"
            msg += f"🎉 فزت! +{points} نقطة!"
            return True, msg, points
        else:
            msg = f"🎲 النرد: {dice1} + {dice2} = {total}\n\n"
            msg += f"❌ خسرت! +{config.POINTS_PER_GAME} نقطة"
            return True, msg, config.POINTS_PER_GAME

# ==================== KEYBOARDS ====================
def main_menu_keyboard(user_id: int) -> InlineKeyboardMarkup:
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    keyboard = [
        [InlineKeyboardButton(f"🎮 المستوى {user.level} ({level_name}) | ⭐ {user.points}", callback_data="stats")],
        [InlineKeyboardButton("🃏 ورق (Blackjack)", callback_data="game_blackjack"), InlineKeyboardButton("🎰 سلوت", callback_data="game_slot")],
        [InlineKeyboardButton("🎲 نرد", callback_data="game_dice"), InlineKeyboardButton("🃏 بلوت", callback_data="game_balot")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats"), InlineKeyboardButton("🏆 إنجازات", callback_data="achievements")],
    ]
    return InlineKeyboardMarkup(keyboard)

def blackjack_keyboard(game_id: str) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🃏 hit - سحب", callback_data=f"bj_hit_{game_id}")],
        [InlineKeyboardButton("✋ stand - توقف", callback_data=f"bj_stand_{game_id}")],
    ]
    return InlineKeyboardMarkup(keyboard)

def dice_keyboard() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("⬆️ كبير (7-12)", callback_data="dice_high"), InlineKeyboardButton("⬇️ صغير (2-6)", callback_data="dice_low")],
        [InlineKeyboardButton("👫 زوجي", callback_data="dice_even"), InlineKeyboardButton("🔢 فردي", callback_data="dice_odd")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="back")]])

def play_again_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔄 لعب مرة أخرى", callback_data="play_again")]])

# ==================== BOT HANDLERS ====================
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    user_id = user.id
    
    user_data = get_user(user_id)
    level_name, _ = get_level_info(user_data.level)
    
    welcome = f"""🃏 مرحباً {user.first_name}!

🎰 ألعاب الكازينو:

🃏 ورق (Blackjack)
• اقترب من 21 دون تجاوز
• الرهان: 10-100 نقطة

🎰 سلوت
• 3 رموز متطابقة للفوز
• التكلفة: 10 نقاط

🎲 النرد
• تخمن مجموع النردين
• رهان: 10-50 نقطة

🃏 بلوت
• ضد البوت
• نظام مبسط

💰 النقاط:
• كل لعبة: {config.POINTS_PER_GAME}
• الفوز: +{config.WIN_BONUS}

🎯 مستواك: {user_data.level} ({level_name})
⭐ نقاطك: {user_data.points}
"""
    await update.message.reply_text(welcome, reply_markup=main_menu_keyboard(user_id))
    logger.info(f"User {user_id} started card games bot")

async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    user = get_user(user_id)
    level_name, _ = get_level_info(user.level)
    
    text = f"""📊 إحصائياتك
━━━━━━━━━━━━━━━━
🏆 المستوى: {user.level} ({level_name})
⭐ النقاط: {user.points}

🃏 ورق:
• انتصارات: {user.blackjack_wins}
• هزائم: {user.blackjack_losses}

🎰 سلوت:
• لعبت: {user.slots_played}
• فزت: {user.slots_won}

🎲 النرد:
• لعبت: {user.dice_played}
• فزت: {user.dice_won}

🃏 بلوت:
• انتصارات: {user.balot_wins}
• هزائم: {user.balot_losses}

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
    elif data == "play_again":
        await stats_handler(update, context)
        return
    
    # Blackjack
    elif data == "game_blackjack":
        await query.edit_message_text(
            "🃏 ورق (Blackjack)\n\n"
            "هدف اللعبة: اقترب من 21 دون تجاوز!\n\n"
            "أرسل رهانك:\n"
            "`ورق 20`\n\n"
            "(10-100 نقطة)",
            reply_markup=back_keyboard()
        )
        return
    
    elif data.startswith("bj_"):
        parts = data.split("_")
        action = parts[1]
        game_id = parts[2] if len(parts) > 2 else None
        
        if action == "hit" and game_id:
            success, msg = BlackjackEngine.hit(game_id, user_id)
            if "خسرت" in msg or "فزت" in msg or "تعادل" in msg:
                await query.edit_message_text(msg, reply_markup=play_again_keyboard())
            else:
                await query.edit_message_text(msg, reply_markup=blackjack_keyboard(game_id))
        elif action == "stand" and game_id:
            success, msg = BlackjackEngine.stand(game_id, user_id)
            await query.edit_message_text(msg, reply_markup=play_again_keyboard())
        return
    
    # Slot
    elif data == "game_slot":
        won, msg, points = SlotEngine.spin(user_id)
        await query.edit_message_text(msg, reply_markup=play_again_keyboard())
        return
    
    # Dice
    elif data == "game_dice":
        await query.edit_message_text(
            "🎲 النرد\n\n"
            "اختر تخمينك:\n\n"
            "⬆️ كبير: مجموع 7-12\n"
            "⬇️ صغير: مجموع 2-6\n"
            "👫 زوجي: مجموع زوجي\n"
            "🔢 فردي: مجموع فردي\n\n"
            "أرسل: `نرد 20 كبير`",
            reply_markup=dice_keyboard()
        )
        return
    
    elif data.startswith("dice_"):
        prediction = data.replace("dice_", "")
        if prediction == "high":
            prediction = "high"
        elif prediction == "low":
            prediction = "low"
        
        won, msg, points = DiceEngine.roll(user_id, prediction, 20)
        await query.edit_message_text(msg, reply_markup=play_again_keyboard())
        return
    
    # Balot
    elif data == "game_balot":
        await query.edit_message_text(
            "🃏 بلوت\n\n"
            "قريباً...\n\n"
            "هذه اللعبة تحتاج لاعبين حقيقيين!\n\n"
            "أنشئ غرفة: `بلوت`",
            reply_markup=back_keyboard()
        )
        return

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text.strip()
    user_id = update.message.from_user.id
    user = get_user(user_id)
    
    # Blackjack
    if text.startswith("ورق "):
        try:
            bet = int(text.replace("ورق ", ""))
            if bet < 10 or bet > 100:
                await update.message.reply_text("الرهان يجب أن يكون 10-100!")
                return
            
            if user.points < bet:
                await update.message.reply_text("نقاطك غير كافية!")
                return
            
            game = BlackjackEngine.start(user_id, bet)
            if game:
                msg = f"🃏 ورق - رهان: {bet}\n\n"
                msg += f"🎮 يدك: {BlackjackEngine.get_display(game.player_cards)}\n"
                msg += f"   النقاط: {game.player_score}\n\n"
                msg += f"🃏 الديلر: {BlackjackEngine.get_display(game.dealer_cards, True)}\n\n"
                msg += f"اختر:\n"
                msg += f"• hit - سحب ورقة\n"
                msg += f"• stand - توقف"
                
                await update.message.reply_text(msg, reply_markup=blackjack_keyboard(game.id))
            else:
                await update.message.reply_text("نقاطك غير كافية!")
        except:
            await update.message.reply_text("الصيغة: `ورق 20`")
        return
    
    # Hit/Stand commands
    if text == "hit":
        games = db.blackjack_games
        active = [g for g in games if g["user_id"] == user_id and g["status"] == "playing"]
        if active:
            success, msg = BlackjackEngine.hit(active[-1]["id"], user_id)
            if "خسرت" in msg or "فزت" in msg or "تعادل" in msg:
                await update.message.reply_text(msg, reply_markup=play_again_keyboard())
            else:
                await update.message.reply_text(msg, reply_markup=blackjack_keyboard(active[-1]["id"]))
        return
    
    if text == "stand":
        games = db.blackjack_games
        active = [g for g in games if g["user_id"] == user_id and g["status"] == "playing"]
        if active:
            success, msg = BlackjackEngine.stand(active[-1]["id"], user_id)
            await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        return
    
    # Slot
    if text == "سلوت" or text == "🎰":
        won, msg, points = SlotEngine.spin(user_id)
        await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        return
    
    # Dice
    if text.startswith("نرد "):
        try:
            parts = text.replace("نرد ", "").split()
            bet = int(parts[0])
            prediction = parts[1] if len(parts) > 1 else "high"
            
            if prediction in ["كبير", "high"]:
                prediction = "high"
            elif prediction in ["صغير", "low"]:
                prediction = "low"
            elif prediction in ["زوجي", "even"]:
                prediction = "even"
            elif prediction in ["فردي", "odd"]:
                prediction = "odd"
            
            won, msg, points = DiceEngine.roll(user_id, prediction, bet)
            await update.message.reply_text(msg, reply_markup=play_again_keyboard())
        except:
            await update.message.reply_text("الصيغة: `نرد 20 كبير`")
        return
    
    # Default
    await update.message.reply_text(
        "🃏 العب من القائمة!",
        reply_markup=main_menu_keyboard(user_id)
    )

# ==================== MAIN ====================
def main() -> None:
    logger.info("🃏 Starting Card Games Bot...")
    
    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return
    
    app = Application.builder().token(config.BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("stats", stats_handler))
    app.add_handler(CommandHandler("help", lambda u, c: u.message.reply_text("""الأوامر:
/start - بدء
/stats - إحصائيات

🃏 ورق:
ورق 20 - ابدأ بلعبة
hit - سحب ورقة
stand - توقف

🎰 سلوت:
سلوت - تدوير

🎲 نرد:
نرد 20 كبير - تخمين
نرد 20 صغير
نرد 20 زوجي
نرد 20 فردي
"""))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(message_handler))
    
    logger.info("✅ Bot is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
