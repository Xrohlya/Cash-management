import re
from datetime import date, datetime, timedelta


def parse_amount(text: str):
    clean = text.replace(" ", "").replace("₽", "").replace("руб", "").replace(",", ".")
    matches = re.findall(r"\d+(?:\.\d{1,2})?", clean)
    return float(matches[0]) if matches else None


def parse_expense(text: str):
    amount = parse_amount(text)
    if amount is None:
        return None, None
    description = re.sub(r"\d+(?:[.,]\d{1,2})?", "", text, count=1).strip()
    return amount, description or "Расход"


def looks_like_income(text: str) -> bool:
    low = text.lower().strip()
    return low.startswith(("получил", "получила", "зарплата", "доход", "пришло", "пришла", "получение"))


def extract_date(text: str, today=None):
    """Recognise today/yesterday and simple DD.MM dates without changing DB schema."""
    today = today or date.today()
    low = text.casefold()
    if "позавчера" in low:
        return today - timedelta(days=2)
    if "вчера" in low:
        return today - timedelta(days=1)
    if "сегодня" in low:
        return today
    m = re.search(r"\b(\d{1,2})[./-](\d{1,2})(?:[./-](\d{2,4}))?\b", text)
    if not m:
        return None
    day, month = int(m.group(1)), int(m.group(2))
    year = int(m.group(3)) if m.group(3) else today.year
    if year < 100:
        year += 2000
    try:
        return date(year, month, day)
    except ValueError:
        return None


def strip_date_words(text: str) -> str:
    text = re.sub(r"\b(сегодня|вчера|позавчера)\b", " ", text, flags=re.I)
    text = re.sub(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", " ", text)
    return " ".join(text.split())
