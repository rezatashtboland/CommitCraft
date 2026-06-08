# CommitCraft

CommitCraft is an AI-powered Python assistant that detects Git changes, asks a GapGPT-compatible ChatGPT API for a clean commit message, commits selected files, and keeps a colorful terminal menu open for more actions.

## English

### Features

- Colorful terminal UI with `commit`, `push`, and `exit` options.
- `commit` is the default active menu option.
- First-run configuration stored at `~/.commitcraft/config.json`.
- Separate UI language and AI commit-message language.
- Persian and English support, with Persian as the default.
- Persian RTL shaping through `arabic-reshaper` and `python-bidi`.
- Retry management for unstable AI responses.
- Cross-platform support for Windows, Linux, and macOS.
- Automatic dependency check and installation through `pip`.

### Requirements

- Python 3.10 or newer
- Git installed and available in `PATH`
- A GapGPT-compatible API token

### Install

```bash
python -m pip install -r requirements.txt
```

If dependencies are missing, the script also attempts to install them automatically on startup. If that fails, it prints each package name, minimum version, and manual install command.

### Run

```bash
python commitcraft_cli.py
```

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
  "ui_language": "fa",
  "model_output_language": "fa",
  "retry_wait_seconds": 5,
  "retry_attempts": 10,
  "model": "gpt-4o-mini"
}
```

### Commit Message Format

The AI is instructed to return:

- First line in Conventional Commit style, such as `feat: add AI commit assistant`
- Optional body with 1-3 short bullet points when useful
- No explanations outside the commit message
- No Markdown code fences

## فارسی

کامیت‌کرفت یک دستیار پایتونی هوشمند است که تغییرات Git را تشخیص می‌دهد، آن‌ها را برای یک API سازگار با GapGPT و ChatGPT می‌فرستد، پیام کامیت مناسب می‌گیرد، فایل‌های انتخاب‌شده را stage می‌کند و عملیات commit را انجام می‌دهد.

### امکانات

- رابط ترمینالی رنگی و جذاب با گزینه‌های `commit`، `push` و `exit`
- گزینه پیش‌فرض منو روی `commit`
- ساخت تنظیمات در اجرای اول و ذخیره در `~/.commitcraft/config.json`
- استقلال زبان رابط کاربری از زبان خروجی مدل
- پشتیبانی از فارسی و انگلیسی، با فارسی به‌عنوان پیش‌فرض
- پشتیبانی از نمایش راست‌به‌چپ فارسی با `arabic-reshaper` و `python-bidi`
- تلاش مجدد هنگام پاسخ نامناسب یا خطای سرور
- پشتیبانی از Windows، Linux و macOS
- بررسی و نصب خودکار وابستگی‌ها با `pip`

### پیش‌نیازها

- پایتون نسخه 3.10 یا جدیدتر
- نصب بودن Git و در دسترس بودن آن در `PATH`
- توکن API سازگار با GapGPT

### نصب

```bash
python -m pip install -r requirements.txt
```

اگر وابستگی‌ها نصب نباشند، برنامه هنگام اجرا تلاش می‌کند آن‌ها را خودکار نصب کند. اگر نصب خودکار ناموفق باشد، نام پکیج، نسخه موردنیاز و دستور نصب دستی نمایش داده می‌شود.

### اجرا

```bash
python commitcraft_cli.py
```

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
  "ui_language": "fa",
  "model_output_language": "fa",
  "retry_wait_seconds": 5,
  "retry_attempts": 10,
  "model": "gpt-4o-mini"
}
```

### ساختار پیام کامیت

مدل هوش مصنوعی باید این ساختار را رعایت کند:

- خط اول با قالب Conventional Commit، مثل `feat: add AI commit assistant`
- بدنه اختیاری با ۱ تا ۳ bullet کوتاه فقط در صورت نیاز
- بدون توضیح اضافه بیرون از پیام کامیت
- بدون Markdown code fence
