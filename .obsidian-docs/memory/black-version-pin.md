---
name: black-version-pin
description: black запускать только из .venv (23.11.0) — системный black 26.x переформатирует 26 файлов иначе
metadata: 
  node_type: memory
  type: project
  originSessionId: 42e6a568-e20f-4dc4-8b18-1e55f3129802
  modified: 2026-08-21T16:30:49.325Z
---

В FinFocus эталон форматирования — black 23.11.0 из `.venv/bin/black`.
Системный black (~/.local/bin, переустановлен 2026-08-21 → 26.5.1)
форматирует иначе: `--check app/` показывает 26 файлов к переформатированию.

**Why:** 2026-08-21 чинили сломанные шебанги anaconda в ~/.local/bin и
поставили свежий black; массовое переформатирование раздуло бы диффы и
загрязнило blame.

**How to apply:** в этом проекте вызывать `/home/skytiger/Projects/FinFocus/.venv/bin/black`
(и для worktree тоже — venv живёт в PROJECT_ROOT). Не запускать голый
`black app/` из PATH. Бамп версии black — отдельным протоколом с одним
общим коммитом переформатирования.
