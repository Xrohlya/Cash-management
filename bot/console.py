import logging
import sys
from time import perf_counter

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message


USE_COLOR = sys.stdout.isatty()


class Style:
    RESET = "\033[0m" if USE_COLOR else ""
    DIM = "\033[2m" if USE_COLOR else ""
    BOLD = "\033[1m" if USE_COLOR else ""
    BLUE = "\033[38;5;39m" if USE_COLOR else ""
    CYAN = "\033[38;5;45m" if USE_COLOR else ""
    GREEN = "\033[38;5;42m" if USE_COLOR else ""
    YELLOW = "\033[38;5;220m" if USE_COLOR else ""
    RED = "\033[38;5;203m" if USE_COLOR else ""


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
        force=True,
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.WARNING)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)


def _money(value):
    if value is None:
        return "ошибка"
    whole, fraction = f"{float(value):,.2f}".split(".")
    amount = whole.replace(",", " ")
    if fraction != "00":
        amount += f",{fraction}"
    return amount + " ₽"


def _display_name(item):
    username = f"@{item['username']}" if item["username"] else ""
    return " · ".join(part for part in (item["first_name"], username) if part) or "без имени"


def _status_line(marker, label, value, marker_color):
    width = 72
    plain = f"{marker} {label}: {value}"
    padding = " " * max(0, width - len(plain) - 1)
    print(
        f"{Style.BLUE}│{Style.RESET} {marker_color}{marker}{Style.RESET} "
        f"{label}: {value}{padding}{Style.BLUE}│{Style.RESET}"
    )


def show_startup(bot_info, users, database_name="PostgreSQL · Aiven", webapp_url=""):
    width = 72
    title = "CASH MANAGEMENT"
    subtitle = f"Telegram-бот @{bot_info.username}" if bot_info.username else "Telegram-бот"
    print()
    print(f"{Style.BLUE}╭{'─' * width}╮{Style.RESET}")
    print(f"{Style.BLUE}│{Style.RESET} {Style.BOLD}{title:<70}{Style.RESET}{Style.BLUE}│{Style.RESET}")
    print(f"{Style.BLUE}│{Style.RESET} {Style.DIM}{subtitle:<70}{Style.RESET}{Style.BLUE}│{Style.RESET}")
    print(f"{Style.BLUE}├{'─' * width}┤{Style.RESET}")
    _status_line("✓", "База данных", database_name, Style.GREEN)
    _status_line("✓", "Telegram API", "подключен", Style.GREEN)
    _status_line("✓", "Mini App", webapp_url or "не настроен", Style.GREEN)
    _status_line("→", "Пользователей", str(len(users)), Style.CYAN)
    print(f"{Style.BLUE}╰{'─' * width}╯{Style.RESET}")

    if users:
        print(f"\n{Style.BOLD}ПОЛЬЗОВАТЕЛИ{Style.RESET}")
        print(f"{Style.DIM}{'ID':<16} {'ИМЯ / НИК':<34} {'БАЛАНС':>18}{Style.RESET}")
        print(f"{Style.DIM}{'─' * 16} {'─' * 34} {'─' * 18}{Style.RESET}")
        for item in users:
            name = _display_name(item)[:34]
            balance = _money(item["balance"])
            balance_color = Style.RED if item["balance"] is None else Style.GREEN
            print(f"{str(item['user_id']):<16} {name:<34} {balance_color}{balance:>18}{Style.RESET}")
    else:
        print(f"\n{Style.DIM}Пользователей пока нет.{Style.RESET}")

    print(f"\n{Style.BOLD}АКТИВНОСТЬ{Style.RESET}")
    print(f"{Style.DIM}Время     Пользователь                         Действие{Style.RESET}")
    print(f"{Style.DIM}{'─' * 72}{Style.RESET}")
    sys.stdout.flush()


def _activity_name(event):
    if isinstance(event, CallbackQuery):
        labels = {
            "status": "обновил бюджет",
            "today": "открыл расходы за сегодня",
            "history": "открыл историю",
            "forecast": "открыл прогноз",
            "savings": "открыл накопления",
            "goal": "открыл цель",
            "recurring": "открыл регулярные платежи",
            "income_sources": "открыл источники дохода",
            "analytics": "открыл аналитику",
            "compare": "открыл сравнение",
            "report": "запросил отчёт",
            "help": "открыл помощь",
            "clear_chat": "очистил чат",
        }
        return labels.get(event.data, f"кнопка: {event.data or 'без данных'}")
    if isinstance(event, Message):
        if event.text and event.text.startswith("/"):
            return f"команда {event.text.split(maxsplit=1)[0][:32]}"
        if event.photo:
            return "отправил фотографию"
        if event.document:
            return "отправил документ"
        return "отправил сообщение"
    return "действие"


class ActivityMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user = getattr(event, "from_user", None) or data.get("event_from_user")
        started = perf_counter()
        try:
            result = await handler(event, data)
        except Exception:
            self._print(user, _activity_name(event), perf_counter() - started, False)
            raise
        self._print(user, _activity_name(event), perf_counter() - started, True)
        return result

    @staticmethod
    def _print(user, action, duration, success):
        from datetime import datetime

        if user:
            username = f"@{user.username}" if user.username else ""
            display = " · ".join(part for part in (user.first_name, username) if part)
            who = f"{display or 'без имени'} [{user.id}]"
        else:
            who = "неизвестный пользователь"
        marker = f"{Style.GREEN}✓{Style.RESET}" if success else f"{Style.RED}×{Style.RESET}"
        timing = f"{duration * 1000:.0f} мс"
        print(
            f"{Style.DIM}{datetime.now():%H:%M:%S}{Style.RESET}  {marker} "
            f"{who[:34]:<34} {action[:25]:<25} {Style.DIM}{timing:>8}{Style.RESET}"
        )
        sys.stdout.flush()
