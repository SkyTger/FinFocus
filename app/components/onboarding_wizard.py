"""Onboarding Wizard — modal для первоначальной настройки."""
import logging
from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import callback, ctx, html, no_update, Input, Output, State
from dash.exceptions import PreventUpdate

from app.core.database import get_db_session
from app.services.onboarding_service import OnboardingService

logger = logging.getLogger(__name__)
DEFAULT_USER_ID = 1


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


# =============================================================================
# Callbacks
# =============================================================================


@callback(
    [
        Output("onboarding-modal", "is_open"),
        Output("onboarding-submit-btn", "disabled"),
        Output("onboarding-balance-warning", "style"),
    ],
    [
        Input("url", "pathname"),
        Input("onboarding-balance-input", "value"),
    ],
    prevent_initial_call=False,
)
def check_onboarding_and_validate(
    pathname: str | None,
    balance_value: float | None,
) -> tuple[bool, bool, dict]:
    """Проверяет first_launch и валидирует ввод.

    DB Failure Strategy: Fail-closed.
    При ошибке чтения first_launch wizard скрывается, позволяя
    пользователю работать. Повторная попытка при следующей загрузке.
    """
    triggered_id = ctx.triggered_id

    # При первой загрузке или navigation — проверяем first_launch
    if triggered_id == "url" or triggered_id is None:
        try:
            with get_db_session() as session:
                service = OnboardingService(session)
                status = service.get_status(DEFAULT_USER_ID)

            if status["first_launch"]:
                return True, True, {"display": "none"}
            else:
                return False, True, {"display": "none"}

        except Exception as e:
            # FAIL-CLOSED: скрыть wizard при ошибке
            logger.error(f"Ошибка проверки онбординга (fail-closed): {e}")
            return False, True, {"display": "none"}

    # При вводе значения — валидация
    if triggered_id == "onboarding-balance-input":
        if balance_value is None or balance_value == "":
            return no_update, True, {"display": "none"}

        try:
            value = float(balance_value)
            is_negative = value < 0
            return (
                no_update,
                False,  # Enable submit
                {"display": "block"} if is_negative else {"display": "none"},
            )
        except (ValueError, TypeError):
            return no_update, True, {"display": "none"}

    raise PreventUpdate


@callback(
    Output("onboarding-modal", "is_open", allow_duplicate=True),
    [
        Input("onboarding-submit-btn", "n_clicks"),
        Input("onboarding-skip-btn", "n_clicks"),
    ],
    State("onboarding-balance-input", "value"),
    prevent_initial_call=True,
)
def handle_onboarding_action(
    submit_clicks: int | None,
    skip_clicks: int | None,
    balance_value: float | None,
) -> bool:
    """Обрабатывает submit или skip действия."""
    # Guard: проверяем что был реальный клик
    if not ctx.triggered:
        raise PreventUpdate

    triggered_id = ctx.triggered_id

    # Guard: проверяем что значение не None (автовызов)
    trigger_value = ctx.triggered[0].get("value")
    if trigger_value is None:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            service = OnboardingService(session)

            if triggered_id == "onboarding-submit-btn":
                balance = (
                    Decimal(str(balance_value)) if balance_value else Decimal("0")
                )
                service.complete_with_balance(DEFAULT_USER_ID, balance)
            elif triggered_id == "onboarding-skip-btn":
                service.skip(DEFAULT_USER_ID)

            session.commit()

        return False  # Close modal

    except Exception as e:
        logger.error(f"Ошибка сохранения онбординга: {e}")
        return False  # Close modal anyway
