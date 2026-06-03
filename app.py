from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import time
import threading
import psutil
import shutil

app = Flask(__name__)
CORS(app)

# ==================== KONFIGURASYON ====================
BOT_TOKEN = "8655805223:AAFRr05iUdZYSghcORaCl8MdW3hNpdkbOc4"
ADMIN_ID = 8610336203
RENDER_URL = "https://rinexturknetsorguapi.onrender.com"

# Bakım modu
BAKIM_MODU = False

# ==================== TELEGRAM BOT ====================
import telebot
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# Geçici veri depolama
user_data = {}

# ==================== DOSYA OKUYUCU ====================
def dosya_oku(icerik):
    veriler = []
    
    try:
        veri = json.loads(icerik)
        if isinstance(veri, dict):
            return [veri]
        elif isinstance(veri, list):
            return veri
    except:
        pass
    
    for satir in icerik.split('\n'):
        satir = satir.strip()
        if satir:
            try:
                v = json.loads(satir)
                if isinstance(v, dict):
                    veriler.append(v)
            except:
                try:
                    v = json.loads(satir.replace("'", '"'))
                    if isinstance(v, dict):
                        veriler.append(v)
                except:
                    pass
    
    if veriler:
        return veriler
    
    json_pattern = r'\{[^{}]*\}'
    bulunanlar = re.findall(json_pattern, icerik)
    for bul in bulunanlar:
        try:
            veriler.append(json.loads(bul))
        except:
            try:
                veriler.append(json.loads(bul.replace("'", '"')))
            except:
                pass
    
    return veriler if veriler else None

def renk(metin, renk):
    emoji = {
        "kirmizi": "🔴", "yesil": "🟢", "mavi": "🔵",
        "sari": "🟡", "mor": "🟣", "turuncu": "🟠", "beyaz": "⚪"
    }
    return f"{emoji.get(renk, '⚪')} {metin}"

# ==================== API YÖNETİMİ ====================
def api_dosyalari():
    return [f.replace('.py', '') for f in os.listdir('.') if f.endswith('.py') and f not in ['app.py']]

def api_durdur(api_ismi):
    try:
        os.remove(f"{api_ismi}.py")
        return True
    except:
        return False

def api_sil(api_ismi):
    try:
        os.remove(f"{api_ismi}.py")
        return True
    except:
        return False

def api_bakim_modu(durum):
    global BAKIM_MODU
    BAKIM_MODU = durum
    return BAKIM_MODU

# ==================== BOT KOMUTLARI ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ Yetkiniz yok!")
        return
    
    bot.reply_to(message, f"""
{renk('HOŞ GELDİNİZ', 'yesil')}

🤖 *API YÖNETİM BOTU*

{renk('📌 KOMUTLAR:', 'mavi')}
/newapi - Yeni API oluştur
/liste - API listesi
/durum - Sistem durumu
/bakim - Bakım modu
/api_bakim - API bakım
/api_durdur - API durdur
/api_sil - API sil
/api_yeniden - API yeniden başlat
/temizlik - Temizlik
/yardim - Yardım

{renk('⚡ ÖZELLİKLER:', 'mor')}
• JSON/TXT/Karışık formatlar
• Otomatik endpoint
• API yönetimi
• Bakım modu
• Düşük CPU/RAM

{renk('🔗 LİNKLER:', 'turuncu')}
🌐 {RENDER_URL}
""", parse_mode='Markdown')

@bot.message_handler(commands=['newapi'])
def cmd_newapi(message):
    if message.chat.id != ADMIN_ID:
        return
    
    if BAKIM_MODU:
        bot.reply_to(message, "⚠️ Bakım modu aktif! Şu anda yeni API oluşturulamaz.")
        return
    
    user_data[message.chat.id] = {'adim': 1}
    bot.reply_to(message, f"""
{renk('YENİ API', 'yesil')}

📁 *Adım 1/2*
JSON veya TXT dosyanızı gönderin.

{renk('Örnek:', 'sari')}
```json
{{"AD":"AHMET","SOYAD":"YILMAZ","TC":"12345678901"}}
