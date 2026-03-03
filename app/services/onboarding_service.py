"""Сервис управления онбордингом и профилем пользователя."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID
from app.models.database import User
from app.schema.onboarding import OnboardingStatus, UserProfile


class OnboardingService:
    """Сервис управления онбордингом и профилем пользователя.

    Предоставляет методы для проверки и завершения процесса онбординга,
    а также управления профилем (имя, аватарка).

    Note:
        Методы модификации делают flush(), но НЕ commit.
        Caller отвечает за вызов session.commit() или rollback().

    Example:
        with get_db_session() as session:
            service = OnboardingService(session)
            service.complete(user_id=1, name="Иван", avatar_id="emoji-rocket",
                           starting_balance=Decimal("10000"))
            session.commit()
    """

    def __init__(self, session: Session) -> None:
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy сессия.
        """
        self.session = session

    def _validate_profile_fields(self, name: str, avatar_id: str) -> tuple[str, str]:
        """Валидация полей профиля.

        Args:
            name: Имя пользователя (будет stripped).
            avatar_id: Идентификатор аватарки.

        Returns:
            Кортеж (validated_name, validated_avatar_id).

        Raises:
            ValueError: Если имя пустое или длиннее 50 символов.

        Note:
            Лимит 50 символов — UI-ограничение. Колонка String(100)
            допускает больше для обратной совместимости.
        """
        clean_name = name.strip() if name else ""
        if not clean_name or len(clean_name) > 50:
            raise ValueError("Имя должно быть от 1 до 50 символов")
        valid_avatar = avatar_id if avatar_id in AVATARS else DEFAULT_AVATAR_ID
        return clean_name, valid_avatar

    def get_status(self, user_id: int) -> OnboardingStatus:
        """Получить статус онбординга пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            OnboardingStatus с полями first_launch, starting_balance,
            needs_balance_alert, name, avatar_id.

        Raises:
            ValueError: Если пользователь не найден.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        return OnboardingStatus(
            first_launch=user.first_launch,
            starting_balance=user.starting_balance,
            needs_balance_alert=user.starting_balance == Decimal("0"),
            name=user.name,
            avatar_id=user.avatar_id,
        )

    def complete(
        self,
        user_id: int,
        name: str,
        avatar_id: str,
        starting_balance: Decimal,
    ) -> None:
        """Завершить онбординг с профилем и балансом.

        Args:
            user_id: ID пользователя.
            name: Имя пользователя.
            avatar_id: Идентификатор аватарки.
            starting_balance: Начальный баланс.

        Raises:
            ValueError: Если пользователь не найден или имя невалидно.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        clean_name, valid_avatar = self._validate_profile_fields(name, avatar_id)
        user.name = clean_name
        user.avatar_id = valid_avatar
        user.starting_balance = starting_balance
        user.first_launch = False
        self.session.flush()

    def complete_with_balance(self, user_id: int, starting_balance: Decimal) -> None:
        """Завершить онбординг с балансом (deprecated).

        Обёртка для обратной совместимости. Используйте complete().

        Args:
            user_id: ID пользователя.
            starting_balance: Начальный баланс.
        """
        self.complete(
            user_id=user_id,
            name="Пользователь",
            avatar_id=DEFAULT_AVATAR_ID,
            starting_balance=starting_balance,
        )

    def update_profile(self, user_id: int, name: str, avatar_id: str) -> None:
        """Обновить профиль пользователя (имя и аватарку).

        Args:
            user_id: ID пользователя.
            name: Новое имя.
            avatar_id: Новый идентификатор аватарки.

        Raises:
            ValueError: Если пользователь не найден или имя невалидно.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        clean_name, valid_avatar = self._validate_profile_fields(name, avatar_id)
        user.name = clean_name
        user.avatar_id = valid_avatar
        self.session.flush()

    def get_profile(self, user_id: int) -> UserProfile:
        """Получить профиль пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            UserProfile с name и avatar_id.

        Raises:
            ValueError: Если пользователь не найден.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        return UserProfile(name=user.name, avatar_id=user.avatar_id)

    def skip(self, user_id: int) -> None:
        """Пропустить онбординг (баланс остается 0).

        Args:
            user_id: ID пользователя.

        Raises:
            ValueError: Если пользователь не найден.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user.first_launch = False
        self.session.flush()
