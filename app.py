from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import time
import threading
import psutil
import csv
import io

app = Flask(__name__)
CORS(app)

# ==================== KONFIGURASYON ====================
BOT_TOKEN = "8655805223:AAGf7anf_9bMlVB1B9MXZVgsSnytGgum5ic"
ADMIN_ID = 8610336203
RENDER_URL = "https://rinexturknetsorguapi.onrender.com"

# Sistem değişkenleri
BAKIM_MODU = False
API_BAKIM = {}  # API bazında bakım modu
API_ZAMANLAYICI = {}  # API zamanlayıcı

# ==================== TELEGRAM BOT ====================
import telebot
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

user_data = {}

# ==================== DOSYA OKUYUCU (TÜM FORMATLAR) ====================
def dosya_oku_tum(icerik, dosya_adi=""):
    """JSON, TXT, CSV her formatı okur, TÜM verileri alır"""
    veriler = []
    
    # 1. CSV formatı
    if dosya_adi.endswith('.csv') or (',' in icerik[:100] and '"' not in icerik[:100]):
        try:
            csv_reader = csv.DictReader(io.StringIO(icerik))
            for row in csv_reader:
                veriler.append(row)
            if veriler:
                return veriler
        except:
            pass
    
    # 2. Tam JSON dene
    try:
        veri = json.loads(icerik)
        if isinstance(veri, dict):
            return [veri]
        elif isinstance(veri, list):
            return veri
    except:
        pass
    
    # 3. Satır satır JSON dene
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
    
    # 4. İçindeki tüm JSON'ları bul
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
    
    # 5. TXT olarak kaydet (anahtar-değer)
    satirlar = icerik.split('\n')
    if len(satirlar) < 50:
        veri = {}
        for satir in satirlar:
            if ':' in satir:
                key, val = satir.split(':', 1)
                veri[key.strip()] = val.strip()
        if veri:
            return [veri]
    
    return None

# ==================== SİSTEM İZLEME ====================
def sistem_durumu():
    cpu = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory()
    return {
        'cpu': cpu,
        'ram_kullanim': ram.used / (1024 * 1024),
        'ram_toplam': ram.total / (1024 * 1024),
        'ram_yuzde': ram.percent
    }

# ==================== API YÖNETİMİ ====================
def api_dosyalari():
    return [f.replace('.py', '') for f in os.listdir('.') if f.endswith('.py') and f not in ['app.py']]

def api_olustur(api_ismi, veri):
    api_link = f"{RENDER_URL}/{api_ismi}"
    
    # Endpointleri otomatik bul
    ilk = veri[0] if veri else {}
    endpoints = []
    for k in ilk.keys():
        uk = k.upper()
        if uk in ['AD', 'NAME', 'ISIM', 'FIRST_NAME']:
            endpoints.append('adsoyad')
        if uk in ['SOYAD', 'SURNAME', 'LAST_NAME']:
            endpoints.append('adsoyad')
        if uk in ['TC', 'TC_KIMLIK', 'TCKIMLIK']:
            endpoints.append('tc')
        if uk in ['HAT_NO', 'HATNO', 'PHONE', 'TEL']:
            endpoints.append('hatno')
    endpoints = list(set(endpoints))
    
    # API kodu
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
    
    with open(f"{api_ismi}.py", 'w', encoding='utf-8') as f:
        f.write(api_kodu)
    
    return api_link

def api_durdur(api_ismi):
    try:
        os.remove(f"{api_ismi}.py")
        return True
    except:
        return False

def api_bakim(api_ismi, durum):
    API_BAKIM[api_ismi] = durum
    return True

def api_zamanla(api_ismi, sure):
    """API'yi belirli süre sonra durdur (saniye cinsinden)"""
    def zamanlayici():
        time.sleep(sure)
        api_durdur(api_ismi)
        if api_ismi in API_ZAMANLAYICI:
            del API_ZAMANLAYICI[api_ismi]
    
    if api_ismi in API_ZAMANLAYICI:
        return False
    
    thread = threading.Thread(target=zamanlayici, daemon=True)
    thread.start()
    API_ZAMANLAYICI[api_ismi] = thread
    return True

# ==================== BOT KOMUTLARI ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ Yetkiniz yok!")
        return
    
    sys = sistem_durumu()
    bot.reply_to(message, 
        f"🟢 *API YÖNETİM BOTU*\n\n"
        f"🤖 *Durum:* Aktif\n"
        f"💻 *CPU:* %{sys['cpu']:.0f}\n"
        f"🧠 *RAM:* {sys['ram_kullanim']:.0f}/{sys['ram_toplam']:.0f} MB\n\n"
        f"📌 *KOMUTLAR:*\n"
        f"/newapi - Yeni API oluştur\n"
        f"/liste - API listesi\n"
        f"/durum - Detaylı sistem durumu\n"
        f"/api_durdur - API durdur\n"
        f"/api_baslat - API başlat\n"
        f"/api_sil - API sil\n"
        f"/api_bakim - API bakım\n"
        f"/api_zamanla - API zamanla\n"
        f"/bakim - Bot bakım\n"
        f"/temizlik - Temizlik\n"
        f"/yardim - Yardım\n\n"
        f"🔗 {RENDER_URL}", parse_mode='Markdown')

@bot.message_handler(commands=['newapi'])
def cmd_newapi(message):
    if message.chat.id != ADMIN_ID:
        return
    if BAKIM_MODU:
        bot.reply_to(message, "⚠️ Bakım modu aktif!")
        return
    
    user_data[message.chat.id] = {'adim': 1}
    bot.reply_to(message, 
        "📁 *Dosyanızı gönderin*\n\n"
        "✅ Desteklenen formatlar:\n"
        "• JSON (.json)\n"
        "• TXT (.txt)\n"
        "• CSV (.csv)\n\n"
        "📝 Dosyadaki TÜM veriler otomatik API olacak!\n\n"
        "Dosyayı gönderin:", parse_mode='Markdown')
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
        file_info = bot.get_file(message.document.file_id)
        file_path = file_info.file_path
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        import requests
        response = requests.get(url)
        
        if response.status_code != 200:
            bot.reply_to(message, "❌ Dosya indirilemedi!")
            return
        
        icerik = response.text
        veri = dosya_oku_tum(icerik, dosya_adi)
        
        if not veri or len(veri) == 0:
            bot.reply_to(message, "❌ Dosya okunamadı! Format desteklenmiyor.")
            return
        
        user_data[chat_id]['veri'] = veri
        user_data[chat_id]['dosya_adi'] = dosya_adi
        
        ilk = veri[0] if veri else {}
        anahtarlar = list(ilk.keys())[:8]
        
        bot.reply_to(message, 
            f"✅ *DOSYA OKUNDU!*\n\n"
            f"📊 *Kayıt:* {len(veri)}\n"
            f"🔑 *Alanlar:* {', '.join(anahtarlar)}{'...' if len(ilk) > 8 else ''}\n\n"
            f"📝 *API için isim girin:*\n"
            f"(küçük harf, rakam, tire)", parse_mode='Markdown')
        bot.register_next_step_handler(message, api_ismi_al)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)[:200]}")

def api_ismi_al(message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or 'veri' not in user_data[chat_id]:
        bot.reply_to(message, "❌ Önce /newapi ile başlayın!")
        return
    
    api_ismi = re.sub(r'[^a-z0-9-]', '', message.text.strip().lower())
    if not api_ismi or len(api_ismi) < 2:
        bot.reply_to(message, "❌ Geçersiz isim! En az 2 karakter.")
        return
    
    veri = user_data[chat_id]['veri']
    dosya_adi = user_data[chat_id]['dosya_adi']
    
    bot.reply_to(message, f"⚙️ *API oluşturuluyor:* {api_ismi}\n⏳ Lütfen bekleyin...", parse_mode='Markdown')
    
    try:
        api_link = api_olustur(api_ismi, veri)
        
        bot.reply_to(message, 
            f"✅ *API OLUŞTURULDU!*\n\n"
            f"📌 *İsim:* `{api_ismi}`\n"
            f"📁 *Dosya:* {dosya_adi}\n"
            f"📊 *Kayıt:* {len(veri)}\n"
            f"🔗 *Link:* {api_link}\n\n"
            f"🔗 *KULLANIM:*\n"
            f"• {api_link}/tumveriler\n"
            f"• {api_link}/sorgula?ad=AHMET&soyad=YILMAZ\n\n"
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
        liste = "\n".join([f"• `{a}`" for a in apiler])
        bot.reply_to(message, f"📋 *API LİSTEM*\n\n{liste}\n\n*Toplam:* {len(apiler)} API", parse_mode='Markdown')

@bot.message_handler(commands=['durum'])
def cmd_durum(message):
    if message.chat.id != ADMIN_ID:
        return
    sys = sistem_durumu()
    apiler = api_dosyalari()
    bot.reply_to(message, 
        f"📊 *SİSTEM DURUMU*\n\n"
        f"💻 *CPU:* %{sys['cpu']:.1f}\n"
        f"🧠 *RAM:* {sys['ram_kullanim']:.0f}/{sys['ram_toplam']:.0f} MB (%{sys['ram_yuzde']:.0f})\n"
        f"🤖 *Bot:* {'Aktif' if not BAKIM_MODU else 'Bakım'}\n"
        f"📦 *API Sayısı:* {len(apiler)}\n"
        f"⏱️ *Zamanlı API:* {len(API_ZAMANLAYICI)}\n"
        f"👑 *Admin:* {ADMIN_ID}\n"
        f"🔗 {RENDER_URL}", parse_mode='Markdown')

@bot.message_handler(commands=['api_durdur'])
def cmd_api_durdur(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_dosyalari()
    if not apiler:
        bot.reply_to(message, "❌ API yok!")
        return
    bot.reply_to(message, f"⏹️ *Hangi API durdurulsun?*\n\n" + "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)]), parse_mode='Markdown')
    bot.register_next_step_handler(message, api_durdur_sec)

def api_durdur_sec(message):
    apiler = api_dosyalari()
    secim = message.text.strip()
    if secim.isdigit() and 1 <= int(secim) <= len(apiler):
        api_ismi = apiler[int(secim)-1]
    elif secim in apiler:
        api_ismi = secim
    else:
        bot.reply_to(message, "❌ Geçersiz seçim!")
        return
    if api_durdur(api_ismi):
        bot.reply_to(message, f"⏹️ `{api_ismi}` durduruldu!", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Durdurulamadı!")

@bot.message_handler(commands=['api_sil'])
def cmd_api_sil(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_dosyalari()
    if not apiler:
        bot.reply_to(message, "❌ API yok!")
        return
    bot.reply_to(message, f"🗑️ *Hangi API silinsin?*\n\n" + "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)]), parse_mode='Markdown')
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
    if api_durdur(api_ismi):
        bot.reply_to(message, f"🗑️ `{api_ismi}` silindi!", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Silinemedi!")

@bot.message_handler(commands=['api_zamanla'])
def cmd_api_zamanla(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_dosyalari()
    if not apiler:
        bot.reply_to(message, "❌ API yok!")
        return
    bot.reply_to(message, f"⏰ *Hangi API zamanlansın?*\n\n" + "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)]), parse_mode='Markdown')
    bot.register_next_step_handler(message, api_zamanla_sec)

def api_zamanla_sec(message):
    global api_zamanla_ismi
    apiler = api_dosyalari()
    secim = message.text.strip()
    if secim.isdigit() and 1 <= int(secim) <= len(apiler):
        api_zamanla_ismi = apiler[int(secim)-1]
    elif secim in apiler:
        api_zamanla_ismi = secim
    else:
        bot.reply_to(message, "❌ Geçersiz seçim!")
        return
    bot.reply_to(message, "⏰ *Kaç dakika sonra dursun?*\n(Sadece sayı girin, örn: 30)")
    bot.register_next_step_handler(message, api_zamanla_sure)

def api_zamanla_sure(message):
    try:
        sure_dk = int(message.text.strip())
        sure_sn = sure_dk * 60
        if api_zamanla(api_zamanla_ismi, sure_sn):
            bot.reply_to(message, f"⏰ `{api_zamanla_ismi}` {sure_dk} dakika sonra duracak!", parse_mode='Markdown')
        else:
            bot.reply_to(message, "❌ Zaten zamanlı API!")
    except:
        bot.reply_to(message, "❌ Geçersiz süre!")

@bot.message_handler(commands=['bakim'])
def cmd_bakim(message):
    if message.chat.id != ADMIN_ID:
        return
    global BAKIM_MODU
    BAKIM_MODU = not BAKIM_MODU
    durum = "AÇIK" if BAKIM_MODU else "KAPALI"
    bot.reply_to(message, f"🔧 *BAKIM MODU*\n\nDurum: {durum}", parse_mode='Markdown')

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
        "/newapi - Yeni API oluştur (dosya gönder)\n"
        "/liste - API listesi\n"
        "/durum - Sistem durumu (CPU/RAM)\n"
        "/api_durdur - API durdur\n"
        "/api_sil - API sil\n"
        "/api_zamanla - API'yi zamanla\n"
        "/bakim - Bot bakım modu\n"
        "/temizlik - Temizlik\n"
        "/yardim - Bu menü\n\n"
        "✅ *DESTEKLENEN FORMATLAR:*\n"
        "• JSON (.json)\n"
        "• TXT (.txt)\n"
        "• CSV (.csv)\n\n"
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
        "apis": apiler
    })

# ==================== BOTU BAŞLAT ====================
def start_bot():
    print("🤖 Bot başlatılıyor...")
    print(f"👑 Admin ID: {ADMIN_ID}")
    bot.infinity_polling(timeout=60, long_polling_timeout=60)

if __name__ == '__main__':
    thread = threading.Thread(target=start_bot, daemon=True)
    thread.start()
    print("🚀 Flask sunucusu başlatılıyor...")
    app.run(host='0.0.0.0', port=10000, debug=False)
