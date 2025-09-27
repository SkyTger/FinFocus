"""
Запуск приложения FinFocus.
"""
import os
from app.main import app

if __name__ == "__main__":
    # Создаем папку data если её нет
    os.makedirs("data", exist_ok=True)

    # Запускаем приложение
    debug = os.getenv('DEBUG', 'True').lower() == 'true'
    port = int(os.getenv('PORT', 8050))

    print(f"🚀 Запускаем FinFocus на http://localhost:{port}")
    print("📊 Планировщик бюджета готов к работе!")

    app.run_server(
        debug=debug,
        port=port,
        host='0.0.0.0'
    )
