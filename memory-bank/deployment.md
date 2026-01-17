# Запуск и деплоймент FinFocus

## Локальная разработка

### Системные требования
- **Python**: >= 3.12
- **OS**: Linux, macOS, Windows (WSL recommended)
- **RAM**: 1GB minimum, 2GB recommended
- **Disk**: 500MB for virtualenv + dependencies

### Установка зависимостей

```bash
# 1. Клонировать репозиторий
git clone https://github.com/SkyTger/FinFocus
cd FinFocus

# 2. Создать виртуальное окружение
python3.12 -m venv .venv

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

## CI/CD Pipeline (Planned)

**GitHub Actions** (.github/workflows/test.yml):
```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - run: pip install -r requirements.txt
      - run: black --check app/
      - run: flake8 app/
      - run: pytest --cov=app --cov-report=xml
      - uses: codecov/codecov-action@v3
```

**Deployment workflow**:
```
git push → GitHub Actions → Tests → Build Docker → Deploy to server
```

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
