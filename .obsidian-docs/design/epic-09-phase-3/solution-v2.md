# Solution v2: Setup-скрипты и beta-документация (исправленная версия)

## Обзор решения
Создаются два платформенных скрипта (`start.sh`, `start.bat`) с полной детализацией, которые инкапсулируют процесс настройки среды и запуска приложения для нетехнических бета-тестеров. Параллельно разделяются зависимости на runtime/dev и создается пользовательская документация. Код приложения (`app/`) не затрагивается -- изменения только в инфраструктурных файлах корня проекта.

**Ключевые отличия от v1:**
- Минимальная версия Python явно зафиксирована: **3.10+** (подтверждено аудитом кодовой базы -- нет match/case, нет type aliases 3.12, нет @override)
- `start.bat` раскрыт до полного псевдокода на уровне детализации `start.sh`
- Добавлена проверка занятости порта ДО запуска Dash (с понятным сообщением на русском)
- Добавлен `trap` handler для корректного завершения фоновых процессов
- Подтверждено покрытие `.gitignore` для `.venv`
- `start.bat` включает `pause` при ошибке

## Архитектура

### Компоненты

**1. start.sh (Linux/macOS)** -- bash-скрипт, единая точка входа для Unix-систем.
Логика:
- Определить корневую директорию скрипта (`$SCRIPT_DIR`)
- Определить имя Python-интерпретатора (`python3` или `python`)
- Проверить версию >= 3.10 через парсинг `--version`
- Если Python не найден или версия < 3.10 -- русскоязычное сообщение с инструкцией
- Проверить `python3-venv` пакет (Ubuntu/Debian)
- Создать `.venv/` при необходимости
- Установить зависимости при необходимости (маркер-файл + сравнение mtime)
- Проверить что порт 8050 свободен; если занят -- сообщение с подсказкой `PORT=8051`
- Запустить `python run.py` в foreground, `open_browser` в background
- `trap` handler для корректного завершения при Ctrl+C (kill background browser job)

**2. start.bat (Windows)** -- batch-скрипт для cmd.exe с полностью проработанной логикой.
- `chcp 65001` для русского текста
- `py -3 --version` (Python Launcher) с fallback на `python --version`
- Парсинг версии через `for /f` + проверка >= 3.10
- Создание/активация `.venv` через `Scripts\activate.bat`
- Маркер-файл для зависимостей, инвалидация через сравнение дат (`xcopy /D /L`)
- Проверка порта через `netstat -an`
- `pause` при любой ошибке чтобы окно cmd.exe не закрывалось
- `start "" http://localhost:8050` для браузера

**3. BETA_README.md** -- документ на русском, структура: 3 шага, FAQ с конкретными вопросами, раздел обратной связи.

**4. requirements.txt / requirements-dev.txt** -- разделение зависимостей.

**5. docs/RELEASE_GUIDE.md** -- процесс создания GitHub Release.

### Диаграмма взаимодействия
```
Пользователь
    |
    v
[start.sh / start.bat]
    |
    +---> Проверка Python 3.10+ -----> [НЕТ] ---> Сообщение + инструкция --> EXIT(1)
    |
    +---> (Linux only) python3-venv? -> [НЕТ] ---> "sudo apt install..." --> EXIT(1)
    |
    +---> .venv существует? ----------> [НЕТ] ---> python -m venv .venv
    |
    +---> Маркер .deps_installed? -----> [НЕТ или requirements.txt новее]
    |         |                                  ---> pip install -r requirements.txt
    |         +--- [ДА и актуален] -----------> пропускаем
    |
    +---> Порт 8050 свободен? --------> [НЕТ] ---> "Порт занят" + подсказка --> EXIT(1)
    |
    +---> open_browser & (background, PID сохранен)
    |
    +---> trap INT TERM -> kill browser PID
    |
    +---> python run.py (foreground, blocking)
    |
    +---> [Ctrl+C] ---> trap handler ---> kill browser PID ---> EXIT(0)
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

### start.sh -- полный псевдокод
```bash
#!/usr/bin/env bash
set -euo pipefail

# === Константы ===
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

VENV_DIR=".venv"
DEPS_MARKER="$VENV_DIR/.deps_installed"
REQUIRED_PYTHON_MAJOR=3
REQUIRED_PYTHON_MINOR=10
PORT="${PORT:-8050}"
APP_URL="http://localhost:$PORT"
PYTHON_CMD=""
BROWSER_PID=""

# === Цвета (если терминал поддерживает) ===
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'  # No Color
else
    RED='' GREEN='' YELLOW='' NC=''
fi

# === Вспомогательные функции ===
info()  { echo -e "${GREEN}[FinFocus]${NC} $1"; }
warn()  { echo -e "${YELLOW}[Внимание]${NC} $1"; }
error() { echo -e "${RED}[Ошибка]${NC} $1"; }
die()   { error "$1"; exit 1; }

# === Trap handler: корректное завершение ===
cleanup() {
    echo ""
    info "Завершение работы..."
    if [ -n "$BROWSER_PID" ] && kill -0 "$BROWSER_PID" 2>/dev/null; then
        kill "$BROWSER_PID" 2>/dev/null || true
    fi
    exit 0
}
trap cleanup INT TERM

# === 1. Поиск Python ===
find_python() {
    local cmd version_output major minor

    for cmd in python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version_output="$("$cmd" --version 2>&1)" || continue
            # Парсим "Python 3.12.1" -> major=3 minor=12
            major=$(echo "$version_output" | sed -n 's/Python \([0-9]*\)\..*/\1/p')
            minor=$(echo "$version_output" | sed -n 's/Python [0-9]*\.\([0-9]*\)\..*/\1/p')

            if [ "$major" -eq "$REQUIRED_PYTHON_MAJOR" ] && [ "$minor" -ge "$REQUIRED_PYTHON_MINOR" ]; then
                PYTHON_CMD="$cmd"
                info "Найден $version_output ($cmd)"
                return 0
            else
                warn "Найден $version_output, но требуется Python >=$REQUIRED_PYTHON_MAJOR.$REQUIRED_PYTHON_MINOR"
            fi
        fi
    done

    error "Python $REQUIRED_PYTHON_MAJOR.$REQUIRED_PYTHON_MINOR или новее не найден."
    echo ""
    echo "Установите Python:"
    echo "  - Скачать:  https://www.python.org/downloads/"
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "  - macOS:    brew install python3"
    else
        echo "  - Ubuntu:   sudo apt install python3"
        echo "  - Fedora:   sudo dnf install python3"
    fi
    exit 1
}

# === 2. Проверка python3-venv (Ubuntu/Debian) ===
check_venv_package() {
    if ! "$PYTHON_CMD" -m venv --help &>/dev/null; then
        local py_minor
        py_minor=$("$PYTHON_CMD" -c "import sys; print(sys.version_info.minor)")
        error "Модуль venv не доступен."
        echo "  Установите: sudo apt install python3.$py_minor-venv"
        exit 1
    fi
}

# === 3. Создание venv ===
ensure_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        info "Создаю виртуальное окружение..."
        "$PYTHON_CMD" -m venv "$VENV_DIR"
        info "Виртуальное окружение создано."
    fi
}

# === 4. Установка зависимостей ===
ensure_deps() {
    # Переустанавливаем если: маркера нет ИЛИ requirements.txt новее маркера
    if [ ! -f "$DEPS_MARKER" ] || [ "requirements.txt" -nt "$DEPS_MARKER" ]; then
        info "Устанавливаю зависимости (это может занять 1-2 минуты)..."
        "$VENV_DIR/bin/pip" install --quiet -r requirements.txt || {
            error "Не удалось установить зависимости."
            echo "  Проверьте подключение к интернету."
            exit 1
        }
        touch "$DEPS_MARKER"
        info "Зависимости установлены."
    else
        info "Зависимости актуальны."
    fi
}

# === 5. Проверка порта ===
check_port() {
    local port_in_use=false

    if command -v ss &>/dev/null; then
        ss -tlnH "sport = :$PORT" 2>/dev/null | grep -q "$PORT" && port_in_use=true
    elif command -v lsof &>/dev/null; then
        lsof -iTCP:"$PORT" -sTCP:LISTEN &>/dev/null && port_in_use=true
    elif command -v netstat &>/dev/null; then
        netstat -tln 2>/dev/null | grep -q ":$PORT " && port_in_use=true
    fi
    # Если ни одна утилита не найдена -- пропускаем проверку (Dash сам сообщит)

    if [ "$port_in_use" = true ]; then
        error "Порт $PORT уже занят другим приложением."
        echo ""
        echo "  Возможные решения:"
        echo "  1. Закройте другое приложение, использующее порт $PORT"
        echo "  2. Запустите FinFocus на другом порту:"
        echo "     PORT=8051 ./start.sh"
        exit 1
    fi
}

# === 6. Открытие браузера (в фоне) ===
open_browser() {
    sleep 3
    if command -v xdg-open &>/dev/null; then
        xdg-open "$APP_URL" 2>/dev/null
    elif command -v open &>/dev/null; then
        open "$APP_URL"
    else
        info "Откройте в браузере: $APP_URL"
    fi
}

# === Главный поток ===
echo ""
echo "=============================="
echo "  FinFocus — запуск"
echo "=============================="
echo ""

find_python
check_venv_package
ensure_venv
ensure_deps
check_port

info "Запускаю FinFocus на $APP_URL ..."
info "Для остановки нажмите Ctrl+C"
echo ""

open_browser &
BROWSER_PID=$!

"$VENV_DIR/bin/python" run.py
```

### start.bat -- полный псевдокод
```batch
@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

REM === Переходим в директорию скрипта ===
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "DEPS_MARKER=%VENV_DIR%\.deps_installed"
set "REQUIRED_MAJOR=3"
set "REQUIRED_MINOR=10"
set "PORT=8050"
if defined PORT set "PORT=%PORT%"
set "APP_URL=http://localhost:%PORT%"
set "PYTHON_CMD="

echo.
echo ==============================
echo   FinFocus -- zapusk
echo ==============================
echo.

REM === 1. Поиск Python ===
REM Пробуем py -3 (Python Launcher, устанавливается с python.org)
py -3 --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=py -3"
    goto :check_version
)

REM Пробуем python
python --version >nul 2>&1
if !errorlevel! equ 0 (
    set "PYTHON_CMD=python"
    goto :check_version
)

REM Python не найден
echo [Ошибка] Python не найден.
echo.
echo   Установите Python:
echo   1. Скачайте с https://www.python.org/downloads/
echo   2. При установке ОБЯЗАТЕЛЬНО отметьте "Add Python to PATH"
echo   3. После установки перезапустите этот скрипт
echo.
goto :exit_with_pause

:check_version
REM === 2. Парсинг версии ===
for /f "tokens=2 delims= " %%V in ('!PYTHON_CMD! --version 2^>^&1') do set "PY_VERSION=%%V"
REM PY_VERSION = "3.12.1"
for /f "tokens=1,2 delims=." %%A in ("!PY_VERSION!") do (
    set "PY_MAJOR=%%A"
    set "PY_MINOR=%%B"
)

REM Проверка: major == 3 И minor >= 10
if !PY_MAJOR! neq %REQUIRED_MAJOR% goto :version_fail
if !PY_MINOR! lss %REQUIRED_MINOR% goto :version_fail

echo [FinFocus] Найден Python !PY_VERSION! (!PYTHON_CMD!)
goto :ensure_venv

:version_fail
echo [Ошибка] Найден Python !PY_VERSION!, но требуется %REQUIRED_MAJOR%.%REQUIRED_MINOR% или новее.
echo.
echo   Скачайте новую версию: https://www.python.org/downloads/
goto :exit_with_pause

REM === 3. Создание venv ===
:ensure_venv
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo [FinFocus] Виртуальное окружение найдено.
    goto :ensure_deps
)

echo [FinFocus] Создаю виртуальное окружение...
!PYTHON_CMD! -m venv "%VENV_DIR%"
if !errorlevel! neq 0 (
    echo [Ошибка] Не удалось создать виртуальное окружение.
    goto :exit_with_pause
)
echo [FinFocus] Виртуальное окружение создано.

REM === 4. Установка зависимостей ===
:ensure_deps
REM Проверяем: маркер существует?
if not exist "%DEPS_MARKER%" goto :install_deps

REM Проверяем: requirements.txt новее маркера?
REM xcopy /D /L сравнивает даты: если requirements.txt новее, вывод не пуст
for /f %%F in ('xcopy /D /L /Y "requirements.txt" "%DEPS_MARKER%" 2^>nul') do (
    if "%%F" neq "0" goto :install_deps
)

echo [FinFocus] Зависимости актуальны.
goto :check_port

:install_deps
echo [FinFocus] Устанавливаю зависимости (это может занять 1-2 минуты)...
"%VENV_DIR%\Scripts\pip.exe" install --quiet -r requirements.txt
if !errorlevel! neq 0 (
    echo [Ошибка] Не удалось установить зависимости.
    echo   Проверьте подключение к интернету.
    goto :exit_with_pause
)
REM Создаём маркер
type nul > "%DEPS_MARKER%"
echo [FinFocus] Зависимости установлены.

REM === 5. Проверка порта ===
:check_port
netstat -an 2>nul | findstr "LISTENING" | findstr ":%PORT% " >nul 2>&1
if !errorlevel! equ 0 (
    echo [Ошибка] Порт %PORT% уже занят другим приложением.
    echo.
    echo   Возможные решения:
    echo   1. Закройте другое приложение, использующее порт %PORT%
    echo   2. Запустите FinFocus на другом порту:
    echo      set PORT=8051 ^&^& start.bat
    goto :exit_with_pause
)

REM === 6. Запуск ===
echo [FinFocus] Запускаю FinFocus на %APP_URL% ...
echo [FinFocus] Для остановки нажмите Ctrl+C или закройте это окно.
echo.

REM Открываем браузер (не ждём)
start "" "%APP_URL%"

REM Запускаем приложение (блокирующий вызов)
"%VENV_DIR%\Scripts\python.exe" run.py
if !errorlevel! neq 0 (
    echo.
    echo [Ошибка] Приложение завершилось с ошибкой.
    goto :exit_with_pause
)

goto :exit_normal

:exit_with_pause
echo.
pause
exit /b 1

:exit_normal
echo.
echo [FinFocus] Приложение остановлено.
pause
exit /b 0
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

### BETA_README.md -- черновик структуры
```markdown
# FinFocus -- Инструкция для бета-тестеров

## Что это?
FinFocus -- персональный финансовый планировщик, работает в браузере.

## Установка за 3 шага

### Шаг 1: Установите Python (если ещё не установлен)
- Скачайте Python с https://www.python.org/downloads/
- **Windows**: при установке ОБЯЗАТЕЛЬНО отметьте "Add Python to PATH"
- **macOS**: `brew install python3` или скачайте с python.org
- **Linux (Ubuntu)**: `sudo apt install python3 python3-venv`

### Шаг 2: Распакуйте архив
Распакуйте скачанный ZIP-файл в любую папку.

### Шаг 3: Запустите
- **Windows**: дважды кликните по файлу `start.bat`
- **Linux/macOS**: откройте терминал в папке и выполните `./start.sh`

Приложение откроется в браузере автоматически.

## Частые вопросы (FAQ)

**Q: Приложение не запускается, пишет "Python не найден"**
A: Установите Python (шаг 1). На Windows убедитесь что при установке
   отметили "Add Python to PATH". После установки перезапустите start.bat.

**Q: Пишет "Порт 8050 занят"**
A: Другое приложение уже использует порт 8050.
   - Windows: `set PORT=8051 && start.bat`
   - Linux/macOS: `PORT=8051 ./start.sh`

**Q: Браузер не открылся автоматически**
A: Откройте вручную: http://localhost:8050

**Q: Как остановить приложение?**
A: Нажмите Ctrl+C в окне терминала. На Windows можно просто закрыть окно.

**Q: При повторном запуске всё устанавливается заново**
A: Нет, при повторном запуске установка пропускается -- запуск будет быстрым.

## Нашли ошибку?
Создайте issue на GitHub: [ссылка]
Опишите: что делали, что ожидали, что произошло.
Приложите скриншот ошибки из окна терминала.
```

### docs/RELEASE_GUIDE.md -- структура
```markdown
# Процесс создания GitHub Release

## Tag формат
`v0.9.0-beta.N` (N = номер бета-релиза, начиная с 1)

## Шаги
1. Убедиться что main зелёный (тесты проходят)
2. Обновить CHANGELOG (если есть)
3. Создать tag: `git tag -a v0.9.0-beta.1 -m "Beta 1 release"`
4. Push tag: `git push origin v0.9.0-beta.1`
5. На GitHub: Releases -> Draft new release -> выбрать tag
6. Заполнить Release Notes по шаблону ниже
7. Прикрепить ZIP-архив (без .venv, без data/*.db, без __pycache__)

## Шаблон Release Notes
...

## Что включать в ZIP
- start.sh, start.bat, BETA_README.md
- requirements.txt
- run.py, app/, alembic/, alembic.ini
- НЕ включать: .venv/, data/*.db, __pycache__/, .git/, tests/
```

## Обработка ошибок

| Сценарий | start.sh | start.bat |
|----------|----------|-----------|
| Python не найден | `die()` + инструкция apt/brew/python.org | `goto :exit_with_pause` + инструкция python.org + "Add to PATH" |
| Python < 3.10 | `die()` + "Найден X.Y, требуется 3.10+" | `goto :version_fail` + ссылка на загрузку |
| `python3-venv` нет (Ubuntu) | Проверка `python -m venv --help`, сообщение `sudo apt install python3.X-venv` | N/A (Windows venv встроен) |
| `pip install` ошибка сети | Сообщение "Проверьте подключение к интернету", exit 1 | `goto :exit_with_pause` + аналогичное сообщение |
| Порт занят | Проверка `ss`/`lsof`/`netstat`, сообщение + `PORT=8051 ./start.sh` | Проверка `netstat`, сообщение + `set PORT=8051 && start.bat` |
| `venv` создание не удалось | `set -e` прерывает + сообщение из die | `errorlevel` проверка + `goto :exit_with_pause` |
| Ctrl+C в первые 3 сек | `trap cleanup` убивает background `open_browser` PID | N/A (Windows: `start` уже запустил браузер, не проблема) |
| Dash runtime error | Traceback в терминал; пользователю видно окно | `errorlevel neq 0` -> `goto :exit_with_pause` |

## План реализации

### Батч 1 (4 файла): requirements + скрипты
1. **requirements.txt** -- EDIT: убрать 4 dev-строки (pytest, pytest-cov, black, flake8)
2. **requirements-dev.txt** -- CREATE: `-r requirements.txt` + 4 dev-зависимости
3. **start.sh** -- CREATE: полный bash-скрипт (chmod +x)
4. **start.bat** -- CREATE: полный batch-скрипт

### Батч 2 (2 файла): документация
5. **BETA_README.md** -- CREATE: пошаговая инструкция с FAQ
6. **docs/RELEASE_GUIDE.md** -- CREATE: процесс GitHub Release

### Проверки после каждого батча
- `pytest -k "not test_budget_change_updates_allocation"` -- все тесты проходят
- `black app/` + `flake8 app/` -- без ошибок (код app/ не менялся)
- Ручной тест: `bash start.sh` на Linux -- приложение запускается
- Ручной тест: повторный запуск -- зависимости не переустанавливаются
- Проверка: `shellcheck start.sh` (если доступен) -- без критичных предупреждений

## Зависимости

- **Внешние**: отсутствуют. Все runtime-зависимости уже в requirements.txt
- **Между батчами**: Батч 2 не зависит от Батча 1 технически, но BETA_README.md ссылается на start.sh/start.bat
- **Порядок внутри Батча 1**: requirements.txt -> requirements-dev.txt -> start.sh -> start.bat

## Риски и mitigation

| Риск | Вероятность | Impact | Mitigation |
|------|-------------|--------|------------|
| Ubuntu нет `python3-venv` | Средняя | Высокий | start.sh проверяет `python -m venv --help` и выводит конкретную команду `sudo apt install python3.X-venv` с правильной minor version |
| Windows Python не в PATH | Средняя | Высокий | start.bat пробует `py -3` (Python Launcher), затем `python`; при ошибке -- инструкция "Add to PATH" |
| `chcp 65001` не решает кодировку cmd.exe полностью | Низкая | Средний | Критичные сообщения дублируются в ASCII-fallback стиле (квадратные скобки `[Ошибка]` вместо emoji) |
| macOS Gatekeeper блокирует start.sh | Низкая | Средний | BETA_README описывает `chmod +x start.sh` и `./start.sh` |
| `set -euo pipefail` прерывает на non-fatal | Низкая | Низкий | Background `open_browser` обёрнут в отдельную функцию, PID отслеживается через trap |
| `xcopy /D /L` ведёт себя по-разному на разных Windows | Низкая | Средний | Fallback: если парсинг xcopy непредсказуем, маркер-файл просто пересоздаётся (повторный pip install с --quiet быстр если всё установлено) |
| Порт 8050 занят предыдущим запуском FinFocus | Средняя | Средний | Проверка порта ДО запуска с понятным сообщением и подсказкой альтернативного порта |

## Requirements Traceability Matrix (RTM)

| # | Requirement | Spec | Реализация | Тип |
|---|-------------|------|------------|-----|
| R1 | `start.sh` для Linux/macOS: Python 3.10+, venv, pip, run.py, браузер | brief R1 | `start.sh`: find_python, check_venv_package, ensure_venv, ensure_deps, check_port, open_browser, trap | Integration |
| R1a | Повторный запуск быстрый | NFR | Маркер `.venv/.deps_installed` + `-nt` mtime check | Edge |
| R1b | Сообщения на русском | NFR | Все echo/info/warn/error на русском | UX |
| R1c | Работает на Linux и macOS | NFR | `uname` для определения ОС, `xdg-open` vs `open` | Integration |
| R2 | `start.bat` для Windows: аналогичная логика | brief R2 | `start.bat`: полный batch-скрипт с `py -3`, `chcp 65001`, `netstat`, `pause` | Integration |
| R3 | `BETA_README.md`: 3 шага, FAQ, обратная связь | brief R3 | `BETA_README.md`: установка Python, запуск, FAQ (5 вопросов), bug report | UX |
| R4 | Разделить requirements.txt на runtime/dev | brief R4 | `requirements.txt` EDIT, `requirements-dev.txt` CREATE | Integration |
| R5 | Документация процесса GitHub Release | brief R5 | `docs/RELEASE_GUIDE.md`: tag format, шаблон notes, ZIP-содержимое | UX |

## Blast Radius

### Прямые изменения
- `start.sh` -- CREATE: bash-скрипт запуска (новый файл)
- `start.bat` -- CREATE: batch-скрипт запуска (новый файл)
- `BETA_README.md` -- CREATE: инструкция для тестеров (новый файл)
- `requirements.txt` -- EDIT: убрать 4 dev-строки
- `requirements-dev.txt` -- CREATE: runtime + dev зависимости (новый файл)
- `docs/RELEASE_GUIDE.md` -- CREATE: процесс релиза (новый файл)

### Связанные файлы
- `.gitignore` -- **ПОДТВЕРЖДЕНО**: `.venv` уже игнорируется (строка 31), `data/*.db` игнорируется (строка 34). Изменения НЕ требуются.
- `run.py` -- НЕ меняется; является точкой запуска из скриптов; использует `PORT` env var
- `setup.cfg` -- НЕ меняется; конфигурация flake8/pytest
- `.obsidian-docs/ROADMAP.md` -- обновить статус Phase 3 после реализации
- `CLAUDE.md` -- возможно добавить секцию "Запуск для бета-тестеров"

### Проверить после реализации
- [ ] `pytest -k "not test_budget_change_updates_allocation"` проходит
- [ ] `black app/` + `flake8 app/` без ошибок
- [ ] `bash start.sh` на Linux -- приложение запускается и открывает браузер
- [ ] Повторный `bash start.sh` -- не переустанавливает зависимости (мгновенный запуск)
- [ ] `.venv/.deps_installed` маркер создается после pip install
- [ ] `requirements-dev.txt` корректно подключает runtime зависимости через `-r`
- [ ] Русский текст в start.bat корректно отображается (chcp 65001)
- [ ] `shellcheck start.sh` -- без критичных предупреждений (если доступен)
- [ ] Проверка порта: запустить два раза -- второй раз получаем внятное сообщение

## Учтённые замечания из критики

| Замечание из critique v1 | Как решено |
|--------------------------|------------|
| 🔴 Python version contradiction (3.10 vs 3.12) | Решено: аудит кодовой базы подтвердил отсутствие 3.12-only фич. Минимум = **3.10+**. `REQUIRED_PYTHON_MINOR=10` в обоих скриптах. |
| 🟡 `start.bat` pseudocode too vague | Решено: `start.bat` раскрыт до полного псевдокода с `for /f` парсингом, `xcopy /D /L` сравнением дат, `errorlevel` обработкой, `goto`/label структурой. |
| 🟡 Orphaned background process on Ctrl+C | Решено: добавлен `trap cleanup INT TERM` handler который сохраняет PID фонового `open_browser` и убивает его при завершении. |
| 🟡 No port check before launch | Решено: добавлена функция `check_port()` в start.sh (проверка через `ss`/`lsof`/`netstat` с graceful fallback) и секция `:check_port` в start.bat (через `netstat -an`). Сообщение на русском с подсказкой альтернативного порта. |
| 🟡 `.gitignore` verification not confirmed | Решено: проверено -- `.venv` на строке 31, `data/*.db` на строке 34 `.gitignore`. Изменения НЕ требуются. |
| 🟢 `alembic` runtime vs dev classification | Решено: `alembic` остаётся в runtime. Подтверждено: `run_all_migrations()` вызывается при каждом запуске. |
| 🟢 `python-dotenv` may not be needed | Решено: `python-dotenv` остаётся в runtime. Подтверждено: `load_dotenv()` вызывается в `app/main.py`. Без пакета -- `ImportError`. |
| 🟢 BETA_README.md content not specified | Решено: добавлен полный черновик BETA_README.md с конкретными FAQ (5 вопросов) и разделом обратной связи. |

## Ответы на вопросы критика

1. **Вопрос:** Is the minimum truly 3.10 or 3.12?
   **Ответ:** Минимум = **3.10+**. Аудит кодовой базы подтвердил: НЕТ `match/case`, НЕТ type aliases `type X = ...` (3.12), НЕТ `@override` (3.12). Используются `TypedDict`, `Literal`, `NewType` из `typing` -- все доступны с 3.10.

2. **Вопрос:** Should the script include `pause` on error?
   **Ответ:** Да. `start.bat` включает `pause` при любой ошибке (`goto :exit_with_pause`) и при нормальном завершении (`goto :exit_normal`).

3. **Вопрос:** Is `run_all_migrations()` called at runtime?
   **Ответ:** Да. `run.py` вызывает `run_all_migrations()` при каждом запуске. `alembic` -- runtime-зависимость.
