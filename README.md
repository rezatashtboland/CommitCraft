# CommitCraft

CommitCraft is an AI-powered Python CLI for Git repositories. It detects
uncommitted changes, lets you choose what to commit, asks the active configured
AI provider for a commit message, and runs Git operations from a
colorful terminal menu.

Current version: **1.4.0**

## English

### Features

- Interactive terminal menu with commit, push, fetch, pull, sync, changelog,
  settings, and exit actions.
- Mandatory working-copy path prompt before startup, with validation against a real Git repository.
- Persistent repository path history stored separately from the main settings file.
- First-run configuration wizard stored at `~/.commitcraft/config.json`.
- Multiple AI provider profiles, including GapGPT, OpenAI, and Claude.
- One active provider at a time, with per-provider token, base URL, and model settings.
- Independent display language and commit-message language settings.
- English and Persian display support, with English as the default language.
- Persian RTL shaping installed only when Persian is selected.
- Conventional Commits mode as an AI generation style preference.
- Configurable AI-powered split flow for committing unrelated selected files as separate commits.
- In-app working-copy switching with immediate Git repository validation.
- Git fetch, pull, and sync retries for transient network failures.
- Pull strategy setting for merge or rebase.
- Optional auto-stash during pull and sync, including untracked files.
- Daily UTF-8 log files with configurable `INFO`, `ERROR`, or `DEBUG` detail.
- Incremental `CHANGELOG.md` generator based on Git commit history.
- In-app settings editor with masked API token, validation, reset, and immediate apply.
- Safe Git staging for deleted files by using `git rm --ignore-unmatch`.
- Captured subprocess output decoded safely to avoid crashes on malformed text.

### Requirements

- Python 3.10 or newer
- Git installed and available in `PATH`
- An API token for at least one supported provider
- Network access to the configured AI API URL
- Optional Git remote/upstream configuration for push, fetch, pull, and sync

Runtime Python dependencies:

```text
requests>=2.31.0
rich>=13.7.0
```

Optional Persian display dependencies:

```text
python-bidi>=0.4.2
arabic-reshaper>=3.0.0
```

### Installation

Install dependencies from the repository:

```bash
python -m pip install -r requirements.txt
```

You can also install the project in editable mode to use the `commitcraft`
console command defined by `pyproject.toml`:

```bash
python -m pip install -e .
```

If core dependencies are missing at startup, CommitCraft attempts to install
them automatically with the current Python executable. Persian display
dependencies are checked and installed only when Persian is selected.

### How To Run

Run from the repository checkout:

```bash
python commitcraft_cli.py
```

If installed as a package:

```bash
commitcraft
```

At startup, CommitCraft asks for the working-copy folder path. The path is
required, must exist, must be a directory, and must be inside a Git working
tree. The last confirmed path is appended to:

```text
~/.commitcraft/last_repository_paths.log
```

When the stored path is still valid, it is offered as the next run's default.

### Main Menu

The interactive menu accepts these options:

| Option | Action |
| --- | --- |
| `1` or Enter | Commit changes |
| `2` | Push commits |
| `3` | Fetch from remote |
| `4` | Pull from remote |
| `5` | Sync with remote |
| `6` | Generate changelog |
| `7` | Settings |
| `0` | Exit |

The default menu choice is `1`.

### Commit Workflow

1. Choose `Commit changes` or press Enter.
2. Review the table of uncommitted files and Git status codes.
3. Press Enter to keep all files selected, or enter comma-separated file numbers to remove.
4. If automatic commit splitting is enabled, review AI-identified logical commit groups.
5. CommitCraft stages the selected files.
6. CommitCraft sends the staged diff and staged file status to the AI.
7. Review the generated message and edit it inline if needed.
8. Confirm the final message to create the commit.

For deleted paths, CommitCraft stages with `git rm --ignore-unmatch` instead
of `git add` to avoid pathspec errors.

### Git Remote Workflows

- `Push commits` shows the current branch, asks for confirmation, and runs `git push`.
  If the branch has no upstream, CommitCraft runs `git push --set-upstream origin <branch>`.
- `Fetch from remote` shows the current branch, asks for confirmation, and runs `git fetch --prune`.
- `Pull from remote` runs `git pull --no-rebase` or `git pull --rebase` based on settings.
- `Sync with remote` runs the configured pull operation first, then `git push`
  after a successful pull.

The pull strategy setting defaults to merge. First-run setup and the settings
menu show a numbered list: choose `1` for merge or `2` for rebase. Press Enter
to keep the default or current strategy.

Pull and sync first verify that the repository has at least one commit and that
the current branch has an upstream. In a fresh repository with no commits or no
tracking branch, CommitCraft shows a clear message and returns to the menu
without running `git pull`.

Fetch, pull, and sync retry only retryable transport failures, such as DNS,
timeout, connection reset, TLS/SSL, and HTTP 5xx failures. Authentication
errors and merge/rebase/stash conflicts are reported without retrying.

When Git fails, CommitCraft shows the classified cause when recognized, plus
the exit code, command, and captured Git output. Push errors distinguish common
cases such as missing upstream, authentication failure, and non-fast-forward
rejection.

When auto-stash is enabled and local changes exist, pull and sync create a
`CommitCraft auto-stash` with `--include-untracked` and restore it after the
integration operation if the repository is not left in a merge or rebase state.

### Logging

CommitCraft writes diagnostic logs separately from the terminal UI. Logs use
UTF-8 and one file per day:

```text
~/.commitcraft/logs/commitcraft-YYYY-MM-DD.log
```

The default log level is `INFO`. Change `Log level` in settings to `INFO`,
`ERROR`, or `DEBUG`; the choice is persisted in `~/.commitcraft/config.json`.
`DEBUG` includes Git command details, exit codes, stdout, and stderr.

### Changelog Generator

Choose `Generate changelog` from the main menu to create or continue
`CHANGELOG.md` in the selected repository root.

The changelog generator:

- Creates `CHANGELOG.md` with a Keep a Changelog-style introduction when missing.
- Uses SemVer version headings with the current app version and current date.
- Reads commits after the last CommitCraft-generated changelog marker.
- Adds only commits that are not already represented in the changelog.
- Groups entries into standard categories such as Added, Changed, Fixed,
  Documentation, Tests, Build, and Chore.
- Keeps hidden commit markers in the file so later runs continue incrementally.

Example generated section:

```markdown
## [1.2.0] - 2026-06-16

### Added
- Add changelog generator (`abc1234`)
```

### Settings

Settings are stored in:

```text
~/.commitcraft/config.json
```

Current default-backed config shape:

```json
{
  "providers": {
    "GapGPT": {
      "name": "GapGPT",
      "provider_type": "openai",
      "api_token": "YOUR_TOKEN",
      "api_url": "https://api.gapgpt.app/v1/chat/completions",
      "model": "gpt-4o-mini"
    }
  },
  "active_provider": "GapGPT",
  "ui_language": "en",
  "model_output_language": "en",
  "retry_wait_seconds": 5,
  "retry_attempts": 10,
  "conventional_commits": true,
  "pull_strategy": "merge",
  "auto_stash": true,
  "auto_split_commits": false,
  "log_level": "INFO"
}
```

On first run, CommitCraft asks for:

- GapGPT API token
- GapGPT API URL, defaulting to `https://api.gapgpt.app/v1/chat/completions`
- GapGPT model name
- Display language, `English` or `Persian`
- Commit message language, `English` or `Persian`
- Retry wait seconds, default `5`
- Retry attempts, default `10`
- Conventional Commits mode, default `yes`
- Pull strategy, default `merge`
- Auto-stash, default `yes`
- Automatic commit splitting, default `no`

The Settings menu can edit:

- Add or update AI provider profiles
- Switch the active AI provider
- Model name for the active provider
- Display language
- Commit message language
- Retry wait seconds
- Retry attempts
- Conventional Commits mode
- Automatic commit splitting
- Pull strategy
- Auto-stash
- Working copy path

Validation rules:

- Provider names, API tokens, and model names cannot be empty.
- Provider type must be `openai` or `anthropic`.
- API URL must be a valid HTTP or HTTPS URL.
- Languages must be English or Persian.
- Retry values must be positive integers.
- Boolean values accept yes/no-like values, including English and Persian forms.
- Pull strategy must be `merge` or `rebase`.
- API token is masked in the settings table and is never printed in full.

Legacy configs with top-level `api_token`, `api_url`, and `model` are migrated
automatically into an active `GapGPT` provider profile when loaded.

Provider examples:

```json
{
  "OpenAI": {
    "name": "OpenAI",
    "provider_type": "openai",
    "api_token": "OPENAI_TOKEN",
    "api_url": "https://api.openai.com/v1/chat/completions",
    "model": "gpt-4o-mini"
  },
  "Claude": {
    "name": "Claude",
    "provider_type": "anthropic",
    "api_token": "ANTHROPIC_TOKEN",
    "api_url": "https://api.anthropic.com/v1/messages",
    "model": "claude-3-5-sonnet-latest"
  }
}
```

Choose `Settings`, then `Add or update AI provider` to create or update a
provider profile. Choose `Active AI provider` to switch between configured
providers. The settings table shows which provider is active.

Choose `Settings`, then `Working copy` to change repositories while the app is
running. The new path must exist, must be a directory, and must be inside a Git
working tree. After validation, it becomes active immediately and is saved to
the separate working-copy history file.

When `Automatic commit splitting` is enabled, CommitCraft asks the active AI
provider to group selected files into logical commits. The app shows how many
groups were identified and asks before proceeding. Each group is staged and
committed separately with its own generated message. When the setting is
disabled, all selected files are committed together.

The settings submenu also includes reset to defaults, cancel without saving,
and back to main menu actions.

### Commit Message Style

When Conventional Commits mode is enabled, the AI is prompted to prefer:

- A first line like `type(scope): description`, `type: description`, or a `!` breaking form.
- One of these types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`,
  `test`, `build`, `ci`, `chore`, `revert`.
- A short lowercase scope inferred from the staged diff when useful.
- An imperative, present-tense description when useful.
- Optional body or footer when useful.
- No Markdown code fences and no explanation outside the commit message.

When Conventional Commits mode is disabled, the AI is prompted for one concise
free-form commit message in the configured commit-message language.

CommitCraft does not reject user-edited commit messages for length or format.
After review, users can commit any message text accepted by Git.

### Usage Examples

Run the local script:

```bash
python commitcraft_cli.py
```

Install and run the console command:

```bash
python -m pip install -e .
commitcraft
```

Example commit flow input:

```text
Working copy folder path: /path/to/repo
Choose an option [1]: 1
Remove []: 2,4
Split unrelated changes into separate commits? [no]: no
Edit commit message, or press Enter to keep it:
Commit with this message? [yes]: yes
```

## فارسی

کامیت‌کرفت یک ابزار خط فرمان پایتونی برای مخزن‌های Git است. این برنامه
تغییرات کامیت‌نشده را پیدا می‌کند، اجازه می‌دهد فایل‌های کامیت را انتخاب
کنید، از یک API سازگار با GapGPT برای پیام کامیت کمک می‌گیرد و عملیات Git را
از یک منوی ترمینالی رنگی اجرا می‌کند.

نسخه فعلی: **1.4.0**

### امکانات

- منوی تعاملی ترمینال با عملیات commit، push، fetch، pull، sync، changelog،
  settings و exit.
- دریافت اجباری مسیر پوشه کاری پیش از شروع و اعتبارسنجی آن به‌عنوان مخزن Git.
- ذخیره تاریخچه مسیر پوشه کاری جدا از فایل تنظیمات اصلی.
- ساخت تنظیمات اجرای اول در `~/.commitcraft/config.json`.
- پشتیبانی از چند ارائه‌دهنده هوش مصنوعی، شامل GapGPT، OpenAI و Claude.
- فعال بودن تنها یک ارائه‌دهنده در هر لحظه، با توکن، نشانی و مدل جداگانه برای هرکدام.
- جدایی زبان نمایش برنامه از زبان پیام کامیت.
- پشتیبانی از نمایش انگلیسی و فارسی، با انگلیسی به‌عنوان پیش‌فرض.
- نصب وابستگی‌های نمایش راست‌به‌چپ فارسی فقط هنگام انتخاب فارسی.
- حالت Conventional Commits به‌عنوان ترجیح سبک تولید پیام توسط AI.
- تقسیم خودکار تغییرات نامرتبط به چند commit منطقی با کمک هوش مصنوعی.
- تغییر پوشه کاری از داخل تنظیمات با اعتبارسنجی فوری مخزن Git.
- تلاش مجدد برای fetch، pull و sync فقط در خطاهای موقت شبکه.
- تنظیم روش pull بین merge و rebase.
- auto-stash اختیاری هنگام pull و sync، همراه با فایل‌های untracked.
- فایل‌های log روزانه با UTF-8 و سطح قابل تنظیم `INFO`، `ERROR` یا `DEBUG`.
- تولید افزایشی `CHANGELOG.md` بر اساس تاریخچه commit.
- ویرایش تنظیمات داخل برنامه با مخفی‌سازی توکن، اعتبارسنجی، بازنشانی و اعمال فوری.
- stage کردن امن فایل‌های حذف‌شده با `git rm --ignore-unmatch`.

### پیش‌نیازها

- Python نسخه 3.10 یا جدیدتر
- Git نصب‌شده و قابل دسترس در `PATH`
- توکن API برای حداقل یکی از ارائه‌دهنده‌های پشتیبانی‌شده
- دسترسی شبکه به آدرس API تنظیم‌شده
- تنظیم بودن remote/upstream برای عملیات push، fetch، pull و sync

### نصب

```bash
python -m pip install -r requirements.txt
```

برای استفاده از دستور `commitcraft` می‌توانید پروژه را به‌صورت editable نصب کنید:

```bash
python -m pip install -e .
```

اگر وابستگی‌های اصلی هنگام شروع برنامه نصب نباشند، برنامه تلاش می‌کند آن‌ها
را با همان Python جاری نصب کند. وابستگی‌های نمایش فارسی فقط هنگام انتخاب
فارسی بررسی و نصب می‌شوند.

### اجرا

```bash
python commitcraft_cli.py
```

یا پس از نصب بسته:

```bash
commitcraft
```

در شروع برنامه، مسیر پوشه کاری پرسیده می‌شود. این مسیر باید وجود داشته باشد،
پوشه باشد و داخل یک working tree گیت باشد. آخرین مسیر معتبر در فایل زیر ذخیره
می‌شود:

```text
~/.commitcraft/last_repository_paths.log
```

### منوی اصلی

| گزینه | عملیات |
| --- | --- |
| `1` یا Enter | کامیت تغییرات |
| `2` | پوش کردن کامیت‌ها |
| `3` | fetch از remote |
| `4` | pull از remote |
| `5` | sync با remote |
| `6` | تولید changelog |
| `7` | تنظیمات |
| `0` | خروج |

گزینه پیش‌فرض منو `1` است.

### روند کامیت

1. گزینه commit را انتخاب کنید یا Enter بزنید.
2. فایل‌های تغییرکرده و وضعیت Git آن‌ها را ببینید.
3. برای انتخاب همه فایل‌ها Enter بزنید یا شماره فایل‌های حذفی را با کاما وارد کنید.
4. اگر تقسیم خودکار کامیت فعال باشد، گروه‌های منطقی تشخیص‌داده‌شده توسط AI را بررسی کنید.
5. برنامه فایل‌های انتخاب‌شده را stage می‌کند.
6. diff آماده‌شده برای تولید پیام کامیت به AI فرستاده می‌شود.
7. پیام تولیدشده را بررسی و در صورت نیاز ویرایش کنید.
8. پیام نهایی را تأیید کنید تا commit ساخته شود.

### عملیات Remote

- push شاخه فعلی را پس از تأیید با `git push` ارسال می‌کند. اگر شاخه بالادستی
  نداشته باشد، CommitCraft دستور `git push --set-upstream origin <branch>` را اجرا می‌کند.
- fetch پس از تأیید `git fetch --prune` را اجرا می‌کند.
- pull بسته به تنظیمات با merge یا rebase اجرا می‌شود.
- sync ابتدا pull تنظیم‌شده را اجرا می‌کند و پس از موفقیت، `git push` می‌زند.

روش pull به‌صورت پیش‌فرض merge است. هنگام راه‌اندازی اولیه و در منوی تنظیمات،
فهرست شماره‌دار نمایش داده می‌شود: برای merge عدد `1` و برای rebase عدد `2`
را انتخاب کنید. با زدن Enter مقدار پیش‌فرض یا مقدار فعلی حفظ می‌شود.

پیش از pull و sync بررسی می‌شود که مخزن حداقل یک commit داشته باشد و شاخه فعلی
شاخه بالادستی داشته باشد. در مخزن تازه بدون commit یا بدون شاخه tracking،
CommitCraft پیام روشن نمایش می‌دهد و بدون اجرای `git pull` به منو برمی‌گردد.

اگر Git ناموفق شود، CommitCraft در صورت تشخیص علت، پیام روشن نمایش می‌دهد و
کد خروج، فرمان اجراشده و خروجی ثبت‌شده Git را نشان می‌دهد. خطاهای push برای
موارد رایج مثل نبود upstream، مشکل احراز هویت و رد شدن non-fast-forward
جداگانه توضیح داده می‌شوند.

### ثبت رویداد

CommitCraft لاگ‌های عیب‌یابی را جدا از خروجی ترمینال می‌نویسد. فایل‌ها UTF-8
هستند و برای هر روز یک فایل ساخته می‌شود:

```text
~/.commitcraft/logs/commitcraft-YYYY-MM-DD.log
```

سطح پیش‌فرض `INFO` است. در تنظیمات می‌توانید `Log level` را به `INFO`،
`ERROR` یا `DEBUG` تغییر دهید؛ این مقدار در `~/.commitcraft/config.json`
ذخیره می‌شود. سطح `DEBUG` جزئیات فرمان Git، کد خروج، stdout و stderr را ثبت می‌کند.

### تولید Changelog

با گزینه تولید changelog در منوی اصلی، فایل `CHANGELOG.md` در ریشه مخزن
انتخاب‌شده ساخته یا ادامه داده می‌شود.

این قابلیت:

- اگر فایل وجود نداشته باشد، قالب اولیه سازگار با Keep a Changelog می‌سازد.
- برای نسخه فعلی برنامه heading نسخه SemVer همراه با تاریخ روز می‌نویسد.
- commitهای بعد از آخرین marker تولیدشده توسط CommitCraft را می‌خواند.
- فقط commitهایی را اضافه می‌کند که قبلاً در changelog ثبت نشده‌اند.
- ورودی‌ها را در دسته‌هایی مثل Added، Changed، Fixed، Documentation، Tests،
  Build و Chore گروه‌بندی می‌کند.
- markerهای مخفی commit را نگه می‌دارد تا اجرای بعدی افزایشی ادامه پیدا کند.

نمونه خروجی:

```markdown
## [1.2.0] - 2026-06-16

### Added
- Add changelog generator (`abc1234`)
```

### تنظیمات

فایل تنظیمات:

```text
~/.commitcraft/config.json
```

نمونه ساختار فعلی:

```json
{
  "providers": {
    "GapGPT": {
      "name": "GapGPT",
      "provider_type": "openai",
      "api_token": "YOUR_TOKEN",
      "api_url": "https://api.gapgpt.app/v1/chat/completions",
      "model": "gpt-4o-mini"
    }
  },
  "active_provider": "GapGPT",
  "ui_language": "en",
  "model_output_language": "en",
  "retry_wait_seconds": 5,
  "retry_attempts": 10,
  "conventional_commits": true,
  "pull_strategy": "merge",
  "auto_stash": true,
  "auto_split_commits": false,
  "log_level": "INFO"
}
```

تنظیمات قابل ویرایش شامل افزودن یا به‌روزرسانی ارائه‌دهنده‌های AI، تغییر
ارائه‌دهنده فعال، نام مدل ارائه‌دهنده فعال، زبان نمایش، زبان پیام کامیت، زمان
انتظار تلاش مجدد، تعداد تلاش مجدد، حالت Conventional Commits، تقسیم خودکار
کامیت‌ها، روش pull، auto-stash، سطح log و پوشه کاری است. توکن در جدول تنظیمات مخفی
نمایش داده می‌شود.

تنظیمات قدیمی با `api_token`، `api_url` و `model` به‌صورت خودکار به پروفایل
فعال `GapGPT` مهاجرت می‌کنند. برای تغییر مخزن در زمان اجرا، از گزینه پوشه
کاری در Settings استفاده کنید؛ مسیر جدید باید وجود داشته باشد و داخل مخزن Git
باشد. اگر تقسیم خودکار کامیت‌ها فعال باشد، برنامه گروه‌های منطقی تشخیص‌داده‌شده
را نمایش می‌دهد و پیش از ساخت چند کامیت جدا تأیید می‌گیرد.

### سبک پیام کامیت

در حالت Conventional Commits، از AI خواسته می‌شود پیام را ترجیحاً با یکی از
نوع‌های `feat`، `fix`، `docs`، `style`، `refactor`، `perf`، `test`، `build`،
`ci`، `chore` یا `revert` تولید کند. این فقط ترجیح تولید پیام است و برنامه
پیام ویرایش‌شده کاربر را به‌خاطر طول یا قالب رد نمی‌کند. پس از بررسی، هر پیام
قابل قبول برای Git می‌تواند commit شود.
