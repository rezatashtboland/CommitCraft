# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-06-16
### Added
- اضافه کردن دستیار کامیت هوش مصنوعی CommitCraft (`9a956ca`) <!-- commitcraft:entry=9a956ca386fb058059022cbb450b1fc815e309af -->
- افزودن منوی تنظیمات تعاملی با اعتبارسنجی - تعریف SettingsOption و SETTINGS_OPTIONS و افزودن منوی تنظیمات - پیاده‌سازی عملیات ویرایش، ریست و ذخیره تنظیمات با اعتبارسنجی - اعتبارسنجی توکن/API URL/زبان و پوشش ماسک مقادیر حساس (`399566c`) <!-- commitcraft:entry=399566cbc880847872ba9a22843f86ff4aff49e7 -->
- افزودن درخواست مسیر پوشه کاری و ذخیره آن برای اجرای بعدی - افزودن prompt برای مسیر پوشه کاری پیش از سایر کارها در CLI - ذخیره و بازگردانی آخرین مسیر تأییدشده در فایل جدا از پیکربندی کاربر - استفاده از مسیر مخزن در App و GitService برای کار با مخزن مشخص (`12b536c`) <!-- commitcraft:entry=12b536cc5fec83780a1675b44c1a9d03e7f545c4 -->
- Update Persian language support and improve dependency management (`4b01967`) <!-- commitcraft:entry=4b019677ccc9b5b3377c68ac86c705a7a623bed0 -->
- مدیریت زبان جلسه‌ای UI با بررسی وابستگی‌های فارسی (`5d84ecd`) <!-- commitcraft:entry=5d84ecd812e709e0a16309c6645c673a41aa678e -->
- افزودن پشتیبانی از Conventional Commits (`447773c`) <!-- commitcraft:entry=447773ce43547b4cdcd8179dfb9023a1c22de00f -->
- افزود fetch، pull و sync با استراتژی قابل تنظیم (`60f6b30`) <!-- commitcraft:entry=60f6b309cec61f9968d5ec70e5f68c1716ba47ce -->
- افزودن کلیدهای ترجمه برای منوی کشویی (`6d47765`) <!-- commitcraft:entry=6d4776589b949bdb558819a4fcd9b54dcb95b063 -->
- ایجاد قابلیت تولید changelog از تاریخچه گیت (`0bb824f`) <!-- commitcraft:entry=0bb824f88abbdc1e9be79202632f6a12213936f1 -->

### Changed
- بهبود پیاده‌سازی وضعیت تغییرات با _status_entries - استفاده از _status_entries به جای پردازش خروجی 'git status' - افزودن _split_deleted_files و مدیریت حذف‌ها در diff - بهبود استخراج فایل‌های untracked با _status_entries (`121c7f6`) <!-- commitcraft:entry=121c7f656b0e08e4a040d2490db109982ad18653 -->

### Documentation
- افزودن AGENTS.md با دستورالعمل‌های هوش مصنوعی (`76c9ebd`) <!-- commitcraft:entry=76c9ebd47c038d90aebbe818e30f96549ca735d1 -->
- به‌روزرسانی مستندات README و AGENTS (`c54e6d0`) <!-- commitcraft:entry=c54e6d0b29fe052419e4aef7f837e027714939c6 -->

<!-- commitcraft:last-commit=0bb824f88abbdc1e9be79202632f6a12213936f1 -->
