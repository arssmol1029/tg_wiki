# tg_wiki

Телеграм‑бот на aiogram для просмотра случайных статей из Википедии и поиска статей по запросу.  
Проект включает слой сервисов (Wiki/Search/Reco/Settings), кэш (in‑memory или Redis) и постоянное хранилище пользовательских настроек в PostgreSQL.

---

## Возможности

### Команды
- `/start` — приветствие и краткая справка.
- `/help` — список команд.
- `/next` — получить следующую случайную статью.
- `/search <запрос>` — поиск по Википедии и выбор результата кнопкой.
- `/settings` — настройки (длина страницы, включение текста/картинки, языки).
- `/cancel` — сброс текущего состояния.

---

## Технологии

- Python **3.12+**
- aiogram
- aiohttp (HTTP‑клиент к Wikipedia API)
- Redis (опционально) — кэш статей и пользовательских данных
- PostgreSQL — пользователи, настройки, вектор предпочтений (заготовка под рекомендации)
- SQLAlchemy + asyncpg
- Alembic (миграции)

---

## Быстрый старт (Docker Compose)

1) Создайте `.env` в корне проекта:

```env
BOT_TOKEN=123456789:AA...your_token...
```

2) Запустите инфраструктуру и приложение:

```bash
docker compose up --build
```

Команда контейнера приложения автоматически выполнит миграции:

```sh
alembic upgrade head && tg-wiki
```

По умолчанию `docker-compose.yml` поднимает:
- `db`: `pgvector/pgvector` (PostgreSQL 16 + расширение vector),
- `redis`,
- `app`.

---

## Локальный запуск (venv)

### 1) Установка
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

### 2) Переменные окружения

Минимум:
- `BOT_TOKEN` — токен бота.
- `DB_DSN` — DSN для подключения к PostgreSQL.

Пример `.env` для локальной разработки:

```env
BOT_TOKEN=...your_token...

DB_DSN=postgresql+asyncpg://tg_wiki:tg_wiki@localhost:5432/tg_wiki

CACHE_BACKEND=redis
REDIS_URL=redis://localhost:6379/0
REDIS_PREFIX=tg_wiki
```

### 3) Миграции
```bash
alembic upgrade head
```

### 4) Запуск
```bash
tg-wiki
```

---

## Конфигурация

### Обязательные переменные
- `BOT_TOKEN` — токен Telegram Bot API.
- `DB_DSN` — строка подключения SQLAlchemy для asyncpg, например:  
  `postgresql+asyncpg://user:pass@host:5432/dbname`

### Настройки пула БД (опционально)
- `DB_POOL_SIZE` (по умолчанию `5`)
- `DB_MAX_OVERFLOW` (по умолчанию `5`)

### pgvector (опционально)
- `PREF_VECTOR_DIM` (по умолчанию `1536`) — размерность вектора предпочтений в БД 
(не задаётся только параметром конфигурации, необходимы изменения в исходниках).

### Кэш (опционально)
- `CACHE_BACKEND`: `in-memory` (по умолчанию) или `redis`
- `REDIS_URL` (по умолчанию `redis://localhost:6379/0`)
- `REDIS_PREFIX` (по умолчанию `tg_wiki`)

TTL/лимиты Redis (в секундах; используются при `CACHE_BACKEND=redis`):
- `REDIS_ARTICLE_TTL_S` (по умолчанию `86400`) — кэш статей
- `REDIS_MAX_PER_USER` (по умолчанию `20`) — лимит истории просмотренных статей
- `REDIS_LASTVIEW_TTL_S` (по умолчанию `604800`) — TTL истории просмотренных
- `REDIS_SETTINGS_TTL_S` (по умолчанию `86400`) — кэш настроек
- `REDIS_USERID_TTL_S` (по умолчанию `86400`) — кэш соответствий внешнего id → внутренний user_id

---

## База данных и схема

Миграция `migrations/versions/*_init_schema.py` создаёт:
- `users`
- `user_identities` (provider + external_id → user_id)
- `user_settings`
- `user_preferences` (поле `pref_vector` типа `vector(1536)`)

Также выполняется:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

---

## Архитектура проекта

Код находится в `src/tg_wiki`:

- `tg_wiki/main.py` — сборка зависимостей, выбор кэша, запуск polling.
- `tg_wiki/wiki_service/*` — обращение к Wikipedia API (используется `ru.wikipedia.org`).
- `tg_wiki/reco_service/*` — выдача случайных статей с учётом истории пользователя.
- `tg_wiki/search_service/*` — поиск по соответствию и загрузка статьи по `pageid`.
- `tg_wiki/settings_service/*` — сохранение/получение настроек пользователя.
- `tg_wiki/cache/*` — порты и реализации кэша (in‑memory / Redis).
- `tg_wiki/db/*` — конфиг, модели, репозиторий PostgreSQL, порты.
- `tg_wiki/bot/*` — Telegram UI.

---

---

## Troubleshooting

### `Cannot connect to host api.telegram.org:443`
Проверьте доступность Telegram API из вашей сети:

```bash
getent hosts api.telegram.org
curl -I https://api.telegram.org
curl "https://api.telegram.org/bot<ТОКЕН>/getMe"
```

### Ошибки БД / pgvector
- Убедитесь, что подключаетесь к PostgreSQL, где доступно расширение `vector` (проще всего — контейнер `pgvector/pgvector`).
- Проверьте, что выполнены миграции: `alembic upgrade head`.

---

## Лицензия

MIT — см. `LICENSE`.
