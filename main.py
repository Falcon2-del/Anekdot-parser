import requests
from bs4 import BeautifulSoup
import os
import time
import datetime
import random

# --- НАСТРОЙКИ ЯНДЕКС ДИСКА ---
YANDEX_TOKEN = os.getenv("YANDEX_DISK_TOKEN")
ROOT_FOLDER = "/Моя_Соцсеть"
QUEUE_FOLDER = f"{ROOT_FOLDER}/Очередь/Anekdot"
MEDIA_FOLDER = f"{ROOT_FOLDER}/Медиа_Архив"

BASE_URL = "https://www.anekdot.ru"
SEND_DELAY = 2

def yandex_create_folder(path):
    url = "https://cloud-api.yandex.net/v1/disk/resources"
    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    params = {"path": path}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 404:
        requests.put(url, headers=headers, params=params)

def yandex_upload_bytes(path, data):
    url = "https://cloud-api.yandex.net/v1/disk/resources/upload"
    headers = {"Authorization": f"OAuth {YANDEX_TOKEN}"}
    params = {"path": path, "overwrite": "true"}
    res = requests.get(url, headers=headers, params=params)
    if res.status_code == 200:
        upload_url = res.json().get("href")
        requests.put(upload_url, data=data)

def save_to_yandex_disk(target_type, body_content, img_data=None, origin_url=None):
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        microsec = datetime.datetime.now().microsecond
        rand_id = random.randint(1000, 9999)
        post_id = f"{target_type}_{timestamp}_{microsec}_{rand_id}"
        
        post_queue_path = f"{QUEUE_FOLDER}/{post_id}"
        
        yandex_create_folder(ROOT_FOLDER)
        yandex_create_folder(f"{ROOT_FOLDER}/Очередь")
        yandex_create_folder(QUEUE_FOLDER)
        yandex_create_folder(post_queue_path)
        
        unix_time = str(int(time.time()))
        yandex_upload_bytes(f"{post_queue_path}/time.txt", unix_time.encode('utf-8'))
        
        html_body = body_content.replace('\n', '<br>')
        
        if img_data:
            yandex_create_folder(MEDIA_FOLDER)
            original_file_name = f"{post_id}_original.jpg"
            yandex_upload_bytes(f"{MEDIA_FOLDER}/{original_file_name}", img_data)
            yandex_upload_bytes(f"{post_queue_path}/img_thumb.jpg", img_data)
            
            html_template = (
                "<html><body>"
                f"<p style='font-size:18px;'>{html_body}</p>"
                "<div style='text-align:center;'><img src='img_thumb.jpg' style='max-width:100%; border-radius:8px;'></div>"
                f"<br><p style='text-align:center;'><small><a href='{origin_url}'>Открыть оригинал из источника</a></small></p>"
                "</body></html>"
            )
            yandex_upload_bytes(f"{post_queue_path}/content.html", html_template.encode('utf-8'))
        else:
            html_template = f"<html><body><p style='font-size:18px;'>{html_body}</p></body></html>"
            yandex_upload_bytes(f"{post_queue_path}/content.html", html_template.encode('utf-8'))
            
        print(f"  [Яндекс.Диск OK] {post_id} сохранен в очередь.")
        return True
    except Exception as e:
        print(f"Ошибка сохранения на Яндекс Диск: {e}")
        return False

def run_delivery():
    targets = [
        {'url': '/last/anekdot/', 'type': 'анекдот'},
        {'url': '/last/story/', 'type': 'история'},
        {'url': '/last/mem/', 'type': 'мем'}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    
    for target in targets:
        print(f"\nОбработка раздела: {target['type']}")
        url = f"{BASE_URL}{target['url']}"
        try:
            res = requests.get(url, headers=headers, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            items = soup.find_all('div', class_='topicbox')
            
            for item in items:
                text_div = item.find('div', class_='text')
                if target['type'] in ['анекдот', 'история'] and text_div:
                    content = text_div.get_text(separator='\n').strip()
                    if len(content) > 10:
                        if save_to_yandex_disk(target['type'], content):
                            print(f"  [OK] {target['type']} обработан")
                            time.sleep(SEND_DELAY)

                elif target['type'] == 'мем':
                    img_tag = item.find('img')
                    if img_tag:
                        src = img_tag.get('data-src') or img_tag.get('src')
                        if src:
                            if not src.startswith('http'):
                                src = "https:" + src
                            try:
                                img_bytes = requests.get(src, headers=headers, timeout=10).content
                                if save_to_yandex_disk('мем', img_tag.get('alt', ''), img_bytes, origin_url=src):
                                    print(f"  [OK] мем обработан")
                                    time.sleep(SEND_DELAY)
                            except: pass
        except Exception as e:
            print(f"Ошибка при обработке {target['type']}: {e}")

if __name__ == "__main__":
    if not YANDEX_TOKEN:
        print("Ошибка: Не настроен секрет YANDEX_DISK_TOKEN")
    else:
        print("Запуск обработки Anekdot.ru...")
        run_delivery()
        print("Готово!")
