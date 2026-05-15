import requests
from bs4 import BeautifulSoup
import smtplib
import os
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

# --- НАСТРОЙКИ (Берутся из GitHub Secrets) ---
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")

BASE_URL = "https://www.anekdot.ru"
SEND_DELAY = 2  # Интервал между письмами 2 секунды

def send_email(subject, body, img_data=None):
    msg = MIMEMultipart('related') 
    msg['From'] = EMAIL_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = f"Anekdot.ru: {subject}"
    
    html_body = body.replace('\n', '<br>')
    if img_data:
        html_template = "<html><body><p>{0}</p><img src='cid:meme_image'></body></html>"
        msg.attach(MIMEText(html_template.format(html_body), 'html'))
        try:
            img = MIMEImage(img_data)
            img.add_header('Content-ID', '<meme_image>')
            msg.attach(img)
        except: pass
    else:
        msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)
            return True
    except Exception as e:
        print(f"Ошибка отправки: {e}")
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
        # Берем только первую страницу для разового запуска
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
                        if send_email(target['type'], content):
                            print(f"  [OK] {target['type']} отправлен")
                            time.sleep(SEND_DELAY)

                elif target['type'] == 'мем':
                    img_tag = item.find('img')
                    if img_tag:
                        src = img_tag.get('data-src') or img_tag.get('src')
                        if src:
                            try:
                                img_bytes = requests.get(src, headers=headers, timeout=10).content
                                if send_email('мем', img_tag.get('alt', ''), img_bytes):
                                    print(f"  [OK] мем отправлен")
                                    time.sleep(SEND_DELAY)
                            except: pass
        except Exception as e:
            print(f"Ошибка при обработке {target['type']}: {e}")

if __name__ == "__main__":
    if not all([EMAIL_USER, EMAIL_PASS, EMAIL_TO]):
        print("Ошибка: Не настроены секреты (EMAIL_USER, EMAIL_PASS, EMAIL_TO)")
    else:
        print("Запуск рассылки...")
        run_delivery()
        print("Готово!")
