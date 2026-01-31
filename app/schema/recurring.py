"""TypedDicts для recurring операций."""
from typing import TypedDict


class RecurringDeleteContext(TypedDict):
    """Контекст для модала удаления recurring операции.

    Виртуальные экземпляры не имеют ID в БД, поэтому используем
    template_id + instance_date как идентификатор.

    Attributes:
        template_id: ID шаблона recurring операции.
        instance_date: ISO date (YYYY-MM-DD) экземпляра.
    """

    template_id: int
    instance_date: str


# Константы scope options для RadioItems
DELETE_SCOPE_OPTIONS = [
    {"label": "Только этот экземпляр", "value": "instance"},
    {"label": "Эту и все будущие", "value": "future"},
    {"label": "Всю серию", "value": "all"},
]
