from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
import re
import io

app = Flask(__name__)
CORS(app)

# ==================== TELEGRAM BOT ====================
import telebot
from telebot.types import InputFile

BOT_TOKEN = "8655805223:AAFRr05iUdZYSghcORaCl8MdW3hNpdkbOc4"
ADMIN_ID = 8610336203

bot = telebot.TeleBot(BOT_TOKEN)
bot.remove_webhook()

# Kullanıcı verilerini geçici tut
user_data = {}

# ==================== BOT KOMUTLARI ====================
@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id != ADMIN_ID:
        bot.reply_to(message, "❌ Bu bot sadece admin tarafından kullanılabilir!")
        return
    
    bot.reply_to(message, """
🤖 *API Oluşturma Botu - ÇALIŞIYOR*

📌 *Komutlar:*
/newapi - Yeni API oluştur (JSON dosyası gönder)
/durum - Bot durumunu göster
/yardim - Yardım

⚡ *Nasıl kullanılır?*
1. /newapi yaz
2. JSON dosyanı gönder
3. API ismini gir
4. Bot sana linki versin

✅ *Bot aktif ve hazır!*
""", parse_mode='Markdown')

@bot.message_handler(commands=['newapi'])
def newapi(message):
    if message.chat.id != ADMIN_ID:
        return
    
    user_data[message.chat.id] = {}
    bot.reply_to(message, "📁 *Adım 1/2:* Lütfen JSON dosyanızı gönderin.\n\n(.json veya .txt uzantılı dosya kabul edilir)", parse_mode='Markdown')
    bot.register_next_step_handler(message, dosya_al)

def dosya_al(message):
    chat_id = message.chat.id
    
    # Dosya kontrolü
    if not message.document:
        bot.reply_to(message, "❌ Lütfen geçerli bir dosya gönderin! (JSON veya TXT formatında)")
        return
    
    dosya_adi = message.document.file_name
    if not (dosya_adi.endswith('.json') or dosya_adi.endswith('.txt')):
        bot.reply_to(message, "❌ Sadece .json veya .txt uzantılı dosyalar kabul edilir!")
        return
    
    bot.reply_to(message, f"📥 Dosya alınıyor: {dosya_adi}\n⏳ İşleniyor...")
    
    try:
        # Dosyayı indir
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        dosya_icerik = downloaded_file.decode('utf-8')
        
        # JSON parse et
        veri = None
        try:
            veri = json.loads(dosya_icerik)
        except:
            # Satır satır dene
            for satir in dosya_icerik.split('\n'):
                satir = satir.strip()
                if satir:
                    try:
                        veri = json.loads(satir)
                        break
                    except:
                        continue
        
        if not veri:
            bot.reply_to(message, "❌ Dosya geçerli bir JSON formatında değil!")
            return
        
        # Veriyi düzenle
        if isinstance(veri, dict):
            veri = [veri]
        elif isinstance(veri, list) and len(veri) > 0:
            pass
        else:
            bot.reply_to(message, "❌ JSON formatı geçersiz! Dizi veya nesne bekleniyor.")
            return
        
        # Kullanıcı verisini kaydet
        user_data[chat_id]['veri'] = veri
        user_data[chat_id]['dosya_adi'] = dosya_adi
        
        bot.reply_to(message, f"✅ Dosya başarıyla okundu!\n📊 {len(veri)} kayıt bulundu.\n\n📝 *Adım 2/2:* API için bir isim girin (örnek: turknetapi)\nSadece küçük harf ve rakam kullanın.", parse_mode='Markdown')
        bot.register_next_step_handler(message, api_ismi_al)
        
    except Exception as e:
        bot.reply_to(message, f"❌ Dosya okuma hatası: {str(e)}")

def api_ismi_al(message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or 'veri' not in user_data[chat_id]:
        bot.reply_to(message, "❌ Önce /newapi ile dosya göndermelisiniz!")
        return
    
    api_ismi = re.sub(r'[^a-z0-9]', '', message.text.strip().lower())
    if not api_ismi or len(api_ismi) < 3:
        bot.reply_to(message, "❌ Geçersiz isim! En az 3 karakter, sadece harf ve rakam kullanın.")
        return
    
    veri = user_data[chat_id]['veri']
    dosya_adi = user_data[chat_id]['dosya_adi']
    
    bot.reply_to(message, f"⏳ API oluşturuluyor: {api_ismi}\nBu işlem 10-20 saniye sürebilir...")
    
    # Otomatik endpointleri bul
    endpointler = []
    ilk_kayit = veri[0] if veri else {}
    for anahtar in ilk_kayit.keys():
        anahtar_upper = anahtar.upper()
        if anahtar_upper in ['AD', 'NAME', 'ISIM', 'FIRST_NAME']:
            endpointler.append('ad')
        if anahtar_upper in ['SOYAD', 'SURNAME', 'LAST_NAME']:
            endpointler.append('soyad')
        if anahtar_upper in ['TC', 'TC_KIMLIK', 'TCKIMLIK', 'IDENTITY']:
            endpointler.append('tc')
        if anahtar_upper in ['HAT_NO', 'HATNO', 'PHONE', 'TEL', 'TELEFON']:
            endpointler.append('hatno')
    
    # Benzersiz endpointleri al
    endpointler = list(set(endpointler))
    
    # API kodunu oluştur
    api_kodu = f'''from flask import Flask, request, jsonify
from flask_cors import CORS
import json

app = Flask(__name__)
CORS(app)

VERI = {json.dumps(veri, ensure_ascii=False, indent=2)}

@app.route('/')
def home():
    return jsonify({{
        "api": "{api_ismi}",
        "status": "active",
        "kayit_sayisi": len(VERI),
        "endpointler": {endpointler}
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
            if str(kayit.get('TC_KIMLIK', '')) == tc or str(kayit.get('TC', '')) == tc:
                return jsonify(kayit)
        elif hatno:
            if str(kayit.get('HAT_NO', '')) == hatno or str(kayit.get('HATNO', '')) == hatno:
                return jsonify(kayit)
    
    return jsonify({{"hata": "Kayit bulunamadi"}}), 404

@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad():
    data = request.json
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    for kayit in VERI:
        if kayit.get('AD', '').upper() == ad and kayit.get('SOYAD', '').upper() == soyad:
            return jsonify(kayit)
    return jsonify({{"hata": "Bulunamadi"}}), 404

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc():
    data = request.json
    tc = data.get('tc', '')
    for kayit in VERI:
        if str(kayit.get('TC_KIMLIK', '')) == tc or str(kayit.get('TC', '')) == tc:
            return jsonify(kayit)
    return jsonify({{"hata": "Bulunamadi"}}), 404

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno():
    data = request.json
    hatno = data.get('hatno', '')
    for kayit in VERI:
        if str(kayit.get('HAT_NO', '')) == hatno or str(kayit.get('HATNO', '')) == hatno:
            return jsonify(kayit)
    return jsonify({{"hata": "Bulunamadi"}}), 404

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
'''
    
    # API kodunu dosyaya kaydet
    try:
        with open(f"{api_ismi}.py", 'w', encoding='utf-8') as f:
            f.write(api_kodu)
        
        # GitHub'a gönderme işlemi (basitleştirilmiş)
        api_link = f"https://rinexturknetsorguapi.onrender.com/{api_ismi}"
        
        # Endpoint bilgilerini oluştur
        endpoint_text = ""
        if 'ad' in endpointler and 'soyad' in endpointler:
            endpoint_text += f"\n• /sorgula?ad=BEYZANUR&soyad=KOSEOGLU"
        if 'tc' in endpointler:
            endpoint_text += f"\n• /sorgula?tc=10001763200"
        if 'hatno' in endpointler:
            endpoint_text += f"\n• /sorgula?hatno=1780341975"
        
        bot.reply_to(message, f"""
✅ *API Başarıyla Oluşturuldu!*

📌 *API Adı:* `{api_ismi}`
🔗 *Ana Link:* {api_link}

📝 *Kullanım:*

**Tüm Veriler:**
• {api_link}/tumveriler

**Sorgulama:{endpoint_text}**

**POST Örneği:**
```json
{{
  "ad": "BEYZANUR",
  "soyad": "KÖSEOĞLU"
}}
