# CommitCraft

CommitCraft is an AI-powered Python assistant that detects Git changes, asks a GapGPT-compatible ChatGPT API for a clean commit message, commits selected files, and keeps a colorful terminal menu open for more actions.

## English

### Features

- Colorful terminal UI with `commit`, `push`, `settings`, and `exit` options.
- `commit` is the default active menu option.
- First-run configuration stored at `~/.commitcraft/config.json`.
- Separate UI language and AI commit-message language.
- Persian and English support, with English as the first-run default.
- Persian RTL shaping installed on demand through `arabic-reshaper` and `python-bidi`.
- Retry management for unstable AI responses.
- Cross-platform support for Windows, Linux, and macOS.
- Automatic dependency check and installation through `pip`.
- In-app settings editor with masked secrets, validation, reset, and instant apply.

### Requirements

- Python 3.10 or newer
- Git installed and available in `PATH`
- A GapGPT-compatible API token

### Install

```bash
python -m pip install -r requirements.txt
```

If core dependencies are missing, the script also attempts to install them automatically on startup. Persian display dependencies are installed only when Persian is selected.

### Run

```bash
python commitcraft_cli.py
```

Every run starts by asking for the working-copy folder path. This path is
mandatory and must point to an existing Git repository. CommitCraft remembers
the last successfully confirmed path in a standalone path-history file, separate
from `~/.commitcraft/config.json`, and offers it as the next run's default.

On first run, CommitCraft asks for:

- AI API token
- AI API URL
- Display language: `fa` or `en`
- AI output language for commit messages: `fa` or `en`
- Retry wait time, default `5`
- Retry attempts, default `10`

### Workflow

1. Choose `Commit changes` or press Enter.
2. Review uncommitted files.
3. All files are selected by default.
4. Enter file numbers to remove unwanted files, separated by commas.
5. Confirm the AI-generated commit message.
6. CommitCraft stages selected files and creates the commit.

The menu remains active after every commit or push. Exit only happens through the `Exit` option or `Ctrl+C`.

### Configuration

Config file:

```text
~/.commitcraft/config.json
```

Example:

```json
{
  "api_token": "YOUR_TOKEN",
  "api_url": "https://api.gapgpt.app/v1/chat/completions",
  "ui_language": "en",
  "model_output_language": "en",
  "retry_wait_seconds": 5,
  "retry_attempts": 10,
  "model": "gpt-4o-mini"
}
```

You can also choose `Settings` from the main menu to view and edit every
configuration value without opening the JSON file manually:

- API token is always masked and never printed in full.
- API URL, model name, UI language, model output language, retry wait, and retry
  attempts are individually editable.
- UI language and model output language remain independent and accept only
  Persian/`fa` or English/`en`.
- Selecting Persian installs Persian display support if it is not already available.
- Numeric values must be positive, and the API URL must be a valid HTTP(S) URL.
- Changes are saved to `~/.commitcraft/config.json` and applied immediately.
- `Cancel without saving` discards the current edit, `Reset to defaults`
  restores default values, and `Back to main menu` closes the submenu.

### Commit Message Format

The AI is instructed to return:

- First line in Conventional Commit style, such as `feat: add AI commit assistant`
- Optional body with 1-3 short bullet points when useful
- No explanations outside the commit message
- No Markdown code fences

## فارسی

کامیت‌کرفت یک دستیار پایتونی هوشمند است که تغییرات Git را تشخیص می‌دهد، آن‌ها را برای یک API سازگار با GapGPT و ChatGPT می‌فرستد، پیام کامیت مناسب می‌گیرد، فایل‌های انتخاب‌شده را stage می‌کند و عملیات commit را انجام می‌دهد.

### امکانات

- رابط ترمینالی رنگی و جذاب با گزینه‌های `commit`، `push`، `settings` و `exit`
- گزینه پیش‌فرض منو روی `commit`
- ساخت تنظیمات در اجرای اول و ذخیره در `~/.commitcraft/config.json`
- استقلال زبان رابط کاربری از زبان خروجی مدل
- پشتیبانی از فارسی و انگلیسی، با انگلیسی به‌عنوان پیش‌فرض اجرای اول
- نصب پشتیبانی نمایش راست‌به‌چپ فارسی فقط هنگام انتخاب فارسی
- تلاش مجدد هنگام پاسخ نامناسب یا خطای سرور
- پشتیبانی از Windows، Linux و macOS
- بررسی و نصب خودکار وابستگی‌ها با `pip`
- ویرایش تنظیمات داخل برنامه با مخفی‌سازی مقادیر حساس، اعتبارسنجی، بازنشانی و اعمال فوری

### پیش‌نیازها

- پایتون نسخه 3.10 یا جدیدتر
- نصب بودن Git و در دسترس بودن آن در `PATH`
- توکن API سازگار با GapGPT

### نصب

```bash
python -m pip install -r requirements.txt
```

اگر وابستگی‌های اصلی نصب نباشند، برنامه هنگام اجرا تلاش می‌کند آن‌ها را خودکار نصب کند. وابستگی‌های نمایش فارسی فقط هنگام انتخاب فارسی نصب می‌شوند.

### اجرا

```bash
python commitcraft_cli.py
```

در هر اجرا ابتدا مسیر پوشه کاری پرسیده می‌شود. این مسیر اجباری است و باید به
یک مخزن Git موجود اشاره کند. کامیت‌کرفت آخرین مسیر تأییدشده را در یک فایل
تاریخچه مستقل، جدا از `~/.commitcraft/config.json`، نگه می‌دارد و در اجرای
بعدی به‌عنوان مقدار پیش‌فرض پیشنهاد می‌دهد.

در اجرای اول این موارد پرسیده می‌شود:

- توکن API هوش مصنوعی
- آدرس API هوش مصنوعی
- زبان نمایش برنامه: `fa` یا `en`
- زبان خروجی مدل برای پیام کامیت: `fa` یا `en`
- زمان انتظار بین تلاش‌ها، پیش‌فرض `5`
- تعداد تلاش مجدد، پیش‌فرض `10`

### روند استفاده

1. گزینه `کامیت تغییرات` را انتخاب کنید یا Enter بزنید.
2. فهرست فایل‌های تغییرکرده را ببینید.
3. همه فایل‌ها به‌صورت پیش‌فرض انتخاب هستند.
4. شماره فایل‌هایی را که نمی‌خواهید کامیت شوند، با کاما وارد کنید.
5. پیام کامیت تولیدشده توسط هوش مصنوعی را تأیید کنید.
6. کامیت‌کرفت فایل‌های انتخاب‌شده را stage کرده و commit را ایجاد می‌کند.

بعد از commit یا push برنامه بسته نمی‌شود و منو فعال می‌ماند. خروج فقط با گزینه `Exit` یا `Ctrl+C` انجام می‌شود.

### تنظیمات

مسیر فایل تنظیمات:

```text
~/.commitcraft/config.json
```

نمونه:

```json
{
  "api_token": "YOUR_TOKEN",
  "api_url": "https://api.gapgpt.app/v1/chat/completions",
  "ui_language": "en",
  "model_output_language": "en",
  "retry_wait_seconds": 5,
  "retry_attempts": 10,
  "model": "gpt-4o-mini"
}
```

همچنین می‌توانید از منوی اصلی گزینه `تنظیمات` را انتخاب کنید و همه مقادیر
پیکربندی را بدون ویرایش دستی فایل JSON ببینید یا تغییر دهید:

- توکن API همیشه مخفی نمایش داده می‌شود و هیچ‌وقت کامل چاپ نمی‌شود.
- آدرس API، نام مدل، زبان رابط کاربری، زبان خروجی مدل، زمان انتظار و تعداد
  تلاش مجدد به‌صورت جداگانه قابل ویرایش هستند.
- زبان رابط کاربری و زبان خروجی مدل مستقل هستند و فقط فارسی/`fa` یا
  انگلیسی/`en` را می‌پذیرند.
- انتخاب فارسی در صورت نیاز پشتیبانی نمایش فارسی را نصب می‌کند.
- مقدارهای عددی باید مثبت باشند و آدرس API باید یک URL معتبر HTTP(S) باشد.
- تغییرات در `~/.commitcraft/config.json` ذخیره و بلافاصله در همان نشست اعمال می‌شوند.
- گزینه `لغو بدون ذخیره` ویرایش جاری را لغو می‌کند، گزینه
  `بازنشانی به پیش‌فرض‌ها` مقادیر پیش‌فرض را برمی‌گرداند و گزینه
  `بازگشت به منوی اصلی` زیرمنو را می‌بندد.

### ساختار پیام کامیت

مدل هوش مصنوعی باید این ساختار را رعایت کند:

- خط اول با قالب Conventional Commit، مثل `feat: add AI commit assistant`
- بدنه اختیاری با ۱ تا ۳ bullet کوتاه فقط در صورت نیاز
- بدون توضیح اضافه بیرون از پیام کامیت
- بدون Markdown code fence
