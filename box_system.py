"""
🎁 Mystery Box System - نظام الصناديق النادرة
💎 نظام فتح الصناديق للحصول على مكافآت نادرة
"""

import os
import json
import random
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_TOKEN_HERE")
    DB_PATH = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("BoxSystem")

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        os.makedirs(config.DB_PATH, exist_ok=True)
        self.users_file = f"{config.DB_PATH}/users.json"
        self.boxes_file = f"{config.DB_PATH}/boxes.json"
        self.drops_file = f"{config.DB_PATH}/drops.json"
        self._init_files()

    def _init_files(self):
        defaults = {
            self.users_file: {},
            self.boxes_file: {
                "box_types": {},
                "rewards": [],
                "statistics": {"total_opened": 0, "total_spent": 0}
            },
            self.drops_file: {"drops": [], "history": []}
        }
        for path, data in defaults.items():
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

    @property
    def users(self):
        return self._load(self.users_file)

    @users.setter
    def users(self, data):
        self._save(self.users_file, data)

    @property
    def boxes(self):
        return self._load(self.boxes_file)

    @boxes.setter
    def boxes(self, data):
        self._save(self.boxes_file, data)

    @property
    def drops(self):
        return self._load(self.drops_file)

    @drops.setter
    def drops(self, data):
        self._save(self.drops_file, data)

db = Database()

# ==================== BOX TYPES ====================
class BoxRarity(Enum):
    COMMON = "common"      # شائع
    UNCOMMON = "uncommon"  # غير شائع
    RARE = "rare"          # نادر
    EPIC = "epic"          # أسطوري
    LEGENDARY = "legendary"# خارق

class BoxType:
    """تعريف نوع الصندوق"""

    BOXES = {
        "basic": {
            "name": "صندوق أساسي",
            "rarity": BoxRarity.COMMON,
            "price": 50,
            "weight": 50,
            "rewards": [
                {"type": "points", "min": 10, "max": 30, "chance": 70},
                {"type": "points", "min": 30, "max": 50, "chance": 20},
                {"type": "gems", "min": 1, "max": 5, "chance": 10},
            ]
        },
        "silver": {
            "name": "صندوق فضي",
            "rarity": BoxRarity.UNCOMMON,
            "price": 150,
            "weight": 30,
            "rewards": [
                {"type": "points", "min": 50, "max": 100, "chance": 50},
                {"type": "points", "min": 100, "max": 200, "chance": 25},
                {"type": "gems", "min": 5, "max": 15, "chance": 15},
                {"type": "item", "chance": 10},
            ]
        },
        "gold": {
            "name": "صندوق ذهبي",
            "rarity": BoxRarity.RARE,
            "price": 500,
            "weight": 15,
            "rewards": [
                {"type": "points", "min": 200, "max": 400, "chance": 40},
                {"type": "points", "min": 400, "max": 800, "chance": 20},
                {"type": "gems", "min": 20, "max": 50, "chance": 15},
                {"type": "item", "chance": 15},
                {"type": "title", "chance": 10},
            ]
        },
        "diamond": {
            "name": "صندوق ماسي",
            "rarity": BoxRarity.EPIC,
            "price": 1500,
            "weight": 4,
            "rewards": [
                {"type": "points", "min": 500, "max": 1000, "chance": 30},
                {"type": "gems", "min": 50, "max": 100, "chance": 20},
                {"type": "item", "chance": 25},
                {"type": "title", "chance": 15},
                {"type": "boost", "chance": 10},
            ]
        },
        "mythic": {
            "name": "صندوق أسطوري",
            "rarity": BoxRarity.LEGENDARY,
            "price": 5000,
            "weight": 1,
            "rewards": [
                {"type": "points", "min": 2000, "max": 5000, "chance": 25},
                {"type": "gems", "min": 100, "max": 300, "chance": 20},
                {"type": "item", "chance": 20},
                {"type": "title", "chance": 15},
                {"type": "boost", "chance": 10},
                {"type": "ton", "chance": 10},
            ]
        }
    }

    @classmethod
    def get_all_boxes(cls) -> List[Dict]:
        """جلب جميع الصناديق"""
        return [
            {"id": k, **v} for k, v in cls.BOXES.items()
        ]

    @classmethod
    def get_box(cls, box_id: str) -> Optional[Dict]:
        """جلب صندوق محدد"""
        return cls.BOXES.get(box_id)

# ==================== REWARDS ====================
class RewardType(Enum):
    POINTS = "points"
    GEMS = "gems"
    ITEM = "item"
    TITLE = "title"
    BOOST = "boost"
    TON = "ton"

class Rewards:
    """قائمة المكافآت"""

    # العناصر النادرة (Items)
    ITEMS = [
        {"id": "sword_bronze", "name": "سيف برونزي", "rarity": "common", "value": 100},
        {"id": "sword_silver", "name": "سيف فضي", "rarity": "uncommon", "value": 300},
        {"id": "sword_gold", "name": "سيف ذهبي", "rarity": "rare", "value": 1000},
        {"id": "shield_iron", "name": "درع حديدي", "rarity": "common", "value": 100},
        {"id": "shield_diamond", "name": "درع ماسي", "rarity": "epic", "value": 3000},
        {"id": "potion_health", "name": "جرعة صحة", "rarity": "common", "value": 50},
        {"id": "potion_xp", "name": "جرعة XP", "rarity": "uncommon", "value": 200},
        {"id": "gem_red", "name": "ياقوت أحمر", "rarity": "rare", "value": 500},
        {"id": "gem_blue", "name": "ياقوت أزرق", "rarity": "rare", "value": 500},
        {"id": "key_door", "name": "مفتاح باب", "rarity": "epic", "value": 2000},
    ]

    # الألقاب (Titles)
    TITLES = [
        {"id": "lucky", "name": "محظوظ", "color": "🟢"},
        {"id": "champion", "name": "بطل", "color": "🏆"},
        {"id": "master", "name": "أستاذ", "color": "🎓"},
        {"id": "legend", "name": "أسطورة", "color": "🔥"},
        {"id": "king", "name": "ملك", "color": "👑"},
        {"id": "hunter", "name": "صياد", "color": "🎯"},
    ]

    # التعزيزات (Boosts)
    BOOSTS = [
        {"id": "xp_2x", "name": "XP ×2", "duration": 3600, "value": 500},
        {"id": "points_2x", "name": "نقاط ×2", "duration": 3600, "value": 500},
        {"id": "streak_freeze", "name": "تجميد السلسلة", "duration": 86400, "value": 300},
    ]

    @classmethod
    def get_random_item(cls, rarity: str = None) -> Dict:
        """جلب عنصر عشوائي"""
        items = cls.ITEMS
        if rarity:
            items = [i for i in items if i["rarity"] == rarity]
        return random.choice(items) if items else None

    @classmethod
    def get_random_title(cls) -> Dict:
        """جلب لقب عشوائي"""
        return random.choice(cls.TITLES)

    @classmethod
    def get_random_boost(cls) -> Dict:
        """جلب تعزيز عشوائي"""
        return random.choice(cls.BOOSTS)

# ==================== BOX SYSTEM ====================
class BoxSystem:
    """نظام الصناديق"""

    @staticmethod
    def calculate_drop(box_id: str) -> Tuple[Dict, Dict]:
        """حساب المكافأة"""
        box = BoxType.get_box(box_id)
        if not box:
            return None, None

        rewards = box["rewards"]
        roll = random.random() * 100
        cumulative = 0

        for reward in rewards:
            cumulative += reward.get("chance", 0)
            if roll <= cumulative:
                # Found the reward tier
                reward_type = reward["type"]

                if reward_type == "points":
                    amount = random.randint(reward["min"], reward["max"])
                    return {"type": "points", "amount": amount, "name": f"{amount} نقطة"}, box

                elif reward_type == "gems":
                    amount = random.randint(reward["min"], reward["max"])
                    return {"type": "gems", "amount": amount, "name": f"{amount} جوهرة"}, box

                elif reward_type == "item":
                    item = Rewards.get_random_item()
                    return {"type": "item", "item": item, "name": item["name"]}, box

                elif reward_type == "title":
                    title = Rewards.get_random_title()
                    return {"type": "title", "title": title, "name": f"{title['color']} {title['name']}"}, box

                elif reward_type == "boost":
                    boost = Rewards.get_random_boost()
                    return {"type": "boost", "boost": boost, "name": boost["name"]}, box

                elif reward_type == "ton":
                    amount = round(random.uniform(0.1, 1.0), 2)
                    return {"type": "ton", "amount": amount, "name": f"{amount} TON"}, box

        # Default fallback
        return {"type": "points", "amount": 10, "name": "10 نقاط"}, box

    @staticmethod
    def open_box(user_id: int, box_id: str) -> Tuple[bool, str, Dict]:
        """فتح صندوق"""
        users = db.users
        uid = str(user_id)

        if uid not in users:
            return False, "المستخدم غير موجود!", None

        user = users[uid]
        box = BoxType.get_box(box_id)

        if not box:
            return False, "الصندوق غير موجود!", None

        # Check balance
        if user.get("points", 0) < box["price"]:
            return False, f"نقاط غير كافية! تحتاج {box['price']}", None

        # Deduct points
        user["points"] -= box["price"]

        # Add to inventory
        inventory = user.get("inventory", {})
        if box_id not in inventory:
            inventory[box_id] = 0
        inventory[box_id] = inventory.get(box_id, 0) + 1

        # Get reward
        reward, box_info = BoxSystem.calculate_drop(box_id)

        # Add reward to user
        if reward["type"] == "points":
            user["points"] = user.get("points", 0) + reward["amount"]
        elif reward["type"] == "gems":
            user["gems"] = user.get("gems", 0) + reward["amount"]
        elif reward["type"] == "item":
            items = user.get("items", [])
            items.append(reward["item"])
            user["items"] = items
        elif reward["type"] == "title":
            titles = user.get("titles", [])
            if reward["title"]["id"] not in [t["id"] for t in titles]:
                titles.append(reward["title"])
                user["titles"] = titles
        elif reward["type"] == "boost":
            boosts = user.get("boosts", [])
            boosts.append(reward["boost"])
            user["boosts"] = boosts
        elif reward["type"] == "ton":
            user["ton_balance"] = user.get("ton_balance", 0) + reward["amount"]

        # Update stats
        user["boxes_opened"] = user.get("boxes_opened", 0) + 1
        user["total_spent"] = user.get("total_spent", 0) + box["price"]
        user["inventory"] = inventory

        # Save
        users[uid] = user
        db.users = users

        # Update global stats
        boxes_data = db.boxes
        boxes_data["statistics"]["total_opened"] = boxes_data["statistics"].get("total_opened", 0) + 1
        boxes_data["statistics"]["total_spent"] = boxes_data["statistics"].get("total_spent", 0) + box["price"]
        db.boxes = boxes_data

        return True, f"🎉 فتحت {box_info['name']}!", reward

    @staticmethod
    def buy_box(user_id: int, box_id: str, quantity: int = 1) -> Tuple[bool, str]:
        """شراء صندوق"""
        users = db.users
        uid = str(user_id)

        if uid not in users:
            return False, "المستخدم غير موجود!"

        user = users[uid]
        box = BoxType.get_box(box_id)

        if not box:
            return False, "الصندوق غير موجود!"

        total_cost = box["price"] * quantity

        if user.get("points", 0) < total_cost:
            return False, f"نقاط غير كافية! تحتاج {total_cost}"

        # Deduct points
        user["points"] -= total_cost

        # Add to inventory
        inventory = user.get("inventory", {})
        inventory[box_id] = inventory.get(box_id, 0) + quantity
        user["inventory"] = inventory

        users[uid] = user
        db.users = users

        return True, f"✅ اشتريت {quantity} × {box['name']}!"

# ==================== USER HELPERS ====================
def get_user(user_id: int) -> Dict:
    users = db.users
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "points": 100,
            "gems": 0,
            "ton_balance": 0,
            "boxes_opened": 0,
            "total_spent": 0,
            "inventory": {},
            "items": [],
            "titles": [],
            "boosts": [],
            "created_at": datetime.now().isoformat()
        }
        db.users = users

    return users[uid]

def update_user(user_id: int, data: Dict):
    users = db.users
    uid = str(user_id)
    if uid in users:
        users[uid].update(data)
        db.users = users

# ==================== KEYBOARDS ====================
def boxes_keyboard(user_id: int):
    user = get_user(user_id)

    keyboard = [
        [InlineKeyboardButton("📦 أساسي (50)", callback_data="box_buy_basic")],
        [InlineKeyboardButton("🥈 فضي (150)", callback_data="box_buy_silver")],
        [InlineKeyboardButton("🥇 ذهبي (500)", callback_data="box_buy_gold")],
        [InlineKeyboardButton("💎 ماسي (1500)", callback_data="box_buy_diamond")],
        [InlineKeyboardButton("🔥 أسطوري (5000)", callback_data="box_buy_mythic")],
        [InlineKeyboardButton("🎁 فتح صندوق", callback_data="box_open_menu")],
        [InlineKeyboardButton("🎒 حقيبتي", callback_data="box_inventory")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="box_stats")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def inventory_keyboard(user_id: int):
    user = get_user(user_id)
    inventory = user.get("inventory", {})

    keyboard = []
    for box_id, qty in inventory.items():
        if qty > 0:
            box = BoxType.get_box(box_id)
            if box:
                keyboard.append(InlineKeyboardButton(
                    f"{box['name']} ×{qty}",
                    callback_data=f"box_open_{box_id}"
                ))

    if not keyboard:
        keyboard.append([InlineKeyboardButton("لا توجد صناديق!", callback_data="box_menu")])

    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="box_menu")])
    return InlineKeyboardMarkup(keyboard)

def back_keyboard(callback: str = "box_menu"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=callback)]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    get_user(user.id)

    await update.message.reply_text(
        f"🎁 نظام الصناديق النادرة
"
        f"━━━━━━━━━━━━━━━━
"
        f"💰 نقاطك: {get_user(user.id)['points']}
"
        f"💎 جواهر: {get_user(user.id).get('gems', 0)}
"
        f"📦 صناديق مفتوحة: {get_user(user.id).get('boxes_opened', 0)}

"
        f"🎁 اختر الصندوق:",
        reply_markup=boxes_keyboard(user.id)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)

    # Box menu
    if data == "box_menu":
        await query.edit_message_text(
            f"🎁 نظام الصناديق النادرة
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 نقاطك: {user['points']}
"
            f"💎 جواهر: {user.get('gems', 0)}

"
            f"🎁 اختر الصندوق:",
            reply_markup=boxes_keyboard(user_id)
        )

    # Buy boxes
    elif data.startswith("box_buy_"):
        box_id = data.replace("box_buy_", "")
        box = BoxType.get_box(box_id)

        if box:
            success, msg = BoxSystem.buy_box(user_id, box_id)
            if success:
                user = get_user(user_id)
                await query.answer(msg, show_alert=True)
                await query.edit_message_text(
                    f"✅ {msg}

"
                    f"💰 الرصيد: {user['points']}
"
                    f"📦 {box['name']}: {user['inventory'].get(box_id, 0)}",
                    reply_markup=boxes_keyboard(user_id)
                )
            else:
                await query.answer(msg, show_alert=True)

    # Open box menu
    elif data == "box_open_menu":
        await query.edit_message_text(
            f"🎁 فتح صندوق
"
            f"━━━━━━━━━━━━━━━━
"
            f"📦 صناديقك:",
            reply_markup=inventory_keyboard(user_id)
        )

    # Open specific box
    elif data.startswith("box_open_"):
        box_id = data.replace("box_open_", "")
        inventory = user.get("inventory", {})

        if inventory.get(box_id, 0) <= 0:
            await query.answer("⚠️ لا تملك هذا الصندوق!", show_alert=True)
            return

        # Open the box
        success, msg, reward = BoxSystem.open_box(user_id, box_id)

        if success:
            # Decrease inventory
            inventory[box_id] -= 1
            update_user(user_id, {"inventory": inventory})

            user = get_user(user_id)

            # Build reward message
            reward_emoji = {
                "points": "💰",
                "gems": "💎",
                "item": "🎁",
                "title": "🏅",
                "boost": "⚡",
                "ton": "🪙"
            }

            emoji = reward_emoji.get(reward["type"], "🎁")

            await query.edit_message_text(
                f"🎉 تهانينا!
"
                f"━━━━━━━━━━━━━━━━
"
                f"📦 الصندوق: {BoxType.get_box(box_id)['name']}

"
                f"🎁 المكافأة:
"
                f"{emoji} {reward['name']}

"
                f"💰 نقاطك: {user['points']}
"
                f"📦 متبقي: {user['inventory'].get(box_id, 0)}",
                reply_markup=inventory_keyboard(user_id)
            )
        else:
            await query.answer(msg, show_alert=True)

    # Inventory
    elif data == "box_inventory":
        inventory = user.get("inventory", {})
        items = user.get("items", [])
        titles = user.get("titles", [])
        boosts = user.get("boosts", [])

        text = f"🎒 حقيبتك
━━━━━━━━━━━━━━━━
"

        text += f"
📦 الصناديق:
"
        for box_id, qty in inventory.items():
            if qty > 0:
                box = BoxType.get_box(box_id)
                if box:
                    text += f"• {box['name']}: {qty}
"

        text += f"
🎁 العناصر ({len(items)}):
"
        for item in items[:5]:
            text += f"• {item['name']} ({item['rarity']})
"

        if titles:
            text += f"
🏅 الألقاب:
"
            for title in titles:
                text += f"{title['color']} {title['name']}
"

        if boosts:
            text += f"
⚡ التعزيزات:
"
            for boost in boosts[:3]:
                text += f"• {boost['name']}
"

        await query.edit_message_text(text, reply_markup=back_keyboard("box_menu"))

    # Stats
    elif data == "box_stats":
        boxes_data = db.boxes
        stats = boxes_data.get("statistics", {})

        text = f"📊 إحصائيات الصناديق
━━━━━━━━━━━━━━━━
"
        text += f"📦总数 المفتوحة: {stats.get('total_opened', 0)}
"
        text += f"💰 إجمالي الصرف: {stats.get('total_spent', 0)}
"
        text += f"👥 اللاعبين: {len(db.users)}
"

        await query.edit_message_text(text, reply_markup=back_keyboard("box_menu"))

    # Back
    elif data == "back":
        await start(update, context)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()

    await update.message.reply_text(
        "🎁 اضغط /start لفتح نظام الصناديق!",
        reply_markup=boxes_keyboard(user_id)
    )

# ==================== MAIN ====================
def main():
    logger.info("🎁 Starting Box System Bot...")

    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return

    app = Application.builder().token(Config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(message))

    logger.info("✅ Box System is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
