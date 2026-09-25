# Cash Management 2.0

Telegram-бот и Mini App для персонального бюджета. Чат и приложение используют одну базу и одну бизнес-логику.

## Что готово

- отдельный приватный чат для каждого Telegram-пользователя;
- изоляция данных по подписанному Telegram `user_id`;
- доходы, расходы, квартира, обязательный процент и накопления;
- финансовый месяц с 20-го по 19-е;
- Mini App: сводка, создание операций, история;
- защита от повторной отправки операции из Mini App;
- PDF- и Excel-отчёты с отдельными именами файлов для каждого пользователя;
- SQLite для локальной работы и PostgreSQL для многопользовательского облака;
- перенос существующей истории без изменения исходной базы.

## Структура

- `app.py` — polling-процесс Telegram-бота;
- `backend/main.py` — API и раздача Mini App;
- `webapp/` — интерфейс Mini App;
- `database/` — схема и операции с данными;
- `services/` — расчёты, аналитика и отчёты;
- `tools/migrate_sqlite_to_postgres.py` — перенос истории в PostgreSQL;
- `data/budget.db` — согласованная копия актуальной SQLite-базы на момент сборки.

## Локальный запуск

1. Скопируйте `.env.example` в `.env`.
2. Укажите `BOT_TOKEN`.
3. Не запускайте одновременно старую и новую копии с одним токеном.
4. Запустите `START.command` или команды ниже.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --host 127.0.0.1 --port 8788
```

В другом терминале:

```bash
source .venv/bin/activate
python app.py
```

Для Mini App нужен публичный HTTPS-адрес. Укажите его в `WEBAPP_URL`; бот добавит кнопку приложения в меню и в основное сообщение.

## Проверка

```bash
python -m unittest discover -s tests -v
```

Полный порядок облачного переключения описан в [CLOUD_DEPLOY.md](CLOUD_DEPLOY.md).
