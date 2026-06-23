# animeiat-cli

<p align="center">
  <strong>العربية</strong> &nbsp;|&nbsp; <a href="README.md">English</a>
</p>

> هذه الترجمة العربية لأغراض المساعدة. النسخة الإنجليزية هي المرجع الرسمي.

تطبيق طرفية (Terminal) للبحث عن حلقات الأنمي وتشغيلها من مصادر متعددة على الويب.

![License](https://img.shields.io/github/license/PanDuroDev/animeiat_cli?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey?style=for-the-badge)

## المحتويات

- [للمستخدم النهائي](#للمستخدم-النهائي)
  - [ماذا يفعل التطبيق](#ماذا-يفعل-التطبيق)
  - [قبل البدء](#قبل-البدء)
  - [التثبيت السريع](#التثبيت-السريع)
  - [كيفية الاستخدام](#كيفية-الاستخدام)
  - [حل المشكلات الشائعة](#حل-المشكلات-الشائعة)
- [للمطورين](#للمطورين)
  - [المتطلبات](#المتطلبات)
  - [طريقة التثبيت](#طريقة-التثبيت)
  - [دليل الأوامر (CLI)](#دليل-الأوامر-cli)
  - [الإعدادات (Configuration)](#الإعدادات-configuration)
  - [هيكل المشروع](#هيكل-المشروع)
  - [المساهمة](#المساهمة)
- [الرخصة](#الرخصة)

---

## للمستخدم النهائي

### ماذا يفعل التطبيق

animeiat-cli هو برنامج يعمل في الطرفية (Terminal) الخاصة بجهازك. يتيح لك البحث عن الأنمي، تصفح قوائم الحلقات، وتشغيلها مباشرة في مشغل الفيديو المفضل لديك — دون الحاجة إلى فتح متصفح أو التعامل مع الإعلانات.

الإمكانيات الرئيسية:

- البحث عن الأنمي بالاسم عبر عدة مواقع مصدر.
- تصفح قوائم الحلقات باستخدام أزرار لوحة المفاتيح.
- تشغيل الحلقات مباشرة في VLC أو MPV أو أي مشغل آخر مثبت.
- استئناف المشاهدة من حيث توقفت — يتم حفظ سجل المشاهدة محليًا.
- حفظ العروض المفضلة أو تحميل الحلقات للمشاهدة دون اتصال.
- جميع البيانات تبقى على جهازك. لا حاجة لحساب أو تسجيل.

### قبل البدء

يجب أن يتوفر لديك:

- **جهاز كمبيوتر** يعمل بنظام Windows أو macOS أو Linux.
- **Python** إصدار 3.10 أو أحدث مثبت على نظامك.
- **مشغل فيديو** مثل VLC أو MPV. سيكتشفه التطبيق تلقائيًا.
- **متصفح Chrome أو Edge** (اختياري) — يُستخدم فقط لاستخراج الكوكيز (cookies) للوصول إلى مصادر الأنمي. التطبيق لا يقرأ أي بيانات شخصية.

إذا لم تكن متأكدًا من كيفية تثبيت Python، حمّله من [python.org](https://www.python.org/downloads/) وحدد "Add Python to PATH" أثناء التثبيت على Windows، أو استخدم مدير الحزم الخاص بنظامك على macOS/Linux.

### التثبيت السريع

1. **ثبّت Python ومشغل الفيديو** (انظر [قبل البدء](#قبل-البدء) أعلاه).

2. **حمّل المشروع.** انقر على الزر الأخضر "Code" في [صفحة GitHub](https://github.com/PanDuroDev/animeiat_cli) واختر "Download ZIP"، ثم فك الضغط. أو استخدم Git:

   ```bash
   git clone https://github.com/PanDuroDev/animeiat_cli.git
   cd animeiat_cli
   ```

3. **ثبّت حزم Python المطلوبة.** افتح الطرفية (Command Prompt على Windows، Terminal على macOS/Linux) في مجلد المشروع وشغّل:

   ```bash
   pip install -r requirements.txt
   ```

   إذا فشل الأمر، جرب `pip3` بدل `pip`، أو شغّل `python -m pip install -r requirements.txt`.

4. **ثبّت مكون المتصفح Playwright** (ضروري للوصول إلى مصادر الأنمي عبر الكوكيز):

   ```bash
   playwright install chromium
   ```

   على Linux قد تحتاج تشغيل `playwright install --with-deps chromium` لتثبيت مكتبات النظام.

5. **شغّل التطبيق:**

   ```bash
   python anime_cli.py
   ```

   استخدم `python3` على macOS و Linux إذا لم يعمل `python`.

سيحاول التطبيق تثبيت أي تبعيات مفقودة تلقائيًا عند أول تشغيل. إذا نجح `playwright install chromium`، فكل شيء جاهز.

#### باستخدام Docker

إذا كان Docker مثبتًا على جهازك، يمكنك تخطي الإعداد اليدوي:

```bash
docker build -t animeiat-cli .
docker run -it animeiat-cli
```

### كيفية الاستخدام

شغّل `python anime_cli.py` لبدء الواجهة التفاعلية (TUI).

القائمة الرئيسية تعرض هذه الخيارات:

- **Search** (بحث) — اكتب اسم أنمي للبحث عبر المصادر المتاحة.
- **URL** (رابط) — الصق رابطًا مباشرًا من أحد المصادر المدعومة.
- **Favorites** (المفضلة) — تصفح العروض التي حفظتها.
- **Continue Watching** (متابعة المشاهدة) — استأنف عرضًا بدأته.
- **Download Manager** (مدير التحميل) — إدارة التحميلات المعلقة.
- **Settings** (الإعدادات) — تغيير المشغل، الجودة، المظهر، والمزيد.
- **Exit** (خروج) — إنهاء التطبيق.

استخدم أزرار الأسهم (أعلى/أسفل) للتنقل في القوائم واضغط Enter للاختيار. اضغط `d` لإظهار لوحة التفاصيل على الجانب الأيمن. اضغط `Esc` للرجوع و `q` للخروج.

#### وضع عدم التفاعل (Non-interactive)

يمكنك استخدام التطبيق بدون الواجهة التفاعلية:

```bash
# تشغيل رابط معين مباشرة
python anime_cli.py --url https://example.com/anime/... --no-tui

# عرض الحلقات بصيغة JSON
python anime_cli.py --url https://... --list-episodes --json

# إضافة حلقة لقائمة التحميل
python anime_cli.py --url https://... --download

# عرض الإصدار
python anime_cli.py --version
```

### حل المشكلات الشائعة

| المشكلة | السبب المحتمل | الحل |
|---------|---------------|------|
| "pip is not recognized" (pip غير معروف) | Python غير مضاف إلى PATH | أعد تثبيت Python وحدد "Add Python to PATH". أعد تشغيل الطرفية. |
| فشل الأمر `playwright install chromium` | مكتبات نظام مفقودة (Linux) | شغّل `playwright install --with-deps chromium` بدلًا منه. |
| "No player found" (لم يتم العثور على مشغل) | VLC أو MPV غير مثبت | ثبّت أحد المشغلين المدعومين. انظر [قبل البدء](#قبل-البدء). |
| التطبيق يفتح لكن لا توجد نتائج بحث | كوكيز المتصفح غير متوفرة | يحتاج التطبيق لكوكيز من Chrome أو Edge. افتح المتصفح، زر موقع المصدر مرة، ثم أعد تشغيل التطبيق. |
| الواجهة تبدو مشوشة أو غير محاذاة | خط الطرفية أو حجمها | استخدم طرفية حديثة (Windows Terminal, iTerm2, GNOME Terminal). اضبط الخط على خط أحادي المسافة (monospace). |

---

## للمطورين

### المتطلبات

- Python 3.10 أو أحدث.
- Windows أو macOS أو Linux.
- أحد المشغلين: VLC، MPV، IINA (macOS فقط)، Celluloid، Haruna.
- Chrome أو Edge (اختياري، لاستخراج الكوكيز).

التبعيات (تُثبّت عبر `pip install -r requirements.txt`):

| الحزمة | الغرض |
|--------|-------|
| `rich` | عرض واجهة المستخدم في الطرفية |
| `httpx` | مكتبة HTTP لاستدعاء واجهات مصادر الأنمي |
| `beautifulsoup4` + `lxml` | تحليل صفحات HTML |
| `playwright` | استخراج كوكيز المتصفح |
| `pycryptodome` | فك تشفير الكوكيز |
| `keyring` | الوصول البديل لمفاتيح الكوكيز على macOS/Linux (اختياري) |

### طريقة التثبيت

```bash
git clone https://github.com/PanDuroDev/animeiat_cli.git
cd animeiat_cli
pip install -r requirements.txt
playwright install chromium
python anime_cli.py
```

على Linux، إذا فشل الأمر `playwright install chromium`، شغّل:

```bash
playwright install --with-deps chromium
```

### دليل الأوامر (CLI)

| الأمر | الاختصار | النوع | القيمة الافتراضية | الوصف |
|-------|----------|-------|--------------------|-------|
| `--help` | `-h` | — | — | عرض رسالة المساعدة والخروج |
| `--player` | `-p` | نص (string) | `auto` | المشغل المفضل: `auto`, `vlc`, `mpv`, `iina`, `celluloid`, `haruna` |
| `--quality` | `-q` | نص (string) | `auto` | جودة البث: `auto`, `1080p`, `720p`, `480p`, `360p` |
| `--url` | `-u` | نص (string) | — | رابط أنمي للتشغيل المباشر |
| `--no-tui` | — | علم (flag) | `false` | وضع عدم التفاعل: شغّل واخرج |
| `--version` | `-V` | علم (flag) | `false` | عرض رقم الإصدار والخروج |
| `--json` | — | علم (flag) | `false` | مخرجات JSON (لوضع عدم التفاعل) |
| `--list-episodes` | — | علم (flag) | `false` | عرض جميع الحلقات والخروج |
| `--download` | — | علم (flag) | `false` | إضافة رابط البث لقائمة التحميل والخروج |

### الإعدادات (Configuration)

يتم إنشاء ملف الإعدادات تلقائيًا عند أول تشغيل. موقعه:

| النظام | المسار |
|--------|--------|
| Windows | `%APPDATA%\animeiat_cli\config.json` |
| macOS/Linux | `~/.config/animeiat_cli/config.json` |

المفاتيح المتاحة:

| المفتاح | النوع | القيمة الافتراضية | الوصف |
|---------|-------|--------------------|-------|
| `preferred_player` | نص (string) | `"auto"` | مشغل الفيديو المفضل. الخيارات: `auto`, `vlc`, `mpv`, `iina`, `celluloid`, `haruna` |
| `default_quality` | نص (string) | `"auto"` | جودة البث المفضلة. الخيارات: `auto`, `1080p`, `720p`, `480p`, `360p` |
| `preferred_browser` | نص (string) | `"auto"` | المتصفح لاستخراج الكوكيز: `auto`, `chrome`, `edge` |
| `history_tracking` | منطقي (bool) | `true` | تفعيل أو تعطيل سجل المشاهدة |
| `fullscreen` | منطقي (bool) | `true` | تشغيل مشغل الفيديو في وضع ملء الشاشة |
| `custom_player_args` | نص (string) | `""` | وسائط إضافية تُمرّر لمشغل الفيديو (مثال: `--volume=80 --fs-screen=2`) |
| `nerd_fonts` | منطقي (bool) | `false` | تفعيل أيقونات Nerd Font في الواجهة (يتطلب تثبيت خط Nerd Font) |
| `scraping_method` | نص (string) | `"auto"` | محرك الاستخراج: `auto`, `playwright`, `httpx` |
| `enabled_sources` | مصفوفة (array) | `[0, 1]` | أرقام المصادر المفعلة. يمكن تغييرها من الإعدادات > مصادر البحث |
| `search_history` | مصفوفة (array) | `[]` | عمليات البحث الأخيرة (حد أقصى 5، تُدار تلقائيًا) |

### هيكل المشروع

```
animeiat-cli/
├── anime_cli.py              # نقطة الدخول — تُمرّر المهام إلى src/
├── requirements.txt          # تبعيات Python
├── pyproject.toml            # بيانات المشروع (PEP 621)
├── setup.py                  # إعداد بناء Cython
├── Dockerfile                # بناء حاوية Docker
├── src/
│   ├── ui/
│   │   ├── tui.py            # واجهة المستخدم التفاعلية (Rich)
│   │   └── cli.py            # تحليل وسائط سطر الأوامر والتوجيه
│   ├── providers/
│   │   ├── witanime.py       # مزود Witanime
│   │   ├── anineko.py        # مزود Anineko
│   │   └── anime3rb.py       # مزود Anime3rb
│   ├── playback/
│   │   ├── discovery.py      # كشف المشغلات المثبتة وتثبيتها
│   │   ├── launch.py         # تشغيل مشغلات الفيديو (VLC, MPV, IINA ...)
│   │   └── progress.py       # تتبع进度 التشغيل عبر IPC
│   ├── cache/
│   │   └── stream_cache.py   # تخزين مؤقت لروابط البث (SQLite)
│   ├── config/
│   │   └── __init__.py       # إدارة ملف الإعدادات، السمات، الأيقونات
│   └── db/
│       └── __init__.py       # قاعدة البيانات (الحسابات، المفضلة، السجل)
├── scraping.py               # مستخرج قديم (مهمل — استخدم src.providers بدلًا منه)
├── config.py                 # إعادة تصدير قديمة (مهملة)
├── db.py                     # إعادة تصدير قديمة (مهملة)
└── player.py                 # إعادة تصدير قديمة (مهملة)
```

### المساهمة

التطوير يتم على فرع `develop`. لإعداد بيئة التطوير:

```bash
git checkout develop
pip install -r requirements.txt
playwright install chromium
pytest tests/ -v
```

يجب أن تجتاز جميع الاختبارات الـ 74 قبل تقديم طلب سحب (Pull Request). انظر [CONTRIBUTING.md](./CONTRIBUTING.md) للإرشادات التفصيلية حول التفرع (branching)، أسلوب الكود (code style)، وسير عمل طلبات السحب.

---

## الرخصة

[MIT](./LICENSE)
