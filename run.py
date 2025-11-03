"""
Запуск приложения FinFocus.
"""
import os
from app.main import app
from app.models.database import init_database, get_session

if __name__ == "__main__":
    # Создаем папку data если её нет
    os.makedirs("data", exist_ok=True)

    # Инициализируем базу данных
    print("📦 Инициализация базы данных...")
    engine = init_database()
    print("✅ База данных готова")

    # Проверка: есть ли данные в БД?
    session = get_session(engine)
    from app.models.database import User
    user_count = session.query(User).count()
    session.close()

    if user_count == 0:
        print("⚠️  База данных пустая!")
        print("💡 Запустите: python scripts/seed_database.py")
    else:
        print(f"👤 Найдено пользователей: {user_count}")

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
