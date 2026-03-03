@echo off
chcp 65001 >nul 2>&1
setlocal EnableDelayedExpansion

REM === Переходим в директорию скрипта ===
cd /d "%~dp0"

set "VENV_DIR=.venv"
set "DEPS_MARKER=%VENV_DIR%\.deps_installed"
set "REQUIRED_MAJOR=3"
set "REQUIRED_MINOR=10"
if not defined PORT set "PORT=8050"
set "APP_URL=http://localhost:%PORT%"
set "PYTHON_CMD="

echo.
echo ==============================
echo   FinFocus — запуск
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
