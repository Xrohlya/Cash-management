# Cash Management 2.0

Telegram-бот и Mini App для персонального бюджета. Чат и приложение используют одну базу и одну бизнес-логику.

Актуальные архитектурные решения и правила проекта собраны в
[`PROJECT_CONTEXT.md`](PROJECT_CONTEXT.md). Перед существенными изменениями
сначала сверяйтесь с ним.

## Что готово

- Mini App: четыре вкладки Бюджет, Операции, Планы, Настройки;
- калькулятор покупки, сценарии, ожидаемые доходы, лимиты категорий,
  недельная сводка и подтверждаемая отмена последней операции с архивом;
- оформление в `webapp/static/design.css`, HTML-разделы в `webapp/sections/`;
- ожидаемые доходы не увеличивают баланс до подтверждения поступления;

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
- `bot/routes/` — команды и кнопки Telegram по назначению;
- `backend/main.py` — сборка API и раздача Mini App;
- `backend/routes/` — маршруты операций, счетов, источников и настроек;
- `webapp/` — интерфейс Mini App, JavaScript-модули в `static/modules/`;
- `database/` — схема и операции с данными;
- `services/` — расчёты, аналитика и отчёты;
- `tools/backup_postgres.py` — резервная копия PostgreSQL;
- `BACKUP_DATABASE.command` — простой запуск резервного копирования;
- `tools/set_database_url.py` — безопасная смена адреса PostgreSQL.

## Локальный запуск

### Visual Studio Code

1. Откройте папку проекта в VS Code.
2. Не запускайте одновременно старую и новую копии с одним токеном.
3. Нажмите `Cmd+Shift+B` или выберите `Terminal -> Run Task -> Cash Management: запустить`.

Задача сама создаёт `.venv`, устанавливает зависимости при их изменении, запускает API и бота. Остановка: `Ctrl+C` в терминале задачи.

### Терминал

Скопируйте `.env.example` в `.env`, заполните параметры и запустите `START.command` или команды ниже.

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
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
find webapp/static -name '*.js' ! -name '._*' -exec node --check {} \;
```

Перед важными изменениями запустите `BACKUP_DATABASE.command`.
