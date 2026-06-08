"""Translation strings and terminal text helpers."""

from __future__ import annotations

from dataclasses import dataclass


SUPPORTED_LANGUAGES = {"fa", "en"}
DEFAULT_LANGUAGE = "fa"


TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "app_title": "CommitCraft",
        "subtitle": "AI-powered Git commit assistant",
        "menu_commit": "Commit changes",
        "menu_push": "Push commits",
        "menu_settings": "Settings",
        "menu_exit": "Exit",
        "menu_prompt": "Choose an option",
        "invalid_choice": "Invalid choice. Please try again.",
        "config_missing": "Config file was not found. Let's create it.",
        "api_token": "AI API token",
        "api_url": "AI API URL",
        "ui_language": "Display language",
        "model_language": "Commit message language",
        "retry_wait": "Retry wait seconds",
        "retry_attempts": "Retry attempts",
        "leave_default": "Press Enter to use default",
        "config_saved": "Config saved successfully.",
        "dependency_check": "Checking Python dependencies...",
        "dependency_installing": "Installing missing dependencies",
        "dependency_failed": "Automatic dependency installation failed.",
        "dependency_manual": "Install manually",
        "git_not_repo": "This directory is not a Git repository.",
        "git_missing": "Git is not installed or is not available in PATH.",
        "no_changes": "No uncommitted changes found.",
        "changed_files": "Uncommitted files",
        "selection_help": "All files are selected by default. Enter numbers to remove, comma-separated, or press Enter to keep all.",
        "selected_files": "Selected files",
        "nothing_selected": "No files selected.",
        "generating": "Generating commit message with AI...",
        "ai_retry": "AI request failed. Retrying",
        "commit_message": "Generated commit message",
        "confirm_commit": "Commit with this message?",
        "committing": "Creating commit...",
        "commit_done": "Commit completed successfully.",
        "commit_failed": "Commit failed.",
        "push_confirm": "Push current branch to remote?",
        "pushing": "Pushing commits...",
        "push_done": "Push completed successfully.",
        "push_failed": "Push failed.",
        "current_branch": "Current branch",
        "press_enter": "Press Enter to continue...",
        "yes": "yes",
        "no": "no",
        "settings_title": "Current settings",
        "settings_edit": "Edit settings?",
        "ctrl_c": "Interrupted. Goodbye.",
        "error": "Error",
        "unknown": "Unknown",
    },
    "fa": {
        "app_title": "کامیت‌کرفت",
        "subtitle": "دستیار هوشمند کامیت گیت",
        "menu_commit": "کامیت تغییرات",
        "menu_push": "پوش کردن کامیت‌ها",
        "menu_settings": "تنظیمات",
        "menu_exit": "خروج",
        "menu_prompt": "یک گزینه را انتخاب کنید",
        "invalid_choice": "انتخاب نامعتبر است. دوباره تلاش کنید.",
        "config_missing": "فایل تنظیمات پیدا نشد. آن را می‌سازیم.",
        "api_token": "توکن API هوش مصنوعی",
        "api_url": "آدرس API هوش مصنوعی",
        "ui_language": "زبان نمایش",
        "model_language": "زبان پیام کامیت",
        "retry_wait": "زمان انتظار بین تلاش‌ها بر حسب ثانیه",
        "retry_attempts": "تعداد تلاش مجدد",
        "leave_default": "برای استفاده از مقدار پیش‌فرض Enter بزنید",
        "config_saved": "تنظیمات با موفقیت ذخیره شد.",
        "dependency_check": "در حال بررسی وابستگی‌های پایتون...",
        "dependency_installing": "در حال نصب وابستگی‌های نصب‌نشده",
        "dependency_failed": "نصب خودکار وابستگی‌ها ناموفق بود.",
        "dependency_manual": "دستی نصب کنید",
        "git_not_repo": "این مسیر یک مخزن Git نیست.",
        "git_missing": "Git نصب نیست یا در PATH در دسترس نیست.",
        "no_changes": "هیچ تغییر کامیت‌نشده‌ای پیدا نشد.",
        "changed_files": "فایل‌های کامیت‌نشده",
        "selection_help": "همه فایل‌ها به‌صورت پیش‌فرض انتخاب هستند. شماره فایل‌های حذفی را با کاما وارد کنید یا Enter بزنید.",
        "selected_files": "فایل‌های انتخاب‌شده",
        "nothing_selected": "هیچ فایلی انتخاب نشده است.",
        "generating": "در حال تولید پیام کامیت با هوش مصنوعی...",
        "ai_retry": "درخواست هوش مصنوعی ناموفق بود. تلاش دوباره",
        "commit_message": "پیام کامیت تولیدشده",
        "confirm_commit": "با این پیام کامیت شود؟",
        "committing": "در حال ایجاد کامیت...",
        "commit_done": "کامیت با موفقیت انجام شد.",
        "commit_failed": "کامیت ناموفق بود.",
        "push_confirm": "شاخه فعلی به ریموت پوش شود؟",
        "pushing": "در حال پوش کردن کامیت‌ها...",
        "push_done": "پوش با موفقیت انجام شد.",
        "push_failed": "پوش ناموفق بود.",
        "current_branch": "شاخه فعلی",
        "press_enter": "برای ادامه Enter بزنید...",
        "yes": "بله",
        "no": "خیر",
        "settings_title": "تنظیمات فعلی",
        "settings_edit": "تنظیمات ویرایش شود؟",
        "ctrl_c": "برنامه متوقف شد. بدرود.",
        "error": "خطا",
        "unknown": "نامشخص",
    },
}


@dataclass(frozen=True)
class Translator:
    """Small translation helper for UI strings."""

    language: str = DEFAULT_LANGUAGE

    def __post_init__(self) -> None:
        if self.language not in SUPPORTED_LANGUAGES:
            object.__setattr__(self, "language", DEFAULT_LANGUAGE)

    @property
    def is_rtl(self) -> bool:
        """Return whether current UI language is right-to-left."""

        return self.language == "fa"

    def text(self, key: str) -> str:
        """Translate a message key."""

        return TRANSLATIONS.get(self.language, TRANSLATIONS[DEFAULT_LANGUAGE]).get(
            key,
            TRANSLATIONS["en"].get(key, key),
        )


def normalize_language(value: str | None, default: str = DEFAULT_LANGUAGE) -> str:
    """Normalize a user-provided language value."""

    if not value:
        return default
    normalized = value.strip().lower()
    if normalized in {"persian", "farsi", "فارسی"}:
        return "fa"
    if normalized in {"english", "انگلیسی"}:
        return "en"
    return normalized if normalized in SUPPORTED_LANGUAGES else default
