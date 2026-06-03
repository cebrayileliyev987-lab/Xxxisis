from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import threading
import time
import psutil
import csv
import io

app = Flask(__name__)
CORS(app)

# ==================== KONFIGURASYON ====================
BOT_TOKEN = "8655805223:AAGf7anf_9bMlVB1B9MXZVgsSnytGgum5ic"
ADMIN_ID = 8610336203
RENDER_URL = "https://rinexturknetsorguapi.onrender.com"

# Bot durumları
BAKIM_MODU = False
API_ZAMANLAYICI = {}  # {api_ismi: kapanma_zamani}

# ==================== TELEGRAM BOT ====================
import telebot
bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

user_data = {}

# ==================== DOSYA OKUYUCU (HER FORMAT) ====================
def dosya_oku_her_format(dosya_adi, dosya_icerik):
    """TXT, CSV, JSON her formatı okur, tüm verileri alır"""
    veriler = []
    
    # 1. JSON dene
    try:
        veri = json.loads(dosya_icerik)
        if isinstance(veri, dict):
            return [veri]
        elif isinstance(veri, list):
            return veri
    except:
        pass
    
    # 2. CSV dene
    if dosya_adi.endswith('.csv'):
        try:
            csv_reader = csv.DictReader(io.StringIO(dosya_icerik))
            for row in csv_reader:
                veriler.append(row)
            if veriler:
                return veriler
        except:
            pass
    
    # 3. Satır satır JSON dene
    for satir in dosya_icerik.split('\n'):
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
    
    # 4. Virgülle ayrılmış değerler (CSV benzeri)
    if ',' in dosya_icerik[:500]:
        lines = dosya_icerik.strip().split('\n')
        if len(lines) > 1:
            basliklar = [h.strip() for h in lines[0].split(',')]
            for line in lines[1:]:
                degerler = [d.strip() for d in line.split(',')]
                if len(degerler) == len(basliklar):
                    satir_veri = {}
                    for i, baslik in enumerate(basliklar):
                        satir_veri[baslik] = degerler[i]
                    veriler.append(satir_veri)
            if veriler:
                return veriler
    
    # 5. İçindeki tüm JSON'ları bul
    json_pattern = r'\{[^{}]*\}'
    bulunanlar = re.findall(json_pattern, dosya_icerik)
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
    
    # 6. Hiçbir şey bulunamazsa, ham metni tek veri olarak al
    return [{"veri": dosya_icerik[:1000]}]

# ==================== API YÖNETİM ====================
def api_listesi():
    return [f.replace('.py', '') for f in os.listdir('.') if f.endswith('.py') and f not in ['app.py']]

def api_olustur(api_ismi, veri):
    """API kodunu oluşturur"""
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
    
    return api_link, endpoints

def api_durdur(api_ismi):
    try:
        os.remove(f"{api_ismi}.py")
        return True
    except:
        return False

def api_baslat(api_ismi, veri):
    return api_olustur(api_ismi, veri)

def api_zamanlayici_ekle(api_ismi, sure_dakika):
    API_ZAMANLAYICI[api_ismi] = time.time() + (sure_dakika * 60)
    return True

def renk(metin, renk):
    emoji = {"kirmizi": "🔴", "yesil": "🟢", "mavi": "🔵", "sari": "🟡", "mor": "🟣", "turuncu": "🟠"}
    return f"{emoji.get(renk, '⚪')} {metin}"

# ==================== BOT KOMUTLARI ====================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ Yetkiniz yok!")
        return
    bot.reply_to(message,
        "🟢 *HOŞ GELDİNİZ*\n\n"
        "🤖 *GELİŞMİŞ API YÖNETİM BOTU*\n\n"
        "📌 *KOMUTLAR:*\n"
        "/newapi - Yeni API oluştur (JSON/TXT/CSV gönder)\n"
        "/liste - API listesi\n"
        "/durum - Sistem durumu (CPU/RAM)\n"
        "/api_durdur - API durdur\n"
        "/api_baslat - API başlat\n"
        "/api_zamanla - API'yi süreli kapat\n"
        "/api_bakim - API bakım modu\n"
        "/bakim - Bot bakım modu\n"
        "/temizlik - Temizlik\n"
        "/yardim - Yardım\n\n"
        f"🔗 {RENDER_URL}", parse_mode='Markdown')

@bot.message_handler(commands=['newapi'])
def cmd_newapi(message):
    if message.chat.id != ADMIN_ID:
        return
    if BAKIM_MODU:
        bot.reply_to(message, "⚠️ Bot bakım modunda!")
        return
    user_data[message.chat.id] = {'adim': 1}
    bot.reply_to(message,
        "📁 *Dosyanızı gönderin*\n\n"
        "Desteklenen formatlar:\n"
        "• JSON (.json)\n"
        "• TXT (.txt)\n"
        "• CSV (.csv)\n\n"
        "Dosyadaki TÜM VERİLER otomatik API olacak!", parse_mode='Markdown')
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
        
        dosya_icerik = response.text
        
        # Dosyayı oku
        veri = dosya_oku_her_format(dosya_adi, dosya_icerik)
        
        if not veri or len(veri) == 0:
            bot.reply_to(message, "❌ Dosya okunamadı! İlk 200 karakter:\n" + dosya_icerik[:200])
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
        bot.reply_to(message, "❌ Geçersiz isim! En az 2 karakter, harf/rakam.")
        return
    
    veri = user_data[chat_id]['veri']
    dosya_adi = user_data[chat_id].get('dosya_adi', 'bilinmiyor')
    
    bot.reply_to(message, f"⚙️ *API oluşturuluyor:* {api_ismi}\n⏳ Lütfen bekleyin...", parse_mode='Markdown')
    
    try:
        api_link, endpoints = api_olustur(api_ismi, veri)
        
        # Kullanım örnekleri
        ornekler = []
        if 'adsoyad' in endpoints:
            ornekler.append(f"• {api_link}/sorgula?ad=AHMET&soyad=YILMAZ")
            ornekler.append(f"• POST: {api_link}/sorgu/adsoyad")
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
            f"⚡ *TÜM VERİLER:* {api_link}/tumveriler\n\n"
            f"✅ *API AKTİF!*", parse_mode='Markdown')
        
        del user_data[chat_id]
        
    except Exception as e:
        bot.reply_to(message, f"❌ Oluşturma hatası: {str(e)[:200]}")

@bot.message_handler(commands=['liste'])
def cmd_liste(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_listesi()
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
    ram_kullanilan = psutil.virtual_memory().used / (1024 * 1024)
    ram_toplam = psutil.virtual_memory().total / (1024 * 1024)
    apiler = api_listesi()
    
    bot.reply_to(message,
        f"📊 *SİSTEM DURUMU*\n\n"
        f"💻 *CPU:* %{cpu}\n"
        f"🧠 *RAM:* %{ram} ({ram_kullanilan:.0f}MB / {ram_toplam:.0f}MB)\n"
        f"🤖 *Bot:* {'Aktif' if not BAKIM_MODU else 'Bakım'}\n"
        f"📦 *API Sayısı:* {len(apiler)}\n"
        f"⏱️ *Zamanlı API:* {len(API_ZAMANLAYICI)}\n"
        f"👑 *Admin:* {ADMIN_ID}\n"
        f"🔗 {RENDER_URL}", parse_mode='Markdown')

@bot.message_handler(commands=['api_durdur'])
def cmd_api_durdur(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_listesi()
    if not apiler:
        bot.reply_to(message, "❌ Durdurulacak API yok!")
        return
    liste = "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)])
    bot.reply_to(message, f"⏹️ *Hangi API durdurulsun?*\n\n{liste}\n\nSayı veya isim girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, api_durdur_sec)

def api_durdur_sec(message):
    apiler = api_listesi()
    secim = message.text.strip()
    if secim.isdigit() and 1 <= int(secim) <= len(apiler):
        api_ismi = apiler[int(secim)-1]
    elif secim in apiler:
        api_ismi = secim
    else:
        bot.reply_to(message, "❌ Geçersiz seçim!")
        return
    if api_durdur(api_ismi):
        bot.reply_to(message, f"⏹️ `{api_ismi}` API'si durduruldu!", parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Durdurulamadı!")

@bot.message_handler(commands=['api_baslat'])
def cmd_api_baslat(message):
    bot.reply_to(message, "📝 Daha önce oluşturduğunuz bir API'yi başlatmak için dosyayı tekrar göndermeniz gerekir.\n\n/newapi ile yeni API oluşturun.", parse_mode='Markdown')

@bot.message_handler(commands=['api_zamanla'])
def cmd_api_zamanla(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_listesi()
    if not apiler:
        bot.reply_to(message, "❌ Zamanlanacak API yok!")
        return
    liste = "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)])
    bot.reply_to(message, f"⏰ *Hangi API zamanlansın?*\n\n{liste}\n\nSayı veya isim girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, api_zamanla_sec)

def api_zamanla_sec(message):
    apiler = api_listesi()
    secim = message.text.strip()
    if secim.isdigit() and 1 <= int(secim) <= len(apiler):
        api_ismi = apiler[int(secim)-1]
    elif secim in apiler:
        api_ismi = secim
    else:
        bot.reply_to(message, "❌ Geçersiz seçim!")
        return
    bot.reply_to(message, "⏰ *Kaç dakika sonra kapansın?*\n\n(Örn: 30, 60, 120)", parse_mode='Markdown')
    bot.register_next_step_handler(message, api_zamanla_sure, api_ismi)

def api_zamanla_sure(message, api_ismi):
    try:
        sure = int(message.text.strip())
        if sure < 1:
            bot.reply_to(message, "❌ En az 1 dakika girin!")
            return
        api_zamanlayici_ekle(api_ismi, sure)
        bot.reply_to(message, f"⏰ `{api_ismi}` API'si {sure} dakika sonra otomatik kapanacak!", parse_mode='Markdown')
        
        # Arka planda zamanlayıcı
        def kapat():
            time.sleep(sure * 60)
            if api_ismi in API_ZAMANLAYICI:
                api_durdur(api_ismi)
                del API_ZAMANLAYICI[api_ismi]
        threading.Thread(target=kapat, daemon=True).start()
        
    except:
        bot.reply_to(message, "❌ Geçersiz süre! Sayı girin.")

@bot.message_handler(commands=['api_bakim'])
def cmd_api_bakim(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_listesi()
    if not apiler:
        bot.reply_to(message, "❌ API yok!")
        return
    liste = "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)])
    bot.reply_to(message, f"🔧 *Hangi API bakıma alınsın?*\n\n{liste}\n\nSayı veya isim girin:", parse_mode='Markdown')
    bot.register_next_step_handler(message, api_bakim_sec)

def api_bakim_sec(message):
    apiler = api_listesi()
    secim = message.text.strip()
    if secim.isdigit() and 1 <= int(secim) <= len(apiler):
        api_ismi = apiler[int(secim)-1]
    elif secim in apiler:
        api_ismi = secim
    else:
        bot.reply_to(message, "❌ Geçersiz seçim!")
        return
    
    try:
        with open(f"{api_ismi}.py", 'r', encoding='utf-8') as f:
            icerik = f.read()
        icerik = icerik.replace('"active"', '"bakim"')
        icerik = icerik.replace("'active'", "'bakim'")
        with open(f"{api_ismi}.py", 'w', encoding='utf-8') as f:
            f.write(icerik)
        bot.reply_to(message, f"🔧 `{api_ismi}` API'si bakım moduna alındı!", parse_mode='Markdown')
    except:
        bot.reply_to(message, "❌ Bakım modu hatası!")

@bot.message_handler(commands=['bakim'])
def cmd_bakim(message):
    if message.chat.id != ADMIN_ID:
        return
    global BAKIM_MODU
    BAKIM_MODU = not BAKIM_MODU
    durum = "AÇIK" if BAKIM_MODU else "KAPALI"
    bot.reply_to(message, f"🔧 *BOT BAKIM MODU*\n\nDurum: {durum}", parse_mode='Markdown')

@bot.message_handler(commands=['temizlik'])
def cmd_temizlik(message):
    if message.chat.id != ADMIN_ID:
        return
    silinen = 0
    for f in os.listdir('.'):
        if f.endswith('.py') and f not in ['app.py']:
            os.remove(f)
            silinen += 1
    API_ZAMANLAYICI.clear()
    bot.reply_to(message, f"🧹 *TEMİZLİK*\n\n{silinen} API dosyası silindi.\n{len(API_ZAMANLAYICI)} zamanlayıcı temizlendi.", parse_mode='Markdown')

@bot.message_handler(commands=['yardim'])
def cmd_yardim(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.reply_to(message,
        "📖 *YARDIM MENÜSÜ*\n\n"
        "📌 *KOMUTLAR:*\n"
        "/newapi - Yeni API oluştur (JSON/TXT/CSV gönder)\n"
        "/liste - API listesi\n"
        "/durum - Sistem durumu (CPU/RAM)\n"
        "/api_durdur - API durdur\n"
        "/api_baslat - API başlat\n"
        "/api_zamanla - API'yi süreli kapat\n"
        "/api_bakim - API bakım modu\n"
        "/bakim - Bot bakım modu\n"
        "/temizlik - Temizlik\n"
        "/yardim - Bu menü\n\n"
        "📁 *NASIL KULLANILIR?*\n"
        "1. /newapi yazın\n"
        "2. Dosyanızı gönderin (JSON/TXT/CSV)\n"
        "3. API ismini girin\n"
        "4. API hazır!\n\n"
        "⚡ *ÖZELLİKLER:*\n"
        "• Tüm formatları destekler\n"
        "• Otomatik endpoint\n"
        "• Düşük CPU/RAM\n"
        "• Zamanlı kapatma\n"
        "• Bakım modu\n\n"
        f"🔗 {RENDER_URL}", parse_mode='Markdown')

# ==================== WEB SUNUCU ====================
@app.route('/')
def web_home():
    if BAKIM_MODU:
        return jsonify({"status": "bakim", "message": "Bot bakım modunda"})
    apiler = api_listesi()
    return jsonify({
        "status": "active",
        "bot": "Gelişmiş API Yönetim Botu",
        "api_sayisi": len(apiler),
        "apis": apiler,
        "zamanli_api": list(API_ZAMANLAYICI.keys())
    })

@app.route('/api/<api_ismi>/durum')
def api_durum_web(api_ismi):
    apiler = api_listesi()
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
