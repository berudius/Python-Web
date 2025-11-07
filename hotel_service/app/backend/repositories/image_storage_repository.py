import os
import shutil
import uuid # Для генерації унікальних імен
from fastapi import UploadFile
from typing import List

# 1. Визначаємо, куди ми будемо зберігати файли.
# Це папка 'static/images' у вашому 'hotel_service'
# Path('.../hotel_service/app/backend/repositories') -> '.../hotel_service/app/frontend/static'
STATIC_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "static")
)
IMAGES_DIR = os.path.join(STATIC_DIR, "images")

# Переконаємося, що папка існує
os.makedirs(IMAGES_DIR, exist_ok=True)


def save_image(image_file: UploadFile) -> str:

    allowed_types = ["image/jpeg", "image/png", "image/webp"]
    if image_file.content_type not in allowed_types:
        raise ValueError("Неприпустимий тип файлу. Дозволено: JPEG, PNG, WebP")

    file_extension = os.path.splitext(image_file.filename)[1] 
    
    unique_name = f"{uuid.uuid4()}{file_extension}"
    
    file_path = os.path.join(IMAGES_DIR, unique_name)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image_file.file, buffer)
    finally:
        image_file.file.close()

    web_url = f"/static/images/{unique_name}"
    
    return web_url

def save_images(image_files: List[UploadFile]) -> List[str]:
    """
    Зберігає список файлів.
    Якщо хоча б один файл невалідний, видаляє всі вже збережені
    файли з цієї "партії" та піднімає виняток.
    """
    saved_urls = [] # Тут ми збираємо URL успішно збережених файлів
    try:
        for file in image_files:
            # Викликаємо нашу існуючу функцію для збереження одного файлу
            web_url = save_image(file)
            saved_urls.append(web_url)
            
    except ValueError as e:
        # Помилка! (напр., поганий тип файлу). 
        # Потрібно "відкотити" зміни - видалити все, що ми вже зберегли.
        print(f"Помилка завантаження: {e}. Виконую очищення...")
        for url in saved_urls:
            try:
                remove_image(url)
            except OSError as remove_e:
                # Логуємо, якщо не змогли видалити, але продовжуємо
                print(f"Помилка при очищенні файлу {url}: {remove_e}")
                
        # Після очищення, "прокидаємо" помилку далі, щоб роутер її спіймав
        raise e 
    
    # Якщо все пройшло добре, повертаємо список URL
    return saved_urls



def remove_image(web_url: str) -> bool:
    try:
        # 1. Отримуємо ім'я файлу з URL
        # os.path.basename('/static/images/image.png') -> 'image.png'
        unique_name = os.path.basename(web_url)
        
        # 2. Будуємо повний шлях до файлу на диску
        file_path = os.path.join(IMAGES_DIR, unique_name)
        
        # 3. Перевіряємо, чи файл існує
        if os.path.exists(file_path):
            # 4. Видаляємо файл
            os.remove(file_path)
            return True
        else:
            # Файл не знайдено (можливо, вже видалено)
            return False
            
    except Exception as e:
        # Обробка будь-яких помилок (напр., Permission denied)
        print(f"Помилка при видаленні файлу {web_url}: {e}")
        return False
