"""Скрипт живой приёмки протокола 0033 «можно тратить» — ТОЛЬКО чтение.

Печатает на дату отсчёта то, что щиток покажет владельцу: «Свободно
сегодня», периоды лимита трат на день, узкое место, норму «по плану»,
нехватку и прогноз остатка на конец каждого периода. Нужен основной
сессии для сверки с журналом бюджета на КОПИИ боевой базы.

База открывается в режиме SQLite read-only (``mode=ro``): любая попытка
записи упадёт ошибкой, а не испортит файл. Боевую базу всё равно
передавать копией — правило проекта.

Пример:
    cp data/finfocus.db /tmp/finfocus-copy.db
    .venv/bin/python scripts/acceptance_safe_to_spend.py /tmp/finfocus-copy.db \\
        --ref 2026-11-03
"""

import argparse
import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.calendar_service import CalendarService  # noqa: E402
from app.services.money_layers_service import (  # noqa: E402
    MoneyLayersService,
    bottleneck_marker,
    floor_rub,
)


def _rub(amount: Decimal | None) -> str:
    """Сумма в рублях с разделителем тысяч (без копеек) или «—».

    Args:
        amount: Сумма или None.

    Returns:
        str: Текст суммы.
    """
    if amount is None:
        return "—"
    return f"{floor_rub(amount):,.0f} ₽".replace(",", " ")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Аргументы командной строки.

    Args:
        argv: Аргументы (None — sys.argv).

    Returns:
        argparse.Namespace: db, ref, user_id.
    """
    parser = argparse.ArgumentParser(
        description="Приёмка «можно тратить» по копии базы (только чтение)"
    )
    parser.add_argument("db", type=Path, help="путь к КОПИИ файла базы SQLite")
    parser.add_argument(
        "--ref",
        type=date.fromisoformat,
        default=date.today(),
        help="дата отсчёта YYYY-MM-DD (по умолчанию сегодня)",
    )
    parser.add_argument("--user-id", type=int, default=1, help="ID пользователя")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Печатает срез модели «можно тратить» на дату отсчёта.

    Args:
        argv: Аргументы командной строки (None — sys.argv).

    Returns:
        int: Код выхода (0 — успех, 2 — файла базы нет).
    """
    args = _parse_args(argv)
    db_path = args.db.resolve()
    if not db_path.is_file():
        print(f"Файл базы не найден: {db_path}", file=sys.stderr)
        return 2

    # mode=ro — SQLite откроет файл только на чтение
    engine = create_engine(f"sqlite:///file:{db_path.as_posix()}?mode=ro&uri=true")
    with Session(engine) as session:
        data = MoneyLayersService(session).get_money_layers(args.user_id, args.ref)
        balances = CalendarService(session).calculate_daily_balances(
            args.user_id, args.ref, data["horizon_end"]
        )

    today = data["today"]
    print(
        f"Дата отсчёта: {data['reference_date']}  (горизонт H: {data['horizon_end']})"
    )
    print(
        f"Свободно сегодня: {_rub(today['free'])}  "
        f"(баланс {_rub(today['balance'])} − платежи {_rub(today['payments'])}"
        f" − резерв {_rub(today['reserve'])})"
    )
    print("Периоды лимита:")
    for period in data["limit_periods"]:
        mark = "" if period["reliable"] else "  [ненадёжен: край без дохода]"
        print(
            f"  {period['start']} … {period['end']}: "
            f"~{_rub(period['per_day'])}/день "
            f"(точно {period['per_day']:.2f}); "
            f"прогноз остатка на {period['end']}: "
            f"{_rub(balances.get(period['end']))}{mark}"
        )
    marker = bottleneck_marker(data)
    print(
        f"Узкое место: {data['bottleneck_date']}, доступно "
        f"{_rub(data['bottleneck_available'])}; точка на щитке: {marker.date}"
    )
    print(f"Норма «по плану»: {_rub(data['norm_per_day'])}/день")
    if data["shortfall"] > 0:
        print(f"НЕ ХВАТАЕТ: {_rub(data['shortfall'])} до {data['shortfall_date']}")
    else:
        print("Нехватки нет")
    if data["degraded"]:
        print("ВНИМАНИЕ: часть модели посчитана в деградации (degraded)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
