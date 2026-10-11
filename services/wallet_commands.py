import re


def resolve_wallet(text, accounts, *, with_description=False):
    text = re.sub(r"^(?:со?\s+сч[её]та|сч[её]т|из|с|на)\s+", "", text.strip(), flags=re.I)
    options = [("накоплений", "savings"), ("накопления", "savings"), ("основного", "main"), ("основной", "main")]
    options += [(row["name"], f"account:{row['id']}") for row in accounts]
    for name, wallet in sorted(options, key=lambda item: len(item[0]), reverse=True):
        if text.casefold() == name.casefold():
            return wallet, ""
        if with_description and text.casefold().startswith(name.casefold() + " "):
            return wallet, text[len(name):].strip()
    raise ValueError("Счёт не найден. Укажите «основной», «накопления» или точное название счёта")


def parse_wallet_command(text, accounts):
    match = re.fullmatch(r"/?(возврат|refund|перевод|transfer|расход|expense)\s+(\d+(?:[.,]\d{1,2})?)\s+(.+)", text.strip(), flags=re.I)
    if not match:
        raise ValueError("Примеры: возврат 500 Разное; перевод 3000 из накоплений на счёт Отпуск; расход 500 со счета Отпуск такси")
    command, raw, rest = match.groups()
    amount = float(raw.replace(",", "."))
    if command.casefold() in {"возврат", "refund"}:
        return "refund", amount, rest
    if command.casefold() in {"перевод", "transfer"}:
        parts = re.split(r"\s+на\s+", rest, maxsplit=1, flags=re.I)
        if len(parts) != 2:
            raise ValueError("Пример: перевод 3000 из накоплений на счёт Отпуск")
        source, _ = resolve_wallet(parts[0], accounts)
        destination, _ = resolve_wallet(parts[1], accounts)
        return "transfer", amount, (source, destination)
    wallet, description = resolve_wallet(rest, accounts, with_description=True)
    return "expense", amount, (wallet, description or "Расход")
