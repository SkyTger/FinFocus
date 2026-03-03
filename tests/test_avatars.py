"""Unit тесты для конфигурации аватарок."""
from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID, get_avatar_emoji


class TestAvatarsConfig:
    """Тесты конфигурации аватарок."""

    def test_avatars_has_10_entries(self):
        """Словарь AVATARS содержит 10 записей."""
        assert len(AVATARS) == 10

    def test_default_avatar_id_exists(self):
        """DEFAULT_AVATAR_ID присутствует в AVATARS."""
        assert DEFAULT_AVATAR_ID in AVATARS

    def test_get_avatar_emoji_valid(self):
        """get_avatar_emoji возвращает emoji для валидного id."""
        emoji = get_avatar_emoji("emoji-rocket")
        assert emoji == "\U0001f680"

    def test_get_avatar_emoji_invalid_fallback(self):
        """get_avatar_emoji возвращает default emoji для невалидного id."""
        emoji = get_avatar_emoji("nonexistent-id")
        default_emoji = AVATARS[DEFAULT_AVATAR_ID]["emoji"]
        assert emoji == default_emoji

    def test_avatars_structure(self):
        """Каждая аватарка имеет emoji и label."""
        for avatar_id, data in AVATARS.items():
            assert "emoji" in data, f"{avatar_id} missing emoji"
            assert "label" in data, f"{avatar_id} missing label"
            assert isinstance(data["emoji"], str)
            assert isinstance(data["label"], str)
