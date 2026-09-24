# Cash Management — Telegram Mini App

Mini App: https://xrohlya.github.io/Cash-management/

## Архитектура

GitHub Pages содержит только интерфейс. Данные хранятся в PostgreSQL на сервере API. Telegram `initData` проверяется сервером; `user_id` из браузера не принимается как источник истины.

## Подключение API

После публикации backend откройте `config.js` и задайте:

```js
window.CASH_API_URL = 'https://ВАШ-HTTPS-АДРЕС-СЕРВЕРА';
```

После этого GitHub Pages будет загружать актуальный бюджет через `/api/state` и записывать расходы, доходы и накопления через API.

## Telegram

Кнопка Mini App должна открывать:

`https://xrohlya.github.io/Cash-management/`

Для финансовых операций сервер использует Telegram `initData`, а не переданный клиентом идентификатор пользователя.

## Безопасность

- токен бота не хранится в репозитории;
- PostgreSQL URL не хранится в GitHub Pages;
- `config/access.py` не переносится в репозиторий;
- локальный `data/budget.db` можно сохранить как резервную копию.
