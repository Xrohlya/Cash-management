"""One explanation shared by Telegram and the Mini App."""
from services.formatting import money


def explain_radar(radar):
    calculation = radar["calculation"]
    forecast = radar["projected_balance"]
    if forecast < 0:
        title = f"При текущем темпе не хватит {money(-forecast)} ₽"
    else:
        title = f"При текущем темпе останется {money(forecast)} ₽"
    target = radar["target_balance"]
    if calculation["available"] - radar["reserved"] < target:
        guidance = "Доступных средств уже недостаточно для платежей и желаемого остатка. Безопасный лимит — 0 ₽."
    else:
        guidance = f"Чтобы сохранить {money(target)} ₽: до {money(radar['safe_today'])} ₽ в день."
    elapsed = calculation["elapsed_days"]
    provisional = "Предварительный прогноз" if elapsed <= 7 else "Прогноз"
    notice = f"{provisional} по {elapsed} дн. периода. Это не долг и не текущий баланс."
    return {
        "title": title,
        "pace": f"Средний расход с начала периода — {money(calculation['daily_average'])} ₽/день. Прогноз ещё на {calculation['forecast_days']} дн.",
        "guidance": guidance,
        "notice": notice,
        "target_gap": f"До желаемого остатка не хватает {money(target - forecast)} ₽." if 0 <= forecast < target else "",
    }
