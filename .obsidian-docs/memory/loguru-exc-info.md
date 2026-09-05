---
name: loguru-exc-info
description: loguru молча игнорирует exc_info=True — трейсбек только через logger.opt(exception=True) или logger.exception()
metadata: 
  node_type: memory
  type: project
  originSessionId: 42e6a568-e20f-4dc4-8b18-1e55f3129802
  modified: 2026-08-21T16:42:32.805Z
---

loguru (логгер FinFocus) молча игнорирует kwarg `exc_info=True` из stdlib-идиомы:
сообщение пишется, трейсбек — НЕТ, ошибки тоже нет. Проверено поведенчески
2026-08-21 (протокол 0027).

**Why:** аудит 2026-08-20 (п.5 🟡) отметил разнобой логирования в except-блоках;
существующие `logger.warning(..., exc_info=True)` в кодовой базе (dashboard.py:90
и др.) — «пустые», трейсбек не пишут. Субагент в 0027 воспроизвёл ту же ошибку
по формулировке аудита — исправлено на opt(exception=True).

**How to apply:** в except-блоках использовать `logger.opt(exception=True).warning(...)`
или `logger.exception(...)`. При выполнении п.10 плана аудита (унификация
логирования) — заменить все exc_info=True по кодовой базе. Тест на наличие
трейсбека: sink через `logger.add(...)`, проверять `record["exception"]`
(образец: tests/test_purchase_recommendation.py::test_safe_dates_cushion_failure_is_fail_open).
