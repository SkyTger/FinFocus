"""Onboarding Wizard — modal для первоначальной настройки."""
import dash_bootstrap_components as dbc
from dash import html


def create_onboarding_wizard() -> dbc.Modal:
    """Создает blocking modal для онбординга.

    Returns:
        dbc.Modal: Модальное окно с формой ввода starting_balance.
    """
    return dbc.Modal(
        id="onboarding-modal",
        is_open=False,
        backdrop="static",  # Клик вне modal не закрывает
        keyboard=False,  # Escape не закрывает
        centered=True,
        className="onboarding-modal",
        children=[
            dbc.ModalHeader(
                dbc.ModalTitle("Добро пожаловать в FinFocus!"),
                close_button=False,  # Без крестика
            ),
            dbc.ModalBody([
                html.P(
                    "Для точных расчётов кассового календаря укажите "
                    "текущий остаток на всех ваших счетах:",
                    className="mb-3",
                ),
                dbc.InputGroup(
                    [
                        dbc.Input(
                            id="onboarding-balance-input",
                            type="number",
                            placeholder="0.00",
                            step="0.01",
                            className="onboarding-balance-input",
                        ),
                        dbc.InputGroupText("₽"),
                    ],
                    className="mb-2",
                ),
                html.Div(
                    id="onboarding-balance-warning",
                    className="onboarding-warning text-warning",
                    style={"display": "none"},
                    children="Отрицательный баланс — вы уверены?",
                ),
                html.Small(
                    "Вы сможете изменить это значение позже через Сверку баланса.",
                    className="text-muted",
                ),
            ]),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Пропустить",
                        id="onboarding-skip-btn",
                        color="secondary",
                        outline=True,
                        className="me-2",
                    ),
                    dbc.Button(
                        "Продолжить",
                        id="onboarding-submit-btn",
                        color="success",
                        disabled=True,  # Disabled по умолчанию
                    ),
                ],
                className="justify-content-end",
            ),
        ],
    )
