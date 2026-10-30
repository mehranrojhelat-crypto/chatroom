# Encrypted Chatroom

چت‌روم با رمزنگاری سمت کلاینت (AES-GCM)، ورود با رمز اتاق، PostgreSQL، Redis و Docker.

## اجرا با Docker

```bash
cp .env.example .env
# SECRET_KEY را عوض کنید
docker compose up --build
باز کنید: http://localhost:8000

اجرا محلی
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Postgres و Redis را بالا بیاورید و DATABASE_URL / REDIS_URL را تنظیم کنید
uvicorn app.main:app --reload
امنیت
رمز اتاق با bcrypt روی سرور ذخیره می‌شود.
پس از join یک JWT کوتاه‌عمر صادر می‌شود.
پیام‌ها در مرورگر با کلید مشتق‌شده از رمز اتاق (PBKDF2 → AES-GCM) رمز می‌شوند؛ سرور فقط ciphertext و IV می‌بیند.
برای تولید، HTTPS، SECRET_KEY قوی و salt اختصاصی هر اتاق را جدی بگیرید.
پاکسازی ریپو
rm -rf __pycache__ *.db
git rm -r --cached __pycache__ shortener.db 2>/dev/null || true

---

## نحوه استفاده

1. فایل‌ها را مطابق ساختار بالا جایگزین/اضافه کنید.
2. از ریشه پروژه:

```bash
docker compose up --build
پاکسازی گیت:
git rm -r --cached __pycache__ shortener.db 2>/dev/null
echo "__pycache__/" >> .gitignore
echo "*.db" >> .gitignore
برای scale افقی بعداً می‌توانید چند سرویس web با همان Redis بالا بیاورید؛ pub/sub پیام را بین instanceها پخش می‌کند.
