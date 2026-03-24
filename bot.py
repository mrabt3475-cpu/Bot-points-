"""
🤖 Pointporn Wallet Bot
بوت محفظة إلكترونية مشفرة مع نظام إحالة ودفع باينس
"""

import os
import json
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes

# ==================== CONFIG ====================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8593254152:AAFm59iuO45KmWqnlxb0ufDPRN8kDH6mjGc")
BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "")
BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "")
REFERRAL_COMMISSION = float(os.getenv("REFERRAL_COMMISSION", "0.20"))

# ملفات البيانات
DATA_FILE = "data.json"
USERS_FILE = "users.json"

# ==================== DATABASE ====================
def load_users():
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def get_user(user_id):
    users = load_users()
    if str(user_id) not in users:
        users[str(user_id)] = {
            "balance": 0,
            "referral_code": generate_referral_code(),
            "referred_by": None,
            "referrals_count": 0,
            "earnings": 0,
            "total_spent": 0,
            "join_date": datetime.now().isoformat()
        }
        save_users(users)
    return users[str(user_id)]

def update_user(user_id, data):
    users = load_users()
    users[str(user_id)].update(data)
    save_users(users)

def generate_referral_code():
    return 'REF-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ==================== BINANCE ====================
def create_binance_payment(amount_usdt):
    payment_id = "PAY-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    return {
        "payment_id": payment_id,
        "amount": amount_usdt,
        "address": "YOUR_TRUST_WALLET_ADDRESS",
        "network": "TRC20",
        "status": "pending"
    }

def check_payment_status(payment_id):
    return {"status": "completed", "confirmed": True}

# ==================== KEYBOARDS ====================
def main_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("💰 الرصيد", callback_data="balance")],
        [InlineKeyboardButton("🛒 شراء نقاط", callback_data="buy")],
        [InlineKeyboardButton("📤 إرسال نقاط", callback_data="send")],
        [InlineKeyboardButton("📥 استقبال نقاط", callback_data="receive")],
        [InlineKeyboardButton("🔗 الإحالة", callback_data="referral")],
        [InlineKeyboardButton("❓ مساعدة", callback_data="help")]
    ]
    return InlineKeyboardMarkup(keyboard)

def buy_amount_keyboard():
    keyboard = [
        [InlineKeyboardButton("10 USDT", callback_data="buy_10")],
        [InlineKeyboardButton("25 USDT", callback_data="buy_25")],
        [InlineKeyboardButton("50 USDT", callback_data="buy_50")],
        [InlineKeyboardButton("100 USDT", callback_data="buy_100")],
        [InlineKeyboardButton("💵 مبلغ آخر", callback_data="buy_custom")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")]
    ]
    return InlineKeyboardMarkup(keyboard)

def confirm_payment_keyboard(payment_id):
    keyboard = [
        [InlineKeyboardButton("✅ تم الدفع", callback_data=f"confirm_{payment_id}")],
        [InlineKeyboardButton("❌ إلغاء", callback_data="cancel")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== COMMANDS ====================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    
    args = context.args
    referred_by = None
    if args:
        referred_by = args[0]
    
    user_data = get_user(user_id)
    if referred_by and referred_by != user_data.get("referral_code"):
        users = load_users()
        for uid, udata in users.items():
            if udata.get("referral_code") == referred_by:
                referred_by = uid
                break
        
        if referred_by and not user_data.get("referred_by"):
            user_data["referred_by"] = referred_by
            update_user(user_id, user_data)
            
            referrer_user = get_user(int(referred_by))
            bonus_points = 20
            update_user(int(referred_by), {
                "balance": referrer_user.get("balance", 0) + bonus_points,
                "referrals_count": referrer_user.get("referrals_count", 0) + 1,
                "earnings": referrer_user.get("earnings", 0) + bonus_points
            })
    
    welcome_text = f"""
🎉 مرحباً بك في Pointporn Wallet!

💰 محفظتك الإلكترونية المشفرة

رصيدك الحالي: {user_data.get('balance', 0)} نقطة

🔗 كود الإحالة الخاص بك:
{user_data.get('referral_code')}

🎯 اربح 20% من كل عملية شراء يقوم بها مُحالوك!

اختر من القائمة:
"""
    await update.message.reply_text(welcome_text, reply_markup=main_menu_keyboard())

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user(user_id)
    
    text = f"""
💰 رصيدك الحالي

🪙 الرصيد: {user_data.get('balance', 0)} نقطة

📊 الإحصائيات:
• عدد المُحالين: {user_data.get('referrals_count', 0)}
• أرباح الإحالة: {user_data.get('earnings', 0)} نقطة
• إجمالي أنفقته: {user_data.get('total_spent', 0)} USDT
"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
🛒 شراء نقاط

اختر المبلغ الذي تريد شراؤه:

💵 كل 1 USDT = 100 نقطة
"""
    await update.message.reply_text(text, reply_markup=buy_amount_keyboard())

async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user(user_id)
    
    if user_data.get('balance', 0) < 1:
        await update.message.reply_text("❌ رصيدك غير كافٍ!", reply_markup=main_menu_keyboard())
        return
    
    text = """
📤 إرسال نقاط

أرسل لي رسالة بهذه الصيغة:
إرسال [عدد النقاط] [كود_المستلم]

مثال:
إرسال 100 REF-XXXXXX
"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

async def receive_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user(user_id)
    
    text = f"""
📥 استقبال نقاط

معرف الدفع الخاص بك:
{user_data.get('referral_code')}

ارسل هذا الكود لصديقك ليُرسل لك نقاط!
"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user(user_id)
    
    bot_username = context.bot.username
    
    text = f"""
🔗 نظام الإحالة

🎁 اربح 20% من كل عملية شراء يُجريها مُحالوك!

📊 إحصائياتك:
• عدد المُحالين: {user_data.get('referrals_count', 0)}
• أرباح الإحالة: {user_data.get('earnings', 0)} نقطة

🔗 رابط الإحالة:
https://t.me/{bot_username}?start={user_data.get('referral_code')}

📋 كود الإحالة:
{user_data.get('referral_code')}
"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = """
❓ مساعدة

🤖 الأوامر المتاحة:

• /start - بدء البوت
• /balance - عرض الرصيد
• /buy - شراء نقاط
• /send - إرسال نقاط
• /receive - استقبال نقاط
• /referral - رابط الإحالة
• /help - مساعدة
"""
    await update.message.reply_text(text, reply_markup=main_menu_keyboard())

# ==================== CALLBACKS ====================
async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    if data == "balance":
        await balance_command(update, context)
    elif data == "buy":
        await buy_command(update, context)
    elif data == "send":
        await send_command(update, context)
    elif data == "receive":
        await receive_command(update, context)
    elif data == "referral":
        await referral_command(update, context)
    elif data == "help":
        await help_command(update, context)
    elif data == "back":
        user_data = get_user(user_id)
        text = f"🏠 القائمة الرئيسية\n\nرصيدك: {user_data.get('balance', 0)} نقطة"
        await query.edit_message_text(text, reply_markup=main_menu_keyboard())
    elif data.startswith("buy_"):
        amount = data.replace("buy_", "")
        if amount == "custom":
            await query.edit_message_text("💵 أدخل المبلغ الذي تريد شراؤه (ب USDT):")
        else:
            await process_buy(query, context, int(amount))
    elif data.startswith("confirm_"):
        payment_id = data.replace("confirm_", "")
        await process_payment_confirm(query, context, payment_id)
    elif data == "cancel":
        await query.edit_message_text("❌ تم إلغاء العملية", reply_markup=main_menu_keyboard())

async def process_buy(query, context, amount_usdt):
    payment = create_binance_payment(amount_usdt)
    points = amount_usdt * 100
    
    text = f"""
🛒 طلب شراء جديد

💵 المبلغ: {amount_usdt} USDT
🪙 النقاط: {points} نقطة

📋 معرف الدفع: {payment['payment_id']}

💳 عنوان USDT (TRC20):
{payment['address']}

⚠️ التحذير:
• تأكد من إرسال المبلغ الصحيح
• استخدم شبكة TRC20 فقط
• بعد الإرسال اضغط "تم الدفع"
"""
    await query.edit_message_text(text, reply_markup=confirm_payment_keyboard(payment['payment_id']))

async def process_payment_confirm(query, context, payment_id):
    payment_status = check_payment_status(payment_id)
    
    if payment_status.get("confirmed"):
        user_id = query.from_user.id
        user_data = get_user(user_id)
        
        points = 100
        new_balance = user_data.get('balance', 0) + points
        
        update_user(user_id, {
            "balance": new_balance,
            "total_spent": user_data.get('total_spent', 0) + 1
        })
        
        await query.edit_message_text(f"""
✅ تم تأكيد الدفع!

🎉 تم إضافة {points} نقطة لرصيدك

💰 رصيدك الجديد: {new_balance} نقطة
""", reply_markup=main_menu_keyboard())
    else:
        await query.edit_message_text("⏳ جاري التحقق من الدفع...", reply_markup=main_menu_keyboard())

# ==================== MESSAGE HANDLER ====================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text.startswith("إرسال "):
        await handle_send(update, context)
    else:
        await update.message.reply_text("❌ أمر غير معروف!", reply_markup=main_menu_keyboard())

async def handle_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user_data = get_user(user_id)
    
    try:
        parts = update.message.text.replace("إرسال ", "").split()
        points = int(parts[0])
        recipient = parts[1]
        
        if user_data.get('balance', 0) < points:
            await update.message.reply_text("❌ رصيدك غير كافٍ!", reply_markup=main_menu_keyboard())
            return
        
        users = load_users()
        recipient_id = None
        
        for uid, udata in users.items():
            if udata.get("referral_code") == recipient:
                recipient_id = int(uid)
                break
        
        if not recipient_id:
            await update.message.reply_text("❌ المستخدم غير موجود!", reply_markup=main_menu_keyboard())
            return
        
        if recipient_id == user_id:
            await update.message.reply_text("❌ لا يمكنك إرسال النقاط لنفسك!", reply_markup=main_menu_keyboard())
            return
        
        update_user(user_id, {
            "balance": user_data.get('balance', 0) - points
        })
        
        recipient_data = get_user(recipient_id)
        update_user(recipient_id, {
            "balance": recipient_data.get('balance', 0) + points
        })
        
        await update.message.reply_text(f"""
✅ تم إرسال النقاط!

📤 المُرسل: {user_id}
📥 المُستلم: {recipient_id}
🪙 النقاط: {points}

💰 رصيدك المتبقي: {user_data.get('balance', 0) - points} نقطة
""", reply_markup=main_menu_keyboard())
        
    except:
        await update.message.reply_text("❌ صيغة خاطئة! استخدم:\nإرسال 100 REF-XXXXXX", reply_markup=main_menu_keyboard())

# ==================== MAIN ====================
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("balance", balance_command))
    app.add_handler(CommandHandler("buy", buy_command))
    app.add_handler(CommandHandler("send", send_command))
    app.add_handler(CommandHandler("receive", receive_command))
    app.add_handler(CommandHandler("referral", referral_command))
    app.add_handler(CommandHandler("help", help_command))
    
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(handle_message))
    
    print("🤖 البوت يعمل...")
    app.run_polling(allowed_updates=['message', 'callback_query'])

if __name__ == "__main__":
    main()
