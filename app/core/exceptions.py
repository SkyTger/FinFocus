"""Единые исключения приложения."""


class ValidationError(Exception):
    """Ошибка валидации бизнес-правил.

    Используется для сообщения об ошибках валидации пользователю.

    Attributes:
        message: Текст ошибки на русском языке
        field: Имя поля с ошибкой (опционально)
    """

    def __init__(self, message: str, field: str | None = None):
        """Инициализирует ошибку валидации.

        Args:
            message: Текст ошибки
            field: Имя поля с ошибкой (для подсветки в UI)
        """
        self.message = message
        self.field = field
        super().__init__(message)

    def __str__(self) -> str:
        if self.field:
            return f"[{self.field}] {self.message}"
        return self.message
