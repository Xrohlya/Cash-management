# Cash Management 2.0

Telegram-бот и Mini App для персонального бюджета. Чат и приложение используют одну базу и одну бизнес-логику.

## Что готово

- отдельный приватный чат для каждого Telegram-пользователя;
- изоляция данных по подписанному Telegram `user_id`;
- доходы, расходы, квартира, обязательный процент и накопления;
- настраиваемый день начала финансового месяца;
- Mini App: сводка, создание операций, история;
- защита от повторной отправки операции из Mini App;
- PDF- и Excel-отчёты с отдельными именами файлов для каждого пользователя;
- общая PostgreSQL в Aiven для бота и Mini App;
- локальное резервное копирование актуальной базы.

## Структура

- `app.py` — polling-процесс Telegram-бота;
- `backend/main.py` — API и раздача Mini App;
- `webapp/` — интерфейс Mini App;
- `database/` — схема и операции с данными;
- `services/` — расчёты, аналитика и отчёты;
- `tools/backup_postgres.py` — резервная копия PostgreSQL;
- `BACKUP_DATABASE.command` — простой запуск резервного копирования;
- `tools/set_database_url.py` — безопасная смена адреса PostgreSQL.

## Локальный запуск

### Visual Studio Code

1. Откройте папку проекта в VS Code.
2. Скопируйте `.env.example` в `.env` и заполните параметры.
3. Не запускайте одновременно старую и новую копии с одним токеном.
4. Нажмите `Cmd+Shift+B` или выберите `Terminal -> Run Task -> Cash Management: запустить`.

Задача сама создаёт `.venv`, устанавливает зависимости при их изменении, запускает API и бота. Остановка: `Ctrl+C` в терминале задачи.

### Терминал

Запустите `START.command` или команды ниже.

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

Mini App опубликован через Render. Локальный бот и облачный API используют одну базу Aiven из `DATABASE_URL`.

## Проверка

```bash
python -m unittest discover -s tests -v
```

Перед важными изменениями запустите `BACKUP_DATABASE.command`.
