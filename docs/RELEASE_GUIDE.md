# Процесс создания GitHub Release

## Tag формат

```
v0.9.0-beta.N
```

Где `N` — номер бета-релиза, начиная с 1 (например, `v0.9.0-beta.1`, `v0.9.0-beta.2`).

## Шаги

1. Убедиться что ветка `main` зелёная (все тесты проходят)
2. Создать tag:
   ```bash
   git tag -a v0.9.0-beta.1 -m "Beta 1 release"
   ```
3. Push tag:
   ```bash
   git push origin v0.9.0-beta.1
   ```
4. На GitHub: **Releases** → **Draft a new release** → выбрать tag
5. Заполнить Release Notes по шаблону ниже
6. Прикрепить ZIP-архив

## Создание ZIP-архива

```bash
git archive --format=zip --prefix=FinFocus/ HEAD \
  -o FinFocus-v0.9.0-beta.1.zip \
  start.sh start.bat BETA_README.md requirements.txt \
  run.py app/ scripts/
```

### Что включать в ZIP

- `start.sh`, `start.bat` — скрипты запуска
- `BETA_README.md` — инструкция для тестеров
- `requirements.txt` — runtime-зависимости
- `run.py` — точка входа
- `app/` — код приложения
- `scripts/` — миграции и seed-скрипты БД

### Что НЕ включать

- `.venv/` — виртуальное окружение (создаётся скриптом)
- `data/*.db` — база данных (создаётся при первом запуске)
- `__pycache__/` — кэш Python
- `.git/` — история git
- `tests/` — тесты
- `requirements-dev.txt` — dev-зависимости
- `.obsidian-docs/` — внутренняя документация

## Шаблон Release Notes

```markdown
## FinFocus v0.9.0-beta.N

### Что нового
- [Описание изменений]

### Установка
1. Скачайте ZIP-архив из раздела Assets ниже
2. Распакуйте в любую папку
3. Следуйте инструкции в BETA_README.md

### Требования
- Python 3.10 или новее
- Интернет (для первого запуска)

### Известные ограничения
- [Список известных проблем]
```

## Checklist перед релизом

- [ ] Все тесты проходят на `main`
- [ ] `black app/` и `flake8 app/` без ошибок
- [ ] `start.sh` протестирован на Linux
- [ ] ZIP-архив содержит только нужные файлы
- [ ] Release Notes заполнены
- [ ] Tag создан и запушен
