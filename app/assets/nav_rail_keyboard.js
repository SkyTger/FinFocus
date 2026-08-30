/**
 * Клавиатурная активация аватара полоски-меню (протокол 0031).
 *
 * Аватар — html.Div с role="button" и tabindex=0, а не <button>:
 * Dash считает клики через n_clicks на любом компоненте, но нативной
 * клавиатурной активации у div нет. От элемента с role="button"
 * пользователь вправе ждать, что Enter и Space его нажмут — иначе
 * в окно профиля нельзя попасть с клавиатуры.
 *
 * Слушатель делегированный: сам аватар живёт в слоте, который
 * перерисовывается при переходах между разделами, и вешать
 * обработчик на конкретный узел нельзя — он переживёт не каждый
 * рендер.
 */
document.addEventListener("keydown", function (event) {
    if (event.key !== "Enter" && event.key !== " " && event.key !== "Spacebar") {
        return;
    }

    const avatar = event.target.closest
        ? event.target.closest("#nav-rail-avatar")
        : null;
    if (!avatar) {
        return;
    }

    // Space по умолчанию прокручивает страницу — для кнопки это не нужно.
    event.preventDefault();
    avatar.click();
});
