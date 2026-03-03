"""Конфигурация аватарок пользователя."""

AVATARS: dict[str, dict[str, str]] = {
    "emoji-default": {"emoji": "\U0001f60a", "label": "Улыбка"},
    "emoji-rocket": {"emoji": "\U0001f680", "label": "Ракета"},
    "emoji-fox": {"emoji": "\U0001f98a", "label": "Лиса"},
    "emoji-cat": {"emoji": "\U0001f431", "label": "Кот"},
    "emoji-coffee": {"emoji": "\u2615", "label": "Кофе"},
    "emoji-star": {"emoji": "\u2b50", "label": "Звезда"},
    "emoji-fire": {"emoji": "\U0001f525", "label": "Огонь"},
    "emoji-crystal": {"emoji": "\U0001f48e", "label": "Кристалл"},
    "emoji-leaf": {"emoji": "\U0001f343", "label": "Листок"},
    "emoji-target": {"emoji": "\U0001f3af", "label": "Цель"},
}

DEFAULT_AVATAR_ID: str = "emoji-default"


def get_avatar_emoji(avatar_id: str) -> str:
    """Получить emoji по идентификатору аватарки.

    Args:
        avatar_id: Идентификатор аватарки.

    Returns:
        Emoji строка. При невалидном avatar_id возвращает default.
    """
    avatar = AVATARS.get(avatar_id)
    if avatar is None:
        return AVATARS[DEFAULT_AVATAR_ID]["emoji"]
    return avatar["emoji"]
