from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import time
import threading
import psutil
import requests

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

user_data = {}

# ==================== DOSYA OKUYUCU (TÜM VERİLERİ ALIR) ====================
def dosya_oku_tum(icerik):
    """Dosyadaki TÜM verileri alır, her formatı destekler"""
    veriler = []
    
    # 1. Tam JSON dene
    try:
        veri = json.loads(icerik)
        if isinstance(veri, dict):
            return [veri]
        elif isinstance(veri, list):
            return veri
    except:
        pass
    
    # 2. Satır satır JSON dene (her satırda ayrı JSON)
    for satir in icerik.split('\n'):
        satir = satir.strip()
        if satir:
            try:
                v = json.loads(satir)
                if isinstance(v, dict):
                    veriler.append(v)
            except:
                pass
    
    if veriler:
        return veriler
    
    # 3. Virgülle ayrılmış JSON'ları bul
    try:
        # [ {...}, {...} ] formatı
        if icerik.strip().startswith('['):
            veri = json.loads(icerik)
            if isinstance(veri, list):
                return veri
    except:
        pass
    
    # 4. İçindeki tüm JSON'ları regex ile bul
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
    
    if veriler:
        return veriler
    
    # 5. Hiçbir şey bulunamazsa boş döndür
    return None

# ==================== RENK ====================
def renk(metin, renk):
    emoji = {"kirmizi": "🔴", "yesil": "🟢", "mavi": "🔵", "sari": "🟡", "mor": "🟣", "turuncu": "🟠", "beyaz": "⚪"}
    return f"{emoji.get(renk, '⚪')} {metin}"

def api_dosyalari():
    return [f.replace('.py', '') for f in os.listdir('.') if f.endswith('.py') and f not in ['app.py']]

def api_sil(api_ismi):
    try:
        os.remove(f"{api_ismi}.py")
        return True
    except:
        return False

# ==================== BOT KOMUTLARI ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ Yetkiniz yok!")
        return
    bot.reply_to(message, 
        "🟢 HOŞ GELDİNİZ\n\n"
        "🤖 API YÖNETİM BOTU\n\n"
        "📌 KOMUTLAR:\n"
        "/newapi - Yeni API oluştur\n"
        "/liste - API listesi\n"
        "/durum - Sistem durumu\n"
        "/api_sil - API sil\n"
        "/bakim - Bakım modu\n"
        "/temizlik - Temizlik\n"
        "/yardim - Yardım\n\n"
        f"🔗 {RENDER_URL}")

@bot.message_handler(commands=['newapi'])
def cmd_newapi(message):
    if message.chat.id != ADMIN_ID:
        return
    if BAKIM_MODU:
        bot.reply_to(message, "⚠️ Bakım modu aktif!")
        return
    user_data[message.chat.id] = {'adim': 1}
    bot.reply_to(message, "📁 *JSON/TXT dosyanızı gönderin*\n\nDesteklenen formatlar:\n• Tek JSON nesnesi\n• JSON dizisi\n• Satır satır JSON\n\nÖrnek:\n{\"AD\":\"AHMET\",\"SOYAD\":\"YILMAZ\"}", parse_mode='Markdown')
    bot.register_next_step_handler(message, dosya_al)

def dosya_al(message):
    chat_id = message.chat.id
    
    if not message.document:
        bot.reply_to(message, "❌ Lütfen bir dosya gönderin!")
        bot.register_next_step_handler(message, dosya_al)
        return
    
    dosya_adi = message.document.file_name
    bot.reply_to(message, f"📥 *Dosya:* {dosya_adi}\n⏳ İşleniyor...", parse_mode='Markdown')
    
    try:
        # Dosyayı indir - FARKLI YÖNTEM
        file_id = message.document.file_id
        file_info = bot.get_file(file_id)
        file_path = file_info.file_path
        
        # Telegram API ile dosyayı indir
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        response = requests.get(url)
        
        if response.status_code != 200:
            bot.reply_to(message, "❌ Dosya indirilemedi!")
            return
        
        icerik = response.text
        
        # Dosyayı oku
        veri = dosya_oku_tum(icerik)
        
        if not veri or len(veri) == 0:
            bot.reply_to(message, "❌ Dosya okunamadı! JSON formatında değil.\n\nİlk 200 karakter:\n" + icerik[:200])
            return
        
        user_data[chat_id]['veri'] = veri
        user_data[chat_id]['dosya_adi'] = dosya_adi
        
        ilk = veri[0] if veri else {}
        anahtarlar = list(ilk.keys())[:8]
        
        bot.reply_to(message, 
            f"✅ *DOSYA OKUNDU!*\n\n"
            f"📊 *Kayıt sayısı:* {len(veri)}\n"
            f"🔑 *Alanlar:* {', '.join(anahtarlar)}{'...' if len(ilk) > 8 else ''}\n\n"
            f"📝 *API için isim girin:*\n"
            f"(küçük harf ve rakam, örn: musteriapi)", parse_mode='Markdown')
        bot.register_next_step_handler(message, api_ismi_al)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)[:200]}")

def api_ismi_al(message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or 'veri' not in user_data[chat_id]:
        bot.reply_to(message, "❌ Önce /newapi ile başlayın!")
        return
    
    api_ismi = re.sub(r'[^a-z0-9]', '', message.text.strip().lower())
    if not api_ismi or len(api_ismi) < 2:
        bot.reply_to(message, "❌ Geçersiz isim! En az 2 karakter, sadece harf ve rakam.")
        return
    
    veri = user_data[chat_id]['veri']
    dosya_adi = user_data[chat_id].get('dosya_adi', 'bilinmiyor')
    
    bot.reply_to(message, f"⚙️ *API oluşturuluyor:* {api_ismi}\n⏳ Lütfen bekleyin...", parse_mode='Markdown')
    
    # Endpoint algılama
    ilk = veri[0] if veri else {}
    endpoints = []
    for k in ilk.keys():
        uk = k.upper()
        if uk in ['AD', 'NAME', 'ISIM', 'FIRST_NAME']:
            endpoints.append('adsoyad')
        if uk in ['SOYAD', 'SURNAME', 'LAST_NAME']:
            endpoints.append('adsoyad')
        if uk in ['TC', 'TC_KIMLIK', 'TCKIMLIK', 'IDENTITY']:
            endpoints.append('tc')
        if uk in ['HAT_NO', 'HATNO', 'PHONE', 'TEL', 'TELEFON']:
            endpoints.append('hatno')
    
    endpoints = list(set(endpoints))
    if not endpoints:
        endpoints = ['tumveriler']
    
    api_link = f"{RENDER_URL}/{api_ismi}"
    
    # API kodu oluştur
    api_kodu = "from flask import Flask, request, jsonify\n"
    api_kodu += "from flask_cors import CORS\n"
    api_kodu += "import json\n\n"
    api_kodu += "app = Flask(__name__)\n"
    api_kodu += "CORS(app)\n\n"
    api_kodu += f"VERI = {json.dumps(veri, ensure_ascii=False, indent=2)}\n\n"
    api_kodu += "@app.route('/')\n"
    api_kodu += "def home():\n"
    api_kodu += f"    return jsonify({{'api': '{api_ismi}', 'kayit': len(VERI), 'endpoints': {endpoints}}})\n\n"
    api_kodu += "@app.route('/tumveriler')\n"
    api_kodu += "def tumveriler():\n"
    api_kodu += "    return jsonify(VERI)\n\n"
    api_kodu += "@app.route('/sorgula')\n"
    api_kodu += "def sorgula():\n"
    api_kodu += "    ad = request.args.get('ad', '').upper()\n"
    api_kodu += "    soyad = request.args.get('soyad', '').upper()\n"
    api_kodu += "    tc = request.args.get('tc', '')\n"
    api_kodu += "    hatno = request.args.get('hatno', '')\n"
    api_kodu += "    for v in VERI:\n"
    api_kodu += "        if ad and soyad:\n"
    api_kodu += "            if v.get('AD', '').upper() == ad and v.get('SOYAD', '').upper() == soyad:\n"
    api_kodu += "                return jsonify(v)\n"
    api_kodu += "        elif tc:\n"
    api_kodu += "            if str(v.get('TC_KIMLIK', v.get('TC', ''))) == tc:\n"
    api_kodu += "                return jsonify(v)\n"
    api_kodu += "        elif hatno:\n"
    api_kodu += "            if str(v.get('HAT_NO', v.get('HATNO', ''))) == hatno:\n"
    api_kodu += "                return jsonify(v)\n"
    api_kodu += "    return jsonify({'hata': 'Bulunamadi'}), 404\n\n"
    api_kodu += "@app.route('/sorgu/adsoyad', methods=['POST'])\n"
    api_kodu += "def sorgu_adsoyad():\n"
    api_kodu += "    data = request.json\n"
    api_kodu += "    ad = data.get('ad', '').upper()\n"
    api_kodu += "    soyad = data.get('soyad', '').upper()\n"
    api_kodu += "    for v in VERI:\n"
    api_kodu += "        if v.get('AD', '').upper() == ad and v.get('SOYAD', '').upper() == soyad:\n"
    api_kodu += "            return jsonify(v)\n"
    api_kodu += "    return jsonify({'hata': 'Bulunamadi'}), 404\n\n"
    api_kodu += "@app.route('/sorgu/tc', methods=['POST'])\n"
    api_kodu += "def sorgu_tc():\n"
    api_kodu += "    data = request.json\n"
    api_kodu += "    tc = data.get('tc', '')\n"
    api_kodu += "    for v in VERI:\n"
    api_kodu += "        if str(v.get('TC_KIMLIK', v.get('TC', ''))) == tc:\n"
    api_kodu += "            return jsonify(v)\n"
    api_kodu += "    return jsonify({'hata': 'Bulunamadi'}), 404\n\n"
    api_kodu += "@app.route('/sorgu/hatno', methods=['POST'])\n"
    api_kodu += "def sorgu_hatno():\n"
    api_kodu += "    data = request.json\n"
    api_kodu += "    hatno = data.get('hatno', '')\n"
    api_kodu += "    for v in VERI:\n"
    api_kodu += "        if str(v.get('HAT_NO', v.get('HATNO', ''))) == hatno:\n"
    api_kodu += "            return jsonify(v)\n"
    api_kodu += "    return jsonify({'hata': 'Bulunamadi'}), 404\n\n"
    api_kodu += "if __name__ == '__main__':\n"
    api_kodu += "    app.run(host='0.0.0.0', port=10000)\n"
    
    try:
        with open(f"{api_ismi}.py", 'w', encoding='utf-8') as f:
            f.write(api_kodu)
        
        # Kullanım örnekleri
        ornekler = []
        if 'adsoyad' in endpoints:
            ornekler.append(f"• {api_link}/sorgula?ad=AHMET&soyad=YILMAZ")
        if 'tc' in endpoints:
            ornekler.append(f"• {api_link}/sorgula?tc=12345678901")
        if 'hatno' in endpoints:
            ornekler.append(f"• {api_link}/sorgula?hatno=1234567")
        
        ornek_text = "\n".join(ornekler) if ornekler else f"• {api_link}/tumveriler"
        
        bot.reply_to(message, 
            f"✅ *API OLUŞTURULDU!*\n\n"
            f"📌 *İsim:* `{api_ismi}`\n"
            f"📁 *Dosya:* {dosya_adi}\n"
            f"📊 *Kayıt:* {len(veri)}\n"
            f"🔗 *Link:* {api_link}\n\n"
            f"🔗 *KULLANIM:*\n"
            f"{ornek_text}\n\n"
            f"📝 *POST ÖRNEĞİ:*\n"
            f"```json\n{{\"ad\":\"AHMET\",\"soyad\":\"YILMAZ\"}}\n```\n\n"
            f"⚡ *TÜM VERİLER:* {api_link}/tumveriler\n\n"
            f"✅ *API AKTİF!*", parse_mode='Markdown')
        
        del user_data[chat_id]
        
    except Exception as e:
        bot.reply_to(message, f"❌ Oluşturma hatası: {str(e)[:200]}")

@bot.message_handler(commands=['liste'])
def cmd_liste(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_dosyalari()
    if not apiler:
        bot.reply_to(message, "📭 Henüz API yok.\n/newapi ile oluşturun.")
    else:
        liste = "\n".join([f"• `{a}` - {RENDER_URL}/{a}" for a in apiler])
        bot.reply_to(message, f"📋 *API LİSTEM*\n\n{liste}\n\n*Toplam:* {len(apiler)} API", parse_mode='Markdown')

@bot.message_handler(commands=['durum'])
def cmd_durum(message):
    if message.chat.id != ADMIN_ID:
        return
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    apiler = api_dosyalari()
    bot.reply_to(message, 
        f"📊 *SİSTEM DURUMU*\n\n"
        f"💻 *CPU:* %{cpu}\n"
        f"🧠 *RAM:* %{ram}\n"
        f"🤖 *Bot:* {'Aktif' if not BAKIM_MODU else 'Bakım'}\n"
        f"📦 *API Sayısı:* {len(apiler)}\n"
        f"👑 *Admin:* {ADMIN_ID}\n"
        f"🔗 {RENDER_URL}", parse_mode='Markdown')

@bot.message_handler(commands=['bakim'])
def cmd_bakim(message):
    if message.chat.id != ADMIN_ID:
        return
    global BAKIM_MODU
    BAKIM_MODU = not BAKIM_MODU
    durum = "AÇIK" if BAKIM_MODU else "KAPALI"
    bot.reply_to(message, f"🔧 *BAKIM MODU*\n\nDurum: {durum}", parse_mode='Markdown')

@bot.message_handler(commands=['api_sil'])
def cmd_api_sil(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_dosyalari()
    if not apiler:
        bot.reply_to(message, "❌ Silinecek API yok!")
        return
    liste = "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)])
    bot.reply_to(message, f"🗑️ *Hangi API silinsin?*\n\n{liste}\n\nSayı veya isim girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, api_sil_sec)

def api_sil_sec(message):
    apiler = api_dosyalari()
    secim = message.text.strip()
    if secim.isdigit() and 1 <= int(secim) <= len(apiler):
        api_ismi = apiler[int(secim)-1]
    elif secim in apiler:
        api_ismi = secim
    else:
        bot.reply_to(message, "❌ Geçersiz seçim!")
        return
    if api_sil(api_ismi):
        bot.reply_to(message, f"🗑️ `{api_ismi}` API'si silindi!", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Silinemedi!")

@bot.message_handler(commands=['temizlik'])
def cmd_temizlik(message):
    if message.chat.id != ADMIN_ID:
        return
    silinen = 0
    for f in os.listdir('.'):
        if f.endswith('.py') and f not in ['app.py']:
            os.remove(f)
            silinen += 1
    bot.reply_to(message, f"🧹 *TEMİZLİK*\n\n{silinen} API dosyası silindi.", parse_mode='Markdown')

@bot.message_handler(commands=['yardim'])
def cmd_yardim(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.reply_to(message,
        "📖 *YARDIM MENÜSÜ*\n\n"
        "📌 *KOMUTLAR:*\n"
        "/newapi - Yeni API oluştur\n"
        "/liste - API listesi\n"
        "/durum - Sistem durumu\n"
        "/api_sil - API sil\n"
        "/bakim - Bakım modu\n"
        "/temizlik - Temizlik\n"
        "/yardim - Bu menü\n\n"
        f"🔗 {RENDER_URL}", parse_mode='Markdown')

# ==================== WEB SUNUCU ====================
@app.route('/')
def web_home():
    if BAKIM_MODU:
        return jsonify({"status": "bakim", "message": "Bakım modu aktif"})
    apiler = api_dosyalari()
    return jsonify({
        "status": "active",
        "bot": "API Yönetim Botu",
        "api_sayisi": len(apiler),
        "apis": apiler,
        "bakim_modu": BAKIM_MODU
    })

@app.route('/api/<api_ismi>/durum')
def api_durum_web(api_ismi):
    apiler = api_dosyalari()
    if api_ismi in apiler:
        return jsonify({"api": api_ismi, "status": "active", "url": f"{RENDER_URL}/{api_ismi}"})
    else:
        return jsonify({"api": api_ismi, "status": "durduruldu", "message": "API bulunamadı"}), 404

# ==================== BOTU BAŞLAT ====================
def start_bot():
    print("🤖 Bot başlatılıyor...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    print(f"🔗 Render URL: {RENDER_URL}")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == '__main__':
    thread = threading.Thread(target=start_bot, daemon=True)
    thread.start()
    print("🚀 Flask sunucusu başlatılıyor...")
    app.run(host='0.0.0.0', port=10000, debug=False)
