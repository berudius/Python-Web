import os 

"""
Знаходить шлях до папки static та монтує її до FastAPI app.
"""

# 1. Отримуємо шлях до папки 'config' (де знаходиться ЦЕЙ файл)
#    .../hotel_service/app/config
config_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Піднімаємося на один рівень, щоб отримати шлях до папки 'app'
#    .../hotel_service/app
app_dir = os.path.dirname(config_dir)
app_dir = os.path.dirname(app_dir)

# 3. Тепер будуємо шлях до 'frontend/static' відносно 'app_dir'
#    .../hotel_service/app/frontend/static
static_dir_path = os.path.join(app_dir, "frontend", "static")
