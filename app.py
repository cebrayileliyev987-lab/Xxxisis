from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import requests
import time
import re

app = Flask(__name__)
CORS(app)

# ==================== KONFIGURASYON ====================
BOT_TOKEN = "8655805223:AAFRr05iUdZYSghcORaCl8MdW3hNpdkbOc4"
ADMIN_ID = 8610336203
RENDER_URL = "https://rinexturknetsorguapi.onrender.com"

# ==================== TELEGRAM BOT ====================
import telebot
bot = telebot.TeleBot(BOT_TOKEN)

# ==================== CPU/RAM KONTROL ====================
MAX_CPU_PERCENT = 50
MAX_RAM_MB = 256

def sistem_kontrol():
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.5)
        ram = psutil.virtual_memory().used / (1024 * 1024)
        if cpu > MAX_CPU_PERCENT or ram > MAX_RAM_MB:
            return False
    except:
        pass
    return True

# ==================== BOT KOMUTLARI ====================
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ Bu bot sadece admin tarafından kullanılabilir!")
        return
    bot.reply_to(message, "🤖 API Oluşturma Botu Aktif!\n\nKomutlar:\n/newapi - Yeni API oluştur\n/durum - Sistem durumu")

@bot.message_handler(commands=['newapi'])
def newapi(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.reply_to(message, "📁 JSON dosyanızı gönderin:")
    bot.register_next_step_handler(message, dosya_al)

def dosya_al(message):
    if not message.document:
        bot.reply_to(message, "❌ Lütfen geçerli bir dosya gönderin!")
        return

    dosya_adi = message.document.file_name
    file_info = bot.get_file(message.document.file_id)
    dosya = bot.download_file(file_info.file_path)
    dosya_icerik = dosya.decode('utf-8')

    try:
        veri = json.loads(dosya_icerik)
        bot.reply_to(message, f"✅ Dosya alındı: {dosya_adi}\nAPI için bir isim girin (örn: turknetapi):")
        bot.register_next_step_handler(message, api_ismi_al, dosya_adi, veri)
    except:
        bot.reply_to(message, "❌ Geçersiz JSON formatı!")

def api_ismi_al(message, dosya_adi, veri):
    api_ismi = re.sub(r'[^a-z0-9]', '', message.text.strip().lower())
    if not api_ismi:
        bot.reply_to(message, "❌ Geçersiz isim!")
        return

    if isinstance(veri, dict):
        veri = [veri]

    endpointler = []
    ilk_kayit = veri[0] if veri else {}
    for anahtar in ilk_kayit.keys():
        ust_anahtar = anahtar.upper()
        if ust_anahtar in ['AD', 'NAME', 'ISIM']:
            endpointler.append('adsoyad')
        elif ust_anahtar in ['TC', 'TC_KIMLIK', 'TCKIMLIK']:
            endpointler.append('tc')
        elif ust_anahtar in ['HAT_NO', 'HATNO', 'PHONE']:
            endpointler.append('hatno')

    api_kodu = f'''
from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

VERI = {json.dumps(veri, ensure_ascii=False, indent=2)}

@app.route('/')
def home():
    return jsonify({{"api": "{api_ismi}", "status": "active", "kayit": len(VERI)}})

@app.route('/tumveriler')
def tumveriler():
    return jsonify(VERI)

@app.route('/sorgula')
def sorgula():
    ad = request.args.get('ad', '').upper()
    soyad = request.args.get('soyad', '').upper()
    tc = request.args.get('tc', '')
    hatno = request.args.get('hatno', '')
    for kayit in VERI:
        if ad and soyad:
            if kayit.get('AD', '').upper() == ad and kayit.get('SOYAD', '').upper() == soyad:
                return jsonify(kayit)
        elif tc:
            if kayit.get('TC_KIMLIK') == tc or kayit.get('TC') == tc:
                return jsonify(kayit)
        elif hatno:
            if kayit.get('HAT_NO') == hatno or kayit.get('HATNO') == hatno:
                return jsonify(kayit)
    return jsonify({{"hata": "Bulunamadi"}}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
'''

    # GitHub'a kaydet
    try:
        from github import Github
        GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo("cebrayileliyev987-lab/Xxxisis")
        try:
            contents = repo.get_contents(f"{api_ismi}.py")
            repo.update_file(f"{api_ismi}.py", f"Update {api_ismi}", api_kodu, contents.sha)
        except:
            repo.create_file(f"{api_ismi}.py", f"Create {api_ismi}", api_kodu)

        link = f"{RENDER_URL}/{api_ismi}"
        bot.reply_to(message, f"✅ API Oluşturuldu!\n\n🔗 Link: {link}\n📝 Örnek: {link}/sorgula?ad=BEYZANUR&soyad=KOSEOGLU")
    except Exception as e:
        bot.reply_to(message, f"❌ GitHub hatası: {e}")

@bot.message_handler(commands=['durum'])
def durum(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.reply_to(message, f"📊 Bot çalışıyor\n🔗 Render: {RENDER_URL}")

# ==================== FLASK WEB SUNUCU ====================
@app.route('/')
def web_home():
    return jsonify({"status": "bot_active", "admin": ADMIN_ID})

# ==================== BOTU BAŞLAT ====================
def start_bot():
    bot.infinity_polling()

if __name__ == '__main__':
    import threading
    threading.Thread(target=start_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=10000)
