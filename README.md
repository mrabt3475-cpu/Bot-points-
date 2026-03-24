# Enhanced Crypto Wallet Bot

🤖 بوت محفظة إلكترونية محسن

## الميزات الجديدة

### 💰 المحفظة الإلكترونية
- إيداع USDT عبر باينس
- سحب إلى محفظة خارجية
- تحويل بين المستخدمين
- سجل معاملات كامل

### ⭐ نظام النقاط والمستويات
- 100 نقطة لكل USDT
- 6 مستويات: NEW → BRONZE → SILVER → GOLD → PLATINUM → DIAMOND
- bonus إيداع حسب المستوى (2% - 20%)

### 🔗 نظام الإحالة
- 20 نقطة لكل إحالة
- 10% من إيداعات المُحالين

### 🔐 الأمان
- حدود سحب يومية
- التحقق من الهوية
- رقم PIN
- تشفير البيانات

### 👑 لوحة الأدمن
- إحصائيات شاملة
- إدارة المستخدمين
- مراقبة المعاملات

## الأوامر
- /start - بدء البوت
- /balance - عرض الرصيد
- /deposit - إيداع
- /withdraw - سحب
- /transfer - تحويل
- /referral - الإحالة
- /transactions - المعاملات
- /settings - الإعدادات
- /admin - لوحة الأدمن

## التشغيل
```bash
pip install -r requirements.txt
python bot.py
```

## الإعدادات
عدل ملف `.env`:
```
BOT_TOKEN=your_token
BINANCE_API_KEY=your_api_key
BINANCE_SECRET_KEY=your_secret_key
```
