# animeiat-cli

<p align="center">
  <strong>العربية</strong> &nbsp;|&nbsp; <a href="README.md">English</a>
</p>

> هذه الترجمة العربية لأغراض المساعدة. النسخة الإنجليزية هي المرجع الرسمي.

تطبيق طرفية (Terminal) للبحث عن حلقات الأنمي وتشغيلها من مصادر متعددة على الويب. بدون إعلانات. بدون متصفح.

![License](https://img.shields.io/github/license/PanDuroDev/animeiat_cli?style=for-the-badge)
![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)
![Platform](https://img.shields.io/badge/platform-windows%20%7C%20macos%20%7C%20linux-lightgrey?style=for-the-badge)
[![Latest Release](https://img.shields.io/github/v/release/PanDuroDev/animeiat_cli?style=for-the-badge)](https://github.com/PanDuroDev/animeiat_cli/releases)

## المحتويات

- [للمستخدم النهائي](#للمستخدم-النهائي)
  - [ماذا يفعل التطبيق](#ماذا-يفعل-التطبيق)
  - [قبل البدء](#قبل-البدء)
  - [تحميل الملف التنفيذي الجاهز](#تحميل-الملف-التنفيذي-الجاهز)
  - [التثبيت السريع (من المصدر)](#التثبيت-السريع-من-المصدر)
  - [كيفية الاستخدام](#كيفية-الاستخدام)
  - [حل المشكلات الشائعة](#حل-المشكلات-الشائعة)
- [للمطورين](#للمطورين)
  - [المتطلبات](#المتطلبات)
  - [طريقة التثبيت](#طريقة-التثبيت)
  - [نظام البناء](#نظام-البناء)
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
- **Python 3.10+** (إذا كنت تشغّل من المصدر) أو حمّل الملف التنفيذي الجاهز.
- **مشغل فيديو** مثل VLC أو MPV. سيكتشفه التطبيق تلقائيًا.
- **متصفح Chrome أو Edge** (اختياري) — يُستخدم فقط لاستخراج الكوكيز (cookies) للوصول إلى مصادر الأنمي. التطبيق لا يقرأ أي بيانات شخصية.

إذا لم تكن متأكدًا من كيفية تثبيت Python، حمّله من [python.org](https://www.python.org/downloads/) وحدد "Add Python to PATH" أثناء التثبيت على Windows، أو استخدم مدير الحزم الخاص بنظامك على macOS/Linux.

### تحميل الملف التنفيذي الجاهز

الملفات التنفيذية الجاهزة متوفرة في [صفحة الإصدارات](https://github.com/PanDuroDev/animeiat_cli/releases).

| النظام | الملف | الحالة |
|--------|-------|--------|
| Windows | `animeiat-cli-windows.zip` | متوفر |
| macOS | — | ابنِ عبر CI أو يدويًا (انظر [نظام البناء](#نظام-البناء)) |
| Linux | — | ابنِ عبر CI أو يدويًا (انظر [نظام البناء](#نظام-البناء)) |

> **ملاحظة:** البناء عبر الأنظمة (Cross-compilation) غير مدعوم. كل نظام يجب أن يُبنى عليه بشكل منفصل.
> ادفع tag إصدار (`v*`) لتفعيل [GitHub Actions](https://github.com/PanDuroDev/animeiat_cli/actions) لبناء جميع الأنظمة تلقائيًا.

لا حاجة لتثبيت Python للملفات التنفيذية الجاهزة. حمّل، فك الضغط، وشغّل.

> **ملاحظة:** فرع `main` مخصص للاستخدام الإنتاجي. التطوير (بما في ذلك الاختبارات والملفات التجريبية) يتم على فرع `develop`.

### التثبيت السريع (من المصدر)

1. **ثبّت Python ومشغل الفيديو** (انظر [قبل البدء](#قبل-البدء) أعلاه).

2. **حمّل المشروع:**

   ```bash
   git clone https://github.com/PanDuroDev/animeiat_cli.git
   cd animeiat_cli
   ```

3. **ثبّت حزم Python المطلوبة:**

   ```bash
   pip install -r requirements.txt
   ```

   إذا فشل الأمر، جرب `pip3` بدل `pip`، أو شغّل `python -m pip install -r requirements.txt`.

4. **ثبّت مكون المتصفح Playwright:**

   ```bash
   playwright install chromium
   ```

   على Linux: `playwright install --with-deps chromium`.

5. **شغّل التطبيق:**

   ```bash
   animeiat-cli

   # أو عبر وحدة Python:
   python -m src.ui.cli
   ```

   استخدم `python3` على macOS و Linux إذا لم يعمل `python`.

#### باستخدام Docker

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
| `playwright` | أتمتة المتصفح واستخراج الكوكيز |
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

على Linux، إذا فشل الأمر `playwright install chromium`:

```bash
playwright install --with-deps chromium
```

### نظام البناء

يستخدم المشروع **PyInstaller** لإنشاء ملفات تنفيذية مستقلة.  
لا حاجة لمُجمّع C أو Cython.

#### البداية السريعة

```bash
# تثبيت تبعيات البناء
pip install pyinstaller

# بناء (افتراضي: onedir + Chromium مضمّن)
python build/build.py

# بناء كملف واحد
python build/build.py --onefile

# بناء بدون Chromium (يُحمّل عند أول تشغيل)
python build/build.py --lite

# فحص بيئة البناء
python build/build.py --check

# تنظيف ملفات البناء السابقة
python build/build.py --clean
```

#### خيارات البناء

| الأمر | المخرجات | Chromium | حالة الاستخدام |
|-------|----------|----------|----------------|
| *(افتراضي)* | مجلد `dist/animeiat-cli/` | مضمّن (~170MB) | إقلاع سريع، Playwright مستقر |
| `--onefile` | ملف واحد `dist/animeiat-cli.exe` | مضمّن (~900MB) | توزيع سهل |
| `--lite` | مجلد `dist/animeiat-cli-lite/` | يُحمّل عند التشغيل (~30MB) | حجم تحميل صغير |
| `--clean` | — | — | حذف `dist/` وذاكرة البناء |

نص البناء:
1. يكتشف نظام التشغيل (Windows / macOS / Linux)
2. يُثبّت PyInstaller إذا كان مفقودًا
3. يُحمّل Chromium عبر Playwright (إلا في وضع `--lite`)
4. يشغّل PyInstaller مع ملف المواصفات (`build/animeiat-cli.spec`)
5. يتحقق من صحة المخرجات بتشغيل `--version` على الملف المبني

#### بناء عبر المنصات

لا يوجد بناء عبر المنصات (Cross-compilation). ابنِ على كل منصة بشكل منفصل:

```bash
# Windows
python build\build.py

# macOS / Linux
python build/build.py
```

كل منصة تُنتج ملفًا تنفيذيًا أصليًا بدون تبعيات Python خارجية.

#### كيف يعمل

```
build/
├── build.py              # نص البناء (أمر واحد لجميع المنصات)
└── animeiat-cli.spec     # ملف مواصفات PyInstaller
```

- `build/animeiat-cli.spec` يُحدد محتويات الملف التنفيذي: جميع وحدات `src/`، lxml، Cryptodome، Playwright، متصفح Chromium.
- `build/build.py` يدير العملية بأكملها: فحص التبعيات، تحميل Chromium، تشغيل PyInstaller، التحقق من المخرجات.

#### CI/CD (التكامل المستمر)

[sير عمل GitHub Actions](https://github.com/PanDuroDev/animeiat_cli/actions) يبني المشروع عند كل push إلى `main` وعند كل tag إصدار (`v*`):

| المُشغّل | منصات البناء | المخرجات |
|----------|-------------|----------|
| Push إلى `main` | Windows, macOS, Linux | onedir + onefile (مرفوعة كـ CI artifacts) |
| Tag إصدار `v*` | Windows, macOS, Linux | تُرفق تلقائيًا بصفحة الإصدارات |

لتفعيل بناء لكل المنصات، ادفع tag إصدار:

```bash
git tag v1.0.0
git push origin v1.0.0
```

سير العمل سيَبني جميع المنصات الثلاث ويرفع الملفات التنفيذية إلى صفحة الإصدارات.

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
├── build/
│   ├── build.py              # نص البناء (PyInstaller، أمر واحد)
│   └── animeiat-cli.spec     # ملف مواصفات PyInstaller
├── .github/
│   └── workflows/
│       └── build.yml         # CI/CD: بناء Windows, macOS, Linux تلقائيًا
├── src/
│   ├── __init__.py
│   ├── chromium.py           # أداة تحميل Chromium تلقائي
│   ├── ui/
│   │   ├── __init__.py       # تصديرات واجهة المستخدم
│   │   ├── tui.py            # الواجهة التفاعلية (Rich، ~2450 سطر)
│   │   └── cli.py            # نقطة الدخول وتحليل وسائط سطر الأوامر
│   ├── providers/
│   │   ├── __init__.py       # سجل المزوّدين
│   │   ├── _cookies.py       # استخراج الكوكيز من المتصفح
│   │   ├── _utils.py         # أدوات مساعدة مشتركة (التحقق من الروابط، تصنيف الجودة)
│   │   ├── _scraper.py       # منطق الاستخراج المشترك (httpx + Playwright)
│   │   ├── witanime.py       # مزود WitAnime
│   │   ├── anineko.py        # مزود Anineko
│   │   └── anime3rb.py       # مزود Anime3rb
│   ├── playback/
│   │   ├── __init__.py       # واجهة التشغيل
│   │   ├── discovery.py      # كشف المشغلات (VLC, MPV, IINA...)
│   │   ├── launch.py         # تشغيل مشغل الفيديو
│   │   └── progress.py       # تتبع تقدّم التشغيل
│   ├── cache/
│   │   ├── __init__.py       # واجهة التخزين المؤقت
│   │   └── stream_cache.py   # تخزين روابط البث (SQLite)
│   ├── config/
│   │   └── __init__.py       # إعدادات، سمات، أيقونات
│   └── db/
│       └── __init__.py       # قاعدة البيانات: حسابات، مفضلة، سجل، تحميلات
├── requirements.txt          # تبعيات Python
├── pyproject.toml            # بيانات المشروع (PEP 621)
├── setup.py                  # بناء Cython قديم (مهمل — استخدم build/build.py)
├── Dockerfile                # بناء حاوية Docker
├── CHANGELOG.md              # سجل التغييرات
├── CONTRIBUTING.md           # إرشادات المساهمة
└── LICENSE                   # رخصة MIT
```

### المساهمة

التطوير يتم على فرع `develop`. لإعداد بيئة التطوير:

```bash
git checkout develop
pip install -r requirements.txt
playwright install chromium
pytest tests/ -v
```

يجب أن تجتاز جميع الاختبارات قبل تقديم طلب سحب (Pull Request). انظر [CONTRIBUTING.md](./CONTRIBUTING.md) للإرشادات التفصيلية حول التفرع (branching)، أسلوب الكود (code style)، وسير عمل طلبات السحب.

#### روابط المساهمة

- [لوحة المشروع](https://github.com/PanDuroDev/animeiat_cli/projects) — تتبع التقدّم والميزات المخططة
- [الملفات المفتوحة (Issues)](https://github.com/PanDuroDev/animeiat_cli/issues) — الإبلاغ عن أخطاء أو اقتراح ميزات
- [المناقشات](https://github.com/PanDuroDev/animeiat_cli/discussions) — طرح الأسئلة ومشاركة الأفكار
- [سجل التغييرات](./CHANGELOG.md) — ما تغيّر في كل إصدار

---

## الرخصة

[MIT](./LICENSE)

---

<p align="center">
  <strong>العربية</strong> &nbsp;|&nbsp; <a href="README.md">English</a>
</p>
