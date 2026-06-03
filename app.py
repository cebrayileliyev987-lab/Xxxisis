from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os

app = Flask(__name__)
CORS(app)

# JSON dosyasının yolu (app.py ile aynı klasörde)
JSON_DOSYA = os.path.join(os.path.dirname(__file__), 'turknetrinex.json')

def verileri_yukle():
    try:
        with open(JSON_DOSYA, 'r', encoding='utf-8') as f:
            veri = json.load(f)
        
        # Eğer gelen veri dict ise listeye çevir
        if isinstance(veri, dict):
            veritabani = [veri]
        elif isinstance(veri, list):
            veritabani = veri
        else:
            veritabani = []
        
        print(f"✅ {len(veritabani)} kayıt yüklendi!")
        return veritabani
        
    except FileNotFoundError:
        print(f"❌ Dosya bulunamadı: {JSON_DOSYA}")
        return []
    except json.JSONDecodeError as e:
        print(f"❌ JSON hatası: {e}")
        return []

# Veritabanını yükle
VERITABANI = verileri_yukle()

@app.route('/')
def home():
    return jsonify({
        "status": "API Calisiyor",
        "kayit_sayisi": len(VERITABANI),
        "veri_kaynagi": "turknetrinex.json",
        "endpoints": {
            "/tumveriler": "Tum verileri goster",
            "/sorgula?ad=X&soyad=Y": "Ad soyad sorgula",
            "/sorgula?tc=X": "TC sorgula",
            "/sorgula?hatno=X": "Hat no sorgula"
        }
    })

@app.route('/tumveriler')
def tumveriler():
    return jsonify({
        "toplam": len(VERITABANI),
        "veriler": VERITABANI
    })

@app.route('/sorgula')
def sorgula():
    ad = request.args.get('ad', '').upper().strip()
    soyad = request.args.get('soyad', '').upper().strip()
    tc = request.args.get('tc', '').strip()
    hatno = request.args.get('hatno', '').strip()
    
    if not VERITABANI:
        return jsonify({"hata": "Veritabanı boş! turknetrinex.json dosyasını kontrol et."}), 503
    
    if ad and soyad:
        sonuc = [m for m in VERITABANI 
                 if m.get('AD', '').upper() == ad 
                 and m.get('SOYAD', '').upper() == soyad]
    elif tc:
        sonuc = [m for m in VERITABANI if m.get('TC_KIMLIK') == tc]
    elif hatno:
        sonuc = [m for m in VERITABANI if m.get('HAT_NO') == hatno]
    else:
        return jsonify({
            "hata": "Kullanım örnekleri:",
            "ad_soyad": "/sorgula?ad=BEYZANUR&soyad=KOSEOGLU",
            "tc": "/sorgula?tc=10001763200",
            "hatno": "/sorgula?hatno=1780341975"
        }), 400
    
    return jsonify({
        "bulunan": len(sonuc), 
        "sonuclar": sonuc
    })

# POST metodları
@app.route('/sorgu/adsoyad', methods=['POST'])
def sorgu_adsoyad():
    data = request.get_json()
    if not data:
        return jsonify({"hata": "JSON body gerekli"}), 400
    ad = data.get('ad', '').upper()
    soyad = data.get('soyad', '').upper()
    sonuc = [m for m in VERITABANI if m.get('AD', '').upper() == ad and m.get('SOYAD', '').upper() == soyad]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/tc', methods=['POST'])
def sorgu_tc():
    data = request.get_json()
    if not data:
        return jsonify({"hata": "JSON body gerekli"}), 400
    tc = data.get('tc', '')
    sonuc = [m for m in VERITABANI if m.get('TC_KIMLIK') == tc]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

@app.route('/sorgu/hatno', methods=['POST'])
def sorgu_hatno():
    data = request.get_json()
    if not data:
        return jsonify({"hata": "JSON body gerekli"}), 400
    hatno = data.get('hatno', '')
    sonuc = [m for m in VERITABANI if m.get('HAT_NO') == hatno]
    return jsonify({"bulunan": len(sonuc), "sonuclar": sonuc})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
