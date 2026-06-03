import telebot
import requests
import json
import os
import re
import time
import psutil
from github import Github
from flask import Flask, request, jsonify
from threading import Thread

# ==================== KONFIGURASYON ====================
BOT_TOKEN = "8655805223:AAFRr05iUdZYSghcORaCl8MdW3hNpdkbOc4"
ADMIN_ID = 8610336203
RENDER_URL = "https://rinexturknetsorguapi.onrender.com"
GITHUB_TOKEN = "YOUR_GITHUB_TOKEN"  # GitHub token'ını buraya gir
GITHUB_REPO = "cebrayileliyev987-lab/Xxxisis"

# CPU/RAM limitleri (Render ücretsiz için)
MAX_CPU_PERCENT = 50
MAX_RAM_MB = 256

bot = telebot.TeleBot(BOT_TOKEN)

# Veritabanı (geçici)
api_listesi = {}

# ==================== CPU/RAM KONTROL ====================
def sistem_kontrol():
    """CPU ve RAM kullanımını kontrol et, limit aşılırsa bekle"""
    cpu_kullanim = psutil.cpu_percent(interval=1)
    ram_kullanim = psutil.virtual_memory().used / (1024 * 1024)  # MB
    
    if cpu_kullanim > MAX_CPU_PERCENT:
        time.sleep(2)
        return False
    if ram_kullanim > MAX_RAM_MB:
        time.sleep(3)
        return False
    return True

# ==================== API OLUŞTURUCU ====================
def api_olustur(dosya_adi, dosya_icerik, api_ismi):
    """Dosyadan otomatik API oluşturur"""
    
    # JSON formatını kontrol et
    try:
        veri = json.loads(dosya_icerik)
        if isinstance(veri, dict):
            veri = [veri]
    except:
        veri = []
    
    # Otomatik endpoint'leri bul
    endpointler = []
    if veri and len(veri) > 0:
        anahtarlar = list(veri[0].keys())
        for anahtar in anahtarlar:
            if anahtar.upper() in ['AD', 'NAME', 'ISIM', 'FIRST_NAME']:
                endpointler.append('adsoyad')
            elif anahtar.upper() in ['TC', 'TCKIMLIK', 'TC_KIMLIK', 'IDENTITY']:
                endpointler.append('tc')
            elif anahtar.upper() in ['HATNO', 'HAT_NO', 'PHONE', 'TEL']:
                endpointler.append('hatno')
    
    # API kodu oluştur
    api_kodu = f'''
from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Veriler
VERI = {json.dumps(veri, ensure_ascii=False, indent=2)}

@app.route('/')
def home():
    return jsonifice({{
        "api": "{api_ismi}",
        "status": "active",
        "endpoints": {json.dumps(endpointler)},
        "kayit_sayisi": len(VERI)
    }})

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
            if kayit.get('TC_KIMLIK', '') == tc or kayit.get('TC', '') == tc:
                return jsonify(kayit)
        elif hatno:
            if kayit.get('HAT_NO', '') == hatno or kayit.get('HATNO', '') == hatno:
                return jsonify(kayit)
    
    return jsonify({{"hata": "Bulunamadi"}}), 404

@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad():
    data = request.get_json()
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    for kayit in VERI:
        if kayit.get('AD', '').upper() == ad and kayit.get('SOYAD', '').upper() == soyad:
            return jsonify(kayit)
    return jsonify({{"hata": "Bulunamadi"}}), 404

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc():
    data = request.get_json()
    tc = data.get('tc', '')
    for kayit in VERI:
        if kayit.get('TC_KIMLIK', '') == tc or kayit.get('TC', '') == tc:
            return jsonify(kayit)
    return jsonify({{"hata": "Bulunamadi"}}), 404

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno():
    data = request.get_json()
    hatno = data.get('hatno', '')
    for kayit in VERI:
        if kayit.get('HAT_NO', '') == hatno or kayit.get('HATNO', '') == hatno:
            return jsonify(kayit)
    return jsonify({{"hata": "Bulunamadi"}}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
'''
    return api_kodu, endpointler

def render_yukle(dosya_adi, api_ismi, api_kodu):
    """API kodunu Render'a yükler"""
    try:
        # GitHub'a yükle
        g = Github(GITHUB_TOKEN)
        repo = g.get_user().get_repo(GITHUB_REPO)
        
        # Dosyayı güncelle
        try:
            contents = repo.get_contents(f"{api_ismi}.py")
            repo.update_file(f"{api_ismi}.py", f"Update {api_ismi} API", api_kodu, contents.sha)
        except:
            repo.create_file(f"{api_ismi}.py", f"Create {api_ismi} API", api_kodu)
        
        return f"{RENDER_URL}/{api_ismi}"
    
    except Exception as e:
        return None

# ==================== BOT KOMUTLARI ====================
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ Bu bot sadece admin tarafından kullanılabilir!")
        return
    
    bot.reply_to(message, f"""
🤖 *API Oluşturma Botu Aktif!*

📌 *Komutlar:*
/newapi - Yeni API oluştur
/liste - API listesini göster
/sil - API sil
/durum - Sistem durumu
/yardim - Yardım

⚡ *Özellikler:*
• Otomatik endpoint oluşturma
• Her formatı destekler
• CPU/RAM dostu
• Dış dünyaya açık

🔗 *Render URL:* {RENDER_URL}
""", parse_mode='Markdown')

@bot.message_handler(commands=['newapi'])
def newapi(message):
    if message.chat.id != ADMIN_ID:
        return
    
    bot.reply_to(message, "📁 *Yeni API Oluşturma*\n\nLütfen JSON dosyanızı gönderin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, dosya_al)

def dosya_al(message):
    if not message.document:
        bot.reply_to(message, "❌ Lütfen geçerli bir dosya gönderin!")
        return
    
    # Dosyayı indir
    dosya_adi = message.document.file_name
    dosya_info = bot.get_file(message.document.file_id)
    dosya = bot.download_file(dosya_info.file_path)
    dosya_icerik = dosya.decode('utf-8')
    
    bot.reply_to(message, f"✅ Dosya alındı: {dosya_adi}\n\n📝 API için bir isim girin (örnek: turknetapi):")
    bot.register_next_step_handler(message, api_ismi_al, dosya_adi, dosya_icerik)

def api_ismi_al(message, dosya_adi, dosya_icerik):
    api_ismi = message.text.strip().lower()
    api_ismi = re.sub(r'[^a-z0-9]', '', api_ismi)
    
    if not api_ismi:
        bot.reply_to(message, "❌ Geçersiz isim!")
        return
    
    bot.reply_to(message, "⏳ API oluşturuluyor... (bu 1-2 dakika sürebilir)")
    
    # CPU/RAM kontrolü
    if not sistem_kontrol():
        bot.reply_to(message, "⚠️ Sistem yoğun, lütfen biraz bekleyin...")
        time.sleep(5)
    
    # API oluştur
    api_kodu, endpointler = api_olustur(dosya_adi, dosya_icerik, api_ismi)
    
    # Render'a yükle
    link = render_yukle(dosya_adi, api_ismi, api_kodu)
    
    if link:
        api_listesi[api_ismi] = {"dosya": dosya_adi, "link": link, "endpointler": endpointler}
        
        endpoint_text = "\n".join([f"• /sorgula?{e}=VALUE" for e in endpointler]) if endpointler else "• Otomatik algılandı"
        
        bot.reply_to(message, f"""
✅ *API Başarıyla Oluşturuldu!*

📌 *API Adı:* {api_ismi}
🔗 *API Linki:* {link}

📝 *Kullanım:*

**GET Sorgular:**
• {link}/tumveriler
• {link}/sorgula?ad=BEYZANUR&soyad=KÖSEOĞLU

**POST Sorgular:**
• {link}/sorgu/adsoyad
• {link}/sorgu/tc  
• {link}/sorgu/hatno

**Örnek POST:**
```json
{{
  "ad": "BEYZANUR",
  "soyad": "KÖSEOĞLU"
}}
