# دریافت خودکار قیمت نمادهای بورس از TSETMC

این مخزن با GitHub Actions هر ۱۵ دقیقه تلاش می‌کند اطلاعات نماد «فملی» را از API عمومی TSETMC بگیرد و در `data/prices.json` ذخیره کند. قیمت منتخب، **قیمت پایانی** است؛ اگر در پاسخ قیمت پایانی معتبر نباشد، از **آخرین معامله** استفاده می‌شود.

> این پروژه به API عمومی TSETMC وابسته است؛ ممکن است API محدود، قطع یا تغییر کند. زمان‌بندی ۱۵ دقیقه‌ای به معنی تضمین قیمت لحظه‌ای نیست.

## ۱. ساخت مخزن

1. در GitHub یک repository جدید بسازید؛ مثلاً `tsetmc-price-proxy`.
2. گزینه **Public** را انتخاب کنید تا فایل JSON از آدرس `raw.githubusercontent.com` بدون احراز هویت قابل خواندن باشد.
3. فایل‌های این پروژه را با همان مسیرها در مخزن بارگذاری و Commit کنید.

## ۲. فعال‌سازی GitHub Actions

1. وارد مخزن شوید و به **Actions** بروید.
2. اگر GitHub درخواست کرد، Actions را فعال کنید.
3. از فهرست workflow، گزینه **Update TSETMC prices** را انتخاب کنید.
4. روی **Run workflow** بزنید.
5. بعد از اجرای موفق، فایل `data/prices.json` باید با داده‌های واقعی به‌روزرسانی شده باشد.

زمان‌بندی cron هر ۱۵ دقیقه است؛ اجرای زمان‌بندی‌شده ممکن است با تأخیر شروع شود. برای مخزن عمومی، GitHub Actions معمولاً مناسب است، اما محدودیت‌های حساب و مخزن می‌توانند اثر بگذارند.

## ۳. آدرس JSON

پس از ساخت مخزن، آدرس فایل به این شکل خواهد بود:

`https://raw.githubusercontent.com/USERNAME/REPOSITORY/main/data/prices.json`

`USERNAME` و `REPOSITORY` را با نام کاربری و مخزن خود جایگزین کنید.

نمونه خروجی:

```json
{
  "prices": {
    "فملی": {
      "price_irr": 12345,
      "price_type": "closing",
      "closing_price_irr": 12345,
      "last_trade_price_irr": 12350
    }
  }
}
```

قیمت‌ها به **ریال** هستند. برای تبدیل به تومان، عدد را بر ۱۰ تقسیم کنید.

## ۴. خواندن در Google Sheets با Apps Script

در Google Sheets از مسیر **Extensions → Apps Script** کد زیر را اضافه کنید. آدرس `JSON_URL` را با آدرس خام مخزن خودتان جایگزین کنید.

```javascript
const JSON_URL = "https://raw.githubusercontent.com/USERNAME/REPOSITORY/main/data/prices.json";

function TSETMC_PRICE(symbol, unit) {
  symbol = symbol || "فملی";
  unit = (unit || "toman").toLowerCase();

  const response = UrlFetchApp.fetch(JSON_URL, {
    muteHttpExceptions: true,
    followRedirects: true
  });

  if (response.getResponseCode() !== 200) {
    throw new Error("خطا در دریافت فایل JSON: HTTP " + response.getResponseCode());
  }

  const data = JSON.parse(response.getContentText("UTF-8"));
  const item = data.prices && data.prices[symbol];

  if (!item || item.price_irr == null) {
    throw new Error("قیمت برای نماد " + symbol + " موجود نیست. errors: " +
      JSON.stringify(data.errors || {}));
  }

  const price = Number(item.price_irr);
  return unit === "irr" ? price : price / 10;
}

function TSETMC_PRICE_TYPE(symbol) {
  symbol = symbol || "فملی";
  const response = UrlFetchApp.fetch(JSON_URL);
  const data = JSON.parse(response.getContentText("UTF-8"));
  const item = data.prices && data.prices[symbol];
  return item ? item.price_type : "unavailable";
}

function TSETMC_UPDATED_AT() {
  const response = UrlFetchApp.fetch(JSON_URL);
  const data = JSON.parse(response.getContentText("UTF-8"));
  return data.updated_at_utc || "";
}
```

در سلول شیت:

- قیمت به تومان: `=TSETMC_PRICE("فملی")`
- قیمت به ریال: `=TSETMC_PRICE("فملی","irr")`
- نوع قیمت (`closing` یا `last_trade`): `=TSETMC_PRICE_TYPE("فملی")`
- زمان به‌روزرسانی UTC: `=TSETMC_UPDATED_AT()`

Google Sheets ممکن است خروجی تابع سفارشی را موقتاً cache کند؛ برای مشاهده داده تازه‌تر، سلول را دوباره محاسبه کنید یا از منوی Run در Apps Script یک تابع کمکی اجرا کنید. به‌روزرسانی JSON نیز تنها در صورت موفقیت workflow انجام می‌شود.

## ۵. افزودن نمادهای بیشتر

در ابتدای `scripts/update_prices.py` فهرست زیر را ویرایش کنید:

```python
SYMBOLS = ["فملی", "فولاد", "شستا"]
```

بعد از Commit، workflow دوباره اجرا می‌شود و خروجی را در `prices` برای هر نماد ذخیره می‌کند.

## عیب‌یابی

- **Workflow اجرا نمی‌شود:** در تب Actions بررسی کنید فعال باشد. اجرای زمان‌بندی ممکن است با تأخیر انجام شود.
- **خطای API یا HTTP:** ممکن است TSETMC دسترسی GitHub-hosted runner را محدود کرده باشد یا API تغییر کرده باشد؛ جزئیات در log همان workflow است.
- **قیمت خالی است:** فایل `data/prices.json` را باز کنید و بخش `errors` را بررسی کنید.
- **Google Sheets خطای دسترسی می‌دهد:** مخزن باید Public باشد و URL باید دقیقاً به فایل `main/data/prices.json` اشاره کند.
