from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import time
import threading
import psutil

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
    bot.reply_to(message, "📁 JSON dosyanızı gönderin.\n\nÖrnek format:\n{\"AD\":\"AHMET\",\"SOYAD\":\"YILMAZ\",\"TC\":\"12345678901\"}")
    bot.register_next_step_handler(message, dosya_al)

def dosya_al(message):
    chat_id = message.chat.id
    if not message.document:
        bot.reply_to(message, "❌ Dosya gönderin!")
        bot.register_next_step_handler(message, dosya_al)
        return
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        icerik = downloaded.decode('utf-8')
        veri = dosya_oku(icerik)
        if not veri:
            bot.reply_to(message, "❌ Dosya okunamadı!")
            return
        user_data[chat_id]['veri'] = veri
        bot.reply_to(message, f"✅ {len(veri)} kayıt okundu.\n\nAPI için isim girin (küçük harf, rakam):")
        bot.register_next_step_handler(message, api_ismi_al)
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)[:100]}")

def api_ismi_al(message):
    chat_id = message.chat.id
    if chat_id not in user_data:
        bot.reply_to(message, "❌ Önce /newapi ile başlayın!")
        return
    api_ismi = re.sub(r'[^a-z0-9]', '', message.text.strip().lower())
    if not api_ismi or len(api_ismi) < 2:
        bot.reply_to(message, "❌ Geçersiz isim!")
        return
    veri = user_data[chat_id]['veri']
    bot.reply_to(message, f"⚙️ API oluşturuluyor: {api_ismi}")
    
    # Endpoint algılama
    ilk = veri[0] if veri else {}
    endpoints = []
    for k in ilk.keys():
        uk = k.upper()
        if uk in ['AD', 'NAME', 'ISIM']:
            endpoints.append('adsoyad')
        if uk in ['SOYAD', 'SURNAME']:
            endpoints.append('adsoyad')
        if uk in ['TC', 'TC_KIMLIK']:
            endpoints.append('tc')
        if uk in ['HAT_NO', 'HATNO', 'PHONE']:
            endpoints.append('hatno')
    endpoints = list(set(endpoints))
    if not endpoints:
        endpoints = ['tumveriler']
    
    api_link = f"{RENDER_URL}/{api_ismi}"
    
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
    
    try:
        with open(f"{api_ismi}.py", 'w', encoding='utf-8') as f:
            f.write(api_kodu)
        
        bot.reply_to(message, 
            f"✅ API OLUŞTURULDU!\n\n"
            f"📌 İsim: {api_ismi}\n"
            f"🔗 Link: {api_link}\n"
            f"📊 Kayıt: {len(veri)}\n\n"
            f"🔗 KULLANIM:\n"
            f"• {api_link}/tumveriler\n"
            f"• {api_link}/sorgula?ad=AHMET&soyad=YILMAZ\n\n"
            f"✅ API AKTİF")
        del user_data[chat_id]
    except Exception as e:
        bot.reply_to(message, f"❌ Hata: {str(e)[:100]}")

@bot.message_handler(commands=['liste'])
def cmd_liste(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_dosyalari()
    if not apiler:
        bot.reply_to(message, "📭 API yok")
    else:
        liste = "\n".join([f"• {a} - {RENDER_URL}/{a}" for a in apiler])
        bot.reply_to(message, f"📋 API LİSTEM\n\n{liste}\n\nToplam: {len(apiler)} API")

@bot.message_handler(commands=['durum'])
def cmd_durum(message):
    if message.chat.id != ADMIN_ID:
        return
    cpu = psutil.cpu_percent(interval=0.5)
    ram = psutil.virtual_memory().percent
    apiler = api_dosyalari()
    bot.reply_to(message, 
        f"📊 SİSTEM DURUMU\n\n"
        f"💻 CPU: %{cpu}\n"
        f"🧠 RAM: %{ram}\n"
        f"🤖 Bot: {'Aktif' if not BAKIM_MODU else 'Bakım'}\n"
        f"📦 API Sayısı: {len(apiler)}\n"
        f"👑 Admin: {ADMIN_ID}\n"
        f"🔗 {RENDER_URL}")

@bot.message_handler(commands=['bakim'])
def cmd_bakim(message):
    if message.chat.id != ADMIN_ID:
        return
    global BAKIM_MODU
    BAKIM_MODU = not BAKIM_MODU
    durum = "AÇIK" if BAKIM_MODU else "KAPALI"
    bot.reply_to(message, f"🔧 BAKIM MODU\n\nDurum: {durum}")

@bot.message_handler(commands=['api_sil'])
def cmd_api_sil(message):
    if message.chat.id != ADMIN_ID:
        return
    apiler = api_dosyalari()
    if not apiler:
        bot.reply_to(message, "❌ API yok!")
        return
    bot.reply_to(message, f"Hangi API silinsin?\n\n" + "\n".join([f"{i+1}. {a}" for i, a in enumerate(apiler)]))
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
        bot.reply_to(message, f"🗑️ {api_ismi} silindi!")
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
    bot.reply_to(message, f"🧹 TEMİZLİK\n\n{silinen} API dosyası silindi.")

@bot.message_handler(commands=['yardim'])
def cmd_yardim(message):
    if message.chat.id != ADMIN_ID:
        return
    bot.reply_to(message,
        "📖 YARDIM MENÜSÜ\n\n"
        "📌 KOMUTLAR:\n"
        "/newapi - Yeni API oluştur\n"
        "/liste - API listesi\n"
        "/durum - Sistem durumu\n"
        "/api_sil - API sil\n"
        "/bakim - Bakım modu\n"
        "/temizlik - Temizlik\n"
        "/yardim - Bu menü\n\n"
        f"🔗 {RENDER_URL}")

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
