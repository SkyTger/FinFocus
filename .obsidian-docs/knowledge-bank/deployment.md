---
name: deployment
description: Запуск и деплоймент FinFocus — два способа доставки (setup-скрипты и PyInstaller), оба существуют, выбор основного отложен до аудита
type: reference
---

# Запуск и деплоймент FinFocus

> **Открытый вопрос (2026-08-19)**: в проекте сейчас два независимых
> способа доставки конечному пользователю — setup-скрипты
> (`start.sh`/`start.bat`, требуют установленный Python) и PyInstaller-
> бандл (standalone exe/бинарник, не требует Python). Какой из них
> становится основным — решение отложено: пользователь сначала проводит
> аудит проекта и сейчас сфокусирован на личном использовании, упаковка
> для внешних тестеров не приоритет. Ни один из способов не считать
> "устаревшим" до явного решения.

## Локальная разработка

### Системные требования
- **Python**: 3.10 – 3.12 (см. `tech-stack.md` — 3.13 несовместим с
  SQLAlchemy 2.0.23). Локально разработка ведётся на 3.10.12.
- **OS**: Linux, macOS, Windows (WSL recommended)
- **RAM**: 1GB minimum, 2GB recommended
- **Disk**: 500MB for virtualenv + dependencies

### Установка зависимостей

```bash
# 1. Клонировать репозиторий
git clone https://github.com/SkyTger/FinFocus
cd FinFocus

# 2. Создать виртуальное окружение (любая версия 3.10-3.12)
python3.10 -m venv .venv

# 3. Активировать
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows

# 4. Установить зависимости
pip install -r requirements.txt
```

### Запуск приложения

```bash
# Базовый запуск
python run.py

# С кастомными настройками
PORT=8080 DEBUG=False python run.py

# Доступ
# http://localhost:8050 (default)
```

**Автоинициализация БД**:
- При первом запуске создается `data/finfocus.db`
- Таблицы создаются автоматически через `init_database()` в `run.py`
- Seed данные: `python scripts/seed_test_data.py` (optional)

## Beta Delivery (Текущий способ для тестеров)

### Концепция
Два платформенных скрипта с автонастройкой окружения — нетехнический пользователь делает двойной клик и получает приложение в браузере.

### Скрипты запуска

| Файл | Платформа | Размер |
|------|-----------|--------|
| `start.sh` | Linux / macOS | 168 строк |
| `start.bat` | Windows | 148 строк |

**Что делают скрипты (оба):**
1. Проверяют Python 3.10+ (совместимость с диапазоном, поддерживаемым проектом — 3.10-3.12, см. `tech-stack.md`)
2. Создают `.venv/` если не существует
3. Устанавливают зависимости из `requirements.txt` — пропускают если `.venv/.deps_installed` уже есть
4. Проверяют свободен ли порт 8050
5. Запускают `python run.py` и открывают браузер

**Маркер идемпотентности**: `.venv/.deps_installed`
- Создается командой `touch .venv/.deps_installed` после успешного `pip install`
- start.bat: xcopy /D /L имитирует timestamp-сравнение (dry-run)
- Повторные запуски не переустанавливают зависимости

**start.sh специфика:**
- Проверка порта: fallback chain `ss` → `lsof` → `netstat`
- Браузер: `xdg-open` (Linux) или `open` (macOS)
- Trap handler для cleanup при Ctrl+C
- Цветной вывод через ANSI-коды

**start.bat специфика:**
- Python поиск: `py -3` приоритет, `python` fallback
- Версия парсится через `py -3 -c "import sys; print(sys.version_info...)"`
- Порт: `netstat -an`
- Пауза при ошибке (`pause`) для видимости сообщений

### Разделение зависимостей

```
requirements.txt      ← только runtime (Dash, SQLAlchemy, ...)
requirements-dev.txt  ← dev/test (pytest, black, flake8, coverage)
```

Бета-тестеры устанавливают только `requirements.txt` через start-скрипты.
Разработчики: `pip install -r requirements-dev.txt`.

### Документация для тестеров

**`BETA_README.md`** (86 строк, в корне репозитория):
- 3-шаговая установка: скачать ZIP → запустить скрипт → открыть `localhost:8050`
- 6 FAQ: Python не найден, порт занят, ошибки зависимостей и др.

**`docs/RELEASE_GUIDE.md`** (82 строки):
- Формат тега: `v0.9.0-beta.N`
- ZIP через `git archive`: автоматически исключает `.git`, `.venv`, `data/`
- Шаблон Release Notes и чеклист выпуска

### Ограничения setup-скриптов
- Приложение работает в браузере (`localhost:8050`), не нативное окно
- Требует установленный Python 3.10+ на машине тестера (не включён в поставку)
- Backlog: нативное окно (flaskwebgui/pywebview) — не реализовано

---

## PyInstaller-бандл (реализовано, работает в CI)

### Статус
В отличие от прежней формулировки "отложено post-beta" — **PyInstaller
сборка реально реализована и работает**: конфиг `finfocus.spec` в корне
репозитория, автоматическая сборка в `.github/workflows/build.yml`.
Появилось в коммите `d9e93c6`.

Не путать со статусом "основной способ доставки" — это отдельный
нерешённый вопрос (см. врезку в начале файла).

### Что делает пайплайн
- Собирает **onedir**-бандл (портативная папка, не единый exe) через
  `pyinstaller finfocus.spec --noconfirm`
- Две платформы: `windows-latest` → `FinFocus.exe`, `macos-latest` →
  бинарник `FinFocus` (обе — Python 3.12 в CI)
- Smoke test после сборки: проверка что исполняемый файл существует
- ZIP-архив (`FinFocus-windows.zip` / `FinFocus-macos.zip`) прикладывается
  к GitHub Release автоматически при пуше тега `v*`
- Linux-сборка в `build.yml` не настроена (только Windows и macOS)

### Централизация путей: `app/core/paths.py`

Значимая архитектурная деталь, которую ввёл PyInstaller: приложению нужно
по-разному находить свои файлы в двух режимах запуска, и это вынесено в
отдельный модуль.

| Режим | Как определяется | Куда указывают пути |
|-------|-------------------|----------------------|
| Normal | `is_frozen()` → `False` | Относительно корня проекта |
| Frozen (PyInstaller) | `is_frozen()` → `True` (`sys.frozen` выставлен) | assets — `sys._MEIPASS` (временная распаковка бандла); данные пользователя — директория, где лежит exe |

Ключевые функции:
- `is_frozen()` - проверка режима запуска
- `get_bundle_dir()` - директория с кодом/assets (`sys._MEIPASS` во
  frozen-режиме, корень проекта в normal)
- `get_app_dir()` - директория для пользовательских данных (папка exe во
  frozen-режиме, корень проекта в normal)
- `get_data_dir()` / `get_logs_dir()` - `data/` и `logs/` от `get_app_dir()`,
  создаются автоматически при первом обращении
- `get_assets_dir()` - `app/assets/` от `get_bundle_dir()`

Важно: `app/core/migrations.py` уже переведён на `get_data_dir()` вместо
хардкода пути `data/finfocus.db` — миграции работают одинаково в обоих
режимах.

### Исключения из сборки
`finfocus.spec` явно исключает `alembic`, `tkinter`, `unittest`, `pytest`,
`test` — не нужны в рантайме конечного пользователя, уменьшают размер
бандла.

---

## Environment Variables

**Поддерживаемые переменные** (через `.env` файл):

```bash
# .env (НЕ коммитить в git!)
DATABASE_URL=sqlite:///data/finfocus.db  # SQLite по умолчанию
DEBUG=True                               # Debug mode
PORT=8050                                # HTTP port
```

**Production пример**:
```bash
DATABASE_URL=postgresql://user:pass@host:5432/finfocus
DEBUG=False
PORT=80
```

## База данных

### SQLite (Development)
**Путь**: `data/finfocus.db`
**Инициализация**: Автоматическая через `init_database()`

**Пересоздание БД**:
```bash
rm data/finfocus.db       # Удалить старую
python run.py             # Создаст новую
python scripts/seed_test_data.py  # Заполнить тестовыми данными
```

### PostgreSQL (Production - planned)
**Connection string**:
```
postgresql://username:password@host:port/database
```

**Миграции** (planned):
```bash
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

## Quality Checks

**Перед коммитом** (рекомендуется):
```bash
# Форматирование
black app/

# Линтер
flake8 app/

# Тесты
pytest -v

# Coverage
pytest --cov=app --cov-report=term
```

**Scripts** (planned):
```bash
./scripts/run_lint.sh    # black + flake8
./scripts/run_tests.sh   # pytest с coverage
```

## Production Deployment (Planned)

### Docker (recommended)

**Dockerfile** (planned):
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8050
CMD ["gunicorn", "-b", "0.0.0.0:8050", "app.main:server"]
```

**docker-compose.yml** (planned):
```yaml
version: '3.8'
services:
  web:
    build: .
    ports:
      - "8050:8050"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/finfocus
    depends_on:
      - db

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=finfocus
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass

volumes:
  postgres_data:
```

### WSGI Server (gunicorn)

**Команда запуска**:
```bash
gunicorn -w 4 -b 0.0.0.0:8050 app.main:server
```

**gunicorn.conf.py** (planned):
```python
workers = 4
worker_class = "sync"
bind = "0.0.0.0:8050"
timeout = 120
```

### Reverse Proxy (nginx)

**nginx.conf** (planned):
```nginx
server {
    listen 80;
    server_name finfocus.example.com;

    location / {
        proxy_pass http://127.0.0.1:8050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## CI/CD Pipeline (реализовано частично)

Два независимых workflow в `.github/workflows/`, оба реально существуют
(не "planned"):

### `tests.yml` — прогон тестов
- Триггеры: push в `main`, pull_request, ручной запуск
- Матрица: Python 3.10 и 3.12, `fail-fast: false`
- Шаги: `pip install -r requirements-dev.txt` → `pytest -q`
- Линтеры (`black --check`, `flake8`) **намеренно не включены** — в
  `app/` есть pre-existing E501, было решено не блокировать CI ими
  (детали — `testing.md`)

### `build.yml` — сборка PyInstaller-бандла
- Триггер: push тега `v*` или ручной запуск (не на каждый push/PR)
- Python 3.12, платформы Windows + macOS
- Собирает `finfocus.spec`, прикладывает ZIP к GitHub Release

### Чего нет
- Codecov / отчётов покрытия в CI
- Docker-сборки в CI
- Автоматического деплоя на сервер (весь пайплайн — тесты + сборка
  дистрибутивов, без "deploy" шага, что логично для desktop-приложения)

## Monitoring (Planned)

**Application metrics**:
- Response time (target: < 200ms)
- Error rate (target: < 0.1%)
- Uptime (target: 99%)

**Database metrics**:
- Query performance
- Connection pool usage
- Disk space

**Tools**:
- Sentry for error tracking
- Prometheus + Grafana for metrics
- CloudWatch/DataDog for logs

## Backup Strategy (Planned)

**Database backups**:
- Daily automated backups
- 30 days retention
- Off-site storage (S3)

**Backup script**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d)
pg_dump finfocus > backup_$DATE.sql
aws s3 cp backup_$DATE.sql s3://finfocus-backups/
```

## Troubleshooting

**Проблема**: Database locked (SQLite)
- **Решение**: Закрыть все sessions, перезапустить app

**Проблема**: Port 8050 уже используется
- **Решение**: `PORT=8080 python run.py`

**Проблема**: Import errors
- **Решение**: Проверить virtualenv активирован, переустановить зависимости

**Проблема**: Database not initialized
- **Решение**: Удалить `data/finfocus.db`, перезапустить `run.py`

---

Референсы:
- Dash Deployment: https://dash.plotly.com/deployment
- Gunicorn Docs: https://docs.gunicorn.org/
- Docker Best Practices: https://docs.docker.com/develop/dev-best-practices/
- `finfocus.spec`, `.github/workflows/build.yml` — PyInstaller-сборка
- `app/core/paths.py` — централизация путей normal/frozen режимов

---

**Последнее обновление**: 2026-08-19 (аудит KB: устранено противоречие
Python 3.12/3.10+, PyInstaller зафиксирован как реализованный факт вместо
backlog, добавлен `app/core/paths.py`, описан реальный CI из двух workflow;
выбор основного способа доставки — открытый вопрос, отложен до аудита проекта)
