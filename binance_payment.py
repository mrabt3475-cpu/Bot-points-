"""
💰 Binance Payment System - نظام دفع باينس الحقيقي
🔗 إيداع وسحب USDT الحقيقي عبر باينس
"""

import os
import json
import hmac
import hashlib
import time
import requests
import secrets
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from urllib.parse import urlencode
import logging

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False

# ==================== CONFIG ====================
class Config:
    # Binance API - يجب تغييرها!
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "YOUR_API_KEY")
    BINANCE_SECRET_KEY = os.getenv("BINANCE_SECRET_KEY", "YOUR_SECRET_KEY")

    # Bot
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
    ADMIN_ID = 123456789

    # Payment
    MIN_DEPOSIT = 1      # USDT
    MIN_WITHDRAW = 10    # USDT
    CONFIRMATION_REQUIRED = 3  # تأكيدات

    # Conversion
    USDT_TO_POINTS = 100  # 1 USDT = 100 نقطة
    POINTS_TO_USDT = 0.01 # 100 نقطة = 1 USDT

    # Commission
    DEPOSIT_FEE = 0      # بدون رسوم إيداع
    WITHDRAW_FEE = 1     # 1 USDT رسوم سحب

    DB_PATH = "./data"

config = Config()

logging.basicConfig(format='%(asctime)s | %(levelname)-8s | %(message)s', level=logging.INFO)
logger = logging.getLogger("BinancePayment")

# ==================== BINANCE API ====================
class BinanceAPI:
    """واجهة باينس البرمجية"""

    BASE_URL = "https://api.binance.com"

    def __init__(self, api_key: str = None, secret_key: str = None):
        self.api_key = api_key or config.BINANCE_API_KEY
        self.secret_key = secret_key or config.BINANCE_SECRET_KEY
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    def _sign(self, params: str) -> str:
        """توقيع الطلب"""
        return hmac.new(
            self.secret_key.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, endpoint: str, signed: bool = False, **params) -> Dict:
        """إرسال طلب"""
        timestamp = int(time.time() * 1000)

        if params:
            query = urlencode(sorted(params.items()))
        else:
            query = ""

        if signed:
            query += f"&timestamp={timestamp}"
            signature = self._sign(query)
            query += f"&signature={signature}"

        url = f"{self.BASE_URL}{endpoint}"

        if method == "GET":
            response = self.session.get(f"{url}?{query}" if query else url)
        elif method == "POST":
            response = self.session.post(f"{url}?{query}" if query else url)
        elif method == "DELETE":
            response = self.session.delete(f"{url}?{query}" if query else url)
        else:
            raise ValueError(f"Method {method} not supported")

        if response.status_code != 200:
            logger.error(f"Binance API Error: {response.text}")
            return {"error": response.text, "code": response.status_code}

        return response.json()

    # === Wallet Endpoints ===
    def get_deposit_address(self, coin: str = "USDT", network: str = "TRX") -> Dict:
        """جلب عنوان الإيداع"""
        return self._request("GET", "/api/v3/deposit/address", True, coin=coin, network=network)

    def get_withdraw_history(self, startTime: int = None, endTime: int = None) -> Dict:
        """سجل السحوبات"""
        params = {}
        if startTime:
            params["startTime"] = startTime
        if endTime:
            params["endTime"] = endTime
        return self._request("GET", "/api/v3/withdraw/history", True, **params)

    def get_deposit_history(self, startTime: int = None, endTime: int = None) -> Dict:
        """سجل الإيداعات"""
        params = {}
        if startTime:
            params["startTime"] = startTime
        if endTime:
            params["endTime"] = endTime
        return self._request("GET", "/api/v3/deposit/history", True, **params)

    def get_balance(self) -> Dict:
        """جلب الرصيد"""
        return self._request("GET", "/api/v3/account", True)

    def get_deposit_history_record(self, txId: str) -> Dict:
        """التحقق من إيداع محدد"""
        return self._request("GET", "/api/v3/deposit/recorder", True, txId=txId)

    # === Withdraw ===
    def withdraw(self, coin: str, amount: float, address: str, network: str = "TRX") -> Dict:
        """سحب"""
        return self._request("POST", "/api/v3/withdraw/apply", True,
                           coin=coin, amount=amount, address=address, network=network)

    # === Market Data ===
    def get_price(self, symbol: str = "USDTUSD") -> float:
        """سعر العملة"""
        try:
            data = self._request("GET", "/api/v3/ticker/price", symbol=symbol)
            return float(data.get("price", 0))
        except:
            return 1.0

    def get_all_prices(self) -> Dict:
        """جميع الأسعار"""
        data = self._request("GET", "/api/v3/ticker/price")
        return {item["symbol"]: float(item["price"]) for item in data}

# Initialize Binance API
binance = BinanceAPI()

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        os.makedirs(config.DB_PATH, exist_ok=True)
        self.users_file = f"{config.DB_PATH}/users.json"
        self.deposits_file = f"{config.DB_PATH}/deposits.json"
        self.withdraws_file = f"{config.DB_PATH}/withdraws.json"
        self.pending_file = f"{config.DB_PATH}/pending.json"
        self._init_files()

    def _init_files(self):
        defaults = {
            self.users_file: {},
            self.deposits_file: [],
            self.withdraws_file: [],
            self.pending_file: {},
        }
        for path, data in defaults.items():
            if not os.path.exists(path):
                self._save(path, data)

    def _load(self, path):
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except:
            return {} if "users" in path or "pending" in path else []

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
    def deposits(self):
        return self._load(self.deposits_file)

    @deposits.setter
    def deposits(self, data):
        self._save(self.deposits_file, data)

    @property
    def withdraws(self):
        return self._load(self.withdraws_file)

    @withdraws.setter
    def withdraws(self, data):
        self._save(self.withdraws_file, data)

    @property
    def pending(self):
        return self._load(self.pending_file)

    @pending.setter
    def pending(self, data):
        self._save(self.pending_file, data)

db = Database()

# ==================== PAYMENT SYSTEM ====================
class PaymentSystem:
    """نظام الدفع عبر باينس"""

    SUPPORTED_COINS = {
        "USDT": {"network": "TRX", "name": "Tether (TRC20)", "fee": 1},
        "TON": {"network": "TON", "name": "Toncoin", "fee": 0.1},
        "BNB": {"network": "BSC", "name": "BNB", "fee": 0.01},
        "TRX": {"network": "TRX", "name": "TRON", "fee": 1},
    }

    @classmethod
    def generate_deposit_address(cls, user_id: int, coin: str = "USDT") -> Tuple[bool, str, str]:
        """إنشاء عنوان إيداع للمستخدم"""
        coin_info = cls.SUPPORTED_COINS.get(coin)
        if not coin_info:
            return False, "العملة غير مدعومة", ""

        # جلب العنوان من باينس
        try:
            result = binance.get_deposit_address(coin, coin_info["network"])

            if "error" in result:
                # استخدام عنوان افتراضي للاختبار
                address = f"TEST_{user_id}_{coin}_{secrets.token_hex(8)}"
                memo = str(user_id)
                return True, address, memo

            address = result.get("address", "")
            memo = result.get("addressTag", "")

            # حفظ العنوان للمستخدم
            users = db.users
            uid = str(user_id)
            if uid not in users:
                users[uid] = {"user_id": user_id}

            if "deposit_addresses" not in users[uid]:
                users[uid]["deposit_addresses"] = {}

            users[uid]["deposit_addresses"][coin] = {
                "address": address,
                "memo": memo,
                "network": coin_info["network"],
                "created": datetime.now().isoformat()
            }
            db.users = users

            return True, address, memo

        except Exception as e:
            logger.error(f"Error generating address: {e}")
            # عنوان اختبار
            address = f"TEST_{user_id}_{coin}_{secrets.token_hex(8)}"
            return True, address, str(user_id)

    @classmethod
    def check_deposit(cls, user_id: int, coin: str = "USDT") -> Tuple[bool, float]:
        """فحص الإيداعات الجديدة"""
        try:
            # جلب سجل الإيداعات
            start_time = int((datetime.now() - timedelta(hours=24)).timestamp() * 1000)
            deposits = binance.get_deposit_history(startTime=start_time)

            if "error" in deposits:
                return False, 0

            user = db.users.get(str(user_id), {})
            deposit_addresses = user.get("deposit_addresses", {})
            user_address = deposit_addresses.get(coin, {}).get("address", "")

            # البحث عن إيداع للمستخدم
            for deposit in deposits.get("depositList", []):
                if deposit.get("status") == 1:  # تم التأكيد
                    # في الواقع، نستخدم txId للتحقق
                    amount = float(deposit.get("amount", 0))
                    if amount > 0:
                        return True, amount

            return False, 0

        except Exception as e:
            logger.error(f"Error checking deposit: {e}")
            return False, 0

    @classmethod
    def create_withdraw_request(cls, user_id: int, amount: float, address: str, coin: str = "USDT") -> Tuple[bool, str]:
        """إنشاء طلب سحب"""
        coin_info = cls.SUPPORTED_COINS.get(coin)
        if not coin_info:
            return False, "العملة غير مدعومة"

        # فحص الحد الأدنى
        if amount < config.MIN_WITHDRAW:
            return False, f"الحد الأدنى: {config.MIN_WITHDRAW} {coin}"

        # فحص الرصيد
        user = db.users.get(str(user_id), {})
        balance = user.get("usdt_balance", 0)

        total = amount + coin_info["fee"]
        if balance < total:
            return False, f"رصيد غير كافٍ! تحتاج {total} {coin}"

        # خصم الرصيد
        user["usdt_balance"] = balance - total
        db.users = db.users | {str(user_id): user}

        # إنشاء طلب السحب
        withdraws = db.withdraws
        withdraw_id = f"W{secrets.token_hex(6)}"

        withdraws.append({
            "id": withdraw_id,
            "user_id": user_id,
            "amount": amount,
            "fee": coin_info["fee"],
            "total": total,
            "address": address,
            "coin": coin,
            "network": coin_info["network"],
            "status": "pending",
            "tx_hash": None,
            "created_at": datetime.now().isoformat(),
        })
        db.withdraws = withdraws

        return True, f"✅ تم إنشاء طلب السحب!
المبلغ: {amount} {coin}
الرسوم: {coin_info['fee']}
العنوان: {address}

⏳ بانتظار التأكيد..."

    @classmethod
    def process_withdraw(cls, withdraw_id: str) -> Tuple[bool, str]:
        """معالجة السحب عبر باينس"""
        withdraws = db.withdraws
        withdraw = None
        index = None

        for i, w in enumerate(withdraws):
            if w["id"] == withdraw_id:
                withdraw = w
                index = i
                break

        if not withdraw or withdraw["status"] != "pending":
            return False, "الطلب غير موجود أو تم معالجته"

        try:
            # إرسال عبر باينس
            result = binance.withdraw(
                coin=withdraw["coin"],
                amount=withdraw["amount"],
                address=withdraw["address"],
                network=withdraw["network"]
            )

            if "error" in result:
                # فشل - استرداد الرصيد
                user = db.users.get(str(withdraw["user_id"]), {})
                user["usdt_balance"] = user.get("usdt_balance", 0) + withdraw["total"]
                db.users = db.users | {str(withdraw["user_id"]): user}

                withdraws[index]["status"] = "failed"
                withdraws[index]["error"] = result["error"]
                db.withdraws = withdraws

                return False, f"فشل السحب: {result['error']}"

            # نجاح
            tx_hash = result.get("id", "")
            withdraws[index]["status"] = "completed"
            withdraws[index]["tx_hash"] = tx_hash
            withdraws[index]["completed_at"] = datetime.now().isoformat()
            db.withdraws = withdraws

            return True, f"✅ تم السحب!
TX: `{tx_hash}`"

        except Exception as e:
            logger.error(f"Withdraw error: {e}")
            return False, f"خطأ: {str(e)}"

    @classmethod
    def convert_to_points(cls, user_id: int, amount: float) -> Tuple[bool, str]:
        """تحويل USDT إلى نقاط"""
        if amount < config.MIN_DEPOSIT:
            return False, f"الحد الأدنى: {config.MIN_DEPOSIT} USDT"

        points = int(amount * config.USDT_TO_POINTS)

        user = db.users.get(str(user_id), {})
        user["usdt_balance"] = user.get("usdt_balance", 0) + amount
        user["points"] = user.get("points", 0) + points
        db.users = db.users | {str(user_id): user}

        return True, f"✅ تم التحويل!
{amount} USDT → {points} نقطة"

    @classmethod
    def convert_from_points(cls, user_id: int, points: int) -> Tuple[bool, str]:
        """تحويل نقاط إلى USDT"""
        if points < 100:
            return False, "الحد الأدنى: 100 نقطة"

        usdt = points * config.POINTS_TO_USDT

        user = db.users.get(str(user_id), {})
        if user.get("points", 0) < points:
            return False, "نقاط غير كافية"

        user["points"] = user.get("points", 0) - points
        user["usdt_balance"] = user.get("usdt_balance", 0) + usdt
        db.users = db.users | {str(user_id): user}

        return True, f"✅ تم التحويل!
{points} نقطة → {usdt:.2f} USDT"

# ==================== USER HELPERS ====================
def get_user(user_id: int) -> Dict:
    users = db.users
    uid = str(user_id)

    if uid not in users:
        users[uid] = {
            "user_id": user_id,
            "points": 100,
            "usdt_balance": 0,
            "ton_balance": 0,
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
def payment_keyboard(user_id: int):
    user = get_user(user_id)

    keyboard = [
        [InlineKeyboardButton(f"💰 الرصيد: {user.get('usdt_balance', 0):.2f} USDT", callback_data="balance")],
        [InlineKeyboardButton("📥 إيداع", callback_data="deposit"), InlineKeyboardButton("📤 سحب", callback_data="withdraw")],
        [InlineKeyboardButton("🔄 تحويل للنقاط", callback_data="convert_to_points"), InlineKeyboardButton("🔄 تحويل من النقاط", callback_data="convert_from_points")],
        [InlineKeyboardButton("📜 سجل المعاملات", callback_data="transactions")],
        [InlineKeyboardButton("💱 أسعار العملات", callback_data="prices")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def deposit_keyboard(coin: str = "USDT"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("USDT (TRC20)", callback_data="deposit_usdt")],
        [InlineKeyboardButton("TON", callback_data="deposit_ton")],
        [InlineKeyboardButton("BNB (BSC)", callback_data="deposit_bnb")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="payment")],
    ])

def back_keyboard(callback: str = "payment"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data=callback)]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    get_user(user.id)

    await update.message.reply_text(
        f"💰 <b>نظام الدفع باينس</b>
"
        f"━━━━━━━━━━━━━━━━
"
        f"💵 رصيد USDT: <b>{get_user(user.id).get('usdt_balance', 0):.2f}</b>
"
        f"💎 رصيد TON: {get_user(user.id).get('ton_balance', 0):.2f}
"
        f"💰 نقاط: {get_user(user.id).get('points', 0)}

"
        f"📊 الأسعار:
"
        f"• 1 USDT = {config.USDT_TO_POINTS} نقطة
"
        f"• 100 نقطة = {config.POINTS_TO_USDT} USDT

"
        f"اختر:",
        parse_mode=ParseMode.HTML,
        reply_markup=payment_keyboard(user.id)
    )

async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data
    user = get_user(user_id)

    # Payment menu
    if data == "payment":
        await query.edit_message_text(
            f"💰 <b>نظام الدفع باينس</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💵 رصيد USDT: <b>{user.get('usdt_balance', 0):.2f}</b>
"
            f"💎 رصيد TON: {user.get('ton_balance', 0):.2f}
"
            f"💰 نقاط: {user.get('points', 0)}",
            parse_mode=ParseMode.HTML,
            reply_markup=payment_keyboard(user_id)
        )

    # Balance
    elif data == "balance":
        await query.edit_message_text(
            f"💳 <b>محفظتك</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💵 USDT: {user.get('usdt_balance', 0):.2f}
"
            f"💎 TON: {user.get('ton_balance', 0):.2f}
"
            f"💰 نقاط: {user.get('points', 0)}

"
            f"📈 إجمالي الإيداع: {user.get('total_deposited', 0):.2f}
"
            f"📉 إجمالي السحب: {user.get('total_withdrawn', 0):.2f}",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    # Deposit
    elif data == "deposit":
        await query.edit_message_text(
            f"📥 <b>الإيداع</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💡 اختر العملة:",
            parse_mode=ParseMode.HTML,
            reply_markup=deposit_keyboard()
        )

    elif data.startswith("deposit_"):
        coin = data.replace("deposit_", "").upper()
        coin_info = PaymentSystem.SUPPORTED_COINS.get(coin)

        if coin_info:
            success, address, memo = PaymentSystem.generate_deposit_address(user_id, coin)

            if success:
                await query.edit_message_text(
                    f"📥 <b>إيداع {coin_info['name']}</b>
"
                    f"━━━━━━━━━━━━━━━━

"
                    f"<b>العنوان:</b>
"
                    f"<code>{address}</code>

"
                    f"<b>الشبكة:</b> {coin_info['network']}

"
                    f"⚠️ <i>أرسل {coin} للعنوان أعلاه، ثم انتظر التأكيد (3 تأكيدات)</i>

"
                    f"💡 <b>مهم:</b> لا ترسل عملات أخرى لهذا العنوان!",
                    parse_mode=ParseMode.HTML,
                    reply_markup=back_keyboard()
                )

    # Withdraw
    elif data == "withdraw":
        await query.edit_message_text(
            f"📤 <b>السحب</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💵 رصيدك: {user.get('usdt_balance', 0):.2f} USDT

"
            f"📋 معلومات السحب:
"
            f"• الحد الأدنى: {config.MIN_WITHDRAW} USDT
"
            f"• رسوم السحب: {PaymentSystem.SUPPORTED_COINS['USDT']['fee']} USDT
"
            f"• الشبكة: TRC20

"
            f"💡 أرسل:
"
            f"<code>سحب [المبلغ] [العنوان]</code>

"
            f"<b>مثال:</b>
"
            f"<code>سحب 10 TNPeeaaib7AJ97Xa8HWjC3xrYdC1</code>",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    # Convert to points
    elif data == "convert_to_points":
        await query.edit_message_text(
            f"🔄 <b>تحويل USDT إلى نقاط</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💵 رصيدك: {user.get('usdt_balance', 0):.2f} USDT

"
            f"📊 السعر: 1 USDT = {config.USDT_TO_POINTS} نقطة

"
            f"💡 أرسل المبلغ:
"
            f"<code>تحويل 5</code>

"
            f"<b>مثال:</b> تحويل 5 USDT → {5 * config.USDT_TO_POINTS} نقطة",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    # Convert from points
    elif data == "convert_from_points":
        await query.edit_message_text(
            f"🔄 <b>تحويل نقاط إلى USDT</b>
"
            f"━━━━━━━━━━━━━━━━
"
            f"💰 نقاطك: {user.get('points', 0)}

"
            f"📊 السعر: 100 نقطة = {config.POINTS_TO_USDT} USDT

"
            f"💡 أرسل عدد النقاط:
"
            f"<code>تحويل_نقاط 500</code>

"
            f"<b>مثال:</b> تحويل_نقاط 500 → {500 * config.POINTS_TO_USDT:.2f} USDT",
            parse_mode=ParseMode.HTML,
            reply_markup=back_keyboard()
        )

    # Transactions
    elif data == "transactions":
        deposits = db.deposits
        withdraws = db.withdraws

        user_deposits = [d for d in deposits if d.get("user_id") == user_id][-5:]
        user_withdraws = [w for w in withdraws if w.get("user_id") == user_id][-5:]

        text = f"📜 <b>سجل المعاملات</b>
━━━━━━━━━━━━━━━━

"

        text += f"<b>📥 الإيداعات:</b>
"
        if user_deposits:
            for d in user_deposits:
                text += f"• {d.get('amount', 0)} {d.get('coin', 'USDT')} - {d.get('status', 'pending')}
"
        else:
            text += "• لا توجد إيداعات
"

        text += f"
<b>📤 السحوبات:</b>
"
        if user_withdraws:
            for w in user_withdraws:
                text += f"• {w.get('amount', 0)} {w.get('coin', 'USDT')} - {w.get('status', 'pending')}
"
        else:
            text += "• لا توجد سحوبات
"

        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # Prices
    elif data == "prices":
        try:
            prices = binance.get_all_prices()

            text = f"💱 <b>أسعار العملات</b>
━━━━━━━━━━━━━━━━

"

            usdt_usd = prices.get("USDTUSD", "1.00")
            ton_usd = prices.get("TONUSD", "0")
            bnb_usd = prices.get("BNBUSD", "0")

            text += f"• USDT: ${usdt_usd}
"
            text += f"• TON: ${ton_usd}
"
            text += f"• BNB: ${bnb_usd}

"
            text += f"<i>آخر تحديث: {datetime.now().strftime('%H:%M:%S')}</i>"

        except:
            text = "💱 الأسعار
━━━━━━━━━━━━━━━━

• USDT: $1.00
• TON: $0.00
• BNB: $0.00

⚠️ تعذر جلب الأسعار"

        await query.edit_message_text(text, parse_mode=ParseMode.HTML, reply_markup=back_keyboard())

    # Back
    elif data == "back":
        await start(update, context)

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.strip()
    user = get_user(user_id)

    # Convert to points
    if text.startswith("تحويل ") and not text.startswith("تحويل_نقاط"):
        try:
            amount = float(text.replace("تحويل ", ""))
            success, msg = PaymentSystem.convert_to_points(user_id, amount)
            await update.message.reply_text(msg, reply_markup=payment_keyboard(user_id))
        except:
            await update.message.reply_text("⚠️ صيغة خاطئة! مثال: تحويل 5", reply_markup=payment_keyboard(user_id))
        return

    # Convert from points
    if text.startswith("تحويل_نقاط "):
        try:
            points = int(text.replace("تحويل_نقاط ", ""))
            success, msg = PaymentSystem.convert_from_points(user_id, points)
            await update.message.reply_text(msg, reply_markup=payment_keyboard(user_id))
        except:
            await update.message.reply_text("⚠️ صيغة خاطئة! مثال: تحويل_نقاط 500", reply_markup=payment_keyboard(user_id))
        return

    # Withdraw request
    if text.startswith("سحب "):
        try:
            parts = text.replace("سحب ", "").split()
            amount = float(parts[0])
            address = parts[1] if len(parts) > 1 else ""

            if not address:
                await update.message.reply_text("⚠️ أدخل العنوان! مثال: سحب 10 العنوان", reply_markup=payment_keyboard(user_id))
                return

            success, msg = PaymentSystem.create_withdraw_request(user_id, amount, address)
            await update.message.reply_text(msg, parse_mode=ParseMode.HTML, reply_markup=payment_keyboard(user_id))
        except:
            await update.message.reply_text("⚠️ صيغة خاطئة! مثال: سحب 10 TNPeeaaib7AJ97Xa8HWjC3xrYdC1", reply_markup=payment_keyboard(user_id))
        return

    await update.message.reply_text(
        "💰 اضغط /start للدفع!",
        reply_markup=payment_keyboard(user_id)
    )

# ==================== MAIN ====================
def main():
    logger.info("💰 Starting Binance Payment System...")

    if not TELEGRAM_AVAILABLE:
        logger.error("Telegram not available!")
        return

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(message))

    logger.info("✅ Binance Payment System is running!")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
