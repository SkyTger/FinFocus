"""Сервис управления онбордингом пользователя."""
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.database import User
from app.schema import OnboardingStatus


class OnboardingService:
    """Сервис управления онбордингом пользователя.

    Предоставляет методы для проверки и завершения процесса онбординга.

    Note:
        Методы модификации (complete_with_balance, skip) делают flush(),
        но НЕ commit. Caller отвечает за вызов session.commit() или
        rollback() для завершения транзакции.

    Example:
        with get_db_session() as session:
            service = OnboardingService(session)
            service.complete_with_balance(user_id=1, starting_balance=Decimal("10000"))
            session.commit()  # Caller делает commit!
    """

    def __init__(self, session: Session) -> None:
        """Инициализация сервиса.

        Args:
            session: SQLAlchemy сессия.
        """
        self.session = session

    def get_status(self, user_id: int) -> OnboardingStatus:
        """Получить статус онбординга пользователя.

        Args:
            user_id: ID пользователя.

        Returns:
            OnboardingStatus с полями first_launch, starting_balance,
            needs_balance_alert.

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
        )

    def complete_with_balance(self, user_id: int, starting_balance: Decimal) -> None:
        """Завершить онбординг с указанным балансом.

        Args:
            user_id: ID пользователя.
            starting_balance: Начальный баланс для установки.

        Raises:
            ValueError: Если пользователь не найден.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user.starting_balance = starting_balance
        user.first_launch = False
        self.session.flush()

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
