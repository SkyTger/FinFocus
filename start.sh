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
    NC='\033[0m'
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
