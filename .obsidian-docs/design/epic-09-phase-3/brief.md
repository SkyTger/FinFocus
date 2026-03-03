# Brief: Delivery & Setup for Beta Testers (Epic-09 Phase 3)

## Цель
Дать нетехническим пользователям возможность установить и запустить FinFocus одним действием: скачал zip -> запустил скрипт -> приложение работает в браузере.

## Функциональные требования
- R1: `start.sh` для Linux/macOS -- bash-скрипт с полным циклом: проверка Python 3.10+ -> создание venv -> pip install -> запуск run.py -> открытие браузера
- R2: `start.bat` для Windows -- batch-скрипт с аналогичной логикой через cmd.exe
- R3: `BETA_README.md` -- пошаговая инструкция на русском для нетехнических пользователей (max 3 шага, FAQ, раздел "как сообщить о проблеме")
- R4: Разделить `requirements.txt` на runtime (`requirements.txt`) и dev (`requirements-dev.txt`)
- R5: Документировать процесс создания GitHub Release (tag format `v0.9.0-beta.1`, release notes шаблон)

## Нефункциональные требования
- Сообщения скриптов -- на русском языке
- Повторный запуск быстрый (не пересоздает venv, не переустанавливает зависимости)
- Скрипты идемпотентны и безопасны при повторном вызове
- `start.sh` работает и на Linux, и на macOS (разные команды открытия браузера)

## Ограничения
- Python должен быть уже установлен на машине пользователя (скрипт только проверяет)
- Docker и PyInstaller -- вне scope (отложены в Backlog)
- Нативное окно (flaskwebgui) -- вне scope
- Код приложения (`app/`) НЕ меняется

## Критерии приемки
- [ ] `start.sh` запускает приложение на Linux/macOS при наличии Python 3.10+
- [ ] `start.bat` запускает приложение на Windows при наличии Python 3.10+
- [ ] При отсутствии Python -- понятное сообщение с инструкцией по установке
- [ ] Повторный запуск быстрый (не пересоздает venv)
- [ ] `BETA_README.md` понятен нетехническому пользователю
- [ ] `requirements.txt` содержит только runtime-зависимости
- [ ] `requirements-dev.txt` включает runtime + dev tools
- [ ] Существующие тесты проходят (`pytest -k "not test_budget_change_updates_allocation"`)
- [ ] `black app/` + `flake8 app/` без ошибок

## Вне scope (out of scope)
- Docker-контейнеры
- PyInstaller / нативные бинарники
- Нативное окно (flaskwebgui/pywebview)
- Автоматическая установка Python
- CI/CD pipeline для автосборки
