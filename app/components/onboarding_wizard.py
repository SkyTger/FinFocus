"""Onboarding Wizard — modal для первоначальной настройки."""
import time

from decimal import Decimal

import dash_bootstrap_components as dbc
from dash import callback, ctx, html, no_update, Input, Output, State
from dash.exceptions import PreventUpdate
from loguru import logger

from app.config.avatars import AVATARS, DEFAULT_AVATAR_ID
from app.core.database import get_db_session
from app.services.onboarding_service import OnboardingService

DEFAULT_USER_ID = 1


def _build_avatar_options() -> list[dict]:
    """Формирует опции для RadioItems аватарок."""
    return [
        {"label": html.Span(v["emoji"], title=v["label"]), "value": k}
        for k, v in AVATARS.items()
    ]


def create_onboarding_wizard() -> dbc.Modal:
    """Создает blocking modal для онбординга.

    Единый экран: имя + аватарка (RadioItems) + баланс.

    Returns:
        dbc.Modal: Модальное окно с формой.
    """
    return dbc.Modal(
        id="onboarding-modal",
        is_open=False,
        backdrop="static",
        keyboard=False,
        centered=True,
        className="onboarding-modal",
        children=[
            dbc.ModalHeader(
                dbc.ModalTitle("Добро пожаловать в FinFocus!"),
                close_button=False,
            ),
            dbc.ModalBody(
                [
                    # Имя
                    dbc.Label("Как вас зовут?", className="fw-semibold mb-1"),
                    dbc.Input(
                        id="onboarding-name-input",
                        type="text",
                        placeholder="Как вас зовут?",
                        maxLength=50,
                        className="mb-3",
                    ),
                    # Аватарка
                    dbc.Label(
                        "Выберите аватарку", className="fw-semibold mb-1"
                    ),
                    dbc.RadioItems(
                        id="onboarding-avatar-selector",
                        options=_build_avatar_options(),
                        value=DEFAULT_AVATAR_ID,
                        inline=True,
                        className="avatar-grid mb-3",
                        inputClassName="avatar-radio-hidden",
                        labelClassName="avatar-option",
                        labelCheckedClassName="avatar-option-selected",
                    ),
                    # Баланс
                    dbc.Label(
                        "Текущий остаток на счетах",
                        className="fw-semibold mb-1",
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
                        "Вы сможете изменить баланс позже через Сверку.",
                        className="text-muted",
                    ),
                ]
            ),
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
                        disabled=True,
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
        Input("onboarding-name-input", "value"),
        Input("onboarding-balance-input", "value"),
    ],
    prevent_initial_call=False,
)
def check_onboarding_and_validate(
    pathname: str | None,
    name_value: str | None,
    balance_value: float | None,
) -> tuple[bool, bool, dict]:
    """Проверяет first_launch и валидирует ввод.

    Оптимизация по ctx.triggered_id: DB-запрос только при навигации.
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
            logger.error(f"Ошибка проверки онбординга (fail-closed): {e}")
            return False, True, {"display": "none"}

    # При вводе имени — валидация (NO DB call)
    if triggered_id == "onboarding-name-input":
        has_name = bool(name_value and name_value.strip())
        return no_update, not has_name, no_update

    # При вводе баланса — warning для отрицательного (NO DB call)
    if triggered_id == "onboarding-balance-input":
        if balance_value is None or balance_value == "":
            return no_update, no_update, {"display": "none"}

        try:
            value = float(balance_value)
            is_negative = value < 0
            return (
                no_update,
                no_update,
                {"display": "block"} if is_negative else {"display": "none"},
            )
        except (ValueError, TypeError):
            return no_update, no_update, {"display": "none"}

    raise PreventUpdate


@callback(
    [
        Output("onboarding-modal", "is_open", allow_duplicate=True),
        Output("profile-updated", "data"),
    ],
    [
        Input("onboarding-submit-btn", "n_clicks"),
        Input("onboarding-skip-btn", "n_clicks"),
    ],
    [
        State("onboarding-name-input", "value"),
        State("onboarding-avatar-selector", "value"),
        State("onboarding-balance-input", "value"),
    ],
    prevent_initial_call=True,
)
def handle_onboarding_action(
    submit_clicks: int | None,
    skip_clicks: int | None,
    name_value: str | None,
    avatar_value: str | None,
    balance_value: float | None,
) -> tuple[bool, float | None]:
    """Обрабатывает submit или skip действия."""
    if not ctx.triggered:
        raise PreventUpdate

    triggered_id = ctx.triggered_id
    trigger_value = ctx.triggered[0].get("value")
    if trigger_value is None:
        raise PreventUpdate

    try:
        with get_db_session() as session:
            service = OnboardingService(session)

            if triggered_id == "onboarding-submit-btn":
                name = name_value.strip() if name_value else "Пользователь"
                avatar = avatar_value or DEFAULT_AVATAR_ID
                balance = (
                    Decimal(str(balance_value)) if balance_value else Decimal("0")
                )
                service.complete(DEFAULT_USER_ID, name, avatar, balance)
            elif triggered_id == "onboarding-skip-btn":
                service.skip(DEFAULT_USER_ID)

            session.commit()

        return False, time.time()

    except Exception as e:
        logger.error(f"Ошибка сохранения онбординга: {e}")
        return False, None
