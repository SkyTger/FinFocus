"""Profile Modal — модал редактирования профиля (имя + аватарка)."""
import time

import dash_bootstrap_components as dbc
from dash import callback, ctx, html, Input, Output, State
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


def create_profile_modal() -> dbc.Modal:
    """Создает глобальный modal редактирования профиля.

    Returns:
        dbc.Modal: Модальное окно с полями имени и аватарки.
    """
    return dbc.Modal(
        id="profile-modal",
        is_open=False,
        centered=True,
        className="profile-modal",
        children=[
            dbc.ModalHeader(
                dbc.ModalTitle("Редактировать профиль"),
            ),
            dbc.ModalBody(
                [
                    dbc.Label("Имя", className="fw-semibold mb-1"),
                    dbc.Input(
                        id="profile-name-input",
                        type="text",
                        placeholder="Ваше имя",
                        maxLength=50,
                        className="mb-3",
                    ),
                    dbc.Label("Аватарка", className="fw-semibold mb-1"),
                    dbc.RadioItems(
                        id="profile-avatar-selector",
                        options=_build_avatar_options(),
                        value=DEFAULT_AVATAR_ID,
                        inline=True,
                        className="avatar-grid mb-3",
                        inputClassName="avatar-radio-hidden",
                        labelClassName="avatar-option",
                        labelCheckedClassName="avatar-option-selected",
                    ),
                ]
            ),
            dbc.ModalFooter(
                [
                    dbc.Button(
                        "Отмена",
                        id="profile-cancel-btn",
                        color="secondary",
                        outline=True,
                        className="me-2",
                    ),
                    dbc.Button(
                        "Сохранить",
                        id="profile-save-btn",
                        color="success",
                    ),
                ],
                className="justify-content-end",
            ),
        ],
    )


# =============================================================================
# Callback
# =============================================================================


@callback(
    [
        Output("profile-modal", "is_open"),
        Output("profile-name-input", "value"),
        Output("profile-avatar-selector", "value"),
        Output("profile-updated", "data", allow_duplicate=True),
    ],
    [
        Input("sidebar-profile-container", "n_clicks"),
        Input("profile-save-btn", "n_clicks"),
        Input("profile-cancel-btn", "n_clicks"),
    ],
    [
        State("profile-name-input", "value"),
        State("profile-avatar-selector", "value"),
    ],
    prevent_initial_call=True,
)
def handle_profile_modal(
    open_clicks: int | None,
    save_clicks: int | None,
    cancel_clicks: int | None,
    name_value: str | None,
    avatar_value: str | None,
) -> tuple[bool, str | None, str | None, float | None]:
    """Управляет открытием/закрытием и сохранением профиля."""
    triggered_id = ctx.triggered_id
    if not triggered_id:
        raise PreventUpdate

    # Open — загрузить данные из БД
    if triggered_id == "sidebar-profile-container":
        try:
            with get_db_session() as session:
                service = OnboardingService(session)
                profile = service.get_profile(DEFAULT_USER_ID)
            return True, profile["name"], profile["avatar_id"], None
        except Exception:
            logger.error("Failed to load profile for modal", exc_info=True)
            return True, "Пользователь", DEFAULT_AVATAR_ID, None

    # Save — обновить профиль
    if triggered_id == "profile-save-btn":
        try:
            with get_db_session() as session:
                service = OnboardingService(session)
                service.update_profile(
                    DEFAULT_USER_ID,
                    name_value or "Пользователь",
                    avatar_value or DEFAULT_AVATAR_ID,
                )
                session.commit()
            return False, None, None, time.time()
        except ValueError:
            logger.warning("Invalid profile data", exc_info=True)
            return True, name_value, avatar_value, None
        except Exception:
            logger.error("Failed to save profile", exc_info=True)
            return False, None, None, None

    # Cancel
    if triggered_id == "profile-cancel-btn":
        return False, None, None, None

    raise PreventUpdate
