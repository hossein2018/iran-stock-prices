import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Add more symbols here if needed. TSETMC search names should be Persian.
SYMBOLS = ["فملی"]
BASE_URL = "https://cdn.tsetmc.com/api"
OUTPUT = Path("data/prices.json")


def get_json(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; TSETMCPriceUpdater/1.0)",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.tsetmc.com/",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8-sig"))


def find_instrument(symbol: str):
    url = f"{BASE_URL}/Instrument/GetInstrumentSearch/{urllib.parse.quote(symbol)}"
    payload = get_json(url)
    rows = payload.get("instrumentSearch") or []

    # Prefer an exact match after normalizing Arabic/Persian character variants.
    def norm(value):
        return str(value or "").replace("ي", "ی").replace("ك", "ک").replace("\u200c", "").strip()

    matches = [r for r in rows if norm(r.get("lVal18AFC")) == norm(symbol)]
    if not matches:
        matches = [r for r in rows if norm(r.get("lVal18AFC")).startswith(norm(symbol))]
    if not matches:
        raise RuntimeError(f"Instrument not found: {symbol}")

    # If multiple rows match, select the first result returned by TSETMC.
    return matches[0]


def get_price(instrument):
    ins_code = str(instrument["insCode"])
    url = f"{BASE_URL}/ClosingPrice/GetClosingPriceInfo/{ins_code}"
    payload = get_json(url)
    info = payload.get("closingPriceInfo") or {}

    closing = info.get("pClosing")
    last = info.get("pDrCotVal")

    def positive_number(value):
        try:
            n = float(value)
            return n if n > 0 else None
        except (TypeError, ValueError):
            return None

    closing_n = positive_number(closing)
    last_n = positive_number(last)
    chosen = closing_n if closing_n is not None else last_n
    chosen_type = "closing" if closing_n is not None else ("last_trade" if last_n is not None else None)

    return {
        "symbol": instrument.get("lVal18AFC"),
        "name": instrument.get("lVal30"),
        "insCode": ins_code,
        "closing_price_irr": closing_n,
        "last_trade_price_irr": last_n,
        "price_irr": chosen,
        "price_type": chosen_type,
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": url,
    }


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result = {
        "updated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "TSETMC CDN API",
        "prices": {},
        "errors": {},
    }

    for symbol in SYMBOLS:
        try:
            instrument = find_instrument(symbol)
            result["prices"][symbol] = get_price(instrument)
            print(f"OK {symbol}: {result['prices'][symbol]['price_irr']}")
        except Exception as exc:
            result["errors"][symbol] = str(exc)
            print(f"ERROR {symbol}: {exc}")
        time.sleep(1)

    OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # Fail the workflow if all symbols failed, so GitHub shows a visible error.
    if not result["prices"]:
        raise SystemExit("No symbols were updated successfully.")


if __name__ == "__main__":
    main()
