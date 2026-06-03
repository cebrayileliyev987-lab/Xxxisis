from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# Aynı dizindeki txt dosyasını oku
DOSYA_YOLU = os.path.join(os.path.dirname(__file__), 'turknetrinex.txt')

def verileri_yukle():
    try:
        with open(DOSYA_YOLU, 'r', encoding='utf-8') as f:
            icerik = f.read().strip()
        
        if not icerik:
            print("❌ Dosya boş!")
            return []
        
        # JSON'u parse et
        veri = json.loads(icerik)
        
        # Eğer gelen veri sözlük (dict) ise listeye çevir
        if isinstance(veri, dict):
            return [veri]
        elif isinstance(veri, list):
            return veri
        else:
            print("❌ Bilinmeyen format")
            return []
            
    except FileNotFoundError:
        print(f"❌ Dosya bulunamadı: {DOSYA_YOLU}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON hatası: {e}")
        return []
    except Exception as e:
        print(f"❌ Hata: {e}")
        return []

# Veritabanını yükle
VERITABANI = verileri_yukle()
print(f"✅ {len(VERITABANI)} kayıt yüklendi!")

@app.route('/')
def home():
    return jsonify({
        "status": "API Calisiyor",
        "kayit_sayisi": len(VERITABANI),
        "endpoints": {
            "/tumveriler": "Tum verileri goster",
            "/sorgula?ad=X&soyad=Y": "Ad soyad sorgula",
            "/sorgula?tc=X": "TC sorgula",
            "/sorgula?hatno=X": "Hat no sorgula"
        }
    })

@app.route('/tumveriler')
def tumveriler():
    return jsonify({"toplam": len(VERITABANI), "veriler": VERITABANI})

@app.route('/sorgula')
def sorgula():
    ad = request.args.get('ad', '').upper()
    soyad = request.args.get('soyad', '').upper()
    tc = request.args.get('tc', '')
    hatno = request.args.get('hatno', '')
    
    if not VERITABANI:
        return jsonify({"hata": "Veritabanı boş! turknetrinex.txt dosyasını kontrol et."}), 503
    
    if ad and soyad:
        sonuc = [v for v in VERITABANI if v.get('AD', '').upper() == ad and v.get('SOYAD', '').upper() == soyad]
    elif tc:
        sonuc = [v for v in VERITABANI if v.get('TC_KIMLIK') == tc]
    elif hatno:
        sonuc = [v for v in VERITABANI if v.get('HAT_NO') == hatno]
    else:
        return jsonify({"hata": "Kullanım: ?ad=BEYZANUR&soyad=KOSEOGLU veya ?tc=10001763200 veya ?hatno=1780341975"}), 400
    
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

# POST metodları da eklendi
@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad():
    data = request.get_json()
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    sonuc = [v for v in VERITABANI if v.get('AD', '').upper() == ad and v.get('SOYAD', '').upper() == soyad]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc():
    data = request.get_json()
    tc = data.get('tc', '')
    sonuc = [v for v in VERITABANI if v.get('TC_KIMLIK') == tc]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno():
    data = request.get_json()
    hatno = data.get('hatno', '')
    sonuc = [v for v in VERITABANI if v.get('HAT_NO') == hatno]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
