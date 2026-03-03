# Solution v1: Setup-скрипты и beta-документация

## Обзор решения
Создаются два платформенных скрипта (`start.sh`, `start.bat`), которые инкапсулируют весь процесс настройки среды и запуска приложения. Параллельно разделяются зависимости на runtime/dev и создается пользовательская документация. Код приложения не затрагивается -- изменения только в инфраструктурных файлах корня проекта.

## Архитектура

### Компоненты

**1. start.sh (Linux/macOS)** -- bash-скрипт, единая точка входа для Unix-систем.
Логика:
- Определить имя Python-интерпретатора (`python3` или `python`)
- Проверить версию >= 3.10 через парсинг вывода `--version`
- Если Python не найден -- вывести инструкцию (apt/brew/python.org)
- Проверить наличие директории `.venv/` -- если нет, создать через `python3 -m venv .venv`
- Активировать venv и проверить наличие установленных зависимостей (проверка по маркер-файлу `.venv/.deps_installed` или по `pip freeze | grep dash`)
- При необходимости -- `pip install -r requirements.txt`
- Запустить `python run.py` в фоновом процессе
- Подождать 2-3 секунды, затем открыть браузер (`xdg-open` на Linux, `open` на macOS)
- При Ctrl+C -- корректно остановить сервер

**2. start.bat (Windows)** -- batch-скрипт для cmd.exe с аналогичной логикой.
Использует `py -3 --version` (Python Launcher) или `python --version` для обнаружения Python. `start http://localhost:8050` для браузера. `.venv\Scripts\activate.bat` для активации.

**3. BETA_README.md** -- документ на русском, структура: 3 шага установки, FAQ, обратная связь.

**4. requirements.txt / requirements-dev.txt** -- разделение зависимостей.

### Диаграмма взаимодействия
```
Пользователь
    |
    v
[start.sh / start.bat]
    |
    +---> Проверка Python 3.10+ ---> [НЕТ] ---> Сообщение + инструкция --> EXIT
    |
    +---> .venv существует? ---> [НЕТ] ---> python -m venv .venv
    |
    +---> Зависимости установлены? ---> [НЕТ] ---> pip install -r requirements.txt
    |         (проверка .venv/.deps_installed)
    |
    +---> python run.py &  (фоновый процесс)
    |
    +---> sleep 3 + open browser (http://localhost:8050)
    |
    +---> Ожидание Ctrl+C ---> kill server --> EXIT
```

## Файловая структура
```
start.sh               -- CREATE: bash-скрипт для Linux/macOS (chmod +x)
start.bat              -- CREATE: batch-скрипт для Windows
BETA_README.md         -- CREATE: инструкция для бета-тестеров (русский)
requirements.txt       -- EDIT: убрать 4 dev-зависимости (pytest, pytest-cov, black, flake8)
requirements-dev.txt   -- CREATE: -r requirements.txt + dev tools
docs/RELEASE_GUIDE.md  -- CREATE: процесс GitHub Release (R5)
```

## Ключевые интерфейсы

### start.sh -- ключевая логика (псевдокод)
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
DEPS_MARKER=".venv/.deps_installed"
REQUIRED_PYTHON_MINOR=10
PORT=8050

# --- Поиск Python ---
find_python() {
    # Пробуем python3, затем python
    # Парсим версию: python3 --version -> "Python 3.12.1"
    # Сравниваем minor >= 10
}

# --- Создание venv ---
ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Создаю виртуальное окружение..."
        "$PYTHON_CMD" -m venv "$VENV_DIR"
    fi
}

# --- Установка зависимостей ---
ensure_deps() {
    if [ ! -f "$DEPS_MARKER" ] || [ requirements.txt -nt "$DEPS_MARKER" ]; then
        echo "Устанавливаю зависимости..."
        "$VENV_DIR/bin/pip" install -r requirements.txt
        touch "$DEPS_MARKER"
    fi
}

# --- Открытие браузера ---
open_browser() {
    sleep 3
    if command -v xdg-open &>/dev/null; then
        xdg-open "http://localhost:$PORT"
    elif command -v open &>/dev/null; then
        open "http://localhost:$PORT"
    fi
}

# --- Запуск ---
find_python
ensure_venv
ensure_deps
echo "Запускаю FinFocus..."
open_browser &
"$VENV_DIR/bin/python" run.py
```

### start.bat -- ключевая логика (псевдокод)
```batch
@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Проверка Python: py -3 --version, затем python --version
REM Парсинг версии, проверка >= 3.10
REM Создание .venv если нет: python -m venv .venv
REM Установка зависимостей если нет маркера
REM Запуск: start http://localhost:8050 && .venv\Scripts\python.exe run.py
```

### requirements.txt (после редактирования)
```
# Core framework
dash==2.17.1
dash-bootstrap-components==1.5.0
plotly==5.17.0

# Database and ORM
sqlalchemy==2.0.23
alembic==1.13.1

# Date handling
python-dateutil==2.8.2

# Logging
loguru>=0.7.0

# Utils
python-dotenv==1.0.0
```

### requirements-dev.txt
```
-r requirements.txt

# Development and testing
pytest==7.4.3
pytest-cov==4.1.0
black==23.11.0
flake8==6.1.0
```

## Обработка ошибок

| Сценарий | Поведение скрипта |
|----------|-------------------|
| Python не установлен | Понятное сообщение на русском + ссылки: python.org/downloads, инструкции apt/brew |
| Python < 3.10 | Сообщение: "Найден Python X.Y, требуется 3.10 или новее" + ссылка на обновление |
| pip install упал (сеть) | Ошибка pip пробрасывается пользователю; сообщение "Проверьте подключение к интернету" |
| Порт 8050 занят | Dash сам выводит ошибку в терминал; в BETA_README.md описан workaround (PORT=8051) |
| `python -m venv` не работает | На Ubuntu/Debian может не быть `python3-venv`; start.sh проверяет и выводит `sudo apt install python3-venv` |
| Повторный запуск при работающем сервере | Порт занят -- Dash выдаст ошибку; в FAQ описано "как остановить" |

## План реализации

### Батч 1 (3 файла): requirements + start.sh + start.bat
1. **requirements.txt** -- убрать 4 dev-строки (pytest, pytest-cov, black, flake8)
2. **requirements-dev.txt** -- CREATE: `-r requirements.txt` + 4 dev-зависимости
3. **start.sh** -- CREATE: полный bash-скрипт с логикой из раздела "Ключевые интерфейсы"
4. **start.bat** -- CREATE: полный batch-скрипт

### Батч 2 (2 файла): документация
5. **BETA_README.md** -- CREATE: пошаговая инструкция
6. **docs/RELEASE_GUIDE.md** -- CREATE: процесс GitHub Release

### Проверки после каждого батча
- `pytest -k "not test_budget_change_updates_allocation"` -- все тесты проходят
- `black app/` + `flake8 app/` -- без ошибок (код app/ не менялся, но проверяем)
- Ручной тест `start.sh` на Linux

## Зависимости

- **Внешние**: отсутствуют. Все зависимости уже описаны в requirements.txt
- **Между батчами**: Батч 2 не зависит от Батча 1 технически, но логически BETA_README.md ссылается на start.sh/start.bat
- **Порядок внутри Батча 1**: сначала requirements.txt (чтобы start.sh ссылался на корректный файл), затем start.sh, затем start.bat

## Риски и mitigation

| Риск | Вероятность | Mitigation |
|------|-------------|------------|
| На Ubuntu нет `python3-venv` пакета | Средняя | start.sh проверяет `python3 -m venv --help` и выводит инструкцию `sudo apt install python3.X-venv` |
| Windows Python не в PATH | Средняя | start.bat пробует `py -3` (Python Launcher, ставится с python.org) и `python`, выводит инструкцию "Отметьте 'Add to PATH' при установке" |
| Кодировка cmd.exe ломает русский текст | Средняя | `chcp 65001` в начале start.bat переключает на UTF-8 |
| macOS Gatekeeper блокирует start.sh | Низкая | BETA_README.md описывает `chmod +x start.sh` и запуск через `./start.sh` |
| pip freeze проверка медленная при каждом запуске | Низкая | Используем маркер-файл `.venv/.deps_installed` вместо pip freeze; файл инвалидируется если requirements.txt новее маркера (`-nt` в bash, `forfiles` в bat) |
| `set -e` прерывает скрипт на нефатальной ошибке | Низкая | Критические секции (open_browser) запускаются с `|| true`; фоновые процессы не прерывают основной |

## Requirements Traceability Matrix (RTM)

| # | Requirement (дословно из спецификации) | Секция spec | Реализация в solution | Тип |
|---|----------------------------------------|-------------|----------------------|-----|
| R1 | Start-скрипт для Linux/macOS (`start.sh`): проверка Python 3.10+, venv, pip install, run.py, браузер | R1 | `start.sh` -- bash-скрипт с find_python, ensure_venv, ensure_deps, open_browser | Integration |
| R1a | Повторный запуск -- пропускает создание venv и установку | R1 | Маркер-файл `.venv/.deps_installed` + проверка `-d .venv` | Edge |
| R1b | Понятные сообщения на русском | R1 | Все echo-строки на русском | UX |
| R2 | Start-скрипт для Windows (`start.bat`): аналогичная логика | R2 | `start.bat` -- batch-скрипт с `py -3`, `chcp 65001` | Integration |
| R3 | BETA_README.md: инструкция на русском, 3 шага, FAQ, обратная связь | R3 | `BETA_README.md` с разделами: установка Python, запуск, FAQ, bug report | UX |
| R4 | Убрать dev-зависимости из requirements.txt, создать requirements-dev.txt | R4 | `requirements.txt` -- EDIT (убрать 4 строки), `requirements-dev.txt` -- CREATE | Integration |
| R5 | Документация процесса GitHub Release (tag format, release notes) | R5 | `docs/RELEASE_GUIDE.md` с шаблоном release notes и tag format | UX |

## Blast Radius

### Прямые изменения (файлы которые будут созданы/изменены)
- `start.sh` -- CREATE: bash-скрипт запуска
- `start.bat` -- CREATE: batch-скрипт запуска
- `BETA_README.md` -- CREATE: инструкция для тестеров
- `requirements.txt` -- EDIT: убрать 4 dev-зависимости
- `requirements-dev.txt` -- CREATE: runtime + dev зависимости
- `docs/RELEASE_GUIDE.md` -- CREATE: процесс релиза

### Связанные файлы (могут быть затронуты)
- `.gitignore` -- проверить что `.venv` и `data/*.db` уже игнорируются
- `setup.cfg` -- не меняется, но содержит конфигурацию flake8/pytest
- `.obsidian-docs/ROADMAP.md` -- обновить статус Phase 3 после реализации
- `run.py` -- НЕ меняется, но является точкой запуска из скриптов
- `CLAUDE.md` -- возможно обновить секцию "Development Commands"

### Проверить после реализации
- [ ] `pytest -k "not test_budget_change_updates_allocation"` проходит
- [ ] `black app/` + `flake8 app/` без ошибок
- [ ] `start.sh` запускается на Linux (ручной тест)
- [ ] `.venv/.deps_installed` маркер создается после pip install
- [ ] Повторный запуск start.sh не переустанавливает зависимости
- [ ] `requirements-dev.txt` корректно подключает `requirements.txt` через `-r`
- [ ] Русский текст в start.bat корректно отображается в cmd.exe (chcp 65001)
